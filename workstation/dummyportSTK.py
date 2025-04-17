
import threading
import traceback
import collections
import semi.e88_stk_equipment as E88
import semi.e82_equipment as E82
import global_variables

import time
import random

from global_variables import remotecmd_queue
from global_variables import output

class DummyPortSTKE88(threading.Thread):
    def __init__(self, order_mgr, secsgem_e88_h, setting, callback=None, check_timeout=60):
        self.secsgem_e88_h=secsgem_e88_h
        self.workstationID=setting.get('portID', '')
        self.equipmentID=setting.get('equipmentID', '') #2022/12/09

        self.lastEquipmentState=''
        self.equipmentState='Run'
        self.listeners=[]

        self.state=''

        self.code=0
        self.extend_code=0
        self.msg=''
        

        self.enter_unloaded_time=0
        self.check_unloaded_timeout=check_timeout
        self.enter_unknown_time=0
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)   
        self.command_id_list=[]
        # self.callback=callback
        self.update_params(setting)

        self.enable=setting.get('enable') #for Disable

        if not self.enable: #chocp fix 2023/9/8
            self.state='Disable'
            self.notify('initial')

        self.e88_port=None
        if self.secsgem_e88_h:
            self.secsgem_e88_h.Ports.add(self.workstationID)
            datasets={}
            datasets['StockerCraneID']=setting.get('stage', '')
            self.secsgem_e88_h.Ports.set(self.workstationID, datasets)
            self.e88_port=self.secsgem_e88_h.Ports.Data[self.workstationID]

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
        self.limitBuf=setting.get('limitBuf', 'All')

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        #self.enable=setting.get('enable', True) #for Disable


    def add_listener(self, obj):
        self.listeners.append(obj)
        obj.on_notify(self, 'sync')

    def notify(self, event):
        for obj in self.listeners:
            obj.on_notify(self, event)

    def enter_unknown_state(self, event):
        self.alarm=False
        self.state='InService' if self.enable else 'OutOfService'
        self.carrierID=''
        self.enter_unknown_time=time.time()

        self.carrierID=''
        self.carrierType=''
        self.carrier_source=''

        self.notify(event)

    def enter_out_of_service_state(self, event):
        self.alarm=False
        self.state='OutOfService'
        self.notify(event)
        if self.e88_port:
            self.e88_port.out_of_service()

        print(self.workstationID, 'enter_out_of_service_state', self.stage)

    def enter_in_service_state(self, event):
        self.alarm=False
        self.state='InService'
        self.notify(event)
        if self.e88_port:
            self.e88_port.in_service()

        print(self.workstationID, 'enter_in_service_state', self.stage)

    def enter_transfer_block_state(self, event):
        self.alarm=False
        self.state='TransferBlock'
        self.carrierID=''
        self.notify(event)
        # self.e88_port.PortBook=False
        if self.e88_port:
            if (self.e88_port.PortState, self.e88_port.PortServiceState) != (3, 2):
                self.e88_port.transfer_block()

        print(self.workstationID, 'enter_transfer_block_state', self.stage)

    def enter_ready_to_load_state(self, event):
        self.alarm=False
        self.state='ReadyToLoad'
        self.carrierID=''
        self.notify(event)
        if self.e88_port:
            self.e88_port.ready_to_load()

        print(self.workstationID, 'enter_ready_to_load_state', self.stage)

    def enter_ready_to_unload_state(self, event, data={}):
        self.alarm=False
        self.state='ReadyToUnload'
        self.carrierID=data.get('CarrierID','')
        self.notify(event)
        if self.e88_port:
            self.e88_port.ready_to_unload()

        print(self.workstationID, 'enter_ready_to_unload_state', self.stage)

    def enter_other_state(self, event, next_state):
        self.alarm=False
        self.state=next_state
        self.notify(event)

    def change_state(self, event, data={}): #0825
        try:
            if event == 'alarm_set':
                self.alarm=True
                self.state='Alarm'
                self.code=50000
                self.extend_code=data.get('CommandID','0')
                self.msg='Loadport {}: caused by vehicle:{}'.format(self.workstationID, data.get('vehicleID', ''))
                self.notify('alarm_set')

            elif event == 'alarm_reset':
                self.alarm=False
                self.enter_unknown_state(event)

            elif event == 'out_of_service_evt':
                self.enter_out_of_service_state(event)

            elif event == 'in_service_evt':
                self.enter_in_service_state(event)

            elif event == 'transfer_block_evt':
                self.enter_transfer_block_state(event)

            elif event == 'ready_to_load_evt':
                self.enter_ready_to_load_state(event)

            elif event == 'ready_to_unload_evt':
                self.enter_ready_to_unload_state(event, data)

        except:
            #setalarm
            traceback.print_exc()
            pass
   
    def run(self):
        print('start loop:', self.workstationID, self.enable)
        time.sleep(random.randint(1, 5)/10)
        self.enable=True
        if self.enable:
            self.enter_transfer_block_state('transfer_block_evt')
        else:
            self.enter_out_of_service_state('out_of_service_evt')

        while not self.thread_stop:
            time.sleep(1)
            pass

class DummyPortSTKE82(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, callback=None, check_timeout=60):
        self.secsgem_e82_h=secsgem_e82_h
        self.workstationID=setting.get('portID', '')
        self.equipmentID=setting.get('equipmentID', '') #2022/12/09

        self.lastEquipmentState=''
        self.equipmentState='Run'
        self.listeners=[]

        self.state=''
        self.next_state=''
        self.code=0
        self.extend_code=0
        self.msg=''
        

        self.enter_unloaded_time=0
        self.check_unloaded_timeout=check_timeout
        self.enter_unknown_time=0
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)   
        self.command_id_list=[]
        # self.callback=callback
        self.update_params(setting)

        #self.enable=setting.get('enable') #for Disable

        if not self.enable: #chocp fix 2023/9/8
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
        self.state='InService' if self.enable else 'OutOfService'
        self.carrierID=''
        self.enter_unknown_time=time.time()

        self.carrierID=''
        self.carrierType=''
        self.carrier_source=''

        self.notify(event)
        print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
        E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

    def enter_out_of_service_state(self, event):
        self.alarm=False
        self.state='OutOfService'
        self.notify(event)

        print(self.workstationID, 'enter_out_of_service_state', self.stage)

    def enter_in_service_state(self, event):
        self.alarm=False
        self.state='InService'

        print(self.workstationID, 'enter_in_service_state', self.stage)

    def enter_transfer_block_state(self, event):
        self.alarm=False
        self.state='TransferBlock'
        self.carrierID=''
        self.notify(event)

        print(self.workstationID, 'enter_transfer_block_state', self.stage)

    def enter_ready_to_load_state(self, event):
        self.alarm=False
        self.state='ReadyToLoad'
        self.carrierID=''
        self.notify(event)

        print(self.workstationID, 'enter_ready_to_load_state', self.stage)

    def enter_ready_to_unload_state(self, event, data={}):
        self.alarm=False
        self.state='ReadyToUnload'
        self.carrierID=data.get('CarrierID','')
        self.notify(event)

        print(self.workstationID, 'enter_ready_to_unload_state', self.stage)

    def enter_other_state(self, event, next_state):
        self.alarm=False
        self.state=next_state
        self.notify(event)

    def change_state(self, event, data={}): #0825
        try:
            # for USG3 LifterPort (MCS to TSC)
            if global_variables.RackNaming == 35:
                if event == 'remote_port_state_set':
                    LifterPortState = ['OutOfService', 'InService', 'TransferBlock', 'ReadyToLoad', 'ReadyToUnLoad', 'PortAlarm']
                    try:
                        self.next_state = LifterPortState[int(data.get('PortStatus', 0))-1]
                        print('next_state:', self.next_state)
                    except:
                        pass

                elif event == 'manual_port_state_set':
                    port_status = data.get('next_state', 'Unknown')
                    if port_status == 'Running':
                        self.next_state = 'TransferBlock'
                        self.enter_transfer_block_state(event)
                    elif port_status == 'UnLoaded':
                        self.next_state = 'ReadyToLoad'
                        self.enter_ready_to_load_state(event)
                    elif port_status == 'Loaded':
                        data={}
                        self.next_state = 'ReadyToUnLoad'
                        self.enter_ready_to_unload_state(event, data)

                    print('next_state:', self.next_state)

                elif self.next_state == 'OutOfService':
                    self.enter_out_of_service_state(event)

                elif event=='in_service_evt':
                    self.enter_in_service_state(event)

                elif self.next_state == 'TransferBlock':
                    self.enter_transfer_block_state(event)

                elif self.next_state == 'ReadyToLoad':
                    self.enter_ready_to_load_state(event)

                elif self.next_state == 'ReadyToUnLoad':
                    self.enter_ready_to_unload_state(event, data)

                elif event=='timeout_10_sec':
                    print('timeout_10_sec', self.state, self.enable, self.workstationID, (time.time()-self.enter_unknown_time), self.check_unknown_timeout)
                    if self.state == 'InService' and self.enter_unknown_time and (time.time()-self.enter_unknown_time) > self.check_unknown_timeout:
                    # if self.state == 'InService' and (time.time()-self.enter_unknown_time) > self.check_unknown_timeout:
                        self.enter_unknown_state(event)
                        print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
                        E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

            if event=='alarm_set':
                self.alarm=True
                self.state='Alarm'
                self.code=50000
                self.extend_code=data.get('CommandID','0')
                self.msg='Loadport {}: caused by vehicle:{}'.format(self.workstationID, data.get('vehicleID', ''))
                self.notify('alarm_set')

            elif event == 'alarm_reset':
                self.alarm=False
                self.enter_unknown_state(event)

            elif event == 'out_of_service_evt':
                self.enter_out_of_service_state(event)

            elif event == 'in_service_evt':
                self.enter_in_service_state(event)

            elif event == 'transfer_block_evt':
                self.enter_transfer_block_state(event)

            elif event == 'ready_to_load_evt':
                self.enter_ready_to_load_state(event)

            elif event == 'ready_to_unload_evt':
                self.enter_ready_to_unload_state(event, data)

            elif event == 'timeout_10_sec':
                if self.state == 'InService' and self.enter_unknown_time and (time.time()-self.enter_unknown_time)>self.check_unknown_timeout:
                    self.enter_unknown_state(event)
                    print('PortStatusReq for {}, due to {}'.format(self.workstationID, event))
                    E82.report_event(self.secsgem_e82_h, E82.PortStatusReq, {'PortID':self.workstationID})

        except:
            #setalarm
            traceback.print_exc()
            pass

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

