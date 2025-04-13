import os
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables

import time
import random
import tools
import logging.handlers as log_handler
import logging

from semi.SecsHostMgr import E82_Host
from global_variables import remotecmd_queue
from global_variables import output

from global_variables import Erack

class DummyPortUtac(threading.Thread):
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

        self.check_unloaded_timeout=120
        self.check_alarm_timeout=180
        self.check_loaded_timeout=300
        self.check_tracking_timeout=300
        self.check_rejected_timeout=300
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)

        self.update_params(setting)

        self.state='Unknown' #[Disable, OutOfService, Unknown, Loaded, Unloaded, 'Loading', 'Exchange', 'UnLoading', 'Trackinh', 'Running', 'Alarm']
        self.last_state='Unknown'
        self.enter_state_time=''
        self.next_dest=''

        self.eap_port_state=''

        self.command_id_list=[]

        self.logger=logging.getLogger('dummyport')
        self.logger.setLevel(logging.DEBUG)
        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_dmyport.log"), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s"))
        self.logger.addHandler(fileHandler)

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

        #print('iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii')
        #print('workstationID:{}, Enable:{}'.format(self.workstationID, setting.get('enable', True)))
        #print('iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii')

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
        #print(self.zoneID, self.secsgem_e82_h)
        #print(E82_Host.client_map_h)
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

        if self.equipmentState == 'Run' or self.equipmentState == 'Idle':
            self.hold=False
            self.dispatch(self.stage, False)

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

        #eap_port_state=data.get('') ???

        #get'RejectAndReadyToUnLoad' message from EAP
        if self.eap_port_state == 'RejectAndReadyToUnLoad' and self.carrier_source:
        #if elf.eap_port_state == 'RejectAndReadyToUnLoad' and self.carrier_source and self.last_state == 'Tracking':
            self.next_dest=self.carrier_source
        else:
            self.next_dest=self.back_erack

        if self.next_dest.lower() == 'back':
            self.next_dest=self.carrier_source

        if not self.next_dest:
            self.next_dest='*'

        self.notify(event)

        if self.equipmentState == 'Run' or self.equipmentState == 'Idle':
            self.hold=False
            self.dispatch(self.stage, True)

    def enter_other_state(self, event, next_state, data={}): #CallReplace, CallUnload, CallLaod, Running
        if next_state in ['Disable', 'OutOfService', 'Loading', 'UnLoading', 'Exchange', 'Tracking', 'Running', 'Alarm', 'Rejected']: #ignore 'NearComplete'
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
                    self.logger.debug(" {} exceeds Alarm timeout {} sec, changing to 'Unknown'".format(self.workstationID,self.check_alarm_timeout))

            elif self.state == 'Unknown' or self.state == 'OutOfService':
                if event == 'remote_port_state_set': #chocp for AEI
                    if self.eap_port_state == 'ReadyToUnLoad' or self.eap_port_state == 'RejectAndReadyToUnLoad':
                        self.enter_loaded_state(event, data)
                        self.logger.debug("{} recv {}:{}, changing to 'Loaded'".format(
                            self.workstationID, event, self.eap_port_state))

                    elif self.eap_port_state == 'ReadyToLoad':
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} recv {}:{}, changing to 'UnLoaded'".format(
                            self.workstationID, event, self.eap_port_state))

                    elif self.eap_port_state == 'Running':
                        self.enter_other_state(event, 'Running', data)
                        self.logger.debug("{} recv {}:{}, changing to 'Running'".format(
                            self.workstationID, event, self.eap_port_state))

                elif event == 'manual_port_state_set': #from UI change state
                    print('get manual_port_state_set=>', data)
                    if data['next_state'] == 'UnLoaded':
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} recv {}, changing to 'UnLoaded'".format(self.workstationID, event))

                    elif data['next_state'] == 'Running':
                        self.enter_other_state(event, 'Running', data)
                        self.logger.debug("{} recv {}, changing from 'Running'".format(self.workstationID, event))

                    elif data['next_state'] == 'Loaded':
                        self.enter_loaded_state(event, data)
                        self.logger.debug("{} recv {}, changing to 'Loaded'".format(self.workstationID, event))


                #for new state diagram 2023/10/25
                #elif self.enter_state_time and (time.time()-self.enter_state_time)>self.check_unknown_timeout:
                #    self.enter_unknown_state(event)

            elif self.state == 'Loaded': #with foup
                if event == 'unload_transfer_cmd':
                    self.enter_other_state(event, 'UnLoading')
                    self.logger.debug("{} recv {}, changing from 'Loaded' to '{}'".format(
                        self.workstationID, event, self.state))

                elif event == 'replace_transfer_cmd':
                    self.enter_other_state(event, 'Exchange')
                    self.logger.debug("{} recv {}, changing from 'Loaded' to '{}'".format(
                        self.workstationID, event, self.state))

                elif event == 'remote_port_state_set': #chocp for AEI
                    if self.eap_port_state == 'ReadyToLoad':
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} recv {}, changing from 'Loaded' to '{}'".format(
                            self.workstationID, event, self.state))

                elif self.enter_state_time and (time.time()-self.enter_state_time)>self.check_loaded_timeout:
                    self.alarm=True
                    self.state='Alarm'
                    self.last_state=self.state
                    self.enter_state_time=time.time()
                    self.code=50005
                    #self.extend_code=data.get('CommandID','0')
                    self.msg='Loadport {}: Loaded state not change execeed {} sec'.format(self.workstationID, self.check_loaded_timeout)
                    self.notify('alarm_set')
                    self.logger.debug(" {} exceeds 'Loaded' timeout {} sec, changing to 'Alarm'".format(self.workstationID, self.check_loaded_timeout))

            elif self.state == 'UnLoaded': #empty
                if event == 'load_transfer_cmd':
                    self.enter_other_state(event, 'Loading')
                    self.logger.debug("{} recv {}, changing from 'UnLoaded' to '{}'".format(
                        self.workstationID, event, self.state))

                elif event == 'remote_port_state_set':
                    if self.eap_port_state == 'Running':
                        self.enter_other_state(event, 'Running', data)
                        self.logger.debug("{} recv {}, changing from 'UnLoaded' to '{}'".format(
                            self.workstationID, event, self.state))

                    elif self.eap_port_state == 'ReadyToUnLoad' or self.eap_port_state == 'RejectAndReadyToUnLoad': #carrier movein by man
                        self.enter_loaded_state(event, data)
                        self.logger.debug("{} recv {}:{}, changing from 'UnLoaded' to '{}'".format(
                            self.workstationID, event, self.eap_port_state, self.state))

                elif self.enter_state_time and (time.time()-self.enter_state_time)>self.check_unloaded_timeout:
                    if not self.hold:
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} exceeds 'UnLoaded' timeout {} sec, changing to 'Alarm'".format(
                            self.workstationID, self.check_unloaded_timeout))


            elif self.state == 'Rejected': #empty
                if event == 'remote_port_state_set':
                    if self.eap_port_state == 'ReadyToLoad':
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} recv {}, changing from 'Rejected' to '{}'".format(
                            self.workstationID, event, self.state))

                    elif self.eap_port_state == 'ReadyToUnLoad': #carrier movein by man
                        self.enter_loaded_state(event, data)
                        self.logger.debug("{} recv {}:{}, changing from 'Rejected' to '{}'".format(
                            self.workstationID, event, self.eap_port_state, self.state))

                elif self.enter_state_time and (time.time()-self.enter_state_time)>self.check_rejected_timeout:
                    self.alarm=True
                    self.state='Alarm'
                    self.last_state=self.state
                    self.enter_state_time=time.time()
                    self.code=50007
                    self.msg='Loadport {}: Rejected state not change execeed {} sec'.format(
                        self.workstationID, self.check_rejected_timeout)
                    self.notify('alarm_set')
                    self.logger.debug(" {} exceeds 'Rejected' timeout {} sec, changing to 'Alarm'".format(
                        self.workstationID, self.check_rejected_timeout))



            elif self.state == 'UnLoading':
                if event == 'acquire_complete_evt':
                    self.enter_other_state(event, 'Tracking')
                    self.logger.debug("{} recv {}, changing from 'UnLoading' to '{}'".format(
                        self.workstationID, event, self.state))
                    #E82.report_event(self.secsgem_e82_h, E82.EqUnloadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH

            elif self.state == 'Loading' or self.state == 'Exchange':
                if event == 'deposit_complete_evt':
                    self.carrierID=data.get('carrierID')
                    self.carrierType=data.get('carrierType')
                    self.carrier_source=data.get('source', '') #chocp add 9/1

                    self.enter_other_state(event, 'Tracking')
                    self.logger.debug("{} recv {}, changing to '{}'".format(self.workstationID, event, self.state))
                    #E82.report_event(self.secsgem_e82_h, E82.EqLoadComplete, {'VehicleID':data['vehicleID'], 'EQID':self.equipmentID, 'PortID':self.workstationID, 'CarrierID': data['carrierID']}) # 2022/8/3 for HH

            elif self.state == 'Running':
                if event == 'remote_port_state_set': #chocp for AEI
                    #if self.eap_port_state == 'NearComplete' or self.eap_port_state == 'ReadyToUnLoad':
                    if self.eap_port_state == 'ReadyToUnLoad':
                        self.enter_loaded_state(event, data)
                        self.logger.debug("{} recv {}, changing from '{}' to 'Loaded'".format(
                            self.workstationID, event, self.state))
                    #elif eap_next_state == 'ReadyToLoad':
                    #    self.enter_unloaded_state(event)

            elif self.state == 'Tracking':
                if event == 'remote_port_state_set':
                    if self.eap_port_state == 'Running':
                        self.enter_other_state(event, 'Running', data)
                        self.logger.debug("{} recv {}, changing from 'Tracking' to '{}'".format(
                            self.workstationID, event, self.state))

                    elif self.eap_port_state == 'ReadyToLoad' and self.last_state == 'UnLoading':
                        self.enter_unloaded_state(event)
                        self.logger.debug("{} recv {}, changing from 'Tracking' to 'UnLoaded'".format(
                            self.workstationID, event))

                    elif self.eap_port_state == 'RejectAndReadyToUnLoad':
                        self.enter_other_state(event, 'Rejected', data)
                        self.logger.debug("{} recv {}, changing from 'Tracking' to 'Rejected'".format(
                            self.workstationID, event))


                elif self.enter_state_time and (time.time()-self.enter_state_time)>self.check_tracking_timeout:
                    self.alarm=True
                    self.state='Alarm'
                    self.last_state=self.state
                    self.enter_state_time=time.time()
                    self.code=50006
                    #self.extend_code=data.get('CommandID','0')
                    self.msg='Loadport {}: Tracking state not change execeed {} sec'.format(self.workstationID, self.check_tracking_timeout)
                    self.notify('alarm_set')
                    self.logger.debug(" {} exceeds 'Tracking' timeout {} sec, changing to 'Alarm'".format(
                        self.workstationID, self.check_tracking_timeout))

            else: # 'OutOfService', 'Alarm'
                pass

        except:
            #setalarm
            traceback.print_exc()
            pass

    def dispatch(self, stage, isLoaded): #chocp 2022/1/2

        portID=self.workstationID
        eqID=self.equipmentID
        stageID=self.stage
        if 'LotOut&ECIn' in self.workstation_type:
            h_eRacks=[]
            for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                for_stage=h_eRack.func.get('ECIn')
                if for_stage and for_stage == stageID:
                    h_eRacks.append(h_eRack)

            res, source_port_id, empty_carrier_id=tools.select_any_empty_carrier_in_racks(h_eRacks, carrierType='') #lotID
            if res:
                obj={}
                uuid=100*time.time()%1000000000000 #chocp add 2021/11/7
                obj['remote_cmd']='transfer_format_check'
                    
                if isLoaded:
                    obj['commandinfo']={'CommandID':'AutoSwap%.12d'%uuid, 'Priority':0, 'Replace':1}

                    obj['transferinfolist']=[{'CarrierID':empty_carrier_id, 'SourcePort':source_port_id, 'DestPort':portID},\
                                                {'CarrierID':self.carrierID, 'CarrierType':self.carrierType, 'SourcePort':portID, 'DestPort': self.next_dest}]
                else:
                    obj['commandinfo']={'CommandID':'AutoLoad%.12d'%uuid, 'Priority':0, 'Replace':0}
                    obj['transferinfolist']=[{'CarrierID':empty_carrier_id, 'SourcePort':source_port_id, 'DestPort':portID}]

                #remotecmd_queue.append(obj)
                tools.indicate_slot(source_port_id, portID, vehicle_id='') #2024/1/2
                self.orderMgr.send_transfer(obj)  #for USG# 2023/12/15

                self.command_id_list.append(obj['commandinfo']['CommandID'])
            else:
                print('Dispatch:', 'Not find a empty carrier')

            return

        if self.eap_port_state == 'RejectAndReadyToUnLoad':
            self.hold=True
            obj={}
            uuid=100*time.time()%1000000000000 #chocp add 2021/11/7
            obj['remote_cmd']='transfer_format_check'
            obj['commandinfo']={'CommandID':'RejectUnload%.12d'%uuid, 'Priority':0, 'Replace':0}
            obj['transferinfolist']=[{'SourcePort': portID, 'CarrierID': self.carrierID, 'CarrierType':self.carrierType, 'DestPort': self.next_dest}]
            #remotecmd_queue.append(obj)
            self.orderMgr.send_transfer(obj)  #for USG# 2023/12/15
            self.command_id_list.append(obj['commandinfo']['CommandID'])
            return

        for work in self.orderMgr.work_list: #cmd load or replace transfer
            if work['Status'] == 'WAITING':
                match=False
                if global_variables.RackNaming == 13:
                    if (work['Priority'] == 100 and portID == work['Machine']) or (eqID in work['Machine'] or '*' == work['Machine']):
                        match=True
                elif eqID in work['Machine'] or '*' == work['Machine']:
                    match=True

                if match:
                    self.hold=True
                    if global_variables.TSCSettings.get('Other', {}).get('HoldEnable') == 'yes': #only for RTD mode
                        self.orderMgr.my_lock.acquire()
                        work['Status']='HOLD'
                        work['DestPort']=portID
                        if isLoaded:
                            work['Replace']=1
                            self.change_state('replace_transfer_cmd')
                        else:
                            work['Replace']=0
                            self.change_state('load_transfer_cmd')
                        self.orderMgr.my_lock.release()
                    else:
                        self.orderMgr.my_lock.acquire()
                        work['Status']='DISPATCH'
                        work['DestPort']=portID
                        work['Replace']=1 if isLoaded else 0
                        self.orderMgr.my_lock.release()

                        if work['Replace']:
                            obj_for_load={}
                            obj_for_load['remote_cmd']='transfer_format_check'
                            obj_for_load['commandinfo']={'CommandID':work['WorkID']+'-LOAD', 'Priority':0, 'Replace':0}
                            obj_for_load['transferinfolist']=[{'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', ''), 'SourcePort':work['Location'], 'DestPort':portID}]

                            obj_for_unload={}
                            obj_for_unload['remote_cmd']='transfer_format_check'
                            obj_for_unload['commandinfo']={'CommandID':work['WorkID']+'-UNLOAD', 'Priority':0, 'Replace':0}
                            obj_for_unload['transferinfolist']=[{'CarrierID':self.carrierID, 'CarrierType':self.carrierType, 'SourcePort':portID, 'DestPort': self.next_dest, 'link':obj_for_load['transferinfolist'][0]}] #fix for UTAC
                            #below cmd sequence is critical
                            self.orderMgr.send_transfer(obj_for_unload)  #for USG# 2023/12/15
                            #remotecmd_queue.append(obj_for_unload)
                            self.orderMgr.send_transfer(obj_for_load)  #for USG# 2023/12/15
                            #remotecmd_queue.append(obj_for_load)

                            self.command_id_list.append(obj_for_unload['commandinfo']['CommandID'])
                            self.command_id_list.append(obj_for_load['commandinfo']['CommandID'])
                        else:
                            #self.state='Loading'
                            obj={}
                            obj['remote_cmd']='transfer_format_check'
                            obj['commandinfo']={'CommandID':work['WorkID'], 'Priority':0, 'Replace':0}
                            obj['transferinfolist']=[{'SourcePort':work['Location'], 'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', ''), 'DestPort':portID}]
                            
                            self.orderMgr.send_transfer(obj)  #for USG# 2023/12/15
                            #remotecmd_queue.append(obj) #dispatch status will hang, when transfer cmd check error
                            self.command_id_list.append(obj['commandinfo']['CommandID'])

                        if global_variables.RackNaming == 13:
                            couples=work.get('Couples')
                            if couples:
                                couple_carrier_id=couples[0]
                                if couple_carrier_id:
                                    print('<< dispatch_couples >>:', couples)
                                    for couple_work in self.orderMgr.work_list:
                                        print('<<exist_couples_work>>:', couple_work)
                                        if couple_work['CarrierID'] == couple_carrier_id:
                                            # cls.my_lock.acquire()
                                            if couple_work['Status'] == 'INIT':
                                            # couple_work['Machine']=eqID # SAW, one port
                                            # couple_work['Priority']=100 #set highest
                                            # # couple_work['Replace']=1 if isLoaded else 0
                                            # cls.my_lock.release()
                                                self.orderMgr.update_work_status(couple_work['WorkID'], 'WAITING', 0, 0, machine=eqID, priority=100)
                                            #elif couple_work['Status'] == 'WAITING':

                                            print('<<dispatch_couples_work>>:', couple_work)

                                    # uuid=100*time.time()
                                    # uuid%=1000000000000
                                    # order={}
                                    # order['workID']='O%.12d'%uuid
                                    # order['CarrierID']=couple_carrier_id
                                    # #carrierType
                                    # order['LotID']=work['LotID']
                                    # order['Stage']=work['Stage']
                                    # order['Machine']=eqID#SAW, one port
                                    # order['Priority']=100 #set highest
                                    # order['Couples']=couples
                                    # obj={'remote_cmd':'work_add', 'workinfo':order}
                                    # remotecmd_queue.append(obj)
                                    #may repeat, dummpy port need delay...
                    output('WorkPlanListUpdate', {
                    'WorkID':work['WorkID'],
                    'Status':work['Status'],
                    'Machine':work['Machine'],
                    'DestPort':portID,
                    'Location':work['Location'],
                    'Replace':work['Replace'],
                    'Couples':work.get('Couples', [])
                    }) #chocp: machine update 2021/3/23
                    break
        else: #no carrier in worklist, so cmd unload tranfer 2022/12/22
            if isLoaded:
                self.hold=True
                obj={}
                uuid=100*time.time()%1000000000000 #chocp add 2021/11/7
                obj['remote_cmd']='transfer_format_check'
                obj['commandinfo']={'CommandID':'AutoUnload%.12d'%uuid, 'Priority':0, 'Replace':0}
                obj['transferinfolist']=[{'SourcePort': portID, 'CarrierID': self.carrierID, 'CarrierType':self.carrierType, 'DestPort': self.next_dest}]
                #remotecmd_queue.append(obj)
                self.orderMgr.send_transfer(obj)  #for USG# 2023/12/15
                self.command_id_list.append(obj['commandinfo']['CommandID'])

