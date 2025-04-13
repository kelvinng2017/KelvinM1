from gem_host import Host
from time import sleep
from secsgem.secs.dataitems import ALED, ACKC5, ACKC6
import secsgem
import vid_v3 as v3

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
OpenDoorAcquire=516#peter 240705,test call door for K11


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

VehicleRoutes=805 # Mike: 2023/05/17
VehicleEnterSegment=806 # Mike: 2023/05/17
VehicleExitSegment=807 # Mike: 2023/05/17
VehicleRouteFailed=808 # Mike: 2023/07/17
VehicleBlocking=809 # Mike: 2023/07/17

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


for attr in dir(v3):
    if '__' not in attr:
        globals()[attr]=getattr(v3, attr)

class E82Proxy():
    def __init__(self, host_ip, host_port, Active, DevID, Name, Log_Handler, Callback, mdln='TEST1.0', T3=45, T5=10, T6=5, T7=10, T8=5):
        self.h=Host(host_ip, host_port, Active, DevID, Name, Log_Handler, mdln=mdln, T3=T3, T5=T5, T6=T6, T7=T7, T8=T8)

        self.h.Callback=Callback

        self.h.EventList={
            # Control State 
            GEM_EQP_OFFLINE:['OffLine'],
            GEM_CONTROL_STATE_LOCAL:['LocalOnLine'],
            GEM_CONTROL_STATE_REMOTE:['RemoteOnLine'],
            # TSC state transition events 
            TSCAutoCompleted:['TSCAutoCompleted'],
            TSCAutoInitiated:['TSCAutoInitiated'],
            TSCPauseCompleted:['TSCPauseCompleted'],
            TSCPaused:['TSCPaused'],
            TSCPauseInitiated:['TSCPauseInitiated'],
            # transfer command state transition events 
            TransferAbortCompleted:['TransferAbortCompleted', 'CommandID', 'TransferCompleteInfo'],
            TransferAbortFailed:['TransferAbortFailed', 'CommandID'],
            TransferAbortInitiated:['TransferAbortInitiated', 'CommandID'],
            TransferCancelCompleted:['TransferCancelCompleted', 'CommandID'],
            TransferCancelFailed:['TransferCancelFailed', 'CommandID'],
            TransferCancelInitiated:['TransferCancelInitiated', 'CommandID'],
            TransferCompleted:['TransferCompleted', 'CommandInfo', 'TransferCompleteInfo', 'ResultCode'],
            TransferInitiated:['TransferInitiated', 'CommandID'],
            TransferPaused:['TransferPaused', 'CommandID'],
            TransferResumed:['TransferResumed', 'CommandID'],
            Transferring:['Transferring', 'CommandID'],
            # vehicle state transition events 
            VehicleArrived:['VehicleArrived', 'VehicleID', 'CommandID', 'TransferPort'],
            VehicleAcquireStarted:['VehicleAcquireStarted', 'VehicleID', 'CommandID', 'TransferPort', 'CarrierID'],
            VehicleAcquireCompleted:['VehicleAcquireCompleted', 'VehicleID', 'CommandID', 'TransferPort', 'CarrierID', 'ResultCode'],
            VehicleAssigned:['VehicleAssigned', 'VehicleID', 'CommandIDList'],
            VehicleDeparted:['VehicleDeparted', 'VehicleID', 'CommandID', 'TransferPort'],
            VehicleDepositStarted:['VehicleDepositStarted', 'VehicleID', 'CommandID', 'TransferPort', 'CarrierID'],
            VehicleDepositCompleted:['VehicleDepositCompleted', 'VehicleID', 'CommandID', 'TransferPort', 'CarrierID', 'ResultCode'],
            VehicleChargeStarted:['VehicleChargeStarted', 'VehicleID'],
            VehicleChargeCompleted:['VehicleChargeCompleted', 'VehicleID'],
            VehicleInstalled:['VehicleInstalled', 'VehicleID'],
            VehicleRemoved:['VehicleRemoved', 'VehicleID'],
            VehicleUnassigned:['VehicleUnassigned', 'VehicleID', 'CommandIDList'],
            VehicleBatteryHealth: ['VehicleBatteryHealth', 'VehicleID', 'VehicleSOH'],
            VehicleRoutes: ['VehicleRoutes', 'VehicleID', 'Routes'],
            VehicleEnterSegment: ['VehicleEnterSegment', 'VehicleID', 'Routes'],
            VehicleExitSegment: ['VehicleExitSegment', 'VehicleID', 'Routes'],
            VehicleRouteFailed: ['VehicleRouteFailed', 'VehicleID', 'CommandIDList', 'TransferInfoList'],
            VehicleBlocking: ['VehicleBlocking', 'VehicleID', 'CommandIDList', 'TransferInfoList'],
            # carrier state transition events 
            CarrierInstalled:['CarrierInstalled', 'VehicleID', 'CarrierID', 'CarrierLoc', 'CommandID'],
            CarrierRemoved:['CarrierRemoved', 'VehicleID', 'CarrierID', 'CarrierLoc', 'CommandID'],
            # port transfer state transition events
            PortInService:['PortInService', 'PortID'],
            PortOutOfService:['PortOutOfService', 'PortID'],
            # non-transition events 
            OperatorInitiatedAction:['OperatorInitiatedAction', 'CommandID', 'CommandType', 'CarrierID', 'SourcePort', 'DestPort', 'Priority'],
            LocateComplete:['LocateComplete', 'CarrierID', 'Device', 'Port', 'Result'],
            # Tr request 
            TrAddReq:['TrAddReq', 'VehicleID', 'TransferPort'],
            TrLoadReq:['TrLoadReq', 'VehicleID', 'TransferPort', 'CarrierID'],
            TrUnLoadReq:['TrUnLoadReq', 'VehicleID', 'TransferPort', 'CarrierID'],
            TrBackReq:['TrBackReq', 'VehicleID', 'TransferPort', 'CarrierID'],
            EQStatusReq:['EQStatusReq', 'EQID'],
            PortStatusReq:['PortStatusReq', 'PortID'],
            EqLoadComplete:['EqLoadComplete', 'VehicleID', 'EQID', 'PortID', 'CarrierID'],
            EqUnloadComplete:['EqUnloadComplete', 'VehicleID', 'EQID', 'PortID', 'CarrierID'],
            TrLoadWithGateReq:['TrLoadWithGateReq', 'VehicleID', 'TransferPort', 'CarrierID'],
            TrUnLoadWithGateReq:['TrUnLoadWithGateReq', 'VehicleID', 'TransferPort', 'CarrierID'],
            AssistCloseDoorReq:['AssistCloseDoorReq', 'VehicleID', 'TransferPort'],
            EQAutoOnReq:['EQAutoOnReq', 'EQID'],
            EQAutoOffReq:['EQAutoOffReq', 'EQID'],
            OpenDoorAcquire: ['OpenDoorAcquire', 'VehicleID', 'TransferPort'],#peter 240705,test call door for K11
        }

        self.h.AlarmList={
    # ALID: {'report_id':[], 'report':[], 'text':ALTX},
            10001: ['10001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode'],
            10002: ['10002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID'],
            10003: ['10003', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10004: ['10004', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10005: ['10005', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'SourcePort', 'DestPort'],
            10006: ['10006', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID'],
            10007: ['10007', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10008: ['10008', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID'],
            10009: ['10009', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10010: ['10010', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID'],
            10011: ['10011', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'STKID'],
            10012: ['10012', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'STKID'],
            10013: ['10013', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'PortID'],
            10014: ['10014', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            10015: ['10015', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10016: ['10016', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10017: ['10017', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID', 'CarrierID'],
            10018: ['10018', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID', 'CarrierID'],
            10019: ['10019', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID', 'CarrierID'],
            10020: ['10020', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID', 'CarrierID'],
            10021: ['10021', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10022: ['10022', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10023: ['10023', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10024: ['10024', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'SourcePort', 'DestPort'],
            10025: ['10025', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10026: ['10026', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'CarrierID', 'CarrierType'],
            10027: ['10027', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID'],
            10028: ['10028', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'SourcePort', 'DestPort'],
            10029: ['10029', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'PortID'],
            10030: ['10030', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'PortID' ],
            10031: ['10031', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID'],
            10032: ['10032', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID', 'CommandID', 'PortID'],
            10033: ['10033', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'VehicleID'],

            10051: ['10051', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            10052: ['10052', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            10053: ['10053', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            10054: ['10054', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            10055: ['10055', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],

            40000: ['40000', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode'],

            40001: ['40001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],
            40002: ['40002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],

            40011: ['40011', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'SourcePort'],
            40012: ['40012', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'DestPort'],
            40013: ['40013', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'CarrierID'],
            40014: ['40014', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'CarrierID'],
            40015: ['40015', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'SourcePort'],
            40016: ['40016', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'CarrierID'],
            40017: ['40017', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'DestPort'],
            40018: ['40018', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'SourcePort', 'CarrierID'],
            40019: ['40019', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'DestPort'],
            40020: ['40020', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'SourcePort'],
            40021: ['40021', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],

            51001: ['51001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],
            51002: ['51002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],

            51051: ['51051', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'DeviceID'],
            51052: ['51052', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'DeviceID'],
            51053: ['51053', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'DeviceID'],

            60000: ['60000', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],
            60001: ['60001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],
            60002: ['60002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID'],
            60003: ['60003', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'CarrierID'],
            60004: ['60004', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'CommandID', 'CarrierID', 'DestPort'],
        }


    def SV_Request(self, SV_List):

        #self.logger.info("send abort cmd.")

        sv_list=SV_List
        if not isinstance(SV_List, list):
            sv_list=[SV_List]
        res=self.h.send_sv_request(sv_list)
        ret={}
        for i in range(len(sv_list)):
            ret[sv_list[i]]=res[i].get()
        return ret

    def Abort(self, CommandID):

        #self.logger.info("send abort cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})

        res=self.h.send_remote_cmd("ABORT", PARAMS)
        return res

    def Assert(self, Request, CommandID, CarrierID, DestPort, Result, **kwargs):

        #self.logger.info("send assert cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "REQUEST", "CPVAL": Request})
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "DESTPORT", "CPVAL": DestPort})
        PARAMS.append({"CPNAME": "RESULT", "CPVAL": Result})
        if 'LotID' in kwargs:
            PARAMS.append({"CPNAME": "LOTID", "CPVAL": kwargs.get('LotID')})
        if 'Quantity' in kwargs:
            PARAMS.append({"CPNAME": "QUANTITY", "CPVAL": kwargs.get('Quantity')})

        res=self.h.send_remote_cmd("ASSERT", PARAMS)
        return res

    def Call(self, CommandID, DestPort, NoBlockingTime, WaitTimeout, VehicleID=''):

        #self.logger.info("send locate cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})
        PARAMS.append({"CPNAME": "DESTPORT", "CPVAL": DestPort})
        PARAMS.append({"CPNAME": "NOBLOCKINGTIME", "CPVAL": NoBlockingTime})
        PARAMS.append({"CPNAME": "WAITTIMEOUT", "CPVAL": WaitTimeout})
        if VehicleID:
            PARAMS.append({"CPNAME": "VEHICLEID", "CPVAL": VehicleID})

        res=self.h.send_remote_cmd("CALL", PARAMS)
        return res

    def Cancel(self, CommandID):

        #self.logger.info("send cancel cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})

        res=self.h.send_remote_cmd("CANCEL", PARAMS)
        return res

    def Change(self, DataID, ObjSpec, CommandID, Priority, Replace, TransferList, **kwargs):

        #self.logger.info("send transfer cmd.")

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["COMMANDID", CommandID])
        CEPVALS.append(["PRIORITY", Priority])
        CEPVALS.append(["REPLACE", Replace])
        PARAMS.append({"CPNAME": "COMMANDINFO", "CEPVAL": CEPVALS})
        for transfer in TransferList:
            CEPVALS=[]
            CEPVALS.append(["CARRIERID", transfer['CarrierID']])
            CEPVALS.append(["SOURCEPORT", transfer['SourcePort']])
            CEPVALS.append(["DESTPORT", transfer['DestPort']])
            PARAMS.append({"CPNAME": "TRANSFERINFO", "CEPVAL": CEPVALS})
        for key, value in kwargs.items():
            if isinstance(value, dict):
                CEPVALS=[]
                for d_key, d_value in value.items():
                    CEPVALS.append([key, value])
                PARAMS.append({"CPNAME": key, "CEPVAL": CEPVALS})
            else:
                PARAMS.append({"CPNAME": key, "CEPVAL": value})

        res=self.h.send_enhance_remote_cmd(DataID, ObjSpec, "CHANGE", PARAMS)
        return res

    def EQState(self, DataID, ObjSpec, EQID, EQStatus, PortInfoList):

        #self.logger.info("send transfer cmd.")

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["EQID", EQID])
        CEPVALS.append(["EQSTATUS", EQStatus])
        PARAMS.append({"CPNAME": "EQINFO", "CEPVAL": CEPVALS})
        CEPVALS=[]
        for portinfo in PortInfoList:
            CEPVALS.append(["PORTID", portinfo['PortID']])
            CEPVALS.append(["CARRIERID", portinfo['CarrierID']])
            CEPVALS.append(["PORTSTATUS", portinfo['PortStatus']])
            if 'LotID' in portinfo:
                CEPVALS.append(["LOTID", portinfo['LotID']])
            if 'Quantity' in portinfo:
                CEPVALS.append(["QUANTITY", portinfo['Quantity']])
        PARAMS.append({"CPNAME": "PORTINFO", "CEPVAL": CEPVALS})

        res=self.h.send_enhance_remote_cmd(DataID, ObjSpec, "EQSTATE", PARAMS)
        return res

    def Infoupdate(self, CarrierID, **kwargs):

        #self.logger.info("send associate cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        i=1
        for key, items in kwargs.items():
            PARAMS.append({"CPNAME": "CARRIERINFOLABEL{}".format(i), "CPVAL": key})
            PARAMS.append({"CPNAME": "CARRIERINFO{}".format(i), "CPVAL": items})
            i += 1

        res=self.h.send_remote_cmd("INFOUPDATE", PARAMS)
        return res

    def Locate(self, CarrierID):

        #self.logger.info("send locate cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})

        res=self.h.send_remote_cmd("LOCATE", PARAMS)
        return res

    def Pause(self):

        #self.logger.info("send pause cmd.")

        PARAMS=[]

        res=self.h.send_remote_cmd("PAUSE", PARAMS)
        return res

    def PortState(self, PortID, CarrierID, PortStatus, **kwargs):

        #self.logger.info("send port state cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "PORTID", "CPVAL": PortID})
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "PORTSTATUS", "CPVAL": PortStatus})
        if 'LotID' in kwargs:
            PARAMS.append({"CPNAME": "LOTID", "CPVAL": kwargs.get('LotID')})
        if 'Quantity' in kwargs:
            PARAMS.append({"CPNAME": "QUANTITY", "CPVAL": kwargs.get('Quantity')})

        res=self.h.send_remote_cmd("PORTSTATE", PARAMS)
        return res

    def PreTransfer(self, DataID, ObjSpec, CommandID, Priority, Replace, TransferList, **kwargs):

        #self.logger.info("send transfer cmd.")

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["COMMANDID", CommandID])
        CEPVALS.append(["PRIORITY", Priority])
        CEPVALS.append(["REPLACE", Replace])
        PARAMS.append({"CPNAME": "COMMANDINFO", "CEPVAL": CEPVALS})
        for transfer in TransferList:
            CEPVALS=[]
            CEPVALS.append(["CARRIERID", transfer['CarrierID']])
            CEPVALS.append(["SOURCEPORT", transfer['SourcePort']])
            CEPVALS.append(["DESTPORT", transfer['DestPort']])
            for key, items in kwargs.items():
                if key not in ["CARRIERID", "SOURCEPORT", "DESTPORT"]:
                    CEPVALS.append([key.upper(), transfer[key]])
            PARAMS.append({"CPNAME": "TRANSFERINFO", "CEPVAL": CEPVALS})
        for key, value in kwargs.items():
            if isinstance(value, dict):
                CEPVALS=[]
                for d_key, d_value in value.items():
                    CEPVALS.append([key, value])
                PARAMS.append({"CPNAME": key, "CEPVAL": CEPVALS})
            else:
                PARAMS.append({"CPNAME": key, "CEPVAL": value})

        res=self.h.send_enhance_remote_cmd(DataID, ObjSpec, "PRETRANSFER", PARAMS)
        return res

    def Reassign(self, CommandID, CarrierID, DestPort):

        #self.logger.info("send reassign cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "DESTPORT", "CPVAL": DestPort})

        res=self.h.send_remote_cmd("REASSIGN", PARAMS)
        return res

    def ResetAllPortState(self):

        #self.logger.info("send resume cmd.")

        PARAMS=[]

        res=self.h.send_remote_cmd("RESETALLPORTSTATE", PARAMS)
        return res

    def Resume(self):

        #self.logger.info("send resume cmd.")

        PARAMS=[]

        res=self.h.send_remote_cmd("RESUME", PARAMS)
        return res

    def StageDelete(self, StageID):

        #self.logger.info("send locate cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "STAGEID", "CPVAL": StageID})

        res=self.h.send_remote_cmd("STAGEDELETE", PARAMS)
        return res

    def Stage(self, DataID, ObjSpec, StageID, Priority, Replace, ExpectedDuration, NonblockingTime, WaitTimeout, TransferList):

        #self.logger.info("send transfer cmd.")

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["COMMANDID", StageID])
        CEPVALS.append(["PRIORITY", Priority])
        CEPVALS.append(["REPLACE", Replace])
        CEPVALS.append(["REPLACE", ExpectedDuration])
        CEPVALS.append(["REPLACE", NonblockingTime])
        CEPVALS.append(["REPLACE", WaitTimeout])
        PARAMS.append({"CPNAME": "STAGEINFO", "CEPVAL": CEPVALS})
        for transfer in TransferList:
            CEPVALS=[]
            CEPVALS.append(["CARRIERID", transfer['CarrierID']])
            CEPVALS.append(["SOURCEPORT", transfer['SourcePort']])
            CEPVALS.append(["DESTPORT", transfer['DestPort']])
            PARAMS.append({"CPNAME": "TRANSFERINFO", "CEPVAL": CEPVALS})

        res=self.h.send_enhance_remote_cmd(DataID, ObjSpec, "TRANSFER", PARAMS)
        return res

    def Transfer(self, DataID, ObjSpec, CommandID, Priority, Replace, TransferList, **kwargs):

        #self.logger.info("send transfer cmd.")

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["COMMANDID", CommandID])
        CEPVALS.append(["PRIORITY", Priority])
        CEPVALS.append(["REPLACE", Replace])
        PARAMS.append({"CPNAME": "COMMANDINFO", "CEPVAL": CEPVALS})
        for transfer in TransferList:
            CEPVALS=[]
            CEPVALS.append(["CARRIERID", transfer['CarrierID']])
            CEPVALS.append(["SOURCEPORT", transfer['SourcePort']])
            CEPVALS.append(["DESTPORT", transfer['DestPort']])
            for key, items in kwargs.items():
                if key not in ["CARRIERID", "SOURCEPORT", "DESTPORT"]:
                    CEPVALS.append([key.upper(), transfer[key]])
            PARAMS.append({"CPNAME": "TRANSFERINFO", "CEPVAL": CEPVALS})
        for key, value in kwargs.items():
            if isinstance(value, dict):
                CEPVALS=[]
                for d_key, d_value in value.items():
                    CEPVALS.append([key, value])
                PARAMS.append({"CPNAME": key, "CEPVAL": CEPVALS})
            else:
                PARAMS.append({"CPNAME": key, "CEPVAL": value})

        res=self.h.send_enhance_remote_cmd(DataID, ObjSpec, "TRANSFER", PARAMS)
        return res

    def enable(self):
        self.h.enable()
        sleep(1)
        self.h.send_prime_message(self.h.stream_function(1, 17)())

    def disable(self):
        self.h.disable()

