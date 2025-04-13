# -*- coding: utf-8 -*-

import threading
import traceback
import time
import os
import logging
import logging.handlers as log_handler
import collections
import json
# import re
# import alarms
#from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime


class MyException(Exception):
    pass


class LinkLostWarning(MyException):
    def __init__(self, txt='linking timeout'):
        self.alarm_set = 'Error'
        self.code = 50003
        self.txt = txt


class OVENAdapter(threading.Thread):
    def __init__(self, setting):
        super(OVENAdapter, self).__init__()
        self.listeners = []
        self.heart_beat = 0
        self.ip = setting.get('ip', '127.0.0.1')
        self.port = setting.get('port', 502)
        self.device_id = setting.get('DeviceID', "OVENAdapter")
        self.OVENAdapter_amount = 1
        self.write_address = 6448
        self.read_address = 7448

        self.check_flag = False
        self.modbus_timeout = setting.get('modbus_timeout', 2)
        self.stop_event = threading.Event()
        self.cmd_executing = False
        self.lock = threading.Lock()
        self.last_write_date = None

        self.write_address_mapping = {
                "LD_TR_Req": self.write_address + 0,
                "LD_Busy": self.write_address + 1,
                "LD_TR_Comple": self.write_address + 2,
                "ULD_TR_Req": self.write_address + 32,
                "ULD_Busy": self.write_address + 33,
                "ULD_TR_Comple": self.write_address + 34,
        }

        self.read_address_mapping = {
                "LD_Load_Req": 0,
                "LD_Ready": 1,
                "ULD_UnLoad_Req": 32,
                "ULD_Ready": 33,
        }

        self.client = ModbusTcpClient(host=self.ip, port=self.port)

        self.logger = logging.getLogger(self.device_id)
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
            h.close()
        self.logger.setLevel(logging.DEBUG)

        self.OVENAdapter = collections.OrderedDict({
            "device_id": self.device_id,
            "link": "Disconnect",
            "syncing_time": 0,
        })

        # 只處理單一設備
        for i in range(self.OVENAdapter_amount):
            self.OVENAdapter[i] = collections.OrderedDict({
                "LD": collections.OrderedDict({
                    "Ready": False,
                    "Load_Req": "Undefined",
                }),
                "ULD": collections.OrderedDict({
                    "Ready": False,
                    "UnLoad_Req": "Undefined",
                })
            })
        # for i in range(self.OVENAdapter_amount):
        #     self.OVENAdapter[i] = collections.OrderedDict({
        #         "LD_Ready": False,
        #         "LD_Load_Req": "Undefined",
        #         "ULD_Ready": False,
        #         "ULD_UnLoad_Req": "Undefined",
        #     })

        filename = os.path.join("log", "Gyro_{}.log".format(self.device_id))
        MRLogFileHandler = log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30)
        MRLogFileHandler.setLevel(logging.DEBUG)
        MRLogFileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(MRLogFileHandler)

        # For console. Mike: 2021/07/16
        streamLogHandler = logging.StreamHandler()
        streamLogHandler.setLevel(logging.INFO)
        streamLogHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(streamLogHandler)

    def add_listener(self, obj):
        self.listeners.append(obj)

    def notify(self, event):
        # self.logger.debug('[notify] {}'.format(event))
        # print(('[notify] {}'.format(event)))
        for obj in self.listeners:
            obj.on_notify(*event)

    def update_params(self, setting):
        self.device_id = setting.get('device_id', 'ELV')

    def update_OVENAdapter_status(self, status_data):
        # 更新狀態的邏輯
        self.OVENAdapter['status'] = status_data

    def LD_RequestTransport(self):
        print("Attempting to TR_Req. ON: {}".format("Load"))
        if self.OVENAdapter[0]["LD"]["Load_Req"] is False:
            print('Load Req is OFF')
            return False
        print("OVENAdapter LD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Request On')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["LD_TR_Req"],
                value=1,
                unit=1
            )
            print('OVENAdapter Request On')
            return True

    def LD_ApproveTransport(self):
        print("Attempting to BUSY ON: {}".format("Load"))
        if self.OVENAdapter[0]["LD"]["Ready"] is False:
            print('Load Ready is OFF')
            return False
        print("OVENAdapter LD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Ready On')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["LD_Busy"],
                value=1,
                unit=1
            )
            print('OVENAdapter Busy On')
            return True

    def LD_CheckPresence(self):
        print("Attempting to CheckPresence : {}".format("Load"))
        if self.OVENAdapter[0]["LD"]["Load_Req"] is True:
            print('Load Requset is On')
            return False
        print("OVENAdapter LD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Load Request OFF')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["LD_TR_Req"],
                value=0,
                unit=1
            )
            self.client.write_register(
                address=self.write_address_mapping["LD_Busy"],
                value=0,
                unit=1
            )
            self.client.write_register(
                address=self.write_address_mapping["LD_TR_Comple"],
                value=1,
                unit=1
            )
            print('OVENAdapter LD_TR_Comple On')
            return True


    def LD_VerifyDevicePins(self):
        print("Attempting to VerifyEQ: {}".format("Load"))
        if self.OVENAdapter[0]["LD"]["Ready"] is True:
            print('Load Ready is On')
            return False
        print("OVENAdapter LD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Ready OFF')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["LD_TR_Comple"],
                value=0,
                unit=1
            )
            print('OVENAdapter LD_TR_Comple OFF')
            return True


    def ULD_RequestTransport(self):
        print("Attempting to TR_Req. ON: {}".format("UnLoad"))

        if self.OVENAdapter[0]["ULD"]["UnLoad_Req"] is False:
            print('UnLoad Req is OFF')
            return False
        print("OVENAdapter ULD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Request On')
        with self.lock:

            self.client.write_register(
                address=self.write_address_mapping["ULD_TR_Req"],
                value=1,
                unit=1
            )
            print('OVENAdapter Request On')
            return True


    def ULD_ApproveTransport(self):
        print("Attempting to BUSY ON: {}".format("UnLoad"))
        if self.OVENAdapter[0]["ULD"]["Ready"] is False:
            print('UnLoad Ready is OFF')
            return False
        print("OVENAdapter ULD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Ready On')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["ULD_Busy"],
                value=1,
                unit=1
            )
            print('OVENAdapter Ready On')
            return True


    def ULD_CheckPresence(self):
        print("Attempting to CheckPresence : {}".format("UnLoad"))
        if self.OVENAdapter[0]["ULD"]["UnLoad_Req"] is True:
            print('UnLoad Request is On')
            return False
        print("OVENAdapter ULD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Load Request OFF')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["ULD_TR_Req"],
                value=0,
                unit=1
            )
            self.client.write_register(
                address=self.write_address_mapping["ULD_Busy"],
                value=0,
                unit=1
            )
            self.client.write_register(
                address=self.write_address_mapping["ULD_TR_Comple"],
                value=1,
                unit=1
            )
            print('OVENAdapter ULD_TR_Comple On')
            return True


    def ULD_VerifyDevicePins(self):
        print("Attempting to VerifyEQ: {}".format("UnLoad"))
        if self.OVENAdapter[0]["ULD"]["Ready"] is True:
            print('UnLoad Ready is On')
            return False
        print("OVENAdapter ULD not_cmd_executing")
        print("not_cmd_executing")
        self.logger.info('Ready OFF')
        with self.lock:
            self.client.write_register(
                address=self.write_address_mapping["ULD_TR_Comple"],
                value=0,
                unit=1
            )
            print('OVENAdapter ULD_TR_Comple OFF')
            return True



    def run(self):
        while not self.stop_event.is_set():
            try:
                self.heart_beat = time.time()
                if self.OVENAdapter['link'] == 'Disconnect':
                    # 嘗試連線至 Modbus server
                    if not self.client.connect():
                        self.logger.warning("Failed to connect to Modbus server: {}:{}".format(self.ip, self.port))
                        time.sleep(1)
                        continue
                    self.logger.info('Modbus Connected: {}, {}:{}'.format(self.device_id, self.ip, self.port))
                    self.OVENAdapter['link'] = 'Unsynced'
                    self.OVENAdapter['syncing_time'] = time.time()
                else:
                    try:
                        # all register is OUT to read status
                        results = []  # 用于存储所有读取的结果
                        group_size = 125  # 每组读取125个寄存器
                        total_registers = 64 * self.OVENAdapter_amount  # 需要读取的总寄存器数

                        for start in range(0, total_registers, group_size):
                            count = min(group_size, total_registers - start)  # 确保不会超出剩余寄存器数
                            result = self.client.read_holding_registers(address=self.read_address + start, count=count, unit=1)
                            results.extend(result.registers)

                        for i in range(self.OVENAdapter_amount):
                            self.OVENAdapter[i]['LD']['Ready'] = results[self.read_address_mapping['LD_Ready']+64*i] == 1
                            self.OVENAdapter[i]['LD']['Load_Req'] = results[self.read_address_mapping['LD_Load_Req']+64*i] == 1

                            self.OVENAdapter[i]['ULD']['Ready'] = results[self.read_address_mapping['ULD_Ready']+64*i] == 1
                            self.OVENAdapter[i]['ULD']['UnLoad_Req'] = results[self.read_address_mapping['ULD_UnLoad_Req']+64*i] == 1

                        self.OVENAdapter['link'] = 'Synced'
                        self.OVENAdapter['syncing_time'] = time.time()

                        # 印出狀態，調試用
                        # print(json.dumps(dict(self.oven), indent=4))

                    except Exception as e:
                        self.logger.warning('Error during Modbus communication: {}'.format(e))
                        self.OVENAdapter['link'] = 'Unsynced'
                        if time.time() - self.oven['syncing_time'] > self.modbus_timeout:
                            self.logger.info('LinkLostWarning')
                            raise ConnectionAbortedError('LinkLostWarning')
                            # raise alarms.LinkLostWarning(self.device_id)
                    time.sleep(0.1)
            except Exception:
                traceback.print_exc()
                self.logger.warning('\n'+traceback.format_exc())
                self.OVENAdapter['link'] = 'Disconnect'
                self.client.close()
                self.logger.info('<<Modbus Closed>>')
                time.sleep(1)

        self.client.close()
        self.logger.info('<<Modbus Closed>>')
        self.logger.info('{} end.'.format(self.device_id))

    def stop(self):
        self.stop_event.set()

# 192.168.5.71
# 192.168.1.216


if __name__ == '__main__':
    setting = {}
    setting['ip'] = '192.168.5.71'
    setting['port'] = 502
    setting['device_id'] = "OVENAdapter"
    setting['modbus_timeout'] = 10
    h = OVENAdapter(setting)
    h.start()

    try:
        while True:
            print("in try")
            res = raw_input('please input:')
            print ('res',res)
            if res:
                print("in res")
                print("cmds",res)
                cmds = res.split(',')
                if cmds[0] == 'LDReq':  # LD_Request,1
                    h.LD_RequestTransport()
                elif cmds[0] == 'LDApp':  # LD_Approve,1
                    h.LD_ApproveTransport()
                elif cmds[0] == 'LDChe':  # LD_Check,1
                    h.LD_CheckPresence()
                elif cmds[0] == 'LDVeri':  # LD_Verify,1
                    h.LD_VerifyDevicePins()
                elif cmds[0] == 'ULDReq':  # ULD_Request,1
                    h.ULD_RequestTransport()
                elif cmds[0] == 'ULDApp':  # ULD_Approve,1
                    h.ULD_ApproveTransport()
                elif cmds[0] == 'ULDChe':  # ULD_Check,1
                    h.ULD_CheckPresence()
                elif cmds[0] == 'ULDVeri':  # ULD_Verify,1
                    h.ULD_VerifyDevicePins()
                elif cmds[0] == 'check':
                    pass
                # 在此可以添加更多的指令處理邏輯
            print(json.dumps(dict(h.OVENAdapter[0]), indent=4))
            # print(json.dumps(dict(h.OVENAdapter), indent=4))
    except:
        print("GG")
        traceback.print_exc()
        pass

    h.stop()
    h.join()
    print("執行緒已關閉")
