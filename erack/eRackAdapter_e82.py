import collections
import traceback
import threading
import time
import socket
import re

from  tr_wq_lib import TransferWaitQueue

import semi.e82_equipment as E82 #can use singleton

import global_variables

from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host #can use singleton

from global_variables import Vehicle


from global_variables import output

import json
import copy
from pprint import pformat

import queue
import tools
from workstation.eq_mgr import EqMgr
from global_variables import remotecmd_queue


class MyException(Exception):
    pass

class ConnectWarning(MyException):
    def __init__(self, eRacKID, ip, port):
        self.alarm_set='Rack'
        self.unit_id=eRacKID
        self.code=10051
        self.sub_code=0
        self.level='Error'
        self.txt='{}, Rack connect:{}, port:{} fail'.format(eRacKID, ip, port)

class SocketNullStringWarning(MyException):
    def __init__(self, eRacKID):
        self.alarm_set='Rack'
        self.unit_id=eRacKID
        self.code=30002
        self.sub_code=0
        self.level='Error'
        self.txt='receive null string from socket'

class LinkLostWarning(MyException):
    def __init__(self, eRacKID, txt='linking timeout'):
        self.alarm_set='Rack'
        self.unit_id=eRacKID
        self.code=30003
        self.sub_code=0
        self.level='Error'
        self.txt='linking timeout'

class SocketFormatWarning(MyException):
    def __init__(self, eRacKID, txt='receive format error from socket'):
        self.alarm_set='Rack'
        self.unit_id=eRacKID
        self.code=30004
        self.sub_code=0
        self.level='Error'
        self.txt=txt

class eRackAdapter(threading.Thread):
    #def __init__(self, idx, name, mac, zoneID, func, loc, ip, port=5000):

    def update_params(self, setting={}):
        if setting:
            self.idx=setting['idx']
            self.device_id=setting['eRackID']
            self.mac=setting['mac']
            self.groupID=setting['groupID'] if setting['groupID'] else setting['eRackID'] #9/26
            self.zone=setting['zone']
            self.link_zone=setting.get('link', '') #v8.24F for SJ
            if not self.link_zone: self.link_zone=self.zone #v8.24F for SJ
            
            self.ip=setting['ip']
            self.port=int(setting.get('port', 5000))
            self.func=setting.get('func', '')
            self.loc=setting.get('location', '')
            self.type=setting.get('type', '3x4')
            self.zonesize=int(setting.get('zonesize', 12))
            self.zonetype=int(setting.get('zonetype', 1))
            
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

            self.model=setting.get('model', 'Shelf')

            if self.model =='TurnTable':
                self.zonetype =3



    def __init__(self, secsgem_e82_h, setting):
 #h=eRackAdapter(setting['idx'], setting['eRackID'], setting['mac'],  setting['zone'], setting['func'], setting.get('location', ''), setting['ip'], setting['port'], setting['type'])
        self.secsgem_e82_h=secsgem_e82_h
        
        
        # self.idx=setting['idx']         
        # self.device_id=setting['eRackID']
        # self.mac=setting['mac']
        # self.groupID=setting['groupID'] if setting['groupID'] else setting['eRackID'] #9/26
        # self.zone=setting['zone']
        # self.ip=setting['ip']
        # self.port=setting.get('port', 5000)
        # self.func=setting.get('func', '')
        # self.loc=setting.get('location', '')
        # self.type=setting.get('type', '3x4')

        self.available=0 #9/26 chocp

        self.water_level='' #chi 05/10
        self.last_water_level='' #chi 05/10

        self.update_params(setting) #chi 05/10
        print(self.device_id, self.rows, self.columns, self.slot_num)
        self.thread_stop=False
        self.sock=0

        self.associate_queue=collections.deque()

        self.last_erack_status='None'
        

        self.connected=False
        self.sync=False

        self.syncing_time=0
        
        self.sendby=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.erack_status='DOWN'
        '''
        self.last_carriers=[\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':4},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':4},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':4}]
        self.carriers=[\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':1, 'rack_col':4},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':2, 'rack_col':4},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':1},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':2},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':3},\
        {'checked':1, 'carrierID':'', 'status':'down', 'rack_row':3, 'rack_col':4}]
        self.lots=[\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''},\
        {'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''}]
        '''
        self.read_carriers=[]
        self.last_carriers=[]
        self.carriers=[]
        self.last_lots=[]
        self.lots=[]

        for i in range(self.rows):  #chi 05/10
            for j in range(self.columns):
                self.read_carriers.append({'carrierID':''})
                self.last_lots.append({'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':'','recipe':''})
                self.lots.append({'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':'','recipe':''})
                self.last_carriers.append({'box_color':'', 'area_id':'', 'checked':1, 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0,'direction':'', 'direction_target':'','transfering':False})
                self.carriers.append({'box_color':'', 'area_id':'', 'checked':1, 'carrierID':'', 'status':'down', 'idx':self.columns*i+j, 'rack_row':i+1, 'rack_col':j+1, 'errorCode':'', 'create_time':0,'direction':'', 'direction_target':'','transfering':False})
        # for i in range(self.rows):
        #     for j in range(self.columns):
        #         self.lots.append({'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''})
        #         self.last_carriers.append({'checked':1, 'carrierID':'', 'status':'down', 'rack_row':i+1, 'rack_col':j+1, 'errorCode':''})
        #         self.carriers.append({'checked':1, 'carrierID':'', 'status':'down', 'rack_row':i+1, 'rack_col':j+1, 'errorCode':''})
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

        self.turn=0 #every 3 echo, update 1 relative lot info
        self.begin=0
        self.end=0

        threading.Thread.__init__(self)


    # def notify_panel(self):
    #     n=0
    #     mCarriers=[]
    #     for idx, carrier in enumerate(self.carriers):
    #         #mCarriers.append(carrier) #big bug: 2021/2/21 chocp
    #         mCarriers.append(copy.deepcopy(carrier))
    #         mCarriers[idx]['lot']=self.lots[idx]
    #         #print(carrier['status'], carrier['carrierID'], self.lots[idx]['booked'])
    #         if carrier['status'] == 'up' and carrier['carrierID'] == '': #9/26 chocp
    #             if not self.lots[idx]['booked']:
    #                 n+=1

    #     if self.erack_status == 'DOWN':
    #         self.available=0
    #     else:
    #         self.available=n

    #     output('eRackStatusUpdate', {
    #             'idx':self.idx,
    #             'DeviceID':self.device_id,
    #             'MAC':self.mac,
    #             'IP':self.ip,
    #             'Status':self.erack_status,
    #             'carriers':mCarriers,
    #             'SlotNum':self.slot_num,
    #             'StockNum':self.slot_num-self.available
    #             })

    #     #print('carriers', mCarriers)
    #     # print(self.device_id, 'idx:11 checked', mCarriers[11]['checked'])
    #     pass
    def notify_panel(self):
        try:
            n=0
            mCarriers=[]

            for idx, carrier in enumerate(self.carriers):
                #mCarriers.append(carrier) #big bug: 2021/2/21 chocp
                mCarriers.append(copy.deepcopy(carrier))
                mCarriers[idx]['lot']=self.lots[idx]
                #print(carrier['status'], carrier['carrierID'], self.lots[idx]['booked'])
                if carrier['status'] == 'up' and carrier['carrierID'] == '': #9/26 chocp
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

            if self.available == 0:
                self.water_level='full'

            # elif self.available<self.slot_num-self.slot_num*global_variables.WaterLevel.get('waterLevelHigh', 80)/100:
            #     self.water_level='high'

            # elif self.available<self.slot_num-self.slot_num*global_variables.WaterLevel.get('waterLevelLow', 20)/100:
            #     self.water_level='medium'

            elif self.available < self.slot_num-self.slot_num*self.waterlevelhigh/100:
                self.water_level='high'

            elif self.available < self.slot_num-self.slot_num*self.waterlevellow/100:
                self.water_level='medium'

            elif self.available<self.slot_num:
                self.water_level='low'

            elif self.available == self.slot_num:
                self.water_level='empty'

            else:
                pass


            if self.last_water_level != self.water_level:
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
            rack_id=self.device_id
            port_no=idx+1
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)

            h_vehicle=None
            sendby=0
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
            
            if carrier['status'] == 'down': #status: Fail
                #for rack update
                state={'SlotID': idx+1, 'Status':'Fail', 'Machine':self.lots[idx]['machine']} # Mike: 2022/05/23
                states.append(state)
                #for port update
                #if self.last_carriers[idx]!=carrier:
                if self.last_carriers[idx]['carrierID']!=carrier['carrierID'] or self.last_carriers[idx]['status']!=carrier['status']:
                    carrier_change=True
                    E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby, 'RackLocation': self.loc,'RackGroup':self.groupID}) # Mike: 2021/05/12
                if self.last_carriers[idx]['carrierID']!=carrier['carrierID']:
                    if self.last_carriers[idx]['carrierID']:
                        self.secsgem_e82_h.rm_carrier(self.last_carriers[idx]['carrierID'])
                    if carrier['carrierID']:
                        self.secsgem_e82_h.add_carrier(carrier['carrierID'], {
                                             'RackID':self.device_id,
                                             'SlotID':state['SlotID'],
                                             'CarrierID':carrier['carrierID']})
                    if h_vehicle and global_variables.TSCSettings.get('Safety', {}).get('TrBackReqCheck', 'yes').lower() == 'yes':
                        h_vehicle.adapter.robot_check_control(False)

            elif carrier['carrierID'] == '': #status: None
                #for rack update
                state={'SlotID': idx+1, 'Status':'None', 'Machine':self.lots[idx]['machine']} # Mike: 2022/05/23
                states.append(state)
                #for port update
                #if self.last_carriers[idx]!=carrier:
                if self.last_carriers[idx]['carrierID']!=carrier['carrierID'] or self.last_carriers[idx]['status']!=carrier['status']:
                    
                    carrier_change=True
                    #print('In None', idx, carrier)
                    E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby, 'RackLocation': self.loc,'RackGroup':self.groupID}) # Mike: 2021/05/12
                    if self.last_carriers[idx]['carrierID']!=carrier['carrierID']:
                        self.secsgem_e82_h.rm_carrier(self.last_carriers[idx]['carrierID'])
                        
                    #Hshuo add cacel order when carrier remove 20240611
                    #if no srtd also can cancel and abort
                    if global_variables.RackNaming == 1 and sendby == 0:
                        carrierID=self.last_carriers[idx]['carrierID']
                        if carrierID:
                            if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes': # for ASECL L5
                                WorkID=EqMgr.getInstance().orderMgr.query_work_list_by_carrierID(carrierID)                                                           
                                if WorkID:
                                    obj={'remote_cmd':'work_cancel', 'WorkID':WorkID}
                                    remotecmd_queue.append(obj)
                            else:  #no srtd for ASECL CP                                                           
                                for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                                    for host_tr_cmd in zone_wq.queue: #cancel waiting queue                                        
                                        if host_tr_cmd.get('carrierID') == carrierID:                             
                                            CommandID=host_tr_cmd.get('CommandInfo').get('CommandID')                                                                        
                                            obj={'remote_cmd':'cancel',  'CommandID':CommandID}                                        
                                            remotecmd_queue.append(obj)                                    
                                    else:       #abort executing queue
                                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():                                            
                                            for local_tr_cmd in h_vehicle.tr_cmds:
                                                if local_tr_cmd.get('TransferInfo').get('CarrierID') == carrierID:                                                
                                                    CommandID=local_tr_cmd.get('host_tr_cmd').get('CommandInfo').get('CommandID')                                                                                     
                                                    obj={'remote_cmd':'abort',  'CommandID':CommandID}                                        
                                                    remotecmd_queue.append(obj)
                    
            else: #with carrierID, checked=1
                state={'SlotID': idx+1, 'Status':carrier['carrierID'], 'Machine':self.lots[idx]['machine']} # Mike: 2022/05/23
                states.append(state)

                #if self.last_carriers[idx]!=carrier:
                if self.last_carriers[idx]['carrierID']!=carrier['carrierID'] or self.last_carriers[idx]['status']!=carrier['status']:
                    #print('diff', self.last_carriers[idx], carrier)
                    
                    carrier_change=True
                    '''
                    if carrier['checked']: #if carrier check by operator,then launch movin event
                        #print('In Carrier', idx, carrier)
                        E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby, 'RackLocation': self.loc}) # Mike: 2021/05/12
                        E82.report_event(self.secsgem_e82_h, E82.CheckIn, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status']})
                    '''
                    #back old version
                    if h_vehicle and global_variables.TSCSettings.get('Safety', {}).get('TrBackReqCheck', 'yes').lower() == 'yes':
                        h_vehicle.adapter.robot_check_control(True)
                    E82.report_event(self.secsgem_e82_h, E82.PortStatusUpdate, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status'], 'SendBy': sendby, 'RackLocation': self.loc,'RackGroup':self.groupID}) # Mike: 2021/05/12
                    E82.report_event(self.secsgem_e82_h, E82.CheckIn, {'RackID':self.device_id , 'SlotID':state['SlotID'], 'SlotStatus':state['Status']})
                    if self.last_carriers[idx]['carrierID']!=carrier['carrierID']:
                        self.secsgem_e82_h.add_carrier(carrier['carrierID'], {
                                             'RackID':self.device_id,
                                             'SlotID':state['SlotID'],
                                             'CarrierID':carrier['carrierID']})
                        if self.last_carriers[idx]['carrierID']:
                            self.secsgem_e82_h.rm_carrier(self.last_carriers[idx]['carrierID'])

                if self.last_carriers[idx]['checked']!=carrier['checked']: #only for update panel chocp: 2021/6/22
                    carrier_change=True

        if self.last_lots != self.lots:
            carrier_change=True
            self.last_lots=copy.deepcopy(self.lots)

        # Mike: 2020/07/29
        #e82 rack update
        if carrier_change:
            RackInfo={'RackInfo':{'RackID':self.device_id, 'RackStates':states, 'RackLoc': self.loc}} # Mike: 2021/05/12
            #disable erack status update, chocp:2021/6/22
            #E82.report_event(self.secsgem_e82_h, E82.RackStatusUpdate, RackInfo)

            #sync e82
            ActiveRacks=E82.get_variables(self.secsgem_e82_h, 'ActiveRacks')
            ActiveRacks[self.device_id]=RackInfo
            E82.update_variables(self.secsgem_e82_h, {'ActiveRacks': ActiveRacks}) 

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

        
    def eRackInfoUpdate(self, info): #9/28
        print(info)
        if info['cmd'] == 'associate':
            data=info.get('data', '')
            print(data)
            try:
                lot_info=data.split(',') #ASECL use ','
                print(lot_info)
                if len(lot_info) == 1: #chi 2022/09/26
                    self.lots[info['port_idx']]['lotID']='{}'.format(lot_info[0])
                else:
                    self.lots[info['port_idx']]['lotID']='{}({})'.format(lot_info[0], len(lot_info)) if lot_info[0] else ''
                self.lots[info['port_idx']]['desc']=info.get('addition', [''])[0] #chocp 9/2
                self.lots[info['port_idx']]['stage']=info.get('addition', ['',''])[1]  #20231108
                print(self.lots[info['port_idx']]['lotID'], self.lots[info['port_idx']]['desc'])
            except:
                traceback.print_exc()
                pass
        elif info['cmd'] == 'assginlot':
            self.lots[info['port_idx']]['machine']=info.get('destport', '')

        elif info['cmd'] == 'infoupdate':
            self.lots[info['port_idx']]['lotID']=''
            self.lots[info['port_idx']]['stage']=''
            self.lots[info['port_idx']]['desc']=''
            self.lots[info['port_idx']]['custID']=''  #chi 2022/10/18 use LowerLevelErack for spil CY
            self.lots[info['port_idx']]['product']=''
            self.lots[info['port_idx']]['lottype']=''
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
            if 'desc' in info['data']:
                self.lots[info['port_idx']]['desc']=info['data']['desc']

        self.notify_panel()
	    
        


    #for thread
    def run(self):
        print('\n<start eRack thread:{}>\n'.format(self.device_id))
        self.eRackStatusUpdate() 
        while not self.thread_stop:
            try:
                if not self.connected:
                    retry=0
                    while(retry<5): #fix 5
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
                        raise ConnectWarning(self.device_id, self.ip, self.port)
     
                else:
                    try:
                        self.sock.settimeout(1) #from 10sec
                        raw_rx=self.sock.recv(2048).decode('utf-8')

                        if raw_rx == '':
                            print('SocketNullStringWarning')
                            raise SocketNullStringWarning(self.device_id)

                        begin=raw_rx.find('[')
                        end=raw_rx.find(']')

                        if  begin<0 or end<0:
                            print('SocketFormatWarning', begin, end)
                            raise SocketFormatWarning(self.device_id)

                        try:
                            query_payload=json.loads(raw_rx[begin:end+1])
                        except:
                            print('SocketFormatWarning', 'parse json error')
                            raise SocketFormatWarning(self.device_id)
                    #except socket.timeout:
                    except:

                        if self.syncing_time and (time.time()-self.syncing_time > 3):
                            raise LinkLostWarning(self.device_id)
                        else:
                            self.sync=False
                            continue

                    
                    self.erack_status='UP' 
                    self.sync=True
                    self.syncing_time=time.time()

                    datasets=[]
                    doc={'res':'no found', 'time':time.time()}
                    
                    for idx, port in enumerate(query_payload): #have 12 pcs
                        if idx > self.slot_num-1: #choc add 2021/11/9
                            break
                        #print(idx, port)
                        #if port['status'] == 'ERROR':
                        if port['status'] == 'ERROR' or port['status'] == 'DISABLE': #chocp:2021/5/31
                            self.carriers[idx]['status']='down'
                            self.lots[idx]['booked']=0 #chocp 7/15
                            self.lots[idx]['booked_for']='' #chocp 7/15
                        else:
                            self.carriers[idx]['status']='up'
                            self.carriers[idx]['carrierID']=port['carrierID'].strip() #chocp: 2021/9/1
                            self.carriers[idx]['checked']=port.get('checked', 1) #chocp:2021/5/31
                         
                            #port.get('check', True) ...........
                            if self.carriers[idx]['carrierID'] == '': #clear lot info
                                self.lots[idx]['lotID']=''
                                self.lots[idx]['stage']=''
                                self.lots[idx]['machine']=''
                                self.lots[idx]['desc']=''
                                    #self.lots[idx]['booked']=0 #chocp add 0917
                            else:
                                self.lots[idx]['booked']=0 #chocp 9/17
                                self.lots[idx]['booked_for']='' #chocp 10/3
                                    
                        if idx in range(self.begin, self.end): #chocp:2021/5/31, 12/15 fix
                                datasets.append({\
                                            'index':idx,\
                                            'lotID': self.lots[idx].get('lotID',''),\
                                            'stage':self.lots[idx].get('stage',''),\
                                            'machine':self.lots[idx].get('machine',''),\
                                            'desc':self.lots[idx].get('desc',''),\
                                            'booked':self.lots[idx].get('booked', 0),\
                                            'area_id':self.carriers[idx].get('area_id', ''),\
                                            'box_color':self.carriers[idx].get('box_color', 0), #chocp 2021/12/14
                                            })
                                doc={'res':'found', 'datasets':datasets, 'time':time.time()}
 
                    self.turn=(self.turn+1)%3
                    self.begin=4*self.turn
                    self.end=self.begin+4
                  
                    self.sock.send(bytearray(json.dumps(doc), encoding='utf-8')) #response remote query #chocp:2021/5/31
  
                    self.eRackStatusUpdate()

            except MyException as e: #ErackOffLineWarning
                #traceback.print_exc()
                self.sock.close()
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'
                output('AlarmSet', {'UnitType':e.alarm_set, 'UnitID':e.unit_id, 'Level':e.level, 'Code':e.code, 'SubCode':e.sub_code, 'CommandID':'', 'Cause':e.txt, 'Detail':'', 'Params': '', 'Description':''})  #chi 2022/08/16
                #output('AlarmSet', {'type':e.alarm_set, 'code':e.code, 'extend_code':e.sub_code, 'txt':e.txt})
                
                self.eRackStatusUpdate()
                time.sleep(1) #fix


            except: #ErackOffLineWarning
                traceback.print_exc()
                self.sock.close()
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'
                #output('AlarmSet', {'UnitType':e.alarm_set, 'UnitID':e.unit_id, 'Level':e.level, 'Code':e.code, 'SubCode':e.sub_code, 'CommandID':'', 'Cause':e.txt, 'Detail':'', 'Params': '', 'Description':''})
                #output('AlarmSet', {'type':'Error', 'code':30000, 'extend_code':self.device_id, 'txt':traceback.format_exc()})
                self.eRackStatusUpdate()
                time.sleep(1) #fix
                #self.secsgem_e82_h.set_alarm(self.error_code)

        else:
            print('\n<end eRack thread:{}>\n'.format(self.device_id))



class E82_ErackMgr(threading.Thread):
    __instance=None

    '''
    @staticmethod
    def getInstance():
        #print('call ErackMgr getInstance')
        if ErackMgr.__instance == None:
            ErackMgr(config=[])
        return ErackMgr.__instance
    '''

    def __init__(self, config=[]):
        self.eRacks={}
        self.erack_groups={}
        self.port_areas={}
        self.map_zones={}

        self.api_queue=queue.Queue()

        E82_ErackMgr.__instance=self
        threading.Thread.__init__(self)

    def add_listener(self, obj):
        for rack_no, h in self.eRacks.items():
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
            obj=self.api_queue.get() #if none, will hold
            eRacks_tmp={}
            erack_groups_tmp={}
            map_zones_tmp={}
            port_areas_tmp={}
            port_areas_revert_tmp={}

            def update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h):
                print('setting:', setting)

                if erack_groups_tmp.get(group_id):
                    erack_groups_tmp[setting['groupID']].append(h)
                else:
                    erack_groups_tmp[setting['groupID']]=[h]

                if map_zones_tmp.get(zone_id): #chocp fix 2021/10/30
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



            for idx, setting in enumerate(obj['config']):
                '''print('*******************************')
                print('get setting:', idx, setting)
                print('*******************************')'''

                rack_id=setting['eRackID']
                group_id=setting['groupID']
                zone_id=setting['zone']
                #h=self.eRacks.get(rack_id, 0)
                try:
                    h=self.eRacks.pop(rack_id)
                except:
                    h=0
                if h and h.is_alive():  #chi 05/10
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
                    #dynamic assign secsgem_e88_h before create eRackAdapter
                    secsgem_e82_h=E82_Host.getInstance(setting['zone'])
                    h=eRackAdapter(secsgem_e82_h, setting) #2023/11/3 bug
                    print("<<< new: {} >>>".format(rack_id))
                    eRacks_tmp[rack_id]=h
                    h.setDaemon(True)
                    h.start()
                    update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)
                # if h and h.is_alive():
                #     if setting['enable'] == 'yes' and h.ip == setting['ip'] and h.port == setting['port'] and h.idx == setting['idx']: #chocp add 2021/12/21
                #         eRacks_tmp[rack_id]=h
                #         #h_vehicle.update_params(setting)
                #         update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)
                #         print("<<< continue: {} >>>".format(rack_id))
                #         continue

                #     else:
                #         print("<<< stop: {} >>>".format(rack_id))
                #         h.thread_stop=True
                #     #time.sleep(5)

                # h=eRackAdapter(setting)

                # if setting['enable'] == 'yes':
                #     print("<<< new: {} >>>".format(rack_id))
                    
                #     h.setDaemon(True)
                #     h.start()
                #     update_groups_zones_areas(erack_groups_tmp, map_zones_tmp, port_areas_tmp, port_areas_revert_tmp, setting, h)
                # # 9/19
                # eRacks_tmp[rack_id]=h

               
            #need clear ....
            for erackid, h in self.eRacks.items():#2021/12/8
                h.thread_stop=True

            self.eRacks=eRacks_tmp
            self.map_zones=map_zones_tmp
            self.erack_groups=erack_groups_tmp #fix chocp 2021/112/7
            self.port_areas=port_areas_tmp
            self.port_areas_revert=port_areas_revert_tmp

         
            '''print(self.eRacks)
            print(self.map_zones)
            print(self.port_areas)'''

            


                
            


    

