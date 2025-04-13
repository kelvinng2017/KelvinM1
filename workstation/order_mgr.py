import os
import threading
import global_variables
import alarms #to alarm system
from global_variables import output #to UI
from global_variables import remotecmd_queue #to TSC

#from workstation.eq_mgr import EqMgr

import tools
import time
import requests

import logging.handlers as log_handler
import logging

class OrderMgr():
    __instance=None
    # @staticmethod
    # def getInstance():
    #     if OrderMgr.__instance == None:
    #         OrderMgr()
    #     return OrderMgr.__instance

    def __init__(self, parent):
        self.logger=logging.getLogger("OrderMgr")
        self.logger.setLevel(logging.DEBUG)
        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_ordermgr.log"), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s"))
        self.logger.addHandler(fileHandler)

        self.work_list=[]
        self.my_lock=threading.Lock()
        self.parent=parent
        OrderMgr.__instance=self

    def send_transfer(self, obj): #for USG# 2023/12/15
        if global_variables.field_id == 'USG3':
            mcs_cmd={
                'CommandID': obj['commandinfo']['CommandID'],
                'Priority': obj['commandinfo']['Priority'],
                'Replace': obj['commandinfo']['Replace'],
                'Transfer':[{'CarrierID': obj['transferinfolist'][0]['CarrierID'],
                                'CarrierType': obj['transferinfolist'][0]['CarrierType'],
                                'Source': obj['transferinfolist'][0]['SourcePort'],
                                'Dest': obj['transferinfolist'][0]['DestPort']}]
                }
            r=requests.post('http://127.0.0.1:8080/api/SendTransferCommand', data=mcs_cmd)
            self.logger.debug('<<<SendTransferCommand>>>: mcs_cmd: {}'.format(mcs_cmd))
        else:
            remotecmd_queue.append(obj) 

    def delete_transfer(self, obj): #for USG# 2023/12/15
        if global_variables.field_id == 'USG3':
            mcs_cmd={
                'CommandID': obj['CommandID']
                }
            r=requests.post('http://127.0.0.1:8080/api/DeleteTransferCommand', data=mcs_cmd)
            self.logger.debug('<<<DeleteTransferCommand>>>: mcs_cmd: {}'.format(mcs_cmd))
        else:
            remotecmd_queue.append(obj)  # remotecmd_queue.appendleft(obj)

    def recovery_work_list(self, workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, destport, replace, status, cause):
        work={
            'WorkID':workID,
            'CarrierID':carrierID,
            'CarrierType':carrierType,
            'LotID':lotID,
            'Location':location,
            'Stage':next_step,
            'Machine':machine,
            'Priority':priority,
            'Status':status,
            'DestPort':destport,
            'Replace':0,
            'Cause':cause
        }
        self.my_lock.acquire()
        self.work_list.append(work)
        self.my_lock.release()

    def add_work_list(self, workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, couples=[]): #chocp add for UTAC couples
        # for usg1 SAW 2023/12/06
        status='INIT' if couples else 'WAITING'
        #print('<<add_work_list_1>>:', workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, couples, status)
        work={
            'WorkID':workID,
            'CarrierID':carrierID,
            'CarrierType':carrierType,
            'Couples':couples,
            'LotID':lotID,
            'Location':location,
            'Stage':next_step,
            'Machine':machine,
            'Priority':priority,
            'Status':status,
            'DestPort':'',
            'Replace':0,
            'Cause':0
        }
        for i, order in enumerate(self.work_list):
            if order['CarrierID'] == carrierID:
                alarms.RtdOrderCarrierDuplicatedInList(workID, carrierID)
                return

        for i, order in enumerate(self.work_list):
            if order['WorkID'] == workID:
                alarms.RtdOrderCarrierDuplicatedInList(workID, carrierID)
                return

        # Check the status of couples work orders and update the current work order accordingly
        for couple_carrier_id in couples:
            # print('<<couples_check>>:', couple_carrier_id)
            couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
            # print('<<couple_WorkID>>:', couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid)
            # If the couple work order is in 'INIT' state or has been dispatched or completed,
            # then set the current work order to 'WAITING' and update 'DestPort' if necessary
            if couple_Work_status in ['INIT', 'DISPATCH', 'SUCCESS']:
                # print('<<couple_Work_status>>:', couple_Work_status)
                work['Status']='WAITING'
                if couple_Work_status == 'DISPATCH' or couple_Work_status == 'SUCCESS':
                    work['Machine']=couple_Work_dest.split('_')[0]
                    work['Priority']=100
                    # print('<<couple_Work_add_check>>:', work, couple_Work_dest, work['Priority'])
                break
        self.my_lock.acquire()
        for i, order in enumerate(self.work_list):
            if int(priority)>int(order['Priority']):
                self.work_list.insert(i, work)
                break
        else:
            self.work_list.append(work)
        self.my_lock.release()
        #print('<<add_work_list_2>>:', workID, carrierID, carrierType,
        #      lotID,  location, next_step, machine, priority, couples, status)
        output('WorkPlanListAdd', work, True) #need try to trigger dispatch
        return

    def update_work_status(self, workID, status, cause, location=None, machine=None, priority=None):
        for work in self.work_list:
            if work['WorkID'] in workID: #chocp fix, make xxxx in  xxxxx-LOAD
                self.my_lock.acquire()
                work['Status']=status
                work['Cause']=cause
                if location:
                    work['Location']=location
                # for utac usg1 SAW
                if machine:
                    work['Machine']=machine
                if priority is not None:
                    work['Priority']=priority
                self.my_lock.release()

                output('WorkPlanListUpdate', work)
                should_remove=True
                if status == 'SUCCESS':
                    destport=work.get('DestPort', '')
                    h=self.parent.workstations.get(destport)
                    # print('<<h_for_SUCCESS>>:', h, '<<work>>:', work['WorkID'], '<<command_ID_list>>:', h.command_id_list)
                    # Remove WorkID from h.command_id_list
                    if h:
                        try:
                            # Remove WorkID and related IDs (like with '-LOAD' or '-UNLOAD' suffix)
                            h.command_id_list=[cmd_id for cmd_id in h.command_id_list if not cmd_id.startswith(work['WorkID'])]
                            # print('<<new_command_id_list_for_SUCCESS>>:', h.command_id_list)
                        except ValueError:
                            pass  # Do nothing if WorkID is not in the list

                    # Check if 'Couples' key exists and is not empty
                    if 'Couples' in work and work['Couples']:
                        should_remove=all(self.query_work_list_by_carrierID_for_utac(couple_carrier_id)[1] == 'SUCCESS' for couple_carrier_id in work['Couples'])
                        # print('<<couple_work_list_by_workID>>:', self.work_list)
                        # print('<<couples_check>>:', work['Couples'], should_remove)
                        self.logger.debug('check couple {} status {}'.format(work['Couples'], should_remove))
                        if not should_remove:
                            continue
                    if should_remove:
                        self.remove_work_list_by_workID(work['WorkID']) #need change load only
                        # print('<<remove_work_list_by_workID>>:', self.work_list)
                        if 'Couples' in work:
                            for couple_carrier_id in work['Couples']:
                                couple_work_id, _, _, _=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                                self.remove_work_list_by_workID(couple_work_id)
                        # print('<<remove_work_list_by_couple_workID>>:', self.work_list)

                elif status == 'FAIL': #need cnacel or abort all relative command
                    obj={}
                    obj['remote_cmd']='cancel'
                    # Remove WorkID and related IDs from h.command_id_list
                    destport=work.get('DestPort', '')
                    h=self.parent.workstations.get(destport)
                    #print('<<h_for_FAIL>>:', h, '<<work>>:', work['WorkID'], '<<command_ID_list>>:', h.command_id_list)
                    if h:
                        try:
                            h.command_id_list=[cmd_id for cmd_id in h.command_id_list if not cmd_id.startswith(work['WorkID'])]
                            #print('<<new_command_id_list_for_FAIL>>:', h.command_id_list)
                        except ValueError:
                            pass  # Do nothing if WorkID is not in the list
                    if '-UNLOAD' in workID:
                        obj['CommandID']=work['WorkID']+'-LOAD' #not use workID, maybe workID hvave -Load or -UnLoad suffix
                        remotecmd_queue.append(obj)
                        print('<< Order fail due to transfer fail, so cancel relative transfer: {} >>'.format(obj['CommandID']))

                    elif '-LOAD' in workID:
                        obj['CommandID']=work['WorkID']+'-UNLOAD' #not use workID, maybe workID hvave -Load or -UnLoad suffix
                        remotecmd_queue.append(obj)
                        print('<< Order fail due to transfer fail, so cancel relative transfer: {} >>'.format(obj['CommandID']))
                break

    def update_work_location(self, workID, location):
        for work in self.work_list:
            if work['WorkID'] in workID:
                self.my_lock.acquire()
                work['Location']=location
                self.my_lock.release()
                output('WorkPlanListUpdate', work)
                break

    def work_edit(self, workID, carrierID):
        for work in self.work_list:
            if work['WorkID'] in workID:
                res, target=tools.re_assign_source_port(carrierID)
                if res:
                    self.my_lock.acquire()
                    work['Location']=target
                    self.my_lock.release()

                output('WorkPlanListEdit', {
                    'WorkID':work.get('WorkID', ''),
                    'Status':work.get('Status', ''),
                    'Machine':work.get('Machine', ''),
                    'DestPort':work.get('DestPort', ''),
                    'Location':work.get('Location', ''),
                    'Replace':work.get('Replace', 0)
                    }) #chocp: machine update 2021/3/23
                break

    def remove_work_list_by_workID(self, workID):
        output('WorkPlanListRemove', {'WorkID':workID}, True)
        for work in self.work_list:
            if work['WorkID'] in workID:
                self.my_lock.acquire()
                self.work_list.remove(work)
                self.my_lock.release()
                break

    def cancel_work_list_by_workID(self, workID):
        output('WorkPlanListUpdate', {'WorkID':workID, 'Status':'CANCEL'}) # race condition?
        output('WorkPlanListRemove', {'WorkID':workID}, True)
        for work in self.work_list:
            if work['WorkID'] in workID:
                portID=work['DestPort']
                self.my_lock.acquire()
                self.work_list.remove(work)
                self.my_lock.release()

                # print('<< cancel_work_list_by_workID: {} >>'.format(work['WorkID']))
                #print('<< alarm_reset, workstation: {} >>'.format(portID))
                #EqMgr.getInstance().trigger(portID, 'alarm_reset')
                
                obj_load={}    
                obj_load['remote_cmd']='cancel' 
                obj_load['CommandID']=work['WorkID']+'-LOAD' #not use workID, maybe workID hvave -Load or -UnLoad suffix
                remotecmd_queue.append(obj_load)
                # print('<< cancel relative transfer: {} >>'.format(obj_load['CommandID']))

                obj_unload={}
                obj_unload['remote_cmd']='cancel'
                obj_unload['CommandID']=work['WorkID']+'-UNLOAD' #not use workID, maybe workID hvave -Load or -UnLoad suffix
                remotecmd_queue.append(obj_unload)
                # print('<< cancel relative transfer: {} >>'.format(obj_unload['CommandID']))


                # for utac usg1 SAW
                for couple_carrier_id in work.get('Couples', []):
                    # print('<<couples_check>>:', couple_carrier_id)
                    couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                    # print('<<couple_WorkID>>:', couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid)
                    if couple_Work_status == 'WAITING':

                        self.update_work_status(couple_WorkID, 'INIT', 0)
                        couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(
                            couple_carrier_id)
                        # print('<<couple_Work_status>>:', work)
                        break


                break

    def reset_work_list_by_workID(self, workID):
        for work in self.work_list:
            if work['WorkID'] in workID:
                portID=work['DestPort']
                self.my_lock.acquire()
                res, target=tools.re_assign_source_port(work['CarrierID'])
                if res:
                    work['Location']=target
                work['Status']='WAITING'
                work['DestPort']=''
                work['Replace']=0
                work['Cause']=''
                self.my_lock.release()

                output('WorkPlanListUpdate', work)
                #EqMgr.getInstance().trigger(portID, 'alarm_reset')
                break

    def query_work_list_by_carrierID(self, carrierID):
        res=''
        for work in self.work_list:
            if work['CarrierID'] == carrierID:
                self.my_lock.acquire()
                res=work
                self.my_lock.release()
                break
        if res:
            return work['WorkID']
        return ''

    def query_work_status_by_carrierID(self, carrierID):
        res=''
        for work in self.work_list:
            if work['CarrierID'] == carrierID:
                self.my_lock.acquire()
                res=work
                self.my_lock.release()
                break
        if res:
            return work['WorkID'], work['Status']
        return '', ''

    def query_work_list_by_carrierID_for_utac(self, carrierID):
        self.my_lock.acquire()
        for work in self.work_list:
            if carrierID in work['CarrierID']:
                result=(work['WorkID'], work['Status'], work['DestPort'], work.get('Couples', []))
                self.my_lock.release()
                return result
        self.my_lock.release()
        return '', '', '', ''

    def query_success_work_by_carrierID_for_utac(self, carrierID):
        res=''
        for workID, work in self.success_dict.items():
            print(type(workID), workID)
            if carrierID in work['Couples']:
                self.my_lock.acquire()
                res=work
                self.my_lock.release()
                break
        if res:
            return res['WorkID'], res['Status'], res['DestPort'], res['Couples']
        return '', '', '', ''
    def infoupdate_work_list_by_carrierID(self, carrierID, lotID, stage, machine, priority):
        res2=''
        for work in self.work_list:
            if work['CarrierID'] == carrierID:
                res2=work
                if work['LotID'] == lotID and work['Stage'] == stage and work['Machine'] == machine and work['Priority'] == priority:
                    break
                self.my_lock.acquire()
                work['Status']='WAITING'
                work['LotID']=lotID
                work['Stage']=stage
                work['Machine']=machine
                work['Priority']=priority
                work['DestPort']=''
                self.my_lock.release()
                output('WorkPlanListUpdate', work)
                break
        if res2:
            return work['WorkID']
        return ''

    def direct_dispatch(self, workID, carrierID, location, machineID, replace, destport, h):
        print('direct_dispatch', workID, carrierID, location, machineID, replace, destport)
        for work in self.work_list:
            if work['WorkID'] == workID:
                if work['Status']!='DISPATCH':
                    #if work['DestPort']!=destport:
                    #    EqMgr.getInstance().trigger(work['DestPort'], 'alarm_reset')

                    self.my_lock.acquire()
                    work['Status']='DISPATCH'
                    work['CarrierID']=carrierID
                    work['Location']=location
                    work['DestPort']=destport

                    eqID=''
                    for test_machine_id in machineID.split(','):
                        if test_machine_id in destport:
                            eqID=test_machine_id
                            break

                    self.my_lock.release()

                    output('WorkPlanListUpdate', work) # race condition?
                    if replace: #chocp 2021/12/26
                        obj_for_load={}
                        obj_for_load['remote_cmd']='transfer_format_check'
                        obj_for_load['commandinfo']={'CommandID':work['WorkID']+'-LOAD', 'Priority':0, 'Replace':0}
                        obj_for_load['transferinfolist']=[{'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', ''), 'SourcePort':work['Location'], 'DestPort':destport}]

                        obj_for_unload={}
                        obj_for_unload['remote_cmd']='transfer_format_check'
                        obj_for_unload['commandinfo']={'CommandID':work['WorkID']+'-UNLOAD', 'Priority':0, 'Replace':0}
                        #due to fore dispatch, so unload  carrierID set '', carrierType same as order cmd, 'DestPort' set '*' transfer to MR itself
                        obj_for_unload['transferinfolist']=[{'CarrierID':'', 'CarrierType':work.get('CarrierType', ''), 'SourcePort':destport, 'DestPort': '*', 'link':obj_for_load['transferinfolist'][0]}]

                        self.send_transfer(obj_for_unload)  #for USG# 2023/12/15
                        self.send_transfer(obj_for_load)  #for USG# 2023/12/15

                        h.command_id_list.append(obj_for_unload['commandinfo']['CommandID'])
                        h.command_id_list.append(obj_for_load['commandinfo']['CommandID'])
                    else:
                        #h.state='Loading'
                        obj={}
                        obj['remote_cmd']='transfer_format_check'
                        obj['commandinfo']={'CommandID':workID, 'Priority':1, 'Replace':0}
                        obj['transferinfolist']=[{'CarrierID':work['CarrierID'], 'CarrierType':work.get('CarrierType', ''), 'SourcePort':work['Location'], 'DestPort':destport, 'ExecuteTime':0}]
                        
                        self.send_transfer(obj)  #for USG# 2023/12/15
                        
                        h.command_id_list.append(obj['commandinfo']['CommandID'])

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
                                order['LotID']=work['LotID']
                                order['Stage']=work['Stage']
                                order['Machine']=eqID #SAW, one port
                                order['Priority']=100 #set highest
                                order['Couples']=couples
                                obj={'remote_cmd':'work_add', 'workinfo':order}
                                remotecmd_queue.append(obj)
                                #may repeat, dummpy port need delay...
                break
        else:
            e=alarms.RtdOrderDispatchFailWarning(workID, carrierID, machineID)
            self.update_work_status(workID, 'FAIL', e.code)