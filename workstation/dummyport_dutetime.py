
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host
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


class DummyPort(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, check_timeout=10):
        self.secsgem_e82_h=secsgem_e82_h
        self.listeners=[]
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
        self.equipmentID=setting.get('equipmentID', '') #2022/12/09
        self.command_id_list=[]
        
        state=setting.get('state')
        self.state= state if state else 'Unknown'
        
        carrierID=setting.get('carrierID')
        self.carrierID=carrierID if carrierID else 'Unknown'

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        self.code=0
        self.extend_code=0
        self.msg=''
        #self.callback=callback
        self.enter_unloaded_time=0
        self.prepare_time=0

        self.check_timeout=check_timeout
        
        self.prepare=False
        self.duetime=-20

        #self.notify('initial') #choc add 2021/10/13
        #self.thread_stop=False
        #threading.Thread.__init__(self)

        self.enable=setting.get('enable', True) #for Disable
        if self.enable: #chocp fix 2023/9/8
            self.state='Unknown'
            self.enter_unknown_state('initial')
            self.thread_stop=False
            threading.Thread.__init__(self)
        else:           
            self.state='Disable'
            self.notify('initial')

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
        self.notify(event)
        print('loaded_check_req by {}'.format(self.workstationID))
        E82.report_event(self.secsgem_e82_h,
                        E82.TrLoadReq,{
                        'VehicleID':'',
                        'TransferPort':self.workstationID,
                        'CarrierID':''})
        
    def enter_unloaded_state(self, event):
        self.alarm=False
        self.state='UnLoaded'
        self.carrierID='Unknown'
        self.enter_unloaded_time=time.time()
        self.notify(event)
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
        #print(self.workstationID, self.state, event)
        if self.state == 'Disable':
            if event == 'enable':
                self.enter_unknown_state(event)
        else: #Enable state
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
                next_state=data
                if next_state == 'Loaded':
                    self.enter_loaded_state(event)

                elif next_state == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif next_state in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running']:
                    self.enter_other_state(event, next_state)

            elif event == 'timeout_2_sec' and self.state == 'UnLoaded' and not self.prepare:
                if self.enter_unloaded_time and (time.time()-self.enter_unloaded_time)>self.check_timeout:
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
                
            elif event == 'update_duetime_evt':
                self.duetime=data.get('DueTime', -20)
            
            elif event == 'timeout_2_sec' and int(self.duetime)<=60 and int(self.duetime>-10):#and self.state in ['Running','Loaded','UnLoaded']:
                if (time.time()-self.prepare_time)>self.check_timeout:
                    loaded=False
                    if self.state == 'Loaded':
                        loaded=True
                    #self.callback(self.stage, self, loaded,True)
                    self.prepare_time=time.time()

   

    def run(self):
        raw_rx=''
        #self.change_state('enable')
        while not self.thread_stop:

            try:
                if self.duetime>-10:
                    print("\033[33m")
                    print(self.workstationID,self.duetime)
                    print("\033[0m")
                time.sleep(2)
                self.change_state('timeout_2_sec')
                if self.duetime>0: #sec, new for asecl
                    self.duetime-=2
            except:
                #setalarm
                traceback.print_exc()
                pass
    
