
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables

import time
import random
import requests

class DummyPort(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, callback=None, check_timeout=60):
        self.secsgem_e82_h=secsgem_e82_h
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
        self.allow_shift=setting.get('allowShift', False)
        self.limitBuf=setting.get('limitBuf', 'All')

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        self.enable=setting.get('enable', True) #for Disable
        self.ip=setting.get('ip', '')
        self.port=setting.get('port','')


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

        self.carrierID=''
        self.carrierType=''
        self.carrier_source=''

        self.notify(event)
        
        
    def enter_unloaded_state(self, event):
        self.alarm=False
        self.state='UnLoaded'
        self.carrierID='Unknown'
        self.enter_unloaded_time=time.time()
        self.notify(event)

        print('enter_unloaded_state', self.stage, self.enter_unloaded_time)

        #self.callback(self.stage, self, False) #chocp 2022/1/2

    def enter_loaded_state(self, event, data={}): #chocp 2022/1/2, chocp 2022/6/7 fix
        self.alarm=False
        self.state='Loaded'
        self.carrierID=data.get('CarrierID','')
        self.dest=data.get('DestPort', '')
        self.notify(event)
        #self.callback(self.stage, self, True) #not do replace    

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

            elif event == 'load_req_ok' :
                if self.state == 'Unknown':
                    self.enter_unloaded_state(event)

            elif event == 'unload_cmd_evt': #if self.state == 'Unknown' or self.state == 'Running':
                self.enter_loaded_state(event, data) #chocp fix 2022/6/7

            elif event == 'load_transfer_cmd':
                self.enter_other_state(event, 'CallLoad')
            
            elif event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'CallReplace')

            elif event == 'unload_transfer_cmd':
                self.enter_other_state(event, 'CallUnLoad')

            elif event == 'remote_port_state_set' :
                next_state=data
                if next_state == 'Loaded':
                    self.enter_loaded_state(event)

                elif next_state == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif next_state in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running']:
                    self.enter_other_state(event, next_state)

            elif event == 'manual_port_state_set' :#and self.state == 'Unknown':
                next_state=data.get('next_state')

                if next_state == 'Loaded':
                    self.enter_loaded_state(event)

                elif next_state == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif next_state in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running']:
                    self.enter_other_state(event, next_state)

            elif event == 'timeout_10_sec':
                if self.state == 'UnLoaded' and self.enter_unloaded_time and (time.time()-self.enter_unloaded_time)>self.check_unloaded_timeout:
                    self.enter_unloaded_state(event)

            elif event == 'acquire_start_evt':
                if self.state == 'CallReplace':
                    self.enter_other_state(event, 'Exchange')
                else:
                    self.enter_other_state(event, 'UnLoading')

            elif event == 'acquire_complete_evt':
                if self.state!='Exchange':
                    self.enter_unloaded_state(event)

            elif event == 'deposit_start_evt':
                if self.state!='Exchange':
                    self.enter_other_state(event, 'Loading')

            elif event == 'deposit_complete_evt':
                #chocp add 8/27
                if global_variables.RackNaming!=18:
                    E82.report_event(self.secsgem_e82_h, E82.EqLoadComplete, {'VehicleID':data['vehicleID'], 'EQID':'', 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 10/25
                
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_other_state(event, 'Running')
        except:
            #setalarm
            traceback.print_exc()
            pass

    def door_action(self, id, cmd_type=None, timeout=90, max_retries=3, wait=True): #only for SJ by zhenghao zhou
        result=0
        msg=''
        eq_port=self.equipmentID.rsplit('-', 1)[-1]
        for _ in range(max_retries):
            try:
                url='http://{}:{}'.format(self.ip, self.port)
                data={
                    'MSGID':id,
                    'EQUID':self.equipmentID,
                    'MODEL': '',
                    'IP':self.ip,
                    'CMDTYPE':cmd_type or eq_port, # cmd_type (2:close door after unload, 5:close door after load, eq_port: eq port )
                    'REPLY': int(wait) # 0:no msg, 1:wait msg
                }
                print('req_door_action', data)
                response=requests.post(url, json=data, timeout=timeout)
                if response.status_code == 200:
                    response_data=response.json()
                    result=int(response_data.get('RESULT', 0)) # 0:fail, 1:success
                    msg=response_data.get('MSGSTR', '').encode('utf-8')
                    # When the response is "success" or action is close, exit directly.
                    if result == 1:
                        time.sleep(5) # delay for 5 seconds and wait until the door is fully opened.
                        break
                    if cmd_type in [2, 5]:
                        break
                else:
                    msg="door_action response status code {}".format(response.status_code)
            except Exception:
                msg=traceback.format_exc()
        else:
            msg += " door_action failed after {} attempts".format(max_retries)
        return result, msg
   
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
    
