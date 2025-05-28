#####################################################################
# gem_equipment.py
#
# (c) Copyright 2016, Benjamin Parzella. All rights reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#####################################################################
import logging
import code

import secsgem

import collections
import subprocess

import traceback
from time import strftime
from time import localtime
from time import sleep
from datetime import datetime
#from communication_log_file_handler import CommunicationLogFileHandler

from . import E82_dataitems as DI

from protocol.protocol_list import protocol_list

from global_variables import remotecmd_queue

import threading

#from global_variables import eRacks

#from vehicle import VehicleMgr
#chocp 2021/1/6


#chocp add
lock=threading.Lock()
def report_event(secsgem_h, ceid, dataset={}):
    if not secsgem_h:
        print("secsgem_h not start!!!!")
        return
    #print("secsgem_h:",secsgem_h)
    lock.acquire()
    try:
        for key, value in dataset.items():
            #print(secsgem_h, key, value)
            setattr(secsgem_h, key, value)

        secsgem_h.trigger_collection_events([ceid])
        #print('report_vehicle_event, ceid=%d'%ceid)
    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** report event error ***')
        getattr(secsgem_h, "communicationLogger").warn('CEID:{}, DATASET:{}'.format(ceid, dataset))
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass

    lock.release()
    return

def alarm_set(secsgem_h, alid, alarm_set, dataset={}): # Mike: 2021/08/10
    if not secsgem_h:
        return

    lock.acquire()
    try:
        for key, value in dataset.items():
            #print(key, value)
            setattr(secsgem_h, key, value)

        if alarm_set:
            secsgem_h.set_alarm(alid)
        else:
            secsgem_h.clear_alarm(alid)
        #print('alarm_set, alid=%d'%alid)
        sleep(0.05) #chocp fix 2021/11/24
    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** report event error ***')
        getattr(secsgem_h, "communicationLogger").warn('ALID:{}, SET:{}, DATASET:{}'.format(alid, alarm_set, dataset))
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass

    lock.release()
    return

# Mike: 2020/07/29
def get_variables(secsgem_h, key):
    if not secsgem_h:
        return

    lock.acquire()
    try:

        value=''
        value=getattr(secsgem_h, key)

    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** get variables error ***')
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass

    lock.release()
    return value

# Mike: 2020/07/29
def update_variables(secsgem_h, dataset={}):
    if not secsgem_h:
        return

    lock.acquire()
    try:

        for key, value in dataset.items():
            #print(key, value)
            setattr(secsgem_h, key, value)

    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** update variables error ***')
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass

    lock.release()
    return



CarrierNum=5
CommandNum=5
PortNum=5
VehicleNum=5
TransNum=5

########################
#       SVID
########################
''' basic '''
GEM_MDLN=1
GEM_SOFTREV=2
GEM_CLOCK=3
GEM_ALARMS_ENABLED=4
GEM_ALARMS_SET=5
GEM_CONTROL_STATE=6
GEM_LINK_STATE=7
GEM_EVENTS_ENABLED=8
''' SV '''

SV_EnhancedCarriers=50 #2024/06/21 for Mirle MCS
SV_AlarmsSetDescription=40 #2024/08/28 for Mirle MCS

SV_CarrierIDList=101 # CarrierID*n
SV_TSCState=103
SV_EqpName=104
#SV_SpecVersion=GEM_SOFTREV
SV_ActiveCarriers=201

SV_ActiveTransfers=202
SV_ActiveVehicles=203
SV_TransferCompleteInfo=501 # [TransferInfo, CarrierLoc]*n
#SV_TransferPortList=502 # TransferPort*n
SV_TransferPort=502
SV_TransferInfo=503
SV_TransferInfoList=504
SV_FromPort=525 #kelvin 202504/23

''' tmp sv, for events, not available '''
SV_CommandID=601
SV_VehicleInfo=602 # VehicleID, VehicleState
SV_CommandInfo=603 # CommandID, Priority, Replace
SV_ResultCode=604 # U2
SV_VehicleID=605
SV_CarrierID=606 # 'UNKNOWN[EqpName][Seq]'
SV_CarrierLoc=607
SV_PortID=608
SV_CommandType=609
SV_SourcePort=610
SV_DestPort=611
SV_Priority=612
SV_VehicleState=613 #chocp 0528
SV_CommandIDList=614
SV_StageID=615 # Mike: 2021/07/22
SV_VehicleLastState=626
SV_IDReadStatus=630
SV_BatteryValue=631
SV_VehicleLastPosition=632
SV_NearPort=633
SV_CurrentPortStates=118
SV_BlockNode=648#peter 241120
SV_DoorState=649 #peter 240705
SV_VehiclePose=634
SV_PointID=635

SV_ExecuteTime=616 #Kelvin 2022/08/21
SV_ALID=650
SV_ALTX=651
SV_ALSV=652
SV_UnitType=653
SV_UnitID=654
SV_Level=655
SV_CarrierType=656 #chocp 2022/1/2
SV_SubCode=657 #Chi 2022/06/17
SV_EnhancedCarrierInfo=658 #2024/06/21 for Mirle MCS
SV_InstallTime=659 #2024/06/21 for Mirle MCS
SV_CarrierState=660 #2024/06/21 for Mirle MCS
SV_NearLoc=310 # add for amkor ben 250502

''' Rack '''
SV_ActiveRacks=701
SV_eRack1=702
SV_eRack2=703
SV_eRack3=704
SV_eRack4=705
SV_RackInfo=706 #chocp 0528
SV_RackLocation=707 # Mike: 2021/05/11
SV_RackGroup=708 #Richard: 2024/08/16

SV_RackID=617 #chocp 0531
SV_SlotID=618 #chocp 0531
SV_SlotStatus=619 #chocp 0531
SV_LocateResult=620 # Mike: 2020/08/18
SV_SendBy=621
SV_EQID=622 # Mike: 2020/11/11
SV_VehicleSOH=623 # Mike: 2021/05/11
SV_TransferState=624
SV_Routes=625  # Mike: 2023/05/17
########################
#       CEID
########################
''' Control State '''
GEM_EQP_OFFLINE=11
GEM_CONTROL_STATE_LOCAL=12
GEM_CONTROL_STATE_REMOTE=13
''' TSC state transition events '''
TSCAutoCompleted=301
TSCAutoInitiated=302
TSCPauseCompleted=303
TSCPaused=304
TSCPauseInitiated=305
''' transfer command state transition events '''
TransferAbortCompleted=401
TransferAbortFailed=402
TransferAbortInitiated=403
TransferCancelCompleted=404
TransferCancelFailed=405
TransferCancelInitiated=406
TransferCompleted=407
TransferInitiated=408
TransferPaused=409
TransferResumed=410
Transferring=411
''' vehicle state transition events '''
VehicleStateChange=500

VehicleArrived=501
VehicleAcquireStarted=502
VehicleAcquireCompleted=503
VehicleAssigned=504
VehicleDeparted=505
VehicleDepositStarted=506
VehicleDepositCompleted=507

VehicleInstalled=508
VehicleRemoved=509
VehicleUnassigned=510

VehicleChargeStarted=511
VehicleChargeCompleted=512
VehicleExchangeStarted=513
VehicleExchangeCompleted=514
VehicleSwapStarted=515
VehicleSwapCompleted=516
VehicleShiftCompleted=517
VehicleShiftStarted=518
OpenDoorAcquire=519#peter 240705,test call door for K11

VehicleTrafficBlocking=521
VehicleTrafficRelease=522
VehicleObstacleBlocking=523
VehicleObstacleRelease=524

VehicleWaitGo=525 #peter 240126,vehicle wait go
NodeStatusChanged=526 #peter 241120

''' carrier state transition events '''
CarrierInstalled=601
CarrierRemoved=602
CarrierIDRead=603
''' port transfer state transition events'''
PortInService=701
PortOutOfService=702
''' non-transition events '''
OperatorInitiatedAction=801

RackStatusUpdate=802
PortStatusUpdate=803

VehicleBatteryHealth=804 # Mike: 2021/05/12

VehicleRoutes=805 # Mike: 2023/05/17
VehicleEnterSegment=806 # Mike: 2023/05/17
VehicleExitSegment=807 # Mike: 2023/05/17

LocateComplete=810
EqLoadComplete=820 # Mike: 2020/11/11
EqUnloadComplete=821 # Mike: 2022/07/24
CheckIn=850 # Mike: 2020/11/11
LoadBackOrder=851 # Mike: 2024/03/08

StageInvalided=860 # Mike: 2020/07/22
StageReached=861 # Mike: 2020/07/22
NoBlockingTimeExpired=862 # Mike: 2020/07/22
ExpectedDurationExpired=863 # Mike: 2020/07/22
WaitTimeoutExpired=864 # Mike: 2020/07/22

''' Tr request '''
TrLoadReq=901
TrUnLoadReq=902
TrBackReq=903
EQStatusReq=904
PortStatusReq=905
TrLoadWithGateReq=906
TrUnLoadWithGateReq=907
AssistCloseDoorReq=908
EQAutoOnReq=909
EQAutoOffReq=910
VehicleAssignReq=911
TrSwapReq=912
TrShiftReq=914# kelvinng 2024/11/04 TrShiftCheck


''' Alarm '''
AlarmCleared=51
AlarmSet=52
UnitAlarmSet=912
UnitAlarmCleared=913

''' Other '''
RuntimeStatus=200
VehicleLocationReport=531
VehicleOffline=532
VehicleOnline=533

secsgem.gem.equipmenthandler.GEM_MDLN=GEM_MDLN
secsgem.gem.equipmenthandler.GEM_SOFTREV=GEM_SOFTREV
secsgem.gem.equipmenthandler.GEM_CLOCK=GEM_CLOCK
secsgem.gem.equipmenthandler.GEM_ALARMS_ENABLED=GEM_ALARMS_ENABLED
secsgem.gem.equipmenthandler.GEM_ALARMS_SET=GEM_ALARMS_SET
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE=GEM_CONTROL_STATE
secsgem.gem.equipmenthandler.GEM_LINK_STATE=GEM_LINK_STATE
secsgem.gem.equipmenthandler.GEM_EVENTS_ENABLED=GEM_EVENTS_ENABLED
secsgem.gem.equipmenthandler.GEM_EQP_OFFLINE=GEM_EQP_OFFLINE
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_LOCAL=GEM_CONTROL_STATE_LOCAL
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_REMOTE=GEM_CONTROL_STATE_REMOTE

type_mapping={
    'l': secsgem.SecsVarList,
    'list': secsgem.SecsVarList,
    'array': secsgem.SecsVarArray,
    'a': secsgem.SecsVarString,
    'str': secsgem.SecsVarString,
    'string': secsgem.SecsVarString,
    'b': secsgem.SecsVarBinary,
    'bin': secsgem.SecsVarBinary,
    'binary': secsgem.SecsVarBinary,
    'f8': secsgem.SecsVarF8,
    'f4': secsgem.SecsVarF4,
    'i8': secsgem.SecsVarI8,
    'i4': secsgem.SecsVarI4,
    'i2': secsgem.SecsVarI2,
    'i1': secsgem.SecsVarI1,
    'u8': secsgem.SecsVarU8,
    'u4': secsgem.SecsVarU4,
    'u2': secsgem.SecsVarU2,
    'u1': secsgem.SecsVarU1,
    'bool': secsgem.SecsVarBoolean,
    'boolean': secsgem.SecsVarBoolean,
}

VariableTable={
    # SVID: {'name':'', 'unit':'', 'type':'list/array/str/b/f8/f4/i8/i4/i2/i1/u8/u4/u2/u1/bool'},SecsVarArray, SecsVarString, SecsVarBinary, \
}

EventTable={
    # CEID: {'report_id':[], 'report':[]},
    GEM_EQP_OFFLINE: {'report':[]},
    GEM_CONTROL_STATE_LOCAL: {'report':[]},
    GEM_CONTROL_STATE_REMOTE: {'report':[]},
    TSCAutoCompleted: {'report':[]},
    TSCAutoInitiated: {'report':[]},
    TSCPauseCompleted: {'report':[]},
    TSCPaused: {'report':[]},
    TSCPauseInitiated: {'report':[]},
    TransferAbortCompleted: {'report':[SV_CommandID, SV_TransferCompleteInfo]},
    TransferAbortFailed: {'report':[SV_CommandID]},
    TransferAbortInitiated: {'report':[SV_CommandID]},
    TransferCancelCompleted: {'report':[SV_CommandID]},
    TransferCancelFailed: {'report':[SV_CommandID]},
    TransferCancelInitiated: {'report':[SV_CommandID]},
    TransferCompleted: {'report':[SV_CommandInfo, SV_TransferCompleteInfo, SV_ResultCode]},
    TransferInitiated: {'report':[SV_CommandID]},
    TransferPaused: {'report':[SV_CommandID]},
    TransferResumed: {'report':[SV_CommandID]},
    Transferring: {'report':[SV_CommandID]},
    VehicleWaitGo: {'report':[SV_VehicleID, SV_TransferPort]},#peter 240126,vehicle wait go
    VehicleArrived: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_ResultCode]},

    VehicleAcquireStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},

    VehicleAcquireCompleted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},

    VehicleAssigned: {'report':[SV_VehicleID, SV_CommandIDList]},

    VehicleDeparted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort]},

    VehicleDepositStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},
    VehicleSwapStarted: {'report':[SV_VehicleID, SV_TransferPort]},
    VehicleSwapCompleted: {'report':[SV_VehicleID, SV_TransferPort, SV_ResultCode]},

    VehicleDepositCompleted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},
    VehicleShiftCompleted: {'report':[SV_VehicleID,SV_FromPort, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},
    VehicleShiftStarted: {'report':[SV_VehicleID, SV_FromPort, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},
    VehicleExchangeStarted: {'report':[SV_VehicleID]},
    VehicleExchangeCompleted: {'report':[SV_VehicleID]},
    VehicleChargeStarted: {'report':[SV_VehicleID]},
    VehicleChargeCompleted: {'report':[SV_VehicleID]},
    VehicleInstalled: {'report':[SV_VehicleID]},
    VehicleRemoved: {'report':[SV_VehicleID]},
    VehicleUnassigned: {'report':[SV_VehicleID, SV_CommandIDList]},
    
    VehicleStateChange: {'report':[SV_VehicleID, SV_VehicleState, SV_VehicleLastState]},

    CarrierInstalled: {'report':[SV_VehicleID, SV_CarrierID, SV_CarrierLoc, SV_CommandID]},

    CarrierRemoved: {'report':[SV_VehicleID, SV_CarrierID, SV_CarrierLoc, SV_CommandID]},

    PortInService: {'report':[SV_PortID]},
    PortOutOfService: {'report':[SV_PortID]},
    OperatorInitiatedAction: {'report':[SV_CommandID, SV_CommandType, SV_CarrierID, SV_SourcePort, SV_DestPort, SV_Priority]},
    RackStatusUpdate: {'report':[SV_RackInfo]},
    PortStatusUpdate: {'report':[SV_RackID, SV_SlotID, SV_SlotStatus, SV_SendBy, SV_RackLocation,SV_RackGroup]},#Richard: 2024/08/16
    VehicleBatteryHealth: {'report':[SV_VehicleID, SV_VehicleSOH]},
    VehicleRoutes: {'report':[SV_VehicleID, SV_Routes]},
    VehicleEnterSegment: {'report':[SV_VehicleID, SV_Routes]},
    VehicleExitSegment: {'report':[SV_VehicleID, SV_Routes]},
    LocateComplete: {'report':[SV_CarrierID, SV_RackID, SV_SlotID, SV_LocateResult]},
    EqLoadComplete: {'report':[SV_VehicleID, SV_EQID, SV_PortID, SV_CarrierID]},
    EqUnloadComplete: {'report':[SV_VehicleID, SV_EQID, SV_PortID, SV_CarrierID]},
    CheckIn: {'report':[SV_RackID, SV_SlotID, SV_SlotStatus]},
    LoadBackOrder: {'report':[SV_RackID, SV_CommandIDList]},
    StageInvalided: {'report':[SV_StageID]},
    StageReached: {'report':[SV_StageID, SV_VehicleID]},
    NoBlockingTimeExpired: {'report':[SV_StageID]},
    ExpectedDurationExpired: {'report':[SV_StageID]},
    WaitTimeoutExpired: {'report':[SV_StageID]},
    TrLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrUnLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrShiftReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},#kelvinng 20250216
    TrBackReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrSwapReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    EQStatusReq: {'report':[SV_EQID]},
    PortStatusReq: {'report':[SV_PortID]},
    TrLoadWithGateReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrUnLoadWithGateReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    AssistCloseDoorReq: {'report':[SV_VehicleID, SV_TransferPort]},
    EQAutoOnReq: {'report':[SV_EQID]},
    EQAutoOffReq: {'report':[SV_EQID]},
    VehicleAssignReq: {'report':[SV_VehicleID, SV_TransferPort]},
    AlarmCleared: {'report':[SV_CommandID, SV_VehicleInfo, SV_ALID, SV_ALTX, SV_CarrierID, SV_CarrierLoc]},
    AlarmSet: {'report':[SV_CommandID, SV_VehicleInfo, SV_ALID, SV_ALTX, SV_CarrierID, SV_CarrierLoc]},
    CarrierIDRead:{'report':[SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_IDReadStatus]},
    UnitAlarmSet :{'report':[]},
    UnitAlarmCleared :{'report':[]},
    RuntimeStatus :{'report':[]},
    OpenDoorAcquire: {'report':[SV_VehicleID, SV_TransferPort,SV_DoorState]},#peter 240705,test call door for K11
    NodeStatusChanged: {'report':[SV_BlockNode]},#peter 241120
    
    VehicleTrafficBlocking: {'report':[SV_VehicleID]},
    VehicleTrafficRelease: {'report':[SV_VehicleID]},
    VehicleObstacleBlocking: {'report':[SV_VehicleID]},
    VehicleObstacleRelease: {'report':[SV_VehicleID]},
    VehicleLocationReport: {'report':[SV_VehicleID, SV_VehiclePose, SV_PointID]},
    VehicleOffline: {'report':[SV_VehicleID]},
    VehicleOnline: {'report':[SV_VehicleID]},
}

ReportTable={
    # RPTID: [SVID],
}


AlarmTable={
    # ALID: {'report_id':[], 'report':[], 'text':ALTX},
    10000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode], 'text':'TSC internal error or code exception'}, #chocp 2021/11/26
    10001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text':'Vehicle internal error or code exception'}, #chocp 2021/11/26
    10002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID], 'text':'Vehicle generate action fail or no buffer left'}, #chocp 2021/11/26
    10003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'Robot status error'},
    10004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR move status error'},
    10005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_SourcePort, SV_DestPort], 'text':'MR route error error'},
    10006: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text':'MR offline'},
    10007: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'interlock error'},
    10008: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text':'MR not in auto mode'},
    10009: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR with other alarm'},
    10010: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text':'TSC in manual test'},
    10011: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_RackID], 'text':'Fault rack full or allocate fail'},
    10012: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_RackID], 'text':'Select rack full or allocate fail'},
    10013: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_PortID], 'text':'Port not found or syntax error'},
    10014: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack syntax error'},
    10015: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'Safety check fail, port not reach'},
    10016: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'Safety check fail, eq port check fail'},
    10017: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'Safety check fail, erack check fail'},
    10018: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'Safety check fail, buffer check fail'},
    10019: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'CarrierID read fail'},
    10020: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'CarrierID already exists'},
    10021: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'Robot status check error'},
    10022: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR move status check error'},
    10023: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'Transfer command timeout'}, #chocp fix 2021/10/10
    10024: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_SourcePort, SV_DestPort], 'text':'MR try or select to standby station fail'},
    10025: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR excecute charge command timeout'},
    10026: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'CarrierType None or Check Error for Acquire/Deposit'},
    10027: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID], 'text':'MR move with route obstacles'},
    10028: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_SourcePort, SV_DestPort], 'text': 'MR try or select to charge station fail'},
    10029: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_PortID], 'text': 'Stop MR command to replace new job'},
    10030: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_PortID], 'text': 'No available carrier.'},
    10031: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID], 'text': 'MR Stop wit host command'},
    10032: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text': 'MR with other warning'},
    10033: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text': 'MR with emergency evacuation'},
    10034: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text': 'Action not support'},
    10035: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CarrierLoc, SV_CarrierID, SV_CommandID], 'text':'Fault carrier on MR'},

    
    10051: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack off line'},
    10052: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level high'},
    10053: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level full'},
    10054: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level low'},
    10055: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level empty'},


    40000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, ], 'text':'Host transfer cmd parse get exception'},

    40001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Cancel by host'},
    40002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Abort by host'},

    40007: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, commandID duplicated in active transfers'},
    40008: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host change cmd dest port, due to TrLoad request NG'},
    40009: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'Host transfer cmd, CarrierType None or Error'},
    40010: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID not in white list'},
    40011: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort], 'text':'Host transfer cmd, source port not found'},
    40012: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host transfer cmd, dest port not found'},
    40013: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID duplicated in waiting queue'},
    40014: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID duplicated in executing queue'},
    40015: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort], 'text':'Host transfer cmd, source port null'},
    40016: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, can not locate carrierID'},
    40017: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host transfer cmd, dest port auto assign fail'},
    40018: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort, SV_CarrierID], 'text':'Host transfer cmd, source port conflict with specified carrier'},
    40019: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host transfer cmd, dest port duplicate with other cmd'},
    40020: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort], 'text':'Host transfer cmd, source port duplicate with other cmd'},
    40021: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, can not specify MR'},
    40022: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, loadport disabled'},#Hshuo 20231211 
    40023: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, service zone disabled'},#Hshuo 20231211   
    40024: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort, SV_CarrierID], 'text':'Host transfer cmd, carrier source port mismatch'},

    50061: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Elevator with alarmst'},
    50062: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Elevator linking timeout'},
    50063: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Elevator Connect fail'},

    60000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host order rtd cmd, workID duplicate in worklist'},
    60001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier duplicate in worklist'},
    60002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, can not locate carrier'},
    60003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier ID can not null'},
    60004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_DestPort], 'text':'Host order rtd cmd, dest port dispatch fail'},



}

def GEM_PARAM_DEF():
    secsgem.gem.equipmenthandler.GEM_MDLN=GEM_MDLN
    secsgem.gem.equipmenthandler.GEM_SOFTREV=GEM_SOFTREV
    secsgem.gem.equipmenthandler.GEM_CLOCK=GEM_CLOCK
    secsgem.gem.equipmenthandler.GEM_ALARMS_ENABLED=GEM_ALARMS_ENABLED
    secsgem.gem.equipmenthandler.GEM_ALARMS_SET=GEM_ALARMS_SET
    secsgem.gem.equipmenthandler.GEM_CONTROL_STATE=GEM_CONTROL_STATE
    secsgem.gem.equipmenthandler.GEM_LINK_STATE=GEM_LINK_STATE
    secsgem.gem.equipmenthandler.GEM_EVENTS_ENABLED=GEM_EVENTS_ENABLED
    secsgem.gem.equipmenthandler.GEM_EQP_OFFLINE=GEM_EQP_OFFLINE
    secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_LOCAL=GEM_CONTROL_STATE_LOCAL
    secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_REMOTE=GEM_CONTROL_STATE_REMOTE
    secsgem.gem.equipmenthandler.GEM_SPOOL_COUNT_ACTUAL=GEM_SPOOL_COUNT_ACTUAL
    secsgem.gem.equipmenthandler.GEM_SPOOL_COUNT_TOTAL=GEM_SPOOL_COUNT_TOTAL
    secsgem.gem.equipmenthandler.GEM_SPOOL_FULL_TIME=GEM_SPOOL_FULL_TIME
    secsgem.gem.equipmenthandler.GEM_SPOOL_START_TIME=GEM_SPOOL_START_TIME
    secsgem.gem.equipmenthandler.GEM_SPOOL_STATE=GEM_SPOOL_STATE
    secsgem.gem.equipmenthandler.GEM_SPOOL_UNLOAD_SUPSTATE=GEM_SPOOL_UNLOAD_SUPSTATE

class E82Equipment(secsgem.GemEquipmentHandler):
    def __init__(self, address, port, active, session_id, name='Gyro Agvc', log_name="E82_hsms_communication", mdln='TSC_v3.7', T3=45, T5=10, T6=5, T7=10, T8=5, custom_connection_handler=None, initial_control_state="ONLINE", initial_online_control_state="REMOTE"):

        SOFTREV='' # Mike: 2021/11/12
        try:
            f=open('version.txt','r')
            SOFTREV=f.readline()
            f.close()
        except:
            pass

        if mdln in protocol_list:
            print('open special protocal for {}'.format(mdln))
            for attr in dir(protocol_list[mdln]):
                if '__' not in attr:
                    globals()[attr]=getattr(protocol_list[mdln], attr)
            GEM_PARAM_DEF()
        elif 'v3' in mdln.lower():
            for attr in dir(protocol_list['v3']):
                if '__' not in attr:
                    globals()[attr]=getattr(protocol_list['v3'], attr)
            GEM_PARAM_DEF()

        secsgem.GemEquipmentHandler.__init__(self, address, port, active, session_id, name, custom_connection_handler, initial_control_state, initial_online_control_state)

        self.connection.T3=T3
        self.connection.T5=T5
        self.connection.T6=T6
        self.connection.T7=T7
        self.connection.T8=T8

        self.MDLN=mdln
        self.SOFTREV=SOFTREV
        self.EqpName=name
        self._spool_enable=0 # 0: disable, 1: enable

        self.communicationLogger=logging.getLogger(log_name) # Mike: 2020/04/29
        self.communicationLogger.setLevel(logging.DEBUG)
        self.logger=self.communicationLogger
        self.connection.logger=self.communicationLogger

        self.ERROR_MSG=''

        self.stop=False
        self.msg_queue=collections.deque(maxlen=20)


        # Mike: 2020/03/19
        self.CommandID=''

        # Mike: 2021/07/22
        self.StageID=''

        ### example: self.CommandIDList=["111111", "222222"]
        self.CommandIDList=[]

        ### example: self.VehicleInfo={"VehicleID":"666666", "VehicleState":3}
        ### VehicleState=1: Remove, 2: Not Assigned, 3: Enroute, 4: Parked, 5: Acquiring, 6: Depositing
        self.VehicleInfo={"VehicleID":"123321", "VehicleState":2, "VehicleLastState":1}

        ### example: self.TransferCompleteInfo=[
        ###              {"TransferInfo":{"CarrierID": "123456", "SourcePort": "PORTX1", "DestPort": "PORTY1"}, "CarrierLoc":"aaaa"},
        ###              {"TransferInfo":{"CarrierID": "654321", "SourcePort": "PORTX2", "DestPort": "PORTY2"}, "CarrierLoc":"bbbb"}
        ###          ]
        self.TransferCompleteInfo=[]

        ### example: self.CommandInfo={"CommandID":"cmd1", "Priority":1, "Replace":0}
        self.CommandInfo={"CommandID":"", "Priority":0, "Replace":0, "TransferState":0} # CommandID, Priority, Replace
        self.TransferInfo={"CarrierID": "", "SourcePort": "", "DestPort": ""} # CarrierID, SourcePort, DestPort # Mike: 2021/08/10
        self.TransferInfoList=[] # TransferInfo # Mike: 2021/07/27
        self.TransferState=0
        ### 0: success, 1: canceled, 2: aborted
        self.ResultCode=0

        self.VehicleID=''

        ### example: self.TransferPortList=["PORT01", "PORT02"]
        self.TransferPortList=[]
        self.CurrentPortStates=[]
        self.TransferPort=''
        self.FromPort=''#kelvinng202504/23

        ### example: self.CarrierIDList=["123456", "654321"]
        self.CarrierIDList=[]

        ### 'UNKNOWN[EqpName][Seq]' for unknown carrier
        self.CarrierID=''

        self.CarrierLoc=''

        self.PortID=''

        ### TRANSFER, CANCEL, ABORT
        self.CommandType=''

        self.SourcePort=''
        self.DestPort=''
        self.NearPort=  ''

        ### 0: invalid 1~99: low~high
        self.Priority=0
        self.IDReadStatus=0
        self.BatteryValue=0
        self.VehicleLastPosition=''

        self.CurrentPortStates=''
        SV_VehicleState=''
        SV_VehicleLastState=''

        ### 1: SC Init, 2: Paused, 3: Auto, 4: Pausing
        self.TSCState=0

        ### example: ActiveCarriers={
        ###              "123456":{"CarrierID": "123456", "VehicleID": "111111", "CarrierLoc": "aaaa"},
        ###              "654321":{"CarrierID": "654321", "VehicleID": "666666", "CarrierLoc": "bbbb"}
        ###          }
        self.ActiveCarriers={}
        self.EnhancedCarriers={}
        ### example: self.ActiveTransfers={
        ###              "cmd1":{
        ###                  "CommandInfo": {"CommandID":"cmd1", "Priority":1, "Replace":0},
        ###                  "TransferInfo": [{"CarrierID": "123456", "SourcePort": "PORTX1", "DestPort": "PORTY1"},
        ###                                   {"CarrierID": "654321", "SourcePort": "PORTX2", "DestPort": "PORTY2"}]},
        ###              "cmd2":{
        ###                  "CommandInfo": {"CommandID":"cmd2", "Priority":2, "Replace":0},
        ###                  "TransferInfo": [{"CarrierID": "111111", "SourcePort": "PORTX3", "DestPort": "PORTY3"},
        ###                                   {"CarrierID": "666666", "SourcePort": "PORTX4", "DestPort": "PORTY4"}]}
        ###          }
        self.ActiveTransfers={}

        ### example: self.h.ActiveVehicles={
        ###              "111111": {"VehicleInfo":{"VehicleID": "111111", "VehicleState": 2}},
        ###              "111111": {"VehicleInfo":{"VehicleID": "666666", "VehicleState": 4}}
        ###          }
        self.ActiveVehicles={}
        self.AlarmsSetDescription={}
        ### example: self.h.ActiveRacks={
        ###              "E001": {"RackInfo":{"RackID": "E001", "RackState": [{"PortID":"1", "Status":'None'}, {"PortID":"2", "Status":'None'}, ...]}},
        ###              "E002": {"RackInfo":{"RackID": "E002", "RackState": [{"PortID":"1", "Status":'None'}, {"PortID":"2", "Status":'None'}, ...]}},
        ###              "E003": {"RackInfo":{"RackID": "E003", "RackState": [{"PortID":"1", "Status":'None'}, {"PortID":"2", "Status":'None'}, ...]}},
        ###              "E004": {"RackInfo":{"RackID": "E004", "RackState": [{"PortID":"1", "Status":'None'}, {"PortID":"2", "Status":'None'}, ...]}}
        ###          }
        self.RackLocation='' # Mike: 2021/05/11
        self.RackGroup='' # Richard: 2024/08/16
        RackState=[]
        for i in range(12):
            RackState.append({"SlotID":str(i+1), "Status":'None', "Machine":""}) #chocp 0531
        self.ActiveRacks={}
        self.RackInfo={"RackID": "E001", "RackStates": RackState, "RackLoc": self.RackLocation} # Mike: 2021/05/11
        self.RackID=''
        self.SlotID=''
        self.VehicleSOH=100 # Mike: 2021/05/11
        self.SlotStatus='None'
        self.LocateResult='' # Mike: 2020/08/18
        self.SendBy=0
        self.EQID='' # Mike: 2020/11/11
        self.ALID=0 #2024/07/25
        self.ALTX=''
        self.ALSV=''
        self.UnitType=''
        self.UnitID=''
        self.Level=''
        self.CarrierType='' #chocp: 2022/1/2
        self.SubCode='' #Chi 2022/06/17
        self.Routes=''# Mike: 2023/05/17
        self.ExecuteTime=''
        self.DoorState=""#peter 240705
        self.VehiclePose='(0,0,0,0)' # (x, y, w, z)
        self.PointID=''

        self.transfer_lock=threading.Lock()

        #####################################
        #     Status Variable Declaration
        #####################################
        ''' SV initial '''
        '''for VID, DATA in VariableTable.items():
            if 'default' in DATA:
                self.status_variables.update({
                    VID: secsgem.StatusVariable(VID, DATA['name'], DATA['unit'], type_mapping[DATA['type'].lower()], False),
                })
                self.status_variables[VID].value=DATA['default']
            else:
                self.status_variables.update({
                    VID: secsgem.StatusVariable(VID, DATA['name'], DATA['unit'], type_mapping[DATA['type'].lower()], True),
                })'''

        self.status_variables.update({
            GEM_MDLN: secsgem.StatusVariable(GEM_MDLN, "GEM_MDLN", "", secsgem.SecsVarString, False),
            GEM_SOFTREV: secsgem.StatusVariable(GEM_SOFTREV, "GEM_SOFTREV", "", secsgem.SecsVarString, False),
            SV_EqpName: secsgem.StatusVariable(SV_EqpName, "SV_EqpName", "", secsgem.SecsVarString, False),
            SV_CarrierIDList: secsgem.StatusVariable(SV_CarrierIDList, "SV_CarrierIDList", "", secsgem.SecsVarArray, True),
            SV_TSCState: secsgem.StatusVariable(SV_TSCState, "SV_TSCState", "", secsgem.SecsVarU2, True),
            SV_ActiveCarriers: secsgem.StatusVariable(SV_ActiveCarriers, "SV_ActiveCarriers", "", secsgem.SecsVarArray, True),
            SV_EnhancedCarriers: secsgem.StatusVariable(SV_EnhancedCarriers, "SV_EnhancedCarriers", "", secsgem.SecsVarArray, True),
            SV_ActiveTransfers: secsgem.StatusVariable(SV_ActiveTransfers, "SV_ActiveTransfers", "", secsgem.SecsVarArray, True),
            SV_ActiveVehicles: secsgem.StatusVariable(SV_ActiveVehicles, "SV_ActiveVehicles", "", secsgem.SecsVarArray, True),
            SV_ActiveRacks: secsgem.StatusVariable(SV_ActiveRacks, "SV_ActiveRacks", "", secsgem.SecsVarArray, True),
            SV_TransferCompleteInfo: secsgem.StatusVariable(SV_TransferCompleteInfo, "SV_TransferCompleteInfo", "", secsgem.SecsVarArray, True),
            #SV_TransferPortList: secsgem.StatusVariable(SV_TransferPortList, "SV_TransferPortList", "", secsgem.SecsVarArray, True),
            SV_TransferPort: secsgem.StatusVariable(SV_TransferPort, "SV_TransferPort", "", secsgem.SecsVarString, True),
            SV_FromPort: secsgem.StatusVariable(SV_FromPort, "SV_FromPort", "", secsgem.SecsVarString, True),# kelvinng 20250423
            SV_TransferInfo: secsgem.StatusVariable(SV_TransferInfo, "SV_TransferInfo", "", secsgem.SecsVarList, True), # Mike: 2021/08/10
            SV_TransferInfoList: secsgem.StatusVariable(SV_TransferInfoList, "SV_TransferInfoList", "", secsgem.SecsVarArray, True), # Mike: 2021/11/1
            #for internal use
            SV_CommandID: secsgem.StatusVariable(SV_CommandID, "SV_CommandID", "", secsgem.SecsVarString, True),
            SV_CommandIDList: secsgem.StatusVariable(SV_CommandIDList, "SV_CommandIDList", "", secsgem.SecsVarArray, True),
            SV_VehicleInfo: secsgem.StatusVariable(SV_VehicleInfo, "SV_VehicleInfo", "", secsgem.SecsVarList, True),
            SV_CommandInfo: secsgem.StatusVariable(SV_CommandInfo, "SV_CommandInfo", "", secsgem.SecsVarList, True),
            SV_ResultCode: secsgem.StatusVariable(SV_ResultCode, "SV_ResultCode", "", secsgem.SecsVarU2, True),
            SV_VehicleID: secsgem.StatusVariable(SV_VehicleID, "SV_VehicleID", "", secsgem.SecsVarString, True),
            SV_CarrierID: secsgem.StatusVariable(SV_CarrierID, "SV_CarrierID", "", secsgem.SecsVarString, True),
            SV_CarrierLoc: secsgem.StatusVariable(SV_CarrierLoc, "SV_CarrierLoc", "", secsgem.SecsVarString, True),
            SV_PortID: secsgem.StatusVariable(SV_PortID, "SV_PortID", "", secsgem.SecsVarString, True),
            SV_CommandType: secsgem.StatusVariable(SV_CommandType, "SV_CommandType", "", secsgem.SecsVarString, True),
            SV_SourcePort: secsgem.StatusVariable(SV_SourcePort, "SV_SourcePort", "", secsgem.SecsVarString, True),
            SV_DestPort: secsgem.StatusVariable(SV_DestPort, "SV_DestPort", "", secsgem.SecsVarString, True),
            SV_Priority: secsgem.StatusVariable(SV_Priority, "SV_Priority", "", secsgem.SecsVarU2, True),
            SV_RackInfo: secsgem.StatusVariable(SV_RackInfo, "SV_RackInfo", "", secsgem.SecsVarList, True),
            SV_RackID: secsgem.StatusVariable(SV_RackID, "SV_RackID", "", secsgem.SecsVarString, True),
            SV_RackLocation: secsgem.StatusVariable(SV_RackLocation, "SV_RackLocation", "", secsgem.SecsVarString, True), # Mike: 2021/05/12
            SV_RackGroup: secsgem.StatusVariable(SV_RackGroup, "SV_RackGroup", "", secsgem.SecsVarString, True), # Richard: 2024/08/12
            SV_VehicleSOH: secsgem.StatusVariable(SV_VehicleSOH, "SV_VehicleSOH", "", secsgem.SecsVarU2, True), # Mike: 2021/05/12
            SV_SlotID: secsgem.StatusVariable(SV_SlotID, "SV_SlotID", "", secsgem.SecsVarString, True),
            SV_SlotStatus: secsgem.StatusVariable(SV_SlotStatus, "SV_SlotStatus", "", secsgem.SecsVarString, True),
            SV_LocateResult: secsgem.StatusVariable(SV_LocateResult, "SV_LocateResult", "", secsgem.SecsVarString, True), # Mike: 2020/08/18
            SV_SendBy: secsgem.StatusVariable(SV_SendBy, "SV_SendBy", "", secsgem.SecsVarU2, True),
            SV_EQID: secsgem.StatusVariable(SV_EQID, "SV_EQID", "", secsgem.SecsVarString, True), # Mike: 2020/11/11
            SV_StageID: secsgem.StatusVariable(SV_StageID, "SV_StageID", "", secsgem.SecsVarString, True), # Mike: 2021/07/22
            SV_ExecuteTime: secsgem.StatusVariable(SV_ExecuteTime, "SV_ExecuteTime", "", secsgem.SecsVarString, True), # Mike: 2021/07/22
            SV_ALID: secsgem.StatusVariable(SV_ALID, "SV_ALID", "", secsgem.SecsVarString, True), # 2024/07/12
            SV_ALTX: secsgem.StatusVariable(SV_ALTX, "SV_ALTX", "", secsgem.SecsVarString, True), # Mike: 2021/11/08
            SV_ALSV: secsgem.StatusVariable(SV_ALSV, "SV_ALSV", "", secsgem.SecsVarString, True), # Mike: 2021/11/08
            SV_UnitType: secsgem.StatusVariable(SV_UnitType, "SV_UnitType", "", secsgem.SecsVarString, True), # Mike: 2021/11/29
            SV_UnitID: secsgem.StatusVariable(SV_UnitID, "SV_UnitID", "", secsgem.SecsVarString, True), # Mike: 2021/11/29
            SV_Level: secsgem.StatusVariable(SV_Level, "SV_Level", "", secsgem.SecsVarString, True), # Mike: 2021/12/01
            SV_CarrierType: secsgem.StatusVariable(SV_CarrierType, "SV_CarrierType", "", secsgem.SecsVarString, True), # chocp 2022/1/2
            SV_SubCode: secsgem.StatusVariable(SV_SubCode, "SV_SubCode", "", secsgem.SecsVarString, True), #Chi 2022/06/17
            SV_TransferState: secsgem.StatusVariable(SV_TransferState, "SV_TransferState", "", secsgem.SecsVarU2, True),
            SV_Routes: secsgem.StatusVariable(SV_Routes, "SV_Routes", "", secsgem.SecsVarString, True), # Mike: 2023/05/17
            SV_CarrierState: secsgem.StatusVariable(SV_CarrierState, "SV_CarrierState", "", secsgem.SecsVarU2, True),
            SV_InstallTime: secsgem.StatusVariable(SV_InstallTime, "SV_InstallTime", "", secsgem.SecsVarString, True), # Mike: 2023/05/17
            SV_IDReadStatus:secsgem.StatusVariable(SV_IDReadStatus, "SV_IDReadStatus", "", secsgem.SecsVarU2, True), # 2024/07/15
            SV_BatteryValue:secsgem.StatusVariable(SV_BatteryValue, "SV_BatteryValue", "", secsgem.SecsVarU2, True), # 2024/07/15
            SV_VehicleLastPosition:secsgem.StatusVariable(SV_VehicleLastPosition, "SV_VehicleLastPosition", "", secsgem.SecsVarString, True), # 2024/07/15
            SV_VehicleState:secsgem.StatusVariable(SV_VehicleState, "SV_VehicleState", "", secsgem.SecsVarU2, True), # 2024/07/15
            SV_VehicleLastState:secsgem.StatusVariable(SV_VehicleLastState, "SV_VehicleLastState", "", secsgem.SecsVarU2, True), # 2024/07/15
            SV_NearPort:secsgem.StatusVariable(SV_NearPort, "SV_NearPort", "", secsgem.SecsVarString, True), # 2024/07/15
            SV_CurrentPortStates: secsgem.StatusVariable(SV_CurrentPortStates, "SV_CurrentPortStates", "", secsgem.SecsVarList, True), # Mike: 2021/08/10
            SV_AlarmsSetDescription: secsgem.StatusVariable(SV_AlarmsSetDescription, "SV_AlarmsSetDescription", "", secsgem.SecsVarList, True), # 2024/08/28
            SV_DoorState: secsgem.StatusVariable(SV_DoorState, "SV_DoorState", "", secsgem.SecsVarString, True),#peter 240705
            SV_VehiclePose: secsgem.StatusVariable(SV_VehiclePose, "SV_VehiclePose", "", secsgem.SecsVarString, True),
            SV_PointID: secsgem.StatusVariable(SV_PointID, "SV_PointID", "", secsgem.SecsVarString, True),

        })
        self.status_variables[GEM_MDLN].value=self.MDLN
        self.status_variables[GEM_SOFTREV].value=self.SOFTREV
        self.status_variables[SV_EqpName].value=self.EqpName


        #####################################
        #       Report Declaration
        #####################################
        ''' Report initial '''
        for RPTID, DATA in ReportTable.items():
            self.registered_reports.update({
                RPTID: secsgem.CollectionEventReport(RPTID, DATA),
            })

        for CEID, DATA in EventTable.items():
            if 'report' in DATA and 'report_id' not in DATA:
                if DATA['report']:
                    self.registered_reports.update({
                        CEID+5000: secsgem.CollectionEventReport(CEID+5000, DATA['report']),
                    })

        for ALID, DATA in AlarmTable.items():
            if 'report' in DATA and 'report_id' not in DATA:
                if DATA['report']:
                    self.registered_reports.update({
                        ALID+500000: secsgem.CollectionEventReport(ALID+500000,  DATA['report']),
                    })


        #####################################
        #       Event Declaration/Link
        #####################################
        ''' Report link initial'''
        for ALID, DATA in AlarmTable.items():
            if 'report_id' in DATA:
                if DATA['report_id']:
                    self.registered_collection_events.update({
                        ALID+100000: secsgem.CollectionEventLink(ALID+100000, DATA['report_id']),
                        ALID+200000: secsgem.CollectionEventLink(ALID+200000, DATA['report_id']),
                    })
                    self.registered_collection_events[ALID+100000].enabled=True
                    self.registered_collection_events[ALID+200000].enabled=True
                    continue
            if 'report' in DATA:
                if DATA['report']:
                    self.registered_collection_events.update({
                        ALID+100000: secsgem.CollectionEventLink(ALID+100000, [ALID+500000]),
                        ALID+200000: secsgem.CollectionEventLink(ALID+200000, [ALID+500000]),
                    })
                    self.registered_collection_events[ALID+100000].enabled=True
                    self.registered_collection_events[ALID+200000].enabled=True
                    continue
            self.registered_collection_events.update({
                ALID+100000: secsgem.CollectionEventLink(ALID+100000, [ALID+500000]),
                ALID+200000: secsgem.CollectionEventLink(ALID+200000, [ALID+500000]),
            })
            self.registered_collection_events[ALID+100000].enabled=True
            self.registered_collection_events[ALID+200000].enabled=True

        for CEID, DATA in EventTable.items():
            if 'report_id' in DATA:
                if DATA['report_id']:
                    self.registered_collection_events.update({
                        CEID: secsgem.CollectionEventLink(CEID, [DATA['report_id']]),
                    })
                    self.registered_collection_events[CEID].enabled=True
                    continue
            if 'report' in DATA:
                if DATA['report']:
                    self.registered_collection_events.update({
                        CEID: secsgem.CollectionEventLink(CEID, [CEID+5000]),
                    })
                    self.registered_collection_events[CEID].enabled=True
                    continue
            self.registered_collection_events.update({
                CEID: secsgem.CollectionEventLink(CEID, []),
            })
            self.registered_collection_events[CEID].enabled=True


        #####################################
        #         Alarm Declaration
        #####################################
        ''' Alarm initial '''
        for ALID, DATA in AlarmTable.items():
            if mdln == 'v3_MIRLE':
                if 'event_id' in DATA and len(DATA['event_id']) == 2:
                    self.alarms.update({
                        ALID: secsgem.Alarm((ALID), DATA['text'], DATA['text'], secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, DATA['event_id'][0], DATA['event_id'][1]),
                    })
                else:
                    self.alarms.update({
                        ALID: secsgem.Alarm((ALID), DATA['text'], DATA['text'], secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, 52, 51),
                    })
            else:
                if 'event_id' in DATA and len(DATA['event_id']) == 2:
                    self.alarms.update({
                        ALID: secsgem.Alarm((ALID), DATA['text'], DATA['text'], secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, DATA['event_id'][0], DATA['event_id'][1]),
                    })
                else:
                    self.alarms.update({
                        ALID: secsgem.Alarm((ALID), DATA['text'], DATA['text'], secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, ALID+100000, ALID+200000),
                    })
            self.alarms[ALID].enabled=True


        #####################################
        #     Remote Command Declaration
        #####################################
        ''' Remote command '''
        self.remote_commands.clear()

        self.remote_commands.update({
            "ABORT": secsgem.RemoteCommand("ABORT", "abort command", ["COMMANDID"], None),
            "ASSERT": secsgem.RemoteCommand("ASSERT", "assert command", ["REQUEST", "COMMANDID", "CARRIERID", "DESTPORT", "RESULT"], None, ["LOTID", "QUANTITY", "HEIGHT","WAIT","TYPE","NGPORT","TOTAL"]),
            "ASSIGNABLE": secsgem.RemoteCommand("ASSIGNABLE", "assignable command", ["VEHICLEID"], None),
            "ASSGINLOT": secsgem.RemoteCommand("ASSGINLOT", "assginlot command", ["CARRIERID", "DESTPORT"], None),
            "ASSOCIATE": secsgem.RemoteCommand("ASSOCIATE", "associate command", ["RACKID", "PORTID", "CARRIERID", "ASSOCIATEDATA"], None, ["*"]), # Mike: 2020/07/29, chocp need fix
            #"ASSOCIATE": secsgem.RemoteCommand("ASSOCIATE", "associate command", ["RACKID", "PORTID", "CARRIERID", "LOTID", "CUSTOMER", "PLANT", "NEXTSTEP"], None), # Mike: 2020/07/29, chocp need fix
            "BINDING": secsgem.RemoteCommand("BINDING", "binding command", ["CARRIERID", "LOTID", "NEXTSTEP", "EQLIST", "PRIORITY"], None), # Mike: 2020/11/11
            "CALL": secsgem.RemoteCommand("CALL", "call vehicle command", ["VEHICLEID", "DESTPORT"], None, ["COMMANDID", "NOBLOCKINGTIME", "WAITTIMEOUT"]),
            "CANCEL": secsgem.RemoteCommand("CANCEL", "cancel command", ["COMMANDID"], None),
            "DOOROPENREPLY": secsgem.RemoteCommand("DOOROPENREPLY", "open door reply command",["VEHICLEID"], None,['DOORSTATE']), #peter 240705,test call door for K11
            "EVACUATION": secsgem.RemoteCommand("EVACUATION", "emergency evacuation command", ['SITUATION'], None,["VEHICLEID"]), # Chi: 2024/05/29
            "INFOUPDATE": secsgem.RemoteCommand("INFOUPDATE", "in foup date command", ["CARRIERID"], None, ["*"]), # Mike: 2020/08/18
            "LOCATE": secsgem.RemoteCommand("LOCATE", "locate command", ["CARRIERID"], None), # Mike: 2020/08/18
            "PAUSE": secsgem.RemoteCommand("PAUSE", "pause command", [], None),
            "PORTSTATE": secsgem.RemoteCommand("PORTSTATE", "port state command", ["PORTID", "CARRIERID", "PORTSTATUS"], None, ["LOTID", "QUANTITY"]),
            "PRIORITYUPDATE": secsgem.RemoteCommand("PRIORITYUPDATE", "update cmd priority",["COMMANDID","PRIORITY"],None,["*"]), #chi 24/10/25
            "REASSIGN": secsgem.RemoteCommand("REASSIGN", "reassign command", ["COMMANDID", "CARRIERID", "DESTPORT"], None),
            "RESETALLPORTSTATE": secsgem.RemoteCommand("RESETALLPORTSTATE", "reset all port state command", [], None),
            "RENAME": secsgem.RemoteCommand("RENAME", "rename carrier command", ["CARRIERID", "CARRIERLOC"], None),
            "RESUME": secsgem.RemoteCommand("RESUME", "resume command", [], None),
            "STAGEDELETE": secsgem.RemoteCommand("STAGEDELETE", "stage delete command", [], None, ["STAGEID"]), # Mike: 2021/07/12
            "STOPVEHICLE": secsgem.RemoteCommand("STOPVEHICLE", "stop vehicle command", [], None, ["VEHICLEID"]), # Chi: 2023/03/15
            "SUSPENDCANCEL": secsgem.RemoteCommand("SUSPENDCANCEL", "continue vehicle move", ["VEHICLEID", "DESTPORT"], None), # Chi: 2024/09/20
            "VALIDPERMISSION": secsgem.RemoteCommand("VALIDPERMISSION", "validpermission command", ["CARRIERID", "COMMANDID", "PERMISSIONRESULT"], None, ["*"]),
            "VEHICLERETRYACTION": secsgem.RemoteCommand("VEHICLERETRYACTION", "retry vehicle action", ["VEHICLEID"], None), # Chi: 2024/09/20
            
        })


        #####################################
        # Enhanced Remote Command Declaration
        #####################################
        ''' Enhance Remote command '''
        self.enhance_remote_commands.clear()

        self.enhance_remote_commands.update({
            "CHANGE": secsgem.RemoteCommand("CHANGE", "change command", {"COMMANDINFO":["COMMANDID", "PRIORITY", "REPLACE"], "TRANSFERINFO":["CARRIERID", "SOURCEPORT", "DESTPORT"]}, None, {"STAGEIDLIST":None, "TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY"], "CARRIERTYPE":None, "EXECUTETIME":None}),
            "DUETIMEUPDATE": secsgem.RemoteCommand("DUETIMEUPDATE", "due time update command", {"DUETIMEINFO":["PORTID", "DUETIME"]}, None), # Mike: 2021/12/24
            "EQSTATE": secsgem.RemoteCommand("EQSTATE", "EQ state command", {"EQINFO":["EQID", "EQSTATUS"], "PORTINFO":["PORTID", "CARRIERID", "PORTSTATUS"]}, None, {"PORTINFO":["LOTID", "QUANTITY"]}),
            "PRETRANSFER": secsgem.RemoteCommand("PRETRANSFER", "pre-transfer command", {"COMMANDINFO":["COMMANDID", "PRIORITY", "REPLACE"], "TRANSFERINFO":["CARRIERID", "SOURCEPORT", "DESTPORT"]}, None, {"TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY", "QTIME"]}),
            "STAGE": secsgem.RemoteCommand("STAGE", "stage command", {"STAGEINFO":["STAGEID", "PRIORITY", "REPLACE", "EXPECTEDDURATION", "NOBLOCKINGTIME", "WAITTIMEOUT"], "TRANSFERINFO":["CARRIERID", "SOURCEPORT", "DESTPORT"]}, None, {"TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY"], "VEHICLEID":None}), # Mike: 2021/07/12
            "TRANSFER": secsgem.RemoteCommand("TRANSFER", "transfer command", {"COMMANDINFO":["COMMANDID", "PRIORITY", "REPLACE"], "TRANSFERINFO":["CARRIERID", "SOURCEPORT", "DESTPORT"]}, None, {"TRANSFERINFO_CST":["LOT_ID","CARRIER_TYPE"], "STAGEIDLIST":None, "TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY", "QTIME", "LOT", "LOTNUM"], "EXECUTETIME":None, "CARRIERTYPE":None, "VEHICLEID":None, "OPERATORID":None}),
        })


    #####################################
    #       Variable Callback
    #####################################
    def on_sv_value_request(self, svid, sv):

        if sv.svid == SV_CarrierIDList: # CarrierID*n
            ret=secsgem.SecsVarArray(DI.CARRIERID, self.CarrierIDList)
            return ret
        elif sv.svid == SV_TSCState:

            value=self.TSCState
            return sv.value_type(value)
        elif sv.svid == SV_ActiveCarriers:
            L_ActiveCarriers=[]
            for CarrierID, ActiveCarrier in self.ActiveCarriers.items():
                #CarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.VEHICLEID, DI.CARRIERLOC], [ActiveCarrier["CarrierID"], ActiveCarrier["VehicleID"], ActiveCarrier["CarrierLoc"]])
                CarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.RACKID, DI.SLOTID], [ActiveCarrier["CarrierID"], ActiveCarrier["RackID"], ActiveCarrier["SlotID"]])
                L_ActiveCarriers.append(CarrierInfo_n)
            ret=secsgem.SecsVarArray(DI.ACTIVECARRIERSUNIT, L_ActiveCarriers)
            return ret
        elif sv.svid == SV_EnhancedCarriers:
            L_EnhancedCarriers=[]
            for CarrierID, EnhancedCarrier in self.EnhancedCarriers.items():
                #CarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.VEHICLEID, DI.CARRIERLOC], [ActiveCarrier["CarrierID"], ActiveCarrier["VehicleID"], ActiveCarrier["CarrierLoc"]])
                CarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.RACKID, DI.SLOTID, DI.INSTALLTIME,DI.CARRIERSTATE], [EnhancedCarrier["CarrierID"], EnhancedCarrier["RackID"], EnhancedCarrier["SlotID"], EnhancedCarrier["InstallTime"], EnhancedCarrier["CarrierState"]])
                L_EnhancedCarriers.append(CarrierInfo_n)
            ret=secsgem.SecsVarArray(DI.ENHANCEDCARRIERUNIT, L_EnhancedCarriers)
            return ret
        elif sv.svid == SV_ActiveTransfers:
            try:
                L_ActiveTransfers=[]
                for CommandID, ActiveTransfer in self.ActiveTransfers.items():
                    L_TransferInfo=[]
                    for TransferInfo in ActiveTransfer["TransferInfo"]:
                        TransferInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.SOURCEPORT, DI.DESTPORT], [TransferInfo["CarrierID"], TransferInfo["SourcePort"], TransferInfo["DestPort"]])
                        L_TransferInfo.append(TransferInfo_n)
                    A_TransferInfo=secsgem.SecsVarArray(DI.TRANSFERINFO, L_TransferInfo)
                    CommandInfo=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY, DI.REPLACE, DI.TRANSFERSTATE], [ActiveTransfer["CommandInfo"]["CommandID"], ActiveTransfer["CommandInfo"]["Priority"], ActiveTransfer["CommandInfo"]["Replace"], ActiveTransfer["CommandInfo"]["TransferState"]])
                    TransferCommand_n=secsgem.SecsVarList([DI.COMMANDINFO, DI.TRANSFERCOMMANDUNIT], [CommandInfo, A_TransferInfo])
                    L_ActiveTransfers.append(TransferCommand_n)
                ret=secsgem.SecsVarArray(DI.ACTIVETRANSFERSUNIT, L_ActiveTransfers)
            except:
                traceback.print_exc()
            return ret
        elif sv.svid == SV_ActiveVehicles:
            L_ActiveVehicles=[]
            for key, ActiveVehicle in self.ActiveVehicles.items():
                VehicleInfo_n=secsgem.SecsVarList([DI.VEHICLEID, DI.VEHICLESTATE, DI.VEHICLESOH], [ActiveVehicle["VehicleInfo"]["VehicleID"], ActiveVehicle["VehicleInfo"]["VehicleState"], ActiveVehicle["VehicleInfo"]["SOH"]])
                L_ActiveVehicles.append(VehicleInfo_n)
            ret=secsgem.SecsVarArray(DI.ACTIVEVEHICLESUNIT, L_ActiveVehicles)
            return ret
        elif sv.svid == SV_TransferCompleteInfo: # [TransferInfo, CarrierLoc]*1 for single transfer
            L_TransferCompleteInfo=[]
            TransferCompleteInfo_n=[]
            for TransferCompleteInfo in self.TransferCompleteInfo:
                TransferInfo=secsgem.SecsVarList([DI.CARRIERID, DI.SOURCEPORT, DI.DESTPORT], [TransferCompleteInfo["TransferInfo"]["CarrierID"], TransferCompleteInfo["TransferInfo"]["SourcePort"], TransferCompleteInfo["TransferInfo"]["DestPort"]])
                TransferCompleteInfo_n=secsgem.SecsVarList([DI.TRANSFERINFO, DI.CARRIERLOC], [TransferInfo, TransferCompleteInfo["CarrierLoc"]])
                L_TransferCompleteInfo.append(TransferCompleteInfo_n)
            if self.MDLN  == 'v3_MIRLE':
                return TransferCompleteInfo_n
            else:
                ret=secsgem.SecsVarArray(DI.TRANSFERCOMPLETEINFOUNIT, L_TransferCompleteInfo)
                return ret
        elif sv.svid == SV_TransferInfoList: # [TransferInfo]*n # Mike: 2021/11/01
            L_TransferInfoList=[]
            for TransferInfo in self.TransferInfoList:
                TransferInfoList_n=secsgem.SecsVarList([DI.CARRIERID, DI.SOURCEPORT, DI.DESTPORT], [TransferInfo["CarrierID"], TransferInfo["SourcePort"], TransferInfo["DestPort"]])
                L_TransferInfoList.append(TransferInfoList_n)
            ret=secsgem.SecsVarArray(DI.TRANSFERINFOLISTUNIT, L_TransferInfoList)
            return ret
        elif sv.svid == SV_ActiveRacks:
            L_ActiveRacks=[]
            for key, ActiveRack in self.ActiveRacks.items():
                L_RackState=[]
                for RackState in ActiveRack["RackInfo"]["RackStates"]:
                    RackState_n=secsgem.SecsVarList([DI.PORTID, DI.STATUS, DI.MACHINE], [RackState["SlotID"], RackState["Status"], RackState["Machine"]]) # Mike: 2021/05/11 # Mike: 2022/05/23
                    L_RackState.append(RackState_n)
                A_RackState=secsgem.SecsVarArray(DI.RACKSTATEUNIT, L_RackState)
                # RackInfo_n=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE], [ActiveRack["RackInfo"]["RackID"], A_RackState]) # Mike: 2021/05/11
                RackInfo_n=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE, DI.RACKLOCATION], [ActiveRack["RackInfo"]["RackID"], A_RackState, ActiveRack["RackInfo"]["RackLoc"]]) # Mike: 2021/05/11
                L_ActiveRacks.append(RackInfo_n)
            ret=secsgem.SecsVarArray(DI.ACTIVERACKUNIT, L_ActiveRacks)
            return ret
        elif sv.svid in [SV_eRack1, SV_eRack2, SV_eRack3, SV_eRack4]:
            index=sv.svid - 702
            ActiveRack=self.ActiveRacks[index]
            L_RackState=[]
            for RackState in ActiveRack["RackInfo"]["RackStates"]:
                RackState_n=secsgem.SecsVarList([DI.PORTID, DI.STATUS, DI.MACHINE], [RackState["SlotID"], RackState["Status"], RackState["Machine"]]) # Mike: 2021/05/11 # Mike: 2022/05/23
                L_RackState.append(RackState_n)
            A_RackState=secsgem.SecsVarArray(DI.RACKSTATEUNIT, L_RackState)
            ret=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE], [ActiveRack["RackInfo"]["RackID"], A_RackState])
            return ret

        elif sv.svid == SV_RackInfo:
            L_RackState=[]
            for RackState in self.RackInfo["RackStates"]:
                # RackState_n=secsgem.SecsVarList([DI.PORTID, DI.STATUS], [RackState["SlotID"], RackState["Status"]])
                RackState_n=secsgem.SecsVarList([DI.PORTID, DI.STATUS, DI.MACHINE], [RackState["SlotID"], RackState["Status"], RackState["Machine"]]) # Mike: 2021/05/11 # Mike: 2022/05/23
                L_RackState.append(RackState_n)
            A_RackState=secsgem.SecsVarArray(DI.RACKSTATEUNIT, L_RackState)
            #ret=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE], [ActiveRack["RackInfo"]["RackID"], A_RackState])
            #ret=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE], [self.RackInfo["RackID"], A_RackState]) # Mike: 2021/05/11
            ret=secsgem.SecsVarList([DI.RACKID, DI.RACKSTATE, DI.RACKLOCATION], [self.RackInfo["RackID"], A_RackState, self.RackInfo["RackLoc"]]) # Mike: 2021/05/11
            return ret
        
        elif sv.svid == SV_DoorState:#peter 240705
            ret=self.DoorState
            return ret
        elif sv.svid == SV_FromPort:
            #ret=self.transferPort
            ret=self.FromPort #chocp fix
            return ret
        elif sv.svid == SV_TransferPort:
            #ret=self.transferPort
            ret=self.TransferPort #chocp fix
            return ret
            '''elif sv.svid == SV_TransferPortList: # TransferPort*1 for single transfer
                ret=secsgem.SecsVarArray(DI.TRANSFERPORT, self.TransferPortList)
                return ret'''
        elif sv.svid == SV_ExecuteTime: #chocp add 2023/7/21
            value=self.ExecuteTime
            return sv.value_type(value)
        elif sv.svid == SV_CommandID:
            value=self.CommandID
            return sv.value_type(value)
        elif sv.svid == SV_CommandIDList: # CommandID*n
            ret=secsgem.SecsVarArray(DI.COMMANDID, self.CommandIDList)
            return ret
        elif sv.svid == SV_TransferInfo: # Mike: 2021/08/10
            ret=secsgem.SecsVarList([DI.CARRIERID, DI.SOURCEPORT, DI.DESTPORT], [self.TransferInfo["CarrierID"], self.TransferInfo["SourcePort"], self.TransferInfo["DestPort"]])
            return ret
        elif sv.svid == SV_VehicleInfo: # VehicleID, VehicleState
            ret=secsgem.SecsVarList([DI.VEHICLEID, DI.VEHICLESTATE], [self.VehicleInfo["VehicleID"], self.VehicleInfo["VehicleState"]])
            return ret
        elif sv.svid == SV_CommandInfo: # CommandID, Priority, Replace
            ret=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY, DI.REPLACE], [self.CommandInfo["CommandID"], self.CommandInfo["Priority"], self.CommandInfo["Replace"]])
            return ret
        elif sv.svid == SV_ResultCode: # U2
            value=self.ResultCode
            return sv.value_type(value)
        elif sv.svid == SV_VehicleID:
            value=self.VehicleID
            return sv.value_type(value)
        elif sv.svid == SV_CarrierID: # 'UNKNOWN[EqpName][Seq]'
            value=self.CarrierID
            return sv.value_type(value)
        elif sv.svid == SV_CarrierLoc:
            value=self.CarrierLoc
            return sv.value_type(value)
        elif sv.svid == SV_PortID:
            value=self.PortID
            return sv.value_type(value)
        elif sv.svid == SV_CommandType:
            value=self.CommandType
            return sv.value_type(value)
        elif sv.svid == SV_SourcePort:
            value=self.SourcePort
            return sv.value_type(value)
        elif sv.svid == SV_DestPort:
            value=self.DestPort
            return sv.value_type(value)
        elif sv.svid == SV_Priority:
            value=self.Priority
            return sv.value_type(value)
        elif sv.svid == SV_RackID:
            value=self.RackID
            return sv.value_type(value)
        elif sv.svid == SV_SlotID:
            value=self.SlotID
            return sv.value_type(value)
        elif sv.svid == SV_SlotStatus:
            value=self.SlotStatus
            return sv.value_type(value)
        elif sv.svid == SV_VehicleSOH: # Mike: 2021/05/11
            value=self.VehicleSOH
            return sv.value_type(value)
        elif sv.svid == SV_RackLocation: # Mike: 2021/05/11
            value=self.RackLocation
            return sv.value_type(value)
            '''elif sv.svid == SV_RackPortStatus:
                value=self.RackPortStatus
                return sv.value_type(value)'''
        elif sv.svid == SV_RackGroup: # Richard:2024/08/16
            value=self.RackGroup
            return sv.value_type(value)
        elif sv.svid == SV_LocateResult: # Mike: 2020/08/18
            value=self.LocateResult
            return sv.value_type(value)
        elif sv.svid == SV_SendBy:
            value=self.SendBy
            return sv.value_type(value) #chocp add for ASE
        elif sv.svid == SV_EQID: # Mike: 2020/11/11
            value=self.EQID
            return sv.value_type(value)
        elif sv.svid == SV_StageID: # Mike: 2021/07/22
            value=self.StageID
            return sv.value_type(value)
        elif sv.svid == SV_ALID: # 2024/07/12
            value=self.ALID
            return sv.value_type(value)
        elif sv.svid == SV_ALTX: # Mike: 2021/11/08
            value=self.ALTX
            return sv.value_type(value)
        elif sv.svid == SV_ALSV: # Mike: 2021/11/08
            value=self.ALSV
            return sv.value_type(value)
        elif sv.svid == SV_UnitType: # Mike: 2021/11/29
            value=self.UnitType
            return sv.value_type(value)
        elif sv.svid == SV_UnitID: # Mike: 2021/11/29
            value=self.UnitID
            return sv.value_type(value)
        elif sv.svid == SV_Level: # Mike: 2021/12/01
            value=self.Level
            return sv.value_type(value)
        elif sv.svid == SV_CarrierType: # chocp: 2022/1/2
            value=self.CarrierType
            return sv.value_type(value)
        elif sv.svid == SV_SubCode: # Chi: 2022/06/17
            value=self.SubCode
            return sv.value_type(value)
        elif sv.svid == SV_TransferState: # Chi: 2022/12/05
            value=self.TransferState
            return sv.value_type(value)
        elif sv.svid == SV_Routes: # Mike: 2023/05/17
            value=self.Routes
            return sv.value_type(value)
        elif sv.svid == SV_IDReadStatus: # 2024/07/15
            value=self.IDReadStatus
            return sv.value_type(value)
        elif sv.svid == SV_BatteryValue: # 2024/07/15
            value=self.BatteryValue
            return sv.value_type(value)
        elif sv.svid == SV_VehicleLastPosition: # 2024/07/15
            value=self.VehicleLastPosition
            return sv.value_type(value)
        elif sv.svid == SV_NearPort: # 2024/07/15
            value=self.NearPort
            return sv.value_type(value)
        elif sv.svid == SV_VehiclePose: # 2024/10/02
            value=self.VehiclePose
            return sv.value_type(value)
        elif sv.svid == SV_PointID: # 2024/10/02
            value=self.PointID
            return sv.value_type(value)
        elif sv.svid == SV_VehicleState: # 2024/08/28
            value=self.VehicleInfo["VehicleState"]
            return sv.value_type(value)
        elif sv.svid == SV_VehicleLastState: # 2024/08/28
            value=self.VehicleInfo["VehicleLastState"]
            return sv.value_type(value)
        elif sv.svid == SV_CurrentPortStates: 
            L_CurrentPortStates=[]
            for CurrentPortState in self.CurrentPortStates:
                CurrentPortState_n=secsgem.SecsVarList([DI.PORTID, DI.PORTTRANSFERSTATE], [CurrentPortState["PortID"], CurrentPortState["PortTransferState"]])
                L_CurrentPortStates.append(CurrentPortState_n)
            ret=secsgem.SecsVarArray(DI.CURRENTPORTSTATEUNIT, L_CurrentPortStates)
            return ret
        elif sv.svid == SV_AlarmsSetDescription: 
            L_AlarmsSetDescription=[]
            for key, EnhancedALID in self.AlarmsSetDescription.items():
                if not EnhancedALID["ALID"]:
                    continue
                UnitInfo_n=secsgem.SecsVarList([DI.VEHICLEID, DI.VEHICLESTATE], [EnhancedALID["UnitInfo"]["VehicleID"], EnhancedALID["UnitInfo"]["VehicleState"]])
                EnhancedALID_n=secsgem.SecsVarList([DI.ALID, DI.UNITINFO, DI.ALARMTEXT], [EnhancedALID["ALID"], UnitInfo_n, EnhancedALID["AlarmText"]])
                L_AlarmsSetDescription.append(EnhancedALID_n)
            ret=secsgem.SecsVarArray(DI.ACTIVEVEHICLESUNIT, L_AlarmsSetDescription)
            return ret
        

        '''
        def on_dv_value_request(self, dvid, dv):
        if dv.dvid=1:
            dv_list=secsgem.SecsVarList([
                secsgem.AAA,
            ])
            dv_list.AAA=AAA
            return dv_list
        '''

    #####################################
    #      Stream Function Callback
    #####################################
    def _on_s02f15(self, handler, packet):
        return self.stream_function(9, 5)() # Function Disable (New EC)

    def _on_s06f23(self, handler, packet):
        return self.stream_function(6, 0)() # Function Disable (spool)

    def _on_s02f17(self, handler, packet):
        """Callback handler for Stream 2, Function 17, Request online

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        if self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"]:
            return self.stream_function(2, 0)()

        del handler, packet  # unused parameters

        TIME=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]

        return self.stream_function(2, 18)(TIME)

    def _on_s02f31(self, handler, packet):
        """Callback handler for Stream 2, Function 31, Request online

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        if self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"]:
            return self.stream_function(2, 0)()

        del handler  # unused parameters

        message=self.secs_decode(packet)
        TIME=message.get() # TIME='YYYYmmddHHMMSSXX'

        # set system date
        if len(TIME) not in [14, 16]:
            return self.stream_function(2, 32)(secsgem.TIACK.ERROR)

        YY=TIME[0:4]
        mm=TIME[4:6]
        dd=TIME[6:8]
        HH=TIME[8:10]
        MM=TIME[10:12]
        SS=TIME[12:14]
        XX=TIME[14:16] if len(TIME) == 16 else '00'

        TIME="{}{}{} {}:{}:{}.{}".format(YY,mm,dd,HH,MM,SS,XX)

        print ("set time: {}".format(TIME))
        
        def set_system_time(TIME):
            try:
                password='gsi5613686'
                command=['sudo', '-S', 'timedatectl', 'set-ntp', 'false']
                p=subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.stdin.write((password + '\n').encode())
                output, error=p.communicate()
                subprocess.call(['sudo', 'date', '-s', TIME])
            except:
                command=['sudo', '-S', 'timedatectl', 'set-ntp', 'true']
                p=subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.stdin.write((password + '\n').encode())
                output, error=p.communicate()
                traceback.print_exc()  

        time_thread=threading.Thread(target=set_system_time, args=(TIME,))
        time_thread.start()
        return self.stream_function(2, 32)(secsgem.TIACK.OK)

        commands.getoutput("sudo timedatectl set-ntp off")
        msg=commands.getoutput('sudo date -s "'+TIME+'"')

        if "cst" not in msg:
            commands.getoutput("sudo timedatectl set-ntp on")
            return self.stream_function(2, 32)(secsgem.TIACK.ERROR)

        return self.stream_function(2, 32)(secsgem.TIACK.OK)

    def set_alarm(self, alid, alarmlevel =''): # Mike: 2021/11/26
        """The list of the alarms

        :param alid: Alarm id
        :type alid: str/int
        """
        if alid not in self.alarms:
            raise ValueError("Unknown alarm id {}".format(alid))

        '''if not self.alarms[alid].set:
            return'''

        if self.alarms[alid].enabled:
            if not self._spool_enable and (self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"] or not self.communicationState.isstate("COMMUNICATING")):
                pass
            else:
                try:
                    self.send_prime_message(self.stream_function(5, 1)({"ALCD": self.alarms[alid].code | secsgem.ALCD.ALARM_SET , \
                        "ALID": alid, "ALTX": self.alarms[alid].text}))
                except Exception as err:
                    self.send_stream_function(self.stream_function(9, 9)())
                    raise Exception(err)
        
        self.alarms[alid].set=True
        if self.MDLN  == 'v3_MIRLE':
            if alarmlevel == 'Warning':
                self.trigger_collection_events(503) 
            else:
                self.trigger_collection_events([self.alarms[alid].ce_on])  
        else:
            self.trigger_collection_events([self.alarms[alid].ce_on])  

    def clear_alarm(self, alid, alarmlevel =''): # Mike: 2021/11/26
        """The list of the alarms

        :param alid: Alarm id
        :type alid: str/int
        """
        if alid not in self.alarms:
            raise ValueError("Unknown alarm id {}".format(alid))

        '''if not self.alarms[alid].set:
            return'''

        if self.alarms[alid].enabled:
            if not self._spool_enable and (self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"] or not self.communicationState.isstate("COMMUNICATING")):
                pass
            else:
                try:
                    self.send_prime_message(self.stream_function(5, 1)({"ALCD": self.alarms[alid].code , "ALID": alid, "ALTX": self.alarms[alid].text}))
                except Exception as err:
                    self.send_stream_function(self.stream_function(9, 9)())
                    raise Exception(err)

        self.alarms[alid].set=False
        if self.MDLN  == 'v3_MIRLE':
            if alarmlevel == 'Warning':
                self.trigger_collection_events(504) 
            else:
                self.trigger_collection_events([self.alarms[alid].ce_off])  
        else:
            self.trigger_collection_events([self.alarms[alid].ce_off])  

    #####################################
    #      Remote Command Callback
    #####################################
    def _on_rcmd_ABORT(self, COMMANDID, system, ack_params):
        # print("get abort cmd, param:{}\n", COMMANDID)
        #print("get abort cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if COMMANDID not in self.ActiveTransfers:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='abort'
        obj['CommandID']=COMMANDID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.COMMANDID=COMMANDID

        self.ResultCode=2
        if self.MDLN  == 'v3_MIRLE':
            self.send_response(self.stream_function(2,42)([4]), system)
        else:
            self.send_response(self.stream_function(2,42)([0]), system)    
        remotecmd_queue.append(obj)

    def _on_rcmd_ASSERT(self, REQUEST, COMMANDID, CARRIERID, DESTPORT, RESULT, system, ack_params, **kwargs): # Mike: 2020/07/29
        #print("get assert cmd, param:{}, {}, {}, {}, {}\n".format(REQUEST, COMMANDID, CARRIERID, DESTPORT, RESULT))
        #print("get assert cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        ''' #9/30 chocp
        if COMMANDID not in self.ActiveTransfers:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return
        '''

        obj={}
        obj['remote_cmd']='assert'
        obj['REQUEST']=REQUEST
        obj['COMMANDID']=COMMANDID
        obj['CARRIERID']=CARRIERID
        obj['DESTPORT']=DESTPORT
        obj['RESULT']=RESULT
        for key, value in kwargs.items():
            obj[key]=value
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)
        
    def _on_rcmd_VALIDPERMISSION(self, CARRIERID, COMMANDID, PERMISSIONRESULT, system, ack_params, **kwargs): 
        #print("get assert cmd, param:{}, {}, {}, {}, {}\n".format(REQUEST, COMMANDID, CARRIERID, DESTPORT, RESULT))
        #print("get assert cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        obj={}
        obj['remote_cmd']='assert'
        obj['REQUEST']='None'
        obj['COMMANDID']=COMMANDID
        obj['CARRIERID']=CARRIERID
        obj['DESTPORT']='None'
        obj['RESULT']=PERMISSIONRESULT
        for key, value in kwargs.items():
            obj[key]=value
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_ASSIGNABLE(self, VEHICLEID, system, ack_params): #8.25.12-2

        if VEHICLEID and VEHICLEID not in self.ActiveVehicles:
            ack_params.append(['VEHICLEID', 2])
            print("\VehicleID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='assignable'
        obj['VehicleID']=VEHICLEID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj) #chocp fix

    def _on_rcmd_ASSGINLOT(self, CARRIERID, DESTPORT, system, ack_params): #8.25.12-2

        if CARRIERID and CARRIERID not in self.ActiveCarriers:
            ack_params.append(['CARRIER', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='assginlot'
        obj['CARRIERID']=CARRIERID
        obj['DESTPORT']=DESTPORT 
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj) #chocp fix

    def _on_rcmd_ASSOCIATE(self, RACKID, PORTID, CARRIERID, ASSOCIATEDATA, system, ack_params, **kwargs):
        #print("get associate cmd, param:{}, {}, {}, {}, {}\n".format(RACKID, PORTID, CARRIERID, ASSOCIATEDATA, kwargs))
        #print("get associate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        if CARRIERID and CARRIERID not in self.ActiveCarriers:
            ack_params.append(['CARRIER', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='associate'
        obj['RACKID']=self.ActiveCarriers[CARRIERID]['RackID']
        obj['PORTID']=self.ActiveCarriers[CARRIERID]['SlotID']
        obj['CARRIERID']=CARRIERID
        obj['ASSOCIATEDATA']=ASSOCIATEDATA #need fix
        for key, value in kwargs.items():
            obj[key]=value
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj) #chocp fix

    def _on_rcmd_BINDING(self, CARRIERID, LOTID, NEXTSTEP, EQLIST, PRIORITY, system, ack_params):
        #print("get binding cmd, param:{}, {}, {}, {}, {}\n", CARRIERID, LOTID, NEXTSTEP, EQLIST, PRIORITY)
        #print("get binding cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='binding'
        obj['CARRIERID']=CARRIERID
        obj['LOTID']=LOTID
        obj['NEXTSTEP']=NEXTSTEP
        obj['EQLIST']=EQLIST
        obj['PRIORITY']=PRIORITY
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_CALL(self, VEHICLEID, DESTPORT, system, ack_params, **kwargs):
        #print("get binding cmd, param:{}, {}, {}, {}, {}\n", CARRIERID, LOTID, NEXTSTEP, EQLIST, PRIORITY)
        #print("get binding cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        
        obj={}
        obj['remote_cmd']='call'
        obj['VehicleID']=VEHICLEID
        obj['Destport']=DESTPORT
        obj['CommandID']=kwargs.get('COMMANDID', '')
        obj['NoBlockingTime']=int(kwargs.get('NOBLOCKINGTIME','')) if kwargs.get('NOBLOCKINGTIME','') else 0
        obj['WaitTimeout']=int(kwargs.get('WAITTIMEOUT','')) if kwargs.get('WAITTIMEOUT','') else 0
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        #self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_CANCEL(self, COMMANDID, system, ack_params):
        #print("get cancel cmd, param:{}\n", COMMANDID)
        #print("get cancel cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if COMMANDID not in self.ActiveTransfers:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='cancel'
        obj['CommandID']=COMMANDID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.ResultCode=1
        if self.MDLN  == 'v3_MIRLE':
            self.send_response(self.stream_function(2,42)([4]), system)
        else:
            self.send_response(self.stream_function(2,42)([0]), system)   
        remotecmd_queue.append(obj)
    
    def _on_rcmd_DOOROPENREPLY(self, VEHICLEID, system, ack_params ,**kwargs):
        #peter 240705,test call door for K11
        if VEHICLEID:
            obj={}
            obj['remote_cmd']='dooropenreply'
            obj['VehicleID']=VEHICLEID
            for key, value in kwargs.items():#kelvin 2023/10/12 
                obj[key]=value 
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            self.send_response(self.stream_function(2,42)([0]), system)
            remotecmd_queue.append(obj)
        else:
            ack_params.append(['VEHICLEID', 2])
            print("\nVEHICLEID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

    def _on_rcmd_EVACUATION(self, system, ack_params, SITUATION, **kwargs): #Chi 2023/03/15
        
        obj={}
        obj['remote_cmd']='evacuation'
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        obj['Situation']=SITUATION
        obj['VehicleID']=kwargs.get('VEHICLEID', '')
        if obj['VehicleID']:
            if obj['VehicleID'] not in self.ActiveVehicles:
                ack_params.append(['VEHICLEID', 2])
                print("\nVEHICLEID not found.\n")
                self.send_response(self.stream_function(2,42)([3, ack_params]), system)
                return
        
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_INFOUPDATE(self, CARRIERID, system, ack_params, **kwargs): # Mike: 2021/07/27
        #print("get locate cmd, param:{}\n", COMMANDID)
        #print("get locate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if CARRIERID and CARRIERID not in self.ActiveCarriers:
            ack_params.append(['CARRIER', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='infoupdate'
        obj['CarrierID']=CARRIERID
        for key, value in kwargs.items():
            obj[key]=value
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_LOCATE(self, CARRIERID, system, ack_params): # Mike: 2020/08/18
        #print("get locate cmd, param:{}\n", COMMANDID)
        #print("get locate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if CARRIERID and CARRIERID not in self.ActiveCarriers:
            ack_params.append(['CARRIERID', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return

        obj={}
        obj['remote_cmd']='locate'
        obj['CARRIERID']=CARRIERID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([4]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_PAUSE(self, system, ack_params):
        #print("get pause cmd\n")
        #print("get pause cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='pause'
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_PORTSTATE(self, PORTID, CARRIERID, PORTSTATUS, system, ack_params, **kwargs):
        #print("get associate cmd, param:{}, {}, {}, {}, {}\n".format(RACKID, PORTID, CARRIERID, ASSOCIATEDATA, kwargs))
        #print("get associate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='PortState'
        obj['PortID']=PORTID
        obj['CarrierID']=CARRIERID
        obj['PortStatus']=PORTSTATUS
        for key, value in kwargs.items():
            obj[key]=value
            
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj) #chocp fix

    def _on_rcmd_PRIORITYUPDATE(self, COMMANDID, PRIORITY, system, ack_params, **kwargs):
        #print("get associate cmd, param:{}, {}, {}, {}, {}\n".format(RACKID, PORTID, CARRIERID, ASSOCIATEDATA, kwargs))
        #print("get associate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='priorityupdate'
        obj['CommandID']=COMMANDID
        obj['Priority']=PRIORITY
        for key, value in kwargs.items():
            obj[key]=value
            
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        #self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj) #chocp fix
    def _on_rcmd_REASSIGN(self, COMMANDID, CARRIERID, DESTPORT, system, ack_params):
        #print("get transfer cmd, param:{}, {}, {}\n", COMMANDINFO, TRANSFERINFO, STAGEIDLIST)
        #print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        obj={}
        obj['remote_cmd']='host_reassign' #chocp fix
        obj['CommandID']=COMMANDID
        obj['CarrierID']=CARRIERID
        obj['DestPort']=DESTPORT
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        #print(obj)
        #self.send_response(self.stream_function(2,50)([4]), system) #2021/1/17 chocp add back for ASE MCS layer
        remotecmd_queue.append(obj)
    
    def _on_rcmd_RENAME(self, CARRIERID, CARRIERLOC, system, ack_params):
        #print("get rename cmd\n")
        #print("get rename cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='rename'
        obj['CarrierID']=CARRIERID
        obj['CarrierLoc']=CARRIERLOC
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_RENAME(self, CARRIERID, CARRIERLOC, system, ack_params):
        #print("get rename cmd\n")
        #print("get rename cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='rename'
        obj['CarrierID']=CARRIERID
        obj['CarrierLoc']=CARRIERLOC
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_RESETALLPORTSTATE(self, system, ack_params):
        #print("get pause cmd\n")
        #print("get pause cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='ResetAllPortState'
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_RESUME(self, system, ack_params):
        #print("get resume cmd\n")
        #print("get resume cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='resume'
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_STAGEDELETE(self, system, ack_params, STAGEID=''): # Mike: 2020/08/18
        #print("get stage delete cmd, param:{}\n", STAGEID)
        #print("get stage delete cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        obj={}
        obj['remote_cmd']='stagedelete'
        obj['StageID']=STAGEID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([4]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_SUSPENDCANCEL(self, VEHICLEID, DESTPORT, system, ack_params, **kwargs):
        
        obj={}
        obj['remote_cmd']='suspendcancel'
        obj['VehicleID']=VEHICLEID
        obj['DESTPORT']=DESTPORT
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        if obj['VehicleID'] not in self.ActiveVehicles:
            ack_params.append(['VEHICLEID', 2])
            print("\nVEHICLEID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)
        
    def _on_rcmd_VEHICLERETRYACTION(self, VEHICLEID, system, ack_params, **kwargs):
        
        obj={}
        obj['remote_cmd']='retry'
        obj['VehicleID']=VEHICLEID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        if obj['VehicleID'] not in self.ActiveVehicles:
            ack_params.append(['VEHICLEID', 2])
            print("\nVEHICLEID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
            return
        #self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)
    def _on_rcmd_STOPVEHICLE(self, system, ack_params, **kwargs): #Chi 2023/03/15

        obj={}
        obj['remote_cmd']='stopvehicle'
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        obj['VehicleID']=kwargs.get('VEHICLEID', '')
        if obj['VehicleID']:
            if obj['VehicleID'] not in self.ActiveVehicles:
                ack_params.append(['VEHICLEID', 2])
                print("\nVEHICLEID not found.\n")
                self.send_response(self.stream_function(2,42)([3, ack_params]), system)
                return
        self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_ercmd_CHANGE(self, COMMANDINFO, TRANSFERINFO, system, ack_params, **kwargs):
        #print("get transfer cmd, param:{}, {}, {}\n", COMMANDINFO, TRANSFERINFO, STAGEIDLIST)
        #print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        while not self.transfer_lock.acquire():
            sleep(0.1)
        try:
            '''print('hahaha', COMMANDINFO[0][0][1], self.ActiveTransfers)
                if COMMANDINFO[0][0][1] not in ['', '0'] and COMMANDINFO[0][0][1] in self.ActiveTransfers:
                ack_params.append(['COMMANDID', 2])
                print("\COMMANDID error.\n")
                self.send_response(self.stream_function(2,42)([3, ack_params]), system)
                return'''

            if COMMANDINFO[0][1][1] > 100:
                ack_params.append(['PRIORITY', 2])
                print("\PRIORITY error.\n")
                self.send_response(self.stream_function(2,50)([3, ack_params]), system)
                return

            self.ResultCode=0
            self.CommandID=COMMANDINFO[0][0][1]
            self.CommandInfo={}
            self.CommandInfo["CommandID"]=COMMANDINFO[0][0][1]
            self.CommandInfo["Priority"]=COMMANDINFO[0][1][1]
            self.CommandInfo["Replace"]=COMMANDINFO[0][2][1]

            #D_TransferInfo={} #chocp fix
            self.TransferInfo={}
            self.TransferInfo["CarrierID"]=TRANSFERINFO[0][0][1]
            self.TransferInfo["SourcePort"]=TRANSFERINFO[0][1][1]
            self.TransferInfo["DestPort"]=TRANSFERINFO[0][2][1]

            self.TransferCompleteInfo=[{"TransferInfo":self.TransferInfo, "CarrierLoc":"aaaa"}] #chocp fix
            self.CarrierLoc="aaaa"
            self.CarrierID=TRANSFERINFO[0][0][1]
            self.SourcePort=TRANSFERINFO[0][1][1]
            self.DestPort=TRANSFERINFO[0][2][1]
            self.TransferPortList=[self.SourcePort]

            self.TransferInfoList=[] # Mike: 2021/07/27
            for Trans in TRANSFERINFO:
                Transfer={}
                Transfer["CarrierID"]=Trans[0][1]
                Transfer["SourcePort"]=Trans[1][1]
                Transfer["DestPort"]=Trans[2][1]
                for t in Trans[3:]:
                    if t[0] == "CARRIERTYPE":
                        Transfer["CarrierType"]=t[1]
                    elif t[0] == "LOTID":
                        Transfer["LotID"]=t[1]
                    elif t[0] == "LOTTYPE":
                        Transfer["LotType"]=t[1]
                    elif t[0] == "CUSTID":
                        Transfer["CustID"]=t[1]
                    elif t[0] == "PRODUCT":
                        Transfer["Product"]=t[1]
                    elif t[0] == "QUANTITY":
                        Transfer["Quantity"]=t[1]
                    else:
                        pass
                self.TransferInfoList.append(Transfer)


            #D_TransferInfo={} #chocp fix
            self.stageIDlist=kwargs.get("STAGEIDLIST", [[]])[0]

            #self.ActiveTransfers[self.CommandID]={'CommandInfo': self.CommandInfo, 'TransferInfo': self.TransferInfoList}
            #print(self.ActiveTransfers)
            #self.add_transfer_cmd(self.CommandID, {'CommandInfo': self.CommandInfo, 'TransferInfo': self.TransferInfoList})

            obj={}
            obj['remote_cmd']='host_change' #chocp fix
            obj['commandinfo']=self.CommandInfo
            # obj['transferinfo']=self.TransferInfo # Mike: 2021/07/27
            obj['transferinfolist']=self.TransferInfoList # Mike: 2021/07/27
            obj['stageIDlist']=self.stageIDlist
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            obj['CARRIERTYPE']=kwargs.get('CARRIERTYPE', [''])
            obj['EXECUTETIME']=kwargs.get('EXECUTETIME', [''])
            #print(obj)
            #self.send_response(self.stream_function(2,50)([4]), system) #2021/1/17 chocp add back for ASE MCS layer
            remotecmd_queue.append(obj)
        except:
            print("\Exception found in transfer.\n")
            self.send_response(self.stream_function(2,0)(), system)
            return
        finally:
            self.transfer_lock.release()

    def _on_ercmd_DUETIMEUPDATE(self, DUETIMEINFO, system, ack_params, **kwargs): # Mike: 2021/12/24
        #print("get transfer cmd, param:{}, {}, {}\n", COMMANDINFO, TRANSFERINFO, STAGEIDLIST)
        #print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        self.DueTimeInfoList=[] # Mike: 2021/07/27
        for DueTimes in DUETIMEINFO:
            DueTime={}
            DueTime["PortID"]=DueTimes[0][1]
            DueTime["DueTime"]=DueTimes[1][1]
            self.DueTimeInfoList.append(DueTime)

        obj={}
        obj['remote_cmd']='duetimeupdate' #chocp fix
        obj['duetimeinfolist']=self.DueTimeInfoList
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        #print(obj)
        #self.send_response(self.stream_function(2,50)([4]), system) #2021/1/17 chocp add back for ASE MCS layer
        remotecmd_queue.append(obj)

    def _on_ercmd_EQSTATE(self, EQINFO, PORTINFO, system, ack_params): # Mike: 2020/08/18, chocp 2022/8/30
        #print("get EQ state cmd, param:{}, {}\n", EQINFO, PORTINFO)
        #print("get EQ state cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        self.EQInfo={}
        self.EQInfo["EQID"]=EQINFO[0][0][1]
        self.EQInfo["EQStatus"]=EQINFO[0][1][1]

        self.PortInfoList=[] # Mike: 2022/07/29
        for Port in PORTINFO:
            PortInfo={}
            PortInfo["PortID"]=Port[0][1]
            PortInfo["CarrierID"]=Port[1][1]
            PortInfo["PortStatus"]=Port[2][1]
            for p in Port[3:]:
                if p[0] == "LOTID":
                    PortInfo["LotID"]=p[1]
                elif p[0] == "QUANTITY":
                    PortInfo["Quantity"]=p[1]
                elif p[0] == "CARRIERTYPE": #from 2023/10/12
                    PortInfo["CarrierType"]=p[1]
                else:
                    pass
            self.PortInfoList.append(PortInfo)

        obj={}
        obj['remote_cmd']='EQState'
        obj['EQinfo']=self.EQInfo
        obj['portinfolist']=self.PortInfoList
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        self.send_response(self.stream_function(2,50)([4]), system)
        remotecmd_queue.append(obj)

    def _on_ercmd_PRETRANSFER(self, COMMANDINFO, TRANSFERINFO, system, ack_params, **kwargs):
        #print("get transfer cmd, param:{}, {}, {}\n", COMMANDINFO, TRANSFERINFO, STAGEIDLIST)
        #print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        while not self.transfer_lock.acquire():
            sleep(0.1)
        try:
        
            '''if COMMANDINFO[0][0][1] not in ['', '0'] and COMMANDINFO[0][0][1] in self.ActiveTransfers:
                ack_params.append(['COMMANDID', 2])
                print("\COMMANDID error.\n")
                self.send_response(self.stream_function(2,42)([3, ack_params]), system)
                return'''

            if COMMANDINFO[0][1][1] > 101:
                ack_params.append(['PRIORITY', 2])
                print("\PRIORITY error.\n")
                self.send_response(self.stream_function(2,50)([3, ack_params]), system)
                return

            self.ResultCode=0
            self.CommandID=COMMANDINFO[0][0][1]
            self.CommandInfo={}
            self.CommandInfo["CommandID"]=COMMANDINFO[0][0][1]
            self.CommandInfo["Priority"]=COMMANDINFO[0][1][1]
            self.CommandInfo["Replace"]=COMMANDINFO[0][2][1]

            #D_TransferInfo={} #chocp fix
            self.TransferInfo={}
            self.TransferInfo["CarrierID"]=TRANSFERINFO[0][0][1]
            self.TransferInfo["SourcePort"]=TRANSFERINFO[0][1][1]
            self.TransferInfo["DestPort"]=TRANSFERINFO[0][2][1]

            self.TransferInfoList=[] # Mike: 2021/07/27
            for Trans in TRANSFERINFO:
                Transfer={}
                Transfer["CarrierID"]=Trans[0][1]
                Transfer["SourcePort"]=Trans[1][1]
                Transfer["DestPort"]=Trans[2][1]
                for t in Trans[3:]:
                    if t[0] == "CARRIERTYPE":
                        Transfer["CarrierType"]=t[1]
                    elif t[0] == "LOTID":
                        Transfer["LotID"]=t[1]
                    elif t[0] == "LOTTYPE":
                        Transfer["LotType"]=t[1]
                    elif t[0] == "CUSTID":
                        Transfer["CustID"]=t[1]
                    elif t[0] == "PRODUCT":
                        Transfer["Product"]=t[1]
                    elif t[0] == "QUANTITY":
                        Transfer["Quantity"]=t[1]
                    elif t[0] == "QTIME":
                        Transfer["QTime"]=t[1]
                    else:
                        pass
                self.TransferInfoList.append(Transfer)

            #self.add_transfer_cmd(self.CommandID, {'CommandInfo': self.CommandInfo, 'TransferInfo': self.TransferInfoList})

            obj={}
            obj['remote_cmd']='pre_transfer' #chocp fix
            obj['commandinfo']=self.CommandInfo
            # obj['transferinfo']=self.TransferInfo # Mike: 2021/07/27
            obj['transferinfolist']=self.TransferInfoList # Mike: 2021/07/27
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            #print(obj)
            #self.send_response(self.stream_function(2,50)([4]), system) #2021/1/17 chocp add back for ASE MCS layer
            remotecmd_queue.append(obj)
        except:
            print("\Exception found in transfer.\n")
            self.send_response(self.stream_function(2,0)(), system)
            return
        finally:
            self.transfer_lock.release()

    def _on_ercmd_STAGE(self, STAGEINFO, TRANSFERINFO, system, ack_params, **kwargs): # Mike: 2020/08/18
        #print("get stage cmd, param:{}, {}\n", STAGEINFO, TRANSFERINFO)
        #print("get stage cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if STAGEINFO[0][1][1] > 101:
            ack_params.append(['PRIORITY', 2])
            print("\PRIORITY error.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
            return

        if not STAGEINFO[0][0][1]:
            ack_params.append(['STAGEID', 2])
            print("\STAGEID error.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
            return

        #D_TransferInfo={} #chocp fix
        self.StageInfo={}
        self.StageInfo["StageID"]=STAGEINFO[0][0][1]
        self.StageInfo["Priority"]=STAGEINFO[0][1][1]
        self.StageInfo["Replace"]=STAGEINFO[0][2][1]
        self.StageInfo["ExpectedDuration"]=STAGEINFO[0][3][1]
        self.StageInfo["NoBlockingTime"]=STAGEINFO[0][4][1]
        self.StageInfo["WaitTimeout"]=STAGEINFO[0][5][1]

        #D_TransferInfo={} #chocp fix
        self.TransferInfo={}
        self.TransferInfo["CarrierID"]=TRANSFERINFO[0][0][1]
        self.TransferInfo["SourcePort"]=TRANSFERINFO[0][1][1]
        self.TransferInfo["DestPort"]=TRANSFERINFO[0][2][1]

        self.TransferInfoList=[] # Mike: 2021/07/27
        for Trans in TRANSFERINFO:
            Transfer={}
            Transfer["CarrierID"]=Trans[0][1]
            Transfer["SourcePort"]=Trans[1][1]
            Transfer["DestPort"]=Trans[2][1]
            for t in Trans[3:]:
                if t[0] == "CARRIERTYPE":
                    Transfer["CarrierType"]=t[1]
                elif t[0] == "LOTID":
                    Transfer["LotID"]=t[1]
                elif t[0] == "LOTTYPE":
                    Transfer["LotType"]=t[1]
                elif t[0] == "CUSTID":
                    Transfer["CustID"]=t[1]
                elif t[0] == "PRODUCT":
                    Transfer["Product"]=t[1]
                elif t[0] == "QUANTITY":
                    Transfer["Quantity"]=t[1]
                else:
                    pass
            self.TransferInfoList.append(Transfer)

        obj={}
        obj['remote_cmd']='stage'
        obj['stageinfo']=self.StageInfo
        # obj['transferinfo']=self.TransferInfo # Mike: 2021/07/27
        obj['transferinfolist']=self.TransferInfoList # Mike: 2021/07/27
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        obj['VEHICLEID']=kwargs.get('VEHICLEID', [''])
        # self.send_response(self.stream_function(2,50)([4]), system)
        remotecmd_queue.append(obj)

    def _on_ercmd_TRANSFER(self, COMMANDINFO, TRANSFERINFO, system, ack_params, **kwargs):
        #print("get transfer cmd, param:{}, {}, {}\n", COMMANDINFO, TRANSFERINFO, STAGEIDLIST)
        #print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        while not self.transfer_lock.acquire():
            sleep(0.1)
        try:
        
            '''if COMMANDINFO[0][0][1] not in ['', '0'] and COMMANDINFO[0][0][1] in self.ActiveTransfers:
                ack_params.append(['COMMANDID', 2])
                print("\COMMANDID error.\n")
                self.send_response(self.stream_function(2,42)([3, ack_params]), system)
                return'''

            if COMMANDINFO[0][1][1] > 101:
                ack_params.append(['PRIORITY', 2])
                print("\PRIORITY error.\n")
                self.send_response(self.stream_function(2,50)([3, ack_params]), system)
                return

            self.ResultCode=0
            self.CommandID=COMMANDINFO[0][0][1]
            self.CommandInfo={}
            self.CommandInfo["CommandID"]=COMMANDINFO[0][0][1]
            self.CommandInfo["Priority"]=COMMANDINFO[0][1][1]
            self.CommandInfo["Replace"]=COMMANDINFO[0][2][1]

            #D_TransferInfo={} #chocp fix
            self.TransferInfo={}
            self.TransferInfo["CarrierID"]=TRANSFERINFO[0][0][1]
            self.TransferInfo["SourcePort"]=TRANSFERINFO[0][1][1]
            self.TransferInfo["DestPort"]=TRANSFERINFO[0][2][1]

            self.TransferCompleteInfo=[{"TransferInfo":self.TransferInfo, "CarrierLoc":"aaaa"}] #chocp fix
            self.CarrierLoc="aaaa"
            self.CarrierID=TRANSFERINFO[0][0][1]
            self.SourcePort=TRANSFERINFO[0][1][1]
            self.DestPort=TRANSFERINFO[0][2][1]
            self.TransferPortList=[self.SourcePort]

            self.TransferInfoList=[] # Mike: 2021/07/27
            for Trans in TRANSFERINFO:
                Transfer={}
                Transfer["CarrierID"]=Trans[0][1]
                Transfer["SourcePort"]=Trans[1][1]
                Transfer["DestPort"]=Trans[2][1]
                for t in Trans[3:]:
                    if t[0] == "CARRIERTYPE":
                        Transfer["CarrierType"]=t[1]
                    elif t[0] == "LOTID":
                        Transfer["LotID"]=t[1]
                    elif t[0] == "LOTTYPE":
                        Transfer["LotType"]=t[1]
                    elif t[0] == "CUSTID":
                        Transfer["CustID"]=t[1]
                    elif t[0] == "PRODUCT":
                        Transfer["Product"]=t[1]
                    elif t[0] == "QUANTITY":
                        Transfer["Quantity"]=t[1]
                    elif t[0] == "QTIME":
                        Transfer["QTime"]=t[1]
                    elif t[0] == "LOT":
                        Transfer["LotID"]=t[1]
                    elif t[0] == "LOTNUM":
                        Transfer["LotNum"]=t[1]
                    else:
                        pass
                self.TransferInfoList.append(Transfer)


            #D_TransferInfo={} #chocp fix
            self.stageIDlist=kwargs.get("STAGEIDLIST", [[]])[0]

            #self.add_transfer_cmd(self.CommandID, {'CommandInfo': self.CommandInfo, 'TransferInfo': self.TransferInfoList})

            obj={}
            obj['remote_cmd']='host_transfer' #chocp fix
            obj['commandinfo']=self.CommandInfo
            # obj['transferinfo']=self.TransferInfo # Mike: 2021/07/27
            obj['stageIDlist']=self.stageIDlist
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            obj['CARRIERTYPE']=kwargs.get('CARRIERTYPE', [])
            if obj['CARRIERTYPE']:
                for transfer in self.TransferInfoList:
                    if transfer.get('CarrierType',''):
                        continue
                    else:
                        transfer['CarrierType']=obj['CARRIERTYPE'][0]
            obj['EXECUTETIME']=kwargs.get('EXECUTETIME', [''])
            obj['VEHICLEID']=kwargs.get('VEHICLEID', [''])
            obj['operatorID']=kwargs.get('OPERATORID', [''])[0]
            obj['transferinfolist']=self.TransferInfoList # Mike: 2021/07/27
            # print(obj)
            #self.send_response(self.stream_function(2,50)([4]), system) #2021/1/17 chocp add back for ASE MCS layer
            remotecmd_queue.append(obj)
        except:
            print("\Exception found in transfer.\n")
            self.send_response(self.stream_function(2,0)(), system)
            return
        finally:
            self.transfer_lock.release()

    #####################################
    #       Normal Function Define
    #####################################
    def add_transfer_cmd(self, CommandID, TransferInfo):
        self.ActiveTransfers[CommandID]=TransferInfo

    def rm_transfer_cmd(self, CommandID):
        if CommandID in self.ActiveTransfers:
            del self.ActiveTransfers[CommandID]

    def add_carrier(self, CarrierID, CarrierInfo):
        self.ActiveCarriers[CarrierID]=CarrierInfo
        
    def enhanced_add_carrier(self, CarrierID, CarrierInfo):
        self.EnhancedCarriers[CarrierID]=CarrierInfo

    def rm_carrier(self, CarrierID):
        if CarrierID in self.ActiveCarriers:
            del self.ActiveCarriers[CarrierID]
        if CarrierID in self.EnhancedCarriers:
            del self.EnhancedCarriers[CarrierID]

    def check_transfer_cmd_duplicate(self, CommandID):
        if CommandID not in ['', '0'] and CommandID in self.ActiveTransfers:
            return True
        return False

    def enable_event(self, CEID_list):
        for CEID in CEID_list:
            if CEID in self.registered_collection_events:
                self.registered_collection_events[CEID].enabled=True

    def disable_event(self, CEID_list):
        for CEID in CEID_list:
            if CEID in self.registered_collection_events:
                self.registered_collection_events[CEID].enabled=False






