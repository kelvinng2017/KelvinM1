import collections
import traceback
import threading
import re
import time

import semi.e82_equipment as E82
import semi.e88_equipment as E88
import semi.e88_stk_equipment as E88STK

from pprint import pformat

import global_variables

import logging.handlers as log_handler
import logging

from workstation.eq_mgr import EqMgr

from global_variables import remotecmd_queue
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host
from global_variables import Erack

from global_variables import PortsTable
from global_variables import PoseTable
from global_variables import output
from global_variables import Vehicle
from global_variables import Equipment
from global_variables import M1_global_variables
from threading import Timer
import copy
import tools
import alarms

import tr_wq_lib
from  tr_wq_lib import TransferWaitQueue
from web_service_log import *

class TSC(threading.Thread):
    def __init__(self, secsgem_e82_h, secsgem_e88_h, secsgem_e88_stk_h):

        self.secsgem_e82_default_h=secsgem_e82_h
        self.secsgem_e88_default_h=secsgem_e88_h
        self.secsgem_e88_stk_default_h=secsgem_e88_stk_h

        E82.report_event(self.secsgem_e82_default_h, E82.TSCAutoInitiated)
        self.mTscState='TSCInitiated'
        self.mControlState=False
        self.mLastControlState=False

        self.mCommunicationState='' #'Not communication'
        self.mLastCommunicationState='' #'Not communication'
        self.secsgem_e82_default_h.TSCState=1
        self.batch_timeout=0
        self.run_tsc=False
        self.use_e82=True
        self.check_source_dest_is_other=True

        self.zone_data={}
        self.last_zone_data={}

        self.vehicle_dispatch_delay={}

        if self.secsgem_e88_default_h:
            E88.report_event(self.secsgem_e88_default_h, E88.SCAutoInitiated)
            self.mScState='SCInitiated'
            self.mScControlState=False
            self.mScLastControlState=False

            self.mScCommunicationState='' #'Not communication'
            self.mScLastCommunicationState='' #'Not communication'
            self.secsgem_e88_default_h.SCState=1
            self.run_sc=False

        if self.secsgem_e88_stk_default_h:
            self.secsgem_e88_stk_default_h.initial()
            self.secsgem_e88_stk_default_h.resume()
            # E88.report_event(self.secsgem_e88_stk_default_h, E88STK.SCAutoInitiated)
            self.mSTKcState='SCInitiated'
            self.mSTKcControlState=False
            self.mSTKcLastControlState=False

            self.mSTKcCommunicationState='' #'Not communication'
            self.mSTKcLastCommunicationState='' #'Not communication'
            self.run_sc=False

        self.logger=logging.getLogger("tsc")

        self.heart_beat=0
        threading.Thread.__init__(self)


    def racklevel_overhigh_handler(self, h_eRack):
        rack_available=0

        for dest_racks in h_eRack.returnto.split(','): # chi change split '|,' to ',' , '|'
            for rackID in dest_racks.strip().split('|'): #for xxx|xxx|xxx
                h=Erack.h.eRacks.get(rackID)
                if h:
                    rack_available+=h.available #chi remove avaiable '.()'


        if h_eRack.batchsize<=rack_available:
            sorted_carriers=sorted(h_eRack.carriers, key=lambda carrier: carrier['create_time'], reverse=False)
            dispatched=0
            for carrier in sorted_carriers:
                idx=carrier['idx']
                if carrier['carrierID'] and carrier['status'] == 'up' and not h_eRack.lots[idx]['machine'] and dispatched<h_eRack.batchsize:
                    uuid=100*time.time()
                    uuid%=1000000000000
                    CommandInfo={'CommandID':'E%.12d'%uuid, 'Replace':0, 'Priority':0, 'TransferState':1}
                    TransferInfoList=[{'CarrierID':carrier['carrierID'], 'SourcePort':'*', 'DestPort':h_eRack.returnto}]

                    assert_error, code, ack, alarm, stageList=tr_wq_lib.transfer_format_check(self.secsgem_e82_default_h, CommandInfo['CommandID'], TransferInfoList)

                    if not assert_error:
                        self.add_transfer_cmd(CommandInfo, TransferInfoList)
                        h_eRack.lots[idx]['machine']='ReturnToErack' #self.returnto #xxx|yyy,zzz need check???? 2022/4/29  chi change self to h_eRack
                        dispatched+=1

    def decide_service_zone_common(self, tr_cmd):
        candidate_zones=[]
        candidate_link_zones=[]
        candidate_priority_zones=[] #priority to workstation

        RackToRackTransfer=False
        rack_detect_flag=False
        s_zoneID='other'
        d_zoneID='other'
        matching_zones=[]
        taskSourceDestZone={}
        if global_variables.global_crossZoneLink:
            s_workstation=EqMgr.getInstance().workstations.get(tr_cmd['source'])
            if s_workstation:
                s_zoneID=getattr(s_workstation, 'zoneID', 'other')
            else: 
                res, rack_id, port_no=tools.rackport_format_parse(tr_cmd['source'])
                if res:
                    h_eRack=Erack.h.eRacks.get(rack_id)
                    if h_eRack:
                        s_zoneID=getattr(h_eRack, 'zone', 'other')
                        
            d_workstation=EqMgr.getInstance().workstations.get(tr_cmd['dest'])
            if d_workstation:
                d_zoneID=getattr(d_workstation, 'zoneID', 'other')
            else: 
                res, rack_id, port_no=tools.rackport_format_parse(tr_cmd['dest'])
                if res:
                    h_eRack=Erack.h.eRacks.get(rack_id)
                    if h_eRack:
                        d_zoneID=getattr(h_eRack, 'zone', 'other')
                        
            taskSourceDestZone['From']=s_zoneID
            taskSourceDestZone['To']=d_zoneID
            matching_zones = [(zone, d['handlingType']) for zone, items in global_variables.global_crossZoneLink.items()
                  for d in items if d['From'] == taskSourceDestZone['From'] and d['To'] == taskSourceDestZone['To']]
            if matching_zones:
                belonging_zones, handling_type = matching_zones[0]
                tr_cmd['handlingType']=handling_type
                return belonging_zones, False  

        for port_type, portID in [('Source', tr_cmd['source']), ('Dest', tr_cmd['dest'])]:
            zoneID=portID.split('BUF')[0]
            self.logger.debug("port_type:{},portID:{}".format(port_type, portID))
            if zoneID in list(Vehicle.h.vehicles.keys()): #port in vehicle
                return zoneID, True

            if port_type == 'Dest' and (portID == '*' or portID == 'E0P0' or portID == ''): #for preTransfer
                print('Branch 1:', candidate_zones)
                return candidate_zones.pop(), False

            h_workstation=EqMgr.getInstance().workstations.get(portID)
            if h_workstation:
                if h_workstation.workstation_type=='ErackPort':
                    if rack_detect_flag:
                        RackToRackTransfer=True
                    rack_detect_flag=True
                    #zoneID=getattr(h_workstation, 'zoneID', 'other')
                    
                        
                        
                    zoneID=getattr(h_workstation, 'zoneID', 'other')
                    candidate_link_zones.append(zoneID)
                else:
                    zoneID=getattr(h_workstation, 'zoneID', 'other')
                    candidate_zones.append(zoneID)
                    candidate_link_zones.append(getattr(h_workstation, 'link_zone', 'other'))
                    candidate_priority_zones.append(zoneID)
                    print('Branch 2:', candidate_zones, candidate_link_zones, candidate_priority_zones)
                continue

            res, rack_id, port_no=tools.rackport_format_parse(portID)
            if res:
                h_eRack=Erack.h.eRacks.get(rack_id)
                if h_eRack and not 'TurnTable' in h_eRack.model:
                    if rack_detect_flag:
                        RackToRackTransfer=True

                    rack_detect_flag=True

                    zoneID=getattr(h_eRack, 'zone', 'other')
                    candidate_zones.append(zoneID)
                    candidate_link_zones.append(getattr(h_eRack, 'link_zone', 'other'))
                    print('Branch 3:', candidate_zones, candidate_link_zones, candidate_priority_zones)
                    continue

            candidate_zones.append('other')
            candidate_link_zones.append('other')
        #end for loop

        if global_variables.TSCSettings.get('CommandDispatch', {}).get('DivideMethod') == 'ByDestPort':
            candidate_zones=candidate_zones[::-1]
            candidate_link_zones=candidate_link_zones[::-1]
            candidate_priority_zones=candidate_priority_zones[::-1]
            if global_variables.RackNaming == 21:  #240625 Hshuo for ASECL M11 if plasma overflow then priority=99
                if len(set(candidate_priority_zones)) > 1 and tr_cmd['dest'] not in['Out','ASRS']:
                    tr_cmd["priority"]=99
                elif len(set(candidate_priority_zones)) == 1 and tr_cmd['dest'] not in['Out','ASRS']:
                    if tr_cmd["priority"] != 100:
                        tr_cmd["priority"]=3

        if global_variables.TSCSettings.get('CommandDispatch', {}).get('DivideMethodByMachinePior') == 'yes':
            for zoneID in candidate_priority_zones:
                if zoneID != 'other':
                    return zoneID, False

        if RackToRackTransfer:
            test_zones=candidate_link_zones
        else:
            test_zones=candidate_zones

        print('Branch 4:', RackToRackTransfer, test_zones)

        for zoneID in test_zones:
            if zoneID != 'other' and zoneID != 'None': #fix 2023/11/9 chocp
                return zoneID, False

        return 'other' , False

    def transfer_cancel(self, host_command_id, cause):
        res=False
        queueID=''
        cancel_success=False
        host_command_detail=tools.find_command_detail_by_commandID(host_command_id)                       
        E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelInitiated, {'CommandID':host_command_id,'CommandInfo':host_command_detail.get('CommandInfo',''),'TransferCompleteInfo':host_command_detail.get('OriginalTransferCompleteInfo','')})

        for queue_id, wq in TransferWaitQueue.getAllInstance().items():
            print('In transfer_cancel, try lock acquire')
            wq.wq_lock.acquire() #8.21-4
            try:

                res, host_tr_cmd=wq.remove_waiting_transfer_by_commandID(host_command_id, cause)
                if res:
                    wq.stop_vehicle=False
                    wq.preferVehicle=''
                    queueID=queue_id
                    cancel_success=True
                    if global_variables.RackNaming == 40 and wq.lot_list:
                        to_remove = []
                        for handling_type in ['In', 'Out']:
                            if handling_type in wq.lot_list:
                                for lot_id, lot_info in wq.lot_list[handling_type].items():
                                    if host_command_id in lot_info['CommandID']:
                                        lot_info['CommandID'].remove(host_command_id)

                                    if len(lot_info['CommandID']) < lot_info['QUANTITY']:
                                        lot_info['dispatch'] = False

                                    if len(lot_info['CommandID']) == 0 and (handling_type, lot_id) not in to_remove:
                                        to_remove.append((handling_type, lot_id))

                        for handling_type, lot_id in to_remove:
                            del wq.lot_list[handling_type][lot_id]
                        print(wq.lot_list)
                    #self.secsgem_e82_default_h.rm_transfer_cmd(host_command_id)
                    # E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelCompleted, {'CommandID':host_command_id}) #2022/6/30

                    for transferinfo in host_tr_cmd['TransferInfoList']:
                        host_tr_cmd['TransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':transferinfo['SourcePort']}) #bug, need check
                    for transferinfo in host_tr_cmd['OriginalTransferInfoList']:
                        CarrierID=transferinfo['CarrierID']
                        CarrierLoc=transferinfo['SourcePort']
                        if CarrierID in self.secsgem_e82_default_h.ActiveCarriers:
                            CarrierLoc=self.secsgem_e82_default_h.ActiveCarriers[CarrierID]["RackID"]+self.secsgem_e82_default_h.ActiveCarriers[CarrierID]["SlotID"]
                        host_tr_cmd['OriginalTransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':CarrierLoc}) #bug, need check

                    E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelCompleted, {
                                'CommandInfo':host_tr_cmd['CommandInfo'],
                                'CommandID':host_tr_cmd['uuid'],
                                'TransferCompleteInfo':host_tr_cmd['OriginalTransferCompleteInfo'], #9/13
                                'TransferInfo':host_tr_cmd['OriginalTransferInfoList'][0] if host_tr_cmd['OriginalTransferInfoList'] else {},
                                'CommandID':host_tr_cmd['CommandInfo'].get('CommandID', ''),
                                'Priority':host_tr_cmd['CommandInfo'].get('Priority', 0),
                                'Replace':host_tr_cmd['CommandInfo'].get('Replace', 0),
                                'CarrierID':host_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                'SourcePort':host_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                'DestPort':host_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                #'CarrierLoc':self.action_in_run['loc'],
                                'CarrierLoc':host_tr_cmd['dest']}) #chocp fix for tfme 2021/10/23
                    output('TransferCancelCompleted', {'CommandID':host_command_id})

                    if global_variables.TSCSettings.get('Safety', {}).get('SkipCancelLoadWhenUnloadCancel', 'no') == 'no': #8.25.9-2
                        if host_tr_cmd.get('link'): #check with link cmd, also need delete
                            link_tr_cmd=host_tr_cmd.get('link')
                            E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelInitiated, {'CommandID':link_tr_cmd.get('uuid',), 'CommandInfo':link_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':link_tr_cmd.get('OriginalTransferCompleteInfo','')})
                            res, link_tr_cmd_return=wq.remove_waiting_transfer_by_commandID(link_tr_cmd.get('uuid'), cause='by link') #chocp 2023/11/13
                            if res:
                                for transferinfo in link_tr_cmd['TransferInfoList']:
                                    link_tr_cmd['TransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':transferinfo['SourcePort']}) #bug, need check
                                for transferinfo in link_tr_cmd['OriginalTransferInfoList']:
                                    CarrierID=transferinfo['CarrierID']
                                    CarrierLoc=transferinfo['SourcePort']
                                    if CarrierID in self.secsgem_e82_default_h.ActiveCarriers:
                                        CarrierLoc=self.secsgem_e82_default_h.ActiveCarriers[CarrierID]["RackID"]+self.secsgem_e82_default_h.ActiveCarriers[CarrierID]["SlotID"]
                                    link_tr_cmd['OriginalTransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':CarrierLoc}) #bug, need check

                                # E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelCompleted, {'CommandID':link_tr_cmd.get('uuid')}) #2022/6/30
                                E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelCompleted, {
                                            'CommandInfo':link_tr_cmd['CommandInfo'],
                                            'CommandID':link_tr_cmd['uuid'],
                                            'TransferCompleteInfo':link_tr_cmd['OriginalTransferCompleteInfo'], #9/13
                                            'TransferInfo':link_tr_cmd['OriginalTransferInfoList'][0] if link_tr_cmd['OriginalTransferInfoList'] else {},
                                            'CommandID':link_tr_cmd['CommandInfo'].get('CommandID', ''),
                                            'Priority':link_tr_cmd['CommandInfo'].get('Priority', 0),
                                            'Replace':link_tr_cmd['CommandInfo'].get('Replace', 0),
                                            'CarrierID':link_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                            'SourcePort':link_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                            'DestPort':link_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                            #'CarrierLoc':self.action_in_run['loc'],
                                            'CarrierLoc':link_tr_cmd['dest']}) #chocp fix for tfme 2021/10/23
                                output('TransferCancelCompleted', {'CommandID':link_tr_cmd.get('uuid')})
                            else:
                                E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelFailed, {'CommandID':link_tr_cmd.get('uuid'), 'CommandInfo':link_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':link_tr_cmd.get('OriginalTransferCompleteInfo','')})

                    #??? how to deal link command???
                    if host_tr_cmd.get('sourceType') == 'FromVehicle': #8.21N-2
                        temp_vehicle_buf=host_tr_cmd['source']
                        buf_vehicle_id=temp_vehicle_buf.split('BUF00')[0] # must be 'BUF00'
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if vehicle_id == buf_vehicle_id:
                                # h_vehicle.doPreDispatchCmd=False
                                vehicle_wq=TransferWaitQueue.getInstance(h_vehicle.id)
                                for queue in vehicle_wq.relation_links: #for FST, clear vehicle waiting queue relationship queue
                                    queue.preferVehicle=''
                                link_host_command_id='PRE-'+host_command_id
                                E82.report_event(self.secsgem_e82_default_h, E82.TransferAbortInitiated, {'CommandID':link_host_command_id})
                                abort_res=h_vehicle.abort_tr_cmds_and_actions(link_host_command_id, 40002, 'Transfer command in exectuing queue be aborted', cause='by link', check_link=False)
                                if not abort_res:
                                    E82.report_event(self.secsgem_e82_default_h, E82.TransferAbortFailed, {'CommandID':link_host_command_id})
                                    for idx in range(h_vehicle.bufNum):
                                        if link_host_command_id == h_vehicle.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('uuid'):
                                            if h_vehicle.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'):
                                                h_vehicle.bufs_status[idx]['local_tr_cmd_mem']['host_tr_cmd']['preTransfer']=False

                wq.wq_lock.release()
            except:
                wq.wq_lock.release()
                msg=traceback.format_exc()
                self.logger.info('Handling queue:{} in transfer_cancel() with a exception:\n {}'.format(wq.queueID, msg))
                pass

        if not cancel_success:
            E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelFailed, {'CommandID':host_command_id,'CommandInfo':host_command_detail.get('CommandInfo',''),'TransferCompleteInfo':host_command_detail.get('OriginalTransferCompleteInfo','')})

        return res, queueID

    def stage_completed(self, stage_id, host_tr_cmd, obj):
        print('> in stage_completed')
        # check if stage is in waiting queue
        host_command_id=host_tr_cmd['uuid']
        new_host_priority=host_tr_cmd['priority']
        for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
            if stage_id not in zone_wq.transfer_list:
                continue
            for waiting_command_id, waiting_tr_cmd in zone_wq.transfer_list.items(): #have lock or race condition problem???
                if waiting_command_id == stage_id:
                    print('> find stage id in waiting queue')

                    if waiting_tr_cmd['dest'] != host_tr_cmd['dest']:
                        print('> new dest found!')
                        waiting_tr_cmd['dest']=host_tr_cmd['dest']
                        waiting_tr_cmd['destType']=host_tr_cmd['destType']
                        waiting_tr_cmd['TransferInfoList']=host_tr_cmd['TransferInfoList']
                        waiting_tr_cmd['OriginalTransferInfoList']=host_tr_cmd['OriginalTransferInfoList']

                    # replace tr_cmd uuid
                    zone_wq.my_lock.acquire()
                    try:
                        waiting_tr_cmd['uuid']=host_command_id
                        waiting_tr_cmd['stage']=False
                        print(waiting_tr_cmd)
                        zone_wq.transfer_list[host_command_id]=zone_wq.transfer_list[stage_id]
                        del zone_wq.transfer_list[stage_id]
                        if stage_id in zone_wq.linked_list:
                            zone_wq.linked_list.remove(stage_id)
                            zone_wq.linked_list.append(host_command_id)

                        try:
                            # if obj:
                            if obj and obj.get('system'): #from secs
                                if hasattr(obj['handle'], 'add_transfer_cmd'):
                                    ActiveTransfers=E82.get_variables(obj['handle'], 'ActiveTransfers')
                                    ActiveTransfers[host_command_id]=ActiveTransfers[stage_id]
                                    ActiveTransfers[host_command_id]['CommandInfo']['CommandID']=host_command_id
                                    ActiveTransfers[host_command_id]['TransferInfo']=host_tr_cmd['TransferInfoList']
                                    del ActiveTransfers[stage_id]
                                    E82.update_variables(obj['handle'], {'ActiveTransfers': ActiveTransfers})
                                if hasattr(obj['handle'], 'Transfers'):
                                    obj['handle'].Transfers.mod(stage_id, host_command_id)
                                    obj['handle'].Transfers.set(host_command_id, {'Dest':host_tr_cmd['dest']})
                            else:
                                if hasattr(self.secsgem_e82_default_h, 'add_transfer_cmd'):
                                    ActiveTransfers=E82.get_variables(self.secsgem_e82_default_h, 'ActiveTransfers')
                                    ActiveTransfers[host_command_id]=ActiveTransfers[stage_id]
                                    ActiveTransfers[host_command_id]['CommandInfo']['CommandID']=host_command_id
                                    ActiveTransfers[host_command_id]['TransferInfo']=host_tr_cmd['TransferInfoList']
                                    del ActiveTransfers[stage_id]
                                    E82.update_variables(self.secsgem_e82_default_h, {'ActiveTransfers': ActiveTransfers})

                        except:
                            pass

                        print('> replace stage id by real transfer id')
                    except:
                        pass
                    zone_wq.my_lock.release()

                    # remove stage cmd from waiting queue
                    output('TransferWaitQueueRemove', {'CommandID':stage_id}, True)

                    # add real transfer cmd into waiting queue
                    output('TransferWaitQueueAdd', {
                            'Channel':waiting_tr_cmd.get('channel', 'Internal'), #chocp 2022/6/13
                            'Idx':0,
                            'CarrierID':waiting_tr_cmd['carrierID'],
                            'CarrierType':waiting_tr_cmd['TransferInfoList'][0].get('CarrierType', ''), #chocp 2022/2/9

                            'ZoneID':waiting_tr_cmd['zoneID'],  #chocp 9/14
                            'Source':waiting_tr_cmd['source'],
                            'Dest':host_tr_cmd['dest'],
                            'CommandID':waiting_tr_cmd["uuid"],
                            'TransferInfoList':waiting_tr_cmd['TransferInfoList'],
                            # 'Priority':waiting_tr_cmd["priority"] if not waiting_tr_cmd.get('original_priority','') else waiting_tr_cmd['original_priority'],
                            'Priority':new_host_priority,
                            'Replace':waiting_tr_cmd['replace'],
                            'Back':waiting_tr_cmd['back'],
                            'OperatorID':host_tr_cmd.get('operatorID', '')
                            }, True)
                    
                    print('change stage priority {} to transfer priority {}'.format(waiting_tr_cmd["priority"], new_host_priority))
                    zone_wq.change_transfer_priority(host_command_id, new_host_priority)
                    break
            else:
                continue
            print('> check if pre-dispatch command in vehicle')
            stage_id='PRE-'+stage_id
            host_command_id='PRE-'+host_command_id

        # check if stage is executing
        vehicle_id=''
        h_vehicle=0
        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
            if stage_id in h_vehicle.CommandIDList:
                break
        else:
            print('> no stage command or pre-dispatch command in vehicle')
            return
        print('> find stage id in vehicle')

        # replace tr_cmd uuid
        local_tr_cmd={}
        for local_tr_cmd in h_vehicle.tr_cmds:
            if local_tr_cmd['uuid'] == stage_id:
                print('> replace stage id by host cmd id in vehicle transfer queue')
                local_tr_cmd['uuid']=host_command_id
                local_tr_cmd['host_tr_cmd']['uuid']=host_command_id
                local_tr_cmd['host_tr_cmd']['CommandInfo']['CommandID']=host_command_id
                try:
                    # if obj:
                    if obj and obj.get('system'): #from secs
                        if hasattr(obj['handle'], 'add_transfer_cmd'):
                            ActiveTransfers=E82.get_variables(obj['handle'], 'ActiveTransfers')
                            ActiveTransfers[host_command_id]=ActiveTransfers[stage_id]
                            ActiveTransfers[host_command_id]['CommandInfo']['CommandID']=host_command_id
                            ActiveTransfers[host_command_id]['TransferInfo']=host_tr_cmd['TransferInfo']
                            del ActiveTransfers[stage_id]
                            E82.update_variables(obj['handle'], {'ActiveTransfers': ActiveTransfers})
                        if hasattr(obj['handle'], 'Transfers'):
                            obj['handle'].Transfers.mod(stage_id, host_command_id)
                            obj['handle'].Transfers.set(host_command_id, {'Dest':host_tr_cmd['dest']})
                    else:
                        if hasattr(self.secsgem_e82_default_h, 'add_transfer_cmd'):
                            ActiveTransfers=E82.get_variables(self.secsgem_e82_default_h, 'ActiveTransfers')
                            ActiveTransfers[host_command_id]=ActiveTransfers[stage_id]
                            ActiveTransfers[host_command_id]['CommandInfo']['CommandID']=host_command_id
                            ActiveTransfers[host_command_id]['TransferInfo']=host_tr_cmd['TransferInfo']
                            del ActiveTransfers[stage_id]
                            E82.update_variables(self.secsgem_e82_default_h, {'ActiveTransfers': ActiveTransfers})

                except:
                    pass
                break

        # send unassign for stage cmd
        '''E82.report_event(h_vehicle.secsgem_e82_h,
                    E82.VehicleUnassigned,{
                    'VehicleID':vehicle_id,
                    'CommandIDList':[stage_id],
                    'CommandID':stage_id,
                    'BatteryValue':h_vehicle.adapter.battery['percentage']})'''
        '''output('VehicleUnassigned',{
                'Battery':h_vehicle.adapter.battery['percentage'],
                'Charge':h_vehicle.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':h_vehicle.adapter.online['connected'],
                'Health':h_vehicle.adapter.battery['SOH'],
                'MoveStatus':h_vehicle.adapter.move['status'],
                'RobotStatus':h_vehicle.adapter.robot['status'],
                'RobotAtHome':h_vehicle.adapter.robot['at_home'],
                'VehicleID':vehicle_id,
                'VehicleState':h_vehicle.AgvState,
                'TransferTask':{'VehicleID':vehicle_id, 'Action':'', 'CommandID':'', 'CarrierID':'', 'Dest':'', 'ToPoint':''},
                'Message':h_vehicle.message,
                'ForceCharge':h_vehicle.force_charge,
                'CommandIDList':[stage_id]}) #may be include fail cmd'''
        output('TransferExecuteQueueRemove', {'CommandID':stage_id}, True)

        # send assign for real transfer cmd
        h_vehicle.CommandIDList.append(host_command_id)
        E82.report_event(h_vehicle.secsgem_e82_h, E82.TransferInitiated, {'CommandID':host_command_id,'CommandInfo':local_tr_cmd.get('host_tr_cmd', {}).get('CommandInfo', {}),'TransferCompleteInfo':local_tr_cmd.get('host_tr_cmd', {}).get('OriginalTransferCompleteInfo', {})})
        output('TransferInitiated',  {'CommandID':host_command_id})

        E82.report_event(h_vehicle.secsgem_e82_h,
                            E82.VehicleAssigned,{
                            'VehicleID':vehicle_id,
                            'CommandIDList':[host_command_id],
                            'CommandID':host_command_id,
                            'BatteryValue':h_vehicle.adapter.battery['percentage']})
        output('VehicleAssigned',{
            'Battery':h_vehicle.adapter.battery['percentage'],
            'Charge':h_vehicle.adapter.battery['charge'], #chocp 2022/5/20
            'Connected':h_vehicle.adapter.online['connected'],
            'Health':h_vehicle.adapter.battery['SOH'],
            'MoveStatus':h_vehicle.adapter.move['status'],
            'RobotStatus':h_vehicle.adapter.robot['status'],
            'RobotAtHome':h_vehicle.adapter.robot['at_home'],
            'VehicleID':vehicle_id,
            'VehicleState':h_vehicle.AgvState,
            'Message':h_vehicle.message,
            'ForceCharge':h_vehicle.force_charge, #???
            'CommandIDList':h_vehicle.CommandIDList})
        
        E82.report_event(h_vehicle.secsgem_e82_h, E82.Transferring, {'CommandID':host_command_id,'CarrierID':local_tr_cmd.get('carrierID', ''),'VehicleID':vehicle_id}) #8.24B-4
        output('Transferring', {'CommandID':host_command_id})

        output('TransferExecuteQueueAdd', {
                    'VehicleID':vehicle_id,
                    'CommandID':host_command_id,
                    'CarrierID':local_tr_cmd.get('carrierID', ''),
                    'Loc':local_tr_cmd.get('loc', ''),
                    'CarrierType':local_tr_cmd.get('TransferInfo', {}).get('CarrierType', ''), #chocp 2022/2/24
                    'Source':local_tr_cmd['source'],
                    'Dest':local_tr_cmd['dest'],
                    'Priority':local_tr_cmd['priority'],
                    'OperatorID':local_tr_cmd.get('host_tr_cmd', {}).get('operatorID', '')
                    }, True)

        # change action type
        for action in h_vehicle.actions:
            # print(action.get('local_tr_cmd', {}).get('uuid'), host_command_id)
            if action.get('local_tr_cmd', {}).get('uuid') == host_command_id:
                if action.get('type') == 'ACQUIRE_STANDBY':
                    print('> replace action type with ACQUIRE')
                    action['type']='ACQUIRE'
                if action.get('type') == 'DEPOSIT':
                    print('> replace action target with new dest')
                    action['taget']=host_tr_cmd['dest']
                    action['point']=tools.find_point(host_tr_cmd['dest'])
                    
    def host_transfer_abort(self, local_command_id, cause='by host'): #'by man', 'by host', 'by replace'
        res=False
        vehicleID=''

        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
            #chocp add this alarm 2021/1031
            for tr_cmd in h_vehicle.tr_cmds:
                uuid=tr_cmd['uuid']
                if cause=='by host':
                    if uuid.endswith('-LOAD'):
                        uuid=uuid[:-5]
                    elif uuid.endswith('-UNLOAD'):
                        uuid=uuid[:-7]
                if uuid == local_command_id:
                    if global_variables.RackNaming== 43 and h_vehicle.AgvState in ['Acquiring', 'Depositing']:
                        break
                    #local_command_id, result_code, result_txt, link_workstation=False, cause='by alarm'): #fix 6
                    res=h_vehicle.abort_tr_cmds_and_actions(local_command_id, 40002, 'Transfer command in exectuing queue be aborted', cause)
                    if res: #abort_tr_cmds_and_actions will respond abort complete
                        if tr_cmd['host_tr_cmd'].get('link'): #chi 2022/09/29
                            vehicleID=h_vehicle.id
                            break
                        else:
                            vehicleID=h_vehicle.id
                            break
            else:
                continue
            break

        return res, vehicleID


    def add_transfer_cmd(self, CommandInfo, TransferInfoList, channel='Internal', transfer_type='Normal', obj=None, stageIDList=None): #chocp remove stage 2022/6/9
        swap= False if len(TransferInfoList) == 1 else True
        if obj and not obj.get('system'):
            E82.report_event(self.secsgem_e82_default_h, E82.OperatorInitiatedAction, {'CommandID':CommandInfo['CommandID'], 'CommandType':'Transfer', 'CarrierID':TransferInfoList[0]['CarrierID'], 'SourcePort':TransferInfoList[0]['SourcePort'], 'DestPort':TransferInfoList[0]['DestPort'], 'Priority':CommandInfo['Priority']})

        host_tr_cmd={
            'stage':'StageID' in CommandInfo,
            'primary':1,
            'received_time':time.time(),
            'channel':channel,
            'uuid':CommandInfo.get('CommandID', ''),
            'carrierID':TransferInfoList[0]['CarrierID'],
            'source':TransferInfoList[0]["SourcePort"],
            'original_source':TransferInfoList[0]["SourcePort"],
            'dest':TransferInfoList[0]["DestPort"],
            'sourceType':'Normal', #for StockOut
            'destType':'Normal', #for StockOut
            'BufConstrain':False, #for BufConstrain
            'bufferAllowedDirections':'All', #for Buflimite
            'priorityBuf':None,
            'zoneID':'other', #9/14
            'priority':int(CommandInfo.get('Priority', 0)),
            'replace':1 if swap else 0,
            'back': TransferInfoList[1]["DestPort"] if swap else '',
            'CommandInfo':CommandInfo,
            'TransferCompleteInfo':[],
            'OriginalTransferCompleteInfo':[],
            'TransferInfoList':TransferInfoList,
            'OriginalTransferInfoList':copy.deepcopy(TransferInfoList),
            'link':None,
            'equipmentID':'',
            'operatorID':obj.get('operatorID', '') if obj else '',
            'Residence_Time':TransferInfoList[0].get('QTime', 1000) if transfer_type == "pre_transfer" else 2000#Yuri 10/21
        }
        
        
        h_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest']) #add for Buf Constrain
        if h_workstation:
            if h_workstation.workstation_type in ["LotIn&LotOut", "LotIn&ECOut", "LotOut&ECIn"]: #add for StockOut
                host_tr_cmd['destType']='WorkStation'

            
        print(obj)
        print(host_tr_cmd)
        print(stageIDList)

        if stageIDList:
            for stageID in stageIDList:
                if obj.get('system'): #from secs
                    self.stage_completed(stageID, host_tr_cmd, obj)
                    if hasattr(obj['handle'], 'add_transfer_cmd'):
                        obj['handle'].add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': host_tr_cmd['OriginalTransferInfoList']}) # Mike: 2021/09/22
                    if hasattr(obj['handle'], 'Transfers'):
                        obj['handle'].transfer_cmd(CommandInfo['CommandID'], CommandInfo['Priority'], TransferInfoList[0]['CarrierID'], TransferInfoList[0]['SourcePort'], TransferInfoList[0]['DestPort'])
                    #self.secsgem_e82_default_h.send_response(self.secsgem_e82_default_h.stream_function(2,50)([4]), obj['system'])
                    obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])
                else:
                    if hasattr(self.secsgem_e82_default_h, 'add_transfer_cmd'):
                        self.stage_completed(stageID, host_tr_cmd, obj)
                        self.secsgem_e82_default_h.add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': host_tr_cmd['OriginalTransferInfoList']}) # Mike: 2021/09/22
            return

        host_tr_cmd['preTransfer']=True if '*' in host_tr_cmd['dest'] or host_tr_cmd['dest'][:-5] in Vehicle.h.vehicles or transfer_type == 'pre_transfer' else False #chocp 2023/7/26  8.27.4-1

        #chocp 2024/8/21 for shift
        #try:
        source_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['source'])
        dest_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest'])
        if global_variables.RackNaming in [33, 58]:
            if source_workstation and (not source_workstation.valid_input or '_OUT_OK' in source_workstation.workstationID) and global_variables.RackNaming == 58:
                host_tr_cmd['BufConstrain']=True
                host_tr_cmd['bufferAllowedDirections']='Bottom'
            if source_workstation:    
                if '_OUT_OK' in source_workstation.workstationID:
                    host_tr_cmd['priorityBuf'] = source_workstation.limitBuf 
                elif not source_workstation.valid_input and dest_workstation:
                    host_tr_cmd['priorityBuf'] = dest_workstation.limitBuf
                elif '_OUT_NG' in source_workstation.workstationID:
                    host_tr_cmd['priorityBuf'] = source_workstation.limitBuf 
        
        elif (source_workstation and source_workstation.BufConstrain) or (dest_workstation and dest_workstation.BufConstrain): #add for Buf Constrain
            host_tr_cmd['BufConstrain']=True
            if source_workstation and dest_workstation and source_workstation.BufConstrain and dest_workstation.BufConstrain:
                if global_variables.TSCSettings.get('CommandDispatch', {}).get('DivideMethod') == 'ByDestPort':
                    host_tr_cmd['bufferAllowedDirections']=dest_workstation.limitBuf
                else:
                    if global_variables.RackNaming == 36:
                        self.logger.debug("jkjk:{}".format(dest_workstation.equipmentID))
                        host_tr_cmd['bufferAllowedDirections']=dest_workstation.limitBuf
                        self.logger.info("host_tr_cmd['bufferAllowedDirections']:{}".format(host_tr_cmd['bufferAllowedDirections']))
                        
                        
                    else:
                        host_tr_cmd['bufferAllowedDirections']=source_workstation.limitBuf
                        self.logger.info("host_tr_cmd['bufferAllowedDirections']:{}".format(host_tr_cmd['bufferAllowedDirections']))

                    
            elif source_workstation and source_workstation.BufConstrain:
                host_tr_cmd['bufferAllowedDirections']=source_workstation.limitBuf
                
            elif dest_workstation and dest_workstation.BufConstrain:
                host_tr_cmd['bufferAllowedDirections']=dest_workstation.limitBuf
        
        if dest_workstation:
            if source_workstation and dest_workstation: 
                if source_workstation.allow_shift and not host_tr_cmd['replace']:
                    source_point = tools.find_point(host_tr_cmd['source'])
                    dest_point = tools.find_point(host_tr_cmd['dest'])
                    if (source_point == dest_point): 
                        host_tr_cmd['shiftTransfer'] = True
                        print('find a shift cmd from port {} to port {}, at point {}'.format(host_tr_cmd['source'], host_tr_cmd['dest'], source_point))
                if dest_workstation.allow_shift and host_tr_cmd['replace']:
                    source_point = tools.find_point(host_tr_cmd['source'])
                    dest_point = tools.find_point(host_tr_cmd['dest'])
                    if (source_point == dest_point): 
                        host_tr_cmd['shiftTransfer'] = True
                        print('find a shift cmd from port {} to port {}, at point {}'.format(host_tr_cmd['source'], host_tr_cmd['dest'], source_point))
            else:
                if dest_workstation.allow_shift and host_tr_cmd['replace'] and 'BUF' not in host_tr_cmd['back'][-5:]:
                    dest_point = tools.find_point(host_tr_cmd['dest'])
                    back_point = tools.find_point(host_tr_cmd['back'])
                    if (dest_point == back_point):  
                        host_tr_cmd['shiftTransfer'] = True
                        print('find a shift cmd from port {} to port {}, at point {}'.format(host_tr_cmd['dest'], host_tr_cmd['back'], dest_point))
        #except:
        #    pass
        #if 'MR' in host_tr_cmd['source']: #chocp add for SJ 2023/10/27
        # if host_tr_cmd['source'][:-5] in Vehicle.h.vehicles:
        #     host_tr_cmd['sourceType']='FromVehicle' #chocp add for SJ 2023/10/27

        #     buf_vehicle_id=host_tr_cmd['source'].split('BUF0')[0] #8.22J-1
        #     for vehicle_id, h_vehicle in Vehicle.h.vehicles.items(): #need fix for MRxxxBUF0X
        #         if vehicle_id == buf_vehicle_id:
        #             for i in range(h_vehicle.bufNum):
        #                 if host_tr_cmd['carrierID'] == h_vehicle.adapter.carriers[i]['status']:
        #                     if h_vehicle.bufs_status[i].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'): #8.25.7-1
        #                         host_tr_cmd['preTransfer']=True

        #                     h_vehicle.bufs_status[i]['local_tr_cmd']['host_tr_cmd']=host_tr_cmd
        #                     h_vehicle.bufs_status[i]['local_tr_cmd']['uuid']=CommandInfo.get('CommandID', '')

        stockout_queue_id=''

        h_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['source'])
        if h_workstation:
            if h_workstation.workstation_type in ['StockOut', 'StockIn&StockOut', 'LifterPort']: #add for StockOut
                host_tr_cmd['sourceType']='StockOut'
                stockout_queue_id=h_workstation.equipmentID

            if h_workstation.equipmentID:
                if global_variables.RackNaming == 22: #Hshuo 240807 for ASECL OVEN
                    if "Stock" in h_workstation.workstation_type:
                        hh_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest'])
                        host_tr_cmd['equipmentID']=hh_workstation.equipmentID
                    else:
                        # print("\n ASECL OVEN ASRS & PLASMA NOT SOURCE")
                        host_tr_cmd['equipmentID']=h_workstation.equipmentID
                # if  global_variables.RackNaming == 36:
                #     if "Erack" in h_workstation.workstation_type:
                #         hh_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest'])
                #         host_tr_cmd['equipmentID']=hh_workstation.equipmentID
                #     else:
                #         host_tr_cmd['equipmentID']=h_workstation.equipmentID  #2022/12/09        
                else:
                    host_tr_cmd['equipmentID']=h_workstation.equipmentID  #2022/12/09
        else: #Hshuo 240829 
            if global_variables.RackNaming == 22:
                hh_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest'])
                host_tr_cmd['equipmentID']=hh_workstation.equipmentID

        if global_variables.TSCSettings.get('Other', {}).get('PreDispatchForRack','') == 'yes': #chi 2022/11/15
            res, default_erack, port_no=tools.rackport_format_parse(host_tr_cmd['source'])
            if res:
                host_tr_cmd['sourceType']='ErackOut'

        # if h_workstation and h_workstation.BufConstrain: #add for Buf Constrain
        #     host_tr_cmd['BufConstrain']=True

        # h_workstation=EqMgr.getInstance().workstations.get(host_tr_cmd['dest']) #add for Buf Constrain
        # if h_workstation:
        #     if h_workstation.workstation_type in ["LotIn&LotOut", "LotIn&ECOut", "LotOut&ECIn"]: #add for StockOut
        #         host_tr_cmd['destType']='WorkStation'

        zoneID='other'
        isVehicleZone=False
        if global_variables.TSCSettings.get('CommandDispatch', {}).get('DivideDispatchZoneEnable') == 'yes':
            zoneID, isVehicleZone=self.decide_service_zone_common(host_tr_cmd)

        h_zone=TransferWaitQueue.getInstance(zoneID) #Hshuo 240805 for zone disable
        zone_enable=h_zone.enable
        if zone_enable == 'no': 
            print("\n!!!!!Service zone {} disable".format(zoneID))
            alarms.CommandZoneDisable(host_tr_cmd["uuid"],zoneID,handler=0)
            if obj and obj.get('system'):
                if hasattr(obj['handle'], 'rm_transfer_cmd'):
                    obj['handle'].rm_transfer_cmd(CommandInfo['CommandID']) # Mike: 2021/12/22
                if hasattr(obj['handle'], 'Transfers'):
                    obj['handle'].Transfers.delete(CommandInfo['CommandID'])
                    output('TransferParamsCheckReject', {'CommandID':host_tr_cmd["uuid"],\
                            'CommandInfo': CommandInfo,\
                            'TransferInfo': TransferInfoList,\
                            'ResultCode':40023,\
                            'Message':'Host transfer cmd, service zone disabled'})
                obj['handle'].send_response(obj['handle'].stream_function(2,50)([2, [["TRANSFERPORT",2]]]), obj['system'])
            return
        if transfer_type == 'pre_transfer':
            if 'BUF' in host_tr_cmd['dest']:
                pattern = r"BUF(?!00)"
                match = re.search(pattern, host_tr_cmd['dest'])
                if not match:
                    host_tr_cmd['dest']='*'
                    host_tr_cmd['TransferInfoList'][0]["DestPort"]='*'
            else:
                host_tr_cmd['dest']='*'
                host_tr_cmd['TransferInfoList'][0]["DestPort"]='*'

        print('=>zoneID: ', zoneID, isVehicleZone, host_tr_cmd)

        specifyMR=''
        waiting_tr_cmd={}
        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items(): # find preDispatch cmd in vehicle zone to link
            if zoneID in h_vehicle.serviceZone[0]:
                zone_wq=TransferWaitQueue.getInstance(vehicle_id)
                for waiting_command_id, waiting_tr_cmd in zone_wq.transfer_list.items():
                    if waiting_tr_cmd['dest'] == host_tr_cmd['source'] and not host_tr_cmd['replace'] and not waiting_tr_cmd.get('link'):
                        specifyMR=vehicle_id
                        print('find link cmd in vehicle {} waiting queue'.format(vehicle_id))
                        break
                else:
                    continue
                break

        if TransferInfoList[0].get('HostSpecifyMR'):  
            zoneID=TransferInfoList[0].get('HostSpecifyMR')
            print("HostSpecifyMR", zoneID)
            host_tr_cmd['zoneID']=zoneID
            host_tr_cmd['HostSpecifyMR']=zoneID
            TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_with_check(host_tr_cmd)
        elif specifyMR:
            zoneID=specifyMR
            print("specifyMR", zoneID)
            host_tr_cmd['zoneID']=waiting_tr_cmd['zoneID']
            host_tr_cmd['HostSpecifyMR']=zoneID
            TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_with_check(host_tr_cmd)
            print(TransferWaitQueue.getInstance(zoneID).queue)
        else:
            if isVehicleZone:
                host_tr_cmd['zoneID']=zoneID
                #search waiting unload transfer in all queue and change zone
                for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                    for waiting_tr_cmd in zone_wq.queue: #have lock or race condition problem???
                        if waiting_tr_cmd['source'] == host_tr_cmd['dest'] and not host_tr_cmd['replace'] and not waiting_tr_cmd.get('link'):
                            zone_wq.remove_transfer_from_queue_directly(waiting_tr_cmd)
                            TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_directly(waiting_tr_cmd)
                            break
                        elif waiting_tr_cmd['dest'] == host_tr_cmd['source'] and not host_tr_cmd['replace'] and not waiting_tr_cmd.get('link'):                  
                            zone_wq.remove_transfer_from_queue_directly(waiting_tr_cmd)
                            TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_directly(waiting_tr_cmd)
                            break
                    else:
                        continue
                    break
                #add load cmd
                TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_with_check(host_tr_cmd)
            elif host_tr_cmd['sourceType'] == 'StockOut' and stockout_queue_id and global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes': #make stock out a standalone waiting queue  2022/12/13 chocp
                #stockout need build a queue?
                host_tr_cmd['zoneID']=stockout_queue_id if global_variables.RackNaming !=8 else zoneID
                TransferWaitQueue.getInstance(stockout_queue_id).add_transfer_into_queue_with_check(host_tr_cmd)
            else:
                host_tr_cmd['zoneID']=zoneID
                TransferWaitQueue.getInstance(zoneID).add_transfer_into_queue_with_check(host_tr_cmd)

        tools.indicate_slot(host_tr_cmd['source'], host_tr_cmd['dest'])
        if global_variables.TSCSettings.get('Other', {}).get('BookLater', 'no') == 'no':
            tools.book_slot(host_tr_cmd['dest'])
            tools.book_slot(host_tr_cmd['back'])

        # if obj:
        if obj and obj.get('system'): #from secs
            if hasattr(obj['handle'], 'add_transfer_cmd'):
                obj['handle'].add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': host_tr_cmd['OriginalTransferInfoList']}) # Mike: 2021/09/22
            if hasattr(obj['handle'], 'Transfers'):
                obj['handle'].transfer_cmd(CommandInfo['CommandID'], CommandInfo['Priority'], TransferInfoList[0]['CarrierID'], TransferInfoList[0]['SourcePort'], TransferInfoList[0]['DestPort'])
            #self.secsgem_e82_default_h.send_response(self.secsgem_e82_default_h.stream_function(2,50)([4]), obj['system'])
            obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])
        else:
            if hasattr(self.secsgem_e82_default_h, 'add_transfer_cmd'):
                self.secsgem_e82_default_h.add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': host_tr_cmd['OriginalTransferInfoList']}) # Mike: 2021/09/22

        return

    def run(self):
        output('TSCUpdate', {'TSCState':'TSCAutoInitiated',  'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState})
        #output('STKCUpdate', {'STKCStatus':False, 'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING'})
        #output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCAutoInitiated', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState})
        while True:
            try:
                self.heart_beat=time.time()
                if self.secsgem_e88_default_h:
                    self.mScLastCommunicationState=self.mScCommunicationState
                    if self.secsgem_e88_default_h.communicationState.current == 'COMMUNICATING':
                        self.mScCommunicationState='COMMUNICATING'

                    elif self.secsgem_e88_default_h.communicationState.current == 'NOT_COMMUNICATING':
                        self.mScCommunicationState='NOT_COMMUNICATING'

                    else:
                        self.mScCommunicationState=self.secsgem_e88_default_h.communicationState.current

                    self.mScLastControlState=self.mScControlState
                    self.mScControlState=self.secsgem_e88_default_h.controlState.current

                    if self.mScLastCommunicationState != self.mScCommunicationState or self.mScLastControlState != self.mScControlState:
                        output('STKCUpdate', {'STKCStatus':True, 'STKCState':self.mScState, 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mLastCommunicationState})



                self.mLastCommunicationState=self.mCommunicationState

                if self.secsgem_e82_default_h.communicationState.current == 'COMMUNICATING':
                    #self.mCommunicationState='Host Online'
                    self.mCommunicationState='COMMUNICATING'

                elif self.secsgem_e82_default_h.communicationState.current == 'NOT_COMMUNICATING':
                    #self.mCommunicationState='Host Offline'
                    self.mCommunicationState='NOT_COMMUNICATING'

                else:
                    self.mCommunicationState=self.secsgem_e82_default_h.communicationState.current
                #print('mTscState={}, control={}'.format(self.mTscState, self.secsgem_e82_default_h.controlState.current))
                #if self.mLastCommunicationState != self.mCommunicationState:
                #    output('TSCUpdate', {'TSCState':self.mTscState, 'RemoteStatus':self.mCommunicationState})

                self.mLastControlState=self.mControlState

                self.mControlState=self.secsgem_e82_default_h.controlState.current

                if self.mLastCommunicationState != self.mCommunicationState or self.mLastControlState != self.mControlState:
                    output('TSCUpdate', {'TSCState':self.mTscState, 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState})

                #print(self.secsgem_e82_default_h.communicationState.current, self.secsgem_e82_default_h.controlState.current)
                #COMMUNICATION, NOT_OMMUNICATION, WAIT_DELAY, WAIT_CRA
                #handle remote command from host
                if len(remotecmd_queue)>0:
                    obj=remotecmd_queue.popleft()

                    print('pop get', obj)

                    if obj['remote_cmd'] == 'pause':
                        self.run_tsc=False

                    elif obj['remote_cmd'] == 'resume':
                        self.run_tsc=True

                    elif obj['remote_cmd'] == 'sc_pause': #chi 2022/08/09
                        self.run_sc=False

                    elif obj['remote_cmd'] == 'sc_resume': #chi 2022/08/09
                        self.run_sc=True

                    elif obj['remote_cmd'] == 'sc_online':
                        if self.secsgem_e88_default_h and self.secsgem_e88_default_h.controlState.current in ['OFFLINE', 'EQUIPMENT_OFFLINE']: #chocp fix 2022/7/12
                            self.secsgem_e88_default_h.control_switch_online()

                    elif obj['remote_cmd'] == 'sc_offline':
                        if self.secsgem_e88_default_h and self.secsgem_e88_default_h.controlState.current in ['ONLINE', 'ONLINE_LOCAL', 'ONLINE_REMOTE', 'HOST_OFFLINE']: #chocp fix 2022/7/12
                            self.secsgem_e88_default_h.control_switch_offline()

                    elif obj['remote_cmd'] == 'online':
                        if self.secsgem_e82_default_h.controlState.current in ['OFFLINE', 'EQUIPMENT_OFFLINE']:
                            self.secsgem_e82_default_h.control_switch_online()

                    elif obj['remote_cmd'] == 'offline':
                        if self.secsgem_e82_default_h.controlState.current in ['ONLINE', 'ONLINE_LOCAL', 'ONLINE_REMOTE', 'HOST_OFFLINE']:
                            self.secsgem_e82_default_h.control_switch_offline()

                    elif obj['remote_cmd'] == 'clean_error':
                        print('clean_error_cmd, code:{}, extend_code:{}'.format(obj['parameter']['code'], obj['parameter']['extend_code']))
                        output('AlarmClear', {'code':obj['parameter']['code'], 'extend_code':obj['parameter']['extend_code']})
                        '''
                        code=int(obj['parameter']['code'])
                        if code>=10000 and code<20000: #vehicel, 4XXXX TSC
                            h_vehicle.error_reset_cmd=True
                        '''
                        #only end
                    elif obj['remote_cmd'] == 'release':
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if h_vehicle.id == obj['parameter']['VehicleID']:
                                h_vehicle.error_reset_cmd=True
                                break #chocp:2021/3/7
                            
                    elif obj['remote_cmd'] == 'retry':
                        ack_params=[]
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if obj.get('system'): #from SECS
                                if h_vehicle.id == obj['VehicleID']:
                                    if h_vehicle.AgvState == 'Pause' and h_vehicle.action_in_run:
                                        h_vehicle.error_retry_cmd=True
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                                    else:
                                        ack_params.append(['VEHICLEID', 2])
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, ack_params]), obj['system'])
                                    break           
                            else:  #from UI
                                if h_vehicle.id == obj['parameter']['VehicleID']:
                                    if h_vehicle.AgvState == 'Pause' and h_vehicle.action_in_run:
                                        h_vehicle.error_retry_cmd=True
                                    else:
                                        output('VehicleRetryFailed', {'VehicleID':vehicle_id, 'message':'<-No action needs a retry. Please release the MR','RetryFail':True})
                                    break 

                    elif obj['remote_cmd'] == 'sweep':
                        '''
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if h_vehicle.id == obj['parameter']['VehicleID'] and h_vehicle.AgvState == 'Unassigned': #chocp :2021/7/20
                                h_vehicle.do_fault_recovery()
                                break #chocp:2021/3/7
                        '''
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if h_vehicle.id == obj['parameter']['VehicleID']:
                                h_vehicle.recovery_cmd=True
                                break #chocp:2021/3/7

                    elif obj['remote_cmd'] == 'charge':
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if h_vehicle.id == obj['parameter']['VehicleID'] and h_vehicle.AgvState == 'Unassigned': #chocp 2022/4/12
                                h_vehicle.charge_cmd=True
                                break #chocp:2021/3/7

                    elif obj['remote_cmd'] == 'associate': #from Host
                        try:
                            if obj['RACKID'] in list(Erack.h.eRacks.keys()): #chocp fix 2021/12/8
                                rack_id=obj['RACKID']
                                port_idx=int(obj['PORTID'])-1
                                carrierID=obj['CARRIERID']
                                data=obj['ASSOCIATEDATA']
                                p1=obj.get('ADDITION1', '')
                                p2=obj.get('ADDITION2', '')
                                p3=obj.get('ADDITION3', '')
                                more=[p1, p2, p3]

                                print(rack_id, port_idx, carrierID, data, p1)

                                h_eRack=Erack.h.eRacks[rack_id]

                                #if global_variables.RackNaming == 3: #for tfme chocp 2021/1024
                                if global_variables.TSCSettings.get('CommandCheck', {}).get('AssociateCarrierIDCheck') == 'yes':
                                    if carrierID == '' or h_eRack.carriers[port_idx]['carrierID']!=carrierID:
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [['CARRIERID', 2]]]), obj['system'])
                                        continue

                                h_eRack.eRackInfoUpdate({
                                            'cmd':'associate',
                                            'port_idx':port_idx,
                                            'carrierID':carrierID,
                                            'data':data,
                                            'addition':more})

                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                            else:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [['RACKID', 2]]]), obj['system'])

                        except:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3]), obj['system'])
                            pass

                    elif obj['remote_cmd'] == 'assginlot': #8.25.12-2
                        try:
                            carrierID=obj['CARRIERID']
                            destport =obj['DESTPORT']
                            res, target=tools.re_assign_source_port(carrierID)
                            if res:
                                res, rack_id, port_no=tools.rackport_format_parse(target)
                                if res:
                                    h_eRack=Erack.h.eRacks.get(rack_id)
                                    if h_eRack:
                                        h_eRack.eRackInfoUpdate({
                                                        'cmd':'assginlot',
                                                        'port_idx':port_no-1,
                                                        'carrierID':carrierID,
                                                        'destport':destport})

                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                            else:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [['CARRIERID', 2]]]), obj['system'])


                        except:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3]), obj['system'])
                            pass

                    elif obj['remote_cmd'] == 'infoupdate': #for e82+
                        try:
                            carrierID=obj['CarrierID']
                            rackID='None'
                            slotID='None'
                            locate_result=1
                            # 9/19
                            for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                                for port_no in range(1, h_eRack.slot_num+1, 1):
                                    carrier=h_eRack.carriers[port_no-1]
                                    if carrier['carrierID'] == carrierID and carrier['status'] == 'up':
                                        rackID=rack_id
                                        slotID='%d'%port_no
                                        locate_result=0
                                        break
                                else:
                                    continue
                                break

                            if not locate_result: #chocp fix 2021/12/8
                                print(rackID, slotID, carrierID, obj)
                                h_eRack=Erack.h.eRacks[rackID]

                                #if global_variables.RackNaming == 3: #for tfme chocp 2021/1024
                                if global_variables.TSCSettings.get('CommandCheck', {}).get('AssociateCarrierIDCheck') == 'yes':
                                    if carrierID == '' or h_eRack.carriers[int(slotID)-1]['carrierID']!=carrierID:
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [['CARRIERID', 2]]]), obj['system'])
                                        continue

                                h_eRack.eRackInfoUpdate({
                                            'cmd':'infoupdate',
                                            'port_idx':int(slotID)-1,
                                            'carrierID':carrierID,
                                            'data':obj})

                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])

                            else:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [['CARRIERID', 2]]]), obj['system'])

                        except:
                            traceback.print_exc()
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3]), obj['system'])
                            pass

                    elif obj['remote_cmd'] == 'abort': #force abort
                        CommandID=str(obj['CommandID'])
                        cause='by host' if obj.get('system') else 'by web'
                        
                        if cause =='by web' and obj.get('OperatorInitiated',''):
                            OperatorInitiated=obj.get('OperatorInitiated')
                            E82.report_event(self.secsgem_e82_default_h, E82.OperatorInitiatedAction, {'CommandID':CommandID, 'CommandType':'Abort', 'CarrierID':OperatorInitiated['CarrierID'], 'SourcePort':OperatorInitiated['SourcePort'], 'DestPort':OperatorInitiated['DestPort'], 'Priority':OperatorInitiated['Priority']})
                        command_detail=tools.find_command_detail_by_commandID(CommandID)                       
                        E82.report_event(self.secsgem_e82_default_h, E82.TransferAbortInitiated, {'CommandID':CommandID,'CommandInfo':command_detail.get('CommandInfo',''),'TransferCompleteInfo':command_detail.get('OriginalTransferCompleteInfo','')})
                        #output('TransferCancelInitiated', {'CommandID':CommandID})
                        
                        res, vehicleID=self.host_transfer_abort(CommandID, cause)
                        # if res:
                        #     E82.report_event(self.secsgem_e82_default_h, E82.TransferAbortCompleted, {'CommandID':CommandID})
                        if not res:
                            if obj.get('system'):
                                E82.report_event(obj['handle'], E82.TransferAbortFailed, {'CommandID':CommandID,'CommandInfo':command_detail.get('CommandInfo',''),'TransferCompleteInfo':command_detail.get('OriginalTransferCompleteInfo','')})
                            if cause == 'by web': #force do, remove UI residule
                                output('TransferExecuteQueueRemove', {'CommandID':CommandID}, True)


                    elif obj['remote_cmd'] == 'assert':

                        if obj.get('parameter'): #from UI
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                if h_vehicle.id == obj['parameter']['VehicleID']:
                                    h_vehicle.tr_assert={'Request':'', 'Result':obj['RESULT'], 'TransferPort':'Unknown', 'SendBy':'by web'} #chocp add 2021/12/21, 2022/6/15
                        else: #from host
                            print('Get assert host cmd:', obj['REQUEST'], obj['DESTPORT'], obj['RESULT'])

                            if obj['REQUEST'] == 'Load' or obj['REQUEST'] == 'UnLoad' or obj['REQUEST'] == 'Back' or obj['REQUEST'] == 'Swap' or obj['REQUEST'] == 'Shift':
                                try:
                                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                        if h_vehicle.action_in_run.get('target', '') == obj['DESTPORT']: # Mike: 2021/09/08
                                            default_tr_assert={'Request':obj['REQUEST'], 'Result':obj['RESULT'], 'TransferPort':obj['DESTPORT'], 'CarrierID':obj['CARRIERID'],'SendBy':'by host'} #chocp add 2021/12/21, 2022/6/15
                                            if obj.get('WAIT','') =='Enable':
                                                h_vehicle.wait_eq_operation=True
                                            if obj.get('HEIGHT',''):
                                                default_tr_assert['Height']=obj['HEIGHT']
                                            h_vehicle.tr_assert=default_tr_assert
                                            if global_variables.RackNaming == 36:#peter 240807
                                                self.logger.debug('assert obj:{}'.format(obj))
                                                if obj.get("RESULT",'') == 'NG':
                                                    global_variables.k11_ng_fault_port[h_vehicle.id]=obj.get("NGPORT",'')
                                                if obj.get("TYPE",'')!='':
                                                    self.logger.debug('obj.get("TYPE",''):{}'.format(obj.get("TYPE",'')))
                                                    self.logger.debug('h_vehicle.action_in_run:{}'.format(h_vehicle.action_in_run))
                                                    h_vehicle.action_in_run['local_tr_cmd']['TransferInfo']['CarrierType']=obj["TYPE"]
                                except:
                                    pass

                                if obj['REQUEST'] == 'Load':
                                    if obj['RESULT'] == 'OK':
                                        EqMgr.getInstance().trigger(obj['DESTPORT'], 'load_req_ok')
                                    else:
                                        EqMgr.getInstance().trigger(obj['DESTPORT'], 'load_req_ng')

                                elif obj['REQUEST'] == 'UnLoad' and obj['RESULT'] == 'OK':
                                    EqMgr.getInstance().trigger(obj['DESTPORT'], 'unload_req_ok')

                            elif obj['REQUEST'] == 'Unlock': ##from EQStatusReq response 2022/8/30
                                if obj['REQUEST'] == 'Load' and obj['RESULT'] == 'OK':
                                    EqMgr.getInstance().trigger(obj['DESTPORT'], 'load_req_ok')
                                elif obj['REQUEST'] == 'Unlock' and obj['RESULT'] == 'OK':
                                    EqMgr.getInstance().trigger(obj['DESTPORT'], 'unload_cmd_evt')
                                pass #need fix
                            
                            elif obj['REQUEST'] == 'None': 
                                try:
                                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                        local_tr_cmd=h_vehicle.action_in_run.get('local_tr_cmd', {})
                                        uuid=local_tr_cmd.get('uuid', '')
                                        carrierID=local_tr_cmd.get('carrierID', '')
                                        if uuid == obj['COMMANDID'] and carrierID ==obj['CARRIERID']: # Mike: 2021/09/08
                                            h_vehicle.tr_assert={'Request':obj['REQUEST'], 'Result':obj['RESULT'], 'TransferPort':obj['DESTPORT'], 'CarrierID':obj['CARRIERID'],'SendBy':'by host'} #chocp add 2021/12/21, 2022/6/15
                                except:
                                    pass

                            #not sure the code for what?
                            '''elif obj['REQUEST'] == 'Add': ## chocp 8.23C-2
                                stocker_queue_h=TransferWaitQueue.getInstance(obj['DESTPORT'])
                                if stocker_queue_h:
                                    stocker_queue_h.tr_assert={'Request':'Add', 'Result':obj['RESULT'], 'TransferPort':obj['DESTPORT']}
                                    print('add test get:')
                                    print(stocker_queue_h.tr_assert)
                                pass
                            '''

                    elif obj['remote_cmd'] == 'EQState': #for Jcet, Utac
                            print('Get EQState host cmd:', obj['EQinfo'], obj['portinfolist'])
                            EQStatus=obj['EQinfo'].get('EQStatus', 0)
                            portinfolist=obj.get('portinfolist', [])
                            #portinfolist can't be empty list in pratice
                            real_port_status={}
                            real_carrierID={}
                            real_carrierType={}
                            for portinfo in portinfolist:
                                PortStatus=portinfo.get('PortStatus', 0)
                                PortID=portinfo.get('PortID', '')
                                if PortID:
                                    real_port_status[PortID]=PortStatus
                                    real_carrierID[PortID]=portinfo.get('CarrierID', '')
                                    real_carrierType[PortID]=portinfo.get('CarrierType', '') #from 2023/10/25

                            equipmentID=obj['EQinfo'].get('EQID', '')
                            workstation_list=EqMgr.getInstance().equipments.get(equipmentID, [])
                            for workstation in workstation_list:
                                PortID=getattr(workstation, "workstationID", '')
                                #USG1-3F workstation bug, only update if PortID exists in real_port_status
                                if PortID in real_port_status:
                                    PortStatus=real_port_status.get(PortID, 0)
                                    carrierID=real_carrierID.get(PortID, '')
                                    carrierType=real_carrierType.get(PortID, '')
                                    EqMgr.getInstance().trigger(PortID, 'remote_port_state_set', {'EQStatus':EQStatus, 'PortStatus':PortStatus, 'CarrierID':carrierID, 'CarrierType':carrierType})



                    elif obj['remote_cmd'] == 'PortState': #for Jcet, Utac
                            #print('Get PortState host cmd:', obj)
                            EqMgr.getInstance().trigger(obj.get('PortID',''), 'remote_port_state_set', {'PortStatus': obj.get('PortStatus', 0), 'CarrierID': obj.get('CarrierID', ''),  'CarrierType': obj.get('CarrierType', '')})

                    elif obj['remote_cmd'] == 'ResetAllPortState': #for Jcet
                            for workstationID, h in EqMgr.getInstance().workstations.items():
                                EqMgr.getInstance().trigger(workstationID, 'alarm_reset')

                    elif obj['remote_cmd'] == 'locate':
                        carrierID=obj['CARRIERID']
                        rackID='None'
                        slotID='None'
                        locate_result=1
                        # 9/19
                        for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                            for port_no in range(1, h_eRack.slot_num+1, 1):
                                carrier=h_eRack.carriers[port_no-1]
                                if carrier['carrierID'] == carrierID and carrier['status'] == 'up':
                                    rackID=rack_id
                                    slotID='%d'%port_no
                                    locate_result=0
                                    break
                            else:
                                continue
                            break
                        else:
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                for i in range(h_vehicle.bufNum):
                                    buf=h_vehicle.adapter.carriers[i]
                                    if buf['status'] == carrierID:
                                        target='%s%s'%(h_vehicle.id, h_vehicle.vehicle_bufID[i])
                                        rackID=h_vehicle.id
                                        slotID=h_vehicle.vehicle_bufID[i]
                                        locate_result=0

                        if obj.get('system'):
                            E82.report_event(obj['handle'],
                                        E82.LocateComplete, {
                                        'CarrierID':carrierID,
                                        'RackID':rackID,
                                        'SlotID':slotID,
                                        'LocateResult':locate_result})

                    elif obj['remote_cmd'] == 'stage':
                        if global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes':
                            print(obj)
                            obj['commandinfo']=obj['stageinfo']
                            CommandInfo=obj['stageinfo']
                            CommandInfo['CommandID']=obj['stageinfo'].get('StageID', '0')
                            CommandInfo["TransferState"]=1
                            TransferInfoList=obj['transferinfolist']
                            HostSpecifyMRList=obj.get('VEHICLEID',[])
                            for idx, HostSpecifyMR in enumerate(HostSpecifyMRList):
                                TransferInfoList[idx]['HostSpecifyMR']=str(HostSpecifyMR) if HostSpecifyMR else '' #chocp 2022/1/4

                            obj['remote_cmd']='transfer_format_check'
                            remotecmd_queue.append(obj)
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,50)([1]), obj['system'])

                    elif obj['remote_cmd'] == 'pre_transfer': #8.27.13
                        CommandInfo=obj['commandinfo']
                        TransferInfoList=obj['transferinfolist']
                        #for tfme add 2011001
                        next_from=TransferInfoList[0].get('DestPort', '*')
                        if next_from:
                            TransferInfoList[0]['DestPort']='*'
                            assert_error, code, ack, alarm, stageList=tr_wq_lib.transfer_format_check(self.secsgem_e82_default_h, CommandInfo['CommandID'], TransferInfoList)
                            if assert_error:
                                obj['handle'].rm_transfer_cmd(CommandInfo['CommandID']) # Mike: 2021/12/22
                                obj['handle'].send_response(obj['handle'].stream_function(2,50)([code, ack]), obj['system'])
                                output('TransferParamsCheckReject', {'CommandID':alarm.command_id,\
                                        'CommandInfo': CommandInfo,\
                                        'TransferInfo': TransferInfoList,\
                                        'ResultCode':alarm.code,\
                                        'Message':alarm.txt})
                            else:
                                TransferInfoList[0]['DestPort']=next_from
                                obj['handle'].add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': TransferInfoList}) # Mike: 2021/09/22
                                obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])
                                self.add_transfer_cmd(CommandInfo, TransferInfoList, 'SecsGem', 'pre_transfer') #cocp 2022/6/13


                    elif obj['remote_cmd'] == 'host_transfer' or obj['remote_cmd'] == 'transfer': #from host cmd or UI command
                        #print('from host transfer or UI manual transfer', obj)
                        CommandInfo=obj['commandinfo']
                        CommandInfo["TransferState"]=1
                        TransferInfoList=obj['transferinfolist']
                        executeTime=obj.get('EXECUTETIME', [''])[0]
                        HostSpecifyMR = obj.get('VEHICLEID',[''])[0]
                        '''
                        carrierTypeList=obj.get('CARRIERTYPE', [])
                        if carrierTypeList:
                            for idx, carrierType in enumerate(carrierTypeList):
                                TransferInfoList[idx]['CarrierType']=carrierType if carrierType else 'None'
                        executeTimeList=obj.get('EXECUTETIME', [])
                        for idx, executeTime in enumerate(executeTimeList):
                            TransferInfoList[idx]['ExecuteTime']=int(executeTime) if executeTime else 0 #chocp 2022/1/4
                        '''

                        for idx, TransferInfo in enumerate(TransferInfoList):
                            TransferInfo['ExecuteTime']=int(executeTime) if executeTime else 0 #chocp 2022/1/4
                            TransferInfo['HostSpecifyMR']=str(HostSpecifyMR) if HostSpecifyMR else '' #chocp 2022/1/4

                        if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes' and obj.get('system'): #only for RTD mode, chocp fix 2023/9/18
                            #self.secsgem_e82_default_h.send_response(self.secsgem_e82_default_h.stream_function(2,50)([4]), obj['system'])
                            obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])

                            h_workstation=EqMgr.getInstance().workstations.get(TransferInfoList[0]["SourcePort"])
                            if not TransferInfoList[0].get('CarrierID'):
                                TransferInfoList[0]['CarrierID']=''

                            if h_workstation:
                                carrierID=TransferInfoList[0]["CarrierID"]
                                print('Get a unload cmd from {}, carrierID:{}'.format(TransferInfoList[0]["SourcePort"], carrierID))
                                EqMgr.getInstance().trigger(TransferInfoList[0]["SourcePort"], 'unload_cmd_evt', {'CarrierID': carrierID, 'DestPort': TransferInfoList[0]["DestPort"]}) #chocp 2022/6/7
                            else: #unloading if DestPort is workstation. from Erack Dashboard or host
                                work={}
                                work['workID']=CommandInfo['CommandID']
                                work['CarrierID']=TransferInfoList[0]['CarrierID']
                                work['CarrierType']=TransferInfoList[0].get('CarrierType', '')
                                work['LotID']=''
                                work['Stage']=''
                                work['Machine']=TransferInfoList[0]["DestPort"]
                                work['Priority']=CommandInfo["Priority"]

                                work['Couples']=[] #chocp 2023/9/7 for UTAC couples
                                obj={'remote_cmd':'work_add', 'workinfo':work}

                                remotecmd_queue.append(obj)
                        else: # nor RTD mode
                            if CommandInfo['CommandID'] == '' or CommandInfo['CommandID'] == 0 or CommandInfo['CommandID'] == '0': #chocp add 2021/7/7
                                uuid=100*time.time()%1000000000000
                                if obj.get('system'):
                                    CommandInfo['CommandID']='H%.12d'%uuid
                                else:
                                    CommandInfo['CommandID']='U%.12d'%uuid
                            elif CommandInfo['CommandID']:
                                CommandInfo['CommandID']=str(CommandInfo['CommandID'])

                            obj['remote_cmd']='transfer_format_check'
                            remotecmd_queue.append(obj)

                    elif obj['remote_cmd'] == 'transfer_format_check':
                        CommandInfo=obj['commandinfo']
                        TransferInfoList=obj['transferinfolist']
                        StageIDList=obj.get('stageIDlist', []) # currently not support multiple transfer
                        #for tfme add 2011001
                        if int(CommandInfo.get('Replace', 0)):
                            if len(TransferInfoList) == 1:
                                next_from=TransferInfoList[0].get('DestPort', '*')
                                TransferInfo={'CarrierID':'', 'SourcePort':next_from, 'DestPort':'*'}
                                TransferInfoList.append(TransferInfo)

                        assert_error, code, ack, alarm, stageList=tr_wq_lib.transfer_format_check(obj.get('handle'), CommandInfo['CommandID'], TransferInfoList, 'StageID' in CommandInfo, StageIDList)
                        # print('> transfer_format_check result', assert_error, code, ack, alarm, stageList)
                        #end check
                        if assert_error:
                            if obj.get('system'): #from secs
                                if hasattr(obj['handle'], 'rm_transfer_cmd'):
                                    obj['handle'].rm_transfer_cmd(CommandInfo['CommandID']) # Mike: 2021/12/22
                                if hasattr(obj['handle'], 'Transfers'):
                                    obj['handle'].Transfers.delete(CommandInfo['CommandID'])
                                #self.secsgem_e82_default_h.send_response(self.secsgem_e82_default_h.stream_function(2,50)([code, ack]), obj['system'])
                                obj['handle'].send_response(obj['handle'].stream_function(2,50)([code, ack]), obj['system'])
                            #fix CommandInfo['CommandID'] to alarm.command_id for database deal commandID duplicator
                            output('TransferParamsCheckReject', {'CommandID':alarm.command_id,\
                                    'CommandInfo': CommandInfo,\
                                    'TransferInfo': TransferInfoList,\
                                    'ResultCode':alarm.code,\
                                    'Message':alarm.txt})

                            if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes':
                                if '-UNLOAD' not in CommandInfo['CommandID']:
                                    EqMgr.getInstance().orderMgr.update_work_status(CommandInfo['CommandID'], 'FAIL', alarm.txt) #cancel cmd by man
                        else:
                            transfer_type="pre_transfer" if any(item in TransferInfoList[0]["DestPort"] for item in ["BUF","*"]) else "Normal" #Yuri 2024/11/22
                            self.add_transfer_cmd(CommandInfo, TransferInfoList, 'SecsGem' if obj.get('system') else 'WebApi', transfer_type=transfer_type, obj=obj, stageIDList=stageList) #cocp 2022/6/13

                    elif obj['remote_cmd'] == 'recovery_transfer': #recovery transfer cmd in waiting queue, no check

                        CommandInfo=obj['commandinfo']
                        TransferInfoList=obj['transferinfolist']

                        self.add_transfer_cmd(CommandInfo, TransferInfoList)

                    elif obj['remote_cmd'] == 'host_change': #for spil 5, 6

                        CommandInfo=obj['commandinfo']
                        TransferInfoList=obj['transferinfolist']

                        carrierID=TransferInfoList[0]['CarrierID']
                        if carrierID == '' or carrierID == 'None':
                            obj['handle'].send_response(obj['handle'].stream_function(2,50)([3, [["CARRIERID", 2]]]), obj['system'])

                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            if h_vehicle.AgvState == 'TrLoadReq' and h_vehicle.action_in_run.get('local_tr_cmd',{}).get('carrierID') == carrierID:
                                dest_port=TransferInfoList[0]['DestPort']
                                carrierType=TransferInfoList[0].get('CarrierType', '')

                                res, new_dest_port=tools.new_auto_assign_dest_port(dest_port, carrierType)
                                if res:
                                    h_vehicle.tr_assert={'Result':'CHANGE', 'CarrierID':carrierID, 'NewDestPort':new_dest_port, 'SendBy':'by host'} #chocp add 2021/12/21
                                    obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])
                                else:
                                    obj['handle'].send_response(obj['handle'].stream_function(2,50)([3, [["DESTPORT", 2]]]), obj['system'])

                                break
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,50)([3, [["CARRIERID", 2]]]), obj['system'])

                    elif obj['remote_cmd'] == 'host_reassign':

                        carrierID=obj['CarrierID']
                        commandID=obj['CommandID']

                        if commandID in ['', '0'] and carrierID in ['', 'None', 'ReadFail', 'Unknown']:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2], ["CARRIERID", 2]]]), obj['system'])
                            continue

                        dest_port=obj['DestPort']
                        res, new_dest_port=tools.new_auto_assign_dest_port(dest_port, '') #NG???
                        if res:
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                if commandID not in ['', '0'] and commandID.split('-LOAD')[0].split('-UNLOAD')[0] not in h_vehicle.CommandIDList:
                                    continue

                                if h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid') == commandID \
                                        and h_vehicle.action_in_run.get('type','') == 'DEPOSIT' and h_vehicle.AgvState == 'Enroute':
                                    if 'PRE-' in h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid'):
                                        # print('??? >>>', h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid'))
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                                        break
                                    h_vehicle.action_in_run['target']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['dest']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['TransferInfo']['DestPort']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['OriginalTransferInfo']['DestPort']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['host_tr_cmd']['dest']=new_dest_port
                                    h_vehicle.change_target=True
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([4]), obj['system'])
                                    output('TransferExecuteQueueUpdate', {'CommandID':commandID, 'Dest': new_dest_port}, True)
                                    self.logger.debug('reassign in run {} to {} by commandID'.format(carrierID, new_dest_port))
                                    break
                                elif h_vehicle.action_in_run.get('local_tr_cmd',{}).get('carrierID') == carrierID \
                                        and h_vehicle.action_in_run.get('type','') == 'DEPOSIT' and h_vehicle.AgvState == 'Enroute':
                                    if 'PRE-' in h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid'):
                                        # print('??? >>>', h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid'))
                                        obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                                        break
                                    h_vehicle.action_in_run['target']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['dest']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['TransferInfo']['DestPort']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['OriginalTransferInfo']['DestPort']=new_dest_port
                                    h_vehicle.action_in_run['local_tr_cmd']['host_tr_cmd']['dest']=new_dest_port
                                    h_vehicle.change_target=True
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([4]), obj['system'])
                                    output('TransferExecuteQueueUpdate', {'CommandID':h_vehicle.action_in_run.get('local_tr_cmd',{}).get('uuid'), 'Dest': new_dest_port}, True)
                                    self.logger.debug('reassign in run {} to {} by carrierID'.format(carrierID, new_dest_port))
                                    break
                                else:
                                    for action in list(h_vehicle.actions)[1:]:
                                        if action['local_tr_cmd']['uuid'] == commandID:
                                            if 'PRE-' in action['local_tr_cmd']['uuid']:
                                                # print('??? >>>', action['local_tr_cmd']['uuid'])
                                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                                                break
                                            action['target']=new_dest_port
                                            action['local_tr_cmd']['dest']=new_dest_port
                                            action['local_tr_cmd']['TransferInfo']['DestPort']=new_dest_port
                                            action['local_tr_cmd']['OriginalTransferInfo']['DestPort']=new_dest_port
                                            action['local_tr_cmd']['host_tr_cmd']['dest']=new_dest_port
                                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([4]), obj['system'])
                                            output('TransferExecuteQueueUpdate', {'CommandID':commandID, 'Dest': new_dest_port}, True)
                                            self.logger.debug('reassign {} to {} by commandID'.format(carrierID, new_dest_port))
                                            break
                                        elif action['local_tr_cmd']['carrierID'] == carrierID:
                                            if 'PRE-' in action['local_tr_cmd']['uuid']:
                                                # print('??? >>>', action['local_tr_cmd']['uuid'])
                                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                                                break
                                            action['target']=new_dest_port
                                            action['local_tr_cmd']['dest']=new_dest_port
                                            action['local_tr_cmd']['TransferInfo']['DestPort']=new_dest_port
                                            action['local_tr_cmd']['OriginalTransferInfo']['DestPort']=new_dest_port
                                            action['local_tr_cmd']['host_tr_cmd']['dest']=new_dest_port
                                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([4]), obj['system'])
                                            output('TransferExecuteQueueUpdate', {'CommandID':action['local_tr_cmd']['uuid'], 'Dest': new_dest_port}, True)
                                            self.logger.debug('reassign {} to {} by carrierID'.format(carrierID, new_dest_port))
                                            break
                                    else:
                                        continue
                                    break
                            else:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["DESTPORT", 2]]]), obj['system'])

                    elif obj['remote_cmd'] == 'work_add': #from Order UI
                        workID='0'
                        carrierID=obj['workinfo'].get('CarrierID', '')
                        lotID=obj['workinfo'].get('LotID', '')
                        next_step=obj['workinfo'].get('Stage', '') #Any or one group in eq list
                        machine=obj['workinfo'].get('Machine', '') #Any or one machine
                        priority=obj['workinfo'].get('Priority', 0)
                        couples=obj['workinfo'].get('Couples', [])
                        if type(couples)!=list:
                            couples=couples.split(',') if couples else []

                        carrierType=obj['workinfo'].get('CarrierType', '') #fix UTAC couples
                        if workID == '0':
                            uuid=100*time.time()
                            uuid%=1000000000000
                            workID='O%.12d'%uuid

                        if carrierID == '':
                            alarms.RtdOrderCarrierNull(workID)
                        else:
                            #need check white list
                            # 9/19
                            for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                                for port_no in range(1, h_eRack.slot_num+1, 1):
                                    carrier=h_eRack.carriers[port_no-1]
                                    safety_check=(global_variables.TSCSettings.get('Other', {}).get('RTDCarrierLocateCheck','no') == 'yes')
                                    erack_CarrierCheck=carrier['carrierID'] == carrierID and carrier['status'] == 'up'
                                    if erack_CarrierCheck or not safety_check: #for umc Sean 23/12/19
                                        #h_eRack.lots[port_no-1]['lotID']=lotID
                                        lotID=h_eRack.lots[port_no-1]['lotID']
                                        res, location=tools.print_rackport_format(rack_id, port_no, h_eRack.rows, h_eRack.columns)

                                        if erack_CarrierCheck:
                                            EqMgr.getInstance().orderMgr.add_work_list(workID, carrierID, carrierType, lotID, location, next_step, machine, priority, couples) #fix UTAC couples
                                        elif not safety_check: #for UMC 23/12/21 Sean
                                            EqMgr.getInstance().orderMgr.add_work_list(workID, carrierID, carrierType, lotID, '', next_step, machine, priority, couples) #chocp 2024/03/25
                                        break
                                else:
                                    continue
                                break
                            else:      
                                if global_variables.default_stock_out_port: #chocp 2024/03/25 for UMC stocker
                                    EqMgr.getInstance().orderMgr.add_work_list(workID, carrierID, carrierType, lotID, global_variables.default_stock_out_port, next_step, machine, priority, couples) 
                                else:
                                    alarms.RtdOrderCarrierLocateWarning(workID, carrierID) #chocp 2021/11/8

                    elif obj['remote_cmd'] == 'work_cancel':
                        workID=obj['WorkID']
                        #abort all relative transfer cmd
                        res, queueID=self.transfer_cancel(workID, 'by web')
                        res, vehicleID=self.host_transfer_abort(workID, 'by web')
                        EqMgr.getInstance().orderMgr.cancel_work_list_by_workID(workID)

                    elif obj['remote_cmd'] == 'work_reset':
                        workID=obj['WorkID']
                        EqMgr.getInstance().orderMgr.reset_work_list_by_workID(workID)

                    elif obj['remote_cmd'] == 'work_go':
                        print('work_go:', obj)
                        workID=obj.get('WorkID', '')
                        carrierID=obj.get('CarrierID', '')
                        location=obj.get('Location', '')
                        machine=obj.get('Machine', '')
                        replace=obj.get('Replace', 0)
                        destport=obj.get('DestPort', '')
                        h=EqMgr.getInstance().workstations.get(destport)
                        if h:
                            EqMgr.getInstance().orderMgr.direct_dispatch(workID, carrierID, location, machine, replace, destport, h)
                        else:
                            print('None or Not valid workstation {}'.format(work['DestPort']))

                    elif obj['remote_cmd'] == 'work_edit':

                        workID=obj['WorkID']
                        carrierID=obj['CarrierID']
                        EqMgr.getInstance().orderMgr.work_edit(workID, carrierID)


                    elif obj['remote_cmd'] == 'commands_edit':

                        commandID=obj['CommandID']
                        carrierID=obj.get('CarrierID', 'None')

                        print('commands_edit', commandID, carrierID)
                        res, target=tools.re_assign_source_port(carrierID)
                        location=target if res else ''

                        print('commands_edit', commandID, carrierID, location)

                        output('CommandsEditUpdate', {'CommandID':commandID, 'CarrierID':carrierID, 'Location':location})

                    elif obj['remote_cmd'] == 'cancel': #devide by group
                        CommandID=str(obj['CommandID'])
                        CarrierID=obj.get('CommandID', '')

                        #E82.report_event(self.secsgem_e82_default_h, E82.TransferCancelInitiated, {'CommandID':CommandID})
                        #output('TransferCancelInitiated', {'CommandID':CommandID})
                        cause='by host' if obj.get('system') else 'by web'
                        if cause =='by web' and obj.get('OperatorInitiated',''):
                            OperatorInitiated=obj.get('OperatorInitiated')
                            E82.report_event(self.secsgem_e82_default_h, E82.OperatorInitiatedAction, {'CommandID':CommandID, 'CommandType':'Cancel', 'CarrierID':OperatorInitiated['CarrierID'], 'SourcePort':OperatorInitiated['SourcePort'], 'DestPort':OperatorInitiated['DestPort'], 'Priority':OperatorInitiated['Priority']})
                        res, queueID=self.transfer_cancel(CommandID, cause) #2022/6/30
                        if not res and cause == 'by web':
                            output('TransferWaitQueueRemove', {'CommandID':CommandID}, True) #force to remove UI residule

                    elif obj['remote_cmd'] == 'stagedelete':
                        StageID=obj['StageID']
                        if global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes':
                            if StageID:
                                for VehicleID, h_vehicle in Vehicle.h.vehicles.items():
                                    if 'PRE-'+StageID in h_vehicle.CommandIDList:
                                        # remove stage cmd from vehicle queue
                                        h_vehicle.abort_tr_cmds_and_actions('PRE-'+StageID, 0, 'Stage command delete', cause='by stage')
                                        break
                                else:
                                    for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                                        if StageID not in zone_wq.transfer_list:
                                            continue
                                        # remove stage cmd from waiting queue
                                        zone_wq.remove_waiting_transfer_by_commandID(StageID, cause='by host')
                                        output('TransferWaitQueueRemove', {'CommandID':StageID}, True)
                                        break
                            else: # delete all stage?
                                for VehicleID, h_vehicle in Vehicle.h.vehicles.items():
                                    for local_tr_cmd in h_vehicle.tr_cmds:
                                        if local_tr_cmd.get('host_tr_cmd', {}).get('stage', False):
                                            # remove stage cmd from vehicle queue
                                            h_vehicle.abort_tr_cmds_and_actions(local_tr_cmd['uuid'], 0, 'Stage command delete', cause='by stage')
                                            break
                                for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                                    for waiting_command_id, waiting_tr_cmd in zone_wq.transfer_list.items(): #have lock or race condition problem???
                                        if waiting_tr_cmd['stage']:
                                            # remove stage cmd from waiting queue
                                            zone_wq.remove_waiting_transfer_by_commandID(waiting_command_id, cause='by host')
                                            output('TransferWaitQueueRemove', {'CommandID':waiting_command_id}, True)
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([1]), obj['system'])

                    elif obj['remote_cmd'] == 'duetimeupdate':  # Chi 2022/02/21
                        res=True
                        duetimelist=obj.get('duetimeinfolist', '')
                        for duetimeinfo in duetimelist:
                            HostTime=duetimeinfo.get('DueTime', '')
                            PortID=duetimeinfo.get('PortID', '')
                            try:
                                if len(HostTime) != 12 or HostTime =='':
                                    res=False
                                    obj['handle'].send_response(obj['handle'].stream_function(2,50)([3, [["DueTime", 2]]]), obj['system'])
                                    break
                                if PortID =='':
                                    res=False
                                    obj['handle'].send_response(obj['handle'].stream_function(2,50)([3, [["PortID", 2]]]), obj['system'])
                                    break
                            except:
                                res=False
                                pass
                        if res and duetimelist != '':
                            for duetimeinfo in duetimelist:
                                #Nowtime=time.strftime("%Y%m%d%H%M", time.localtime())
                                Nowtime=time.time()
                                PortID=duetimeinfo.get('PortID')
                                #HostTime=duetimeinfo.get('DueTime')
                                HostTime_stamp=time.strptime(duetimeinfo.get('DueTime'), "%Y%m%d%H%M")
                                time_stamp=time.mktime(HostTime_stamp)
                                DueTime=(int(time_stamp) - int(Nowtime))
                                event='update_duetime_evt'
                                data ={'DueTime':DueTime}
                                EqMgr.getInstance().trigger(PortID, event, data)
                                print(PortID, event,DueTime)
                            obj['handle'].send_response(obj['handle'].stream_function(2,50)([4]), obj['system'])

                    elif obj['remote_cmd'] == 'stopvehicle': #Chi 2023/03/15
                        VehicleID=obj['VehicleID']
                        if VehicleID:
                            h_vehicle=Vehicle.h.vehicles.get(VehicleID)
                            h_vehicle.adapter.host_stop_control()
                        else:
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                h_vehicle.adapter.host_stop_control()
                                
                    elif obj['remote_cmd'] == 'dooropenreply':#peter 240705,test call door for K11
                        VehicleID=obj['VehicleID']
                        if "DOORSTATE" in obj:
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                if VehicleID == vehicle_id:
                                    h_vehicle.adapter.DoorState=obj["DOORSTATE"]

                    elif obj['remote_cmd'] == 'showmcs': #peter 240729
                        output('AlarmSet',obj)
                        self.logger.info("send_mcs_message:{}".format(obj))  
                                
                    elif obj['remote_cmd'] == 'evacuation': #Chi 2024/05/29
                        self.run_tsc=False
                        VehicleID=obj['VehicleID']
                        Situation=obj['Situation']
                        if VehicleID:
                            h_vehicle=Vehicle.h.vehicles.get(VehicleID)
                            h_vehicle.emergency_evacuation(Situation)
                        else:
                            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                                h_vehicle.emergency_evacuation(Situation)

                    elif obj['remote_cmd'] == 'call':
                        res=False
                        VehicleID=obj['VehicleID']
                        PortID=obj['Destport']
                        h_vehicle=Vehicle.h.vehicles.get(VehicleID, '')
                        if PortID not in global_variables.PortsTable.mapping:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["DESTPORT", 2]]]), obj['system'])
                            continue
                        if h_vehicle:
                            if h_vehicle.AgvState == 'Unassigned' and not h_vehicle.waiting_run and not h_vehicle.force_charge:
                                h_vehicle.host_call_cmd=True
                                h_vehicle.host_call_params=obj
                                res=True
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                        else:
                            zoneID=''
                            h_workstation=EqMgr.getInstance().workstations.get(PortID)
                            if h_workstation:
                                zoneID=h_workstation.zoneID
                            nearest_vehicleID=''
                            nearest_vehicle=None
                            nearest_distance=-1
                            point=tools.find_point(PortID)
                            for VehicleID, h_vehicle in Vehicle.h.vehicles.items():
                                if zoneID and zoneID not in h_vehicle.serviceZone[0]:
                                    continue
                                if h_vehicle.AgvState == 'Unassigned' and not h_vehicle.waiting_run and not h_vehicle.force_charge:
                                    distance=global_variables.dist.get(h_vehicle.adapter.last_point, {}).get(point, -1)
                                    if distance < nearest_distance or nearest_distance < 0:
                                        nearest_distance=distance
                                        nearest_vehicleID=VehicleID
                                        nearest_vehicle=h_vehicle
                            if nearest_vehicleID:
                                h_vehicle=nearest_vehicle
                                if h_vehicle.AgvState == 'Unassigned' and not h_vehicle.waiting_run and not h_vehicle.force_charge:
                                    h_vehicle.host_call_cmd=True
                                    h_vehicle.host_call_params=obj
                                    res=True
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                                elif h_vehicle.action_in_run.get('target', '') and tools.find_point(h_vehicle.action_in_run['target']):
                                    res=True
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                        if not res:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["VEHICLEID", 2]]]), obj['system'])

                    elif obj['remote_cmd'] == 'book':
                        res=False
                        VehicleID=self.secsgem_e88_stk_default_h.Ports.Data[obj['PortID']].StockerCraneID
                        h_vehicle=Vehicle.h.vehicles.get(VehicleID)
                        if h_vehicle:
                            if h_vehicle.AgvState == 'Unassigned' and not h_vehicle.waiting_run and not h_vehicle.force_charge:
                                obj['handle'].Ports.Data[obj['PortID']].PortBook=True
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                                h_vehicle.host_call_cmd=True
                                h_vehicle.host_call_params=obj
                            elif h_vehicle.AgvState not in ['Unassigned', 'Pause', 'Removed'] and PortsTable.mapping[h_vehicle.action_in_run['target']][0] == PortsTable.mapping[obj['PortID']][0]:
                                obj['handle'].Ports.Data[obj['PortID']].PortBook=True
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([0]), obj['system'])
                            else:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([2]), obj['system'])

                    elif obj['remote_cmd'] == 'assignable':
                        h_vehicle=Vehicle.h.vehicles.get(obj['VehicleID'])
                        if h_vehicle:
                            h_vehicle.assignable=True
                            print('{} ready to assign!'.format(obj['VehicleID']))

                    elif obj['remote_cmd'] == 'rename':
                        ack=0
                        param=[]
                        if not obj['CarrierID']:
                            ack=3
                            param.append(["CarrierID", 2])
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, []]), obj['system'])
                        r=re.match('(.+)BUF(\d\d)', obj['CarrierLoc'])
                        if r:
                            VehicleID, BufIDX=r.groups()
                            h_vehicle=Vehicle.h.vehicles.get(VehicleID)
                            if h_vehicle:
                                h_vehicle.adapter.rfid_control(int(BufIDX), obj['CarrierID'])
                            else:
                                ack=3
                                param.append(["CarrierLoc", 2])
                        else:
                            ack=3
                            param.append(["CarrierLoc", 2])
                        if param:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([ack, param]), obj['system'])
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([ack]), obj['system'])

                    elif obj['remote_cmd'] == 'socketio_connected_evt':
                        output('TSCUpdate', {'TSCState':self.mTscState, 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState})
                        
                    elif obj['remote_cmd']== 'suspendcancel':
                        h_vehicle=Vehicle.h.vehicles.get(obj['VehicleID'])
                        if h_vehicle and h_vehicle.action_in_run.get('target', '') == obj['DESTPORT']:
                            h_vehicle.wait_eq_operation=False
                            
                    elif obj['remote_cmd']== 'priorityupdate':
                        CommandID=obj['CommandID']
                        Priority=obj['Priority']
                        zoneID , transfercmd=tools.find_command_zone_by_commandID(CommandID)
                        if zoneID:
                            if transfercmd.get('link') or transfercmd.get('primary') == 0:
                                obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                            else:
                                original_priority=transfercmd['priority']
                                if Priority != original_priority:
                                    wq=TransferWaitQueue.getInstance(zoneID)
                                    wq.remove_transfer_from_queue_directly(transfercmd)
                                    transfercmd['priority']=int(Priority)
                                    self.logger.info('Get Host update command priority {} from {} to {}'.format(CommandID, original_priority, Priority))
                                    if global_variables.RackNaming in [16,23,34,54]:
                                        idx=wq.add_transfer_into_queue_with_check_sj_new(transfercmd)
                                    else:
                                        idx=wq.add_transfer_into_queue_with_check_common(transfercmd)
                                    print("{} queue priority >>>".format(wq.queueID),[(cmd['uuid'],cmd['priority']) for cmd in wq.queue])
                                    output('TransferWaitQueueAdd', {
                                        'Channel':transfercmd.get('channel', 'Internal'), #chocp 2022/6/13
                                        'Idx':idx,
                                        'CarrierID':transfercmd['carrierID'],
                                        'CarrierType':transfercmd['TransferInfoList'][0].get('CarrierType', ''), #chocp 2022/2/9
                                        'ZoneID':transfercmd['zoneID'],  #chocp 9/14
                                        'TransferInfoList':transfercmd['TransferInfoList'],
                                        'Source':transfercmd['source'],
                                        'Dest':transfercmd['dest'],
                                        'CommandID':transfercmd["uuid"],
                                        'Priority':Priority,
                                        'Replace':transfercmd['replace'],
                                        'Back':transfercmd['back'],
                                        'OperatorID':transfercmd.get('operatorID', '')
                                        }, True)
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([4]), obj['system'])
                                else:
                                    obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["PRIORITY", 2]]]), obj['system'])
                        else:
                            obj['handle'].send_response(obj['handle'].stream_function(2,42)([3, [["COMMANDID", 2]]]), obj['system'])
                            
                    else:
                        print('get other remote', obj)

                if self.secsgem_e88_default_h:    #2022/08/09 Chi
                    if self.mScState == 'SCInitiated':
                        if self.secsgem_e88_default_h.controlState.current in ['ONLINE', 'ONLINE_REMOTE', 'ONLINE_LOCAL']:
                            output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCPaused', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mScLastCommunicationState})
                            E88.report_event(self.secsgem_e82_default_h, E88.SCPaused)
                            self.mScState='SCPaused'
                            self.secsgem_e88_default_h.SCState=2

                    elif self.mScState == 'SCPaused':
                        if self.run_sc == True:#resume_cmd:
                            output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCAuto', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mScLastCommunicationState})
                            E88.report_event(self.secsgem_e88_default_h, E88.SCAutoCompleted)
                            self.mScState='SCAuto'
                            self.secsgem_e88_default_h.SCState=3

                    elif self.mScState == 'SCPausing':
                        if self.run_sc == True:#resume_cmd:
                            output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCAuto', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mScLastCommunicationState})
                            E88.report_event(self.secsgem_e88_default_h, E88.SCAutoCompleted)
                            self.mScState='SCAuto'
                            self.secsgem_e88_default_h.SCState=3

                        else:
                            output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCPaused', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mScLastCommunicationState})
                            E88.report_event(self.secsgem_e88_default_h, E88.SCPauseCompleted)
                            self.mScState='SCPaused'
                            self.secsgem_e88_default_h.SCState=2

                    elif self.mScState == 'SCAuto':
                        if self.run_sc == False:#pause:
                            output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCPausing', 'ControlState':self.mScControlState, 'CommunicationState':self.mScCommunicationState, 'LastCommunicationState':self.mScLastCommunicationState})
                            E88.report_event(self.secsgem_e88_default_h, E88.SCPauseInitiated)
                            self.mScState='SCPausing'
                            self.secsgem_e88_default_h.SCState=4
                elif not self.secsgem_e88_default_h and  self.use_e82: #chi 2022/08/16
                    output('STKCUpdate', {'STKCStatus':False, 'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING', 'LastCommunicationState':'NOT_COMMUNICATING'})
                    self.use_e82=False

                if self.mTscState == 'TSCInitiated':
                    #need change.....
                    if self.secsgem_e82_default_h.controlState.current in ['ONLINE', 'ONLINE_REMOTE', 'ONLINE_LOCAL']:
                        output('TSCUpdate', {'TSCState':'TSCPaused', 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver})
                        E82.report_event(self.secsgem_e82_default_h, E82.TSCPaused)
                        self.mTscState='TSCPaused'
                        self.secsgem_e82_default_h.TSCState=2

                elif self.mTscState == 'TSCPaused':
                    if self.run_tsc == True:#resume_cmd:
                        output('TSCUpdate', {'TSCState':'TSCAuto', 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver})
                        E82.report_event(self.secsgem_e82_default_h, E82.TSCAutoCompleted)
                        self.mTscState='TSCAuto'
                        self.secsgem_e82_default_h.TSCState=3
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            h_vehicle.tsc_paused=False

                elif self.mTscState == 'TSCPausing':
                    still_moving=False
                    if self.run_tsc == True:#resume_cmd:
                        output('TSCUpdate', {'TSCState':'TSCAuto', 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver})
                        E82.report_event(self.secsgem_e82_default_h, E82.TSCAutoCompleted)
                        self.mTscState='TSCAuto'
                        self.secsgem_e82_default_h.TSCState=3
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            h_vehicle.tsc_paused=False

                    else:
                        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                            h_vehicle.tsc_paused=True
                            if len(h_vehicle.tr_cmds)>0 or h_vehicle.AgvState == 'Enroute':
                                still_moving=True
                        if not still_moving:
                            output('TSCUpdate', {'TSCState':'TSCPaused', 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver})
                            E82.report_event(self.secsgem_e82_default_h, E82.TSCPauseCompleted)
                            self.mTscState='TSCPaused'
                            self.secsgem_e82_default_h.TSCState=2

                elif self.mTscState == 'TSCAuto':
                    if self.run_tsc == False:#pause:
                        output('TSCUpdate', {'TSCState':'TSCPausing', 'ControlState':self.mControlState, 'CommunicationState':self.mCommunicationState, 'LastCommunicationState':self.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver})
                        E82.report_event(self.secsgem_e82_default_h, E82.TSCPauseInitiated)
                        self.mTscState='TSCPausing'
                        self.secsgem_e82_default_h.TSCState=4
                    else:
                        if Erack.h: #2024/1/24
                            for rack_id, h_eRack in Erack.h.eRacks.items(): #chocp 2022/4/29
                                if h_eRack.autodispatch and h_eRack.returnto and h_eRack.returnto!='None':
                                    dispatch_count=0
                                    for lot in h_eRack.lots:
                                        if lot.get('machine'):
                                            dispatch_count+=1

                                    if h_eRack.slot_num-h_eRack.available-dispatch_count>h_eRack.slot_num*h_eRack.waterlevelhigh/100: #chi change self to h_eRack
                                        self.racklevel_overhigh_handler(h_eRack)

                        #select queue have priority high firstor received long cmd
                        def get_weight(wq): #100~-999999999
                            weight=float('-inf')
                            if wq.queue:
                                host_tr_cmd=wq.queue[0]
                                priority=host_tr_cmd.get('priority', 0)
                                if priority:
                                    weight=priority
                                else:
                                    weight=-1*host_tr_cmd.get('received_time', 0)

                                if global_variables.RackNaming == 8:
                                    weight=-1*host_tr_cmd.get('received_time', 0)
                                    
                                elif global_variables.RackNaming == 40:
                                    if wq.queueID == 'zoneR':
                                       weight=float('inf') 
                                    else:
                                        weight=priority

                            return weight

                        for wq in sorted(list(TransferWaitQueue.getAllInstance().values()), key=get_weight, reverse=True): #8.21H-2

                            # if len(wq.queue):
                            #     tsc_logger.info("wq:{}".format(wq.queueID))
                            #     tsc_logger.info("wq length:{}".format(len(wq.queue)))
                            if not wq.wq_lock.acquire(False):
                                print('queueID: {} can not lock'.format(wq.queueID))
                                continue

                            try:
                                can_run_flag=False
                                '''if 'MR' in zoneID and len(zone_wq.queue): #for specified MR for StockOut
                                    can_run_flag=True ''' #disable dispatch cmd for MRxxx zone right now
                                if len(wq.queue): #chi 2022/11/23
                                    if time.time()-wq.queue[0]['received_time']>wq.commandLivingTime:
                                        wq.wq_lock.release() #8.21N-3
                                        res, queueID=self.transfer_cancel(wq.queue[0]['uuid'], 'by Command Timeout')
                                        continue
                                    
                                if wq.vehicleMaxCapacity > 0:
                                    if len(wq.dispatchedMRList):
                                        for vehicleID in wq.dispatchedMRList:
                                            vehicle_th=Vehicle.h.vehicles.get(vehicleID)
                                            if not vehicle_th:
                                                self.logger.info('{} Remove dispatchedMRList:{} no correct vehicle thread'.format(vehicleID, wq.dispatchedMRList))
                                                wq.dispatchedMRList.remove(vehicleID)
                                            elif vehicle_th and vehicle_th.AgvState == 'Removed':
                                                self.logger.info('{} Remove dispatchedMRList:{} vehicle state is Removed'.format(vehicleID, wq.dispatchedMRList))
                                                wq.dispatchedMRList.remove(vehicleID)
                                            
                                    if len(wq.dispatchedMRList) >= wq.vehicleMaxCapacity:
                                        wq.wq_lock.release()
                                        continue

                                if len(wq.queue) and (global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes' or global_variables.TSCSettings.get('Other', {}).get('PreDispatch','no') == 'yes'):
                                    stage_cmd={}
                                    if wq.queue[0]['priority']!=100:
                                        for waiting_tr_cmd in wq.queue[:wq.merge_max_cmds]:
                                            if waiting_tr_cmd.get('sourceType') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']:
                                                wq.change_transfer_priority(waiting_tr_cmd['uuid'], 100, skip_lock=True)
                                                print('In {}, move {} to 100'.format(wq.queueID, waiting_tr_cmd['uuid']))
                                                stage_cmd=waiting_tr_cmd
                                    if wq.queue[0]['priority'] == 100:
                                        if (wq.queue[0]['stage'] or wq.queue[0].get('link', {}) and wq.queue[0].get('stage', False)):
                                            waiting_tr_cmd=wq.queue[0]
                                            # check if stage is expired
                                            if waiting_tr_cmd['CommandInfo']['NoBlockingTime'] and time.time() > waiting_tr_cmd['received_time'] + waiting_tr_cmd['CommandInfo']['NoBlockingTime']:
                                                wq.remove_waiting_transfer_by_commandID(waiting_tr_cmd['uuid'], cause='by stage expired')
                                                output('TransferWaitQueueRemove', {'CommandID':waiting_tr_cmd['uuid']}, True)
                                                print('Stage cmd {} expired!'.format(waiting_tr_cmd['uuid']))

                                if wq.single_transfer_total+wq.replace_transfer_total*2>=wq.merge_max_cmds: #chocp 2022/4/8
                                    exp_t=time.time()-wq.collect_timeout
                                    for cmd in wq.queue[:wq.merge_max_cmds][::-1]:
                                        if cmd['uuid'] in wq.linked_list:
                                            continue
                                        if exp_t > cmd['received_time']:
                                            can_run_flag=True
                                        break
                                    else:
                                        can_run_flag=True
                                    # print('>>>>>> ', exp_t, cmd['uuid'], cmd['received_time'], wq.queue[:wq.merge_max_cmds][::-1], wq.linked_list)
                                    #print(wq.queueID, 'condition 1')

                                elif len(wq.queue)>1 and ((time.time()-wq.last_add_time)>wq.collect_timeout): #chocp 2022/4/8, if cmd len=2,3,...

                                    '''if global_variables.RackNaming == 18 and wq.queueID in list(Vehicle.h.vehicles.keys()): #for k25 chocp 8.22C-2

                                        stocker_queue_h=wq.relation_links[0].queueID if wq.relation_links else ''
                                        if stocker_queue_h and stocker_queue_h.tr_add_assert.get('RESULT') == 'NG':
                                            can_run_flag=True
                                        else:
                                            stocker_queue_h.tr_add_assert={}
                                            E82.report_event(self.secsgem_e82_default_h,
                                                            E82.TrAddReq,{
                                                            'VehicleID':wq.queueID,
                                                            'TransferPort':wq.relation_links[0].queueID if wq.relation_links else ''})

                                            wq.last_add_time=time.time()
                                    else:
                                        can_run_flag=True'''
                                    if wq.queueID in Vehicle.h.vehicles:
                                        h_vehicle=Vehicle.h.vehicles[wq.queueID]
                                        if wq.queueID not in self.vehicle_dispatch_delay:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                        if h_vehicle.AgvState == 'Unassigned':
                                            if self.vehicle_dispatch_delay[wq.queueID] > 1:
                                                self.vehicle_dispatch_delay[wq.queueID]=0
                                                can_run_flag=True
                                                #print(wq.queueID, 'condition 1')
                                            else:
                                                self.vehicle_dispatch_delay[wq.queueID] += 1
                                        else:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                    else:
                                        can_run_flag=True

                                elif len(wq.queue) and ((time.time()-wq.last_add_time)>(wq.merge_start_time+wq.collect_timeout)): #chocp 2022/4/8, if cmd len=1
                                    if wq.queueID in Vehicle.h.vehicles:
                                        h_vehicle=Vehicle.h.vehicles[wq.queueID]
                                        if wq.queueID not in self.vehicle_dispatch_delay:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                        if h_vehicle.AgvState == 'Unassigned':
                                            if self.vehicle_dispatch_delay[wq.queueID] > 1:
                                                self.vehicle_dispatch_delay[wq.queueID]=0
                                                can_run_flag=True
                                                #print(wq.queueID, 'condition 1')
                                            else:
                                                self.vehicle_dispatch_delay[wq.queueID] += 1
                                        else:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                    else:
                                        can_run_flag=True

                                elif len(wq.queue) and wq.queue[0]['priority']>=100 and not wq.queue[0]['stage']: #cond 3, only priority immediately run, chocp 9/8
                                    can_run_flag=True
                                    #print(wq.queueID, 'condition 4')

                                #elif len(wq.queue) and 'MR' not in queueID:
                                #    if wq.queue[0].get('sourceType') == 'StockOut' : #for StockOut
                                #        can_run_flag=True
                                #        print('can run in stockout cmd test')
                                elif (global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' or global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes') and len(wq.queue) and not wq.queue[0].get('preTransfer') and (wq.queue[0].get('sourceType') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']):
                                    if global_variables.RackNaming == 8:
                                        if wq.single_transfer_total+wq.replace_transfer_total*2>=wq.merge_max_cmds: #chocp 2022/4/8
                                            can_run_flag=True

                                        elif len(wq.queue)>1 and ((time.time()-wq.last_add_time)>wq.collect_timeout): #chocp 2022/4/8, if cmd len=2,3,...
                                            can_run_flag=True

                                        elif len(wq.queue) and ((time.time()-wq.last_add_time)>(wq.merge_start_time+wq.collect_timeout)): #chocp 2022/4/8, if cmd len=1
                                            can_run_flag=True

                                        elif len(wq.queue) and wq.queue[0]['priority'] == 100: #cond 3, only priority immediately run, chocp 9/8
                                            can_run_flag=True
                                    else:
                                        can_run_flag=True
                                        # print(wq.queueID, 'condition 5')

                                elif len(wq.queue) and wq.queueID in Vehicle.h.vehicles: # Mike: 2024/03/22
                                    h_vehicle=Vehicle.h.vehicles[wq.queueID]
                                    if wq.queueID not in self.vehicle_dispatch_delay:
                                        self.vehicle_dispatch_delay[wq.queueID]=0
                                    if h_vehicle.AgvState == 'Unassigned':
                                        avaliable, _=h_vehicle.buf_available()
                                        #print(wq.queueID, 'total: ', wq.single_transfer_total, wq.replace_transfer_total, h_vehicle.assignable)
                                        if avaliable == 0 or (wq.replace_transfer_total > 0 and avaliable < 2):
                                            if self.vehicle_dispatch_delay[wq.queueID] > 1:
                                                self.vehicle_dispatch_delay[wq.queueID]=0
                                                can_run_flag=True
                                                #print(wq.queueID, 'condition 1')
                                            else:
                                                self.vehicle_dispatch_delay[wq.queueID] += 1
                                        if h_vehicle.assignable or global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes':
                                            if self.vehicle_dispatch_delay[wq.queueID] > 1:
                                                self.vehicle_dispatch_delay[wq.queueID]=0
                                                can_run_flag=True
                                            else:
                                                self.vehicle_dispatch_delay[wq.queueID] += 1
                                        else:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                    else:
                                        self.vehicle_dispatch_delay[wq.queueID]=0

                                elif not len(wq.queue) and wq.queueID in Vehicle.h.vehicles:
                                    h_vehicle=Vehicle.h.vehicles[wq.queueID]
                                    if wq.queueID not in self.vehicle_dispatch_delay:
                                        self.vehicle_dispatch_delay[wq.queueID]=0
                                    if h_vehicle.AgvState == 'Unassigned':
                                        if self.vehicle_dispatch_delay[wq.queueID] > 1:
                                            self.vehicle_dispatch_delay[wq.queueID]=0
                                        else:
                                            self.vehicle_dispatch_delay[wq.queueID] += 1
                                    else:
                                        self.vehicle_dispatch_delay[wq.queueID]=0

                                #K25 dispatch alternately
                                if (global_variables.RackNaming == 18 or global_variables.RackNaming == 28)  and can_run_flag:
                                    try:
                                        if EqMgr.getInstance().equipments.get(wq.queueID):
                                            if wq.queueID in global_variables.global_occupied_station:
                                                vehicle_id=global_variables.global_occupied_station[wq.queueID] # Mike: 2021/04/27
                                                vehicle_h=Vehicle.h.vehicles.get(vehicle_id, '')
                                                if vehicle_id and vehicle_h and vehicle_h.AgvState != 'Unassigned':
                                                    #print('Unset can_run_flag in dynamic occupied check:', vehicle_id, vehicle_h, vehicle_h.AgvState)
                                                    can_run_flag=False

                                            if wq.queueID in global_variables.global_vehicles_location:
                                                vehicle_id=global_variables.global_vehicles_location[wq.queueID]
                                                vehicle_h=Vehicle.h.vehicles.get(vehicle_id, '')
                                                if vehicle_id and vehicle_h and vehicle_h.AgvState != 'Unassigned':
                                                    #print('Unset can_run_flag in static occupied check:', vehicle_id, vehicle_h, vehicle_h.AgvState)
                                                    can_run_flag=False
                                    except:
                                        traceback.print_exc()
                                        pass
                                    
                                elif global_variables.RackNaming == 40 and wq.lot_list:
                                    can_dispatch_lot_in = 0
                                    can_dispatch_lot_out = 0
                                    wq.can_dispatch_lot_in=False
                                    wq.can_dispatch_lot_out=False

                                    if "In" in wq.lot_list:
                                        for lotinfo in wq.lot_list["In"].values():
                                            if lotinfo.get('dispatch'):
                                                can_dispatch_lot_in += 1

                                    if "Out" in wq.lot_list:
                                        for lotinfo in wq.lot_list["Out"].values():
                                            if lotinfo.get('dispatch'):
                                                can_dispatch_lot_out += 1

                                    if can_dispatch_lot_in >= wq.merge_max_lots:
                                        wq.can_dispatch_lot_in=True
                                        can_run_flag = True
                                    if can_dispatch_lot_out >= wq.merge_max_lots:
                                        wq.can_dispatch_lot_out=True
                                        can_run_flag = True

                                if can_run_flag: #run the zone queue condition available, chocp 10/23 # Mike: 2022/3/11
                                    major_candidates=[] #8.21H-3
                                    slave_candidates=[] #8.21H-3
                                    need_support=False
                                    tmp_wait_stop_vehicle=[]

                                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items(): #find a vehicle

                                        # print('=> ', wq.queueID, h_vehicle.doPreDispatchCmd, wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut'], self.vehicle_dispatch_delay.get(h_vehicle.id, 0))

                                        can_assign=h_vehicle.AgvState == 'Unassigned' and not h_vehicle.waiting_run and (not h_vehicle.force_charge or h_vehicle.doPreDispatchCmd)
                                        
                                        if global_variables.RackNaming == 40:
                                            call_support=h_vehicle.AgvState in ['Removed']
                                        else:
                                            call_support=h_vehicle.AgvState in ['Removed'] or \
                                                    (h_vehicle.AgvState == 'Pause' and h_vehicle.alarm_set == 'Serious') or\
                                                    (h_vehicle.ControlPhase == 'GoCharge' and h_vehicle.force_charge)


                                        call_support=call_support and (time.time()-h_vehicle.call_support_time>h_vehicle.call_support_delay)

                                        if wq.queueID in Vehicle.h.vehicles: #chocp fix for 8.22F-1 xxxMRxxxBUF00 Port not found
                                            if wq.queueID == h_vehicle.id: #@2022/12/19
                                                need_support=False
                                                major_candidates=[]
                                                # print('??????', wq.queueID, h_vehicle.doPreDispatchCmd, wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut'], self.vehicle_dispatch_delay.get(h_vehicle.id, 0))

                                                if can_assign:
                                                    major_candidates=[{h_vehicle:0}]
                                                    h_vehicle.assignable=False
                                                #how about error???
                                                break
                                            else:
                                                continue
                                        #FST
                                        elif wq.preferVehicle and wq.preferVehicle == h_vehicle.id: #for StockOut, how to clean preVehicle 2022/12/19

                                            need_support=False #chocp 2022/6/8
                                            major_candidates=[]

                                            # print('???', wq.queueID, h_vehicle.doPreDispatchCmd, wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut'], self.vehicle_dispatch_delay.get(h_vehicle.id, 0))
                                            check=wq.queue[0].get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'] or wq.queue[0].get('link') and wq.queue[0].get('link', {}).get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']
                                            # print('???', wq.queueID, h_vehicle.doPreDispatchCmd, wq.queue[0].get('sourceType') in ['StockOut', 'ErackOut', 'StockIn&StockOut'], wq.queue[0].get('link') and wq.queue[0].get('link', {}).get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'], self.vehicle_dispatch_delay.get(h_vehicle.id, 0))
                                            # if h_vehicle.doPreDispatchCmd and wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'] and self.vehicle_dispatch_delay.get(h_vehicle.id, 0) < 2:
                                            if h_vehicle.doPreDispatchCmd and not check and self.vehicle_dispatch_delay.get(h_vehicle.id, 0) < 2:
                                                can_assign=False

                                            if can_assign:
                                                vehicle_wq=TransferWaitQueue.getInstance(h_vehicle.id)
                                                try:
                                                    print(wq.queueID, wq.queue[0]['zoneID'])
                                                    print(h_vehicle.id, len(vehicle_wq.queue))
                                                    if len(vehicle_wq.queue) > 0:
                                                        print(wq.queue[0]['zoneID'], vehicle_wq.queue[0]['zoneID'])
                                                        print("----------------------------------------------------")
                                                        if wq.queue[0]['zoneID'] == vehicle_wq.queue[0]['zoneID']:
                                                            major_candidates=[{h_vehicle:0}]
                                                        elif vehicle_wq.queue[0]['link'] and vehicle_wq.queue[0]['link'].get('zoneID', '') == wq.queue[0]['zoneID']:
                                                            major_candidates=[{h_vehicle:0}]
                                                    else: # Why???
                                                        print("----------------------------------------------------")
                                                        major_candidates=[{h_vehicle:0}]
                                                except:
                                                    self.logger.debug('{} prefer {} dispatch exception!'.format(wq.queueID, h_vehicle.id))
                                                    self.logger.debug('{}'.format(traceback.format_exc()))
                                                    pass

                                            break

                                        elif wq.queueID in h_vehicle.serviceZone[0] or wq.queue[0].get('zoneID') in h_vehicle.serviceZone[0]: #2022/12/13 chocp for FST
                                            # print(wq.queueID, h_vehicle.doPreDispatchCmd, wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut'], self.vehicle_dispatch_delay.get(h_vehicle.id, 0))
                                            if h_vehicle.doPreDispatchCmd and wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'] and self.vehicle_dispatch_delay.get(h_vehicle.id, 0) < 2:
                                                can_assign=False

                                            '''if not h_vehicle.doPreDispatchCmd and (global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' or global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes') \
                                                and wq.queue[0].get('sourceType') not in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'] and self.vehicle_dispatch_delay.get(h_vehicle.id, 0) < 2:
                                                can_assign=False'''

                                            if global_variables.TSCSettings.get('Other', {}).get('WithdrawJobOnDemand') == 'yes':  #chocp 2022/10/19
                                                if h_vehicle.AgvState == 'Enroute' and not h_vehicle.force_charge and not h_vehicle.tr_cmds and not h_vehicle.adapter.cmd_sending: #chocp 2022/10/17
                                                    # h_vehicle.stop_command=True #set stop command
                                                    source_port=wq.queue[0].get('source')
                                                    if wq.queue[0].get('link'):
                                                        source_port=wq.queue[0].get('link').get('source')
                                                    distance=tools.calculate_distance(source_port, h_vehicle.adapter.last_point)
                                                    tmp_wait_stop_vehicle.append({h_vehicle:distance})

                                            if can_assign: #8.21H-3
                                                if global_variables.RackNaming == 8 and wq.queue[0].get('sourceType') == 'StockOut': #Chi 2022/12/29 for FST
                                                    dispatch_other_cmd=False
                                                    for wq1 in sorted(list(TransferWaitQueue.getAllInstance().values()), key=get_weight, reverse=True):
                                                        if len(wq1.queue)>1:
                                                            if wq1.queue[0].get('zoneID') in h_vehicle.serviceZone[0] and  wq1.queue[0].get('priority','') >wq.queue[0].get('priority',''):
                                                                avaliable, array=h_vehicle.buf_available()
                                                                if avaliable == 2:
                                                                    if wq1.dispatch_transfer(h_vehicle): #bug, chocp 2022/1/22
                                                                        need_support=False
                                                                        time.sleep(1) #wait vehicle change state
                                                                        dispatch_other_cmd=True
                                                                        break
                                                    if dispatch_other_cmd:
                                                        break
                                                    else:
                                                        if wq.dispatch_transfer(h_vehicle): #bug, chocp 2022/1/22
                                                            need_support=False
                                                            time.sleep(1) #wait vehicle change state
                                                            break
                                                else:
                                                    source_port=wq.queue[0].get('source')
                                                    if wq.queue[0].get('link'):
                                                        source_port=wq.queue[0].get('link').get('source')

                                                    if wq.vehicle_algo == 'by_battery':
                                                        battery=h_vehicle.adapter.battery["percentage"]
                                                        if major_candidates and battery<=list(major_candidates[0].values())[0]:
                                                            major_candidates.append({h_vehicle:battery}) #can add by battery
                                                        else:
                                                            major_candidates.insert(0, {h_vehicle:battery}) #can add by battery
                                                    else:
                                                        distance=tools.calculate_distance(source_port, h_vehicle.adapter.last_point)
                                                        if major_candidates and distance>list(major_candidates[0].values())[0]:
                                                            major_candidates.append({h_vehicle:distance}) #can add by distance
                                                        else:
                                                            major_candidates.insert(0, {h_vehicle:distance}) #can add by distance

                                            elif call_support: #allow other vehicle support
                                                need_support=True #8.21H-3

                                        elif wq.queueID in h_vehicle.serviceZone[1] or wq.queue[0].get('zoneID') in h_vehicle.serviceZone[1]: #2022/12/13 chocp for FST
                                            if can_assign: #8.21H-3
                                                source_port=wq.queue[0].get('source')
                                                if wq.queue[0].get('link'):
                                                    source_port=wq.queue[0].get('link').get('source')

                                                if wq.vehicle_algo == 'by_battery':
                                                    battery=h_vehicle.adapter.battery["percentage"]
                                                    if slave_candidates and battery<=list(slave_candidates[0].values())[0]:
                                                        slave_candidates.append({h_vehicle:battery}) #can add by battery
                                                    else:
                                                        slave_candidates.insert(0, {h_vehicle:battery}) #can add by battery
                                                else:
                                                    distance=tools.calculate_distance(source_port, h_vehicle.adapter.last_point)
                                                    if slave_candidates and distance>list(slave_candidates[0].values())[0]:
                                                        slave_candidates.append({h_vehicle:distance}) #can add by distance
                                                    else:
                                                        slave_candidates.insert(0, {h_vehicle:distance}) #can add by distance


                                    #print('Dispatch try end:', major_candidates, need_support, slave_candidates)
                                    if major_candidates: #8.21H-3
                                        for i in range(len(major_candidates)): #8.24D-3
                                            h_vehicle=list(major_candidates[i].keys())[0]
                                            if wq.dispatch_transfer(h_vehicle):
                                                if h_vehicle.id not in wq.dispatchedMRList:
                                                    wq.dispatchedMRList.append(h_vehicle.id)
                                                    print('dispatchedMRList',wq.dispatchedMRList)
                                                time.sleep(1)
                                                break
                                            else:
                                                continue

                                    elif need_support and slave_candidates: #8.21H-3
                                        for i in range(len(slave_candidates)):
                                            h_vehicle=list(slave_candidates[i].keys())[0]
                                            if wq.dispatch_transfer(h_vehicle):
                                                if h_vehicle.id not in wq.dispatchedMRList:
                                                    wq.dispatchedMRList.append(h_vehicle.id)
                                                    print('dispatchedMRList',wq.dispatchedMRList)
                                                time.sleep(1)
                                                break
                                            else:
                                                continue

                                    elif tmp_wait_stop_vehicle and not wq.stop_vehicle:
                                        wait_stop_vehicle=sorted(tmp_wait_stop_vehicle, key=lambda x: list(x.values()), reverse=False)
                                        h_vehicle=list(wait_stop_vehicle[0].keys())[0]
                                        h_vehicle.stop_command=True
                                        wq.stop_vehicle=True

                                wq.wq_lock.release()
                            except:
                                wq.wq_lock.release()
                                msg=traceback.format_exc()
                                self.logger.info('Handling queue:{} in dispatch() with a exception:\n {}'.format(wq.queueID, msg))
                #if else end


                #time.sleep(0.5)
                time.sleep(0.2) #chocp 2022/8/30

            except alarms.MyException as e:
                traceback.print_exc()
                time.sleep(1)

            except Exception as e:
                msg=traceback.format_exc()
                print(msg)

                alarms.CommandExceptionWarning(msg)
                time.sleep(1)
                pass

