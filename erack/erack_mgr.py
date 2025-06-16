import collections
import traceback
import threading
import time
import socket
import re

import os
import logging.handlers as log_handler
import logging

import argparse

import semi.e88_equipment as E88 #can use singleton

import global_variables
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host #can use singleton
from global_variables import Erack

from global_variables import output
from global_variables import remotecmd_queue
import tools

import json
import copy
from pprint import pformat

import queue
import alarms

from erack.GpmErackAdapter_e88 import GpmErackAdapter
from erack.GyroErackAdapter_e88 import GyroErackAdapter
from erack.ICWiserErackAdapter_e88 import ICWiserErackAdapter
from erack.DummyPortAdapter_e88 import DummyPortAdapter
from erack.TurnTableAdapter_e88 import TurnTableAdapter
from erack.MFErackAdapter_e88 import MFErackAdapter
from erack.CDAErackAdapter_e88 import CDAErackAdapter #Sean for KumamotoTPB

from workstation.eq_mgr import EqMgr
from web_service_log import action_logger


class E88_ErackMgr(threading.Thread):
    __instance=None
    def getInstance():
        return __instance

    def __init__(self, secsgem_e88_h=None, config=[]):
        #print(self.secsgem_e88_h)
        self.eRacks={}
        self.erack_groups={}
        self.port_areas={}
        self.port_areas_revert={} #chocp 2022/4/12
        self.map_zones={}

        self.api_queue=queue.Queue()

        self.secsgem_e88_h=secsgem_e88_h
        self.tsclogger=logging.getLogger("tsc")

        #2024/1/24 add
        if self.secsgem_e88_h:
            self.secsgem_e88_h.remote_commands_callback=self.remote_command_callback
            self.secsgem_e88_h.initial()

            self.Transfers=self.secsgem_e88_h.Transfers
            self.Carriers=self.secsgem_e88_h.Carriers
            self.Carriers.Mapping={}
            self.Zones=self.secsgem_e88_h.Zones

        E88_ErackMgr.__instance=self
        threading.Thread.__init__(self)


    def remote_command_callback(self, obj):
        print("Callback get: ", obj)

        if obj['remote_cmd'] == 'sc_pause': #2022/08/09 Chi
            remotecmd_queue.append(obj)

        elif obj['remote_cmd'] == 'sc_resume': #2022/08/09 Chi
            remotecmd_queue.append(obj)

        elif obj['remote_cmd'] == 'transfer':
            self.Transfers.Data[obj['commandinfo']['CommandID']].State.transfer()
            self.Carriers.Data[obj['transferinfo']['CarrierID']].State.transfer()
            self.Transfers.Data[obj['commandinfo']['CommandID']].State.complete()
            self.Transfers.delete(obj['commandinfo']['CommandID'])
            self.Carriers.Data[obj['transferinfo']['CarrierID']].State.wait_out()

        elif obj['remote_cmd'] == 'associate': # Mike: 2021/06/18
            try:
                # Mike: 2021/08/10
                res, rack_id, port_no=tools.rackport_format_parse(obj['CarrierLoc'])
                if res:
                    port_idx=port_no-1
                    carrierID=obj['CarrierID']
                    data=obj['AssociateData']
                    # 9/19
                    for device_id, h_eRack in self.eRacks.items():
                        if rack_id == device_id:
                            h_eRack.eRackInfoUpdate({
                                'cmd':'associate',
                                'port_idx':port_idx,
                                'carrierID':carrierID,
                                'data':data})
                            break #chocp:2021/3/7



            except:
                pass

        elif obj['remote_cmd'] == 'infoupdate': # Mike: 2021/08/11
            try:
                res, rack_id, port_no=tools.rackport_format_parse(self.Carriers.Data[obj['CarrierID']].CarrierLoc)
                if res:
                    port_idx=port_no-1

                    carrierID=obj['CarrierID']
                    data=obj['Data']

                    # for
                    tmp={}
                    for label, value in obj['Data'].items():
                        if 'CARRIERINFO' in label:
                            if 'LABEL' in label:
                                key=obj['Data'][label]
                                val=obj['Data'][label.replace("LABEL", "")]
                                tmp[key]=val
                        else:
                            tmp[label]=value
                    data=tmp
                    print("data:{}".format(data))
                    action_logger.warning("data:{}".format(data))

                    # 9/19
                    for device_id, h_eRack in self.eRacks.items():
                        if rack_id == device_id:
                            if global_variables.erack_version != 'v3':
                                h_eRack.eRackInfoUpdate({
                                    'cmd':'infoupdate',
                                    'port_idx':port_idx,
                                    'carrierID':carrierID,
                                    'data':data})

                                if global_variables.RackNaming in [13, 35] and global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes':

                                    if global_variables.RackNaming == 35:
                                        for key in self.port_areas:
                                            if 'CrossFloor' in key:
                                                for item in self.port_areas[key]:
                                                    if item['rack_id'] == rack_id and item['slot_no'] == port_idx + 1:
                                                        break  # Stop looping once a match is found

                                    if '[HoldLot]' in data.get('desc'):
                                        # print('>>>>>data', data)
                                        exist_workID = EqMgr.getInstance().orderMgr.query_work_list_by_carrierID(carrierID)
                                        if exist_workID:
                                            obj={'remote_cmd':'work_cancel', 'WorkID':exist_workID}
                                            print('<<work_cancel_for_Hold>>:', obj)
                                            # self.Carriers.Data['carrierID']['cmd_send'] = False
                                            # print('>>>>Carrier_data'.format(self.Carriers.Data['carrierID']))
                                            remotecmd_queue.append(obj)

                                        break

                                    elif '[HoldLot]' not in data.get('desc'):
                                        if global_variables.RackNaming == 13:  # for UTAC usg1 filter
                                            for_stage=h_eRack.func.get('LotIn')
                                            if not for_stage or for_stage != data.get('stage'):
                                                print('for_stage check fail:', for_stage, data.get('stage'))
                                                break
                                        elif global_variables.RackNaming == 35:
                                            for_stage=h_eRack.func.get('LotIn', 'NoStage')
                                            if 'CrossFloor' in for_stage:
                                                data['stage']='CrossFloor'
                                            # print('for_stage', data['stage'])
                                            # first_machine = data.get('desc', '').split(',')[0].strip()
                                    WorkID=EqMgr.getInstance().orderMgr.infoupdate_work_list_by_carrierID(carrierID, data.get('lotID', ''), data.get('stage', ''), data.get('desc', ''), data.get('priority', 0))
                                    lot_id=data.get('lotID')
                                    #if not WorkID:
                                    if not WorkID and lot_id: #lotID need have

                                        uuid=100*time.time()
                                        uuid%=1000000000000
                                        workID='O%.12d'%uuid

                                        work={}
                                        work['workID']=workID
                                        work['CarrierID']=carrierID
                                        work['CarrierType']=data.get('carrierType', '')
                                        work['LotID']=data.get('lotID', '')
                                        work['Stage']=data.get('stage', '')
                                        work['Machine']=data.get('desc', '')
                                        work['Priority']=data.get('priority', 0)
                                        work['Couples']=data.get('couples', '')
                                        obj={'remote_cmd':'work_add', 'workinfo':work}
                                        # print('work_add:', data)
                                        remotecmd_queue.append(obj)


                            else:
                                h_eRack.change_state(h_eRack.carriers[port_idx], 'host_associate_cmd', data)

                            break #chocp:2021/3/7



            except Exception as e:
                print(e)
                pass

        elif obj['remote_cmd'] == 'infoupdatebyrack': # 2021/04/18 SJ
            try:
                h_eRack=self.eRacks.get(obj['ErackID'])
                tmp={}
                for label, value in obj['Data'].items():
                    tmp[label]=value.split(',')
                carrierlen=len(tmp['CARRIERID'])
                for i in range(carrierlen):
                    data={}
                    if tmp['CARRIERID'][i] in self.Carriers.Data:
                        res, rack_id, port_no=tools.rackport_format_parse(self.Carriers.Data[tmp['CARRIERID'][i]].CarrierLoc)
                        if res:
                            port_idx=port_no-1
                            for j in tmp:
                                data[j]=tmp[j][i]

                            carrierID=tmp['CARRIERID'][i]
                            h_eRack.eRackInfoUpdate({
                                'cmd':'infoupdate',
                                'port_idx':port_idx,
                                'carrierID':carrierID,
                                'data':data})

            except Exception as e:
                print(e)
                pass

        if obj['remote_cmd'] == 'book':
            device_id=obj['ZoneName']
            for erackid, h_eRack in self.eRacks.items():#2021/12/8
                if h_eRack.device_id == device_id:
                    h_eRack.book()
                    break

        if obj['remote_cmd'] == 'manual':
            device_id=obj['ZoneName']
            for erackid, h_eRack in self.eRacks.items():#2021/12/8
                if h_eRack.device_id == device_id:
                    h_eRack.manual()
                    break

        if obj['remote_cmd'] == 'auto':
            device_id=obj['ZoneName']
            for erackid, h_eRack in self.eRacks.items():#2021/12/8
                if h_eRack.device_id == device_id:
                    h_eRack.auto()
                    break

    def add_listener(self, obj):
        for rack_id, h in self.eRacks.items():
            h.add_listener(obj)

    def trigger(self, portID, event): #i.e. notify, or command
        res, rack_id, port_no=tools.rackport_format_parse(portID)
        if res:
            #h_eRack=self.eRacks[rack_id] #chocp fix 10/30
            h_eRack=self.eRacks.get(rack_id, 0)
            if h_eRack:
                h_eRack.on_notify(event, portID)

    def attach(settings):
        pass

    def dettach():
        pass


    def run(self):
        while(True):
            for rack_id, h in self.eRacks.items():
                if h.heart_beat > 0 and time.time() - h.heart_beat > 60:
                    h.heart_beat=0
                    self.tsclogger.info('{}'.format("<<<  ErackAdapter {} is dead. >>>".format(rack_id)))
                    
                    
                    if not h.is_alive():
                        self.tsclogger.info('{}'.format("<<<  Attempting to restart ErackAdapter {} >>>".format(rack_id)))
                        try:
                            
                            h.force_reconnect()
                            
                            if not h.is_alive():
                                h.thread_stop = False
                                h.start()
                                self.tsclogger.info('{}'.format("<<<  ErackAdapter {} restarted successfully >>>".format(rack_id)))
                        except Exception as e:
                            self.tsclogger.error('{}'.format("<<<  Failed to restart ErackAdapter {}: {} >>>".format(rack_id, str(e))))

            obj=None
            try:
                obj=self.api_queue.get(timeout=1)
            except:
                continue
            #print('get Erack obj')
            #print(obj['config'])
            eRacks_tmp={}
            erack_groups_tmp={}
            map_zones_tmp={}
            port_areas_tmp={}
            port_areas_revert_tmp={}  #chocp 2022/4/12

            def update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h):
                print('setting:', setting)

                if erack_groups_tmp.get(group_id):
                    erack_groups_tmp[setting['groupID']].append(h)
                else:
                    erack_groups_tmp[setting['groupID']]=[h]

                if map_zones_tmp.get(zone_id): #chocp 2022/4/14 need check zone_id not declare
                    map_zones_tmp[zone_id].append(h)
                else:
                    map_zones_tmp[zone_id]=[h]

                sector=json.loads(setting.get('sector', '{}'))
                print('sector: ', sector)
                if sector:
                    for area_id, slots_string in sector.items():
                        #print(area_id, slots_string)
                        for slot_no in slots_string.split(','):
                            print(area_id, slot_no)
                            if port_areas_tmp.get(area_id):
                                port_areas_tmp[area_id].append({'h':h, 'rack_id': h.device_id, 'slot_no':int(slot_no)})
                            else:
                                port_areas_tmp[area_id]=[{'h':h, 'rack_id': h.device_id, 'slot_no':int(slot_no)}]

                            #for LG, GPM
                            res, port_id=tools.print_rackport_format(h.device_id, int(slot_no), h.rows, h.columns)
                            if res: #port_id valid
                                port_areas_revert_tmp[port_id]=area_id


            self.tsclogger.info('{} '.format('<<< get ErackSettings >>>'))
            try:
                for idx, setting in enumerate(obj['config']):
                    print('*******************************')
                    print('get Erack setting:', idx, setting)
                    print('*******************************')

                    rack_id=setting['eRackID']
                    group_id=setting['groupID']
                    zone_id=setting['zone']
                    #h=self.eRacks.get(rack_id, 0)
                    try:
                        h=self.eRacks.pop(rack_id)
                    except:
                        h=0

                    if rack_id in eRacks_tmp: # zhangpeng 2025-02-13 # Prevent duplicate creation of threads with the same vehicle id
                        continue

                    if h and h.is_alive():
                        if h.ip == setting['ip'] and h.port == setting['port'] and h.idx == setting['idx'] and h.type == setting['type']: #chocp add 2021/12/21
                            if setting['enable'] == 'yes':
                                if not h.is_alive():
                                    h.start()

                                print("<<< continue: {} >>>".format(rack_id))
                                h.update_params(setting)
                                update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)
                                eRacks_tmp[rack_id]=h
                                continue
                            else:
                                if not h.is_alive():
                                    print("<<< continue: {} >>>".format(rack_id))
                                    h.update_params(setting)
                                    update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)
                                    eRacks_tmp[rack_id]=h
                                    continue

                                print("<<< stop: {} >>>".format(rack_id))
                                h.thread_stop=True
                        else:
                            print("<<< stop: {} >>>".format(rack_id))
                            h.thread_stop=True
                        #time.sleep(5)

                    if setting['enable'] == 'yes': # Mike: 2022/02/17
                        secsgem_e88_h=self.secsgem_e88_h

                        if setting.get('model') == 'OtherShelf1':
                            h=ICWiserErackAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                        elif setting.get('model') == 'OtherShelf2':
                            h=MFErackAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                        elif setting.get('model') == 'DumpyPort':
                            h=DummyPortAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                        elif setting.get('model') == 'TurnTable':
                            h=TurnTableAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                        elif setting.get('model') == 'CDAErack': #Sean for KumamotoTPB
                            h=CDAErackAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                        else:
                            if global_variables.erack_version == 'v3':
                                h=GpmErackAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)
                            else:
                                h=GyroErackAdapter(secsgem_e88_h, setting, self.Transfers, self.Carriers, self.Zones)

                        print("<<< new: {} >>>".format(rack_id))
                        eRacks_tmp[rack_id]=h
                        h.name=str(rack_id)
                        h.setDaemon(True)
                        h.start()
                        update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)


                #need clear ....
                for erackid, h in self.eRacks.items():#2021/12/8
                    h.thread_stop=True

                self.eRacks=eRacks_tmp
                self.map_zones=map_zones_tmp
                self.erack_groups=erack_groups_tmp #fix chocp 2021/112/7
                self.port_areas=port_areas_tmp
                self.port_areas_revert=port_areas_revert_tmp

                print(self.eRacks)
                print(self.map_zones)
                print('=================')
                print(self.port_areas)
                print('=================')

            except:
                self.tsclogger.error('{} {} '.format('Erack mgr error', traceback.format_exc()))




if __name__ == '__main__':

    parser=argparse.ArgumentParser()
    parser.add_argument('-url',  help='device ip')
    parser.add_argument('-port',  help='device port')
    parser.add_argument('-s',  help='use vehicle simulator or not')
    parser.add_argument('-size',  help='zone size')
    parser.add_argument('-type',  help='zone type, 1 for erack, 2 for dummy loadport')
    parser.add_argument('-name',  help='zone name')
    args=parser.parse_args()
    ip=''
    try:
        ip=args.url
        port=int(getattr(args, 'port', 5600))
        zonesize=int(getattr(args, 'size', 12))
        zonetype=int(getattr(args, 'type', 1))
        zonename=getattr(args, 'name', 'E001')
    except Exception as e:
        print(e)

    force_simulate=False
    try:
        force_simulate= True if args.s else False
    except:
        pass

    #self.secsgem_e82_h=E82.E82Equipment('', 6000, False, 0, initial_control_state='ONLINE')
    logger=logging.getLogger("E88_hsms_communication")
    logger.setLevel(logging.DEBUG)
    filename=os.path.join("log", "Gyro_E88.log")
    fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_E88.log"), when='midnight', interval=1, backupCount=30)
    fileHandler.setFormatter(logging.Formatter("%(asctime)s %(name)s.%(funcName)s: %(message)s"))
    logger.addHandler(fileHandler)

    SecsGemE88('', 5001, False, 0) #6000

    Erack.h=ErackMgr()
    Erack.h.setDaemon(True)
    Erack.h.start()

    obj={}
    obj['cmd']='start'
    config={}
    config['idx']=0
    config['eRackID']=zonename
    config['mac']='AABBCCDDEE01'
    config['zone']='Zone1'
    config['func']={}
    config['location']='ZZ'
    config['ip']=ip # 192.168.0.236
    config['port']=port # 5000
    config['enable']='yes'
    config['zonesize']=zonesize
    config['zonetype']=zonetype
    obj['config']=[config]

    Erack.h.api_queue.put(obj)

    print('\n*********************************')
    print('** controller start processing **')
    print('*********************************\n')

    #generate_routes()

    time.sleep(2)

    while True:
        try:
            res=raw_input()
        except:
            time.sleep(1)

    #self.secsgem_e82_h.disable()

