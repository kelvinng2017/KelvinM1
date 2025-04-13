
import threading
import traceback
import collections
import semi.e82_equipment as E82
import global_variables
from global_variables import remotecmd_queue
from global_variables import output

import time
import random

class MyException(Exception):
    pass

class SocketNullStringWarning(MyException):
    def __init__(self, txt='receive null string'):
        self.alarm_set='Error'
        self.code=30001
        self.txt=txt


class DummyPortAB(threading.Thread):
    def __init__(self, order_mgr, secsgem_e82_h, setting, check_timeout=60):
        self.secsgem_e82_h=secsgem_e82_h
        self.orderMgr=order_mgr

        self.listeners=[]
        self.state='Unknown'
        self.workstationID=setting.get('portID', '')
        self.equipmentID=setting.get('equipmentID', '') #2022/12/09
        self.command_id_list=[]

        self.code=0
        self.extend_code=0
        self.msg=''
        
        self.enter_unloaded_time=0
        self.check_unloaded_timeout=check_timeout
        self.enter_unknown_time=0
        self.check_unknown_timeout=check_timeout+random.randint(-10, 10)   

        self.update_params(setting)
        
        #self.enable=setting.get('enable') #for Disable
        if not self.enable: #chocp fix 2023/9/8
            self.state='Disable'
            self.notify('initial')
        
        self.thread_stop=False
        threading.Thread.__init__(self)

    def run(self):
        raw_rx=''
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
        self.state='Unknown'
        self.carrierID='Unknown'
        self.enter_unknown_time=time.time()
        self.notify(event)
        
    def enter_unloaded_state(self, event):
        self.alarm=False
        self.state='UnLoaded'
        self.carrierID='Unknown'
        self.enter_unloaded_time=time.time()
        self.notify(event)
        self.dispatch(self.stage, False)

    def enter_loaded_state(self, event, data={}):
        self.alarm=False
        self.state='Loaded'
        self.carrierID=data.get('CarrierID','')
        self.dest=data.get('DestPort', '')
        self.notify(event)
        self.dispatch(self.stage, True) #Must True

    def enter_other_state(self, event, next_state):
        self.alarm=False
        self.state=next_state
        self.notify(event)


    def change_state(self, event, data={}): #0825
        #print(self.workstationID, self.state, event)
        try:
            if event == 'alarm_set':
                self.alarm=True
                self.state='Alarm'
                self.code=50000
                self.msg='Loadport {}: caused by vehicle'.format(self.workstationID)
                self.notify('alarm_set')

            elif event == 'alarm_reset':
                self.alarm=False
                self.enter_unknown_state(event)
                print('loaded_check_req by {}'.format(self.workstationID))
                E82.report_event(self.secsgem_e82_h,
                        E82.TrLoadReq,{
                        'VehicleID':'',
                        'TransferPort':self.workstationID+'A',
                        'CarrierID':''})

            elif event == 'load_req_ok' :
                if self.state == 'Unknown':
                    self.enter_unloaded_state(event)

            elif event == 'unload_cmd_evt': #force
                #if self.state == 'Unknown' or self.state == 'Running':
                self.enter_loaded_state(event, data) #chocp fix 2022/6/7

            elif event == 'load_transfer_cmd':
                if self.state == 'CallUnLoad': #for dummyport_ab replace, for OCR
                    self.enter_other_state(event, 'CallReplace')
                else:
                    self.enter_other_state(event, 'CallLoad')
            
            elif event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'CallReplace')

            elif event == 'unload_transfer_cmd': #????
                self.enter_other_state(event, 'CallUnLoad')

            elif event == 'manual_port_state_set' and self.state == 'Unknown':
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
                E82.report_event(self.secsgem_e82_h, E82.EqLoadComplete, {'VehicleID':data['vehicleID'], 'EQID':'', 'PortID':self.workstationID+'A', 'CarrierID': data['carrierID']}) # 8/27
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_other_state(event, 'Running')
        except:
            #setalarm
            traceback.print_exc()
            pass


    def dispatch(self, stage, isLoaded): #chocp 2022/1/2
        #print('<< Request Dispatch: from {}, {}: replace:{} >>'.format(stage, portID, isLoaded))

        if global_variables.TSCSettings.get('Other', {}).get('RTDEnable')!='yes':
            return
        portID=self.workstationID
        eqID=self.equipmentID

        stageID=self.stage

        for work in self.orderMgr.work_list: #cmd load or replace transfer
            #if work['Status'] == 'WAITING' or work['Status'] == 'HOLD':
            if work['Status'] == 'WAITING':
                match=False
                if global_variables.RackNaming == 13:
                    if (work['Priority'] == 100 and portID == work['Machine']) or (eqID in work['Machine'] or '*' == work['Machine']):
                        match=True
                elif eqID in work['Machine'] or '*' == work['Machine']:
                    match=True

                if match:
                    try:
                        self.hold=True
                        print('{} dispatch lock {}', portID, self.hold)
                    except:
                        pass

                    if global_variables.TSCSettings.get('Other', {}).get('HoldEnable') == 'yes': #only for RTD mode
                        self.orderMgr.my_lock.acquire()
                        work['Status']='HOLD'
                        work['DestPort']=portID
                        # work['Replace']=1 if isLoaded else 0
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


                        #obj['workinfo']={'WorkID':work['WorkID']} #may skip
                        if work['Replace']:
                            obj_for_load={}
                            obj_for_load['remote_cmd']='transfer_format_check'
                            obj_for_load['commandinfo']={'CommandID':work['WorkID']+'-LOAD', 'Priority':0, 'Replace':0}
                            obj_for_load['transferinfolist']=[{'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', 'NA'), 'SourcePort':work['Location'], 'DestPort':portID}]

                            obj_for_unload={}
                            obj_for_unload['remote_cmd']='transfer_format_check'
                            obj_for_unload['commandinfo']={'CommandID':work['WorkID']+'-UNLOAD', 'Priority':0, 'Replace':0}

                            obj_for_unload['transferinfolist']=[{'CarrierID':self.carrierID, 'CarrierType':self.carrierType, 'SourcePort':portID, 'DestPort': self.next_dest, 'link':obj_for_load['transferinfolist'][0]}] #fix for UTAC
                            
                            #below cmd sequence is critical
                            remotecmd_queue.append(obj_for_unload)
                            remotecmd_queue.append(obj_for_load)

                            self.command_id_list.append(obj_for_unload['commandinfo']['CommandID'])
                            self.command_id_list.append(obj_for_load['commandinfo']['CommandID'])
                        else:
                            #self.state='Loading'
                            obj={}
                            obj['remote_cmd']='transfer_format_check'
                            obj['commandinfo']={'CommandID':work['WorkID'], 'Priority':0, 'Replace':0}
                            obj['transferinfolist']=[{'SourcePort':work['Location'], 'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', 'NA'), 'DestPort':portID}]
                            remotecmd_queue.append(obj) #dispatch status will hang, when transfer cmd check error
                            self.command_id_list.append(obj['commandinfo']['CommandID'])

                        if global_variables.RackNaming == 13:
                            couples=work.get('Couples')
                            if couples:
                                couple_carrier_id=couples.pop(0)
                                if couple_carrier_id:
                                    uuid=100*time.time()
                                    uuid%=1000000000000
                                    order={}
                                    order['workID']='O%.12d'%uuid
                                    order['CarrierID']=couple_carrier_id
                                    #carrierType
                                    order['LotID']=work['LotID']
                                    order['Stage']=work['Stage']
                                    order['Machine']=eqID#SAW, one port
                                    order['Priority']=100 #set highest
                                    order['Couples']=couples
                                    obj={'remote_cmd':'work_add', 'workinfo':order}
                                    remotecmd_queue.append(obj)
                                    #may repeat, dummpy port need delay...

                    #output('WorkPlanListUpdate', {'WorkID':work['WorkID'], 'Status':work['Status'], 'Machine':work['Machine'], 'Location':work['Location']}) #chocp: machine update 2021/3/23
                    output('WorkPlanListUpdate', {
                    'WorkID':work['WorkID'],
                    'Status':work['Status'],
                    'Machine':work['Machine'],
                    'DestPort':portID,
                    'Location':work['Location'],
                    'Replace':work['Replace']
                    }) #chocp: machine update 2021/3/23

                    print('WorkPlanListUpdate:', work)

                    break
        else: #no carrier in worklist, so cmd unload tranfer
            if isLoaded:
                #self.state='UnLoading'
                try:
                    self.hold=True
                    print('{} dispatch lock {}', portID, self.hold)
                except:
                    pass

                obj={}
                uuid=100*time.time()%1000000000000 #chocp add 2021/11/7
                obj['remote_cmd']='transfer_format_check'
                obj['commandinfo']={'CommandID':'AutoUnload%.12d'%uuid, 'Priority':0, 'Replace':0}
                obj['transferinfolist']=[{'SourcePort': portID, 'CarrierID': self.carrierID, 'CarrierType':self.carrierType, 'DestPort': self.next_dest}]
                remotecmd_queue.append(obj)
                self.command_id_list.append(obj['commandinfo']['CommandID'])