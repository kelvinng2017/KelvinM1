import secsgem
import collections

import os
import logging
import logging.handlers as log_handler

class E82Host(secsgem.GemHostHandler):
    def __init__(self, address, port, active, session_id, name='MES_TEST', mdln='TEST1.0', T3=45, T5=10, T6=5, T7=10, T8=5, custom_connection_handler=None):
        secsgem.GemHostHandler.__init__(self, address, port, active, session_id, name, custom_connection_handler)
        
        self.CarrierID=''
        self.event_list=collections.deque()

        self.communicationLogger=logging.getLogger("E82_hsms_communication") # Mike: 2020/07/16
        self.communicationLogger.setLevel(logging.DEBUG)

        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "CIM_E82.log"), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.INFO)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.communicationLogger.addHandler(fileHandler)


    def _on_s06f11(self, handler, packet):
        """Callback handler for Stream 6, Function 11, Establish Communication Request

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        del handler  # unused parameters

        message=self.secs_decode(packet)
        
        obj={}
        obj['CEID']=message.CEID.get()
        obj['RPT']={}
        for report in message.RPT:
            rpid=report.RPTID.get()
            obj['RPT'][rpid]=[]
            for sv in report.V:
                obj['RPT'][rpid].append(sv.get())
        
        # self.logger.info("get event. {}".format(obj))
        self.event_list.append(obj)

        self.send_response(self.stream_function(6, 12)(0), packet.header.system)


    def binding(self, LotID, NextStep, EQList, Priority):
        """Disable alarm

        :param alid: alarm id to disable
        :type alid: :class:`secsgem.secs.dataitems.ALID`
        """
        # self.logger.info("send binding cmd.")

        return self.send_prime_message(self.stream_function(2, 41)(\
        {
            "RCMD": "BINDING",
            "PARAMS": 
            [
                {"CPNAME": "CARRIERID", "CPVAL": self.CarrierID}, 
                {"CPNAME": "LOTID", "CPVAL": LotID}, 
                {"CPNAME": "NEXTSTEP", "CPVAL": NextStep}, 
                {"CPNAME": "EQLIST", "CPVAL": EQList}, 
                {"CPNAME": "PRIORITY", "CPVAL": Priority},
            ]
        }))


    def transfer_cmd(self, DATAID, OBJSPEC, COMMANDID, PRIORITY, REPLACE, CARRIERID, SOURCEPORT, DESTPORT):
        """Disable alarm

        :param alid: alarm id to disable
        :type alid: :class:`secsgem.secs.dataitems.ALID`
        """
        # self.logger.info("send transfer cmd.")

        return self.send_prime_message(self.stream_function(2, 49)(
        {
            "DATAID": DATAID,
            "OBJSPEC": OBJSPEC,
            "RCMD": "TRANSFER",
            "PARAMS": 
            [
                {
                    "CPNAME": "COMMANDINFO", 
                    "CEPVAL": 
                    [
                        ["COMMANDID", COMMANDID], 
                        ["PRIORITY", PRIORITY],
                        ["REPLACE", REPLACE],
                    ]
                },
                {
                    "CPNAME": "TRANSFERINFO", 
                    "CEPVAL": 
                    [
                        ["CARRIERID", CARRIERID],
                        ["SOURCEPORT", SOURCEPORT],
                        ["DESTPORT", DESTPORT],
                    ]
                },
            ]
        }))
