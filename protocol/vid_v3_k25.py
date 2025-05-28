########################
#       SVID
########################
''' basic '''
#GEM_ALARMID=1
#GEM_ESTABLISH_COMMUNICATIONS_TIMEOUT=2
GEM_ALARMS_ENABLED=3
GEM_ALARMS_SET=4
GEM_CLOCK=5
GEM_CONTROL_STATE=6
GEM_EVENTS_ENABLED=7
GEM_LINK_STATE=8
GEM_MDLN=9
GEM_SOFTREV=10

GEM_SPOOL_COUNT_ACTUAL=23
GEM_SPOOL_COUNT_TOTAL=24
GEM_SPOOL_FULL_TIME=25
GEM_SPOOL_START_TIME=27
GEM_SPOOL_STATE=28
GEM_SPOOL_UNLOAD_SUPSTATE=29


''' SV '''
SV_CarrierIDList=101 # CarrierID*n
SV_TSCState=73
SV_EqpName=61
#SV_SpecVersion=GEM_SOFTREV
SV_EnhancedCarriers=50
SV_ActiveCarriers=51
SV_ActiveTransfers=52
SV_ActiveVehicles=53
#SV_TransferCommand=66 # [TransferInfo, CarrierLoc]*n
SV_TransferCompleteInfo=74 # [TransferInfo, CarrierLoc]*n
#SV_TransferPortList=69 # TransferPort*n
SV_TransferPort=68
SV_TransferInfo=67
SV_TransferInfoList=69
SV_FromPort=525 #kelvin 202504/23

''' tmp sv, for events, not available '''
SV_CommandID=58
SV_VehicleInfo=71 # VehicleID, VehicleState
SV_CommandInfo=59 # CommandID, Priority, Replace
SV_ResultCode=64 # U2
SV_VehicleID=70
SV_CarrierID=54
#SV_CarrierInfo=55
SV_CarrierLoc=56
SV_PortID=75
#SV_CurrentPortStates=76 #chocp 0528
SV_TransferState=77
#SV_CommandName=57
SV_CommandType=609
SV_SourcePort=65
SV_DestPort=60
SV_Priority=62
#SV_Replace=63
SV_VehicleState=72 #chocp 0528
SV_VehicleLastState=626
SV_CommandIDList=614
SV_StageID=615 # Mike: 2021/07/22
SV_ExecuteTime=616 #Kelvin 2022/08/21
SV_DoorState=649 #peter 240705
SV_ALTX=651
SV_ALSV=652
SV_UnitType=653
SV_UnitID=654
SV_Level=655
SV_CarrierType=656
SV_SubCode=657
SV_EnhancedCarrierInfo=658 #2024/06/21 for Mirle MCS
SV_InstallTime=659 #2024/06/21 for Mirle MCS
SV_CarrierState=660 #2024/06/21 for Mirle MCS

''' Rack '''
SV_ActiveRacks=701
SV_eRack1=702
SV_eRack2=703
SV_eRack3=704
SV_eRack4=705
SV_RackInfo=706 #chocp 0528
SV_RackLocation=707 # Mike: 2021/05/11

SV_RackID=617 #chocp 0531
SV_SlotID=618 #chocp 0531
SV_SlotStatus=619 #chocp 0531
SV_LocateResult=620 # Mike: 2020/08/18
SV_SendBy=621
SV_EQID=622 # Mike: 2020/11/11
SV_VehicleSOH=623 # Mike: 2021/05/11
SV_Routes=625  # Mike: 2023/05/17

########################
#       CEID
########################
''' Control State '''
GEM_EQP_OFFLINE=1
GEM_CONTROL_STATE_LOCAL=2
GEM_CONTROL_STATE_REMOTE=3

''' TSC state transition events '''
TSCAutoCompleted=53
TSCAutoInitiated=54
TSCPauseCompleted=55
TSCPaused=56
TSCPauseInitiated=57

''' transfer command state transition events '''
TransferAbortCompleted=101
TransferAbortFailed=102
TransferAbortInitiated=103
TransferCancelCompleted=104
TransferCancelFailed=105
TransferCancelInitiated=106
TransferCompleted=107
TransferInitiated=108
TransferPaused=109
TransferResumed=110
Transferring=111

''' vehicle state transition events ''' 
VehicleStateChange=200 #kelvinng 20250325 VehicleStateChange
VehicleArrived=201
VehicleAcquireStarted=202
VehicleAcquireCompleted=203
VehicleAssigned=204
VehicleDeparted=205
VehicleDepositStarted=206
VehicleDepositCompleted=207
VehicleInstalled=208
VehicleRemoved=209
VehicleUnassigned=210
VehicleChargeStarted=211
VehicleChargeCompleted=212
VehicleExchangeStarted=213
VehicleExchangeCompleted=214
OpenDoorAcquire=219 #peter 240705,test call elevator for K11
VehicleShiftCompleted=217
VehicleShiftStarted=218
''' carrier state transition events '''
CarrierInstalled=151
CarrierRemoved=152

''' port transfer state transition events'''
PortInService=301
PortOutOfService=302

''' non-transition events '''
OperatorInitiatedAction=254

RackStatusUpdate=802
PortStatusUpdate=803

VehicleBatteryHealth=804 # Mike: 2021/05/12

VehicleRoutes=805 # Mike: 2023/05/17
VehicleEnterSegment=806 # Mike: 2023/05/17
VehicleExitSegment=807 # Mike: 2023/05/17
VehicleRouteFailed=808 # Mike: 2023/07/17
VehicleBlocking=809 # Mike: 2023/07/17

LocateComplete=810
EqLoadComplete=820 # Mike: 2020/11/11
EqUnloadComplete=821 # Mike: 2020/11/11
CheckIn=850 # Mike: 2020/11/11

StageInvalided=860 # Mike: 2020/07/22
StageReached=861 # Mike: 2020/07/22
NoBlockingTimeExpired=862 # Mike: 2020/07/22
ExpectedDurationExpired=863 # Mike: 2020/07/22
WaitTimeoutExpired=864 # Mike: 2020/07/22

''' Tr request '''
TrAddReq=900
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
DestPortChanged=920 # for K25
TrShiftReq=914

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
    TransferAbortCompleted: {'report':[SV_CommandID, SV_TransferCompleteInfo,SV_VehicleID]},
    TransferAbortFailed: {'report':[SV_CommandID]},
    TransferAbortInitiated: {'report':[SV_CommandID]},
    TransferCancelCompleted: {'report':[SV_CommandID, SV_TransferCompleteInfo]},
    TransferCancelFailed: {'report':[SV_CommandID]},
    TransferCancelInitiated: {'report':[SV_CommandID]},
    TransferCompleted: {'report':[SV_CommandInfo,SV_VehicleID, SV_TransferCompleteInfo, SV_ResultCode]},
    TransferInitiated: {'report':[SV_CommandID]},
    TransferPaused: {'report':[SV_CommandID]},
    TransferResumed: {'report':[SV_CommandID]},
    Transferring: {'report':[SV_CommandID,SV_CarrierID]},
    VehicleArrived: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_ResultCode]},

    VehicleAcquireStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},

    VehicleAcquireCompleted: {'report':[SV_VehicleID, SV_CarrierLoc, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},

    VehicleAssigned: {'report':[SV_VehicleID, SV_CommandIDList]},

    VehicleDeparted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort]},

    VehicleDepositStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},

    VehicleDepositCompleted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},
    VehicleShiftCompleted: {'report':[SV_VehicleID, SV_FromPort,SV_CommandID,SV_TransferPort, SV_CarrierID, SV_ResultCode]},
    VehicleShiftStarted: {'report':[SV_VehicleID, SV_FromPort,SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},

    VehicleStateChange: {'report':[SV_VehicleID, SV_VehicleState, SV_VehicleLastState]},
    VehicleChargeStarted: {'report':[SV_VehicleID]},
    VehicleChargeCompleted: {'report':[SV_VehicleID]},
    VehicleExchangeStarted: {'report':[SV_VehicleID]},
    VehicleExchangeCompleted: {'report':[SV_VehicleID]},
    VehicleInstalled: {'report':[SV_VehicleID]},
    VehicleRemoved: {'report':[SV_VehicleID]},
    VehicleUnassigned: {'report':[SV_VehicleID, SV_CommandIDList]},
    CarrierInstalled: {'report':[SV_VehicleID, SV_CarrierID, SV_CarrierLoc, SV_CommandID]},
    CarrierRemoved: {'report':[SV_VehicleID, SV_CarrierID, SV_CarrierLoc, SV_CommandID]},
    PortInService: {'report':[SV_PortID]},
    PortOutOfService: {'report':[SV_PortID]},
    OperatorInitiatedAction: {'report':[SV_CommandID, SV_CommandType, SV_CarrierID, SV_SourcePort, SV_DestPort, SV_Priority]},
    RackStatusUpdate: {'report':[SV_RackInfo]},
    PortStatusUpdate: {'report':[SV_RackID, SV_SlotID, SV_SlotStatus, SV_SendBy, SV_RackLocation]},
    VehicleBatteryHealth: {'report':[SV_VehicleID, SV_VehicleSOH]},
    VehicleRoutes: {'report':[SV_VehicleID, SV_Routes]},
    VehicleEnterSegment: {'report':[SV_VehicleID, SV_Routes]},
    VehicleExitSegment: {'report':[SV_VehicleID, SV_Routes]},
    VehicleRouteFailed: {'report':[SV_VehicleID, SV_CommandIDList, SV_TransferInfoList]},
    VehicleBlocking: {'report':[SV_VehicleID, SV_CommandIDList, SV_TransferInfoList]},
    LocateComplete: {'report':[SV_CarrierID, SV_RackID, SV_SlotID, SV_LocateResult]},
    EqLoadComplete: {'report':[SV_VehicleID, SV_EQID, SV_PortID, SV_CarrierID]},
    EqUnloadComplete: {'report':[SV_VehicleID, SV_EQID, SV_PortID, SV_CarrierID]},
    CheckIn: {'report':[SV_RackID, SV_SlotID, SV_SlotStatus]},
    StageInvalided: {'report':[SV_StageID]},
    StageReached: {'report':[SV_StageID, SV_VehicleID]},
    NoBlockingTimeExpired: {'report':[SV_StageID]},
    ExpectedDurationExpired: {'report':[SV_StageID]},
    WaitTimeoutExpired: {'report':[SV_StageID]},
    TrAddReq: {'report':[SV_VehicleID, SV_TransferPort]},
    TrLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID,SV_CommandID,SV_ExecuteTime]},
    TrUnLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID,SV_CommandID,SV_ExecuteTime]},
    TrBackReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    EQStatusReq: {'report':[SV_EQID]},
    PortStatusReq: {'report':[SV_PortID]},
    TrLoadWithGateReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrUnLoadWithGateReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    AssistCloseDoorReq: {'report':[SV_VehicleID, SV_TransferPort]},
    EQAutoOnReq: {'report':[SV_EQID]},
    EQAutoOffReq: {'report':[SV_EQID]},
    DestPortChanged:{'report':[SV_CommandID, SV_CarrierID,SV_DestPort,SV_TransferPort]},
    OpenDoorAcquire: {'report':[SV_VehicleID, SV_TransferPort, SV_DoorState]},#peter 240705,test call door for K11
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
    10025: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR execute charge command timeout'},
    10026: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'CarrierType None or Check Error for Acquire/Deposit'},
    10027: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID], 'text':'MR move with route obstacles'},
    10028: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_SourcePort, SV_DestPort], 'text': 'MR try or select to charge station fail'},
    10029: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_PortID], 'text': 'Stop MR command to replace new job'},
    10030: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_PortID], 'text': 'No available carrier.'},
    10031: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID], 'text': 'MR Stop wit host command'},
    10032: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR with other warning'},
    10033: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text': 'MR with emergency evacuation'},
    10034: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text': 'Action not support'},
    10035: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CarrierLoc, SV_CarrierID, SV_CommandID], 'text':'Fault carrier on MR'},
    
    20001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode ], 'text':'SC internal error, code exception'},
    20002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID, SV_CarrierLoc], 'text':'Base read rfid error'},
    20003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID, SV_CarrierLoc], 'text':'E84 error'},
    20004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Off line, retry communication with rack timeout'},
    20005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID, SV_CarrierLoc], 'text':'Port in manual mode'},

    20051: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack off line'},
    20052: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level high'},
    20053: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level full'},
    20054: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level low'},
    20055: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack water level empty'},

    30001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack Rack connect fail'},
    30002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'receive null string from socket'},
    30003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'linking timeout'},
    30004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'receive format error from socket'},
    30005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'Erack syntax error'},

    40000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level ,SV_SubCode], 'text':'Host transfer cmd parse get exception'},

    40001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Cancel by host'},
    40002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Abort by host'},

    
    40007: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, commandID duplicated in active transfers'},
    40008: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host change cmd, go to new dest port due to TrLoad request NG'},
    40009: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'Host transfer cmd, CarrierType None or Error'},
    40010: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID not in white list'},
    40011: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort], 'text':'Host transfer cmd, source port not found in map'},
    40012: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_DestPort], 'text':'Host transfer cmd, dest port not found in map'},
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
    40023: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, service zone disabled'},#Hshuo 2023121
    40024: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort, SV_CarrierID], 'text':'Host transfer cmd, carrier source port mismatch'},
    
    50051: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'ABCS with alarms'},
    50052: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'ABCS linking timeout'},
    50053: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_RackID], 'text':'ABCS Connect fail'},

    60000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host order rtd cmd, workID duplicate in worklist'},
    60001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier duplicate in worklist'},
    60002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, can not locate carrier'},
    60003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier ID can not null'},
    60004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_DestPort], 'text':'Host order rtd cmd, dest port dispatch fail'},

}
