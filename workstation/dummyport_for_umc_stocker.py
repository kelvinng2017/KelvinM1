#Sean
#currently copy from utac
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables

import time
import random
import tools
from semi.SecsHostMgr import E82_Host
from global_variables import remotecmd_queue, output, Erack

class DummyPortUMCStocker(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, check_timeout=120):
        self.secsgem_e82_h=secsgem_e82_h
        self.orderMgr=order_mgr

        self.workstationID=setting.get('portID', '')
        self.equipmentID=setting.get('equipmentID', '')

        self.hold=False
        self.lastEquipmentState=''
        self.equipmentState='Run'
        self.listeners=[]

        #self.alarm=False
        self.code=0
        self.extend_code=0
        self.msg=''

        #self.check_unloaded_timeout=120
        self.check_unloaded_timeout=5 #chocp
        self.check_alarm_timeout=180
        #self.check_loaded_timeout=300
        self.check_loaded_timeout=5 #chocp

        self.check_tracking_timeout=300
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)

        #self.callback=callback
        self.update_params(setting)

        self.state='Unknown' #[Disable, OutOfService, Unknown, Loaded, Unloaded, 'Loading', 'Exchange', 'UnLoading', 'Trackinh', 'Running', 'Alarm']
        self.last_state='Unknown'
        self.enter_state_time=''
        self.next_dest=''

        self.eap_port_state=''

        self.command_id_list=[]

        '''if self.enable: #chocp fix 2023/9/8
            print(self.workstationID, 'initial', 'Enable')
            self.enter_unknown_state('initial')
        else:
            print(self.workstationID, 'initial', 'Disable')
            self.enter_other_state('initial', 'Disable')'''

        #self.enable=setting.get('enable', True) #for Disable
        if not self.enable:
            self.enter_other_state('initial', 'Disable')

        self.thread_stop=False
        threading.Thread.__init__(self)

    def run(self):
        print('start loop:', self.workstationID, self.enable)
        time.sleep(random.randint(1, 5)/10)
        self.enable=True
        self.enter_unknown_state('initial')
        
        count=0
        while not self.thread_stop:
            time.sleep(1)
            count=count+1
            if count>10:
                count=0
                self.change_state('timeout_10_sec')

    def update_params(self, setting):
        print('-')
        print('for UMC stocker design')
        print('workstationID:{}, Enable:{}'.format(self.workstationID, setting.get('enable', True)))
        print('-')

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
        self.limitBuf=setting.get('limitBuf', 'All')

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
        self.last_state=self.state
        self.state='Unknown'
        self.enter_state_time=time.time()
        
        self.carrierID='Unknown'
        self.carrierType=''
        self.carrier_source=''
        
        self.code=0
        self.extend_code=0
        self.msg=''

        self.notify(event)
        print('EQStatusReq for {} by {}, due to {}'.format(self.equipmentID, self.workstationID, event))
        E82.report_event(self.secsgem_e82_h, E82.EQStatusReq, {'EQID':self.equipmentID})

    def enter_unloaded_state(self, event):
        self.alarm=False
        self.last_state=self.state
        self.state='UnLoaded'
        self.enter_state_time=time.time()
        self.carrierID=''
        self.carrierType=''
        self.carrier_source=''
        self.notify(event)

    def enter_loaded_state(self, event, data={}): #chocp 2022/1/2, chocp 2022/6/7 fix
        self.alarm=False
        self.last_state=self.state
        self.state='Loaded'
        self.enter_state_time=time.time()
        #from host or UI
        if data.get('CarrierID'):
            self.carrierID=data.get('CarrierID')
        if data.get('CarrierType'):
            self.carrierType=data.get('CarrierType')

        #eap_next_state=data.get('')

        #get'RejectAndReadyToUnLoad' message from EAP
        if self.eap_port_state == 'RejectAndReadyToUnLoad' and self.carrier_source:
        #if data.get('PortStatus') == 5 and self.carrier_source and self.last_state == 'Tracking':
            self.next_dest=self.carrier_source
        else:
            self.next_dest=self.back_erack

        if self.next_dest.lower() == 'back':
            self.next_dest=self.carrier_source

        if not self.next_dest:
            self.next_dest='*'

        self.notify(event)

        
    def enter_other_state(self, event, next_state, data={}): #CallReplace, CallUnload, CallLaod, Running
        if next_state in ['Disable', 'OutOfService', 'Loading', 'UnLoading', 'Exchange', 'Tracking', 'Running', 'Alarm']: #ignore 'NearComplete'
            self.alarm=True if next_state in ['OutOfService', 'Alarm', 'Disable'] else False
            self.last_state=self.state
            self.state=next_state
            self.enter_state_time=time.time()
            #from host or UI
            if data.get('CarrierID'):
                self.carrierID=data.get('CarrierID')
            if data.get('CarrierType'):
                self.carrierType=data.get('CarrierType')

            self.notify(event)

    def change_state(self, event, data={}): #0825
        try:
            #print('change_state', self.workstationID, self.state, self.last_state)
            self.eap_port_state=''
            #common change state test
            if event == 'alarm_set': #from TSC
                self.alarm=True
                self.last_state=self.state
                self.state='Alarm'
                self.enter_state_time=time.time()
                self.code=50001
                self.msg='Loadport {}: caused by {}'.format(self.workstationID, data)
                self.notify('alarm_set')

            elif event == 'alarm_reset':#from UI, reset from all state
                self.alarm=False
                #cancel relative transfer include abort
                
                for command_id in self.command_id_list:
                    print('<< alarm_reset, workstation: {} >>'.format(self.workstationID))
                    obj={}    
                    obj['remote_cmd']='cancel' 
                    obj['CommandID']=command_id
                    remotecmd_queue.append(obj)
                    print('<< cancel relative transfer: {} >>'.format(command_id))

                self.command_id_list=[]
                self.enter_unknown_state(event)

            elif event == 'remote_port_state_set': #chocp for AEI
                AeiPortState=['OutOfService', 'Running', 'NearComplete', 'ReadyToUnLoad', 'ReadyToLoad', 'RejectAndReadyToUnLoad', 'PortAlarm']
                try:
                    AeiEqState=['Down', 'PM', 'Idle', 'Run']
                    try:
                        idx=int(data.get('EQStatus', -1))
                        if idx>=0:
                            self.lastEquipmentState=self.equipmentState
                            self.equipmentState=AeiEqState[idx]
                            if self.lastEquipmentState!=self.equipmentState:
                                self.notify('EQStatus Changed')

                    except:
                        pass

                    try:
                        self.eap_port_state=AeiPortState[int(data.get('PortStatus', 0))]
                        #eap_next_state=data.get('PortStatus', '')
                    except:
                        pass

                    if self.eap_port_state == 'PortAlarm':
                        self.alarm=True
                        self.last_state=self.state
                        self.state='Alarm'
                        self.enter_state_time=time.time()
                        self.code=50003
                        #self.extend_code=data.get('CommandID','0')
                        self.msg='Loadport {}: get PortAlarm by EAP'.format(self.workstationID)
                        self.notify('alarm_set')

                    elif self.eap_port_state == 'OutOfService':
                        self.alarm=True
                        self.last_state=self.state
                        self.state='Alarm'
                        self.enter_state_time=time.time()
                        self.code=50004
                        #self.extend_code=data.get('CommandID','0')
                        self.msg='Loadport {}: get OutOfService by EAP'.format(self.workstationID)
                        self.notify('alarm_set')

                except:
                    self.alarm=True
                    self.last_state=self.state
                    self.state='Alarm'
                    self.enter_state_time=time.time()
                    self.code=50002
                    #self.extend_code=data.get('CommandID','0')
                    self.msg='Loadport {}: parse message error by EAP'.format(self.workstationID)
                    self.notify('alarm_set')

            #specified change state test
            if self.state == 'Alarm':
                if self.enter_state_time and (time.time()-self.enter_state_time)>self.check_alarm_timeout:
                    self.enter_unknown_state(event)

            else:
                if event == 'acquire_complete_evt':
                    self.enter_unloaded_state(event)
                    
                elif event == 'deposit_complete_evt':
                    self.carrierID=data.get('carrierID')
                    self.carrierType=data.get('carrierType')
                    self.carrier_source=data.get('source', '')
                    self.enter_other_state(event, 'Running')

                elif event == 'remote_port_state_set': #chocp for AEI
                    if self.eap_port_state == 'ReadyToUnLoad' or self.eap_port_state == 'RejectAndReadyToUnLoad':
                        self.enter_loaded_state(event, data)

                    elif self.eap_port_state == 'ReadyToLoad':
                        self.enter_unloaded_state(event)

                    elif self.eap_port_state == 'Running':
                        self.enter_other_state(event, 'Running', data)
                    
                    else:
                        self.enter_unknown_state(event)

                elif event == 'manual_port_state_set': #from UI change state
                    print('get manual_port_state_set=>', data)
                    if data['next_state'] == 'UnLoaded':
                        self.enter_unloaded_state(event)

                    elif data['next_state'] == 'Running':
                        self.enter_other_state(event, 'Running', data)

                    elif data['next_state'] == 'Loaded':
                        self.enter_loaded_state(event, data)

                    else:
                        self.enter_unknown_state(event)

                elif self.state == 'Unknown' or self.state == 'OutOfService':
                    if self.enter_state_time and (time.time()-self.enter_state_time)>self.check_unknown_timeout:
                        self.enter_unknown_state(event)

                

                


        except:
            #setalarm
            traceback.print_exc()
            pass

    