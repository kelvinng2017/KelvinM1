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
from requests import get as APIget, post as APIpost

import global_variables
from global_variables import Vehicle
from global_variables import output
from global_variables import remotecmd_queue
import tools

import json
import copy
from pprint import pformat


import semi.e88_equipment as E88


import queue
import alarms


class CDAErackAdapter(threading.Thread):
    OPEN_CMD=0
    CLOSE_CMD=1
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
        self.erack_server='http://' + self.ip + ':' + str(self.port)
        self.erack_host='http://127.0.0.1:8787'
        self.erack_url='http://127.0.0.1:8888'

        try:
            self.func=json.loads(setting.get('func', {})) #chocp 2023/9/11
        except:
            self.func={}
      #for auto dispatch
        self.autodispatch=setting.get('AutoDispatch', False) #3/17 chi
        self.waterlevelhigh=int(setting.get('WaterLevelHigh', 80)) #3/17 chi
        self.waterlevellow=int(setting.get('WaterLevelLow', 20)) #3/17 chi
        self.returnto=setting.get('ReturnTo', 'None' ) #3/17 chi
        self.batchsize=int(setting.get('BatchSize', 4)) #3/17 chi

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
        self.water_level_table={} # Mike: 2022/06/14
        if setting.get('alarmEmptyEnable', False):
            self.water_level_table['empty']=alarms.ErackLevelEmptyWarning
        if setting.get('alarmLowEnable', False):
            self.water_level_table['low']=alarms.ErackLevelLowWarning
        if setting.get('alarmHighEnable', False):
            self.water_level_table['high']=alarms.ErackLevelHighWarning
        if setting.get('alarmFullEnable', False):
            self.water_level_table['full']=alarms.ErackLevelFullWarning

    def __init__(self, secsgem_e88_h, setting, Transfers, Carriers, Zones):
        self.model='CDAErack'
        self.secsgem_e88_h=secsgem_e88_h
        self.E88_Transfers=Transfers
        self.E88_Carriers=Carriers
        self.E88_Zones=Zones
        #self.zonestate='auto'
        self.zonetype=1
        self.zone_list={}
        self.available=0 #9/26 chocp
        self.water_level=''
        self.last_water_level=''

        self.update_params(setting)
        print(self.device_id, self.rows, self.columns, self.slot_num)

        
        #self.sock=0
        self.alarm_table={20002:[], 20003:[], 20004:0, 20005:[]}
        #self.associate_queue=collections.deque()
        self.last_erack_status='None'
        self.connected=False
        self.sync=False
        self.syncing_time=0
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
                self.lots.append({'lotID':'', 'stage':'', 'product':'', 'machine':'', 'desc':'',"lpt":"", "qty":"", 'booked':0, 'booked_for':'','recipe':''})
                self.last_carriers.append({'box_color':'', 'area_id':'', 'checked':1, 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0,'direction':'', 'direction_target':'','transfering':False})
                self.carriers.append({'box_color':'', 'area_id':'', 'checked':1, 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0,'direction':'', 'direction_target':'','transfering':False})

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

        
        #self.turn=0 #every 3 echo, update 1 relative lot info
        #self.begin=0
        #self.end=0

        self.thread_stop=False
        self.heart_beat=0
        threading.Thread.__init__(self)
        self.lock=threading.Lock()

    def zone_capacity_change(self, zonename, change): # Mike: 2022/06/14
        if change == 'Inc':
            self.E88_Zones.Data[zonename].capacity_increase()
        elif change == 'Dec':
            self.E88_Zones.Data[zonename].capacity_decrease()
        elif isinstance(change, int):
            self.E88_Zones.Data[zonename].zone_capacity_change(change)
        else:
            pass

        try:
            if zonename in global_variables.SectorSettings:
                size=self.E88_Zones.Data[zonename].ZoneSize
                high=size * global_variables.SectorSettings[zonename]['waterLevelHigh'] / 100
                low=size * global_variables.SectorSettings[zonename]['waterLevelLow'] / 100
                valid=size - self.E88_Zones.Data[zonename].ZoneCapacity
                level=None
                if valid == 0:
                    level='empty'
                elif valid < low:
                    level='low'
                elif valid < high:
                    level='normal'
                elif valid < size:
                    level='high'
                else:
                    level='full'
                # print(zonename, size, high, low, valid, level, self.E88_Zones.Data[zonename].WaterLevel)
                if self.E88_Zones.Data[zonename].WaterLevel != level:
                    if level in global_variables.SectorSettings[zonename]['water_level_table']:
                        global_variables.SectorSettings[zonename]['water_level_table'][level](zonename, handler=self.secsgem_e88_h)
                    self.E88_Zones.set(zonename, {'WaterLevel': level})
        except:
            traceback.print_exc()

    def notify_panel(self):
        try:
            m=0
            n=0
            mCarriers=[]
            for idx, carrier in enumerate(self.carriers):
                mCarriers.append(copy.deepcopy(carrier))
                mCarriers[idx]['lot']=self.lots[idx]
                #print(carrier['status'], carrier['carrierID'], self.lots[idx]['booked'])
                if carrier['status'] == 'up' and carrier['carrierID'] == '': #9/26 chocp
                    m+=1   #chi 2022/09/19 for water level warning without booking 
                    if not self.lots[idx]['booked']:
                        n+=1

            if self.erack_status == 'DOWN':
                self.available=0
            else:
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

            if m == 0:
                self.water_level='full'

            elif m < self.slot_num-self.slot_num*self.waterlevelhigh/100:
                self.water_level='high'

            elif m < self.slot_num-self.slot_num*self.waterlevellow/100:
                self.water_level='medium'

            elif m<self.slot_num:
                self.water_level='low'

            elif m == self.slot_num:
                self.water_level='empty'
            else:
                pass

            if self.last_water_level != self.water_level:
                if self.water_level in self.water_level_table:
                    self.water_level_table[self.water_level](self.device_id, handler=self.secsgem_e88_h)
                self.last_water_level=self.water_level
            pass

        except Exception:
            print('notify_panel_fail')

    def set_machine_info(self, port_no, dest, vehicle_id=''): #chocp add 9/24
        print('set_machine_info', port_no, dest)
        if vehicle_id:
            self.lots[port_no-1]['machine']=dest + ' by {}'.format(vehicle_id) 
        else:
            self.lots[port_no-1]['machine']=dest
        self.notify_panel()

    def set_booked_flag(self, port_no, flag=False, vehicle_id='', source=''): #2022/3/18
        print('set_booked_flag', port_no, flag)
        
        #API
        response=self.temp_update(port_no, booked=flag)
        if response:
            print('Data forwarded to Erack: Successful')
        else:
            print('Failed to forward data')
        
        #dashboard
        if flag:
            self.lots[port_no-1]['booked']=1
            self.lots[port_no-1]['booked_for']=vehicle_id
            self.lots[port_no-1]['desc']=vehicle_id + ' from {}'.format(source) if source else ''
        else:
            self.lots[port_no-1]['booked']=0
            self.lots[port_no-1]['booked_for']=''
            self.lots[port_no-1]['desc']=''
        self.notify_panel()

    # def on_notify(self, event, data):
    #     #print('eRack {} get {}, data {}'.format(self.device_id, event, data))
    #     if event == 'acquire_start_evt' or event == 'deposit_start_evt':
    #         #self.sendby[0]=1
    #         pass
    #     elif event == 'acquire_complete_evt' or event == 'deposit_complete_evt':
    #         #self.sendby[0]=1
    #         pass

    def eRackStatusUpdate(self):
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
                    if carrier['checked'] and CarrierLoc not in self.E88_Carriers.Mapping: #if carrier check by operator,then launch movin event
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
                        if h_vehicle and global_variables.TSCSettings.get('Safety', {}).get('TrBackReqCheck', 'yes').lower() == 'yes':
                            h_vehicle.adapter.robot_check_control(False)

                    if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                        datasets={}
                        datasets['UnitType']='Rack'
                        datasets['UnitID']=self.device_id
                        datasets['Level']='Error'
                        datasets['SubCode']=20002
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
                        ###print(CarrierLoc, self.E88_Carriers.Mapping[CarrierLoc])
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
                    datasets['UnitType']='Rack'
                    datasets['UnitID']=self.device_id
                    datasets['Level']='Error'
                    datasets['SubCode']=20002
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
                    if carrier['checked']: #if carrier check by operator,then launch movin event
                        
                        if h_vehicle and global_variables.TSCSettings.get('Safety', {}).get('TrBackReqCheck', 'yes').lower() == 'yes':
                            h_vehicle.adapter.robot_check_control(True)

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
                                datasets['UnitType']='Rack'
                                datasets['UnitID']=self.device_id
                                datasets['Level']='Error'
                                datasets['SubCode']=20002
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
                                        datasets['UnitType']='Rack'
                                        datasets['UnitID']=self.device_id
                                        datasets['Level']='Error'
                                        datasets['SubCode']=20002
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
                                    datasets['UnitType']='Rack'
                                    datasets['UnitID']=self.device_id
                                    datasets['Level']='Error'
                                    datasets['SubCode']=20002
                                    datasets['CarrierLoc']=CarrierLoc
                                    self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                                    self.alarm_table[20002].append(CarrierLoc)

                if self.last_carriers[idx]['checked']!=carrier['checked']: #only for update panel chocp: 2021/6/22
                    carrier_change=True

        if carrier_change:
            self.last_carriers=copy.deepcopy(self.carriers)
            self.notify_panel()  

        if self.last_erack_status!=self.erack_status:
            self.last_erack_status=self.erack_status
            self.notify_panel()  

    def initialize_e88_data(self):
        for i in range(self.rows*self.columns): # Mike: 2021/09/22
            rack_id=self.device_id
            port_no=i+1
            area_id=self.carriers[i]['area_id']
            zonename=area_id if area_id else self.groupID if (self.groupID and global_variables.RackNaming == 2) else self.device_id

            #print(rack_id, port_no, self.rows, self.columns)
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            # if not res:
            #     raise alarms.SCSyntaxWarning(self.device_id, handler=self.secsgem_e88_h)
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

    def query_all_slots_status(self):
        param={}
        response=APIget(self.erack_url + '/get_all_status').json()
        # from json import dumps as printdict 
        # printdict(response, indent=4)
        # print(response)
        return response['status_list']
        
        
    def check_and_query_wafer_slot(self, carrierID):
        param={
            'waferboxCardCode': carrierID,
            'action': 0,
        }
        response=APIget(self.erack_host + '/waferBox', params=param).json()
        request_code=response.get('code', -1)
        domain=response.get('domain', '')
        msg=response.get('msg')
        transfer_check=False

        if request_code == 0:
            if msg and domain:
                print(msg)
                transfer_check=True

        elif request_code == -1:
            if not msg:
                print('Request Fail', response.get('detail', ''))
            else:
                print('Erack is full', msg)
        else:
            print('Error Status Code {}'.format(request_code))
        
        return transfer_check, domain

    def open_erack_door(self, port_no):
        door_no=self.port_to_door(port_no)
        param={
            'doornum': door_no,
            'action': 0, # 0=open
        }
        response=APIget(self.erack_host + '/doorAction', params=param).json()

        request_code=response.get('code', -1)
        msg=response.get('msg')
        if request_code == 0:
            return True
        else:
            return False

    def close_erack_door(self, port_no):
        door_no=self.port_to_door(port_no)
        param={
            'doornum': door_no,
            'action': 1, # 1=close
        }
        response=APIget(self.erack_host + '/doorAction', params=param).json()

        request_code=response.get('code', -1)
        msg=response.get('msg')
        box_id=response.get('waferboxCardCode', "") #only close door return
        if request_code == 0:
            return True
        else:
            return False

    def check_door_operation(self, action):
        param={
            'action': action, # 0=open 1=close
            'retry_interval': 30, # 30sec default
        }
        response=APIget(self.erack_host + '/door_action_retry', params=param).json()

        request_code=response.get('code')
        msg=response.get('msg')
        if request_code == 0:
            return True
        elif request_code == -1:
            print("Erack Door Error. Door Operation Failure")
        else:
            print("Check Too Many Time. Further Check Required")
        return False


    def port_to_door(self, port_no):
        if global_variables.RackNaming == 53:  # Kumamoto TPB
            door_no=(port_no + 1) / 2
        else:
            door_no=port_no
        
        return door_no
    
    def health_check(self):
        try:
            response=APIget(self.erack_url + '/health_check')
            #print(response.json())
            if response.status_code == 200:
                return True
            else:
                assert False, response.json()
                
        except Exception as e:
            print("Erack API Link Test Fail")
            print(str(e))
            return False

    
    def temp_update(self, port_no, carrier_id='', booked=False, checked=False, status='', lot_id='', machine='', desc=''): #WIP
        param={
            'status': status,
            'content': {
                'lotID': lot_id,
                'Machine': machine,
                'Desc': desc,
            },
            'booked': booked,
            'checked': checked,
            'ant': port_no,
            'carrierID': carrier_id,
            'errorCode': '',
            'led_status': '0000',
        }
        response=APIpost(self.erack_url + '/forward_status', json=param)
        if response.status_code == 200:
            return True #return {"message": "Data forwarded successfully", "response": response.json()}
        else:
            return False #return {"error": "Failed to forward data", "status_code": response.status_code, "response": response.text}
        

    def eRackInfoUpdate(self, info): #from host
        if info['cmd'] == 'associate':
            data=info['data']
            print(data)
            try:
                lot_info=data.split(',') #ASECL use ','
                print(lot_info)
                if len(lot_info) == 1: #chi 2022/09/26
                    self.lots[info['port_idx']]['lotID']='{}'.format(lot_info[0])
                else:
                    self.lots[info['port_idx']]['lotID']='{}({})'.format(lot_info[0], len(lot_info)) if lot_info[0] else ''
                self.lots[info['port_idx']]['desc']=info.get('addition', [''])[0] #chocp 9/2
                print(self.lots[info['port_idx']]['lotID'], self.lots[info['port_idx']]['desc'])
            except:
                traceback.print_exc()
                pass

        elif info['cmd'] == 'infoupdate':
            self.lots[info['port_idx']]['lotID']=''
            self.lots[info['port_idx']]['stage']=''
            self.lots[info['port_idx']]['desc']=''
            self.lots[info['port_idx']]['cust']=''  #chi 2022/10/18 use LowerLevelErack for spil CY
            self.lots[info['port_idx']]['product']=''
            self.lots[info['port_idx']]['lottype']=''
            self.lots[info['port_idx']]['partID']=''
            self.lots[info['port_idx']]['automotive']=''
            self.lots[info['port_idx']]['state']=''
            self.lots[info['port_idx']]['holdcode']=''
            self.lots[info['port_idx']]['turnratio']=0
            self.lots[info['port_idx']]['eotd']=''
            self.lots[info['port_idx']]['holdreas']=''
            self.lots[info['port_idx']]['potd']=''
            self.lots[info['port_idx']]['waferlot']=''
            self.lots[info['port_idx']]['recipe']=''
            self.lots[info['port_idx']]['alarm']=''
            self.lots[info['port_idx']]['lpt']=''
            self.lots[info['port_idx']]['qty']=''
            self.lots[info['port_idx']]['background_color']=''
            self.lots[info['port_idx']]['buzzer']=''
            
            if 'lotID' in info['data']:
                #self.lots[info['port_idx']]['lotID']=info['data']['lotID']
                lot_info=info['data']['lotID'].split(',') #ASECL use ','
                #print(lot_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(lot_info) == 1: #chi 2022/09/26
                    lotID='{}'.format(lot_info[0])
                else:
                    lotID='{}({})'.format(lot_info[0], len(lot_info))  if lot_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['lotID']=lotID
            if 'stage' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                stage_info=info['data']['stage'].split(',') #ASECL use ','
                #print(stage_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(stage_info) == 1: #chi 2022/09/26
                    stage='{}'.format(stage_info[0])
                else:
                    stage='{}({})'.format(stage_info[0], len(stage_info))  if stage_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['stage']=stage
            if 'CustID' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                cust_info=info['data']['CustID'].split(',') #ASECL use ','
                #print(cust_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(cust_info) == 1: #chi 2022/09/26
                    cust_info='{}'.format(cust_info[0])
                else:
                    cust_info='{}({})'.format(cust_info[0], len(cust_info))  if cust_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['cust']=cust_info
            if 'Product' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                product_info=info['data']['Product'].split(',') #ASECL use ','
                #print(product_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(product_info) == 1: #chi 2022/09/26
                    product_info='{}'.format(product_info[0])
                else:
                    product_info='{}({})'.format(product_info[0], len(product_info))  if product_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['product']=product_info
            if 'LotType' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                lottype_info=info['data']['LotType'].split(',') #ASECL use ','
                #print(lottype_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(lottype_info) == 1: #chi 2022/09/26
                    lottype_info='{}'.format(lottype_info[0])
                else:
                    lottype_info='{}({})'.format(lottype_info[0], len(lottype_info))  if lottype_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['lottype']=lottype_info
            if 'PartID' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                part_info=info['data']['PartID'].split(',') #ASECL use ','
                #print(part_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(part_info) == 1: #chi 2022/09/26
                    part_info='{}'.format(part_info[0])
                else:
                    part_info='{}({})'.format(part_info[0], len(part_info))  if part_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['partID']=part_info
            if 'Automotive' in info['data']: # Mike: 2022/05/04
                self.lots[info['port_idx']]['automotive']=info['data']['Automotive']
            if 'State' in info['data']: # Mike: 2022/05/04
                self.lots[info['port_idx']]['state']=info['data']['State']
            if 'HoldCode' in info['data']: # Mike: 2022/05/04
                self.lots[info['port_idx']]['holdcode']=info['data']['HoldCode']
            if 'TurnRatio' in info['data']: # Mike: 2022/05/04
                self.lots[info['port_idx']]['turnratio']=info['data']['TurnRatio']
            if 'EOTD' in info['data']: # Mike: 2022/05/04
                self.lots[info['port_idx']]['eotd']=info['data']['EOTD']
            if 'desc' in info['data']:
                self.lots[info['port_idx']]['desc']=info['data']['desc']
                pattern=r"LPT:(\d+) QTY:(\d+)" #2024/04/18 for TI AT
                lqdata=re.search(pattern, info['data']['desc'])
                matches= lqdata.groups() if lqdata else ["",""]
                self.lots[info['port_idx']]['lpt']=matches[0]
                self.lots[info['port_idx']]['qty']=matches[1]
            if 'HoldReas' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['holdreas']=info['data']['HoldReas']
            if 'POTD' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['potd']=info['data']['POTD']
            if 'WaferLot' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['waferlot']=info['data']['WaferLot']
            if 'queueTime' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['queue_time']=info['data']['queueTime']
            if 'recipe' in info['data']: # 8.23A
                self.lots[info['port_idx']]['recipe']=info['data']['recipe']
            if 'alarm' in info['data']: #
                self.lots[info['port_idx']]['alarm']=info['data']['alarm']
            if 'color' in info['data']: #
                self.lots[info['port_idx']]['background_color']=info['data']['color']
            if 'buzzer' in info['data']: #
                self.lots[info['port_idx']]['buzzer']=info['data']['buzzer']

            #chocp add
            if 'carrierType' in info['data']:
                self.lots[info['port_idx']]['carrierType']=info['data']['carrierType']
                print('get infoupdate carrierType:', self.lots[info['port_idx']]['carrierType'])

            if 'priority' in info['data']:
                self.lots[info['port_idx']]['priority']=info['data']['priority']
                print('get infoupdate priority:', self.lots[info['port_idx']]['priority'])
        self.notify_panel()

    # def manual(self): # Mike: 2021/07/09
    #     doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'command'}, 'data':{'command':'manual'}}
    #     self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    # def auto(self): # Mike: 2021/07/09
    #     doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'command'}, 'data':{'command':'auto'}}
    #     self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    # def book(self, table): # Mike: 2021/07/09
    #     doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'booked'}, 'data':{table}}
    #     self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    # def connect(self): # Mike: 2021/07/09
    #     doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'connection'}, 'data':{'connection':True}}
    #     self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    # def disconnect(self): # Mike: 2021/07/09
    #     doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'connection'}, 'data':{'connection':False}}
    #     self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    #for thread
    def run(self):
        self.msg_queue=queue.Queue()
        #init for E88 data
        self.initialize_e88_data()

        self.eRackStatusUpdate()
        
        print('\n<start eRack thread:{}>\n'.format(self.device_id))
        
        self.connected=False

        #self.msg_queue.put({'event':'Online', 'data':{}})

        timeout_count=10
        while not self.thread_stop:
            self.heart_beat=time.time()
            msg=''
            try:
                msg=self.msg_queue.get(timeout=1)
                timeout_count=0
            except:
                timeout_count+=1
                #print('timeout')
                pass

            if msg:
                # if msg['event'] == 'AreYouThereResponse':
                #     slots_str=msg.get('data')
                #     print('AreYouThereResponse', slots_str)
                #     pass

                if msg['event'] == 'AllSlotStatus':
                    if self.connected:
                        self.erack_status='UP'
                        try:
                            for slot in data:
                                port_no=slot.get('ant','') -1
                                carrierID=slot.get('carrierID', '')
                                status=slot.get('status', '')
                                if status == 'EMPTY':
                                    self.carriers[port_no]['status']='up'
                                    self.carriers[port_no]['carrierID']=''
                                    self.lots[port_no-1]['booked']=0
                                    self.lots[port_no-1]['booked_for']=''
                                    self.lots[port_no-1]['desc']=''
                                    self.lots[port_no-1]['machine']=''
                                if status == 'ERROR':
                                    self.carriers[port_no]['status']='down'
                                    self.carriers[port_no]['carrierID']=''
                                else:
                                    self.carriers[port_no]['status']='up'
                                    self.carriers[port_no]['carrierID']=carrierID
                        except:
                            traceback.print_exc()
                            pass

                        self.eRackStatusUpdate()

                elif msg['event'] == 'CarrierMoveIn':
                    slotID=msg.get('data', {}).get('slotID')
                    port_no=int(slotID, 16)+1 
                    slotStatus=msg.get('data', {}).get('status')
                    if slotStatus == 'NO':
                        self.carriers[port_no-1]['status']='up'
                        self.carriers[port_no-1]['carrierID']=msg.get('data', {}).get('cassetteID').rstrip()
                    else:
                        self.carriers[port_no-1]['status']='down'
                        self.carriers[port_no-1]['carrierID']=''

                    self.eRackStatusUpdate()

                elif msg['event'] == 'CarrierMoveOut':
                    slotID=msg.get('data', {}).get('slotID')
                    port_no=int(slotID, 16)+1 
                    self.carriers[port_no-1]['status']='up'
                    self.carriers[port_no-1]['carrierID']=''

                    self.lots[port_no-1]['booked']=0
                    self.lots[port_no-1]['booked_for']=''
                    self.lots[port_no-1]['desc']=''
                    self.lots[port_no-1]['machine']=''

                    self.eRackStatusUpdate()

                elif msg['event'] == 'Online':
                    print('Online')
                    self.connected=True
                    #self.erack_status='UP'#

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
                    print('Offline')
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
                    health_check=self.health_check()
                    if not health_check:
                        self.msg_queue.put({'event':'Offline', 'data':{}})
                        continue
                    timeout_count=0
                    #print('query all slot status ...')
                    #self.shelf_h.query_all_slots_status()
                    data=self.query_all_slots_status()
                    self.msg_queue.put({'event':'AllSlotStatus', 'data': data})
            else:
                health_check=self.health_check()
                if health_check:
                    self.msg_queue.put({'event':'Online', 'data':{}})

        else:
            self.finalize_e88_data()
            dataset={'DeviceID':self.device_id}
            E88.report_event(self.secsgem_e88_h, E88.DeviceOffline, dataset)
            #self.sock.close()
            print('\n<end eRack thread:{}>\n'.format(self.device_id))

