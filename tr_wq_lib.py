import semi.e82_equipment as E82
import global_variables
import re
from global_variables import output
import time
import logging

from semi.SecsHostMgr import E82_Host

from workstation.eq_mgr import EqMgr

from global_variables import Erack
from global_variables import Equipment

#from vehicle import VehicleMgr
from global_variables import Vehicle #chocp 2022/5/30 for StockOut


import threading

from global_variables import PortsTable


from global_variables import SaveStockerInDestPortByVehicleId #K25
import tools
import copy
import alarms
import traceback

from web_service_log import *


def transfer_format_check(secsGemE82_h, commandID, TransferInfoList, is_stage=False, StageIDList=[]):
    ack=[]
    code=3
    StageList=[]
    
    print('<start transfer format check>')
    print('1.check commandID duplicate?')
    if secsGemE82_h and secsGemE82_h.check_transfer_cmd_duplicate(commandID):
        e=alarms.CommandIDDuplicatedWarning(commandID, handler=secsGemE82_h)
        if is_stage:
            return True, 3, [['STAGEID', 2]], e, StageList
        return True, 3, [['COMMANDID', 2]], e, StageList #chocp

    # check stage here
    if StageIDList:
        StageList=list(StageIDList)
        stage_found=False
        stage_pairing={}
        print("0.check if there is a stage command exist")
        for stageID in StageIDList:
            if stageID not in StageList:
                continue
            try:
                stage_tr_cmd=E82_Host.default_h.ActiveTransfers.get(stageID)
                if not stage_tr_cmd:
                    print('Cannot find stage cmd in list.')
                    StageList.remove(stageID)
                    continue
            except:
                print('Exception found when try to find stage cmd in list.')
                StageList.remove(stageID)
                continue

            if len(stage_tr_cmd['TransferInfo']) != len(TransferInfoList):
                print('Length of transferinfo mismatch.')
                StageList.remove(stageID)
                continue
                {"CarrierID": "111111", "SourcePort": "PORTX3", "DestPort": "PORTY3"}

        for TransferInfo in TransferInfoList:
            if not StageList:
                break
            tmpStageList=[]
            carrierID=TransferInfo['CarrierID']
            sourcePort=TransferInfo['SourcePort']
            destPort=TransferInfo['DestPort']
            for stageID in StageList:
                stage_tr_cmd=E82_Host.default_h.ActiveTransfers.get(stageID)

                for stage in stage_tr_cmd['TransferInfo']:
                    print('0-1.check carrier id is correct?', carrierID, stage['CarrierID'])
                    if carrierID and carrierID not in ['*']:
                        if carrierID != stage['CarrierID']:
                            continue
                    print('0-2.check source port is correct?', sourcePort, stage['SourcePort'])
                    if sourcePort and sourcePort not in ['*']:
                        if sourcePort != stage['SourcePort']:
                            h_workstation=EqMgr.getInstance().workstations.get(sourcePort)
                            if h_workstation:
                                continue
                            else: # check erack zone
                                res, rack_id, port_no=tools.rackport_format_parse(stage['SourcePort'])
                                if not res or rack_id != sourcePort:
                                    continue

                    '''if global_variables.TSCSettings.get('CommandCheck', {}).get('CarrierDuplicatedInWaitingQueueCheck') == 'yes':
                        print('0-3.check dest port is correct?', destPort, stage['DestPort'])
                        if destPort and destPort not in ['*']:
                            if destPort != stage['DestPort']:
                                h_workstation=EqMgr.getInstance().workstations.get(destPort)
                                if h_workstation:
                                    continue
                                else: # check erack zone
                                    res, rack_id, port_no=tools.rackport_format_parse(stage['DestPort'])
                                    if not res or rack_id != destPort:
                                        continue
                    else:
                        print('0-3.skip check dest port')'''

                    tmpStageList.append(stageID)
                    if stageID not in stage_pairing:
                        stage_pairing[stageID]=[]
                    stage_pairing[stageID].append({'CarrierID':stage['CarrierID'], 'SourcePort':stage['SourcePort'], 'DestPort':stage['DestPort']})
                    break

            StageList=tmpStageList

        if StageList:
            print('<stage cmd found')
            stage_tr_cmd=stage_pairing[StageList[0]]
            for idx, TransferInfo in enumerate(TransferInfoList):
                stage=stage_tr_cmd[idx]
                TransferInfo['CarrierID']=stage['CarrierID']
                TransferInfo['SourcePort']=stage['SourcePort']
                TransferInfo['DestPort']=stage['DestPort']
            return False, 0, [], 0, [StageList[0]]

    for idx, TransferInfo in enumerate(TransferInfoList):
        carrier_id_error=False
        source_error=False
        dest_error=False

        if TransferInfo.get('CarrierID') == 'None' or TransferInfo.get('CarrierID') == '*': #chocp add loss 'CarrierID' from UI batch test
            TransferInfo['CarrierID']='' #2.change format to '' if no carrierID

        carrierID=TransferInfo.get('CarrierID', '')

        sourcePort=TransferInfo.get('SourcePort', '*')
        destPort=TransferInfo.get('DestPort', '*')
        hostspecifyMR=TransferInfo.get('HostSpecifyMR', '')

        if hostspecifyMR:
            if hostspecifyMR not in Vehicle.h.vehicles:
                e=alarms.CommandSpecifyWarning(commandID, handler=secsGemE82_h)
                ack.append(["VEHICLEID", 2])
                return True, 3, ack, e, StageList
            
        h_workstation=EqMgr.getInstance().workstations.get(sourcePort)#Hshuo 240807 check sourceport disable or not
        if h_workstation and not h_workstation.enable:
            print("\n!!!!!1-1.check source port disable or not")
            e=alarms.CommandSourcePortDisable(commandID, sourcePort, handler=secsGemE82_h)
            ack.append(["SOURCEPORT", 2])

            return True, 3, ack, e, StageList
        hh_workstation=EqMgr.getInstance().workstations.get(destPort)#Hshuo 240807 check destport disable or not
        if hh_workstation and not hh_workstation.enable: 
            print("\n!!!!!1-2.dest port is diable!!!!")
            e=alarms.CommandDestPortDisable(commandID, destPort, handler=secsGemE82_h)
            ack.append(["DESTPORT", 2])

            return True, 3, ack, e, StageList

        if TransferInfo.get('CarrierType') == 'None' or TransferInfo.get('CarrierType') == 'NA': #chocp add loss 'CarrierID' from UI batch test
            TransferInfo['CarrierType']='' #3.change format to '' if no carrierType

        carrierType=TransferInfo.get('CarrierType', '')

        print('2.start check TrnaferInfo:?')
        print('Param: carrierID={}, sourcePort={}, destPort={}, carrierType={}'.format(carrierID, sourcePort, destPort, carrierType))

        carrier_type_ok=False

        #print('=>do transfer_format_check: carrierID={}, carrierType={}, sourcePort={}, destPort={}'.format(carrierID, carrierType, sourcePort, destPort))
        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes': #4.check carrierType valid or not
            print('2.check carrierType valid?')
            if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveMethod') == 'ByCarrierID':
                if carrierID:
                    prefixList=global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypePrefix').split(',')
                    for prefix in prefixList:
                        if carrierID[0:len(prefix)] == prefix:
                            carrierType=prefix
                            TransferInfo['CarrierType']=prefix
                            carrier_type_ok=True
                            break

            elif carrierType in global_variables.global_cassetteType or global_variables.RackNaming == 36:#compate with transfer cmd 
                carrier_type_ok=True

            if not carrier_type_ok:
                if idx>0 and TransferInfoList[0].get('CarrierType'):
                    carrier_type_ok=True
                    TransferInfo['CarrierType']=TransferInfoList[0].get('CarrierType')
                else:
                    e=alarms.CommandCarrierTypeNoneWarning(commandID, carrierID, carrierType, handler=secsGemE82_h)
                    return True, 5, ack, e, StageList #need debug, 2022/1/2

        if carrierID:
            if global_variables.TSCSettings.get('CommandCheck', {}).get('CarrierWhiteMask') == 'yes': #6.check valid or not in carrierID white list
                print('3.check carrierID valid in whitelist?')
                if global_variables.RackNaming == 5:
                    if 'C12N2' in carrierID: #for LG 2022/6/7
                        e=alarms.CommandCarrierNotInWhiteListWarning(commandID, carrierID, handler=secsGemE82_h)
                        return True, 5, ack, e, StageList

                elif not global_variables.WhiteCarriersMask.get(carrierID):
                    e=alarms.CommandCarrierNotInWhiteListWarning(commandID, carrierID, handler=secsGemE82_h)
                    return True, 5, ack, e, StageList

            for queueID, zone_wq in TransferWaitQueue.getAllInstance().items(): #7. check if carrierID duplicator in waiting queue
                for host_tr_cmd in zone_wq.queue:
                    if host_tr_cmd['carrierID'] == carrierID:
                        if global_variables.TSCSettings.get('CommandCheck', {}).get('CarrierDuplicatedInWaitingQueueCheck') == 'yes' or host_tr_cmd['stage']:
                            print('4.check carrierID duplicate in waiting queue?')
                            e=alarms.CommandCarrierDuplicatedInWaitingQueueWarning(commandID, carrierID, host_tr_cmd['uuid'], handler=secsGemE82_h)
                            ack.append(["CARRIERID", 2])
                            return True, 5, ack, e, StageList
                        else: #cancel before cmd in waiting queue  
                            host_command_id=host_tr_cmd['uuid']
                            #zone_wq.remove_waiting_transfer_by_commandID(host_command_id, cause='by command check', sub_code='TSC015', handler=secsGemE82_h)  #remind user chocp 2022/10/11, 2022/10/11
                            zone_wq.remove_waiting_transfer_by_commandID(host_command_id, cause='by command check', sub_code='TSC015')  #fix 2023/11/13
                            E82.report_event(secsGemE82_h, E82.TransferCancelInitiated, {'CommandID':host_command_id,'CommandInfo':host_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':host_tr_cmd.get('OriginalTransferCompleteInfo','')}) #chocp 2022/3/11 add

                            if secsGemE82_h:
                                secsGemE82_h.rm_transfer_cmd(host_command_id)

                            for transferinfo in host_tr_cmd['OriginalTransferInfoList']:
                                host_tr_cmd['OriginalTransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':transferinfo['SourcePort']}) #bug, need check

                            E82.report_event(secsGemE82_h,
                                E82.TransferCancelCompleted, {
                                'CommandInfo':host_tr_cmd.get('CommandInfo',''),
                                'CommandID':host_command_id,
                                'TransferCompleteInfo':host_tr_cmd['OriginalTransferCompleteInfo'], #9/13
                                }) #chocp 2022/3/11 change seq

                            if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes': #only for RTD mode???
                                if '-UNLOAD' not in host_command_id:
                                    EqMgr.getInstance().orderMgr.update_work_status(host_command_id, 'FAIL', 'CarrierDuplicatedInWaitingQueue')
                            break
            else: #8. check if carrierID duplicator in executing queue
                #if global_variables.RackNaming!=3: #exclude tfme
                if global_variables.TSCSettings.get('CommandCheck', {}).get('CarrierDuplicatedInExecutingQueueCheck') == 'yes':
                    print('5.check carrierID duplicate in executing queue?')
                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                        for local_tr_cmd in h_vehicle.tr_cmds:
                            if local_tr_cmd['carrierID'] == carrierID:
                                e=alarms.CommandCarrierDuplicatedInExecutingQueueWarning(commandID, carrierID, local_tr_cmd['uuid'], handler=secsGemE82_h)
                                ack.append(["CARRIERID", 2])
                                return True, 5, ack, e, StageList

            print('6.check carrierID location valid or conflict?')
            res, new_source_port=tools.re_assign_source_port(carrierID) #try locate carrier test
            #replace sourcePort
            if '*' in sourcePort or sourcePort == 'E0P0' or sourcePort == '' or not EqMgr.getInstance().workstations.get(sourcePort) or new_source_port[:-5] in Vehicle.h.vehicles:
            #if '*' in sourcePort or sourcePort == 'E0P0' or sourcePort == '' or not EqMgr.getInstance().workstations.get(sourcePort) or source_port[:-5] in Vehicle.h.vehicles: ???
                if not res:
                    e=alarms.CommandCarrierLocateWarning(commandID, carrierID, handler=secsGemE82_h)
                    ack.append(["CARRIERID", 2])
                    return True, 3, ack, e, StageList
                
                if  is_stage and new_source_port[:-5] in Vehicle.h.vehicles:
                    e=alarms.CommandSourcePortConflictWarning(commandID, sourcePort, carrierID, handler=secsGemE82_h) #chocp 2021/11/8
                    ack.append(["SOURCEPORT", 2])
                    return True, 3, ack, e, StageList

                sourcePort=new_source_port #reassign soure port if source port not clear
                TransferInfo['SourcePort']=new_source_port

            if res and sourcePort!=new_source_port: #8. check source port from transfer is equal to real location
                if global_variables.RackNaming == 9: #chi 2022/12/22 for qualcomm
                    sector_name=''
                    sourceport_format=copy.deepcopy(new_source_port)
                    if '-' in sourceport_format:
                        rackid, portnum=sourceport_format.split('-')
                        h_eRack=Erack.h.eRacks.get(rackid)
                        if '0' in portnum:
                            portnum=portnum.split('0')[1]
                        sector_name=h_eRack.carriers[int(portnum)-1]['area_id']

                    if sourcePort != sector_name:
                        e=alarms.CommandSourcePortConflictWarning(commandID, sourcePort, carrierID, handler=secsGemE82_h) #chocp 2021/11/8
                        ack.append(["SOURCEPORT", 2])
                        return True, 3, ack, e, StageList
                    else:
                        sourcePort=new_source_port
                        TransferInfo['SourcePort']=new_source_port
                else:
                    e=alarms.CommandSourcePortConflictWarning(commandID, sourcePort, carrierID, handler=secsGemE82_h) #chocp 2021/11/8
                    ack.append(["SOURCEPORT", 2])
                    return True, 3, ack, e, StageList
        else: #if no carrierID
            print('6.check sourcePort valid?')
            if '*' in sourcePort or sourcePort == 'E0P0' or sourcePort == '': #if carrierID not specified, chocp add '' == '*' 20230523: 
                e=alarms.CommandSourcePortNullWarning(commandID, sourcePort, handler=secsGemE82_h) #chocp 2021/11/8
                ack.append(["SOURCEPORT", 2])
                return True, 3, ack, e, StageList
            else:
                if not EqMgr.getInstance().workstations.get(sourcePort): #This is not a workstation
                    print('6-1.check empty move sourcePort format?')
                    res, new_source_port, carrierID=tools.select_any_carrier_by_area(sourcePort, carrierType) #for emptymove cmd ???only support area???
                    if res:
                        sourcePort=new_source_port
                        TransferInfo['SourcePort']=new_source_port
                        TransferInfo['CarrierID']=carrierID
                    elif new_source_port!='*': # Mike: 2022/12/05
                        e=alarms.NoAvailableCarrierWarning(sourcePort)
                        ack.append(["SOURCEPORT", 2])
                        return True, 3, ack, e, StageList
                    else:
                        pass

        if global_variables.TSCSettings.get('CommandCheck', {}).get('SourcePortDuplicatedCheck') == 'yes': #Chi 2023/02/16
            SourcePortDuplicatedCheck=True
            h_workstation=EqMgr.getInstance().workstations.get(sourcePort)
            if h_workstation:
                h_workstation_type=h_workstation.workstation_type
                if global_variables.RackNaming != 36:# kelvinng  20250125
                    if 'Stock' in h_workstation_type:
                        SourcePortDuplicatedCheck=False
                else:
                    tr_wq_lib_logger.debug("h_workstation.equipmentID in check:{}".format(h_workstation.equipmentID))
                    if 'Stock' in h_workstation_type:
                        SourcePortDuplicatedCheck=False
                    elif h_workstation.equipmentID in ['EQ_3800_MGZ', 'EQ_3800_CRR']:
                        SourcePortDuplicatedCheck=False

            for queueID, zone_wq in TransferWaitQueue.getAllInstance().items(): #check duplicator in waiting queue
                for host_tr_cmd in zone_wq.queue:
                    #if host_tr_cmd['dest'] == destPort:
                    if host_tr_cmd['source'] == sourcePort and SourcePortDuplicatedCheck:
                        e=alarms.CommandSourcetPortDuplicatedWarning(commandID, sourcePort, host_tr_cmd['uuid'], handler=secsGemE82_h)
                        ack.append(["SOURCEPORT", 2])
                        return True, 3, ack, e, StageList
            else:#check duplicator in executing queue
                if global_variables.RackNaming != 36:
                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                        for local_tr_cmd in h_vehicle.tr_cmds:
                            if local_tr_cmd['source'] == sourcePort:
                                e=alarms.CommandSourcetPortDuplicatedWarning(commandID, sourcePort, local_tr_cmd['uuid'], handler=secsGemE82_h)
                                ack.append(["SOURCEPORT", 2])
                                return True, 3, ack, e, StageList

        print('=>Check SourcePort In Map?', sourcePort)
        for st in PortsTable.reverse_mapping:
            if sourcePort in PortsTable.reverse_mapping[st]:
                break
        else:
            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                if h_vehicle.id in sourcePort:
                    break
            else:
                e=alarms.CommandSourcePortNotFoundWarning(commandID, sourcePort, handler=secsGemE82_h)
                ack.append(["SOURCEPORT", 2])
                return True, 3, ack, e, StageList

        print('=>Final Check SourcePort', sourcePort)

        res=False
        default_erack=''
        new_dest_port=''

        h_workstation=EqMgr.getInstance().workstations.get(sourcePort)
        return_to=getattr(h_workstation, 'back_erack', '') #no exception

        '''check=True
        res, rack_id, port_no=tools.rackport_format_parse(destPort)
        if res:
            check=False
        if global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' and h_workstation and h_workstation.workstation_type in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']:
            check=False'''
        check=False
        if destPort not in EqMgr.getInstance().workstations or return_to and return_to not in EqMgr.getInstance().workstations:
            check=True
        if global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' and h_workstation and h_workstation.workstation_type in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']:
            check=False
        res, rack_id, port_no=tools.rackport_format_parse(sourcePort)
        if res: # Erack to erack
            check=False

        if global_variables.TSCSettings.get('Other', {}).get('BookLater', 'no') == 'yes' and check:
            new_dest_port=destPort
            if EqMgr.getInstance().workstations.get(destPort):
                res=True
            elif global_variables.TSCSettings.get('CommandCheck', {}).get('ReturnToFirst') == 'yes' and return_to:
                res=True
                new_dest_port=return_to
            elif destPort == '' or destPort == '*' or destPort[:-5] in Vehicle.h.vehicles: #GF 1: acquire to the MR itself cmd
                #if Dest is '*', not support Source is 'MRxxx'
                if sourcePort[:-5] in Vehicle.h.vehicles:
                    return True, 3, ack, alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h), StageList #GF 2: reject MR to MR itself

                if idx<len(TransferInfoList)-1: #GF 3: reject replace cmd, swap port is AMR buf
                    code=3
                    ack.append(["DESTPORT", 2])
                    return True, 3, ack, alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h), StageList

                res=True
            else:
                res, new_dest_port=tools.preserved_dest_port_in_racks(destPort, TransferInfo.get('CarrierType', ''))
            print(res, new_dest_port)
            if res:
                TransferInfo['DestPort']=new_dest_port
                continue
            else:
                return True, 3, ack, alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h), StageList

        if global_variables.TSCSettings.get('CommandCheck', {}).get('ReturnToFirst') == 'yes' and return_to:
            res, new_dest_port=tools.auto_assign_return_to_port(h_workstation.back_erack, TransferInfo.get('CarrierType', ''))
            if not res: # 2024/09/23 Yuri
                res, new_dest_port=tools.new_auto_assign_dest_port(h_workstation.back_erack, TransferInfo.get('CarrierType', ''))

        elif destPort == '' or destPort == '*' or destPort[:-5] in Vehicle.h.vehicles: #GF 1: acquire to the MR itself cmd
            #if Dest is '*', not support Source is 'MRxxx'
            if sourcePort[:-5] in Vehicle.h.vehicles:
                return True, 3, ack, alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h), StageList #GF 2: reject MR to MR itself

            if idx<len(TransferInfoList)-1: #GF 3: reject replace cmd, swap port is AMR buf
                code=3
                ack.append(["DESTPORT", 2])
                return True, 3, ack, alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h), StageList

            return False, 0, [], 0, StageList #check  success and exit
        
        elif destPort == 'E0P0' and h_workstation: #for ASECL, may ignore...
            if return_to.lower() == 'back': #set back for asecl
                res, default_erack, port_no=tools.rackport_format_parse(h_workstation.carrier_source)
            else:
                default_erack=return_to  #set return_to, xxx|yyy,zzz
            #end select default_erack
            res, new_dest_port=tools.new_auto_assign_dest_port(default_erack, TransferInfo.get('CarrierType', '')) #for tfme 9/28

        else: #DestPort may xxx|yyy,zzz or xxx
            res, new_dest_port=tools.auto_assign_return_to_port(destPort, TransferInfo.get('CarrierType', '')) #MRxxxBUF0X???
            if not res:
                res, new_dest_port=tools.new_auto_assign_dest_port(destPort, TransferInfo.get('CarrierType', ''))

        if global_variables.TSCSettings.get('CommandCheck', {}).get('WSSamplingEnable') == 'yes':  #Jwo: 2023/02/24 for SPIL LG SampleDestSector
            #print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'+'WSSamplingEnable'+'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
            for Eqtype in global_variables.WSSettings: # check if SourcePort is EQ
                #print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'+'Eqtype for loop'+'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                re_pattern=r"^N0\d+" + Eqtype['WSType']
                if re.search(re_pattern, TransferInfo["SourcePort"]):
                    # eq_set=set()
                    # eq_set=tools.sampling_time_check(eq_set)
                    tools.eqset=tools.sampling_time_check(tools.eqset)
                    eq_set=tools.eqset
                    print('EQ SourcePort',TransferInfo["SourcePort"],eq_set)

                    if not TransferInfo["SourcePort"] in eq_set:

                        eq_set.add(TransferInfo["SourcePort"])
                        print(eq_set)

                        res_1, new_dest_port=tools.new_auto_assign_dest_port(Eqtype['DestSector'], TransferInfo.get('carrierType', '')) # change to wait inspect sector
                        if res_1 == False:
                            res_1, new_dest_port=tools.new_auto_assign_dest_port(Eqtype['IfFullUnloadErack'], TransferInfo.get('carrierType', ''))
                    else:
                        pass
                else:
                    pass

        if not res:
            e=alarms.CommandDestPortAssignFailWarning(commandID, destPort, handler=secsGemE82_h)
            dest_error=True
            code=3
            ack.append(["DESTPORT", 2])

            return True, 3, ack, e, StageList

        destPort=new_dest_port
        TransferInfo['DestPort']=new_dest_port

        #check dest duplicate
        if global_variables.TSCSettings.get('CommandCheck', {}).get('DestPortDuplicatedCheck') == 'yes': #for spil CP check dest duplicate
            #check duplicator in waiting queue
            DestPortDuplicatedCheck=True
            h_workstation=EqMgr.getInstance().workstations.get(destPort)
            if h_workstation:
                h_workstation_type=h_workstation.workstation_type
                if global_variables.RackNaming != 36:
                    if 'Stock' in h_workstation_type:
                        DestPortDuplicatedCheck=False
                else:
                    if 'Stock' in h_workstation_type:
                        DestPortDuplicatedCheck=False
                    elif h_workstation.equipmentID in ['EQ_3800_MGZ', 'EQ_3800_CRR']:
                        DestPortDuplicatedCheck=False

            for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                for host_tr_cmd in zone_wq.queue:
                    #if host_tr_cmd['dest'] == destPort:
                    if host_tr_cmd['dest'] == destPort and DestPortDuplicatedCheck: #chocp 2022/5/24 only for workstation... 2024/02/17 for all except Stock type
                        e=alarms.CommandDestPortDuplicatedWarning(commandID, destPort, host_tr_cmd['uuid'], handler=secsGemE82_h)
                        ack.append(["DESTPORT", 2])
                        return True, 3, ack, e, StageList
            else:#check duplicator in executing queue
                #for vehicle_id, h_vehicle in VehicleMgr.getInstance().vehicles.items():
                if global_variables.RackNaming != 36:
                    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                        for local_tr_cmd in h_vehicle.tr_cmds:
                            if local_tr_cmd['dest'] == destPort and DestPortDuplicatedCheck:
                                e=alarms.CommandDestPortDuplicatedWarning(commandID, destPort, local_tr_cmd['uuid'], handler=secsGemE82_h)
                                ack.append(["DESTPORT", 2])
                                return True, 3, ack, e, StageList

        print('=>Check DestPort In Map', destPort) #not check MRxxxBUF0x
        for st in PortsTable.reverse_mapping:
            if destPort in PortsTable.reverse_mapping[st]:
                break
        else:
            #for vehicle_id, h_vehicle in VehicleMgr.getInstance().vehicles.items():
            for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
                if h_vehicle.id in destPort:
                    break
            else:
                e=alarms.CommandDestPortNotFoundWarning(commandID, destPort, handler=secsGemE82_h)
                ack.append(["DESTPORT", 2])

                return True, 3, ack, e, StageList
        
                        
        if carrier_type_ok and global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('ErackCassetteTypeCheck') == 'yes': #8.22-2
            print('=>do ErackCassetteType check...') #not check MRxxxBUF0x
            sourceport_res, source_rack_id, source_port_no=tools.rackport_format_parse(sourcePort)  #2024/1/2
            destport_res, dest_rack_id, dest_port_no=tools.rackport_format_parse(destPort)  #2024/1/2

            for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                if sourceport_res and rack_id == source_rack_id:
                    res=tools.erack_slot_type_verify(h_eRack, source_port_no, carrierType)
                    if not res:
                        print(1, carrierType, h_eRack.validSlotType)
                        e=alarms.CommandSourceErackCarrierTypefailWarning(commandID, carrierID, TransferInfo.get('CarrierType', ''), sourcePort, h_eRack.validSlotType, handler=secsGemE82_h)
                        return True, 3, ack, e, StageList

                elif destport_res and rack_id == dest_rack_id:
                    res=tools.erack_slot_type_verify(h_eRack, dest_port_no, carrierType)
                    if not res:
                        print(2, carrierType, h_eRack.validSlotType)
                        e=alarms.CommandDestErackCarrierTypefailWarning(commandID, carrierID, TransferInfo.get('CarrierType', ''), destPort, h_eRack.validSlotType, handler=secsGemE82_h)
                        return True, 3, ack, e, StageList

        print('<final transfer cmd check?')
    return False, 0, [], 0, StageList



class TransferWaitQueue():
    __instance={}
    @staticmethod
    def getAllInstance():
        return TransferWaitQueue.__instance

    @staticmethod
    def getInstance(queueID, setting={}):
        h=TransferWaitQueue.__instance.get(queueID)
        if h:
            h.update_params(setting)
            return h
        else:
            secsgem_e82_h=E82_Host.getInstance(queueID)
            return TransferWaitQueue(secsgem_e82_h, queueID, setting)

    def __init__(self, secsgem_e82_h, queueID, setting): #need create for all zone and all vehicle waiting queue
        self.queueID=queueID
        self.secsgem_e82_h=secsgem_e82_h
        #self.queueType='Normal' #2022/12/13 chocp
        #self.preferZoneID='' #for FST
        self.my_lock=threading.Lock()
        self.wq_lock=threading.Lock()
        self.queue=[]
        self.tr_point={}#add Yuri
        self.linked_list=[]
        self.transfer_list={}
        self.dispatchedMRList=[]
        self.lot_list={}
        self.waiting_credit=0
        self.single_transfer_total=0
        self.replace_transfer_total=0
        self.last_add_time=0

        self.log_flag=0
        self.stop_vehicle=False
        self.can_dispatch_lot_in=False
        self.can_dispatch_lot_out=False

        self.preferVehicle='' #for StockOut
        self.activeHandlingType=''
        self.relation_links=[]

        self.tr_add_assert={}
    
        self.logger=logging.getLogger("tsc") #chi 2022/08/11

        #default setting
        self.default_setting={
            'mergeMaxCmds':6,
            'mergeStartTime':0,
            'mergeMaxEqps':6,
            'mergeMaxLots':8,
            'collectTimeout':60, #GF need fix for other
            'commandLivingTime':3600,
            'scheduleAlgo':'by_lowest_cost',
            'vehicleAlgo':'by_lowest_distance',
            'enable':'yes',  #Hshuo 240801
            'vehicleMaxCapacity': -1
        }

        self.merge_max_cmds=6 #8.22C-2
        self.merge_start_time=0
        self.merge_max_eqps=6
        self.merge_max_lots=8
        self.collect_timeout=10 #GF ...
        self.commandLivingTime=3600 #2022/11/23
        self.schedule_algo='by_lowest_cost' #for oven
        self.vehicle_algo='by_lowest_distance' 
        self.enable='yes' #Hshuo 240801


        if setting:
            self.update_params(setting)

        elif global_variables.OtherZoneSetting:
            self.update_params(global_variables.OtherZoneSetting)

        else:
            self.update_params(self.default_setting)

        TransferWaitQueue.__instance[queueID]=self
        print('******************************************************')
        print('TransferWaitQueue', 'init', queueID, self.secsgem_e82_h)
        print('******************************************************')

    def update_params(self, setting): #chocp add 2022/4/12
        if setting:
            print('<<update batch run params in waiting queue>>:{}, {}'.format(self.queueID, setting))
            #self.setting=setting
            self.merge_max_cmds=int(setting.get('mergeMaxCmds', 6))
            self.merge_start_time=int(setting.get('mergeStartTime', 0))
            self.merge_max_eqps=int(setting.get('mergeMaxEqps', 6))
            self.merge_max_lots=int(setting.get('mergeMaxLots', 8))
            self.collect_timeout=int(setting.get('collectTimeout', 60))
            self.commandLivingTime=int(setting.get('commandLivingTime', 3600)) #2022/11/23
            schedule_algo=setting.get('scheduleAlgo') #2022/6/23
            self.schedule_algo=schedule_algo if schedule_algo in ['by_lowest_cost', 'by_fix_order', 'by_better_cost', 'by_priority'] else 'by_lowest_cost'
            self.vehicle_algo=setting.get('vehicleAlgo','by_lowest_distance')
            enable=setting.get('enable') #Hshuo 240801
            self.enable=enable if enable in ['yes', 'no'] else 'yes' #Hshuo 240801
            self.vehicleMaxCapacity=int(setting.get('vehicleMaxCapacity', -1))

    def add_transfer_into_queue_directly(self, host_tr_cmd, idx=-1):
        self.last_add_time=time.time()
        self.my_lock.acquire()

        if idx<0:
            self.queue.append(host_tr_cmd)
        else:
            self.queue.insert(idx, host_tr_cmd)

        if host_tr_cmd.get('replace', 0):
            #self.single_transfer_total+=2
            self.replace_transfer_total+=1
        else:
            self.single_transfer_total+=1

        self.transfer_list[host_tr_cmd['uuid']]=host_tr_cmd

        self.my_lock.release()

    def add_transfer_into_queue(self, host_tr_cmd, idx, action='insert'):
        self.last_add_time=time.time()

        self.my_lock.acquire()

        if idx<0:
            self.queue.append(host_tr_cmd)
        else:
            self.queue.insert(idx, host_tr_cmd)
        #print('\nAdd after queue\n', self.queue)

        #Unload first, and load after
        #Unload primary, and link to load cmd
        #load is not primary, no link
        if action == 'combine_with_next':
            self.queue[idx]['link']=self.queue[idx+1]
            self.queue[idx+1]['primary']=0
            self.linked_list.append(self.queue[idx]['uuid'])
            self.linked_list.append(self.queue[idx+1]['uuid'])

        elif action == 'combine_with_before':
            self.queue[idx-1]['link']=self.queue[idx]
            self.queue[idx]['primary']=0
            self.linked_list.append(self.queue[idx-1]['uuid'])
            self.linked_list.append(self.queue[idx]['uuid'])

        '''#Unload first, and load after
        #Unload not primary, no link
        #load is primary, with link to unload cmd
        if action == 'combine_with_next':
            self.queue[idx+1]['link']=self.queue[idx]
            self.queue[idx]['primary']=0
            #print('combine_with_next:')
            #print(self.queue[idx+1])

        elif action == 'combine_with_before':
            self.queue[idx]['link']=self.queue[idx-1]
            self.queue[idx-1]['primary']=0
            #print('combine_with_before:')
            #print(self.queue[idx])'''
        if host_tr_cmd.get('replace', 0):
            #self.single_transfer_total+=2
            self.replace_transfer_total+=1
        else:
            self.single_transfer_total+=1

        # print('linked_list', self.linked_list)

        self.transfer_list[host_tr_cmd['uuid']]=host_tr_cmd

        self.my_lock.release()


    def change_transfer_priority(self, host_tr_cmd_id, new_priority, skip_lock=False):
        host_tr_cmd=self.transfer_list[host_tr_cmd_id]
        if host_tr_cmd['priority'] == new_priority:
            return
        if not skip_lock:
            print('In change_transfer_priority, try lock acquire')
            self.wq_lock.acquire()
        else:
            print('In change_transfer_priority, skip lock acquire')
        try:
            link_tr_cmd=None
            link_priority=-1
            current_index=-1
            update_index=-1
            link_index=-1
            last_waiting_tr_cmd={}
            for idx, waiting_tr_cmd in enumerate(self.queue):
                if new_priority > waiting_tr_cmd['priority'] and update_index < 0:
                    update_index=idx
                if waiting_tr_cmd['uuid'] == host_tr_cmd['uuid']:
                    current_index=idx
                    if host_tr_cmd['link']:
                        link_index=idx+1
                        link_tr_cmd=host_tr_cmd['link']
                    if last_waiting_tr_cmd.get('link', {}) == host_tr_cmd:
                        link_index=idx-1
                        link_tr_cmd=last_waiting_tr_cmd
                    if link_tr_cmd:
                        link_priority=link_tr_cmd.get('original_priority', link_tr_cmd['priority'])
                        if link_priority < new_priority: # change to new priority
                            host_tr_cmd['original_priority']=new_priority
                            host_tr_cmd['priority']=new_priority
                            link_tr_cmd['priority']=new_priority
                            break
                        else:
                            if host_tr_cmd['priority'] < new_priority: # change to link priority
                                host_tr_cmd['original_priority']=new_priority
                                host_tr_cmd['priority']=link_priority
                                link_tr_cmd['priority']=link_priority
                                new_priority=link_priority
                            else: # no change
                                update_index=-1
                                host_tr_cmd['original_priority']=new_priority
                                break
                    else:
                        host_tr_cmd['original_priority']=new_priority
                        host_tr_cmd['priority']=new_priority
                        break
                last_waiting_tr_cmd=waiting_tr_cmd

            if update_index >= 0:
                if link_tr_cmd:
                    self.remove_transfer_from_queue_directly(host_tr_cmd)
                    self.remove_transfer_from_queue_directly(link_tr_cmd)
                    host_tr_cmd['link']=None
                    host_tr_cmd['primary']=1
                    link_tr_cmd['link']=None
                    link_tr_cmd['primary']=1
                    if global_variables.RackNaming in [16,23,34, 54]:
                        idx=self.add_transfer_into_queue_with_check_sj_new(host_tr_cmd)
                        idx=self.add_transfer_into_queue_with_check_sj_new(link_tr_cmd)
                    else:
                        idx=self.add_transfer_into_queue_with_check_common(host_tr_cmd)
                        idx=self.add_transfer_into_queue_with_check_common(link_tr_cmd)
                else:
                    self.remove_transfer_from_queue_directly(host_tr_cmd)
                    if global_variables.RackNaming in [16,23,34, 54]:
                        idx=self.add_transfer_into_queue_with_check_sj_new(host_tr_cmd)
                    else:
                        idx=self.add_transfer_into_queue_with_check_common(host_tr_cmd)

            if not skip_lock:
                self.wq_lock.release()

        except:
            if not skip_lock:
                self.wq_lock.release()
            msg=traceback.format_exc()
            #self.logger.info('Handling queue:{} in change_transfer_priority() with a exception:\n {}'.format(self.wq.queueID, msg))
            self.logger.info('Handling queue:{} in change_transfer_priority() with a exception:\n {}'.format(self.queueID, msg))
            pass

    def add_transfer_into_queue_with_check(self, host_tr_cmd):
        print('In add_transfer_into_queue_with_check, try lock acquire')
        self.wq_lock.acquire()
        try:
            if global_variables.RackNaming in [16,23,34,54]:
                idx=self.add_transfer_into_queue_with_check_sj_new(host_tr_cmd)
            else:
                idx=self.add_transfer_into_queue_with_check_common(host_tr_cmd)
                
            if global_variables.RackNaming == 40:
                lotID = host_tr_cmd['TransferInfoList'][0].get('LotID')
                lotNum = host_tr_cmd['TransferInfoList'][0].get('LotNum')
                handlingType = host_tr_cmd.get('handlingType','')
                if lotID and lotNum and handlingType and handlingType in ['In', 'Out']:
                    self.lot_list=tools.update_lot_list(self.lot_list, lotID, host_tr_cmd["uuid"], lotNum,handlingType)

                print(self.lot_list) 
            print("{} queue priority >>>".format(self.queueID),[(cmd['uuid'],cmd['priority']) for cmd in self.queue])
            print("{} queue lot >>>".format(self.queueID),[(cmd['uuid'],cmd['TransferInfoList'][0].get('LotID')) for cmd in self.queue])

            '''for tr_cmd in self.queue:
                print([tr_cmd['carrierID'], tr_cmd['source'], tr_cmd['dest']])'''

            if host_tr_cmd.get('replace', False):
                EqMgr.getInstance().trigger(host_tr_cmd['dest'], 'replace_transfer_cmd')

            elif host_tr_cmd['TransferInfoList'][0].get('link'): #add for UTAC...
                EqMgr.getInstance().trigger(host_tr_cmd['source'], 'replace_transfer_cmd')
                
            else:
                res, rack_id, port_no=tools.rackport_format_parse(host_tr_cmd['source']) #fix2
                if res: #It's Erack???
                    EqMgr.getInstance().trigger(host_tr_cmd['dest'], 'load_transfer_cmd')
                elif 'BUF' in host_tr_cmd['source']:
                    EqMgr.getInstance().trigger(host_tr_cmd['dest'], 'load_transfer_cmd')
                else:
                    EqMgr.getInstance().trigger(host_tr_cmd['source'], 'unload_transfer_cmd') #may conflick with replace
                    if tools.find_point(host_tr_cmd['source']) in self.tr_point:#Yuri 2024/11/07
                        self.tr_point[tools.find_point(host_tr_cmd['source'])].append([idx if idx > 0 else len(self.queue)-1, host_tr_cmd])
                    else:
                        self.tr_point[tools.find_point(host_tr_cmd['source'])]=[[idx if idx > 0 else len(self.queue)-1, host_tr_cmd]] 

            output('TransferWaitQueueAdd', {
                    'Channel':host_tr_cmd.get('channel', 'Internal'), #chocp 2022/6/13
                    'Idx':idx,
                    'CarrierID':host_tr_cmd['carrierID'],
                    'CarrierType':host_tr_cmd['TransferInfoList'][0].get('CarrierType', ''), #chocp 2022/2/9
                    'TransferInfoList':host_tr_cmd['TransferInfoList'],
                    'ZoneID':host_tr_cmd['zoneID'],  #chocp 9/14
                    'Source':host_tr_cmd['source'],
                    'Dest':host_tr_cmd['dest'],
                    'CommandID':host_tr_cmd["uuid"],
                    'Priority':host_tr_cmd["priority"] if not host_tr_cmd.get('original_priority','') else host_tr_cmd['original_priority'],
                    'Replace':host_tr_cmd['replace'],
                    'Back':host_tr_cmd['back'],
                    'OperatorID':host_tr_cmd.get('operatorID', '')
                    }, True)
            # Mike: 2022/12/02
            try:
                ActiveTransfers=E82.get_variables(self.secsgem_e82_h, 'ActiveTransfers')
                ActiveTransfers[host_tr_cmd.get('uuid', '')]['CommandInfo']['TransferState']=6
                E82.update_variables(self.secsgem_e82_h, {'ActiveTransfers': ActiveTransfers})
            except:
                pass

            #if host_tr_cmd['sourceType']!='FromVehicle': #GRA, already report smae event in zone queue
            #    E82.report_event(self.secsgem_e82_h, E82.TransferInitiated, {'CommandID':host_tr_cmd["uuid"]})
            if not host_tr_cmd.get('stage', 0):
                E82.report_event(self.secsgem_e82_h, E82.TransferInitiated, {'CommandID':host_tr_cmd["uuid"],'CommandInfo':host_tr_cmd['CommandInfo'],'TransferCompleteInfo':host_tr_cmd['OriginalTransferCompleteInfo']})
                output('TransferInitiated',  {'CommandID':host_tr_cmd["uuid"]})

            print('add_waiting_transfer_list', self.queueID, self.single_transfer_total, self.replace_transfer_total)

            self.wq_lock.release()

        except:
            self.wq_lock.release()
            msg=traceback.format_exc()
            #self.logger.info('Handling queue:{} in add_transfer_into_queue_with_check() with a exception:\n {}'.format(self.wq.queueID, msg))
            self.logger.info('Handling queue:{} in add_transfer_into_queue_with_check() with a exception:\n {}'.format(self.queueID, msg))
            pass

    # def add_transfer_into_queue_with_check_for_sj(self, host_tr_cmd):
    #     idx=0
    #     last_same_equipment_idx=-1 #for oven
    #     for idx, waiting_tr_cmd in enumerate(self.queue):
    #         #test same if there is equipment transfer cmd
    #         SpaceLP=global_variables.RackPortFormat[global_variables.RackNaming-1][4]
    #         if SpaceLP:
    #             res=re.match(SpaceLP, host_tr_cmd['source'])
    #             if res and res.group(1) in [waiting_tr_cmd['source'], waiting_tr_cmd['dest']]:
    #                 last_same_equipment_idx=idx

    #             res=re.match(SpaceLP, host_tr_cmd['dest'])
    #             if res and res.group(1) in [waiting_tr_cmd['source'], waiting_tr_cmd['dest']]:
    #                 last_same_equipment_idx=idx

    #         if not host_tr_cmd['replace']:
    #             res=-1
    #             if host_tr_cmd['source'] == waiting_tr_cmd['dest']:
    #                 #print('2 head insert', idx)
    #                 if not waiting_tr_cmd['primary']: #avoid Dest Duplicatecmd, chocp 2022/4/28
    #                     #break
    #                     continue #fix for GB and duplicate dest

    #                 self.add_transfer_into_queue(host_tr_cmd, idx, 'combine_with_next') #host_tr_cmd is unload cmd
    #                 return idx

    #             elif host_tr_cmd['dest'] == waiting_tr_cmd['source']:
    #                 #print('3 Trail insert', idx+1)
    #                 if waiting_tr_cmd['link'] or ('BUF' in host_tr_cmd['dest'] and waiting_tr_cmd['primary']): #avoid Dest Duplicatecmd, chocp 2022/4/28 ???? #8.28.5
    #                 #if waiting_tr_cmd['link']: #avoid Dest Duplicatecmd, chocp 2022/4/28 ????
    #                     #break #????
    #                     continue #fix for GB and duplicate source
                    
    #                 if host_tr_cmd['sourceType'] == 'FromVehicle':
    #                     #if host from MR to EqPort, set priority high
    #                     #remove_idx_from_queue
    #                     #add waiting_tr_cmd to first
    #                     self.remove_transfer_from_queue_directly(waiting_tr_cmd)
    #                     self.add_transfer_into_queue_directly(waiting_tr_cmd, 0)
    #                     self.add_transfer_into_queue(host_tr_cmd, 1, 'combine_with_before') 
    #                 else:
    #                     self.add_transfer_into_queue(host_tr_cmd, idx+1, 'combine_with_before') #host_tr_cmd is load cmd
    #                 return idx

    #     #print('4 Insert first')
    #     if host_tr_cmd['sourceType'] == 'FromVehicle':
    #         self.add_transfer_into_queue(host_tr_cmd, 0)
    #     else:
    #         #print('4 Trail append', len(self.queue))
    #         #same equipmentID bundle together
    #         if last_same_equipment_idx>0: 
    #             self.add_transfer_into_queue(host_tr_cmd, last_same_equipment_idx+1)
    #         else:
    #             self.add_transfer_into_queue(host_tr_cmd, len(self.queue)) #9/9
    #     return idx
    def add_transfer_into_queue_with_check_sj_new(self, host_tr_cmd):
        host_idx=-1
        last_priority_101_idx=-1
        for idx, waiting_tr_cmd in enumerate(self.queue):

            if host_tr_cmd['priority']>waiting_tr_cmd['priority'] and host_idx < 0: #fifo
                host_idx=idx
                
            if waiting_tr_cmd['priority'] == 101:
                last_priority_101_idx=idx

            if not host_tr_cmd['replace'] and not waiting_tr_cmd['replace']: #try schedule to swap transfer
                res=-1
                if host_tr_cmd['source'] == waiting_tr_cmd['dest']:
                    if not waiting_tr_cmd['primary']: #avoid Dest Duplicatecmd, chocp 2022/4/28
                        continue #fix for GB and duplicate dest

                    if host_idx < 0:
                        host_tr_cmd['original_priority']= host_tr_cmd['priority']
                        host_tr_cmd['priority']=waiting_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, idx, 'combine_with_next') #host_tr_cmd is unload cmd
                        host_idx=idx
                        return host_idx
                    else:
                        waiting_tr_cmd['priority']=host_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, host_idx)
                        self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                        self.add_transfer_into_queue(waiting_tr_cmd, host_idx+1, 'combine_with_before')
                        return host_idx

                elif host_tr_cmd['dest'] == waiting_tr_cmd['source']:
                    if waiting_tr_cmd['link'] or ('BUF' in host_tr_cmd['dest'] and waiting_tr_cmd['primary']): #avoid Dest Duplicatecmd, chocp 2022/4/28 ????
                        continue #fix for GB and duplicate source
                    if host_tr_cmd['sourceType'] == 'FromVehicle':
                        if last_priority_101_idx >= 0:
                            waiting_tr_cmd['priority']=host_tr_cmd['priority']
                            self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                            self.add_transfer_into_queue_directly(waiting_tr_cmd, idx)
                            self.add_transfer_into_queue(host_tr_cmd, idx+1 , 'combine_with_before') 
                        #if host from MR to EqPort, set priority high
                        #remove_idx_from_queue
                        #add waiting_tr_cmd to first
                        else:
                            waiting_tr_cmd['priority']=host_tr_cmd['priority']
                            self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                            self.add_transfer_into_queue_directly(waiting_tr_cmd, 0)
                            self.add_transfer_into_queue(host_tr_cmd, 1, 'combine_with_before') 
                        return idx
                    else:
                        if host_idx < 0:
                            host_tr_cmd['original_priority']= host_tr_cmd['priority']
                            host_tr_cmd['priority']=waiting_tr_cmd['priority']
                            self.add_transfer_into_queue(host_tr_cmd, idx+1, 'combine_with_before') #host_tr_cmd is load cmd
                            host_idx=idx
                            return host_idx
                        else:
                            waiting_tr_cmd['priority']=host_tr_cmd['priority']
                            self.add_transfer_into_queue(host_tr_cmd, host_idx)
                            self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                            self.add_transfer_into_queue(waiting_tr_cmd, host_idx, 'combine_with_next')
                            return host_idx
        if host_tr_cmd['sourceType'] == 'FromVehicle':
            if last_priority_101_idx >= 0:
                host_idx=last_priority_101_idx+1
                self.add_transfer_into_queue(host_tr_cmd, host_idx)
            else:
                self.add_transfer_into_queue(host_tr_cmd, 0)
        else:
            self.add_transfer_into_queue(host_tr_cmd, host_idx) #9/9
        return host_idx

    def add_transfer_into_queue_with_check_common(self, host_tr_cmd): # can sort by recv time when same priority? 
        host_idx=-1
        waiting_idx=0
        last_same_idx=-1 #for oven
        last_same_priority=0
        if 'original_priority' not in host_tr_cmd:
            host_tr_cmd['original_priority']=host_tr_cmd['priority']
        for idx, waiting_tr_cmd in enumerate(self.queue):
            #test if there is same equipment transfer cmd
            if global_variables.TSCSettings.get('CommandDispatch', {}).get('SortingCondition','no') == 'yes':
                if global_variables.TSCSettings.get('CommandDispatch', {}).get('SortingMethod') == 'ByEquipmentID':
                    SpaceLP=global_variables.RackPortFormat[global_variables.RackNaming-1][4]
                    if SpaceLP:
                        res=re.match(SpaceLP, host_tr_cmd['source'])
                        if res and (res.group(1) in waiting_tr_cmd['source']) or (res.group(1) in waiting_tr_cmd['dest']):
                            last_same_idx=idx
                            last_same_priority=waiting_tr_cmd['priority']

                        res=re.match(SpaceLP, host_tr_cmd['dest'])
                        if res and (res.group(1) in waiting_tr_cmd['source']) or (res.group(1) in waiting_tr_cmd['dest']):
                            last_same_idx=idx
                            last_same_priority=waiting_tr_cmd['priority']
                elif global_variables.TSCSettings.get('CommandDispatch', {}).get('SortingMethod') == 'ByLotID':
                    if host_tr_cmd['TransferInfoList'][0].get('LotID', '') and waiting_tr_cmd['TransferInfoList'][0].get('LotID', ''):
                        if host_tr_cmd['TransferInfoList'][0].get('LotID') == waiting_tr_cmd['TransferInfoList'][0].get('LotID'):
                            last_same_idx=idx
                            last_same_priority=waiting_tr_cmd['priority']
                        

            if host_tr_cmd['priority']>waiting_tr_cmd['priority'] and host_idx < 0: #fifo
                #print('1 head insert', idx)
                # self.add_transfer_into_queue(host_tr_cmd, idx)
                host_idx=idx

            if not host_tr_cmd['replace'] and not waiting_tr_cmd['replace']: #try schedule to swap transfer
                res=-1
                if host_tr_cmd['source'] == waiting_tr_cmd['dest']:
                    #print('2 head insert', idx)
                    if not waiting_tr_cmd['primary']: #avoid Dest Duplicatecmd, chocp 2022/4/28
                        #break
                        continue #fix for GB and duplicate dest

                    if host_idx < 0:
                        host_tr_cmd['original_priority']= host_tr_cmd['priority']
                        host_tr_cmd['priority']=waiting_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, idx, 'combine_with_next') #host_tr_cmd is unload cmd
                        host_idx=idx
                        return host_idx
                    else:
                        waiting_tr_cmd['priority']=host_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, host_idx)
                        self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                        self.add_transfer_into_queue(waiting_tr_cmd, host_idx+1, 'combine_with_before')
                        return host_idx

                elif host_tr_cmd['dest'] == waiting_tr_cmd['source']:
                    #print('3 Trail insert', idx+1)
                    if waiting_tr_cmd['link']: #avoid Dest Duplicatecmd, chocp 2022/4/28 ????
                        #break #????
                        continue #fix for GB and duplicate source

                    if host_idx < 0:
                        host_tr_cmd['original_priority']= host_tr_cmd['priority']
                        host_tr_cmd['priority']=waiting_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, idx+1, 'combine_with_before') #host_tr_cmd is load cmd
                        host_idx=idx
                        return host_idx
                    else:
                        waiting_tr_cmd['priority']=host_tr_cmd['priority']
                        self.add_transfer_into_queue(host_tr_cmd, host_idx)
                        self.remove_transfer_from_queue_directly(waiting_tr_cmd)
                        self.add_transfer_into_queue(waiting_tr_cmd, host_idx, 'combine_with_next')
                        return host_idx

        #print('4 Trail append', len(self.queue))
        #bundle same equipmentID bundle together
        if last_same_idx>=0:
            host_tr_cmd['priority']=last_same_priority
            self.add_transfer_into_queue(host_tr_cmd, last_same_idx+1)
        else:
            self.add_transfer_into_queue(host_tr_cmd, host_idx) #9/9
        return host_idx

    def remove_transfer_from_queue_directly(self, host_tr_cmd): #8.25.5
        self.last_add_time=time.time()
        self.my_lock.acquire()

        try:
            self.queue.remove(host_tr_cmd)
            if host_tr_cmd.get('replace', 0):
                # self.single_transfer_total-=2
                self.replace_transfer_total-=1
            else:
                self.single_transfer_total-=1

            del self.transfer_list[host_tr_cmd['uuid']]

            self.my_lock.release()
        except:
            self.my_lock.release()

    def remove_waiting_transfer_by_idx(self, host_tr_cmd, idx, remove_directly=False):
        self.my_lock.acquire()
        try:
            if remove_directly:
                self.queue.remove(host_tr_cmd)
            else:
                self.queue.pop(idx)
            if host_tr_cmd.get('replace', 0):
                # self.single_transfer_total-=2
                self.replace_transfer_total-=1
            else:
                self.single_transfer_total-=1
                if host_tr_cmd['uuid'] in self.linked_list:
                    self.linked_list.remove(host_tr_cmd['uuid'])
                    
            idx_uuid_map={i[1]['uuid']: k for k, v in self.tr_point.items() for i in v} #Yuri 2024/11/07 del tr_point
            if host_tr_cmd['uuid'] in idx_uuid_map:
                k=idx_uuid_map[host_tr_cmd['uuid']]
                if len(self.tr_point[k]) > 1:
                    self.tr_point[k]=[i for i in self.tr_point[k] if not (host_tr_cmd['uuid'] == i[1]['uuid'])]
                else:
                    del self.tr_point[k]

            del self.transfer_list[host_tr_cmd['uuid']]

            self.my_lock.release()
        except:
            msg=traceback.format_exc()
            self.logger.info('Handling queue:{} in remove_waiting_transfer_by_idx() with a exception:\n {}'.format(self.queueID, msg))
            self.my_lock.release()

        output('TransferWaitQueueRemove', {
                    'CommandID':host_tr_cmd["uuid"]
                    }, True)

        tools.reset_indicate_slot(host_tr_cmd.get('source')) #chocp add 2021/10/23
        tools.reset_book_slot(host_tr_cmd.get('dest')) #chocp add 2021/10/23
        tools.reset_book_slot(host_tr_cmd.get('back')) #chocp add 2021/10/23

        # print('linked_list', self.linked_list)

        print('remove_waiting_transfer_list', self.queueID, self.single_transfer_total, self.replace_transfer_total)
        #self.logger.debug('{} {} '.format('remove_waiting_transfer_list', self.single_transfer_total))


    def remove_waiting_transfer_by_commandID(self, host_command_id, cause='by alarm', sub_code='0'):
        for i, host_tr_cmd in enumerate(self.queue):
            if host_tr_cmd['uuid'] == host_command_id:
                #chocp add 2021/12/9
                #gen a alarm before cancel
                alarms.CommandCanceledWarning(cause, host_command_id, sub_code, handler=self.secsgem_e82_h) #chocp add 2022

                TransferCompleteInfo=[]
                for TransferInfo in host_tr_cmd['TransferInfoList']:
                    TransferCompleteInfo.append({'TransferInfo': TransferInfo, 'CarrierLoc':''})

                #output('TransferCompleted', {'CommandID':host_command_id,
                #        'VehicleID':'',
                #        'DestType':host_tr_cmd.get('dest_type', 'other'),
                #        'Travel':host_tr_cmd.get('travel', 0),
                #        'ResultCode':40001,
                #        'TransferCompleteInfo':TransferCompleteInfo,
                #        'Message':'Transfer command in waiting queue be canceled {}'.format(cause)}, True)

                #output('TransferCancelCompleted', {'CommandID':host_command_id}) #chocp add 2022/3/11

                #fix for v8.18H
                link_tr_cmd=host_tr_cmd.get('link')
                if link_tr_cmd:
                    link_tr_cmd['primary']=1

                self.remove_waiting_transfer_by_idx(host_tr_cmd, i)

                # try:
                #     EqMgr.getInstance().trigger(host_tr_cmd['source'], 'alarm_set', {'CommandID':host_command_id, 'Message':'Transfer command in waiting queue be canceled {}'.format(cause)})
                # except:
                #     pass

                # try:
                #     EqMgr.getInstance().trigger(host_tr_cmd['dest'], 'alarm_set', {'CommandID':host_command_id, 'Message':'Transfer command in waiting queue be canceled {}'.format(cause)})
                # except:
                #     pass

                if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes':
                    if '-UNLOAD' not in host_command_id:
                        EqMgr.getInstance().orderMgr.update_work_status(host_command_id, 'FAIL', 'Transfer command in waiting queue be canceled') #cancel cmd by man
                        

                self.secsgem_e82_h.rm_transfer_cmd(host_command_id) #fix cancel link cmd 2022/6/28

                return True, host_tr_cmd #fix cancel link cmd 2022/6/28
        else:
            return False, None  #fix cancel link cmd 2022/6/28


    def dispatch_transfer(self, h_vehicle):
        res=False
        if h_vehicle.token.acquire(False):
            try:
                #if h_vehicle.AgvState == 'Unassigned':
                if h_vehicle.AgvState in ['Unassigned','Waiting'] and h_vehicle.AgvSubState == 'InWaitCmdStatus':
                    h_vehicle.AgvSubState='InRecvCmd'
                    if self.dispatch_transfer_with_token(h_vehicle):
                        res=True
                        self.stop_vehicle=False
                        h_vehicle.AgvSubState='InWaitExeCmdStatus'
                    else:
                        h_vehicle.AgvSubState='InWaitCmdStatus' #chocp fix 1/18

                h_vehicle.token.release()
            except:
                h_vehicle.AgvSubState='InWaitCmdStatus' #chocp fix 1/18, 2022/5/10
                h_vehicle.token.release()
                msg=traceback.format_exc()
                self.logger.info('Handling queue:{} in dispatch_transfer with a exception:\n {}'.format(self.queueID, msg))
                #traceback.print_exc()
        else:
            print('dispatch_transfer fail', h_vehicle.AgvState, h_vehicle.AgvSubState)
            self.logger.debug('{} {} {} {}'.format('dispatch_transfer fail vehicle.AgvState=', h_vehicle.AgvState, 'vehicle.AgvSubState', h_vehicle.AgvSubState))

        return res


    def dispatch_transfer_with_token(self, h_vehicle): #new for StockOut
        primary_cmds_total=0
        single_cmds_total=0
        buf_reserved=False
        buf_assigned=[]
        with_buf_contrain_batch=False
        host_cmd_eqs=[]
        zone=''
        actual_dispatch_cmd_list=[]   
        delay_send_to_vehicle_equipmentID_count=0
        block_send_equipmentID=''

        buf_available_num, buf_available_list=h_vehicle.buf_available()

        buf_available_list_sorted=sorted(buf_available_list, key=lambda bufID: 0 if bufID in h_vehicle.vehicle_onTopBufs else 1) #v8.21K
        
        if global_variables.RackNaming==40 and self.activeHandlingType:
            priority = ["Out", "In", "Undefine"] if self.activeHandlingType == "In" else ["In", "Out", "Undefine"]
            self.queue.sort(key=lambda cmd: priority.index(cmd.get("handlingType", "Undefine")))
             
        h_vehicle.tr_cmds=[] #chocp 2021/11/7 clear tr_cmds in vehicle
        h_vehicle.one_buf_for_swap=False #8.27.8 if swap from MR need one buf

        host_tr_cmd=self.queue[0]
        check = self.queue[0].get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort'] or self.queue[0].get('link') and self.queue[0].get('link', {}).get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']
        #if global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' and (self.queue[0].get('sourceType', '') == 'StockOut' or self.queue[0].get('sourceType', '') == 'ErackOut'): #K25 
        if (global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' or global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes') and not host_tr_cmd.get('preTransfer') and check: #K25 

            print("#########################################################")
            print('do preDispatch StouckOut or ErackOut and preTransfer:{}', host_tr_cmd.get('preTransfer'))
            print("#########################################################")

            schedule_algo=''
            if host_tr_cmd.get('preTransfer'):
                schedule_algo=self.schedule_algo
            if host_tr_cmd.get('link'):
                res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd['link'], buf_available_list_sorted, False, schedule_algo)
            else:
                schedule_algo='by_fix_order'

            res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, False, schedule_algo)
            if host_tr_cmd.get('link'):
                res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd['link'], buf_available_list_sorted, False, schedule_algo)
            if res:
                if buf_assigned: #2022/7/13 bufseq 4321
                    with_buf_contrain_batch=True

                '''if host_tr_cmd.get('preTransfer'):
                    self.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, 0) #? need check
                else:
                    self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle) #one pre-dispatch cmd'''
                self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned) #one pre-dispatch cmd

                h_vehicle.doPreDispatchCmd=True
                primary_cmds_total+=primary_cmd_count
                single_cmds_total+=single_cmd_count
        elif global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes' and not host_tr_cmd.get('preTransfer') and self.queue[0].get('stage') and (self.queue[0].get('priority', 0) == 100): #K25 
            print("#########################################################")
            print('do preDispatch for stage cmd:{}'.format(host_tr_cmd['uuid']), host_tr_cmd.get('preTransfer'))
            print("#########################################################")

            schedule_algo=''
            if host_tr_cmd.get('preTransfer'):
                schedule_algo=self.schedule_algo
            else:
                schedule_algo='by_fix_order'

            res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, False, schedule_algo)
            if res:
                if buf_assigned: #2022/7/13 bufseq 4321
                    with_buf_contrain_batch=True

                '''if host_tr_cmd.get('preTransfer'):
                    self.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, 0) #? need check
                else:
                    self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle) #one pre-dispatch cmd'''
                self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned) #one pre-dispatch cmd

                h_vehicle.doPreDispatchCmd=True
                primary_cmds_total+=primary_cmd_count
                single_cmds_total+=single_cmd_count
            """elif global_variables.TSCSettings.get('Other', {}).get('StageEnable','no') == 'yes' and not host_tr_cmd.get('preTransfer') and self.queue[0].get('link') and self.queue[0]['link'].get('stage') and (self.queue[0].get('priority', 0) == 100): #K25 
                host_tr_cmd=self.queue[0]['link']
                print("#########################################################")
                print('do preDispatch for stage cmd:{}'.format(host_tr_cmd['uuid']), host_tr_cmd.get('preTransfer'))
                print("#########################################################")

                schedule_algo=''
                if host_tr_cmd.get('preTransfer'):
                    schedule_algo=self.schedule_algo
                else:
                    schedule_algo='by_fix_order'

                res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, False, schedule_algo)
                if res:
                    if buf_assigned: #2022/7/13 bufseq 4321
                        with_buf_contrain_batch=True

                    '''if host_tr_cmd.get('preTransfer'):
                        self.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, 0) #? need check
                    else:
                        self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle) #one pre-dispatch cmd'''
                    self.preDispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned) #one pre-dispatch cmd

                    h_vehicle.doPreDispatchCmd=True
                    primary_cmds_total+=primary_cmd_count
                    single_cmds_total+=single_cmd_count"""
        else:
            #MRxxx waiting queue
            vehicle_wq=TransferWaitQueue.getInstance(h_vehicle.id)

            res=False
            high_priority=False
            while True and vehicle_wq: #maybe Vehicle Buf to Dest or Source to Vehicle Buf
                buf_specified=[]
                HostSpecify_res=False
                try:
                    host_tr_cmd=vehicle_wq.queue[0]
                    print('clear cmd in vehicle queue', host_tr_cmd)
                    HostSpecifyMR=host_tr_cmd.get('HostSpecifyMR','')
                    priority=host_tr_cmd.get('priority','')
                    if high_priority and priority != 101:
                        break
                    if self.queueID != h_vehicle.id and self.queue[0]['priority'] == 101 and priority != 101:
                        break
                    if HostSpecifyMR:
                        res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, buf_reserved, self.schedule_algo)
                        if res:
                            if buf_assigned: #2022/7/13 bufseq 4321
                                with_buf_contrain_batch=True
                            if priority == 101:
                                high_priority=True
                            vehicle_wq.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, unload_buf_assigned)
                            HostSpecify_res=True
                        else:
                            break
                            
                    else:
                        if host_tr_cmd['link']:
                            zone=host_tr_cmd['zoneID']
                            if host_tr_cmd['link'].get('sourceType','')== 'FromVehicle':
                                h_vehicle.one_buf_for_swap=True
                            if h_vehicle.check_carrier_type == 'yes':
                                res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, buf_reserved, self.schedule_algo)
                                if res:
                                    if buf_assigned: #2022/7/13 bufseq 4321
                                        with_buf_contrain_batch=True
                                    if priority == 101:
                                        high_priority=True
                                    vehicle_wq.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, unload_buf_assigned)
                                    HostSpecify_res=True
                                else:
                                    break
                            else:
                                # if 'MR' not in host_tr_cmd['source']: #GF 5:
                                if host_tr_cmd['source'][:-5] not in Vehicle.h.vehicles and host_tr_cmd['dest'][:-5] not in Vehicle.h.vehicles: #GF 5: 
                                    break

                                r=re.match(r'(.+)(BUF\d+)', host_tr_cmd['source'])
                                if not r:
                                    r=re.match(r'(.+)(BUF\d+)', host_tr_cmd['dest'])
                                    if not r:
                                        break
                                bufID=r.group(2)
                                if bufID!='BUF00' and not host_tr_cmd['replace']:
                                    buf_specified.append(bufID)

                except: #like no cmd
                    break
                time.sleep(1)

                # add book real erack buffer here

                #vehicle_wq.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, []) # bug free by Jason, 2022/7/13 #one dispatch cmd
                if not HostSpecify_res:
                    if priority == 101:
                        high_priority=True
                    vehicle_wq.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_specified) # GF
                    res=True

            if res:
                #flush all vehicle quque link
                for queue in vehicle_wq.relation_links: #for FST, clear vehicle waiting queue relationship queue
                    queue.preferVehicle=''

                vehicle_wq.relation_links=[]
                h_vehicle.doPreDispatchCmd=False

            #specified waiting queue
            i=0
            j=0
            new_stockin_port='' #for K25, only for single transfer

            first_tr_cmd_equipmentID='' #kelvinng 20250401
            same_equipmentID_count=0
            same_AMR_MGZ_equipmentID_dict={}
            
            if global_variables.RackNaming == 40 and self.queue:
                dispatch_cmd_num = 0
                dispatch_cmd_list = []
                dispatch_cmd_lots = []

                first_handling_type = self.queue[0].get('handlingType', '')
                
                if first_handling_type == 'In' and self.can_dispatch_lot_in:
                    allowed_type = 'In'
                elif first_handling_type == 'Out' and self.can_dispatch_lot_out:
                    allowed_type = 'Out'
                elif first_handling_type == 'In' and not self.can_dispatch_lot_in and self.can_dispatch_lot_out:
                    allowed_type = 'Out'
                elif first_handling_type == 'Out' and not self.can_dispatch_lot_out and self.can_dispatch_lot_in:
                    allowed_type = 'In'
                else:
                    allowed_type = None  

                if allowed_type:
                    for host_tr_cmd in self.queue:
                        lot_id = host_tr_cmd['TransferInfoList'][0].get('LotID', '')
                        handling_type = host_tr_cmd.get('handlingType', '')
                        
                        if (
                            lot_id and 
                            handling_type == allowed_type and 
                            handling_type in self.lot_list and 
                            lot_id in self.lot_list[handling_type]
                        ):
                            lot_info = self.lot_list[handling_type][lot_id]
                            if (
                                lot_info['dispatch'] and 
                                (len(buf_available_list_sorted) - dispatch_cmd_num) >= lot_info['QUANTITY'] and 
                                lot_id not in dispatch_cmd_lots
                            ):
                                dispatch_cmd_num += lot_info['QUANTITY']
                                dispatch_cmd_list.extend(lot_info['CommandID'])
                                dispatch_cmd_lots.append(lot_id)
                print(self.lot_list)
                print(dispatch_cmd_list)
                print(dispatch_cmd_lots)
                print(dispatch_cmd_num)
                
            while True:
                try:
                    
                    host_tr_cmd=self.queue[i]
                    tr_wq_lib_logger.debug("get uuid:{},source:{},dest:{},carrierID:{}".format(host_tr_cmd.get("uuid",""),host_tr_cmd.get("source",""),host_tr_cmd.get("dest",""),host_tr_cmd.get("carrierID","")))
                    priority=host_tr_cmd.get('priority','')
                    LotID=host_tr_cmd['TransferInfoList'][0].get('LotID','')
                    handlingType=host_tr_cmd.get('handlingType','')
                    #print(LotID,host_tr_cmd['uuid'],dispatch_cmd_list,handlingType)
                    if  global_variables.RackNaming == 40 and LotID and host_tr_cmd['uuid'] not in dispatch_cmd_list and handlingType and handlingType in ['In', 'Out'] :
                        i+=1
                        continue
                    
                    if high_priority and priority != 101:
                        break
                    #chocp 2024/8/21 for shift
                    #try to insert SHIFT transfer cmd
                    # if host_tr_cmd.get('shiftTransfer'):
                    #     self.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, i)
                    #     continue

                    #if host_tr_cmd['equipmentID'] and host_tr_cmd['equipmentID'] not in host_cmd_eqs:  #2022/12/09
                    if host_tr_cmd.get('equipmentID') and host_tr_cmd['equipmentID'] not in host_cmd_eqs:  #2023/8/23 chocp
                        if len(host_cmd_eqs) < self.merge_max_eqps:
                            host_cmd_eqs.append(host_tr_cmd['equipmentID'])
                        elif i < len(self.queue)+j:
                            i+=1
                            continue
                        else:
                            break

                except:
                    print('No transfer cmd in queue {}'.format(self.queueID))
                    break

                if host_tr_cmd.get('SkipDispatch'):
                    i+=1
                    j+=1
                    del host_tr_cmd['SkipDispatch']
                    continue

                dest_port=host_tr_cmd['dest']
                res, rack_id, port_no=tools.rackport_format_parse(dest_port)
                # print('Find new dest port for undecided rack port.')
                # print(res, rack_id, port_no)
                if Erack.h.port_areas.get(dest_port):
                    res, rack_id, port_no=True, dest_port, 0
                if res and port_no == 0:
                    res, new_dest_port=tools.new_auto_assign_dest_port(rack_id, host_tr_cmd.get('CarrierType', ''))
                    if res:
                        host_tr_cmd['dest']=new_dest_port
                        host_tr_cmd['TransferInfoList'][0]['DestPort']=new_dest_port
                    else:
                        i+=1
                        j+=1
                        if host_tr_cmd['link']:
                            host_tr_cmd['link']['SkipDispatch']=True
                        continue
                back_port=host_tr_cmd['back']
                if host_tr_cmd['back']:
                    back_port=host_tr_cmd['back']
                    res, rack_id, port_no=tools.rackport_format_parse(back_port)
                    if Erack.h.port_areas.get(back_port):
                        res, rack_id, port_no=True, back_port, 0
                    # print('Find new back port for undecided rack port.')
                    # print(res, rack_id, port_no)
                    if res and port_no == 0:
                        res, new_dest_port=tools.new_auto_assign_dest_port(rack_id, host_tr_cmd.get('CarrierType', ''))
                        if res:
                            host_tr_cmd['back']=new_dest_port
                            host_tr_cmd['TransferInfoList'][1]['DestPort']=new_dest_port
                        else:
                            i+=1
                            j+=1
                            continue

                # tr_wq_lib_logger.debug("buf_available_list_sorted:{}".format(buf_available_list_sorted))
                bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections', '')
                # tr_wq_lib_logger.debug("bufferAllowedDirection:{}".format(bufferAllowedDirections))
                # tr_wq_lib_logger.debug("h_vehicle.bufferDirection:{}".format(h_vehicle.bufferDirection))
                if bufferAllowedDirections != "All":
                    matched_buf = [buf for buf in buf_available_list_sorted if buf in h_vehicle.bufferDirection[bufferAllowedDirections]]
                else:
                    matched_buf = [buf for buf in buf_available_list_sorted]

                if global_variables.RackNaming in [46]:
                    #check_zoneID=""
                    check_equipmentID=""
                    count_other_sameEQ_command=0
                    source_is_buf=False
                    equipmentID_has_erack_command=False
                    
                    h_workstation_dest=EqMgr.getInstance().workstations.get(host_tr_cmd['dest'])
                    if h_workstation_dest and  h_workstation_dest.workstation_type != "ErackPort":
                        
                        check_equipmentID=getattr(h_workstation_dest, 'equipmentID', '')
                        
                        tr_wq_lib_logger.debug("check_equipmentID:{}".format(check_equipmentID))
                    else:
                        h_workstation_source=EqMgr.getInstance().workstations.get(host_tr_cmd['source'])
                        if h_workstation_source:
                            
                            check_equipmentID=getattr(h_workstation_source, 'equipmentID', '')
                           
                            tr_wq_lib_logger.debug("check_equipmentID:{}".format(check_equipmentID))
                
                    if check_equipmentID != "":
                        
                        other_same_equipmentID=''

                        if block_send_equipmentID != check_equipmentID:
                        
                            for queue_index in self.queue:
                                
                                if host_tr_cmd.get("uuid","") != queue_index.get("uuid",""):
                                    
                                    check_dest=queue_index.get("dest","")
                                    check_source=queue_index.get("source","")
                                    tr_wq_lib_logger.info("check_dest:{}".format(check_dest))
                                    tr_wq_lib_logger.info("check_source:{}".format(check_source))

                                    h_workstation_check_dest=EqMgr.getInstance().workstations.get(check_dest)
                                    if h_workstation_check_dest and  h_workstation_check_dest.workstation_type != "ErackPort":
                                        
                                        other_same_equipmentID=getattr(h_workstation_check_dest, 'equipmentID', '')
                                        
                                        tr_wq_lib_logger.debug("other_same_equipmentID:{}".format(other_same_equipmentID))
                                    else:
                                        equipmentID_has_erack_command=True
                                        h_workstation_check_source=EqMgr.getInstance().workstations.get(check_source)
                                        if h_workstation_check_source:
                                            
                                            other_same_equipmentID=getattr(h_workstation_check_source, 'equipmentID', '')
                                        
                                            tr_wq_lib_logger.debug("other_same_equipmentID:{}".format(other_same_equipmentID))
                                    
                                    if queue_index.get("shiftTransfer",False) == False:
                                    
                                        if other_same_equipmentID == check_equipmentID:
                                            
                                            count_other_sameEQ_command += 1
                        else:
                            tr_wq_lib_logger.warning("do continue because block_send_equipmentID")
                            i+=1
                            j+=1
                            
                            continue


                    if count_other_sameEQ_command > 0:
                        tr_wq_lib_logger.debug("other count_other_sameEQ_command:{}".format(count_other_sameEQ_command))
                        if host_tr_cmd.get("shiftTransfer",False) == False:
                            count_other_sameEQ_command += 1
                        tr_wq_lib_logger.debug("with self count_other_sameEQ_command:{}".format(count_other_sameEQ_command))
                        tr_wq_lib_logger.debug("buf_available_list_sorted:{}".format(buf_available_list_sorted))
                        if len(buf_available_list_sorted) < count_other_sameEQ_command:
                            tr_wq_lib_logger.warning("do continue because no more buf")
                            i+=1
                            j+=1
                            block_send_equipmentID = check_equipmentID
                            continue
                            
                            # if delay_send_to_vehicle_equipmentID_count <5:
                            #     delay_send_to_vehicle_equipmentID_count+=1
                            #     tr_wq_lib_logger.warning("do continue")
                            #     i+=1
                            #     j+=1
                            #     continue
                            # else:

                            #     host_tr_cmd['dest']=dest_port
                            #     host_tr_cmd['TransferInfoList'][0]['DestPort']=dest_port
                            #     if back_port:
                            #         host_tr_cmd['back']=back_port
                            #         host_tr_cmd['TransferInfoList'][0]['DestPort']=back_port
                            #     delay_send_to_vehicle_equipmentID_count=0
                            #     break
                        else:
                            delay_send_to_vehicle_equipmentID_count=0

                #tr_wq_lib_logger.warning("h_vehicle.tr_cmds:{}".format(h_vehicle.tr_cmds))

                check_h_vehicle=h_vehicle.tr_cmds
                #cbaamr01BUF02
                for check_h_vehicle_index in check_h_vehicle:
                    if "BUF" in check_h_vehicle_index.get("source",""):
                        source_is_buf=True
                        
                        break

                if source_is_buf:
                    tr_wq_lib_logger.warning("source_is_buf:{}".format(source_is_buf))
                    break
                    # if equipmentID_has_erack_command:
                    #     i+=1
                    #     j+=1
                    #     continue

                                        

               

                
               
                res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, buf_reserved, self.schedule_algo)
                tr_wq_lib_logger.debug("out buf_available_list_sorted:{}".format(buf_available_list_sorted))
                print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
                print(res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned, self.merge_max_cmds)
                print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
                print(host_tr_cmd)
                
                if res and (single_cmds_total+single_cmd_count)<=self.merge_max_cmds:
                    if buf_assigned: #2022/7/13 bufseq 4321
                        with_buf_contrain_batch=True

                    #change dest for K25, only for sinagle transfer
                    if global_variables.RackNaming == 18: #check and change destPort, only support single cmd
                        dest=host_tr_cmd['dest']
                        h_workstation=EqMgr.getInstance().workstations.get(dest)
                        self.logger.info("dest1:{}".format(dest))
                        self.logger.info("workstation_typr:{}".format(h_workstation.workstation_type))
                        if h_workstation and h_workstation.workstation_type in ['StockIn', 'StockIn&StockOut', 'LifterPort']:
                            if new_stockin_port:
                                if dest!=new_stockin_port:
                                    E82.report_event(self.secsgem_e82_h, E82.DestPortChanged, 
                                        {'CommandID':host_tr_cmd['uuid'],
                                        'CarrierID':host_tr_cmd['carrierID'], 
                                        'DestPort':host_tr_cmd['dest'], 
                                        'TransferPort':new_stockin_port})

                                    self.logger.info('{}: commandID:{}, carrierID:{}, original dest:{}, new dest:{}'.format('DestPortChanged', host_tr_cmd['uuid'], host_tr_cmd['carrierID'], host_tr_cmd['dest'], new_stockin_port))
                                    host_tr_cmd['dest']=new_stockin_port
                            else:
                                new_stockin_port=dest
                                SaveStockerInDestPortByVehicleId.save_dest_port[h_vehicle.id]=new_stockin_port#kelvin

                    if host_tr_cmd.get('SkipDispatch'):
                        del host_tr_cmd['SkipDispatch']
                    tools.book_slot(host_tr_cmd['dest'], h_vehicle.id, host_tr_cmd['source'])
                    tools.book_slot(host_tr_cmd['back'], h_vehicle.id, host_tr_cmd['dest'])
                    if  priority == 101:
                        high_priority=True
                    if global_variables.RackNaming == 40:
                        actual_dispatch_cmd_list.append(host_tr_cmd['uuid'])
                        self.activeHandlingType=host_tr_cmd.get('handlingType','')
                    self.dispatch_tr_cmd_to_vehicle(host_tr_cmd, h_vehicle, buf_assigned, unload_buf_assigned, i)
                    h_vehicle.doPreDispatchCmd=False
                    primary_cmds_total+=primary_cmd_count
                    single_cmds_total+=single_cmd_count
                else:
                    host_tr_cmd['dest']=dest_port
                    host_tr_cmd['TransferInfoList'][0]['DestPort']=dest_port
                    if back_port:
                        host_tr_cmd['back']=back_port
                        host_tr_cmd['TransferInfoList'][0]['DestPort']=back_port
                    break

        if len(h_vehicle.tr_cmds)>0:
            h_vehicle.use_schedule_algo=self.schedule_algo
            h_vehicle.ControlPhase='GoTransfer'
            vehicle_wq=TransferWaitQueue.getInstance(h_vehicle.id)
            if self == vehicle_wq and zone:
                h_vehicle.wq=TransferWaitQueue.getInstance(zone)
            else:
                h_vehicle.wq=self #8.21-4
            h_vehicle.waiting_run=True

            if with_buf_contrain_batch: #2022/7/13 buf seq 4321
                h_vehicle.with_buf_contrain_batch=True
            else: #2022/7/13 buf seq 1234
                h_vehicle.with_buf_contrain_batch=False
                
            if global_variables.RackNaming == 40 and actual_dispatch_cmd_list:
                to_remove = []
                for uuid in actual_dispatch_cmd_list:
                    for handling_type in ['In', 'Out']:
                        if handling_type in self.lot_list:
                            for lot_id, lot_info in self.lot_list[handling_type].items():
                                if uuid in lot_info['CommandID']:
                                    lot_info['CommandID'].remove(uuid)

                                if len(lot_info['CommandID']) < lot_info['QUANTITY']:
                                    lot_info['dispatch'] = False

                                if len(lot_info['CommandID']) == 0 and (handling_type, lot_id) not in to_remove:
                                    to_remove.append((handling_type, lot_id))

                for handling_type, lot_id in to_remove:
                    del self.lot_list[handling_type][lot_id]

            print('<<dispatch total primary cmd count:{}, single cmd count:{} into {} executing queue, buf_reserved:{}>>'.format(primary_cmds_total, single_cmds_total, h_vehicle.id, buf_reserved))
            print('h_vehicle.tr_cmds len={}, with_buf_contrain_batch={}'.format(len(h_vehicle.tr_cmds), with_buf_contrain_batch))
            #self.logger.debug('{} {} {} {}'.format('vehicle_cmds len=', len(h_vehicle.tr_cmds), 'with_buf_contrain_batch=', with_buf_contrain_batch))

        return h_vehicle.waiting_run #chocp add


    #for StockOut
    def preDispatch_tr_cmd_to_vehicle(self, host_tr_cmd, h_vehicle, buf_assigned):
        do_pre_tr_cmd=host_tr_cmd
        idx=0
        if host_tr_cmd.get('link'):
            do_pre_tr_cmd = host_tr_cmd['link']
            idx=1
        self.remove_waiting_transfer_by_idx(do_pre_tr_cmd, idx)

        self.preferVehicle=h_vehicle.id #add executing queue first, add waiting queue later
        tmp_source=do_pre_tr_cmd['source']
        tmp_sourceType=do_pre_tr_cmd['sourceType']
        tmp_priority=do_pre_tr_cmd['priority'] if global_variables.RackNaming == 8 else 100  #Chi 2022/12/29

        do_pre_tr_cmd['source']='{}BUF00'.format(h_vehicle.id)
        do_pre_tr_cmd['TransferInfoList'][0]['SourcePort']='{}BUF00'.format(h_vehicle.id)
        do_pre_tr_cmd['sourceType']='FromVehicle'
        do_pre_tr_cmd['priority']=int(do_pre_tr_cmd['CommandInfo']['Priority'])
        do_pre_tr_cmd['original_priority']=int(do_pre_tr_cmd['CommandInfo']['Priority'])


        vehicle_wq=TransferWaitQueue.getInstance(h_vehicle.id)

        if idx == 1:
            self.remove_transfer_from_queue_directly(host_tr_cmd)
            vehicle_wq.add_transfer_into_queue_directly(host_tr_cmd)
            print('add {} to zone {}'.format(host_tr_cmd['uuid'], h_vehicle.id))
        else:
            #search waiting unload transfer in all queue and change zone
            for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
                for waiting_tr_cmd in zone_wq.queue: #have lock or race condition problem???
                    if (waiting_tr_cmd['source'] == do_pre_tr_cmd['dest'] and not do_pre_tr_cmd['replace'] and not waiting_tr_cmd.get('link')) or waiting_tr_cmd.get('link') == do_pre_tr_cmd:
                        zone_wq.remove_transfer_from_queue_directly(waiting_tr_cmd)
                        vehicle_wq.add_transfer_into_queue_directly(waiting_tr_cmd)
                        waiting_tr_cmd['link']=do_pre_tr_cmd
                        do_pre_tr_cmd['primary']=0
                        print('add {} to zone {}'.format(waiting_tr_cmd['uuid'], h_vehicle.id))
                        break
                else:
                    continue
                break
        #vehicle_wq.add_transfer_into_queue_with_check(host_tr_cmd)
        vehicle_wq.add_transfer_into_queue_directly(do_pre_tr_cmd) #2023/10/27 chocp rewrite
        output('TransferWaitQueueAdd', {
                    'Channel':do_pre_tr_cmd.get('channel', 'Internal'), #chocp 2022/6/13
                    'Idx':-1,
                    'CarrierID':do_pre_tr_cmd['carrierID'],
                    'CarrierType':do_pre_tr_cmd['TransferInfoList'][0].get('CarrierType', ''), #chocp 2022/2/9
                    # 'ZoneID':h_vehicle.id,  #chocp 9/14
                    'TransferInfoList':do_pre_tr_cmd['TransferInfoList'],
                    'ZoneID':do_pre_tr_cmd['zoneID'],  #chocp 9/14
                    'Source':do_pre_tr_cmd['source'],
                    'Dest':do_pre_tr_cmd['dest'],
                    'CommandID':do_pre_tr_cmd["uuid"],
                    'Priority':do_pre_tr_cmd["priority"],
                    'Replace':do_pre_tr_cmd['replace'],
                    'Back':do_pre_tr_cmd['back'],
                    'OperatorID':do_pre_tr_cmd.get('operatorID', '')
                    }, True)

        vehicle_wq.relation_links.append(self) #for FST, for stockout 2022/12/21 chocp fix

        tools.book_slot(do_pre_tr_cmd['dest'], h_vehicle.id, do_pre_tr_cmd['source'])   #chi 05/19
        tools.indicate_slot(do_pre_tr_cmd['source'], do_pre_tr_cmd['dest'], h_vehicle.id)

        print("###################################################")
        print('preDispatch_tr_cmd_to_vehicle:{}...'.format(h_vehicle))
        print("###################################################")

        #auto transfer
        #uuid=100*time.time()
        #%=1000000000000
        #CommandID='PRE%.12d'%uuid
        bufloc=''
        CommandID='PRE-{}'.format(do_pre_tr_cmd['uuid'])
        CommandInfo=dict(do_pre_tr_cmd['CommandInfo'])
        CommandInfo.update({'CommandID':CommandID, 'Priority':0, 'Replace':0})
        TransferInfo={'CarrierID':do_pre_tr_cmd['carrierID'], 'SourcePort':tmp_source, 'DestPort':'{}BUF00'.format(h_vehicle.id), 'CarrierType': do_pre_tr_cmd['TransferInfoList'][0].get('CarrierType', '')}
        
        if buf_assigned: #for BufConstrain
            bufloc=buf_assigned.pop()
            TransferInfo['DestPort']= h_vehicle.id+bufloc
            
        new_host_tr_cmd={
                        'stage':do_pre_tr_cmd['stage'],
                        'primary':1,
                        'received_time':time.time(),
                        'uuid':CommandInfo['CommandID'],
                        'carrierID':TransferInfo['CarrierID'],
                        'original_source':do_pre_tr_cmd['original_source'],
                        'source':TransferInfo['SourcePort'],
                        'dest':TransferInfo['DestPort'],
                        'zoneID':h_vehicle.id, #9/14
                        'priority':0,
                        'replace':0,
                        'back': '',
                        'CommandInfo':CommandInfo,
                        'TransferCompleteInfo':[],
                        'OriginalTransferCompleteInfo':[],
                        'TransferInfoList':[TransferInfo],
                        'OriginalTransferInfoList':[TransferInfo],
                        'credit':1,
                        'link':do_pre_tr_cmd,  #2022/12/09
                        'sourceType':tmp_sourceType, #chocp 2022/12/23
                        'preTransfer':True
                    }

        local_tr_cmd={
                        'uuid':new_host_tr_cmd['uuid'],
                        'carrierID':new_host_tr_cmd['carrierID'],
                        'carrierLoc':new_host_tr_cmd['source'],
                        'source':new_host_tr_cmd['source'],
                        'dest':new_host_tr_cmd['dest'],
                        'priority':tmp_priority,
                        'first':True,
                        'last':True,
                        'TransferInfo':new_host_tr_cmd['TransferInfoList'][0],
                        'OriginalTransferInfo':new_host_tr_cmd['OriginalTransferInfoList'][0],
                        'host_tr_cmd':new_host_tr_cmd
                    }
        if bufloc:
            local_tr_cmd['buf_loc']=bufloc
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
        h_vehicle.add_executing_transfer_queue(local_tr_cmd)
        tools.book_slot(local_tr_cmd['dest'], h_vehicle.id, local_tr_cmd['source'])  #book for MR, may cause delay
        tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'], h_vehicle.id)



    def dispatch_tr_cmd_to_vehicle(self, host_tr_cmd, h_vehicle, buf_constrain, unload_buf_constrain=[], idx=0):
        if host_tr_cmd.get('shiftTransfer'):
            self.remove_waiting_transfer_by_idx(host_tr_cmd, idx)
            if len(host_tr_cmd['TransferInfoList']) > 1:
                is_source_vehicle=host_tr_cmd.get('source')[:-5] in Vehicle.h.vehicles
                is_back_vehicle=host_tr_cmd.get('back') == '' or host_tr_cmd.get('back') == '*' or host_tr_cmd.get('back')[:-5] in Vehicle.h.vehicles
                if is_back_vehicle:
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-UNLOAD',
                                'carrierID':host_tr_cmd['TransferInfoList'][1].get('CarrierID', ''),
                                'carrierLoc':host_tr_cmd['dest'],
                                'source':host_tr_cmd['dest'],
                                'dest':host_tr_cmd.get('back', '*'),
                                'priority':host_tr_cmd['priority'],
                                'first':False,
                                'last':True,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][1],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][1],
                                'host_tr_cmd':host_tr_cmd
                            }
                    if unload_buf_constrain: #for BufConstrain
                        local_tr_cmd['buf_loc']=unload_buf_constrain.pop()
                    elif buf_constrain: #for BufConstrain
                        local_tr_cmd['buf_loc']=buf_constrain.pop()
                    elif 'BUF' in host_tr_cmd['back'][-5:-2]:
                        local_tr_cmd['buf_loc']=host_tr_cmd['back'][-5:]

                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)
                    tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'], h_vehicle.id)
                    tools.book_slot(local_tr_cmd['dest'], h_vehicle.id, local_tr_cmd['source']) #book for MR
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-LOAD',
                                'carrierID':host_tr_cmd['carrierID'],
                                'carrierLoc':host_tr_cmd['source'],
                                'source':host_tr_cmd['source'],
                                'dest':host_tr_cmd['dest'],
                                'priority':host_tr_cmd['priority'],
                                'first':True,
                                'last':False,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                                'host_tr_cmd':host_tr_cmd,
                                'transferType':'SHIFT'
                            }

                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)       
                elif is_source_vehicle:
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-UNLOAD',
                                'carrierID':host_tr_cmd['TransferInfoList'][1].get('CarrierID', ''),
                                'carrierLoc':host_tr_cmd['dest'],
                                'source':host_tr_cmd['dest'],
                                'dest':host_tr_cmd['back'],
                                'priority':host_tr_cmd['priority'],
                                'first':False,
                                'last':True,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][1],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][1],
                                'host_tr_cmd':host_tr_cmd,
                                'transferType':'SHIFT'
                            }
                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)
                    
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-LOAD',
                                'carrierID':host_tr_cmd['carrierID'],
                                'carrierLoc':host_tr_cmd['source'],
                                'source':host_tr_cmd['source'],
                                'dest':host_tr_cmd['dest'],
                                'priority':host_tr_cmd['priority'],
                                'first':True,
                                'last':False,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                                'host_tr_cmd':host_tr_cmd
                            }
                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '') else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '') else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)
                else:
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-UNLOAD',
                                'carrierID':host_tr_cmd['TransferInfoList'][1].get('CarrierID', ''),
                                'carrierLoc':host_tr_cmd['dest'],
                                'source':host_tr_cmd['dest'],
                                'dest':host_tr_cmd['back'],
                                'priority':host_tr_cmd['priority'],
                                'first':False,
                                'last':True,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][1],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][1],
                                'host_tr_cmd':host_tr_cmd,
                                'transferType':'SHIFT'
                            }

                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)
                    
                    local_tr_cmd={
                                'uuid':host_tr_cmd['uuid']+'-LOAD',
                                'carrierID':host_tr_cmd['carrierID'],
                                'carrierLoc':host_tr_cmd['source'],
                                'source':host_tr_cmd['source'],
                                'dest':host_tr_cmd['dest'],
                                'priority':host_tr_cmd['priority'],
                                'first':True,
                                'last':False,
                                'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                                'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                                'host_tr_cmd':host_tr_cmd,
                                'transferType':'SHIFT'
                            }

                    local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                    local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                    h_vehicle.add_executing_transfer_queue(local_tr_cmd)    
                                
            else:
                local_tr_cmd={
                            'uuid':host_tr_cmd['uuid'],
                            'carrierID':host_tr_cmd['carrierID'],
                            'carrierLoc':host_tr_cmd['source'],
                            'source':host_tr_cmd['source'],
                            'dest':host_tr_cmd['dest'],
                            'priority':host_tr_cmd['priority'],
                            'first':True,
                            'last':True,
                            'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                            'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                            'host_tr_cmd':host_tr_cmd,
                            'transferType':'SHIFT'
                        }
                
                local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
                h_vehicle.add_executing_transfer_queue(local_tr_cmd)
        
        else:
            self.remove_waiting_transfer_by_idx(host_tr_cmd, idx)

            if global_variables.RackNaming == 42:
                if host_tr_cmd.get('priority', 0) == 101:
                    if h_vehicle.bufs_status[0]['stockID'] != 'None':
                        E82.report_event(self.secsgem_e82_h,
                                    E82.TransferCompleted, {
                                    'CommandInfo':host_tr_cmd['CommandInfo'],
                                    'VehicleID':h_vehicle.id,
                                    'TransferCompleteInfo':host_tr_cmd['OriginalTransferCompleteInfo'], #9/13
                                    'TransferInfo':host_tr_cmd['OriginalTransferInfoList'][0] if host_tr_cmd['OriginalTransferInfoList'] else {},
                                    'CommandID':host_tr_cmd['CommandInfo'].get('CommandID', ''),
                                    'Priority':host_tr_cmd['CommandInfo'].get('Priority', 0),
                                    'Replace':host_tr_cmd['CommandInfo'].get('Replace', 0),
                                    'CarrierID':host_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                    'SourcePort':host_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                    'DestPort':host_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                    #'CarrierLoc':self.action_in_run['loc'],
                                    'CarrierLoc':host_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                    'ResultCode':10018 })
                        alarms.BaseCovertrayWarning(h_vehicle.id, host_tr_cmd['uuid'], host_tr_cmd['carrierID'], handler=self.secsgem_e82_h)
                        return

            if host_tr_cmd['carrierID']: #chocp 2022/12/29
                res, new_source_port=tools.re_assign_source_port(host_tr_cmd['carrierID']) #cost all lot
                if res:
                    if global_variables.TSCSettings.get('Safety', {}).get('SourceLocationMismatchCheck') == 'yes' and host_tr_cmd['source']!=new_source_port:
                        alarms.CommandSourceLocationMismatchWarning(host_tr_cmd['uuid'], host_tr_cmd['source'], host_tr_cmd['carrierID'], handler=self.secsgem_e82_h)
                        return
                    else:
                        host_tr_cmd['source']=new_source_port #re-assigned again for tfme, may the carrier move to Erack #2022/6/8
                        host_tr_cmd['TransferInfoList'][0][u'SourcePort']=new_source_port # Yuri 2024/11/07

            if host_tr_cmd['replace']:
                local_tr_cmd_1={
                            'uuid':host_tr_cmd['uuid']+'-UNLOAD',
                            'carrierID':host_tr_cmd['TransferInfoList'][1].get('CarrierID', ''),
                            'carrierLoc':host_tr_cmd['dest'],
                            'source':host_tr_cmd['dest'],
                            'priority':host_tr_cmd['priority'],
                            'dest':host_tr_cmd.get('back', '*'), #chocp 9/3
                            'first':False,
                            'last':True,
                            'TransferInfo':host_tr_cmd['TransferInfoList'][1],
                            'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][1],
                            'host_tr_cmd':host_tr_cmd
                        }
                local_tr_cmd_1['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd_1['source'], '') else 'other'
                local_tr_cmd_1['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd_1['dest'], '') else 'other'
                if unload_buf_constrain: #for BufConstrain
                    local_tr_cmd_1['buf_loc']=unload_buf_constrain.pop()
                elif buf_constrain: #for BufConstrain
                    local_tr_cmd_1['buf_loc']=buf_constrain.pop()
                elif 'BUF' in host_tr_cmd['dest'][-5:2]:
                    local_tr_cmd_1['buf_loc']=host_tr_cmd['dest'][-5:]

                h_vehicle.add_executing_transfer_queue(local_tr_cmd_1)
                tools.indicate_slot(local_tr_cmd_1['source'], local_tr_cmd_1['dest'], h_vehicle.id)
                tools.book_slot(local_tr_cmd_1['dest'], h_vehicle.id, local_tr_cmd_1['source']) #book for MR

                local_tr_cmd_2={
                            'uuid':host_tr_cmd['uuid']+'-LOAD',
                            'carrierID':host_tr_cmd['carrierID'],
                            'carrierLoc':host_tr_cmd['source'],
                            'source':host_tr_cmd['source'],
                            'dest':host_tr_cmd['dest'],
                            'priority':host_tr_cmd['priority'],
                            'first':True,
                            'last':False,
                            'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                            'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                            'host_tr_cmd':host_tr_cmd
                        }

                local_tr_cmd_2['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd_2['source'], '') else 'other'
                local_tr_cmd_2['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd_2['dest'], '') else 'other'

                if buf_constrain: #for BufConstrain
                    local_tr_cmd_2['buf_loc']=buf_constrain.pop()

                h_vehicle.add_executing_transfer_queue(local_tr_cmd_2)
                tools.indicate_slot(local_tr_cmd_2['source'], local_tr_cmd_2['dest'], h_vehicle.id)
                tools.book_slot(local_tr_cmd_2['dest'], h_vehicle.id, local_tr_cmd_2['source']) #book for MR
            else:
                local_tr_cmd={
                            'uuid':host_tr_cmd['uuid'],
                            'carrierID':host_tr_cmd['carrierID'],
                            'carrierLoc':host_tr_cmd['source'],
                            'source':host_tr_cmd['source'],
                            'dest':host_tr_cmd['dest'],
                            'priority':host_tr_cmd['priority'],
                            'first':True,
                            'last':True,
                            'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                            'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                            'host_tr_cmd':host_tr_cmd
                        }
                local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
                local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

                if buf_constrain: #for BufConstrain
                    local_tr_cmd['buf_loc']=buf_constrain.pop()
                elif 'BUF' in host_tr_cmd['dest'][-5:2]:
                    local_tr_cmd['buf_loc']=host_tr_cmd['dest'][-5:]

                h_vehicle.add_executing_transfer_queue(local_tr_cmd)

                tools.book_slot(local_tr_cmd['dest'], h_vehicle.id, local_tr_cmd['source'])  #book for MR, may cause delay
                tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'], h_vehicle.id)


    # def dispatch_shift_tr_cmd_to_vehicle(self, host_tr_cmd, h_vehicle, idx=0): #chocp 2024/8/21 for shift
    #     self.remove_waiting_transfer_by_idx(host_tr_cmd, idx)
    #     local_tr_cmd={
    #                 'uuid':host_tr_cmd['uuid'],
    #                 'carrierID':host_tr_cmd['carrierID'],
    #                 'carrierLoc':host_tr_cmd['source'],
    #                 'source':host_tr_cmd['source'],
    #                 'dest':host_tr_cmd['dest'],
    #                 'priority':host_tr_cmd['priority'],
    #                 'first':True,
    #                 'last':True,
    #                 'TransferInfo':host_tr_cmd['TransferInfoList'][0],
    #                 'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
    #                 'host_tr_cmd':host_tr_cmd,
                    
    #                 'transferType':'SHIFT'
    #             }
        
    #     local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
    #     local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

    #     h_vehicle.add_executing_transfer_queue(local_tr_cmd)


