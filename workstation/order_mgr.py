import os
import threading
import global_variables
import alarms #to alarm system
from global_variables import output #to UI
from global_variables import remotecmd_queue #to TSC
from global_variables import Erack

#from workstation.eq_mgr import EqMgr

import tools
import time
import requests

import logging.handlers as log_handler
import logging
import traceback

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
        self.erack_work_list=[]
        self.my_lock=threading.Lock()
        self.parent=parent
        OrderMgr.__instance=self

    def send_transfer(self, obj): #for USG# 2023/12/15
        if global_variables.field_id == 'USG3':
            mcs_cmd={
                'CommandID': obj['commandinfo']['CommandID'],
                'Priority': obj['commandinfo']['Priority'],
                'Replace': obj['commandinfo']['Replace'],
                'Transfer': obj['transferinfolist']
            }
            existing_carrier=False
            # Check if CarrierID already exists in erack_work_list
            if mcs_cmd['CommandID'].startswith('E'):
                existing_carrier=any(cmd['Transfer'][0]['CarrierID'] == mcs_cmd['Transfer'][0]['CarrierID'] for cmd in self.erack_work_list)

            if existing_carrier:
                print("CarrierID {} already exists in erack_work_list, skipping post.".format(mcs_cmd['Transfer'][0]['CarrierID']))
                return  # Exit the function to avoid posting

            try:
                r = requests.post('http://127.0.0.1:8080/api/SendTransferCommand', json=mcs_cmd)
                print('>>status_code', r.status_code)
                if r.status_code == 200: #and mcs_cmd['CommandID'] .startswith('E'):
                    if mcs_cmd['CommandID'].startswith('E'):
                        self.erack_work_list.append(mcs_cmd)
                        print('>>erack_work_list:', self.erack_work_list)
                    self.logger.debug('<<<SendTransferCommand>>>: mcs_cmd: {}'.format(mcs_cmd))
                else:
                    self.logger.error('Failed to send MCS cmd: HTTP {} - {}'.format(r.status_code, r.text))
            except requests.exceptions.RequestException as e:
                self.logger.error('Error during SendTransferCommand: {}'.format(str(e)))
        else:
            remotecmd_queue.append(obj) 

    def cancel_transfer(self, obj):  # for USG# 2023/12/15
        if global_variables.field_id == 'USG3':
            mcs_cmd={
                'CommandID': obj['CommandID']
            }
            try:
                r=requests.post('http://127.0.0.1:8080/api/CancelTransferCommand', json=mcs_cmd)
                print('>>status_code', r.status_code, '>>data', mcs_cmd)
                if r.status_code == 200:
                    # self.erack_work_list.remove(mcs_cmd)
                    self.remove_erack_work_list_by_workID(mcs_cmd['CommandID'])
                    print('>>erack_work_list:', self.erack_work_list)
                    self.logger.debug('<<<CancelTransferCommand>>>: mcs_cmd: {}'.format(mcs_cmd))
                else:
                    self.logger.error('Failed to cancel MCS cmd: HTTP {}'.format(r.status_code))
            except requests.exceptions.RequestException as e:
                self.logger.error('Error during CancelTransferCommand: {}'.format(str(e)))

        else:
            remotecmd_queue.append(obj)  # remotecmd_queue.appendleft(obj)

    def recovery_work_list(self, workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, destport, replace, status, cause, couples=[]):
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
            'Cause':cause,
            'Couples': couples #2025/02/24 for UTAC USG1
        }
        self.my_lock.acquire()
        self.work_list.append(work)
        self.my_lock.release()

    def add_work_list(self, workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, couples=[]): #chocp add for UTAC couples
        # for usg1 SAW 2023/12/06
        status='INIT' if couples else 'WAITING'
        #print('<<add_work_list_1>>:', workID, carrierID, carrierType, lotID,  location, next_step, machine, priority, couples, status)
        if global_variables.RackNaming in [13, 35]:
            if global_variables.field_id == 'USG3':
                destport=None
                dest_h=None
                loc=tools.find_point(location)
                er_floor=global_variables.PoseTable.mapping[loc].get('z')  # 0, 1
                if er_floor is None:
                    self.logger.error("No Floor info: {} ".format(loc))
                    return

                if 'CrossFloor' in next_step:  # CrossFloor Lot
                    lot_stage='CrossFloor'
                    eq_floor=1 - er_floor
                    destport='DumPortLevel2_upper' if er_floor == 0 else 'DumPortLevel1_upper'

                else:
                    # lot_stage=next_step.split('-')[1]
                    try:
                        lot_stage = next_step.split('-')[1]
                    except IndexError:
                        self.logger.debug("Stage info format error:{}".format(next_step))
                        lot_stage = 'NA'
                    first_workstation=machine.split(',')[0].strip() if machine.strip() else ''

                    if first_workstation:  # machine is not empty
                        port_mapping={
                            'OVN002_1': 'OVN002_1_1',
                            'OVN002_2': 'OVN002_2_3'
                        }
                        first_workstation_port=port_mapping.get(first_workstation, first_workstation + '_1')

                        try:
                            first_workstation_point=tools.find_point(first_workstation_port)
                            eq_floor=global_variables.PoseTable.mapping[first_workstation_point].get('z')
                        except Exception:
                            eq_floor=tools.get_floor_from_api(first_workstation_port)
                            print("Using fallback eq_floor from API: {}".format(eq_floor))

                            if eq_floor is False:
                                self.logger.debug("Floor could not be determined from API for port: {}".format(first_workstation_port))
                                # print("Floor could not be determined from API for port: {}".format(first_workstation_port))
                                return  # Exit if no floor data could be obtained
                    else:
                        eq_floor=1 - er_floor
                        print('eq_floor:{}, er_floor:{}'.format(eq_floor, er_floor))

                destport=machine if eq_floor == er_floor else ('DumPortLevel2_upper' if er_floor == 0 else 'DumPortLevel1_upper')

                if destport:
                    dest_h=self.parent.workstations.get(destport)

                if dest_h:
                    try:
                        rackid, portnum=location.split('_')
                        h_eRack=Erack.h.eRacks.get(rackid)
                        if not h_eRack:
                            self.logger.debug("eRack not found: {}".format(rackid))
                            return
                        for_stage=h_eRack.func.get('LotIn', 'NoStage')
                        # print('for_stage_check', for_stage)
                        portnum_numeric=int(portnum[2:])  # Directly extract the integer part from the string
                        sector_name=h_eRack.carriers[portnum_numeric - 1]['area_id']
                    except Exception:
                        print("Error processing location '{}': {}".format(location, traceback.format_exc()))
                        return

                    print('sector', sector_name)
                    if 'SuperHot' in sector_name:
                        priority = 99
                    elif 'Hot' in sector_name:
                        priority = 80
                    else:
                        priority = 0

                    back_erack=dest_h.back_erack
                    obj={}
                    uuid=100*time.time() % 1000000000000  # chocp add 2021/11/7
                    obj['remote_cmd']='transfer_format_check'
                    obj['commandinfo']={
                        'CommandID': 'E%.12d' % uuid, 'Priority': priority, 'Replace': 0}
                    obj['transferinfolist']=[
                        {'Source': location, 'CarrierID': carrierID, 'CarrierType': carrierType, 'Dest': back_erack}]
                    # remotecmd_queue.append(obj)
                    self.send_transfer(obj)  # for USG# 2023/12/15
                    print('Send to MCS', obj)
                    # tools.book_slot(new_dest_port)
                    # dest_h.command_id_list.append(obj['commandinfo']['CommandID'])
                    return

            else:
                # Check LotIn stage
                rackid, portnum=location.split('_')
                h_eRack=Erack.h.eRacks.get(rackid)
                for_stage=h_eRack.func.get('LotIn', 'NoStage')
                for_stage_list=[str(stage.strip()) for stage in for_stage.split(',')]
                # print('for_stage_check1', for_stage)
                if next_step == 'NA':
                    return
                next_step_stage=next_step.split('-')[1] if '-' in next_step else next_step
                next_step_stage=str(next_step_stage.strip())
                # print('split next_step', next_step_stage)
                if next_step_stage not in for_stage_list :
                    print('for_stage_check2', for_stage_list, next_step, next_step_stage)
                    return
                else:
                    print('for_stage_check3', for_stage, next_step)
                    pass
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
                alarms.RtdOrderIdDuplicatedInList(workID, carrierID)
                return

        if global_variables.field_id == 'USG1ASSY':
            # Check the status of couples work orders and update the current work order accordingly
            # for couple_carrier_id in couples:
            if couples:
                couple_carrier_id=couples[0]
                # print('<<couples_check>>:', couple_carrier_id)
                couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                # print('<<couple_WorkID>>:', couple_WorkID, couple_Work_status, couple_Work_dest, couple_carid)
                # If the couple work order is in 'INIT' state or has been dispatched or completed,
                # then set the current work order to 'WAITING' and update 'DestPort' if necessary
                if couple_Work_status in ['INIT', 'DISPATCH', 'SUCCESS']:
                    # self.my_lock.acquire()
                    # print('<<couple_Work_status>>:', couple_Work_status)
                    # try:
                    work['Status']='WAITING'
                    if couple_Work_status in ['DISPATCH', 'SUCCESS']:
                        machine=couple_Work_dest.split('_')[0]
                        # work['Machine']=couple_Work_dest.split('_')[0]
                        with self.my_lock:
                            work['Machine']=machine
                            work['Priority']=100 # ??? why mark
                    # finally:
                    #     self.my_lock.release()
        last_couple_index=None
        insertion_point=len(self.work_list)
        with self.my_lock:
            for i, existing_work in enumerate(self.work_list):
                # check if couple_work in work_list
                if couples and existing_work['CarrierID'] in couples:
                    last_couple_index=i
                    break

                if int(priority) > int(existing_work['Priority']):
                    insertion_point=i
                    break

            if last_couple_index is not None:
                self.work_list.insert(last_couple_index + 1, work)
                # print("Inserted {} after its couple at index {}".format(work['WorkID'], last_couple_index + 1))
            else:
                self.work_list.insert(insertion_point, work)
                # if insertion_point == len(self.work_list) - 1:
                #     print("Appended {} at the end of work_list".format(work['WorkID']))
                # else:
                #     print("Inserted {} based on priority at index {}".format(work['WorkID'], insertion_point))
        #print('<<add_work_list_2>>:', workID, carrierID, carrierType,
        #      lotID,  location, next_step, machine, priority, couples, status)
        output('WorkPlanListAdd', work, True) #need try to trigger dispatch
        return

    def update_work_status(self, workID, status, cause, location=None, machine=None, priority=None):
        for work in self.work_list:
            if work['WorkID'] in workID: #chocp fix, make xxxx in  xxxxx-LOAD
                # self.my_lock.acquire()
                with self.my_lock:
                    work['Status']=status
                    work['Cause']=cause
                    if location:
                        work['Location']=location
                    # for utac usg1 SAW
                    if machine:
                        work['Machine']=machine
                    if priority is not None:
                        work['Priority']=priority
                    # self.my_lock.release()

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
                        self.logger.debug('Work: {} status is SUCCESS, Check couple work: {}, should_remove?: {}'.format(work['WorkID'], work['Couples'], should_remove))
                        if not should_remove:
                            return

                    if should_remove:
                        self.remove_work_list_by_workID(work['WorkID']) #need change load only
                        # print('<<remove_work_list_by_workID>>:', self.work_list)
                        if work['Couples']: #Only for UTAC USG1 SAW
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
                self.logger.debug("UpdateWorkLocation: {} into Location: {}".format(work, location))
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
                self.logger.debug("WorkPlanListRemove: {}".format(work))
                self.my_lock.release()
                break

    def remove_erack_work_list_by_workID(self, workID):
        self.my_lock.acquire()
        try:
            for cmd in self.erack_work_list:
                if workID.startswith(cmd['CommandID']):
                    self.erack_work_list.remove(cmd)
                    self.logger.debug('Remove mcs_cmd in erack_work_list: {}'.format(cmd['CommandID']))
                    break
        finally:
            self.my_lock.release()

    def cancel_work_list_by_workID(self, workID):

        for work in self.work_list:
            if work['WorkID'] == workID:
                # self.my_lock.acquire()
                # self.work_list.remove(work)
                # self.my_lock.release()
                with self.my_lock:
                    self.work_list.remove(work)

                output('WorkPlanListUpdate', {'WorkID':workID, 'Status':'CANCEL'}) # race condition?
                output('WorkPlanListRemove', {'WorkID':workID}, True)

                # print('<< cancel_work_list_by_workID: {} >>'.format(work['WorkID']))
                #print('<< alarm_reset, workstation: {} >>'.format(portID))
                #EqMgr.getInstance().trigger(portID, 'alarm_reset')

                if work['Status']=='DISPATCH':
                    obj_load={}
                    obj_load['remote_cmd']='cancel'
                    obj_load['CommandID']=work['WorkID']+'-LOAD' #not use workID, maybe workID have -Load or -UnLoad suffix
                    remotecmd_queue.append(obj_load)
                    # print('<< cancel relative transfer: {} >>'.format(obj_load['CommandID']))

                    obj_unload={}
                    obj_unload['remote_cmd']='cancel'
                    obj_unload['CommandID']=work['WorkID']+'-UNLOAD' #not use workID, maybe workID have -Load or -UnLoad suffix
                    remotecmd_queue.append(obj_unload)
                    # print('<< cancel relative transfer: {} >>'.format(obj_unload['CommandID']))

                if global_variables.field_id == 'USG1ASSY':
                    # for utac usg1 SAW
                    couple_carrier_id = work.get('Couples', [None])[0]
                    if couple_carrier_id:
                    # for couple_carrier_id in work.get('Couples', []):
                        # print('<<couples_check>>:', couple_carrier_id)
                        couple_WorkID, couple_work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                        # print('<<couple_WorkID>>:', couple_WorkID, couple_work_status, couple_Work_dest, couple_carid)
                        if couple_work_status == 'WAITING':

                            self.update_work_status(couple_WorkID, 'INIT', 0)
                            # couple_WorkID, couple_work_status, couple_Work_dest, couple_carid=self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                            # print('<<couple_work_status>>:', work)
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

    def reset_work_list_priority(self, workID, priority): # for UTAC
        with self.my_lock:
            for i, work in enumerate(self.work_list):
                # print("",work)
                if work['WorkID'] == workID: #and work['CarrierID'] == carrierID:
                    # print('<<<<reset_wok_prior:{}>>>>'.format(workID))
                    # if work['CarrierID'] == carrierID:
                    # self.my_lock.acquire()
                    work['Status']='WAITING'
                    work['DestPort']=''
                    work['Replace']=0
                    work['Cause']=0
                    # print('prior_pre:', work['Priority'])
                    work['Priority']=int(priority)
                    # print('prior_pos:', int(priority))
                    if int(priority) == 0:
                        # print('<<work_remove>>:',work)
                        self.work_list.remove(work)
                        work['Priority']=int(priority)
                        # print('<<work_add>>:',work)
                        self.logger.debug('WorkAdd {} with priority "{}" from work_list'.format(work['WorkID'], work['Priority'] ))
                        self.work_list.append(work)
                        # print('<<new_work_list>>:',self.work_list)
                    if int(priority) != 0:
                        self.work_list.sort(key=lambda x: (x['Priority'] == 0, x['Priority']))

                    output('WorkPlanListUpdate', work)
                    # print('<<worklist:{}, workID:{}, prior:{}'.format(self.work_list, workID, work['Priority']))
                    break

        for index, work in enumerate(self.work_list, start=1):
            print('<<work_index:{}, workID:{}, prior:{}'.format(index, work['WorkID'], work['Priority']))
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
        return ('', '', '', [])

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
    # for MCS
    def query_erack_work_list_by_carrierID(self, carrierID):
        res=''
        for erack_work in self.erack_work_list:
            if erack_work['Transfer'][0]['CarrierID'] == carrierID:
                self.my_lock.acquire()
                res=erack_work
                self.my_lock.release()
                break
        if res:
            return erack_work['CommandID']
        return ''
    def infoupdate_work_list_by_carrierID(self, carrierID, lotID, stage, machine, priority):
        res2=''
        for work in self.work_list:
            if global_variables.RackNaming in [13,35]:
                if work['CarrierID'] == carrierID and work['LotID'] == lotID:
                    res2=work

                    if global_variables.field_id == 'USG1ASSY':
                        # couples_status_update_needed = False
                        if 'Couples' in work and work['Couples']:
                            for couple_carrier_id in work['Couples']:
                                # res2 = work
                                _, couple_work_status, couple_Work_dest, _ = self.query_work_list_by_carrierID_for_utac(couple_carrier_id)
                                print('<<couples_status>>:', couple_carrier_id, couple_work_status)
                                self.logger.debug("<<couples_status>>:{}, {}".format(couple_carrier_id, couple_work_status))
                                '''if couple_work_status not in ['SUCCESS', 'FAIL']:  # ???

                                    # work['Machine'] = couple_Work_dest.split('_')[0]
                                    # work['Priority'] = 100
                                    print('<<couples_status_update_needed>>:', couple_carrier_id, couple_work_status)
                                    self.logger.debug("<<couples_status_update_needed>>:{}, {}".format(couple_carrier_id, couple_work_status))
                                    couples_status_update_needed = True
                                    break'''

                                if couple_work_status in ['FAIL', 'WAITING']:
                                    self.my_lock.acquire()
                                    work['Status']='INIT'
                                    work['Machine']=machine
                                    work['Priority']=priority
                                    work['DestPort']=''
                                    self.my_lock.release()
                                    output('WorkPlanListUpdate', work)
                                    break

                                elif couple_work_status in ['INIT', 'DISPATCH, ''SUCCESS']:
                                    self.my_lock.acquire()
                                    work['Status']='WAITING'
                                    work['Priority']=priority
                                    if couple_work_status in ['DISPATCH', 'SUCCESS']:
                                        machine=couple_Work_dest.split('_')[0]
                                        work['Machine']=machine
                                        work['Priority']=100
                                    work['DestPort']=''
                                    self.my_lock.release()
                                    output('WorkPlanListUpdate', work)
                                    break

                        else:
                            if work['Status'] == 'FAIL':
                                self.my_lock.acquire()
                                work['Status']='WAITING'
                                work['Machine']=machine
                                work['Priority']=priority
                                work['DestPort']=''
                                self.my_lock.release()
                                output('WorkPlanListUpdate', work)
                                break

                        # if couples_status_update_needed or not work['Couples']:
                        #     res2 = work
                        #     if work['LotID'] == lotID and work['Stage'] == stage and work['Machine'] == machine and work['Priority'] == priority:
                        #         break
                        #     self.my_lock.acquire()
                        #     work['Status'] = 'WAITING'
                        #     work['LotID'] = lotID
                        #     work['Stage'] = stage
                        #     work['Machine'] = machine
                        #     work['Priority'] = priority
                        #     work['DestPort'] = ''
                        #     self.my_lock.release()
                        #     output('WorkPlanListUpdate', work)
                        #     break
                    else:
                        if work['Status'] == 'FAIL':
                            self.my_lock.acquire()
                            work['Status']='WAITING'
                            work['Machine']=machine
                            work['Priority']=priority
                            work['DestPort']=''
                            self.my_lock.release()
                            output('WorkPlanListUpdate', work)
                            break

                else:
                    print('Work Not Found!!')

            elif work['CarrierID'] == carrierID:
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

                    if global_variables.field_id == 'USG1ASSY':
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