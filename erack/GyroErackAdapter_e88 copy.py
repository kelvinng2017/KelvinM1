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
from web_service_log import erack_logger
import json
import copy
from pprint import pformat

import queue
import alarms

#from workstation.order_mgr import OrderMgr
from workstation.eq_mgr import EqMgr

class GetSocketNullString():
    pass

class GyroErackAdapter(threading.Thread):
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
        self.model='Shelf'
        self.zonetype=1
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
        self.alarm_table={20002:[], 20003:[], 20051:0, 20005:[]}
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

        self.zone_list={}
        self.turn=0 #every 3 echo, update 1 relative lot info
        self.begin=0
        self.end=0

        self.raw_logger=logging.getLogger(self.device_id+'_raw') # Mike: 2021/05/17
        for h in self.raw_logger.handlers[:]: # Mike: 2021/09/22
            self.raw_logger.removeHandler(h)
            h.close()
        self.raw_logger.setLevel(logging.DEBUG)

        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_{}_raw.log".format(self.device_id)), when='midnight', interval=1, backupCount=7)
        fileHandler.setLevel(logging.INFO)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.raw_logger.addHandler(fileHandler)

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

    def notify_panel(self, force=False):
        try:
            n=0
            m=0
            mCarriers=[]
            check=True
            for idx, carrier in enumerate(self.carriers):
                #mCarriers.append(carrier) #big bug: 2021/2/21 chocp
                erack_logger.debug("idx:{} carrier:{}".format(idx,  carrier))
                if global_variables.RackNaming == 7:
                    carrier['state'] = self.lots[idx]['state']
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

            if global_variables.filter =='erack':
                check=False if not force else True

            if check:
                erack_logger.debug("eRackStatusUpdate:{}".format({
                    'idx':self.idx,
                    'DeviceID':self.device_id,
                    'MAC':self.mac,
                    'IP':self.ip,
                    'Status':self.erack_status,
                    'carriers':mCarriers,
                    'SlotNum':self.slot_num,
                    'StockNum':self.slot_num-self.available
                    }))
                
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

                    #add cacel order when carrier remove 2023/1/17
                    if global_variables.RackNaming in [13,35] and sendby==0:
                        carrierID=self.last_carriers[idx]['carrierID']
                        if carrierID:
                            WorkID=EqMgr.getInstance().orderMgr.query_work_list_by_carrierID(carrierID)
                            if WorkID:
                                obj={'remote_cmd':'work_cancel', 'WorkID':WorkID}
                                remotecmd_queue.append(obj)
                            if global_variables.field_id == 'USG3':
                                erack_WorkID=EqMgr.getInstance().orderMgr.query_erack_work_list_by_carrierID(carrierID)
                                if erack_WorkID:
                                    obj={'CommandID':erack_WorkID}
                                    EqMgr.getInstance().orderMgr.cancel_transfer(obj)
                                    # print('>>carrier_removed:{}'.format(obj))
                                    # carrier['cmd_send']=False

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
                        
                        if global_variables.TSCSettings.get('Other', {}).get('RTDCarrierLocateCheck','yes') != 'yes': #Sean for UMC 23/12/27
                            for work in EqMgr.getInstance().orderMgr.work_list:
                                if work['CarrierID'] == carrier['carrierID']:
                                    EqMgr.getInstance().orderMgr.update_work_location(work['WorkID'], CarrierLoc)
                                #print(work)
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

                                if global_variables.field_id == 'USG3':  #for USG3 2023/12/15
                                    global_variables.bridge_h.report({'event':'CarrierStored', 'data':{
                                        'CarrierID':datasets['CarrierID'],
                                        'CarrierLoc':datasets['CarrierLoc'],
                                        'HandoffType':datasets['HandoffType']}})
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
            self.notify_panel(force=True)   
            #print('eRack Secs and panel Update...')
            self.last_carriers=copy.deepcopy(self.carriers)

        if self.last_erack_status!=self.erack_status:
            self.notify_panel(force=True)
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
        erack_logger.debug("info:{}".format(info))

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
            self.lots[info['port_idx']]['device'] = ''
            self.lots[info['port_idx']]['lpt']=''
            self.lots[info['port_idx']]['qty']=''
            self.lots[info['port_idx']]['background_color']=''
            self.lots[info['port_idx']]['buzzer']=''

            erack_logger.debug("info['data']:{}".format(info['data']))


            if 'assyLotList' in info['data']:#chipmos use
                
                lotID=info['data'].get("assyLotList",'')
                self.lots[info['port_idx']]['lotID']=lotID
                
            
            if 'entity' in info['data']:#chipmos use
                
                machine=info['data'].get("entity",'')
                self.lots[info['port_idx']]['machine']=machine

            if 'errorCode' in info['data']:
                
                errcode=info['data'].get("errorCode",'')
                self.lots[info['port_idx']]['errorCode']=errcode

            if 'message' in info['data']:
                
                lotsmessage=info['data'].get("message",'')
                self.lots[info['port_idx']]['desc']=lotsmessage

            if 'send_associated_status' in info['data']:
                erack_logger.debug("send_associated_status in info['data']")
                result_send_associated_status=info['data'].get("send_associated_status",True)
                if result_send_associated_status:
                    self.lots[info['port_idx']]['state']='Associated'
                else:
                    self.lots[info['port_idx']]['state']='Identified'
                erack_logger.debug(self.lots)
            
        
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
                if global_variables.RackNaming not in [13, 35]:
                    # self.lots[info['port_idx']]['stage']=info['data']['stage']
                    cust_info=info['data']['CustID'].split(',') #ASECL use ','
                    #print(cust_info)
                    #lotID='{}({})'.format(lot_info[0], len(lot_info)) #chocp 2021/12/15
                    if len(cust_info) == 1: #chi 2022/09/26
                        cust_info='{}'.format(cust_info[0])
                    else:
                        cust_info='{}({})'.format(cust_info[0], len(cust_info))  if cust_info[0] else '' #chocp 2021/12/15 ......

                    self.lots[info['port_idx']]['cust']=cust_info
                else:
                    # print('add_cust_1', info['data']['CustID'])
                    self.lots[info['port_idx']]['cust']=info['data']['CustID']
                    # print('add_cust_2', info['data']['CustID'])

            if 'DeviceID' in info['data']: # Jwo 2024/03/29
                # print('add_device_1', info['data']['DeviceID'])
                self.lots[info['port_idx']]['device']=info['data']['DeviceID']
                # print('add_device_2', info['data']['DeviceID'])
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
        erack_logger.info(self.lots)
            
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
        buf=''
        while not self.thread_stop:
            self.heart_beat=time.time()
            try:
                if not self.connected:
                    if not self.alarm_table[20051] and not start_up: #if carrier check by operator,then launch movin event
                        # self.E88_Zones.Data[self.device_id].zone_alarm_set(20051, True)
                        alarms.ErackOffLineWarning(self.device_id, handler=self.secsgem_e88_h)
                        self.alarm_table[20051]=1
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
                            break
                        except Exception as e:
                            retry+=1
                            time.sleep(2)
                            pass
                    else:
                        print('Out loop for ')
                        raise alarms.ConnectWarning(self.device_id, self.ip, self.port, handler=self.secsgem_e88_h)
                    if self.alarm_table[20051]: #if carrier check by operator,then launch movin event
                        # self.E88_Zones.Data[self.device_id].zone_alarm_set(20051, False)
                        alarms.ErackOffLineWarning(self.device_id, handler=self.secsgem_e88_h)
                        self.secsgem_e88_h.clear_alarm(20051)
                        self.alarm_table[20051]=0
                    dataset={'DeviceID':self.device_id}
                    E88.report_event(self.secsgem_e88_h, E88.DeviceOnline, dataset)
                    buf=''
                else:
                    for zonename in self.zone_list:
                        self.E88_Zones.Data[zonename].ZoneUnitState[self.device_id]=1
                        self.E88_Zones.Data[zonename].ZoneState=1
                    #==================================================================
                    try:
                        self.sock.settimeout(3) #chocp 2022/11/10 #from 10sec
                        tmp = self.sock.recv(2048).decode('utf-8')
                        self.raw_logger.debug('TSC <= {}'.format(tmp))
                        buf=buf+tmp
                        if buf == '':
                            # print('SocketNullStringWarning')
                            raise GetSocketNullString()

                        begin=buf.find('[')
                        end=buf.find(']')

                        if  begin<0 or end<0:
                            continue
                        second_begin=buf.rfind('[')
                        if second_begin != begin and second_begin < end:
                            print('SocketFormatWarning', begin, end)
                            print(buf)
                            buf=''
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)

                        raw_rx=buf[begin:end+1]
                        buf=buf[end+1:]

                        try:
                            query_payload=json.loads(raw_rx) #avoid two echo in buffer
                            #query_payload=json.loads(raw_rx) #???? chocp 2021/12/15
                            # print(query_payload)
                        except:
                            print('SocketFormatWarning', 'parse json error')
                            print(raw_rx)
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)
                    #except socket.timeout:
                    except GetSocketNullString:
                        raise alarms.SocketNullStringWarning(self.device_id, handler=self.secsgem_e88_h)

                    except:
                        traceback.print_exc()
                        if self.syncing_time and (time.time()-self.syncing_time > 10): #chocp 2021/10/4
                            raise alarms.LinkLostWarning(self.device_id, handler=self.secsgem_e88_h)
                        else:
                            self.sync=False
                            time.sleep(1)
                            continue

                    self.erack_status='UP'
                    self.sync=True
                    self.syncing_time=time.time()

                    datasets=[]
                    doc={'res':'no found', 'datasets':datasets, 'time':time.time()}

                    connection=((self.secsgem_e88_h.communicationState.current, self.secsgem_e88_h.controlState.current) == ('COMMUNICATING', 'ONLINE_REMOTE'))

                    for idx, port in enumerate(query_payload): #have 12 pcs
                        if idx > self.slot_num-1: #choc add 2021/11/9
                            break

                        ststus=port['status']
                        ststus_parse=ststus.split('_')
                        if len(ststus_parse) == 2: #8.22H-1
                            port['status']=ststus_parse[1]
                            self.carriers[idx]['direction']=ststus_parse[0]
                            if self.carriers[idx]['direction'] == self.carriers[idx]['direction_target']:
                                self.carriers[idx]['direction_target']= ''

                        if port['status'] == 'ERROR' or port['status'] == 'DISABLE': #chocp:2021/5/31
                            self.carriers[idx]['status']='down'
                            self.lots[idx]['booked']=0 #2022/7/13 for residual book when slot error
                            self.lots[idx]['booked_for']='' #2022/7/13 for residual book when slot error
                            self.carriers[idx]['errorCode']=port.get('errorCode', '')                                
                        elif port['status'] == 'TURNBACK':
                            self.carriers[idx]['status']='turnback'
                            self.lots[idx]['booked']=0 #2022/7/13 for residual book when slot error
                            self.lots[idx]['booked_for']=''
                        elif port['status'] == 'TURNFRONT':
                            self.carriers[idx]['status']='turnfront'
                            self.lots[idx]['booked']=0 #2022/7/13 for residual book when slot error
                            self.lots[idx]['booked_for']=''
                        else:
                            self.carriers[idx]['status']='up'
                            self.carriers[idx]['carrierID']=port['carrierID'].strip() #9/26 chocp
                            self.carriers[idx]['checked']=port.get('checked', 1) #chocp:2021/5/31
                            self.carriers[idx]['alarm']=port.get('alarm', '') # Mike: 2021/6/22
                            self.carriers[idx]['errorCode']=port.get('errorCode', '') # Mike: 2021/6/22
                            #port.get('check', True) ...........
                            if self.carriers[idx]['carrierID'] == '': #clear lot info
                                self.carriers[idx]['create_time']=0 #for auto dispatch
                                self.lots[idx]['lotID']=''
                                self.lots[idx]['stage']=''
                                self.lots[idx]['machine']=''
                                self.lots[idx]['desc']=''
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
                                self.lots[idx]['lpt']=''
                                self.lots[idx]['qty']=''
                                self.lots[idx]['queue_time']=''
                                self.lots[idx]['alarm']=''
                                self.lots[idx]['background_color']=''
                                self.lots[idx]['buzzer']=''
                                self.lots[idx]['device']=''
                                #self.lots[idx]['booked']=0 #chocp add 0917
                            else:
                                self.lots[idx]['booked']=0 #chocp 9/17
                                self.lots[idx]['booked_for']='' #chocp 10/3

                                if not self.carriers[idx].get('create_time', 0): 
                                    self.carriers[idx]['create_time']=time.time() #for auto dispatch
                                
                        if idx in range(self.begin, self.end): #chocp 2021/12/14
                            datasets_index={\
                                        'index':idx,\
                                        'lotID': self.lots[idx].get('lotID',''),\
                                        'stage':self.lots[idx].get('stage',''),\
                                        'product':self.lots[idx].get('product',''),\
                                        'machine':self.lots[idx].get('machine',''),\
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
                                        'desc':self.lots[idx].get('desc',''),\
                                        'device':self.lots[idx].get('device',''),\
                                        'booked':self.lots[idx].get('booked', 0),\
                                        'area_id':self.carriers[idx].get('area_id', ''),\
                                        'box_color':self.carriers[idx].get('box_color', 0), #chocp 2021/12/14
                                        'direction_target':self.carriers[idx].get('direction_target', ''),
                                        'recipe':self.lots[idx].get('recipe',''),
                                        'alarm':self.lots[idx].get('alarm',''),
                                        "lpt":self.lots[idx].get("lpt",""),
                                        "qty":self.lots[idx].get("qty",""),
                                        "lptdesc":self.lots[idx].get("stage",""),
                                        "queue_time":self.lots[idx].get("queue_time",""),
                                        "background_color":self.lots[idx].get('background_color', ''),
                                        "buzzer":self.lots[idx].get('buzzer', ''),
                                        'errorCode':self.lots[idx].get('errorCode', ''),
                                        }
                            datasets_use={}
                            erack_data_item=[] #8.25.11-1
                            if global_variables.RackNaming == 9: #Qualcomm
                                erack_data_item=global_variables.global_erack_item['QUALCOMM'].erack_data

                            elif global_variables.RackNaming in [23,16,34, 54]: #SJ
                                erack_data_item=global_variables.global_erack_item['SJ'].erack_data

                            elif global_variables.RackNaming in [17,11]: #Jcet
                                erack_data_item=global_variables.global_erack_item['JCET'].erack_data

                            elif global_variables.RackNaming == 26: #TI CBUMP
                                erack_data_item=global_variables.global_erack_item['TI'].erack_data

                            elif global_variables.RackNaming == 24: #SkyworksSG
                                erack_data_item=global_variables.global_erack_item['SKYWORKSSG'].erack_data

                            elif global_variables.RackNaming == 7: #Chipmos
                                erack_data_item=global_variables.global_erack_item['CHIPMOS'].erack_data

                            else:
                                erack_data_item=global_variables.global_erack_item['NORMAL'].erack_data

                            for i in erack_data_item:
                                if i in datasets_index.keys():
                                    datasets_use[i]=datasets_index[i]
                            datasets.append(datasets_use)

                            doc={'res':'found', 'datasets':datasets, 'time':time.time(), 'connection':connection}

                    self.turn=(self.turn+1)%self.rows
                    self.begin=self.columns*self.turn
                    self.end=self.begin+self.columns
                    msg = bytearray(json.dumps(doc), encoding='utf-8')
                    self.sock.send(msg) #response remote query #chocp:2021/5/31
                    self.raw_logger.debug('TSC => {}'.format(msg))
                    self.eRackStatusUpdate()

                    try:
                        E88_com_state=self.secsgem_e88_h.communicationState.current
                        if E88_com_state != last_E88_com_state:
                            last_E88_com_state=E88_com_state

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

            dataset={'DeviceID':self.device_id}
            E88.report_event(self.secsgem_e88_h, E88.DeviceOffline, dataset)
            self.sock.close()
            print('\n<end eRack thread:{}>\n'.format(self.device_id))