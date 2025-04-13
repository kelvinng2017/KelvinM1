import secsgem
import logging
from collections import OrderedDict
from secsgem.secs.dataitems import ALED, ACKC5, ACKC6


class Host(secsgem.GemHostHandler):
    def __init__(self, address, port, active, session_id, name='MES_TEST', log_name='hsms_communication', mdln='TEST1.0', T3=45, T5=10, T6=5, T7=10, T8=5, custom_connection_handler=None):
        secsgem.GemHostHandler.__init__(self, address, port, active, session_id, name, custom_connection_handler)

        self.connection.T3=T3
        self.connection.T5=T5
        self.connection.T6=T6
        self.connection.T7=T7
        self.connection.T8=T8

        self.communicationLogger=logging.getLogger(log_name)
        self.communicationLogger.setLevel(logging.DEBUG)
        self.CarrierID=''
        self.Callback=None
        self.EventList={
        }
        self.AlarmList={
        }


    def _on_alarm_received(self, ALCD, ALID, ALTX, system):
        print(ALCD, ALID, ALTX)
        if self.Callback:
            kwargs=OrderedDict()
            kwargs['Set']=(ALCD&0b10000000>0)
            kwargs['ALTX']=ALTX
            self.Callback(str(ALID), **kwargs)
            # self.Callback(self.AlarmList[ALID][0], (ALCD&0b10000000>0), ALTX)
        self.send_response(self.stream_function(5, 2)(ACKC5.ACCEPTED), system)

    def _on_s05f01(self, handler, packet):
        """Callback handler for Stream 5, Function 1, Alarm request

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        message=self.secs_decode(packet)

        obj=OrderedDict()
        obj['ALCD']=message.ALCD.get()
        obj['ALID']=message.ALID.get()
        obj['ALTX']=message.ALTX.get()

        result=self._callback_handler.alarm_received(obj['ALCD'], obj['ALID'], obj['ALTX'], packet.header.system)


    def _on_collection_event_received(self, CEID, RPT, system):
        print(CEID, RPT, system)
        if self.Callback:
            if CEID in self.EventList:
                kwargs=OrderedDict()
                if RPT and (CEID+5000) in RPT:
                    for idx, key in enumerate(self.EventList[CEID][1:]):
                        kwargs[key]=RPT[CEID+5000][idx]
                self.Callback(self.EventList[CEID][0], **kwargs)
            else:
                check=False
                ALID=0
                for ALID in self.AlarmList:
                    if str(CEID) in ['1'+str(ALID), '2'+str(ALID)]:
                        check=True
                        break
                if check:
                    kwargs=OrderedDict()
                    kwargs['ALID']=ALID
                    if RPT and int('5'+str(ALID)) in RPT:
                        for idx, key in enumerate(self.AlarmList[ALID][1:]):
                            kwargs[key]=RPT[int('5'+str(ALID))][idx]
                    if str(CEID)[0] == '1':
                        name='AlarmSet' + str(ALID)
                    else:
                        name='AlarmClear' + str(ALID)
                    self.Callback(name, **kwargs)
        self.send_response(self.stream_function(6, 12)(ACKC6.ACCEPTED), system)

    def _on_s06f11(self, handler, packet):
        """Callback handler for Stream 6, Function 11, Establish Communication Request

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        message=self.secs_decode(packet)

        obj=OrderedDict()
        obj['CEID']=message.CEID.get()
        obj['RPT']={}
        for report in message.RPT:
            rpid=report.RPTID.get()
            obj['RPT'][rpid]=[]
            for sv in report.V:
                obj['RPT'][rpid].append(sv.get())

        self._callback_handler.collection_event_received(obj['CEID'], obj['RPT'], packet.header.system)


    def send_remote_cmd(self, rcmd, params):

        obj=OrderedDict()
        obj['RCMD']=rcmd
        obj['PARAMS']=[]
        for param in params:
            obj['PARAMS'].append(param)

        try:
            response=self.send_and_waitfor_response(self.stream_function(2, 41)(obj))
        except:
            response=None
        if response and response.header.function == 42:
            message=self.secs_decode(response)
            return message.HCACK.get(), message.PARAMS
        return -1, {}

    def send_enhance_remote_cmd(self, dataid, objspec, ercmd, params):

        obj=OrderedDict()
        obj['DATAID']=dataid
        obj['OBJSPEC']=objspec
        obj['RCMD']=ercmd
        obj['PARAMS']=[]
        for param in params:
            obj['PARAMS'].append(param)

        try:
            response=self.send_and_waitfor_response(self.stream_function(2, 49)(obj))
        except:
            response=None
        if response and response.header.function == 50:
            message=self.secs_decode(response)
            return message.HCACK.get(), message.PARAMS
        return -1, {}
