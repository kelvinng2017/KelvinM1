# -*- coding: utf-8 -*-

import threading
import traceback
import time
import os
import logging
import logging.handlers as log_handler
import collections
import json
import re
# import alarms
from datetime import datetime
from pymodbus.client.sync import ModbusTcpClient

class MyException(Exception):
    pass

class LinkLostWarning(MyException):
    def __init__(self, txt='linking timeout'):
        self.alarm_set='Error'
        self.code=50003
        self.txt=txt

class OVEN(threading.Thread):
    def __init__(self, setting):
        super(OVEN, self).__init__()
        self.listeners=[]
        self.heart_beat=0
        self.ip = setting.get('ip', '127.0.0.1')
        self.port = setting.get('port', 502)
        self.device_id=setting.get('device_id', "OVEN1")
        self.oven_amount = 28
        self.write_address = 6000
        self.read_address = 7000
        self.check_flag = False


        self.upper_write_address = self.write_address
        self.upper_read_index = 0

        self.lower_write_address = self.upper_write_address + 16  
        self.lower_read_index = self.upper_read_index + 16

        self.modbus_timeout=setting.get('modbus_timeout', 2)
        self.stop_event = threading.Event()
        self.cmd_executing = False
        self.lock = threading.Lock()
        self.last_write_date = None
        self.write_address_mapping = {
                "Robot is Ready": self.write_address + 0,
                "Robot out the safety area": self.write_address + 3,
                "Interlock ( 1 : online , 0 : offline )": self.write_address + 6,
                "Door open": self.write_address + 7,
                "Door close": self.write_address +  9,
                "Process start":self.upper_write_address+ 10,
                "Thermostat Reset":self.upper_write_address+ 11,
        }

#241125
        self.read_address_mapping = {
                "load/unload port is Ready": 0,
                "Door open position#1": 5,
                "Door close position": 7,
                "Auto Door not safety status": 8,
                "Status-Alarm": 9,
                "Status-Idle": 10,
                "Status-Run": 11,
                "Thermostat Alarm":12,
        }
        # self.read_address_mapping = {
        #     "top": {
        #         "load/unload port is Ready": 0,
        #         "Door open position#1": 5,
        #         "Door close position": 7,
        #         "Auto Door not safety status": 8,
        #         "Status-Alarm": 9,
        #         "Status-Idle": 10,
        #         "Status-Run": 11,
        #         "Thermostat Alarm":12,
        #     }
        # }
        #
        # self.read_address_mapping["bottom"] = {
        #     "load/unload port is Ready": self.read_address_mapping["top"]["load/unload port is Ready"] + 16, #16
        #     "Door open position#1": self.read_address_mapping["top"]["Door open position#1"] + 16, #21
        #     "Door close position": self.read_address_mapping["top"]["Door close position"] + 16, #23
        #     "Auto Door not safety status" :self.read_address_mapping["top"]["Auto Door not safety status"] + 16, #24
        #     "Status-Alarm":self.read_address_mapping["top"]["Status-Alarm"] + 16, #25
        #     "Status-Idle":self.read_address_mapping["top"]["Status-Idle"] + 16, #26
        #     "Status-Run":self.read_address_mapping["top"]["Status-Run"] + 16, #27
        #     "Thermostat Alarm":self.read_address_mapping["top"]["Thermostat Alarm"] + 16, #28            
        # }
        print(self.read_address_mapping)

        self.write_address_time = {
            "year": 7900,
            "month": 7901,
            "day": 7902,
            "hour": 7903,
            "minute": 7904,
            "second": 7905,
        }
        

        self.client = ModbusTcpClient(host=self.ip, port=self.port)

        self.logger = logging.getLogger(self.device_id)
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
            h.close()
        self.logger.setLevel(logging.DEBUG)

        self.oven = collections.OrderedDict({
            "device_id": self.device_id,
            "link": "Disconnect",
            "syncing_time": 0,
        })

        for i in range(self.oven_amount):
            self.oven[i] = collections.OrderedDict({
                "Ready": False,
                "DoorPosition": "Undefined",
                "TemperatureController Status": False,
                "Oven-Status": "Undefined",
            })

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
        self.device_id=setting.get('device_id', 'ELV')
    
    def init(self, oven_id):
        # Write Interlock status to online
        # Write Robot Ready status
        if not self.cmd_executing:
            print("Oven {}: Writing Interlock status to online...".format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Interlock ( 1 : online , 0 : offline )"] + 16 * oven_id,
                value=1,
                unit=1
            )  # online
            print("Oven {}: Interlock written successfully.".format(oven_id))
            print("Oven {}: Writing Robot Ready status...".format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Robot is Ready"] + 16 * oven_id,
                value=1,
                unit=1
            )
            print("Oven {}: Robot Ready status written successfully.".format(oven_id))
            self.cmd_executing = True

        # Check if oven is ready
        print("Oven {}: Checking if oven is ready...".format(oven_id))
        if not self.oven[oven_id]["Ready"]:  # Compare timing diagram
            print("Oven {}: Oven not ready".format(oven_id))
            return False  # not ready, wait forever
        print("Oven {}: Oven is ready.".format(oven_id))

        # Check if door is in closed position
        # print("Oven {}: Checking if door is in closed position...".format(oven_id))
        # if self.oven[oven_id]["DoorPosition"] != "Door Closed":
        #     print("Oven {}: Door not closed".format(oven_id))
        #     return False  # Stop if the door is not closed
        # print("Oven {}: Door is closed.".format(oven_id))

        # Check if oven status is idle
        print("Oven {}: Checking if oven status is idle...".format(oven_id))
        if self.oven[oven_id]["Oven-Status"] != "Idle":
            print("Oven {}: Oven not idle".format(oven_id))
            return False  # Stop if the oven is not idle
        print("Oven {}: Oven is idle.".format(oven_id))

        print("Oven {}: Initialization successful".format(oven_id))
        self.cmd_executing = False
        self.check_flag = True
        return True  # All checks passed

    def open_door(self, oven_id):
        print("Attempting to open door for oven: {}".format(oven_id))
        # print(self.oven)
        # print(json.dumps(dict(self.oven[oven_id]), indent=4))

        # if self.oven[oven_id]["Status-Alarm"]:
        #     msg = "Oven {}: Alarm detected! Aborting door open.".format(oven_id)
        #     print(msg)
        #     self.logger.warning("Alarm active on oven {}. Door open aborted.".format(oven_id))
        #     raise Exception(msg)  # <-- Throw an exception to terminate the process

        if not self.check_flag and not self.init(oven_id):  # if initial not pass
            print("Initialization failed for oven {}".format(oven_id))
            return False

        if not self.cmd_executing:
            print("Oven {}: not_cmd_executing".format(oven_id))
            print("not_cmd_executing")
            self.logger.info('open door')
            with self.lock:

                self.client.write_register(
                    address=self.write_address_mapping["Robot is Ready"] + 16 * oven_id,
                    value=1,
                    unit=1
                )
                self.client.write_register(
                    address=self.write_address_mapping["Door open"] + 16 * oven_id,
                    value=1,
                    unit=1
                )
                self.cmd_executing = True

        print("Oven {}: Waiting for the door to open.".format(oven_id))
        if self.oven[oven_id]["DoorPosition"] == "Door Opened":
            print("Oven {}: DoorPosition: Opened".format(oven_id))
            self.logger.info('open door completed for oven {}'.format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Door open"] + 16 * oven_id,
                value=0,
                unit=1
            )  # door opened remove
            self.cmd_executing = False
            self.check_flag = False
            return True

        return False  # not ready wait forever


    def close_door(self, oven_id):
        print("Attempting to close {} door for oven: ".format(oven_id))

        # if self.oven[oven_id]["Status-Alarm"]:
        #     msg = "Oven {}: Alarm detected! Aborting door open.".format(oven_id)
        #     print(msg)
        #     self.logger.warning("Alarm active on oven {}. Door open aborted.".format(oven_id))
        #     raise Exception(msg)  # <-- Throw an exception to terminate the process

        if not self.check_flag and not self.init(oven_id):   # if initial not pass
            print("Initialization failed for oven {}".format(oven_id))
            return False

        if not self.cmd_executing:
            self.logger.info('close door for oven {}'.format(oven_id))
            with self.lock:
                self.client.write_register(
                    address=self.write_address_mapping["Door close"]+ 16 * oven_id, 
                    value=1, 
                    unit=1
                )
            self.cmd_executing = True

        print("Oven {}: Waiting for the door to close.".format(oven_id))
        if self.oven[oven_id]["DoorPosition"] == "Door Closed":
            self.logger.info('close door completed for oven {}'.format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Door close"]+ 16 * oven_id, 
                value=0,
                unit=1
            )
            self.cmd_executing = False
            self.check_flag = False
            return True
        return False  # not ready wait forever

    def Reset_temperatureController(self, oven_id): 
        print("Attempting to Reset_temperatureController {} door for oven: ".format(oven_id))

        # if not self.check_flag and not self.init(oven_id):   # if initial not pass
        #     print("Initialization failed for oven {}".format(oven_id))
        #     return False

        if not self.cmd_executing: # add Judgment  idle
            if  not self.oven[oven_id]["TemperatureController Status"] and self.oven[oven_id]["Oven-Status"] != "Idle":

                print("Reset TemperatureController failed for oven {}".format(oven_id))
                return False

            print("not_cmd_executing for oven {}".format(oven_id))
            self.logger.info('TemperatureController-Reset for oven: {}'.format(oven_id))
            with self.lock:
                self.client.write_register(
                    address=self.write_address_mapping["Thermostat Reset"]+ 16 * oven_id, 
                    value=1,
                    unit=1
                )
                self.cmd_executing = True

        print("Oven {}: Waiting for the oven to reset temperature.".format(oven_id))
        if self.oven[oven_id]["Oven-Status"] == "Idle":
            self.logger.info('TemperatureController-Reset completed: {}'.format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Thermostat Reset"]+ 16 * oven_id, 
                value=0, 
                unit=1
            )
            self.cmd_executing = False
            self.check_flag = False
            return True
        return False


    def oven_start(self, oven_id):
        print("Attempting to start {} door for oven: ".format(oven_id))
        
        if not self.check_flag and not self.init(oven_id):   # if initial not pass
            print("Initialization failed for oven {}".format(oven_id))
            return False
        
        if not self.cmd_executing:
            if not self.oven[oven_id]["Oven-Status"] == "Idle":
                print("Start failed for oven {}".format(oven_id))
                return False

            print("not_cmd_executing for oven {}".format(oven_id))
            self.logger.info('Oven-Start for oven {}:'.format(oven_id))
            with self.lock:
                self.client.write_register(
                    address=self.write_address_mapping["Process start"]+ 16 * oven_id,
                    value=1,
                    unit=1
                )
                self.cmd_executing = True
        print("Oven {}: Waiting for the oven to start process.".format(oven_id))
        if self.oven[oven_id]["Oven-Status"] == "Running":
            print("Oven is now Running for oven {}".format(oven_id))
            self.logger.info('Oven-Start completed for oven {}:'.format(oven_id))
            self.client.write_register(
                address=self.write_address_mapping["Process start"]+ 16 * oven_id,
                value=0,
                unit=1
            )
            self.cmd_executing = False
            return True
        return False


    
    def time_check(self):
        current_date = datetime.now().date()

        # Check if a day has passed since the last write
        if self.last_write_date == current_date:
            #self.logger.info("No need to write time; already updated today.")
            return

        self.logger.info("Time check started.")
        with self.lock:
            now = datetime.now()
            datetime_values = [now.year, now.month, now.day, now.hour, now.minute, now.second]
            try:
                self.client.write_registers(address=self.write_address_time['year'], values=datetime_values, unit=1)
            except Exception as e:
                self.logger.error("Error occurred during time write: {}".format(e))
                return

        self.last_write_date = current_date  # Update the last write date
        self.logger.info("Time check completed.")

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.heart_beat = time.time()
                if self.oven['link'] == 'Disconnect':
                    # 嘗試連線至 Modbus server
                    if not self.client.connect():
                        self.logger.warning("Failed to connect to Modbus server: {}:{}".format(self.ip, self.port))
                        time.sleep(1)
                        continue
                    self.logger.info('Modbus Connected: {}, {}:{}'.format(self.device_id, self.ip, self.port))
                    self.oven['link'] = 'Unsynced'
                    self.oven['syncing_time'] = time.time()
                else:
                    try:#all register is OUT to read status
                        results = []  # 用于存储所有读取的结果
                        group_size = 125  # 每组读取125个寄存器
                        total_registers = 16 * self.oven_amount  # 需要读取的总寄存器数

                        for start in range(0, total_registers, group_size):
                            count = min(group_size, total_registers - start)  # 确保不会超出剩余寄存器数
                            result = self.client.read_holding_registers(address=self.read_address + start, count=count, unit=1)
                            results.extend(result.registers)
                        # print("results: {}".format(len(results)))
                        # print(result)
                        # self.time_check()

                        # self.logger.info('device {}: {}'.format(self.device_id, str(result.registers)))
#Ready
                        # # 更新烤箱狀態
                        # self.update_oven_status(result)
                        for i in range(self.oven_amount):
                            self.oven[i]['Ready'] = results[self.read_address_mapping['load/unload port is Ready']+16*i] == 1
#DoorPosition
                            if (results[self.read_address_mapping['Door open position#1']+16*i], results[self.read_address_mapping['Door close position']+16*i], results[self.read_address_mapping['Auto Door not safety status']+16*i]) == (1, 0, 0):    
                                self.oven[i]["DoorPosition"] = "Door Opened"
                            elif (results[self.read_address_mapping['Door open position#1']+16*i], results[self.read_address_mapping['Door close position']+16*i], results[self.read_address_mapping['Auto Door not safety status']+16*i]) == (0, 1, 0):    
                                self.oven[i]["DoorPosition"] = "Door Closed"
                            elif (results[self.read_address_mapping['Door open position#1']+16*i], results[self.read_address_mapping['Door close position']+16*i], results[self.read_address_mapping['Auto Door not safety status']+16*i]) == (0, 0, 1):    
                                self.oven[i]["DoorPosition"] = "Door not safety status"
                            else:
                                self.oven[i]["DoorPosition"] = "Undefined"
#TemperatureController Status
                            # if (results[self.read_address_mapping['Status-Idle']+16*i], results[self.read_address_mapping['Thermostat Alarm']+16*i]) == (1, 1):   
                            #     self.oven[i]["TemperatureController Status"] = "Need-To-Reset"
                            # elif (results[self.read_address_mapping['Status-Idle']+16*i], results[self.read_address_mapping['Thermostat Alarm']+16*i]) == (1, 0):   
                            #     self.oven[i]["TemperatureController Status"] = "Oven-Idle"
                            # else:
                            #     self.oven[i]["TemperatureController Status"] = "Undefined"
#TemperatureController Status
                            self.oven[i]["TemperatureController Status"] = results[self.read_address_mapping['Thermostat Alarm']+16*i] == 1                              
#OvenStatus
                            if (results[self.read_address_mapping['Status-Idle']+16*i], results[self.read_address_mapping['Status-Run']+16*i]) == (1, 0):    
                                self.oven[i]["Oven-Status"] = "Idle"
                            elif (results[self.read_address_mapping['Status-Idle']+16*i], results[self.read_address_mapping['Status-Run']+16*i]) == (0, 1):    
                                self.oven[i]["Oven-Status"] = "Running"
                            else:
                                self.oven[i]["Oven-Status"] = "Undefined"
                        ##############-old-###########
                        # self.oven['top']['Ready'] = result.registers[self.read_address_mapping['top']['load/unload port is Ready']] == 1   
                        # self.oven['bottom']['Ready'] = result.registers[self.read_address_mapping['bottom']['load/unload port is Ready']] == 1   
#OvenStatus-Alarm
                            self.oven[i]["Status-Alarm"] = results[self.read_address_mapping['Status-Alarm']+16*i] == 1
#DoorPosition
                        # if (result.registers[self.read_address_mapping['Door open position#1']]+16*i, result.registers[self.read_address_mapping['top']['Door close position']], result.registers[self.read_address_mapping['top']['Auto Door not safety status']]) == (1, 0, 0):    
                        #     self.oven['top']["DoorPosition"] = "Door Opened"
                        # elif (result.registers[self.read_address_mapping['top']['Door open position#1']], result.registers[self.read_address_mapping['top']['Door close position']], result.registers[self.read_address_mapping['top']['Auto Door not safety status']]) == (0, 1, 0):  
                        #     self.oven['top']["DoorPosition"] = "Door Closed"
                        # elif (result.registers[self.read_address_mapping['top']['Door open position#1']], result.registers[self.read_address_mapping['top']['Door close position']], result.registers[self.read_address_mapping['top']['Auto Door not safety status']]) == (0, 0, 1):  
                        #     self.oven['top']["DoorPosition"] = "Door not safety status"
                        # else:
                        #     self.oven['top']["DoorPosition"] = "Undefined"
                        # if (result.registers[self.read_address_mapping['bottom']['Door open position#1']], result.registers[self.read_address_mapping['bottom']['Door close position']], result.registers[self.read_address_mapping['bottom']['Auto Door not safety status']]) == (1, 0, 0):
                        #     self.oven['bottom']["DoorPosition"] = "Door Opened"
                        # elif (result.registers[self.read_address_mapping['bottom']['Door open position#1']], result.registers[self.read_address_mapping['bottom']['Door close position']], result.registers[self.read_address_mapping['bottom']['Auto Door not safety status']]) == (0, 1, 0):
                        #     self.oven['bottom']["DoorPosition"] = "Door Closed"
                        # elif (result.registers[self.read_address_mapping['bottom']['Door open position#1']], result.registers[self.read_address_mapping['bottom']['Door close position']], result.registers[self.read_address_mapping['bottom']['Auto Door not safety status']]) == (0, 0, 1):
                        #     self.oven['bottom']["DoorPosition"] = "Door not safety status"
                        # else:
                        #     self.oven['bottom']["DoorPosition"] = "Undefined"

#TemperatureController Status
                        # if (result.registers[self.read_address_mapping['top']['Status-Idle']], result.registers[self.read_address_mapping['top']['Thermostat Alarm']]) == (1, 1):   
                        #     self.oven['top']["TemperatureController Status"] = "Need-To-Reset"
                        # elif (result.registers[self.read_address_mapping['top']['Status-Idle']], result.registers[self.read_address_mapping['top']['Thermostat Alarm']]) == (1, 0):    
                        #     self.oven['top']["TemperatureController Status"] = "Oven-Idle"
                        # else:
                        #     self.oven['top']["TemperatureController Status"] = "Undefined"
                        # if (result.registers[self.read_address_mapping['bottom']['Status-Idle']], result.registers[self.read_address_mapping['bottom']['Thermostat Alarm']]) == (1, 1):   
                        #     self.oven['bottom']["TemperatureController Status"] = "Need-To-Reset"
                        # elif (result.registers[self.read_address_mapping['bottom']['Status-Idle']], result.registers[self.read_address_mapping['bottom']['Thermostat Alarm']]) == (1, 0):   
                        #     self.oven['bottom']["TemperatureController Status"] = "Oven-Idle"
                        # else:
                        #     self.oven['bottom']["TemperatureController Status"] = "Undefined"
#OvenStatus
                        # if (result.registers[self.read_address_mapping['top']['Status-Idle']], result.registers[self.read_address_mapping['top']['Status-Run']]) == (1, 0):    
                        #     self.oven['top']["Oven-Status"] = "Idle"
                        # elif  (result.registers[self.read_address_mapping['top']['Status-Idle']], result.registers[self.read_address_mapping['top']['Status-Run']]) == (0, 1):   
                        #     self.oven['top']["Oven-Status"] = "Running"
                        # else:
                        #     self.oven['top']["Oven-Status"] = "Undefined"
                        # if (result.registers[self.read_address_mapping['bottom']['Status-Idle']], result.registers[self.read_address_mapping['bottom']['Status-Run']]) == (1, 0):   
                        #     self.oven['bottom']["Oven-Status"] = "Idle"
                        # elif  (result.registers[self.read_address_mapping['bottom']['Status-Idle']], result.registers[self.read_address_mapping['bottom']['Status-Run']]) == (0, 1):   
                        #     self.oven['bottom']["Oven-Status"] = "Running"
                        # else:
                        #     self.oven['bottom']["Oven-Status"] = "Undefined"

                        self.oven['link'] = 'Synced'
                        self.oven['syncing_time'] = time.time()
                        # print(json.dumps(dict(self.oven[1]), indent=4)) #print json format
                    except Exception as e:
                        self.logger.warning('Error during Modbus communication: {}'.format(e))
                        self.oven['link'] = 'Unsynced'
                        if time.time() - self.oven['syncing_time'] > self.modbus_timeout:
                            self.logger.info('LinkLostWarning')
                            raise ConnectionAbortedError('LinkLostWarning')
                            # raise alarms.LinkLostWarning(self.device_id)
                    time.sleep(0.1)
            except:
                traceback.print_exc()
                self.logger.warning('\n'+traceback.format_exc())
                self.oven['link'] = 'Disconnect'
                self.client.close()
                self.logger.info('<<Modbus Closed>>')
                time.sleep(1)

        self.client.close()
        self.logger.info('<<Modbus Closed>>')
        self.logger.info('{} end.'.format(self.device_id))

    def stop(self):
        self.stop_event.set()

#192.168.5.71
if __name__ == '__main__':
    setting = {}
    setting['ip'] = '192.168.1.216'
    setting['port'] = 502
    setting['device_id'] = "OVEN1"
    setting['modbus_timeout'] = 10
    h = OVEN(setting)
    h.start()
    # setting = {}
    # setting['ip'] = '192.168.56.1'
    # setting['port'] = 502
    # setting['address'] = 7032
    # setting['device_id'] = 'OVEN2'
    # setting['modbus_timeout'] = 10
    # h2 = OVEN(setting)
    # h2.start()

    try:
        while True:
            try: #richard 250505
                # Try Python3's input() first
                res = input('please input:') #go,215,300,180
            except NameError:
                # If NameError occurs, it means it is Python 2, use raw_input()
                res = raw_input('please input:') #go,215,300,18
            if res:
                cmds=res.split(',')
                if cmds[0] == 'open': # open,1
                    h.open_door(int(cmds[1]))
                elif cmds[0] == 'close':
                    h.close_door(int(cmds[1]))
                elif cmds[0] == 'reset':
                    h.Reset_temperatureController(int(cmds[1]))
                elif cmds[0] == 'start':
                    h.oven_start(int(cmds[1]))
                elif cmds[0] == 'init':
                    h.init(int(cmds[1]))
                elif cmds[0] == 'check':
                    pass
            print(json.dumps(dict(h.oven[20]), indent=4))
    except:
        traceback.print_exc()
        pass

    h.stop()
    # h2.stop()
    h.join()
    # h2.join()