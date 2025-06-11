# -*- coding: utf-8 -*-
import collections
import traceback
import threading
import time
import socket
import re

import os


import argparse

import semi.e88_equipment as E88 #can use singleton

import global_variables
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host #can use singleton
from global_variables import Erack
from global_variables import Vehicle
from global_variables import output
from global_variables import remotecmd_queue
import tools
from web_service_log import *
import json
import copy
from pprint import pformat

import queue
import alarms

#from web_service_log import * # K25  kelvinng 20240313

class GetSocketNullString():
    pass

class MyException(Exception):
    pass

class SettingsWarning(MyException):
    def __init__(self):
        pass


class ConnectWarning(MyException):
    def __init__(self, eRacKID, ip, port):
        self.alarm_set='Error'
        self.code=30001
        self.sub_code=eRacKID
        self.txt='{}, Rack connect:{}, port:{} fail'.format(eRacKID, ip, port)

class SocketNullStringWarning(MyException):
    def __init__(self, eRacKID, ):
        self.alarm_set='Error'
        self.code=30002
        self.sub_code=eRacKID
        self.txt='receive null string from socket'

class LinkLostWarning(MyException):
    def __init__(self, eRacKID, txt='linking timeout'):
        self.alarm_set='Error'
        self.code=30003
        self.sub_code=eRacKID
        self.txt='linking timeout'


class SocketFormatWarning(MyException):
    def __init__(self, eRacKID, txt='receive format error from socket'):
        self.alarm_set='Error'
        self.code=30004
        self.sub_code=eRacKID
        self.txt=txt


class ErackSyntaxWarning(MyException): #chocp add to local 2021/10/31
    def __init__(self, eRackID):
        self.alarm_set='Error'
        self.code=30005
        self.sub_code=eRackID
        self.txt='Erack syntax error:{}'.format(eRackID)

class GpmErackAdapter(threading.Thread):

    #def __init__(self, idx, name, mac, zoneID, func, loc, Transfers, Carriers, Zones, ip, port=5000, ZoneSize=12, ZoneType=1):
    def update_params(self, setting):
        self.idx=setting['idx']
        self.device_id=setting['eRackID']
        self.mac=setting['mac']
        self.groupID=setting['groupID'] if setting['groupID'] else setting['eRackID'] #9/26
        self.zone=setting['zone']
        self.link_zone=setting.get('link', '') #v8.24F for SJ
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

 

    def __init__(self, secsgem_e88_h,setting, Transfers, Carriers, Zones):
        self.E88_Transfers=Transfers
        self.E88_Carriers=Carriers
        self.E88_Zones=Zones
        self.secsgem_e88_h=secsgem_e88_h
        self.zonestate='auto'

        self.available=0 #9/26 chocp
        self.associated_slots=0
        self.error_slots=0
        self.water_level=''
        self.last_water_level=''

        self.update_params(setting)
        print(self.device_id, self.rows, self.columns, self.slot_num)

        self.thread_stop=False
        self.sock=0

        # 添加重連相關參數
        self.reconnect_count=0
        self.max_reconnect_attempts=120
        self.base_reconnect_delay=2
        self.max_reconnect_delay=30
        self.last_successful_connection=0

        self.alarm_table={20001:0, 20002:0, 20003:0, 20004:0, 20005:0, 20031:0, 20032:0, 20033:0, 20034:0, 20041:0, 20042:0, 20043:0, 20050:0}
        self.alarm_eRackWater={20052:0, 20053:0} 
        # self.water_level_table={'empty':20055, 'low':20054, 'medium':20056, 'high':20052, 'full':20053}
        self.water_level_table={'empty':alarms.ErackLevelEmptyWarning,
                                'low':alarms.ErackLevelLowWarning,
                                'medium':alarms.ErackLevelNormalWarning,
                                'high':alarms.ErackLevelHighWarning,
                                'full':alarms.ErackLevelFullWarning}

        self.E88_Zones.add(self.device_id)
        datasets={}
        datasets['ZoneSize']=self.zonesize
        datasets['ZoneCapacity']=self.zonesize
        datasets['ZoneType']=1 # 1: eRack 2: dummy loadport

        stk_unit={}
        for i in range(12): # Mike: 2021/09/22
            rack_id=self.device_id
            port_no=i+1

            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            if not res:
                raise ErackSyntaxWarning(rack_id)

            self.E88_Zones.ZoneMap[CarrierLoc]=Zones
            stk_unit[i+1]={'StockerUnitID':CarrierLoc, 'StockerUnitState':0, 'CarrierID':''}
        datasets['StockerUnit']=stk_unit
        self.E88_Zones.set(self.device_id, datasets)

        self.associate_queue=collections.deque()

        self.last_erack_status='None'
        

        self.connected=False
        self.sync=False

        self.syncing_time=0
        self.erack_status='DOWN'

        # GpmErackAdapter_logger.error("DOWN1")

        # self.all_erack_port={
        #     "TBD01-01":"","TBD01-02":"","TBD01-03":"","TBD01-04":"","TBD01-05":"","TBD01-06":"","TBD01-07":"","TBD01-08":"","TBD01-09":"","TBD01-10":"","TBD01-11":"","TBD01-12":"",\
        #     "TBD02-01":"","TBD02-02":"","TBD02-03":"","TBD02-04":"","TBD02-05":"","TBD02-06":"","TBD02-07":"","TBD02-08":"","TBD02-09":"","TBD02-10":"","TBD02-11":"","TBD02-12":"",\
        #     "TBD03-01":"","TBD03-02":"","TBD03-03":"","TBD03-04":"","TBD03-05":"","TBD03-06":"","TBD03-07":"","TBD03-08":"","TBD03-09":"","TBD03-10":"","TBD03-11":"","TBD03-12":"",\
        #     "TBD04-01":"","TBD04-02":"","TBD04-03":"","TBD04-04":"","TBD04-05":"","TBD04-06":"","TBD04-07":"","TBD04-08":"","TBD04-09":"","TBD04-10":"","TBD04-11":"","TBD02-12":"",\
        #     "TBE01-01":"","TBE01-02":"","TBE01-03":"","TBE01-04":"","TBE01-05":"","TBE01-06":"","TBE01-07":"","TBE01-08":"","TBE01-09":"","TBE01-10":"","TBE01-11":"","TBE01-12":"",\
        #     "TBE02-01":"","TBE02-02":"","TBE02-03":"","TBE02-04":"","TBE02-05":"","TBE02-06":"","TBE02-07":"","TBE02-08":"","TBE02-09":"","TBE02-10":"","TBE02-11":"","TBE02-12":"",\
        #     "TBE03-01":"","TBE03-02":"","TBE03-03":"","TBE03-04":"","TBE03-05":"","TBE03-06":"","TBE03-07":"","TBE03-08":"","TBE03-09":"","TBE03-10":"","TBE03-11":"","TBE03-12":"",\
        #     "TBE04-01":"","TBE04-02":"","TBE04-03":"","TBE04-04":"","TBE04-05":"","TBE04-06":"","TBE04-07":"","TBE04-08":"","TBE04-09":"","TBE04-10":"","TBE04-11":"","TBE02-12":"",\
        # }
        self.save_port_state={0:"",1:"",2:"",3:"",4:"",5:"",6:"",7:"",8:"",9:"",10:"",11:"",12:""}

        self.sendby=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        '''
        self.last_carriers=[\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':0, 'rack_row':1, 'rack_col':1, 'errorCode':'', 'create_time':0},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':1, 'rack_row':1, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':2, 'rack_row':1, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':3, 'rack_row':1, 'rack_col':4, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':4, 'rack_row':2, 'rack_col':1, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':5, 'rack_row':2, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':6, 'rack_row':2, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':7, 'rack_row':2, 'rack_col':4, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':8, 'rack_row':3, 'rack_col':1, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':9, 'rack_row':3, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':10, 'rack_row':3, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':11, 'rack_row':3, 'rack_col':4, 'errorCode':''}]
        self.carriers=[\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':0, 'rack_row':1, 'rack_col':1, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':1, 'rack_row':1, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':2, 'rack_row':1, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':3, 'rack_row':1, 'rack_col':4, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':4, 'rack_row':2, 'rack_col':1, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':5, 'rack_row':2, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':6, 'rack_row':2, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':7, 'rack_row':2, 'rack_col':4, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':8, 'rack_row':3, 'rack_col':1, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':9, 'rack_row':3, 'rack_col':2, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':10, 'rack_row':3, 'rack_col':3, 'errorCode':''},\
        {'checked':1, 'carrierID':'', 'status':'down', 'idx':11, 'rack_row':3, 'rack_col':4, 'errorCode':''}]
        self.read_carriers=[\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''},\
        {'carrierID':''}]
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

        #chocp fix 2021/119
        self.read_carriers=[]
        self.last_carriers=[]
        self.carriers=[]
        self.lots=[]

        for i in range(self.rows):
            for j in range(self.columns):
                self.read_carriers.append({'carrierID':''})
                self.lots.append({'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''})
                self.last_carriers.append({\
                'idx':self.columns*i+j,\
                'rack_row':i+1,\
                'rack_col':j+1,\
                'status':'down',\
                'state':'Disable',\
                'errorCode':'',\
                'errorTxt':'',\
                'checked':1,\
                'carrierID':'',\
                'lot':{'lotID':'', 'stage':'', 'machine':'', 'desc':'', 'booked':0, 'booked_for':''}}) #lot info for eRack display
                


                self.carriers.append({\
                'idx':self.columns*i+j,\
                'rack_row':i+1,\
                'rack_col':j+1,\
                'status':'down',\
                'state':'Disable',\
                'errorCode':'',\
                'errorTxt':'',\
                'checked':1,\
                'carrierID':'',\
                'lot':self.lots[self.columns*i+j]}) #lot info for eRack display
                

        '''
        for carrier in self.carriers:
            self.change_state_disable(carrier)
        '''

        #desc for target
        #add book_for 202110/2

        self.turn=0 #every 3 echo, update 1 relative lot info
        self.begin=0
        self.end=0

        self.heart_beat=0
        threading.Thread.__init__(self)


    def notify_panel(self):
        
        
        
        
        n=0

        self.available=0
        self.associated_slots=0
        self.error_slots=0
        #print('erack <{}>'.format(self.carriers))
        for idx, carrier in enumerate(self.carriers):
            if carrier['state'] == 'Empty':
                self.available+=1

            if carrier['state'] == 'Associated':
                self.associated_slots+=1

            if carrier['state'] == 'Error':
                self.error_slots+=1
        #print('notify_panel:', self.carriers)

        # update_erack_logger.info("new eRackStatusUpdate:{}".format({
        #     'idx':self.idx,
        #     'DeviceID':self.device_id,
        #     'MAC':self.mac,
        #     'IP':self.ip,
        #     'Status':self.erack_status,
        #     'carriers':self.carriers,
        #     'SlotNum':self.slot_num,
        #     'StockNum':self.slot_num-self.available,
        #     'AssociatedNum':self.associated_slots,
        #     'ErrorNum':self.error_slots
        #     }))
        # action_logger.info("new eRackStatusUpdate:{}".format({
        #     'idx':self.idx,
        #     'DeviceID':self.device_id,
        #     'MAC':self.mac,
        #     'IP':self.ip,
        #     'Status':self.erack_status,
        #     'carriers':self.carriers,
        #     'SlotNum':self.slot_num,
        #     'StockNum':self.slot_num-self.available,
        #     'AssociatedNum':self.associated_slots,
        #     'ErrorNum':self.error_slots
        #     }))
        
        self.send_ui_last_data={
            'idx':self.idx,
            'DeviceID':self.device_id,
            'MAC':self.mac,
            'IP':self.ip,
            'Status':self.erack_status,
            'carriers':self.carriers,
            'SlotNum':self.slot_num,
            'StockNum':self.slot_num-self.available,
            'AssociatedNum':self.associated_slots,
            'ErrorNum':self.error_slots
            }
        
        
        action_logger.debug("eRackStatusUpdate:{}".format({
            'idx':self.idx,
            'DeviceID':self.device_id,
            'MAC':self.mac,
            'IP':self.ip,
            'Status':self.erack_status,
            'carriers':self.carriers,
            'SlotNum':self.slot_num,
            'StockNum':self.slot_num-self.available,
            'AssociatedNum':self.associated_slots,
            'ErrorNum':self.error_slots
            }))
        output('eRackStatusUpdate', {
            'idx':self.idx,
            'DeviceID':self.device_id,
            'MAC':self.mac,
            'IP':self.ip,
            'Status':self.erack_status,
            'carriers':self.carriers,
            'SlotNum':self.slot_num,
            'StockNum':self.slot_num-self.available,
            'AssociatedNum':self.associated_slots,
            'ErrorNum':self.error_slots
            })
    

        if not self.available and not self.alarm_eRackWater[20053]:
            #alarm full
            self.E88_Zones.Data[self.device_id].zone_alarm_set(20053, True)
            self.alarm_eRackWater[20053]=1
        elif self.available and self.slot_num-self.available > self.slot_num*global_variables.WaterLevel.get('waterLevelHigh', 80)/100 and not self.alarm_eRackWater[20052]:
                if self.alarm_eRackWater[20053]:
                    #reset water full
                    self.E88_Zones.Data[self.device_id].zone_alarm_set(20053, False)
                    self.alarm_eRackWater[20053]=0
                
                #alarm high level
                self.E88_Zones.Data[self.device_id].zone_alarm_set(20052, True)
                self.alarm_eRackWater[20052]=1

        elif self.available and self.slot_num-self.available > self.slot_num*global_variables.WaterLevel.get('waterLevelHigh', 80)/100:
            if self.alarm_eRackWater[20053]:
                #reset high level
                self.E88_Zones.Data[self.device_id].zone_alarm_set(20053, False)
                self.alarm_eRackWater[20053]=0           
        elif self.available and self.slot_num-self.available <= self.slot_num*global_variables.WaterLevel.get('waterLevelHigh', 80)/100:
            if self.alarm_eRackWater[20052] or self.alarm_eRackWater[20053]:
                if self.alarm_eRackWater[20052]:
                    #reset water full
                    self.E88_Zones.Data[self.device_id].zone_alarm_set(20052, False)
                    self.alarm_eRackWater[20052]=0
                if self.alarm_eRackWater[20053]:
                    #reset high level
                    self.E88_Zones.Data[self.device_id].zone_alarm_set(20053, False)
                    self.alarm_eRackWater[20053]=0

        pass
        

    def set_machine_info(self, port_no, dest,vehicle_id='',**kwargs):
        try:
           
            clear_carrierID=""
            
            if kwargs:
                if "carrierID" in kwargs:
                    
                    clear_carrierID=kwargs.get("carrierID","")

                    
            
                    if clear_carrierID == self.carriers[port_no-1]['carrierID']:
                        
                        self.carriers[port_no-1]['lot']['machine']=dest
                        self.change_state(self.carriers[port_no-1], 'set_machine_info', {'machine':dest})

            else:
                
                print(self.carriers[port_no-1])
                self.carriers[port_no-1]['lot']['machine']=dest
                self.change_state(self.carriers[port_no-1], 'set_machine_info', {'machine':dest})
            
            
        except:
            pass
        #self.notify_panel()

    def set_booked_flag(self, port_no, flag=False, vehicle_id='', source=''):
        #print('set_booked_flag', port_no, flag)
        if flag:
            self.change_state(self.carriers[port_no-1], 'set_booked_flag', {'booked':1, 'booked_for':vehicle_id, 'desc':vehicle_id})
            
        else:
            self.change_state(self.carriers[port_no-1], 'reset_booked_flag', {'booked':0, 'booked_for':'', 'desc':''})


    def on_notify(self, event, data):
        #print('eRack {} get {}, data {}'.format(self.device_id, event, data))
        if event == 'acquire_start_evt' or event == 'deposit_start_evt':
            #self.sendby[0]=1
            pass
        elif event == 'acquire_complete_evt' or event == 'deposit_complete_evt':
            #self.sendby[0]=1
            pass


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


    #chocp 2
    def change_state_disable(self, carrier):
        #print('change_state_disable', self.device_id, carrier['idx'])

        carrier['status']='down'
        carrier['state']='Disable'
 
        carrier['carrierID']=''
        carrier['checked']=1

        carrier['lot']['lotID']=''
        carrier['lot']['stage']=''
        carrier['lot']['machine']=''
        carrier['lot']['desc']=''
        carrier['lot']['booked']=0
        carrier['lot']['booked_for']=''

        idx=carrier['idx']
        rack_id=self.device_id
        port_no=idx+1
        now_port='{}-{:02d}'.format(self.device_id,port_no)
        
        self.notify_panel()

    def change_state_empty(self, carrier):
        #print('change_state_empty', self.device_id, carrier['idx'])

        carrier['status']='up'
        carrier['state']='Empty'
        carrier['errorCode']=''
        carrier['carrierID']=''
        carrier['checked']=1

        carrier['lot']['lotID']=''
        carrier['lot']['stage']=''
        carrier['lot']['machine']=''
        carrier['lot']['desc']=''
        carrier['lot']['booked']=0
        carrier['lot']['booked_for']=''

        idx=carrier['idx']
        rack_id=self.device_id
        port_no=idx+1
        # now_port='{}-{:02d}'.format(self.device_id,port_no)
        self.save_port_state[idx]=""
        
        

        res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
        if not res:
            raise ErackSyntaxWarning(rack_id)

        self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['StockerUnitState']=1
        self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['CarrierID']=carrier['carrierID']
        
        if CarrierLoc in self.E88_Carriers.Mapping:
            print(CarrierLoc, self.E88_Carriers.Mapping[CarrierLoc])
            if self.E88_Carriers.Mapping[CarrierLoc] in self.E88_Carriers.Data:
                if self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].CarrierState == 3:
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.remove()
                else:
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.kill_carrier()
                    self.E88_Carriers.delete(self.E88_Carriers.Mapping[CarrierLoc])
                    self.E88_Zones.Data[self.device_id].capacity_increase()
                if CarrierLoc in self.E88_Carriers.Mapping:
                    del self.E88_Carriers.Mapping[CarrierLoc]
                self.read_carriers[idx]['carrierID']=''

        # if self.alarm_table[20002]: #if carrier check by operator,then launch movin event
        #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20002, False)
        #     self.alarm_table[20002]=0

        for idx, val in enumerate(self.alarm_table):
            if self.alarm_table[val]: #if carrier check by operator,then launch movin event
                self.E88_Zones.Data[self.device_id].zone_alarm_set(val, False)
                self.alarm_table[val]=0

        self.notify_panel()

    def change_state_booked(self, carrier, data):
        #print('change_state_booked', self.device_id, carrier['idx'])

        carrier['state']='Booked'

        carrier['lot']['desc']=data.get('desc', '')
        carrier['lot']['booked']=data.get('booked', 0)
        carrier['lot']['booked_for']=data.get('booked_for', '')
        idx=carrier['idx']
        rack_id=self.device_id
        port_no=idx+1
        now_port='{}-{:02d}'.format(self.device_id,port_no)
        
        self.notify_panel()


    def change_state_identified(self, carrier, port):
        carrierID= carrier['carrierID']
        
        carrier['status']='up'
        carrier['state']='Identified'
        carrier['errorCode']=''
        carrier['carrierID']=port.get('carrierID', carrierID)
        carrier['checked']=carrier.get('checked', 1)

        carrier['lot']['lotID']=''
        carrier['lot']['stage']=''
        carrier['lot']['machine']=''
        carrier['lot']['lotID']=port.get('assyLotList','')
        carrier['lot']['stage']=''
        carrier['lot']['machine']=port.get('entity','')

        carrier['lot']['desc']=port.get('message','')
        carrier['lot']['booked']=0
        carrier['lot']['booked_for']=''

        idx=carrier['idx']
        rack_id=self.device_id
        port_no=idx+1
        now_port='{}-{:02d}'.format(self.device_id,port_no)
       
        
        if port.get('status') == 'NG':
            if port['send_associated_status']:
                self.change_state_error(carrier, port)
                return

        res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
        if not res:
            raise ErackSyntaxWarning(rack_id)

        self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['StockerUnitState']=2
        self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['CarrierID']=carrier['carrierID']
        if carrier['carrierID'] not in self.E88_Carriers.Data:
            if CarrierLoc not in self.E88_Carriers.Mapping:
                self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                self.read_carriers[idx]['carrierID']=carrier['carrierID']
                self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                datasets={}
                datasets['CarrierID']=self.E88_Carriers.Mapping[CarrierLoc]
                datasets['CarrierLoc']=CarrierLoc
                datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                datasets['CarrierZoneName']=self.device_id
                datasets['PortType']='BP'
                self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 0)
                self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                self.E88_Zones.Data[self.device_id].capacity_decrease()
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
                datasets['CarrierZoneName']=self.device_id
                datasets['PortType']='BP'
                self.E88_Carriers.mod(old_carrier_id, self.E88_Carriers.Mapping[CarrierLoc])
                self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
            # if self.alarm_table[20002]: #if carrier check by operator,then launch movin event
            #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20002, False)
            #     self.alarm_table[20002]=0
            for idx, val in enumerate(self.alarm_table):
                if self.alarm_table[val]: #if carrier check by operator,then launch movin event
                    self.E88_Zones.Data[self.device_id].zone_alarm_set(val, False)
                    self.alarm_table[val]=0
        else:
            if CarrierLoc not in self.E88_Carriers.Mapping:
                if self.E88_Zones.Data[self.E88_Carriers.Data[carrier['carrierID']].CarrierZoneName].ZoneState == 1: # Duplicate
                    FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                    self.read_carriers[idx]['carrierID']=FAILUREID
                    self.E88_Carriers.Mapping[CarrierLoc]=FAILUREID
                    self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                    datasets={}
                    datasets['CarrierID']=carrier['carrierID']
                    datasets['CarrierLoc']=CarrierLoc
                    datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                    datasets['CarrierZoneName']=self.device_id
                    datasets['PortType']='BP'
                    self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 2)
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                    self.E88_Zones.Data[self.device_id].capacity_decrease()
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.transfer()
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_out()
                    # if not self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                    #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20002, True)
                    #     self.alarm_table[20002]=1
                    # if not self.alarm_table[20031]: #if carrier check by operator,then launch movin event
                    #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20031, True)
                    #     self.alarm_table[20031]=1
                    # if not self.alarm_table[20032]: #if carrier check by operator,then launch movin event
                    #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20032, True)
                    #     self.alarm_table[20032]=1
                    for idx, val in enumerate(self.alarm_table):
                        if self.alarm_table[val]: #if carrier check by operator,then launch movin event
                            self.E88_Zones.Data[self.device_id].zone_alarm_set(val, True)
                            self.alarm_table[val]=1
                else:
                    FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                    old_carrier_loc=self.E88_Carriers.Data[carrier['carrierID']].CarrierLoc
                    self.E88_Carriers.Mapping[old_carrier_loc]=FAILUREID
                    self.E88_Carriers.mod(carrier['carrierID'], FAILUREID)
                    datasets={}
                    datasets['CarrierID']=FAILUREID
                    self.E88_Carriers.set(FAILUREID, datasets)
                    self.E88_Carriers.Data[FAILUREID].State.transfer()
                    self.E88_Carriers.Data[FAILUREID].State.wait_o
                    self.E88_Carriers.Mapping[CarrierLoc]=carrier['carrierID']
                    self.read_carriers[idx]['carrierID']=carrier['carrierID']
                    self.E88_Carriers.add(self.E88_Carriers.Mapping[CarrierLoc])
                    datasets={}
                    datasets['CarrierID']=self.E88_Carriers.Mapping[CarrierLoc]
                    datasets['CarrierLoc']=CarrierLoc
                    datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                    datasets['CarrierZoneName']=self.device_id
                    datasets['PortType']='BP'
                    self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].id_read(self.E88_Carriers.Mapping[CarrierLoc], 0)
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.wait_in()
                    self.E88_Zones.Data[self.device_id].capacity_decrease()
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.transfer()
                    self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.store()
                pass
            else: # Duplicate
                old_carrier_id=self.E88_Carriers.Mapping[CarrierLoc]#kelvin 2024/03/08
                # FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                # self.read_carriers[idx]['carrierID']=FAILUREID
                # self.E88_Carriers.Mapping[CarrierLoc]=FAILUREID
                self.read_carriers[idx]['carrierID']=old_carrier_id
                self.E88_Carriers.Mapping[CarrierLoc]=old_carrier_id
                datasets={}
                datasets['CarrierID']=carrier['carrierID']
                datasets['CarrierLoc']=CarrierLoc
                datasets['CarrierIDRead']=self.E88_Carriers.Mapping[CarrierLoc]
                datasets['CarrierZoneName']=self.device_id
                datasets['PortType']='BP'
                self.E88_Carriers.mod(old_carrier_id, self.E88_Carriers.Mapping[CarrierLoc])
                self.E88_Carriers.set(self.E88_Carriers.Mapping[CarrierLoc], datasets)
                # if not self.alarm_table[20002]: #if carrier check by operator,then launch movin event
                #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20002, True)
                #     self.alarm_table[20002]=1
                # if not self.alarm_table[20031]: #if carrier check by operator,then launch movin event
                #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20031, True)
                #     self.alarm_table[20031]=1
                # if not self.alarm_table[20032]: #if carrier check by operator,then launch movin event
                #     self.E88_Zones.Data[self.device_id].zone_alarm_set(20032, True)
                #     self.alarm_table[20032]=1
                for idx, val in enumerate(self.alarm_table):
                    if self.alarm_table[val]: #if carrier check by operator,then launch movin event
                        self.E88_Zones.Data[self.device_id].zone_alarm_set(val, True)
                        self.alarm_table[val]=1
        self.notify_panel()

    def change_state_error(self, carrier, data):
        port_id=carrier.get("idx")
        port_state=carrier.get("state")
        # carrier_id=carrier.get("carrierID")
        if self.save_port_state[port_id]!=port_state:
            
            self.save_port_state[port_id]=port_state
            carrier['state']='Error'

            carrier['status']='down'
            carrier['errorCode']=data.get('errorCode', '') #0001
            carrier['LotID']=data.get('assyLotList', '') #0001
            carrier['machine']=data.get('entity', '') #0001
            
            if data.get('errorTxt'):
                carrier['errorCode']=data.get('errorTxt')
                print('errorCode:<{}>'.format(carrier['errorCode']))

            elif carrier['errorCode'] == '20031':
                carrier['errorTxt']='ID READ FAIL'

            elif carrier['errorCode'] == '20032':
                carrier['errorTxt']='ERROR SKEW'

            elif carrier['errorCode'] == '20033':
                carrier['errorTxt']='IR ERROR'
            
            elif carrier['errorCode'] == '20034':
                carrier['errorTxt']='SLOT OTHER FAIL'

            elif carrier['errorCode'] == '20041':
                carrier['errorTxt']='QUERY DATA NG'

            elif carrier['errorCode'] == '20042':
                carrier['errorTxt']='QUERY DATA FAIL'

            elif carrier['errorCode'] == '20043':
                carrier['errorTxt']='QUERY DATA TIMEOUT'

            elif carrier['errorCode'] == '20050':
                carrier['errorTxt']='TRANSFER FAIL'

            elif carrier['errorCode']!='':
                carrier['errorTxt']=data.get('message', '')
            else:
                carrier['errorTxt']='UNKNOW'

            if carrier['carrierID'] == '':
                carrier['carrierID']=carrier['errorTxt']
            
            idx=carrier['idx']
            rack_id=self.device_id
            port_no=idx+1
            
            res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
            
            if not res:
                
                raise ErackSyntaxWarning(rack_id)

            self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['StockerUnitState']=3
            self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['CarrierID']=carrier['carrierID']
            #print('CarrierLoc <{}>, E88_Carriers <{}>'.format(CarrierLoc, self.E88_Carriers.Mapping))
            if CarrierLoc not in self.E88_Carriers.Mapping: #if carrier check by operator,then launch movin event
                FAILUREID=E88.FailureIDGEN(CarrierLoc, carrier['carrierID'])
                self.read_carriers[idx]['carrierID']=FAILUREID
                self.E88_Carriers.Mapping[CarrierLoc]=self.read_carriers[idx]['carrierID']
                self.E88_Carriers.add(FAILUREID)
                datasets={}
                datasets['CarrierID']=FAILUREID
                datasets['CarrierLoc']=CarrierLoc
                datasets['CarrierIDRead']=carrier['carrierID']
                datasets['CarrierZoneName']=self.device_id
                datasets['PortType']='BP'
                self.E88_Carriers.set(FAILUREID, datasets)
                self.E88_Carriers.Data[FAILUREID].id_read(FAILUREID, 1)
                self.E88_Carriers.Data[FAILUREID].State.wait_in()
                self.E88_Carriers.Data[FAILUREID].State.transfer()
                self.E88_Carriers.Data[FAILUREID].State.wait_out()
            
            

            #print('alarm table: <{}>'.format(self.alarm_table))

            datasets={}
            datasets['CarrierID']=carrier['carrierID']
            datasets['CarrierLoc']=CarrierLoc
            datasets['CarrierIDRead']=carrier['carrierID']
            datasets['CarrierZoneName']=self.device_id
            datasets['PortType']='BP'
            #print('datasets: <{}>'.format(datasets))

            

            if carrier['errorCode']:
                try:
                    codenum=int(carrier['errorCode'])
                    if codenum not in [20050]:
                        
                        self.E88_Zones.Data[self.device_id].zone_alarm_set(codenum, True, datasets)
                        self.alarm_table[int(codenum)]=1 
                except ValueError:
                    pass
                    # GpmErackAdapter_logger.error("Invalid error code:{}".format(carrier['errorCode']))
                 
                    
                
            #     if self.all_erack_port.get(datasets.get("CarrierLoc",""),"") != "error":
                    
            #     #print('error code: <{}> on device:<{}>'.format(carrier['errorCode'], self.device_id))
            #         codenum=int(carrier['errorCode'])
            #         if not self.alarm_table[codenum]: #if carrier check by operator,then launch movin event
            #             self.E88_Zones.Data[self.device_id].zone_alarm_set(codenum, True, datasets)
            #             self.alarm_table[codenum]=1 
            # else:
            #     if not self.alarm_table[20002]: #if carrier check by operator,then launch movin event
            #         if self.all_erack_port.get(datasets.get("CarrierLoc",""),"") != "error":
            #             self.E88_Zones.Data[self.device_id].zone_alarm_set(20002, True)
            #             self.alarm_table[20002]=1
            
            self.notify_panel()

    def change_state_associated(self, carrier, data):

        if data.get('status') == 'NG':
            
            carrierID= carrier['carrierID']
            carrier['status']='up'
            carrier['state']='Identified'
            carrier['errorCode']=''
            carrier['carrierID']=data.get('carrierID', carrierID)
            carrier['checked']=carrier.get('checked', 1)

            carrier['lot']['lotID']=''
            carrier['lot']['stage']=''
            carrier['lot']['machine']=''
            
            carrier['lot']['lotID']=data.get('assyLotList','')
            carrier['lot']['stage']=''
            carrier['lot']['machine']=data.get('entity','')

            carrier['lot']['desc']=data.get('message','')
            carrier['lot']['booked']=0
            carrier['lot']['booked_for']=''

            idx=carrier['idx']
            rack_id=self.device_id
            port_no=idx+1
        
            self.change_state_error(carrier, data)
            return

        carrier['state']='Associated'
        carrier['lot']['booked']=0
        carrier['lot']['booked_for']=''
        idx=carrier['idx']
        rack_id=self.device_id
        port_no=idx+1
        now_port='{}-{:02d}'.format(self.device_id,port_no)
        

        if 'assyLotList' in data:
            carrier['lot']['lotID']=data['assyLotList']

        if 'entity' in data:
            carrier['lot']['machine']=data['entity']

        if 'message' in data:
            carrier['lot']['desc']=data['message']

        if 'status' in data:
            print(data)

        

        self.notify_panel()

    def change_state_preDispatch(self, carrier, data):
        #print('change_state_preDispatch', self.device_id, carrier['idx'])

        carrier['state']='PreDispatch'

        carrier['lot']['machine']=data.get('machine', '')

        self.notify_panel()

    def change_state_dispatch(self, carrier, data):
        
        #print('change_state_dispatch', self.device_id, carrier['idx'])
        print(data)

        carrier['state']='Dispatch'

        carrier['lot']['machine']=data.get('machine', '')

        self.notify_panel()

    def change_state(self, carrier, event, data):
        
        #{"status":"EMPTY"/IDENTIFIED/"ASSOCIATED"/
        # "errorCode":"RFID FAIL"
        # "carrierID":"87654321"
        # "checked":
        if event == 'port_sync_evt' and data['status'] == 'EMPTY':
            if carrier['state']!='Empty' and carrier['state']!='Booked':
                self.change_state_empty(carrier)
            
        elif event == 'port_sync_evt' and data['status'] == 'ERROR':
            #print('<<<error>>> event <{}>, carrier state <{}>'.format(event, carrier['state']))
            if carrier['state']!='Error':
                #print('<<<11>>> carrier <{}>, data <{}>'.format(carrier, data))
                self.change_state_error(carrier, data)
            else:
                #print('<<<22>>> carrier <{}>, data <{}>'.format(carrier, data))
                self.change_state_error(carrier, data)

        elif event == 'port_sync_evt' and data['status'] == 'IDENTIFIED':
            #print('####<<<<Here>>>>#### event is <{}>, Carrier is <{}><{}>'.format(event, data['status'], carrier['state']))
            if carrier['state'] == 'Disable' or carrier['state'] == 'Empty' or carrier['state'] == 'Booked': #chocp 2022/6/2
                
                self.change_state_identified(carrier, data)

        elif event == 'port_sync_evt' and data['status'] in ["IDENTIFIED","ASSOCIATED"]:
            #print('####<<<<Here>>>>#### event is <{}>, Carrier is <{}><{}>'.format(event, data['status'], carrier['state']))
            if carrier['state'] == 'Disable' or carrier['state'] == 'Empty' or carrier['state'] == 'Booked': #chocp 2022/6/2
               
                self.change_state_identified(carrier, data)
                self.change_state_identified(carrier, data)

        elif event == 'port_sync_evt' and data['status'] == 'DISABLE':
            if carrier['state']!='Disable':
                carrier['state']='Disable'
                carrier['status']='down'
                self.notify_panel()

        elif event == 'host_associate_cmd':
            
            if carrier['state'] == 'Identified' or carrier['state'] == 'Associated':
                if(data['send_associated_status']):
                    self.change_state_associated(carrier, data)
                else:
                    self.change_state_identified(carrier, data)
                #self.change_state_associated(carrier, data)

        elif event == 'host_error_evt': #query fail
            self.change_state_error(carrier, data)

        elif event == 'host_reset_evt': #query fail
            carrier['state']='Disable'
            carrier['status']='down'
            carrier['errorCode']=data.get('errorCode', '') #0001
            carrier['errorTxt']=data.get('errorTxt', '') #....
            carrier['checked']=1
            carrier['carrierID']=''


        elif event == 'user_edit_cmd':
            if carrier['state'] == 'Associated':
                self.change_state_preDispatch(carrier, data)

        #elif event == 'host_dispatch_cmd':
        #    self.change_state_dispatch(carrier, data)

        elif event == 'set_booked_flag':
            if carrier['state'] == 'Empty':
                self.change_state_booked(carrier, data)

        elif event == 'reset_booked_flag':
            self.change_state_empty(carrier)

        elif event == 'set_machine_info':
            
            
            if carrier['state'] == 'Identified' or carrier['state'] == 'Associated' or carrier['state'] == 'predispatch' or carrier['state'] == 'PreDispatch':
                self.change_state_dispatch(carrier, data)
            elif(carrier['state'] == 'Dispatch'):
                self.change_state_identified(carrier, data)
        else:
            print('\n<event:{}>\n'.format(event))
            print(carrier['rack_row'], carrier['rack_col'], event, data)

                


    #for thread
    def run(self):
        print('\n<start eRack thread:{}>\n'.format(self.device_id))
        
        E88_com_state=''
        last_E88_com_state=''
        while not self.thread_stop:
            self.heart_beat=time.time()
            try:
                time.sleep(0.5)
                if not self.connected:
                    # GpmErackAdapter_logger.info("{},Erack start connecting...".format(self.device_id))
                    if not self.alarm_table[20004]: #if carrier check by operator,then launch movin event
                        self.E88_Zones.Data[self.device_id].zone_alarm_set(20004, True)
                        self.alarm_table[20004]=1
                    self.E88_Zones.Data[self.device_id].ZoneState=2
                    
                    # 使用新的重連機制
                    success = False
                    while self.reconnect_count < self.max_reconnect_attempts and not self.thread_stop:
                        if self.attempt_reconnection():
                            success = True
                            break
                    
                    if not success and not self.thread_stop:
                        print('[{}] 達到最大重連次數，拋出連接異常'.format(self.device_id))
                        raise ConnectWarning(self.device_id, self.ip, self.port)


                else:
                    if self.alarm_table[20004]: #if carrier check by operator,then launch movin event
                        self.E88_Zones.Data[self.device_id].zone_alarm_set(20004, False)
                        self.alarm_table[20004]=0
                    self.E88_Zones.Data[self.device_id].ZoneState=1
                    try:
                        self.sock.settimeout(5) #from 10sec
                        raw_rx=self.sock.recv(2048).decode('utf-8')
                        #print('-------------------->'.format(raw_rx))
                        if raw_rx == '':
                            
                            # print('SocketNullStringWarning')
                            # raise SocketNullStringWarning(self.device_id)
                            raise GetSocketNullString()

                        begin=raw_rx.find('[')
                        end=raw_rx.find(']')

                        if len(raw_rx) != len(raw_rx[begin:end+1]):
                            print('raw_rx len diff:', len(raw_rx), len(raw_rx[begin:end+1]))

                        if  begin<0 or end<0:
                            print('SocketFormatWarning', begin, end)
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)

                        try:
                            query_payload=json.loads(raw_rx[begin:end+1]) #avoid two echo
                            #query_payload=json.loads(raw_rx) #?????????????? chocp
                            # print(query_payload)
                        except:
                            print('SocketFormatWarning', 'parse json error:', raw_rx) #will make no respond 
                            # raise SocketFormatWarning()
                            raise alarms.SocketFormatWarning(self.device_id, handler=self.secsgem_e88_h)
                    #except socket.timeout:
                    except GetSocketNullString:
                        # GpmErackAdapter_logger.error("{},Erack Offline in except SocketNullStringWarning".format(self.device_id))
                        #break
                        # raise LinkLostWarning(self.device_id)
                        raise alarms.SocketNullStringWarning(self.device_id, handler=self.secsgem_e88_h)
                    except:
                        traceback.print_exc()
                        if self.syncing_time and (time.time()-self.syncing_time > 10): #chocp 2021/10/4
                            raise alarms.LinkLostWarning(self.device_id, handler=self.secsgem_e88_h)
                        else:
                            self.sync=False
                            time.sleep(1)
                            continue
                        
                        
                        

                        # if self.syncing_time and (time.time()-self.syncing_time > 10): #chocp 2021/10/4
                            
                        #     # GpmErackAdapter_logger.error("{},except2".format(self.device_id))

                        #     raise LinkLostWarning(self.device_id)
                        # else:
                        #     # GpmErackAdapter_logger.error("{},except3".format(self.device_id))

                        #     self.sync=False
                        #     continue
                    

                    self.erack_status='UP'
                    self.sync=True
                    self.syncing_time=time.time()


                    if True: #for eRack
                        datasets=[]
                        doc={'res':'no found', 'datasets':'','time':time.time()}

                        for idx, port in enumerate(query_payload): #have 12 pcs
                            if idx > self.slot_num-1: #choc add 2021/11/9
                                break

                            #for port update and respond data
                            # action_logger.info("self.carriers[idx]:{}".format(self.carriers[idx]))
                            # action_logger.info("port:{}".format(port))
                            self.change_state(self.carriers[idx], 'port_sync_evt', port)
   
                            if idx in range(self.begin, self.end):
                                # print(self.carriers[idx])

                                '''datasets.append({\
                                            'index':idx,\
                                            'lotID': self.carriers[idx]['lot'].get('lotID',''),\
                                            'stage': self.carriers[idx]['lot'].get('stage',''),\
                                            'machine':self.carriers[idx]['lot'].get('machine',''),\
                                            'desc':self.carriers[idx]['lot'].get('desc',''),\
                                            'state':self.carriers[idx].get('state', 'Error'),\
                                            })'''

                                datasets.append({\
                                            'index':idx,\
                                            'lotID': self.carriers[idx]['lot'].get('lotID',''),\
                                            'machine':self.carriers[idx]['lot'].get('machine',''),\
                                            'desc':self.carriers[idx]['lot'].get('desc',''),\
                                            'state':self.carriers[idx].get('state', 'Error'),\
                                            'stage':self.carriers[idx].get('stage', ''),\
                                            'errorCode':self.carriers[idx].get('errorCode', '')
                                            })
                                # datasets.append({\
                                #             'index':idx,\
                                #             'lotID': self.carriers[idx]['lot'].get('lotID',''),\
                                #             'machine':'',\
                                #             'desc':'',\
                                #             'state':self.carriers[idx].get('state', 'Error'),\
                                #             'errorCode':''
                                #             })
                                doc={'res':'found', 'datasets':datasets, 'time':time.time()}

                        self.turn=(self.turn+1)%3
                        self.begin=4*self.turn
                        self.end=self.begin+4
                        #print(doc)
                        # print("send9============================================")
                        self.sock.send(bytearray(json.dumps(doc), encoding='utf-8')) #response remote query #chocp:2021/5/31

                    try:
                        E88_com_state=self.secsgem_e88_h.communicationState.current
                        if E88_com_state != last_E88_com_state:
                            last_E88_com_state=E88_com_state

                    except Exception as e:
                        print(e)

            except MyException as e: #ErackOffLineWarning
                # GpmErackAdapter_logger.error("ErackOffLineWarning")
                # GpmErackAdapter_logger.error("MyException:{}".format(e))
                print('[{}] MyException異常: {}'.format(self.device_id, e.txt))
                
                # 關閉連接並重置狀態
                try:
                    self.sock.close()
                except:
                    pass
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'

                output('AlarmSet', {'type':e.alarm_set, 'code':e.code, 'extend_code':e.sub_code, 'txt':e.txt})

                if self.last_erack_status!=self.erack_status:
                    self.notify_panel()
                    self.last_erack_status=self.erack_status

                # 檢查是否需要強制重連
                if time.time() - self.last_successful_connection > 300:  # 5分鐘無成功連接
                    print('[{}] 長時間無成功連接，執行張制重連'.format(self.device_id))
                    self.force_reconnect()
                else:
                    time.sleep(1)

            except: #ErackOffLineWarning
                print('[{}] 一般異常:'.format(self.device_id))
                traceback.print_exc()
                
                # 關閉連接並重置狀態
                try:
                    self.sock.close()
                except:
                    pass
                self.connected=False
                self.sync=False
                self.erack_status='DOWN'

                output('AlarmSet', {'type':'Error', 'code':30000, 'extend_code':self.device_id, 'txt':traceback.format_exc()})

                if self.last_erack_status!=self.erack_status:
                    self.notify_panel()
                    self.last_erack_status=self.erack_status

                # 檢查是否需要強制重連
                if time.time() - self.last_successful_connection > 300:  # 5分鐘無成功連接
                    print('[{}] 長時間無成功連接，執行強制重連'.format(self.device_id))
                    self.force_reconnect()
                else:
                    time.sleep(1)
                #self.secsgem_e82_h.set_alarm(self.error_code)
        else:
            self.E88_Zones.Data[self.device_id].ZoneState=0

            for idx, carrier in enumerate(self.carriers): # Mike: 2021/12/01
                rack_id=self.device_id
                port_no=idx+1
                CarrierLoc=''

                res, CarrierLoc=tools.print_rackport_format(rack_id, port_no, self.rows, self.columns)
                if not res:
                    raise ErackSyntaxWarning(rack_id)


                self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['StockerUnitState']=1
                self.E88_Zones.Data[self.device_id].StockerUnit[idx+1]['CarrierID']=''

                if CarrierLoc in self.E88_Carriers.Mapping:
                    if self.E88_Carriers.Mapping[CarrierLoc] in self.E88_Carriers.Data:
                        if self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].CarrierState == 3:
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.remove()
                        else:
                            self.E88_Carriers.Data[self.E88_Carriers.Mapping[CarrierLoc]].State.kill_carrier()
                        self.E88_Carriers.delete(self.E88_Carriers.Mapping[CarrierLoc])
                        self.E88_Zones.Data[self.device_id].capacity_increase()
                        if CarrierLoc in self.E88_Carriers.Mapping:
                            del self.E88_Carriers.Mapping[CarrierLoc]
                        self.read_carriers[idx]['carrierID']=''

            print('\n<end eRack thread:{}>\n'.format(self.device_id))

    def attempt_reconnection(self):
        """
        嘗試重新連接，使用指數退避算法
        """
        print('[{}] 嘗試重新連接... (第 {} 次)'.format(self.device_id, self.reconnect_count + 1))
        
        try:
            # 關閉舊連接
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            # 創建新連接
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)  # 增加超時時間
            self.sock.connect((self.ip, self.port))
            
            # 連接成功
            self.connected = True
            self.syncing_time = time.time()
            self.last_successful_connection = time.time()
            self.reconnect_count = 0  # 重置重連計數器
            
            print('[{}] 重連成功！'.format(self.device_id))
            return True
            
        except Exception as e:
            self.reconnect_count += 1
            print('[{}] 重連失敗: {} (嘗試次數: {})'.format(self.device_id, str(e), self.reconnect_count))
            
            # 計算下次重連的延遲時間（指數退避）
            delay = min(self.base_reconnect_delay * (2 ** min(self.reconnect_count, 5)), 
                       self.max_reconnect_delay)
            
            print('[{}] {}秒後重試...'.format(self.device_id, delay))
            time.sleep(delay)
            
            return False

    def force_reconnect(self):
        """
        強制重連，重置所有狀態
        """
        print('[{}] 執行強制重連...'.format(self.device_id))
        
        # 重置連接狀態
        self.connected = False
        self.sync = False
        self.erack_status = 'DOWN'
        self.reconnect_count = 0
        
        # 關閉現有連接
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
        # 嘗試重新連接
        return self.attempt_reconnection()
        
