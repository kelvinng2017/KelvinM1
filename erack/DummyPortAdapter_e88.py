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

from global_variables import Vehicle
from global_variables import output
from global_variables import remotecmd_queue

import tools

import json
import copy
from pprint import pformat

import queue
import alarms


import secsgem

class DummyPortAdapter(threading.Thread):
    #def __init__(self, idx, name, mac, zoneID, func, loc, Transfers, Carriers, Zones, ip, port=5000, ZoneSize=12, ZoneType=1):
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
        #self.func=setting.get('func', '')
        try:
            self.func=json.loads(setting.get('func', {})) #chocp 2023/9/11
        except:
            self.func={}
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

        #for auto dispatch
        self.autodispatch=setting.get('AutoDispatch', False) #3/17 chi
        self.waterlevelhigh=int(setting.get('WaterLevelHigh', 80)) #3/17 chi
        self.waterlevellow=int(setting.get('WaterLevelLow', 20)) #3/17 chi
        self.returnto=setting.get('ReturnTo', 'None' ) #3/17 chi
        self.batchsize=int(setting.get('BatchSize', 4)) #3/17 chi
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
        self.model='DummyPort'
        self.zonetype=2
        self.secsgem_e88_h=secsgem_e88_h
        


        self.E88_Transfers=Transfers
        self.E88_Carriers=Carriers
        self.E88_Zones=Zones
        self.zonestate='auto'

        self.available=0 #9/26 chocp
        self.water_level=''
        self.last_water_level=''

        self.update_params(setting)
        print(self.device_id, self.rows, self.columns, self.slot_num)

        self.thread_stop=False
        self.sock=0

        self.alarm_table={20002:[], 20003:[], 20004:0, 20005:[]}
        # self.water_level_table={'empty':20055, 'low':20054, 'medium':20056, 'high':20052, 'full':20053}
        # self.water_level_table={'empty':alarms.ErackLevelEmptyWarning,
        #                         'low':alarms.ErackLevelLowWarning,
        #                         'medium':alarms.ErackLevelNormalWarning,
        #                         'high':alarms.ErackLevelHighWarning,
        #                         'full':alarms.ErackLevelFullWarning}

        self.associate_queue=collections.deque()

        self.last_erack_status='None'
        

        self.connected=False
        self.sync=False

        self.syncing_time=0
        self.erack_status='DOWN'

        self.sendby=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        #chocp fix 2021/119
        self.read_carriers=[]
        self.last_carriers=[]
        self.carriers=[]
        self.lots=[]

        for i in range(self.rows):
            for j in range(self.columns):
                self.read_carriers.append({'carrierID':''})
                self.lots.append({'lotID':'', 'stage':'', 'product':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':'','recipe':''})
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

        self.zone_list={}

        #desc for target
        #add book_for 202110/2

        self.turn=0 #every 3 echo, update 1 relative lot info
        self.begin=0
        self.end=0

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
            n=0
            m=0
            mCarriers=[]

            for idx, carrier in enumerate(self.carriers):
                #mCarriers.append(carrier) #big bug: 2021/2/21 chocp
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
                    'StockNum':self.slot_num-self.available
                    })

            # if self.available == 0:
            #     self.water_level='full'

            # # elif self.available<self.slot_num-self.slot_num*global_variables.WaterLevel.get('waterLevelHigh', 80)/100:
            # #     self.water_level='high'

            # # elif self.available<self.slot_num-self.slot_num*global_variables.WaterLevel.get('waterLevelLow', 20)/100:
            # #     self.water_level='medium'

            # elif self.available < self.slot_num-self.slot_num*self.waterlevelhigh/100:
            #     self.water_level='high'

            # elif self.available < self.slot_num-self.slot_num*self.waterlevellow/100:
            #     self.water_level='medium'

            # elif self.available<self.slot_num:
            #     self.water_level='low'

            # elif self.available == self.slot_num:
            #     self.water_level='empty'

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
                '''if self.last_water_level in ['high', 'full']:
                    self.water_level_table[self.last_water_level](self.id, handler=self.secsgem_e88_h)
                    alarms.SCSyntaxWarning(self.id, handler=self.secsgem_e88_h)
                    self.E88_Zones.Data[self.device_id].zone_alarm_set(self.water_level_table[self.last_water_level], False)'''
                if self.water_level in self.water_level_table:
                    self.water_level_table[self.water_level](self.device_id, handler=self.secsgem_e88_h)
                self.last_water_level=self.water_level

            pass

        except Exception:
            print('notify_panel_fail')




    def set_machine_info(self, port_no, dest): #chocp add 9/24
        print('set_machine_info', port_no, dest)
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

    def eRackStatusUpdate(self):

        carrier_change=False
        states=[]

        for idx, carrier in enumerate(self.carriers):
            #only update to host if carrier status change

            sendby=0

            # 9/19, 9/21
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

                    if carrier['errorCode'] and CarrierLoc not in self.alarm_table[20003]: #if carrier check by operator,then launch movin event
                        datasets={}
                        datasets['CarrierLoc']=CarrierLoc
                        self.E88_Zones.Data[zonename].zone_alarm_set(20003, True, datasets)
                        self.alarm_table[20003].append(CarrierLoc)

            elif carrier['status'] == 'ReadyToLoad':
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=1
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for rack update
                state={'SlotID': idx+1, 'Status':'None'}
                states.append(state)

                #for port update
                if self.last_carriers[idx]!=carrier:

                    carrier_change=True
                    # E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby})
                    if self.read_carriers[idx]['carrierID'] in self.E88_Carriers.Data:
                        datasets={}
                        datasets['HandoffType']=sendby+1
                        self.E88_Carriers.set(self.read_carriers[idx]['carrierID'], datasets)
                        if CarrierLoc in self.E88_Carriers.Mapping:
                            del self.E88_Carriers.Mapping[CarrierLoc]
                        if self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].CarrierState == 3:
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.remove()
                        else:
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.kill_carrier()
                        self.E88_Carriers.delete(self.read_carriers[idx]['carrierID'])
                        self.zone_capacity_change(zonename, 1)
                        self.read_carriers[idx]['carrierID']=''

                if CarrierLoc in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20002, False, datasets)
                    self.alarm_table[20002].remove(CarrierLoc)

                if CarrierLoc in self.alarm_table[20003]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20003, False, datasets)
                    self.alarm_table[20003].remove(CarrierLoc)

                if CarrierLoc in self.alarm_table[20005]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20005, False, datasets)
                    self.alarm_table[20005].remove(CarrierLoc)

            elif carrier['status'] == 'ReadyToUnload':
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=2
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for rack update
                state={'SlotID': idx+1, 'Status':carrier['carrierID']}
                states.append(state)

                if self.last_carriers[idx]!=carrier:
                    #print('diff', self.last_carriers[idx], carrier)

                    carrier_change=True
                    #for port update
                    # E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby})
                    #add checkin event
                    #print('CheckIn', state['SlotID'], state['Status'])
                    # E82.report_event(self.secsgem_e82_h, E82.CheckIn, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status']})

                    if carrier['carrierID'] and carrier['carrierID'] not in self.E88_Carriers.Data:
                        if CarrierLoc not in self.E88_Carriers.Mapping:
                            self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                            self.read_carriers[idx]['carrierID']=carrier['carrierID']
                            self.E88_Carriers.add(self.read_carriers[idx]['carrierID'])
                            datasets={}
                            datasets['CarrierID']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.set(self.read_carriers[idx]['carrierID'], datasets)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].id_read(self.read_carriers[idx]['carrierID'], 0)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.wait_in()
                            self.zone_capacity_change(zonename, 0)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.transfer()
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.wait_out()
                        else:
                            old_carrier_id=self.E88_Carriers.Mapping[CarrierLoc]
                            self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                            self.read_carriers[idx]['carrierID']=carrier['carrierID']
                            datasets={}
                            datasets['CarrierID']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.mod(old_carrier_id, self.read_carriers[idx]['carrierID'])
                            self.E88_Carriers.set(self.read_carriers[idx]['carrierID'], datasets)
                        if CarrierLoc in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                            datasets={}
                            datasets['CarrierLoc']=CarrierLoc
                            self.E88_Zones.Data[zonename].zone_alarm_set(20002, False, datasets)
                            self.alarm_table[20002].remove(CarrierLoc)
                    else:
                        if CarrierLoc not in self.E88_Carriers.Mapping: # Duplicate
                            self.read_carriers[idx]['carrierID']=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                            self.E88_Carriers.Mapping[CarrierLoc]=self.read_carriers[idx]['carrierID']
                            self.E88_Carriers.add(self.read_carriers[idx]['carrierID'])
                            datasets={}
                            datasets['CarrierID']=carrier['carrierID']
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.set(self.read_carriers[idx]['carrierID'], datasets)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].id_read(self.read_carriers[idx]['carrierID'], 2)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.wait_in()
                            self.zone_capacity_change(zonename, 0)
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.transfer()
                            self.E88_Carriers.Data[self.read_carriers[idx]['carrierID']].State.wait_out()
                            if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                                datasets={}
                                datasets['CarrierLoc']=CarrierLoc
                                self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                                self.alarm_table[20002].append(CarrierLoc)
                        elif CarrierLoc == self.E88_Carriers.Data[carrier['carrierID']].CarrierLoc:
                            pass
                        else:
                            old_carrier_id=self.E88_Carriers.Mapping[CarrierLoc]
                            self.read_carriers[idx]['carrierID']=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                            self.E88_Carriers.Mapping[CarrierLoc]=self.read_carriers[idx]['carrierID']
                            datasets={}
                            datasets['CarrierID']=carrier['carrierID']
                            datasets['CarrierLoc']=CarrierLoc
                            datasets['CarrierIDRead']=self.read_carriers[idx]['carrierID']
                            datasets['CarrierZoneName']=zonename
                            datasets['CarrierDeviceName']=self.device_id
                            datasets['HandoffType']=sendby+1
                            datasets['PortType']=self.type # Mike: 2022/04/15
                            self.E88_Carriers.mod(old_carrier_id, self.read_carriers[idx]['carrierID'])
                            self.E88_Carriers.set(self.read_carriers[idx]['carrierID'], datasets)
                            if CarrierLoc not in self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                                datasets={}
                                datasets['CarrierLoc']=CarrierLoc
                                self.E88_Zones.Data[zonename].zone_alarm_set(20002, True, datasets)
                                self.alarm_table[20002].append(CarrierLoc)

                if CarrierLoc in self.alarm_table[20003]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20003, False, datasets)
                    self.alarm_table[20003].remove(CarrierLoc)

                if CarrierLoc in self.alarm_table[20005]: #if carrier check by operator,then launch movin event
                    datasets={}
                    datasets['CarrierLoc']=CarrierLoc
                    self.E88_Zones.Data[zonename].zone_alarm_set(20005, False, datasets)
                    self.alarm_table[20005].remove(CarrierLoc)

            elif carrier['status'] == 'Manual':
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['StockerUnitState']=4
                self.E88_Zones.Data[zonename].StockerUnit[CarrierLoc]['CarrierID']=carrier['carrierID']
                #for port update
                if self.last_carriers[idx]!=carrier:
                    carrier_change=True

                    if CarrierLoc not in self.alarm_table[20005]: #if carrier check by operator,then launch movin event
                        datasets={}
                        datasets['CarrierLoc']=CarrierLoc
                        self.E88_Zones.Data[zonename].zone_alarm_set(20005, True, datasets)
                        self.alarm_table[20005].append(CarrierLoc)

            else:
                #for port update
                if self.last_carriers[idx]!=carrier:
                    carrier_change=True
                    # E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby})


        if carrier_change:
            self.notify_panel()   
            #print('eRack Secs and panel Update...')
            self.last_carriers=copy.deepcopy(self.carriers)

        if self.last_erack_status!=self.erack_status:
            self.notify_panel()
            #print('eRack Panel Update...')
            self.last_erack_status=self.erack_status

    def on_notify(self, event, data):
        #print('eRack {} get {}, data {}'.format(self.device_id, event, data))
        if event == 'acquire_start_evt' or event == 'deposit_start_evt':
            #self.sendby[0]=1
            pass
        elif event == 'acquire_complete_evt' or event == 'deposit_complete_evt':
            #self.sendby[0]=1
            pass


    def eRackInfoUpdate(self, info):
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
            self.lots[info['port_idx']]['custID']=''  #chi 2022/10/18 use LowerLevelErack for spil CY
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
            if 'lotID' in info['data']:
                #self.lots[info['port_idx']]['lotID']=info['data']['lotID']
                lot_info=info['data']['lotID'].split(',') #ASECL use ','
                print(lot_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(lot_info) == 1: #chi 2022/09/26
                    lotID='{}'.format(lot_info[0])
                else:
                    lotID='{}({})'.format(lot_info[0], len(lot_info))  if lot_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['lotID']=lotID
            if 'stage' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                stage_info=info['data']['stage'].split(',') #ASECL use ','
                print(stage_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(stage_info) == 1: #chi 2022/09/26
                    stage='{}'.format(stage_info[0])
                else:
                    stage='{}({})'.format(stage_info[0], len(stage_info))  if stage_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['stage']=stage
            if 'CustID' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                cust_info=info['data']['CustID'].split(',') #ASECL use ','
                print(cust_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(cust_info) == 1: #chi 2022/09/26
                    cust_info='{}'.format(cust_info[0])
                else:
                    cust_info='{}({})'.format(cust_info[0], len(cust_info))  if cust_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['custID']=cust_info
            if 'Product' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                product_info=info['data']['Product'].split(',') #ASECL use ','
                print(product_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(product_info) == 1: #chi 2022/09/26
                    product_info='{}'.format(product_info[0])
                else:
                    product_info='{}({})'.format(product_info[0], len(product_info))  if product_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['product']=product_info
            if 'LotType' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                lottype_info=info['data']['LotType'].split(',') #ASECL use ','
                print(lottype_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(lottype_info) == 1: #chi 2022/09/26
                    lottype_info='{}'.format(lottype_info[0])
                else:
                    lottype_info='{}({})'.format(lottype_info[0], len(lottype_info))  if lottype_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['lottype']=lottype_info
            if 'PartID' in info['data']: # Mike: 2022/05/04
                # self.lots[info['port_idx']]['stage']=info['data']['stage']
                part_info=info['data']['PartID'].split(',') #ASECL use ','
                print(part_info)
                #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                if len(part_info) == 1: #chi 2022/09/26
                    part_info='{}'.format(part_info[0])
                else:
                    part_info='{}({})'.format(part_info[0], len(part_info))  if part_info[0] else '' #chocp 2021/12/15 ......

                self.lots[info['port_idx']]['lottype']=lottype_info
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
            if 'HoldReas' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['holdreas']=info['data']['HoldReas']
            if 'POTD' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['potd']=info['data']['POTD']
            if 'WaferLot' in info['data']: # Mike: 2023/05/25
                self.lots[info['port_idx']]['waferlot']=info['data']['WaferLot']
            if 'recipe' in info['data']: # 8.23A
                self.lots[info['port_idx']]['recipe']=info['data']['recipe']
            if 'alarm' in info['data']: #
                self.lots[info['port_idx']]['alarm']=info['data']['alarm']

            #chocp add
            if 'carrierType' in info['data']:
                self.lots[info['port_idx']]['carrierType']=info['data']['carrierType']
                print('get infoupdate carrierType:', self.lots[info['port_idx']]['carrierType'])

            if 'priority' in info['data']:
                self.lots[info['port_idx']]['priority']=info['data']['priority']
                print('get infoupdate priority:', self.lots[info['port_idx']]['priority'])

        self.notify_panel()

    def manual(self): # Mike: 2021/07/09
        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'command'}, 'data':{'command':'manual'}}
        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    def auto(self): # Mike: 2021/07/09
        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'command'}, 'data':{'command':'auto'}}
        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    def book(self, table): # Mike: 2021/07/09
        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'booked'}, 'data':{table}}
        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    def connect(self): # Mike: 2021/07/09
        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'connection'}, 'data':{'connection':True}}
        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))

    def disconnect(self): # Mike: 2021/07/09
        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'request', 'typeName':'connection'}, 'data':{'connection':False}}
        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8'))



    #for thread
    def run(self):

        for i in range(self.rows*self.columns): # Mike: 2021/09/22
            rack_id=self.device_id
            port_no=i+1
            area_id=self.carriers[i]['area_id']
            zonename=area_id if area_id else self.groupID if (self.groupID and global_variables.RackNaming == 2) else self.device_id

            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            if not res:
                raise alarms.SCSyntaxWarning(self.device_id, handler=self.secsgem_e88_h)

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

        print('\n<start eRack thread:{}>\n'.format(self.device_id))
        self.eRackStatusUpdate()
        E88_com_state=''
        last_E88_com_state=''
        start_up=True
        while not self.thread_stop:
            self.heart_beat=time.time()
            try:
                if not self.connected:
                    if not self.alarm_table[20004] and not start_up: #if carrier check by operator,then launch movin event
                        # self.E88_Zones.Data[self.device_id].zone_alarm_set(20004, True)
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
                    start_up=False
                    retry=0
                    while(retry<5 and not self.thread_stop): #fix 5
                        try:
                            print('Rack adapter {} connecting {}, {}'.format(self.device_id, self.ip, self.port))
                            self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.sock.settimeout(5)
                            self.sock.connect((self.ip, self.port))
                            self.connected=True
                            self.syncing_time=time.time()
                            
                            if E88_com_state not in ["COMMUNICATING"]:
                                self.disconnect()
                            else:
                                self.connect()
                            break
                        except Exception as e:
                            retry+=1
                            time.sleep(2)
                            pass
                    else:
                        print('Out loop for ')
                        raise alarms.ConnectWarning(self.device_id, self.ip, self.port, handler=self.secsgem_e88_h)


                else:
                    if self.alarm_table[20004]: #if carrier check by operator,then launch movin event
                        # self.E88_Zones.Data[self.device_id].zone_alarm_set(20004, False)
                        alarms.ErackOffLineWarning(self.device_id, handler=self.secsgem_e88_h)
                        self.secsgem_e88_h.clear_alarm(20004)
                        self.alarm_table[20004]=0
                        dataset={'DeviceID':self.device_id}
                        E88.report_event(self.secsgem_e88_h, E88.DeviceOnline, dataset)
                    for zonename in self.zone_list:
                        self.E88_Zones.Data[zonename].ZoneUnitState[self.device_id]=1
                        self.E88_Zones.Data[zonename].ZoneState=1

                    #==================================================================
                    try:
                        self.sock.settimeout(3) #chocp 2022/11/10 #from 10sec
                        raw_rx=self.sock.recv(2048).decode('utf-8')

                        if raw_rx == '':
                            # print('SocketNullStringWarning')
                            raise GetSocketNullString()

                        begin=raw_rx.find('[')
                        end=raw_rx.find(']')

                        if  begin<0 or end<0:
                            print('SocketFormatWarning', begin, end)
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)

                        try:
                            query_payload=json.loads(raw_rx[begin:end+1]) #avoid two echo in buffer
                            #query_payload=json.loads(raw_rx) #???? chocp 2021/12/15
                            # print(query_payload)
                        except:
                            print('SocketFormatWarning', 'parse json error')
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)
                    #except socket.timeout:
                    except GetSocketNullString:
                        raise alarms.SocketNullStringWarning(self.device_id, handler=self.secsgem_e88_h)

                    except:

                        if self.syncing_time and (time.time()-self.syncing_time > 10): #chocp 2021/10/4
                            raise alarms.LinkLostWarning(self.device_id, handler=self.secsgem_e88_h)
                        else:
                            self.sync=False
                            time.sleep(1)
                            continue
                    #==================================================================

                    self.erack_status='UP'
                    self.sync=True
                    self.syncing_time=time.time()

                    datasets=[]
                    if query_payload['head']['device name'] != self.device_id:
                        self.E88_Zones.mod(self.device_id, query_payload['head']['device name'])
                        self.device_id=query_payload['head']['device name']
                        datasets={}
                        datasets['ZoneName']=self.device_id
                        self.E88_Zones.set(self.device_id, datasets)

                    if query_payload['head']['typeName'] == 'GetState':
                        doc={'head':{'device name':'E88_interface', 'date':time.strftime("%Y%m%d-%H:%M:%S", time.localtime()), 'service':'reply', 'typeName':'GetState'}, 'data':[]}
                        for port in query_payload['data']: #have 1 pcs
                            #print(idx, port)
                            #if port['status'] == 'ERROR':
                            idx=int(port['port name'][1:])-1
                            if port['state'] == 'Error' or port['state'] == 'Initial': #chocp:2021/5/31
                                self.carriers[idx]['status']='down'
                                self.carriers[idx]['errorCode']=port.get('errorCode', '') # Mike: 2021/6/22
                            else:
                                self.carriers[idx]['status']=port['state']
                                self.carriers[idx]['carrierID']=port['carrierID'].strip() #9/26 chocp
                                self.carriers[idx]['checked']=port.get('checked', 1) #chocp:2021/5/31
                                self.carriers[idx]['errorCode']=port.get('errorCode', '') # Mike: 2021/6/22

                                #port.get('check', True) ...........
                                if self.carriers[idx]['carrierID'] == '': #clear lot info
                                    self.lots[idx]['lotID']=''
                                    self.lots[idx]['stage']=''
                                    self.lots[idx]['machine']=''
                                    self.lots[idx]['desc']=''
                                    self.lots[idx]['priority']=0
                                    self.lots[idx]['cust']=''
                                    self.lots[idx]['partID']=''
                                    self.lots[idx]['lottype']=''
                                    self.lots[idx]['automotive']=''
                                    self.lots[idx]['state']=''
                                    self.lots[idx]['holdcode']=''
                                    self.lots[idx]['turnratio']=0
                                    self.lots[idx]['eotd']=''
                                    self.lots[idx]['holdreas']=''
                                    self.lots[idx]['potd']=''
                                    self.lots[idx]['waferlot']=''
                                    self.lots[idx]['recipe']=''
                                    #self.lots[idx]['booked']=0 #chocp 9/17
                                else:
                                    self.lots[idx]['booked']=0 #chocp 9/17
                                    self.lots[idx]['booked_for']='' #chocp 10/3
                                    
                                if idx in range(self.begin, self.end): #chocp:2021/5/31
                                    datasets.append({\
                                            'index':idx,\
                                            'Foup_ID':self.carriers[idx]['carrierID'] ,\
                                            'lotID': self.lots[idx].get('lotID',''),\
                                            'stage':self.lots[idx].get('stage',''),\
                                            'cust':self.lots[idx].get('cust',''),\
                                            'partID':self.lots[idx].get('partID',''),\
                                            'lottype':self.lots[idx].get('lottype',''),\
                                            'automotive':self.lots[idx].get('automotive',''),\
                                            'state':self.lots[idx].get('state',''),\
                                            'holdcode':self.lots[idx].get('holdcode',''),\
                                            'turnratio':self.lots[idx].get('turnratio',0),\
                                            'eotd':self.lots[idx].get('eotd',''),\
                                            'holdreas':self.lots[idx].get('holdreas',''),\
                                            'potd':self.lots[idx].get('potd',''),\
                                            'waferlot':self.lots[idx].get('waferlot',''),\
                                            'product':self.lots[idx].get('product',''),\
                                            'machine':self.lots[idx].get('machine',''),\
                                            'desc':self.lots[idx].get('desc',''),\
                                            'booked':self.lots[idx].get('booked', 0),\
                                            'content':['lotID', 'stage', 'machine', 'desc'],\
                                            'recipe':self.lots[idx].get('recipe',''),\
                                            'errorCode':'0'
                                        })
                                    doc={'res':'found', 'datasets':datasets, 'time':time.time()}

                                if idx in range(self.begin, self.end): #chocp 2021/12/14 
                                    datasets.append({\
                                        'index':idx,\
                                        'lotID': self.lots[idx].get('lotID',''),\
                                        'stage':self.lots[idx].get('stage',''),\
                                        'cust':self.lots[idx].get('cust',''),\
                                        'partID':self.lots[idx].get('partID',''),\
                                        'lottype':self.lots[idx].get('lottype',''),\
                                        'automotive':self.lots[idx].get('automotive',''),\
                                        'state':self.lots[idx].get('state',''),\
                                        'holdcode':self.lots[idx].get('holdcode',''),\
                                        'turnratio':self.lots[idx].get('turnratio',0),\
                                        'eotd':self.lots[idx].get('eotd',''),\
                                        'holdreas':self.lots[idx].get('holdreas',''),\
                                        'potd':self.lots[idx].get('potd',''),\
                                        'waferlot':self.lots[idx].get('waferlot',''),\
                                        'product':self.lots[idx].get('product',''),\
                                        'machine':self.lots[idx].get('machine',''),\
                                        'desc':self.lots[idx].get('desc',''),\
                                        'booked':self.lots[idx].get('booked', 0),\
                                        'area_id':self.carriers[idx].get('area_id', ''),\
                                        'box_color':self.carriers[idx].get('box_color', 0), #chocp 2021/12/14
                                        })
                                    doc={'res':'found', 'datasets':datasets, 'time':time.time()}

                        self.turn=(self.turn+1)%self.rows
                        self.begin=self.columns*self.turn
                        self.end=self.begin+self.columns

                        # self.begin=self.begin +1
                        # self.end=self.end +1
                        # if self.begin == self.slot_num:
                        #     self.begin=0
                        #     self.end=1
                        #print(doc)
                        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8')) #response remote query #chocp:2021/5/31

                        self.eRackStatusUpdate()

                    try:
                        E88_com_state=self.secsgem_e88_h.communicationState.current
                        if E88_com_state != last_E88_com_state:
                            last_E88_com_state=E88_com_state
                       
                            if E88_com_state not in ["COMMUNICATING"]:
                                self.disconnect()
                            else:
                                self.connect()
                    except Exception as e:
                        print(e)

            except alarms.MyException as e: #ErackOffLineWarning
                #traceback.print_exc()
                self.sock.close()
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'

                # output('AlarmSet', {'type':e.alarm_set, 'code':e.code, 'extend_code':e.sub_code, 'txt':e.txt})
                self.eRackStatusUpdate()
                time.sleep(1)

            except: #ErackOffLineWarning
                traceback.print_exc()
                self.sock.close()
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'

                # output('AlarmSet', {'type':'Error', 'code':30000, 'extend_code':self.device_id, 'txt':traceback.format_exc()})
                self.eRackStatusUpdate()
                time.sleep(1)
                #self.secsgem_e82_h.set_alarm(self.error_code)
        else:

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

            self.sock.close()
            print('\n<end eRack thread:{}>\n'.format(self.device_id))