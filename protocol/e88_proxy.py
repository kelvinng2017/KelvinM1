from gem_host import Host
from time import sleep
from secsgem.secs.dataitems import ALED, ACKC5, ACKC6
import secsgem

''' Control State '''
GEM_EQP_OFFLINE=1
GEM_CONTROL_STATE_LOCAL=2
GEM_CONTROL_STATE_REMOTE=3

''' SC state transition events '''
SCAutoCompleted=53
SCAutoInitiated=54
SCPauseCompleted=55
SCPaused=56
SCPauseInitiated=57

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

''' stocker carrier state transition events '''
CarrierInstallCompleted=151
CarrierRemoveCompleted=152
CarrierRemoved=153
CarrierResumed=154
CarrierStored=155
CarrierStoredAlt=156
CarrierTransferring=157
CarrierWaitIn=158
CarrierWaitOut=159
ZoneCapacityChange=160

''' stocker crane state transition events '''
CraneActive=201
CraneIdle=202

''' port transfer state transition events'''
#PortInService=301
#PortOutOfService=302

''' non-transition events '''
CarrierIDRead=251
CarrierLocateCompleted=252
IDReadError=253
OperatorInitiatedAction=254

DeviceOnline=301
DeviceOffline=302


class E88Proxy():
    def __init__(self, host_ip, host_port, Active, DevID, Name, Log_Handler, Callback, mdln='TEST1.0', T3=45, T5=10, T6=5, T7=10, T8=5):
        self.h=Host(host_ip, host_port, Active, DevID, Name, Log_Handler, mdln=mdln, T3=T3, T5=T5, T6=T6, T7=T7, T8=T8)

        self.h.Callback=Callback

        self.h.EventList={
            # Control State 
            GEM_EQP_OFFLINE:['OffLine'],
            GEM_CONTROL_STATE_LOCAL:['LocalOnLine'],
            GEM_CONTROL_STATE_REMOTE:['RemoteOnLine'],
            # SC state transition events 
            SCAutoCompleted:['SCAutoCompleted'],
            SCAutoInitiated:['SCAutoInitiated'],
            SCPauseCompleted:['SCPauseCompleted'],
            SCPaused:['SCPaused'],
            SCPauseInitiated:['SCPauseInitiated'],
            # transfer command state transition events 
            TransferAbortCompleted:['TransferAbortCompleted', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferAbortFailed:['TransferAbortFailed', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferAbortInitiated:['TransferAbortInitiated', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferCancelCompleted:['TransferCancelCompleted', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferCancelFailed:['TransferCancelFailed', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferCancelInitiated:['TransferCancelInitiated', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferCompleted:['TransferCompleted', 'CommandID', 'CarrierID', 'CarrierLoc', 'ResultCode', 'CarrierZoneName'],
            TransferInitiated:['TransferInitiated', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'Dest'],
            TransferPaused:['TransferPaused', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            TransferResumed:['TransferResumed', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            # stocker carrier state transition events 
            CarrierInstallCompleted:['CarrierInstallCompleted', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'HandoffType', 'PortType'],
            CarrierRemoveCompleted:['CarrierRemoveCompleted', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'HandoffType', 'PortType'],
            CarrierRemoved:['CarrierRemoved', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'HandoffType', 'PortType'],
            CarrierResumed:['CarrierResumed', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'Dest'],
            CarrierStored:['CarrierStored', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'HandoffType', 'PortType'],
            CarrierStoredAlt:['CarrierStoredAlt', 'CommandID', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'Dest'],
            CarrierTransferring:['CarrierTransferring', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            CarrierWaitIn:['CarrierWaitIn', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            CarrierWaitOut:['CarrierWaitOut', 'CarrierID', 'CarrierLoc', 'CarrierZoneName', 'PortType'],
            ZoneCapacityChange:['ZoneCapacityChange', 'ZoneData'],
            # stocker crane state transition events 
            CraneActive:['CraneActive', 'CommandID', 'StockerCraneID'],
            CraneIdle:['CraneIdle', 'CommandID', 'StockerCraneID'],
            # non-transition events 
            CarrierIDRead:['CarrierIDRead', 'CarrierID', 'CarrierLoc', 'IDReadStatus'],
            CarrierLocateCompleted:['CarrierLocateCompleted', 'CarrierID', 'CarrierLoc', 'CarrierZoneName'],
            IDReadError:['IDReadError', 'CarrierID', 'CarrierLoc', 'IDReadStatus'],
            OperatorInitiatedAction:['OperatorInitiatedAction', 'CommandID', 'CommandType', 'CarrierID', 'Source', 'Dest', 'SV_Priority'],
            DeviceOnline:['DeviceOnline','DeviceID'],
            DeviceOffline:['DeviceOffline','DeviceID']
        }

        self.h.AlarmList={
            20001: ['10001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode'],
            20002: ['10002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'ZoneName', 'CarrierLoc'],
            20003: ['10003', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'ZoneName', 'CarrierLoc'],
            20004: ['10004', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'ZoneName'],
            20005: ['10005', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'ZoneName', 'CarrierLoc'],
            20051: ['20051', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            20052: ['20052', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            20053: ['20053', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            20054: ['20054', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            20055: ['20055', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            30001: ['30001', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            30002: ['30002', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            30003: ['30003', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            30004: ['30004', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
            30005: ['30005', 'ALTX', 'ALSV', 'UnitType', 'UnitID', 'Level', 'SubCode', 'STKID'],
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

    def Associate(self, CarrierID, CarrierLoc, AssociateData):

        #self.logger.info("send associate cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "CARRIERLOC", "CPVAL": CarrierLoc})
        PARAMS.append({"CPNAME": "ASSOCIATEDATA", "CPVAL": AssociateData})

        res=self.h.send_remote_cmd("ASSOCIATE", PARAMS)
        return res

    def Binding(self, CarrierID, LotID, NextStep, EQList, Priority):

        #self.logger.info("send binding cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "LOTID", "CPVAL": LotID})
        PARAMS.append({"CPNAME": "NEXTSTEP", "CPVAL": NextStep})
        PARAMS.append({"CPNAME": "EQLIST", "CPVAL": EQList})
        PARAMS.append({"CPNAME": "PRIORITY", "CPVAL": Priority})

        res=self.h.send_remote_cmd("BINDING", PARAMS)
        return res

    def Cancel(self, CommandID):

        #self.logger.info("send cancel cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "COMMANDID", "CPVAL": CommandID})

        res=self.h.send_remote_cmd("CANCEL", PARAMS)
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

    def Install(self, CarrierID, CarrierLoc):

        #self.logger.info("send install cmd.")

        PARAMS=[]
        PARAMS.append({"CPNAME": "CARRIERID", "CPVAL": CarrierID})
        PARAMS.append({"CPNAME": "CARRIERLOC", "CPVAL": CarrierLoc})

        res=self.h.send_remote_cmd("INSTALL", PARAMS)
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

    def Remove(self, CarrierID):

        #self.logger.info("send remove cmd.")

        PARAMS=[]
        PARAMS.append({"CARRIERID" : CarrierID})

        res=self.h.send_remote_cmd("REMOVE", PARAMS)
        return res

    def Resume(self):

        #self.logger.info("send resume cmd.")

        PARAMS=[]

        res=self.h.send_remote_cmd("RESUME", PARAMS)
        return res

    def Retry(self, ErrorID):

        #self.logger.info("send retry cmd.")

        PARAMS=[]
        PARAMS.append({"ERRORID" : ErrorID})

        res=self.h.send_remote_cmd("RETRY", PARAMS)
        return res

    def Transfer(self, DataID, ObjSpec, CommandID, Priority, CarrierID, SourcePort, DestPort):

        #self.logger.info("send transfer cmd.")
  

        PARAMS=[]
        CEPVALS=[]
        CEPVALS.append(["COMMANDID", CommandID])
        CEPVALS.append(["PRIORITY", Priority])
        PARAMS.append({"CPNAME": "COMMANDINFO", "CEPVAL": CEPVALS})
        CEPVALS=[]
        CEPVALS.append(["CARRIERID", CarrierID])
        CEPVALS.append(["SOURCEPORT", SourcePort])
        CEPVALS.append(["DESTPORT", DestPort])
        PARAMS.append({"CPNAME": "TRANSFERINFO", "CEPVAL": CEPVALS})

        res=self.h.send_enhance_remote_cmd(DATAID, OBJSPEC, "TRANSFER", PARAMS)
        return res


    def enable(self):
        self.h.enable()
        sleep(1)
        self.h.send_prime_message(self.h.stream_function(1, 17)())

    def disable(self):
        self.h.disable()

