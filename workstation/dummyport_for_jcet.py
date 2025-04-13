
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables
import random

import time
from global_variables import remotecmd_queue
from global_variables import output

class MyException(Exception):
    pass

class SocketNullStringWarning(MyException):
    def __init__(self, txt='receive null string'):
        self.alarm_set='Error'
        self.code=30001
        self.txt=txt

port_status_map={
    0:'OutOfService',
    1:'Running',
    2:'Running',
    3:'ReadyToUnload',
    4:'ReadyToLoad',
    5:'ReadyToUnload',
    6:'Alarm',
    '0':'OutOfService',
    '1':'Running',
    '2':'Running',
    '3':'ReadyToUnload',
    '4':'ReadyToLoad',
    '5':'ReadyToUnload',
    '6':'Alarm',
}

eq_status_map={
    0:'Down',
    1:'PM',
    2:'Idle',
    3:'Run',
    4:'SEMIAuto',
    12:'Idle',
    13:'Run',
    14:'SEMIAuto',
    '0':'Down',
    '1':'PM',
    '2':'Idle',
    '3':'Run',
    '4':'SEMIAuto',
    '12':'Idle',
    '13':'Run',
    '14':'SEMIAuto',
}

class DummyPortJcet(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, check_timeout=60):
        self.secsgem_e82_h=secsgem_e82_h

        self.listeners=[]
        self.equipmentID=setting.get('equipmentID', '') #for HH
        self.workstation_type=setting.get('type', 'LotIn&LotOut') 
        self.zoneID=setting.get('zoneID', '')
        self.stage=setting.get('stage', '')
        self.workstationID=setting.get('portID', '')
        self.back_erack=setting.get('return', '') 
        self.carrier_source=setting.get('from', '')
        self.valid_input=setting.get('validInput', True)
        self.BufConstrain=setting.get('bufConstrain', False) #for Buf Constrain
        self.open_door_assist=setting.get('openDoorAssist', False) #for req open door assist
        self.allow_shift=setting.get('allowShift', False)
        self.limitBuf=setting.get('limitBuf', 'All')
        self.equipmentState=setting.get('equipmentState', '')
        self.logger=setting.get('logger', None)

        self.command_id_list=[]

        '''self.state=setting.get('state', 'Unknown')
        if self.state != 'Disable':
            self.state='Unknown'''

        carrierID=setting.get('carrierID')
        self.carrierID=carrierID if carrierID else 'Unknown'

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        self.code=0
        self.extend_code=0
        self.msg=''

        self.enter_unloaded_time=0
        self.check_unloaded_timeout=check_timeout

        self.enter_unknown_time=0
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)
        
        self.enable=setting.get('enable', True) #for Disable
        if self.enable: #chocp fix 2023/9/8
            self.enter_unknown_state('initial')
        else:
            self.state='Disable'
            self.notify('initial')

        self.thread_stop=False
        threading.Thread.__init__(self)
        
    def update_params(self, setting):
        self.workstation_type=setting.get('type', 'LotIn&LotOut')
        self.zoneID=setting.get('zoneID', '')
        self.stage=setting.get('stage', '') #or machines

        self.back_erack=setting.get('return', '')

        carrierID=setting.get('carrierID')
        self.carrierID=carrierID if carrierID else 'Unknown'
        self.carrierType=setting.get('carrierType')

        self.carrier_source=setting.get('from', '')
        self.valid_input=setting.get('validInput', True)
        self.BufConstrain=setting.get('bufConstrain', False) #for Buf Constrain
        self.open_door_assist=setting.get('openDoorAssist', False) #for req open door assist
        self.allow_shift=setting.get('allowShift', False)

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False
        self.enable=setting.get('enable', True) #for Disable

    def add_listener(self, obj):
        self.listeners.append(obj)
        obj.on_notify(self, 'sync')

    def notify(self, event):
        for obj in self.listeners:
            obj.on_notify(self, event)
    
    def enter_unknown_state(self, event):
        self.alarm=False
        self.state='Unknown'
        self.carrierID='Unknown'
        self.enter_unknown_time=time.time()
        self.notify(event)


    def enter_unloaded_state(self, event):
        self.alarm=False
        self.state='UnLoaded'
        self.carrierID='' #8.21M-1
        self.enter_unloaded_time=time.time()
        self.notify(event)

    def enter_loaded_state(self, event, data={}): #chocp 2022/1/2, chocp 2022/6/7 fix
        self.alarm=False
        self.state='Loaded'
        self.carrierID=data.get('CarrierID','Unknown') #8.21M-1
        self.dest=data.get('DestPort', '')
        self.notify(event)

    def enter_other_state(self, event, next_state):
        self.alarm=False
        self.state=next_state
        self.notify(event)
   
    def change_state(self, event, data={}): #0825
        #print(self.workstationID, self.state, event)
        if self.state == 'Disable':
            if event == 'enable':
                self.enter_unknown_state(event)
                print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
                E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

        else: #Enable state
            if event == 'alarm_set': #need fix
                self.alarm=True
                self.state='Alarm'
                self.code=50000
                self.extend_code=data.get('CommandID','0')
                self.msg='Loadport {}: caused by vehicle:{}'.format(self.workstationID, data.get('vehicleID', ''))
                self.notify('alarm_set')

            elif event == 'alarm_reset':
                self.alarm=False
                self.enter_unknown_state(event)
                print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
                E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

            elif event == 'load_transfer_cmd':
                self.enter_other_state(event, 'CallLoad')
            
            elif event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'CallReplace')

            elif event == 'unload_transfer_cmd':
                self.enter_other_state(event, 'CallUnLoad')

            elif event == 'remote_port_state_set': #chocp for HH
                eq_status=data.get('EQStatus', None)
                if eq_status != None:
                    self.equipmentState=eq_status_map[eq_status]

                next_state=data.get('PortStatus', '')

                if next_state == 'ReadyToUnload':
                    self.enter_loaded_state(event)

                elif next_state == 'ReadyToLoad':
                    self.enter_unloaded_state(event)

                elif next_state == 'Alarm':
                    self.alarm=True
                    self.state='Alarm'
                    self.code=50000
                    self.extend_code=data.get('CommandID','0')
                    self.msg='Loadport {}: caused by remote'.format(self.workstationID)
                    self.notify('alarm_set')

                elif next_state in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running', 'Run', 'Disable']:
                    self.enter_other_state(event, next_state)

                elif next_state in port_status_map:
                    if int(next_state) in [3, 5]:
                        self.enter_loaded_state(event)
                    elif int(next_state) in [4]:
                        self.enter_unloaded_state(event)
                    else:
                        self.enter_other_state(event, port_status_map[next_state])

            elif event == 'manual_port_state_set': #chocp for HH

                if data['next_state'] == 'Loaded':
                    self.enter_loaded_state(event, data)

                elif data['next_state'] == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif data['next_state'] in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running']:
                    self.enter_other_state(event, data['next_state'])

            elif event == 'timeout_10_sec':
                if self.state == 'Unknown' and self.enter_unknown_time and (time.time()-self.enter_unknown_time)>self.check_unknown_timeout:
                    self.enter_unknown_state(event)
                    print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
                    E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

            elif event == 'acquire_start_evt':
                if self.state == 'CallReplace':
                    self.enter_other_state(event, 'Exchange')
                else:
                    self.enter_other_state(event, 'UnLoading')

            elif event == 'acquire_complete_evt':
                E82.report_event(self.secsgem_e82_h, E82.EqUnloadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH
                if self.state!='Exchange':
                    self.enter_unloaded_state(event)
            elif event == 'deposit_start_evt':
                if self.state!='Exchange':
                    self.enter_other_state(event, 'Loading')

            elif event == 'deposit_complete_evt':
                #chocp add 8/27
                E82.report_event(self.secsgem_e82_h, E82.EqLoadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH
                
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_other_state(event, 'Running')


    def run(self):
        raw_rx=''
        #self.change_state('enable')
        count=0
        while not self.thread_stop:

            try:
                #print("JCET...",self.workstationID)
                time.sleep(2)
                count+=1
                #self.change_state('timeout_2_sec')
                if count>5:
                    count=0
                    self.change_state('timeout_10_sec')

            except:
                #setalarm
                traceback.print_exc()
                pass
    
