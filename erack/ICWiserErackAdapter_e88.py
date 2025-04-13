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

import global_variables
from global_variables import Vehicle
from global_variables import output
from global_variables import remotecmd_queue
import tools

import json
import copy
from pprint import pformat


from semi.SecsHostMgr import E88_Host
import semi.e88_equipment as E88

from semi.E88_functions import Extend_secsStreamsFunctions

import queue
import alarms
import secsgem


class SecsHost(secsgem.GemHostHandler):
    def __init__(self, parent_obj, address, port, active, session_id, name, mdln='TEST1.0', T3=45, T5=10, T6=5, T7=10, T8=5, custom_connection_handler=None):
 
        secsgem.GemHostHandler.__init__(self, address, port, active, session_id, name, custom_connection_handler)

        log_name='hsms_communication_erack_{}'.format(name)
        filename=os.path.join("log", "{}.log".format(log_name))

        commLogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30)
        commLogFileHandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
        commLogFileHandler.setLevel(logging.DEBUG)

        self.communicationLogger=logging.getLogger(log_name)
        for lh in self.communicationLogger.handlers[:]:
            self.communicationLogger.removeHandler(lh)
            lh.close()
        self.communicationLogger.addHandler(commLogFileHandler)
        self.communicationLogger.setLevel(logging.DEBUG)


        self.parent_obj=parent_obj
        self.connection.T3=T3
        self.connection.T5=T5
        self.connection.T6=T6
        self.connection.T7=T7
        self.connection.T8=T8

        for stream in Extend_secsStreamsFunctions:
            if stream not in self.secsStreamsFunctions:
                self.secsStreamsFunctions[stream]={}
            for function in Extend_secsStreamsFunctions[stream]:
                self.secsStreamsFunctions[stream][function]=Extend_secsStreamsFunctions[stream][function]

        self.CarrierID=''
        self.Callback=None
        self.EventList={
        }
        self.AlarmList={
        }

    def send_are_you_there(self):
        # self.send_prime_message(self.stream_function(1, 1)())
        try:
            message=self.secs_decode(self.send_and_waitfor_response(self.stream_function(1, 1)()))
            self.mdln=message[0].get()
            self.softrev=message[1].get()
            pos=message[2].get()
            self.parent_obj.msg_queue.put({'event':'AreYouThereResponse', 'data':pos})
        except:
            pass

    def get_cst_id(self):
        try:
            message=self.secs_decode(self.send_and_waitfor_response(self.stream_function(1, 5)()))
            cst_id=[]
            for cst in message:
                cst_id.append(cst.get())
            self.parent_obj.msg_queue.put({'event':'AllCassetteID', 'data':cst_id})
        except:
            pass

    def query_all_slots_status(self):
        try:
            message=self.secs_decode(self.send_and_waitfor_response(self.stream_function(1, 1)()))
         
            self.mdln=message[0].get()
            self.softrev=message[1].get()
            slots_str=message[2].get()

            message=self.secs_decode(self.send_and_waitfor_response(self.stream_function(1, 5)()))
           
            cst_id_list=[]
            for cst in message:
                cst_id_list.append(cst.get().strip())

            self.parent_obj.msg_queue.put({'event':'AllSlotStatus', 'data':{'slots_str':slots_str, 'cst_id_list':cst_id_list}})
        except:
            traceback.print_exc()
            pass

    def send_display_msg(self, slotID, msg):
        try:
            packet=self.stream_function(18, 21)({'SLOTID':slotID, 'SLOTDATA':msg})
            message=self.secs_decode(self.send_and_waitfor_response(packet))
            slotID=message[0].get()
            slotAck=message[1].get()

            self.parent_obj.msg_queue.put({'event':'DisplayResponse', 'data':slotAck})
        except:
            pass

    def _on_s18f71(self, handler, packet):
        try:
            message=self.secs_decode(packet)
            # print(message)
            # print(message[0].get(), message[1].get(), message[2].get(), message[3].get())
            slotID=message[0].get()
            slotStatus=message[1].get()
            slotPreserved=message[2].get()
            slotMsg=message[3].get()
            self.parent_obj.msg_queue.put({'event':'CarrierMoveIn', 'data':{'slotID':slotID, 'status':slotStatus, 'cassetteID':slotMsg[1]}})
        except:
            pass

    def _on_s18f75(self, handler, packet):
        try:
            message=self.secs_decode(packet)
            # print(message)
            # print(message[0].get(), message[1].get(), message[2].get(), message[3].get())
            slotID=message[0].get()
            slotStatus=message[1].get()
            slotPreserved=message[2].get()
            slotMsg=message[3].get()
            self.parent_obj.msg_queue.put({'event':'CarrierMoveOut', 'data':{'slotID':slotID}})
        except:
            pass

    def _on_state_communicating(self, _):
        secsgem.GemHostHandler._on_state_communicating(self, _)
        self.parent_obj.msg_queue.put({'event':'Online', 'data':{}})

    def on_connection_closed(self, connection):
        if self.communicationState.current == 'COMMUNICATING':
            secsgem.GemHostHandler.on_connection_closed(self, connection)
            self.parent_obj.msg_queue.put({'event':'Offline', 'data':{}})

class ICWiserErackAdapter(threading.Thread):
    def update_params(self, setting):
        self.idx=setting['idx']
        self.device_id=setting['eRackID']
        self.mac=setting['mac']
        self.groupID=setting['groupID'] if setting['groupID'] else setting['eRackID'] #9/26
        self.zone=setting['zone']
        self.link_zone=setting.get('link', '') #v8.24F for SJ
        if not self.link_zone: self.link_zone=self.zone #v8.24F for SJ
        
        self.ip=setting['ip']
        self.port=int(setting.get('port', 5000))

        try:
            self.func=json.loads(setting.get('func', {})) #chocp 2023/9/11
        except:
            self.func={}

        self.autodispatch=setting.get('AutoDispatch', False)
        self.waterlevelhigh=int(setting.get('WaterLevelHigh', 80))
        self.waterlevellow=int(setting.get('WaterLevelLow', 20))
        self.returnto=setting.get('ReturnTo', 'None' )
        self.batchsize=int(setting.get('BatchSize', 4)) 

        self.loc=setting.get('location', '')
        self.type=setting.get('type', '3x4')
        self.zonesize=int(setting.get('zonesize', 12))

        res=re.match(r'(\d+)x(\d+)', self.type)  #fix2
        self.rows=int(res.group(1))
        self.columns=int(res.group(2))
        self.slot_num=self.rows*self.columns

        def format_parse(validSlotType, slot_num): #2023/12/26 chocp
            config={}
            if validSlotType:
                slot_type_list=validSlotType.split(',')
                for desc in slot_type_list:
                    key=desc.split(':')[0].strip()
                    config[key]=[]
                    try:
                        value=desc.split(':')[1]
                        for port in value.split('|'):
                            config[key].append(int(port.strip()))
                    except:
                        for port_no in range(1, slot_num+1): #
                            config[key].append(port_no) 
                        pass
            return config #{'8S':[1,2,3], '12S':[7,8,15], '12C':[1,2,3,4,5,6,7,8,9,10,11,12]}

        self.validSlotType=format_parse(setting.get('validCarrierType', ''), self.slot_num) 




    def wiser_idx_to_coordinate(self, idx): #ex: 5=>
        idx=int(idx)
        a=(idx//self.columns)+1
        b=(idx%self.columns)+1
        return '{}{}'.format(a, b)

    def coordinate_to_wiser_idx(self, loc): #31
        a=int(loc[0])
        b=int(loc[1])
        return (a-1)*self.columns+(b-1)

    def port_no_to_coordinate(self, port_no):
        a=self.rows-(port_no/self.columns)
        b=port_no%self.columns
        if b == 0:
            b=self.columns
            a=a+1
        return str(a)+str(b) #31

    def coordinate_to_port_no(self, loc): #ex: '31' =>1
        a=int(loc[0])
        b=int(loc[1])
        return (self.rows-a)*self.columns+b

    def port_no_mapping_wiser_idx(self, port_no):
        loc=self.port_no_to_coordinate(port_no)
        slot_idx=self.coordinate_to_wiser_idx(loc)
        return slot_idx

    def wiser_idx_mapping_port_no(self, slot_idx):
        loc=self.wiser_idx_to_coordinate(slot_idx)
        port_no=self.coordinate_to_port_no(loc)
        return port_no

    def __init__(self, secsgem_e88_h, setting, Transfers, Carriers, Zones):
        self.model='Shelf'
        self.secsgem_e88_h=secsgem_e88_h
        self.E88_Transfers=Transfers
        self.E88_Carriers=Carriers
        self.E88_Zones=Zones

        self.zonetype=1
        self.zone_list={}
        self.available=0 #9/26 chocp

        self.update_params(setting)
        print(self.device_id, self.rows, self.columns, self.slot_num)

        self.last_status='None'
        self.last_erack_status='None'

        self.connected=False

        self.erack_status='DOWN'

        self.read_carriers=[]
        self.last_carriers=[]
        self.carriers=[]
        self.lots=[]

        self.sendby=[]

        for i in range(self.rows):
            for j in range(self.columns):
                self.sendby.append(0)
                self.read_carriers.append({'carrierID':''})
                self.lots.append({'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''})
                self.last_carriers.append({'checked':1, 'box_color':'', 'area_id':'', 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0, 'transfering':False})
                self.carriers.append({'checked':1, 'box_color':'', 'area_id':'', 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0, 'transfering':False})

        try:
            sector=json.loads(setting.get('sector', '{}'))
            for area_id, slots_string in sector.items():
                #print(area_id, slots_string)
                for slot_no_str in slots_string.split(','):
                    slot_no=int(slot_no_str)
                    self.carriers[slot_no-1]['area_id']=area_id
                    self.carriers[slot_no-1]['box_color']=global_variables.color_sectors.get(area_id)
                    self.last_carriers[slot_no-1]['area_id']=area_id
                    self.last_carriers[slot_no-1]['box_color']=global_variables.color_sectors.get(area_id)
        except:
            traceback.print_exc()
            pass

        
        self.shelf_h=SecsHost(self, self.ip, self.port, True, 0, self.device_id)
        #self.shelf_h.initial()

        self.thread_stop=False
        self.heart_beat=0
        threading.Thread.__init__(self)
        self.lock=threading.Lock()

    def zone_capacity_change(self, zonename, change): # Mike: 2022/06/14
        '''if change == 'Inc':
            self.E88_Zones.Data[zonename].capacity_increase()
        elif change == 'Dec':
            self.E88_Zones.Data[zonename].capacity_decrease()
        elif isinstance(change, int):
            self.E88_Zones.Data[zonename].zone_capacity_change(change)'''
        pass

    def notify_panel(self):
        n=0
        mCarriers=[]
        for idx, carrier in enumerate(self.carriers):
            mCarriers.append(copy.deepcopy(carrier))
            mCarriers[idx]['lot']=self.lots[idx]
            if carrier['status'] == 'up' and carrier['carrierID'] == '': #9/26 chocp
                if not self.lots[idx]['booked']:
                    n+=1

        self.available=n
        output('eRackStatusUpdate', {
                'idx':self.idx,
                'DeviceID':self.device_id,
                'MAC':self.mac,
                'IP':self.ip,
                'Status':self.erack_status,
                'carriers':mCarriers,
                'SlotNum':self.slot_num,
                'StockNum':0 if self.erack_status == 'DOWN' else (self.slot_num-self.available)
                })

    def set_machine_info(self, port_no, dest, vehicle_id=''): #chocp add 9/24
        print('set_machine_info', port_no, dest)
        if vehicle_id:
            self.lots[port_no-1]['machine']=dest + ' by {}'.format(vehicle_id) 
        else:
            self.lots[port_no-1]['machine']=dest
        self.notify_panel()

    def set_booked_flag(self, port_no, flag=False, vehicle_id='', source=''): #2022/3/18
        print('set_booked_flag', port_no, flag)
        if flag:
            self.lots[port_no-1]['booked']=1
            self.lots[port_no-1]['booked_for']=vehicle_id
            self.lots[port_no-1]['desc']=vehicle_id + ' from {}'.format(source) if source else ''
        else:
            self.lots[port_no-1]['booked']=0
            self.lots[port_no-1]['booked_for']=''
            self.lots[port_no-1]['desc']=''
        self.notify_panel()

    def on_notify(self, event, data):
        #print('eRack {} get {}, data {}'.format(self.device_id, event, data))
        if event == 'acquire_start_evt' or event == 'deposit_start_evt':
            #self.sendby[0]=1
            pass
        elif event == 'acquire_complete_evt' or event == 'deposit_complete_evt':
            #self.sendby[0]=1
            pass

    def eRackStatusUpdate(self): #move to erackmgr?
        carrier_change=False
        states=[]
        for idx, carrier in enumerate(self.carriers):
            sendby=0
            rack_id=self.device_id
            port_no=idx+1
            zonename=carrier['area_id'] if carrier['area_id'] else self.groupID if (self.groupID and global_variables.RackNaming == 2) else self.device_id
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            if not res:
                raise alarms.SCSyntaxWarning(rack_id, handler=self.secsgem_e88_h)

            h_vehicle=None
            if Vehicle.h != 0:
                for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                    if h_vehicle.AgvState in ['Acquiring', 'Depositing'] and h_vehicle.action_in_run['target'] == CarrierLoc: #have bug
                        sendby=1
                        break
                else:
                    h_vehicle=None
                    
            if self.erack_status == 'DOWN':
                carrier['status']='down'
                carrier['carrierID']=''
                carrier['checked']=0

            if carrier['status'] == 'down':
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=3
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for rack update
                state={'SlotID': idx+1, 'Status':'Fail'}
                states.append(state)
                #for port update
                if self.last_carriers[idx]!=carrier:
                    carrier_change=True
                    # E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby})
                    FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                    self.read_carriers[idx]['carrierID']=FAILUREID
                    self.E88_Carriers.Mapping[CarrierLoc]=self.read_carriers[idx]['carrierID']
                    self.E88_Carriers.add(FAILUREID)
                    datasets={}
                    datasets['CarrierID']=FAILUREID
                    datasets['CarrierLoc']=CarrierLoc
                    datasets['CarrierIDRead']=carrier['carrierID']
                    datasets['CarrierZoneName']=zonename
                    datasets['CarrierDeviceName']=self.device_id
                    datasets['HandoffType']=sendby+1
                    datasets['PortType']=self.type # Mike: 2022/04/15
                    self.E88_Carriers.set(FAILUREID, datasets)
                    self.E88_Carriers.Data[FAILUREID].id_read(FAILUREID, 1)
                    self.E88_Carriers.Data[FAILUREID].State.wait_in()
                    self.zone_capacity_change(zonename, 'Dec')
                    self.E88_Carriers.Data[FAILUREID].State.transfer()
                    self.E88_Carriers.Data[FAILUREID].State.wait_out()

                    if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                        datasets={}
                        datasets['CarrierLoc']=CarrierLoc
                        self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                        self.alarm_table[20002].append(CarrierLoc)

            elif carrier['carrierID'] == '':
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=1
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for rack update
                state={'SlotID': idx+1, 'Status':'None'}
                states.append(state)
                #for port update
                if self.last_carriers[idx]!=carrier:
                    carrier_change=True
                    # E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby})
                    if CarrierLoc in self.E88_Carriers.Mapping:
                        print(CarrierLoc, self.E88_Carriers.Mapping[CarrierLoc])
                        if self.E88_Carriers.Mapping[CarrierLoc] in self.E88_Carriers.Data:
                            datasets={}
                            datasets['HandoffType']=sendby+1
                            self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                            if self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].CarrierState == 3:
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.remove()
                            else:
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.kill_carrier()
                            self.E88_Carriers.delete(self.E88_Carriers.Mapping[CarrierLoc])
                            self.zone_capacity_change(zonename, 'Inc')
                            if CarrierLoc in self.E88_Carriers.Mapping:
                                del self.E88_Carriers.Mapping[CarrierLoc]
                            self.read_carriers[idx]['carrierID']=''

                if CarrierLoc in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20002, False, datasets)
                    self.alarm_table[20002].remove(CarrierLoc)

            else:
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=2
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for rack update
                state={'SlotID': idx+1, 'Status':carrier['carrierID']}
                states.append(state)

                if self.last_carriers[idx]!=carrier:
                    #print('diff', self.last_carriers[idx], carrier)
                    carrier_change=True
                    if carrier['carrierID'] not in self.E88_Carriers.Data:
                        if CarrierLoc not in self.E88_Carriers.Mapping:
                            self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                            self.read_carriers[idx]['carrierID']=carrier['carrierID']
                            self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                            datasets={}
                            datasets['CarrierID']=self.E88_Carriers.Mapping[CarrierLoc]
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 0)
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                            self.zone_capacity_change(zonename, 'Dec')
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.transfer()
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.store()
                        else:
                            old_carrier_id=self.E88_Carriers.Mapping[CarrierLoc]
                            self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                            self.read_carriers[idx]['carrierID']=carrier['carrierID']
                            datasets={}
                            datasets['CarrierID']=self.E88_Carriers.Mapping[CarrierLoc]
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.mod(old_carrier_id, self.E88_Carriers.Mapping[CarrierLoc])
                            self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                        if CarrierLoc in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                            datasets={}
                            datasets['CarrierLoc']=CarrierLoc
                            self.E88_Zones.Data[zonename].zone_alarm_set(20002, False, datasets)
                            self.alarm_table[20002].remove(CarrierLoc)
                    else:
                        if CarrierLoc not in self.E88_Carriers.Mapping:
                            tmp=self.E88_Carriers.Data[carrier['carrierID']]
                            if self.E88_Zones.Data[tmp.CarrierZoneName].ZoneUnitState[tmp.CarrierDeviceName] == 1: # Duplicate
                                FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                                self.read_carriers[idx]['carrierID']=FAILUREID
                                self.E88_Carriers.Mapping[CarrierLoc]=FAILUREID
                                self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                                datasets={}
                                datasets['CarrierID']=carrier['carrierID']
                                datasets['CarrierLoc']=CarrierLoc
                                datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                                datasets['CarrierZoneName']=zonename
                                datasets['CarrierDeviceName']=self.device_id
                                datasets['HandoffType']=sendby+1
                                datasets['PortType']=self.type # Mike: 2022/04/15
                                self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 2)
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                                self.zone_capacity_change(zonename, 'Dec')
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.transfer()
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_out()
                                if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                                    datasets={}
                                    datasets['CarrierLoc']=CarrierLoc
                                    self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                                    self.alarm_table[20002].append(CarrierLoc)
                            else:
                                FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                                old_carrier_loc=self.E88_Carriers.Data[carrier['carrierID']].CarrierLoc
                                self.E88_Carriers.Mapping[old_carrier_loc]=FAILUREID
                                self.E88_Carriers.mod(carrier['carrierID'], FAILUREID)
                                datasets={}
                                datasets['CarrierID']=FAILUREID
                                self.E88_Carriers.set(FAILUREID, datasets)
                                self.E88_Carriers.Data[FAILUREID].State.transfer()
                                self.E88_Carriers.Data[FAILUREID].State.wait_out()

                                self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                                self.read_carriers[idx]['carrierID']=carrier['carrierID']
                                self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                                datasets={}
                                datasets['CarrierID']=self.E88_Carriers.Mapping[CarrierLoc]
                                datasets['CarrierLoc']=CarrierLoc
                                datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                                datasets['CarrierZoneName']=zonename
                                datasets['CarrierDeviceName']=self.device_id
                                datasets['HandoffType']=sendby+1
                                datasets['PortType']=self.type # Mike: 2022/04/15
                                self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 0)
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                                self.zone_capacity_change(zonename, 'Dec')
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.transfer()
                                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.store()
                            pass
                        else: # Duplicate
                            old_carrier_id=self.E88_Carriers.Mapping[CarrierLoc]
                            FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                            self.read_carriers[idx]['carrierID']=FAILUREID
                            self.E88_Carriers.Mapping[CarrierLoc]=FAILUREID
                            datasets={}
                            datasets['CarrierID']=carrier['carrierID']
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.mod(old_carrier_id, self.E88_Carriers.Mapping[CarrierLoc])
                            self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                            if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                                datasets={}
                                datasets['CarrierLoc']=CarrierLoc
                                self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                                self.alarm_table[20002].append(CarrierLoc)

        if carrier_change:
            self.last_carriers=copy.deepcopy(self.carriers)
            self.notify_panel()  

        if self.last_erack_status!=self.erack_status:
            self.last_erack_status=self.erack_status
            self.notify_panel()  

    def initialize_e88_data(self):
        self.alarm_table={20002:[], 20003:[], 20004:0, 20005:[]}
        for i in range(self.rows*self.columns):
            rack_id=self.device_id
            port_no=i+1
            area_id=self.carriers[i]['area_id']
            zonename=area_id if area_id else self.groupID if (self.groupID and global_variables.RackNaming == 2) else self.device_id

            print(rack_id, port_no, self.rows, self.columns)
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)

            print('initialize_e88_data', i, res, CarrierLoc)

            self.E88_Zones.ZoneMap[CarrierLoc]=self.E88_Zones
            if zonename not in self.zone_list:
                self.zone_list[zonename]={}
            self.zone_list[zonename][CarrierLoc]={'StockerUnitID':CarrierLoc, 'StockerUnitState':0, 'CarrierID':''}

        for zonename in self.zone_list:

            if zonename in self.E88_Zones.Data:
                datasets={}
                datasets['ZoneSize']=self.E88_Zones.Data[zonename].ZoneSize + len(self.zone_list[zonename])
                datasets['ZoneCapacity']=self.E88_Zones.Data[zonename].ZoneCapacity + len(self.zone_list[zonename])
                self.E88_Zones.Data[zonename].StockerUnit.update(self.zone_list[zonename])
                self.E88_Zones.Data[zonename].ZoneUnitState[self.device_id]=1
            else:
                self.E88_Zones.add(zonename)
                datasets={}
                datasets['ZoneSize']=len(self.zone_list[zonename])
                datasets['ZoneCapacity']=len(self.zone_list[zonename])
                datasets['ZoneType']=self.zonetype # 1: eRack 2: dummy loadport
                datasets['StockerUnit']=dict(self.zone_list[zonename])
                datasets['ZoneUnitState']={self.device_id:1}
            self.E88_Zones.set(zonename, datasets)
            print("debug setting:", self.device_id, zonename, self.E88_Zones.Data[zonename].ZoneSize, self.E88_Zones.Data[zonename].ZoneCapacity, self.zone_list[zonename])

    def finalize_e88_data(self):
        for idx, carrier in enumerate(self.carriers): # Mike: 2021/12/01
            rack_id=self.device_id
            port_no=idx+1
            CarrierLoc=''
            zonename=carrier['area_id'] if carrier['area_id'] else self.groupID if (self.groupID and global_variables.RackNaming == 2) else self.device_id
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            if not res:
                alarms.SCSyntaxWarning(rack_id, handler=self.secsgem_e88_h)

            self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=1
            self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=''

            if CarrierLoc in self.E88_Carriers.Mapping:
                if self.E88_Carriers.Mapping[CarrierLoc] in self.E88_Carriers.Data:
                    if self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].CarrierState == 3:
                        self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.remove()
                    else:
                        self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.kill_carrier()
                    self.E88_Carriers.delete(self.E88_Carriers.Mapping[CarrierLoc])
                    self.zone_capacity_change(zonename, 'Inc')
                    if CarrierLoc in self.E88_Carriers.Mapping:
                        del self.E88_Carriers.Mapping[CarrierLoc]
                    self.read_carriers[idx]['carrierID']=''

        for zonename in self.zone_list:
            datasets={}
            datasets['ZoneSize']=self.E88_Zones.Data[zonename].ZoneSize - len(self.zone_list[zonename])
            datasets['ZoneCapacity']=self.E88_Zones.Data[zonename].ZoneCapacity - len(self.zone_list[zonename])
            self.zone_capacity_change(zonename, datasets['ZoneCapacity'])
            if datasets['ZoneSize'] > 0:
                self.E88_Zones.set(zonename, datasets)
                for CarrierLoc in self.zone_list[zonename]:
                    del self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]
            else:
                self.E88_Zones.delete(zonename)
            print(zonename, datasets['ZoneSize'], datasets['ZoneCapacity'], self.zone_list[zonename])

        print('\n<end eRack thread:{}>\n'.format(self.device_id))

    #for thread
    def run(self):
        self.msg_queue=queue.Queue()
        #init for E88 data
        self.initialize_e88_data()
        self.shelf_h.enable()

        self.eRackStatusUpdate()
        
        print('\n<start eRack thread:{}>\n'.format(self.device_id))
        
        self.connected=False

        self.msg_queue.put({'event':'Online', 'data':{}})
        
        timeout_count=10
        while not self.thread_stop:
            self.heart_beat=time.time()
            msg=''
            try:
                msg=self.msg_queue.get(timeout=1)
                timeout_count=0
            except:
                timeout_count+=1
                pass

            if msg:
                if msg['event'] == 'AreYouThereResponse':
                    slots_str=msg.get('data')
                    print('AreYouThereResponse', slots_str)
                    pass

                elif msg['event'] == 'AllSlotStatus':
                    if self.connected:
                        self.erack_status='UP'
             
                        slots_str=msg.get('data', {}).get('slots_str', '')
                        cst_id_list=msg.get('data', {}).get('cst_id_list', [])
                        try:
                            for port_no in range(1, self.slot_num+1):
                                idx=self.port_no_mapping_wiser_idx(port_no)
                                if slots_str[idx] == 'R': #ID read
                                    self.carriers[port_no-1]['status']='up'
                                    self.carriers[port_no-1]['carrierID']=cst_id_list[idx][:7]

                                elif slots_str[idx] == 'F': #empty
                                    self.carriers[port_no-1]['status']='up'
                                    self.carriers[port_no-1]['carrierID']=''

                                    self.lots[port_no-1]['booked']=0
                                    self.lots[port_no-1]['booked_for']=''
                                    self.lots[port_no-1]['desc']=''
                                    self.lots[port_no-1]['machine']=''

                                else: #Read Fail
                                    self.carriers[port_no-1]['status']='down'
                                    self.carriers[port_no-1]['carrierID']=''
                        except:
                            traceback.print_exc()
                            pass

                        self.eRackStatusUpdate()

                elif msg['event'] == 'CarrierMoveIn':
                    slotID=msg.get('data', {}).get('slotID')
                    slot_idx=int(slotID, 16)
                    port_no=self.wiser_idx_mapping_port_no(slot_idx)
                    slotStatus=msg.get('data', {}).get('status')
                    if slotStatus == 'NO':
                        self.carriers[port_no-1]['status']='up'
                        self.carriers[port_no-1]['carrierID']=msg.get('data', {}).get('cassetteID')[:7]
                    else:
                        self.carriers[port_no-1]['status']='down'
                        self.carriers[port_no-1]['carrierID']=''

                    self.eRackStatusUpdate()

                elif msg['event'] == 'CarrierMoveOut':
                    slotID=msg.get('data', {}).get('slotID')
                    slot_idx=int(slotID, 16)
                    port_no=self.wiser_idx_mapping_port_no(slot_idx)
                    self.carriers[port_no-1]['status']='up'
                    self.carriers[port_no-1]['carrierID']=''

                    self.lots[port_no-1]['booked']=0
                    self.lots[port_no-1]['booked_for']=''
                    self.lots[port_no-1]['desc']=''
                    self.lots[port_no-1]['machine']=''

                    self.eRackStatusUpdate()

                elif msg['event'] == 'Online':
                    print('Online', self.shelf_h.communicationState.current)
                    self.connected=True

                    if self.alarm_table[20004]:
                        alarms.ErackOffLineWarning(self.device_id, handler=self.secsgem_e88_h)
                        self.secsgem_e88_h.clear_alarm(20004)
                        self.alarm_table[20004]=0
                        dataset={'DeviceID':self.device_id}
                        E88.report_event(self.secsgem_e88_h, E88.DeviceOnline, dataset)

                    for zonename in self.zone_list:
                        self.E88_Zones.Data[zonename].ZoneUnitState[self.device_id]=1
                        self.E88_Zones.Data[zonename].ZoneState=1

                    self.eRackStatusUpdate()
                
                elif msg['event'] == 'Offline':
                    print('Offline', self.shelf_h.communicationState.current)
                    self.connected=False
                    self.erack_status='DOWN'

                    for port_no in range(1, self.slot_num+1):
                        self.carriers[port_no-1]['status']='down'
                                    
                    if not self.alarm_table[20004]:
                        alarms.ErackOffLineWarning(self.device_id, handler=self.secsgem_e88_h)
                        self.alarm_table[20004]=1
                        dataset={'DeviceID':self.device_id}
                        E88.report_event(self.secsgem_e88_h, E88.DeviceOffline, dataset)
                        for zonename in self.zone_list:
                            self.E88_Zones.Data[zonename].ZoneUnitState[self.device_id]=2
                            state=0
                            for key, val in self.E88_Zones.Data[zonename].ZoneUnitState.items():
                                state=1 if val == 1 else 2 if val == 2 and state != 1 else 0
                            self.E88_Zones.Data[zonename].ZoneState=state

                    self.eRackStatusUpdate()

                else:
                    print('get unknown event', msg)

            elif self.connected:
                if timeout_count>=10:
                    timeout_count=0
                    #print('query all slot status ...')
                    self.shelf_h.query_all_slots_status()

        else:
            self.finalize_e88_data()



