
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


class DummyPortHuahong(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, check_timeout=60):
        self.secsgem_e82_h=secsgem_e82_h

        self.hold=False
        self.listeners=[]

        self.enable=setting.get('enable', True)
        self.equipmentID=setting.get('equipmentID', '') #for HH
        self.equipmentState='Run'

        self.workstation_type=setting.get('type', 'LotIn&LotOut') 
        self.zoneID=setting.get('zoneID', '')
        self.stage=setting.get('stage', '') #or machines
        self.workstationID=setting.get('portID', '')
        self.back_erack=setting.get('return', '') 
        self.carrier_source=setting.get('from', '')
        self.valid_input=setting.get('validInput', True)
        self.BufConstrain=setting.get('bufConstrain', False) #for Buf Constrain
        self.open_door_assist=setting.get('openDoorAssist', False) #for req open door assist
        self.allow_shift=setting.get('allowShift', False)
        self.limitBuf=setting.get('limitBuf', 'All')

        carrierID=setting.get('carrierID')
        self.carrierID=carrierID if carrierID else 'Unknown'

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        self.code=0
        self.extend_code=0
        self.msg=''

        self.enter_unloaded_time=0
        self.enter_loaded_time=0

        self.enter_unloaded_time=0
        self.check_unloaded_timeout=check_timeout

        self.enter_unknown_time=0
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)

        self.state='Unknown' #[OutOfService, Unknown, Loaded, Unloaded, 'CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running', 'Alarm']
        
        #random sleep
        #self.notify('initial') #choc add 2021/10/13

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
        self.command_id_list=[]

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
        
    def enter_idle_state(self, event):
        self.alarm=False
        self.state='Idle'
        self.carrierID='Unknown'
        self.notify(event)
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

        if self.equipmentState == 'Run' or self.equipmentState == 'Idle':
            self.hold=False
    
    def enter_loaded_state(self, event, data={}): #chocp 2022/1/2, chocp 2022/6/7 fix
        self.alarm=False
        self.state='Loaded'
        self.enter_loaded_time=time.time()
        self.carrierID=data.get('CarrierID','')
        self.dest=data.get('DestPort', '*')
        self.notify(event)

        self.hold=False

    def enter_other_state(self, event, next_state): #CallReplace, CallUnload, CallLaod, Running
        self.alarm=False
        self.state=next_state
        self.notify(event)


    def change_state(self, event, data={}): #0825
        print(self.workstationID, self.state, event, data)
        eap_port_next_state='Warn'
        if event == 'alarm_set': #from TSC
            self.alarm=True
            self.state='Alarm'
            self.code=50001
            #self.extend_code=data.get('CommandID','0')
            #self.msg='Loadport {}: caused by vehicle:{}'.format(self.workstationID, data.get('vehicleID', ''))
            self.msg='Loadport {}: caused by {}'.format(self.workstationID, data)
            self.notify('alarm_set')

        elif event == 'alarm_reset':#from UI
            self.alarm=False
            self.enter_unknown_state(event)
            #print('EQStatusReq for {} by {}, due to {}'.format(self.equipmentID, self.workstationID, event))
            E82.report_event(self.secsgem_e82_h, E82.EQStatusReq, {'EQID':self.equipmentID})

        elif event == 'remote_port_state_set': 
            print(data)
            #equipmentState=['Down', 'PM', 'Idle', 'Run']
            eap_eq_next_state=data.get('EQStatus', '')
            if eap_eq_next_state == 'RUN':
                self.equipmentState='Run'

            elif eap_eq_next_state == 'LOST':
                self.equipmentState='Idle'

            elif eap_eq_next_state == 'DOWN':
                self.equipmentState='Down'
                
            else:
                self.equipmentState='PM'
    
            eap_port_next_state=data.get('PortStatus', '')
            if eap_port_next_state == 'Warn' or eap_port_next_state == 'Down':
                self.alarm=True
                self.state='Alarm'
                self.code=50003
                #self.extend_code=data.get('CommandID','0')
                self.msg='Loadport {}: get Warn or Down by MES'.format(self.workstationID)
                self.notify('alarm_set')

            elif eap_port_next_state not in ['ReadyToLoad', 'Run','' ]:
                self.alarm=True
                self.state='Alarm'
                self.code=50002
                #self.extend_code=data.get('CommandID','0')
                self.msg='Loadport {}: parse message: {} error by MES'.format(self.workstationID, eap_port_next_state)
                self.notify('alarm_set')
            else:
                self.notify(event)
                
        elif event == 'timeout_10_sec':
            if self.state == 'Unknown' and self.enter_unknown_time and (time.time()-self.enter_unknown_time)>self.check_unknown_timeout:
                self.enter_unknown_state(event)
                #print('EQStatusReq for {} by {}, due to {}'.format(self.equipmentID, self.workstationID, event))
                E82.report_event(self.secsgem_e82_h, E82.EQStatusReq, {'EQID':self.equipmentID})


        elif event == "enter_idle_state":
            self.enter_idle_state(event)

        ####################################################################################
        if self.state == 'Unknown':
            if event == 'remote_port_state_set': #chocp for AEI
                """
                if eap_port_next_state == 'ReadyToLoad' or :
                    self.enter_unloaded_state(event)
                else:
                    self.enter_other_state(event, 'Running') #'OutOfService', 'Running'
                """
                if eap_port_next_state in ['ReadyToLoad', "Run"]:
                    self.enter_idle_state(event)
                #self.enter_other_state(event, 'Idle') #'Idle'

            elif event == 'manual_port_state_set': #from UI
                if data == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif data =='Running':
                    self.enter_other_state(event, 'Running')
                    
        elif self.state == 'Idle':
            if event == 'load_req_ok' :
                self.enter_unloaded_state(event)
                
            elif event == 'load_req_ng':
                 self.enter_other_state(event, 'Running')
        
        elif self.state == 'Loaded': #with foup
            if event == 'unload_transfer_cmd':
                self.enter_other_state(event, 'UnLoading')

            elif event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'Exchange')

            elif event == 'load_req_ok' :
                self.enter_unloaded_state(event)
                
            elif event == 'load_req_ng':
                 self.enter_other_state(event, 'Running')
            #elif event == 'remote_port_state_set': #chocp for AEI
            #    if eap_port_next_state == 'Run':
            #        self.enter_other_state(event, 'Running')

            #    elif eap_port_next_state == 'ReadyToLoad':
            #        self.enter_unloaded_state(event)

        elif self.state == 'UnLoaded': #empty
            if event == 'load_transfer_cmd':
                self.enter_other_state(event, 'Loading')
            elif event == 'load_req_ng':
                 self.enter_other_state(event, 'Running')
            #elif eap_port_next_state == 'Run':
            #    self.enter_other_state('Running')

            elif self.enter_unloaded_time and (time.time()-self.enter_unloaded_time)>self.check_unloaded_timeout:
                if not self.hold:
                    self.enter_unloaded_state(event)

        elif self.state == 'UnLoading':
            if event == 'acquire_complete_evt':
                self.enter_unloaded_state(event)
                E82.report_event(self.secsgem_e82_h, E82.EqUnloadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH
            
        elif self.state == 'Loading' or self.state == 'Exchange':
            if event == 'deposit_complete_evt':
                E82.report_event(self.secsgem_e82_h, E82.EqLoadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_other_state(event, 'Running')

        elif self.state == 'Running':
            if event == 'unload_cmd_evt':
                self.enter_loaded_state(event, data)
            elif event == 'load_req_ok' :
                self.enter_unloaded_state(event)
 
        else: # 'OutOfService', 'Alarm'
            pass
        

    def run(self):
        raw_rx=''
        #time.sleep(10)
        if self.enable:
            print('*****************************')
            print('InService:{}', self.equipmentID)
            #E82.report_event(self.secsgem_e82_h, E82.EQAutoOnReq, {'EQID':self.equipmentID})
            self.enter_unknown_state('initial')            
        else:
            print('*****************************')
            print('OutOfService:{}', self.equipmentID)
            #E82.report_event(self.secsgem_e82_h, E82.EQAutoOffReq, {'EQID':self.equipmentID})
            self.enter_other_state('initial', 'OutOfService')
            self.thread_stop=True
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
    
