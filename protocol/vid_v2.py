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

GEM_SPOOL_COUNT_ACTUAL=53
GEM_SPOOL_COUNT_TOTAL=54
GEM_SPOOL_FULL_TIME=55
GEM_SPOOL_START_TIME=57
GEM_SPOOL_STATE=58
GEM_SPOOL_UNLOAD_SUPSTATE=59

''' SV '''
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
SV_TransferState=624
SV_ALTX=651
SV_ALSV=652
SV_UnitType=653
SV_UnitID=654
SV_Level=655
SV_CarrierType=656 #chocp 2022/1/2
SV_SubCode=657 #Chi 2022/06/17

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
VehicleArrived=501
VehicleAcquireStarted=502
VehicleAcquireCompleted=503
VehicleAssigned=504
VehicleDeparted=505
VehicleDepositStarted=506
VehicleDepositCompleted=507

VehicleChargeStarted=511
VehicleChargeCompleted=512
VehicleExchangeStarted=513
VehicleExchangeCompleted=514


VehicleInstalled=508
VehicleRemoved=509
VehicleUnassigned=510


''' carrier state transition events '''
CarrierInstalled=601
CarrierRemoved=602
''' port transfer state transition events'''
PortInService=701
PortOutOfService=702
''' non-transition events '''
OperatorInitiatedAction=801

RackStatusUpdate=802
PortStatusUpdate=803

VehicleBatteryHealth=804 # Mike: 2021/05/12

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

    VehicleArrived: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_ResultCode]},

    VehicleAcquireStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},

    VehicleAcquireCompleted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},

    VehicleAssigned: {'report':[SV_VehicleID, SV_CommandIDList]},

    VehicleDeparted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort]},

    VehicleDepositStarted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID]},

    VehicleDepositCompleted: {'report':[SV_VehicleID, SV_CommandID, SV_TransferPort, SV_CarrierID, SV_ResultCode]},

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
    TrLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrUnLoadReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    TrBackReq: {'report':[SV_VehicleID, SV_TransferPort, SV_CarrierID]},
    EQStatusReq: {'report':[SV_EQID]},
    PortStatusReq: {'report':[SV_PortID]},
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
    10032: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text':'MR with other warning'},
    10033: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID], 'text': 'MR with emergency evacuation'},
    10034: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_VehicleID, SV_CommandID, SV_PortID], 'text': 'Action not support'},
    
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
    40023: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, service zone disabled'},#Hshuo 2023121
    40024: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_SourcePort, SV_CarrierID], 'text':'Host transfer cmd, carrier source port mismatch'},

    60000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host order rtd cmd, workID duplicate in worklist'},
    60001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier duplicate in worklist'},
    60002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, can not locate carrier'},
    60003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier ID can not null'},
    60004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_DestPort], 'text':'Host order rtd cmd, dest port dispatch fail'},
}
