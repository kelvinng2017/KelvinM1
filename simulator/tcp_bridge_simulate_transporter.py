#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

import time
from datetime import datetime
import threading
import subprocess
from threading import Timer
import json
#import requests
import socket

#import pickle
import math
from collections import deque
import traceback
import queue
import argparse

import random
import six

class tcp_bridge:
    def __init__(self, port, initial_point):
        self.soft_ver="06C"
        self.spec_ver="2.6"

        self.bind_ip='127.0.0.1'
        self.bind_port=port
        self.num_slots=4

        # Mike: 2021/08/25
        self.charge_rate=30*60/50
        self.discharge_rate=5*60*60/50
        self.charge_status=0
        self.exchange_status=0
        self.robot_time=20 #45 default
        #self.robot_time=33 #for GB real
        self.exchange_time=4.5 #45 default
        self.go_delay=0.5
        #self.go_delay=2 #for GB real
        self.end_delay=0.5
        #self.end_delay=4 #for GB real
        self.angular_speed=30
        self.buffer_num=2
        self.use_readfail_carrier=True

        self.current_map=''

        self.input_buffer=deque()
        self.output_buffer=deque()

        self.move_cmd_queue=deque()

        self.system_byte_counter=0
        self.is_block=0
        self.blocking=False
        self.stop_move=False

        self.client_handler=None
        self.output_sending_thread=None
        self.input_handler_thread=None
        self.testcount=0
        self.errorcode_dict={
            "emergentstop" : "100000",
            "movewhenrobotnothome": "100001",
            "roboterror": "100002",
            "notinchargeposition": "100003",
            "e84chargeabnormal": "100004",
            "chargeronfail": "100006",
            "chargerofffail": "100007",
            "DockNG": "100008",
            "LoadUnloadFail": "100009",
            "movewhencharging": "100010",
            # "movewhenalarm": "100011",
            "BattFullCharge": "100012",
            "BattOT": "100013",
            "BattOvrVolt": "100014",
            "BattOvrChrgCurrent": "100015",
            "LoadUnloadMacroIncorrect": "100016",
            "LoadUnloadE84Fail": "100017",
            "IncorrectCoordinate": "100018",
            "MoveFail": "100019",
            "RFIDReaderAbnormal": "100020",
            "PositionError": "100021",
            "IncorrectRobotCommand": "100022",
            "LoadUnloadNotReady": "100023",
            "AGVMConnectionAbnormal": "100024",
            "RobotCmdWrongStation": "100025",
            "RobotCmdWhenMoving": "100026",
            "FromPortEmpty": "100027",
            "ToPortFull": "100028"
        }


        self.jsonstatus={
                    "ACK" : 'OK',
                    "OPMODE" : "",
                    "ChargeStation" : False,
                    "state" : 'initial',    #(standby, moving, charging, manual, initial)
                    "pose" : [0, 0, 0, 0],   # xCoordinate(mm),yCoordinate(mm),zCoordinate(mm),orientation(deg)


                    "speed" : {
                        "linear" : [0, 0, 0, 0],
                        "angular": [0, 0, 0, 0]
                    },
                    "wheelpwms": [0, 0, 0, 0, 0],
                    "battery" : {
                        "battery_level": 80+random.randint(-10, 10), # Integer (0-100 represents percent charged)
                        "battery_current":3000,
                        "battery_voltage": 10,
                        "battery_remain_capacity" : [80,70],
                        "battery_temperature" : 30,
                        "full": False,
                        "chargeovervolt": False,
                        "chargeovercurrent": False,
                        "chargeovertemperature": False
                    },
                    "robot":{
                        "status" : "0",
                        "coordinate": [0,0,0],
                        "home" : "1"
                    },
                    "cassette" : [
                        {
                            "id" : "",
                            "old_id":"",
                            "port":4,
                            "loading": False
                        } for i in range(self.buffer_num)
                    ],
                    "e84job": "",
                    "e84state": "",
                    "station_id" : "1",      # string
                    "command_id": "",
                    "stop_status": "",
                    "error" : False,
                    "MoveappendQSize": 0,
                    "LoadUnloadQSize": 0,
                    "canrobot": False,
                    "emergentstop": False,
                    "alarm" : {
                        "100000": False,
                        "100001": False,
                        "100002": False,
                        "100003": False,
                        "100004": False,
                        "100005": False,
                        "100006": False,
                        "100007": False,
                        "100008": False,
                        "100009": False,
                        "100010": False,
                        "100011": False,
                        "100012": False,
                        "100013": False,
                        "100014": False,
                        "100015": False,
                        "100016": False,
                        "100017": False,
                        "100018": False,
                        "100019": False,
                        "100020": False,
                        "100021": False,
                        "100022": False,
                        "100023": False,
                        "100024": False,
                        "100025": False,
                        "100026": False,
                        "100027": False,
                        "100028": False
                    },
                    "isCharging": 0,
                    "lastsysbyte":{
                        "P41": "",
                        "P45": ""
                    }
                 }

        self.jsonnak={
                     "ACK" : 'NG'
                 }

        #initial
        self.jsonstatus["robot"]["status"]="0"
        self.jsonstatus["command_id"]=""
        self.jsonstatus["error"]=False
        self.jsonstatus["state"]="standby"

        self.jsonstatus["emergentstop"]=False
        for errorcode in self.jsonstatus["alarm"]:
            self.jsonstatus["alarm"][errorcode]=False

        self.jsonstatus["isCharging"]=0

        self.jsonstatus["pose"][0]=pose_mapping[initial_point][0]
        self.jsonstatus["pose"][1]=pose_mapping[initial_point][1]
        self.jsonstatus["pose"][3]=pose_mapping[initial_point][3]

        self.current_map=pose_mapping[initial_point][4]

        for i in range(self.buffer_num):
            self.jsonstatus["cassette"][i]["id"]='Unknown'

        print("initial pose:{}, {}".format(initial_point, self.jsonstatus["pose"]))

        self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket=None
        self.automode=False


    def handle_client_connection(self, client_socket):
        print("start handle_client_connection")
        msg=b''
        raw_rx=b''
        msg_len=0

        while self.keepThreadAlive:
            time.sleep(0.005)
            try:
                buf=client_socket.recv(1024)
                if(len(buf)>0):
                    raw_rx += buf
                while len(raw_rx)>0:
                    if six.PY2:
                        msg_len=ord(raw_rx[0])
                    else:
                        msg_len=raw_rx[0]
                    if len(raw_rx) >= msg_len+5:
                        msg=raw_rx[:msg_len+5]
                        self.input_buffer.appendleft(msg)
                        raw_rx=raw_rx[msg_len+5:]
                    else:
                        break
            except Exception as e:
                print("Exception found:\n{}".format(e))
                pass
        print("exit handle_client_connection")

    def input_handler(self, client_socket):
        print("start input_handler")

        while(self.keepThreadAlive):
            if(len(self.input_buffer)>0):
                raw_rx=self.input_buffer.pop()
                #print(raw_rx)
                pkglen=0
                if(raw_rx != ''):
                    #print("package received:"+raw_rx[1:-4])
                    if six.PY2:
                        pkglen=ord(raw_rx[0])
                    else:
                        pkglen=raw_rx[0]
                    data_str=raw_rx[1:pkglen+1]
                    payload=str(data_str)
                if six.PY3:
                    raw_rx=raw_rx.decode()
                   
                if pkglen > 2:
                    #print("Xnn: " + raw_rx[1:4])
                    try:
                        if raw_rx[1] == 'P': #echo ack only for P mas
                            #print("package received:"+raw_rx[1:-4])
                            total_pos='%c%02d'%('S', int(raw_rx[2:4])+1)

                        if (raw_rx[1:4] == "P31"):    # Status Report Request
                            # total_pos="S32"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            if(raw_rx[4] == "0"):
                                # All status report
                                print("Send all status report")
                                self.move_status_report()
                                # time.sleep(0.5)
                                self.robot_status_report()
                                # time.sleep(0.5)
                                self.cassette_status_report()
                                # time.sleep(0.5)
                                self.charge_status_report(self.charge_status)
                                # all from 1~5
                            elif(raw_rx[4] == "1"):
                                # Move status report
                                print("Send move status report")
                                self.move_status_report()
                                # P21
                            elif(raw_rx[4] == "2"):
                                # Robot status report
                                print("Send robot status report")
                                self.robot_status_report()
                                # P23
                            elif(raw_rx[4] == "3"):
                                # Cassette status report
                                print("Send cassette status report")
                                self.cassette_status_report()
                                # P25
                            elif(raw_rx[4] == "4"):
                                # Charge status report
                                print("Send charge status report")
                                self.charge_status_report(self.charge_status)
                            elif(raw_rx[4] == "5"):
                                # Map report
                                print("Send map report")
                                self.map_report()


                        elif (raw_rx[1:4] == "P41"): # Move Append Request

                            no_go=False

                            endpoint="0"
                            if(raw_rx[4] == "1"):
                                print("END POINT MOVEAPPEND")
                                endpoint="1"

                            elif(raw_rx[4] == "2"):
                                print("Leave station")
                                endpoint="2"
                            else:
                                print("Report station")
                                endpoint="0"

                               
                            goal_x=int(raw_rx[6:14])
                            if(raw_rx[5] == "N"):
                                goal_x=0 - goal_x
                            goal_y=int(raw_rx[15:23])
                            if(raw_rx[14] == "N"):
                                goal_y=0 - goal_y
                            goal_w=int(raw_rx[23:26])
                            if(goal_w < 0):
                                goal_w=goal_w + 360

                            speed_limit=raw_rx[26:30]

                            leftright=raw_rx[30]

                            gokeep=raw_rx[31]

                            self.jsonstatus["lastsysbyte"]["P41"]=raw_rx[-4:]

                            total_pos += "1"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            params=(goal_x, goal_y, goal_w, speed_limit, endpoint, gokeep)
                            self.move_cmd_queue.appendleft({'move_cmd':params})


                        elif (raw_rx[1:4] == "P85"): # Move Append Request

                            no_go=False

                            print("Report station")
                            endpoint="0"

                               
                            goal_x=int(raw_rx[6:14])
                            if(raw_rx[5] == "N"):
                                goal_x=0 - goal_x
                            goal_y=int(raw_rx[15:23])
                            if(raw_rx[14] == "N"):
                                goal_y=0 - goal_y
                            goal_w=int(raw_rx[23:26])
                            if(goal_w < 0):
                                goal_w=goal_w + 360

                            speed_limit=raw_rx[26:30]

                            leftright=raw_rx[30]

                            gokeep=raw_rx[31]

                            self.jsonstatus["lastsysbyte"]["P85"]=raw_rx[-4:]

                            total_pos += "1"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            params=(goal_x, goal_y, goal_w, speed_limit, endpoint, gokeep)
                            self.move_cmd_queue.appendleft({'move_cmd':params})


                        elif (raw_rx[1:4] == "P47"):    # Charge Request
                            #total_pos="S48"
                            # time.sleep(0.5)
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))

                            direction=raw_rx[4]
                            if(direction == "0"):
                                self.dischargeThread=threading.Thread(target=self.discharge_request)
                                self.dischargeThread.setDaemon(True)
                                self.dischargeThread.start()

                            elif(direction == "1"):
                                self.chargeThread=threading.Thread(target=self.charge_request)
                                self.chargeThread.setDaemon(True)
                                self.chargeThread.start()

                      
                        elif (raw_rx[1:4] == "P71"):    # Exchange Request
                            #total_pos="S72"
                            total_pos += "1"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))

                            self.exchangeThread=threading.Thread(target=self.exchange_request)
                            self.exchangeThread.setDaemon(True)
                            self.exchangeThread.start()

                      
                        elif (raw_rx[1:4] == "P51"):    # Stop Request
                            if raw_rx[4] == "2":
                                #total_pos="S48"
                                # time.sleep(0.5)
                                self.stop_move=True
                                self.move_cmd_queue.clear()
                                total_pos += "1"
                                self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                                print('stop moving')

                        elif (raw_rx[1:4] == "P93"):    # Map Change Request
                            self.current_map=raw_rx[4:-4]
                            total_pos += "1"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            self.mapThread=threading.Thread(target=self.map_change_request)
                            self.mapThread.setDaemon(True)
                            self.mapThread.start()
                                
                        elif(raw_rx[1:4] == "P81"):
                          try:
                            #total_pos="S82"
                            status="7"
                            move_speed="0000"
                            move_speed='{:0>4d}'.format(int(self.jsonstatus["speed"]["linear"][0]))
                            move_direction="000"
                            move_direction='{:0>3d}'.format(int(self.jsonstatus["speed"]["angular"][0]))

                            if self.jsonstatus["error"]:
                                status="6"
                            elif(self.jsonstatus["stop_status"] == "Pause"):
                                status="3"
                            elif(self.jsonstatus["state"] == "standby"):
                                status="0"
                            else:
                                status="1"

                            x_pos=int(self.jsonstatus["pose"][0])
                            y_pos=int(self.jsonstatus["pose"][1])
                            w_pos=int(self.jsonstatus["pose"][3])
                            total_pos += status
                            if(x_pos < 0):
                                total_pos += "N"
                                total_pos += "{:0>8d}".format(0 - x_pos)
                            else:
                                total_pos += "P"
                                total_pos += "{:0>8d}".format(x_pos)
                            if(y_pos < 0):
                                total_pos += "N"
                                total_pos += "{:0>8d}".format(0 - y_pos)
                            else:
                                total_pos += "P"
                                total_pos += "{:0>8d}".format(y_pos)
                            total_pos += "{:0>3d}".format(w_pos)
                            total_pos += move_direction
                            total_pos += move_speed
                            total_pos += self.jsonstatus["robot"]["status"]
                            total_pos += self.jsonstatus["robot"]["home"]
                            # minimum_remain_capacity=min(self.jsonstatus["battery"]["battery_remain_capacity"])
                            # maximum_remain_capacity=max(self.jsonstatus["battery"]["battery_remain_capacity"])
                            # total_pos += '{:0>3d}'.format(abs(int(minimum_remain_capacity)))
                            total_pos += '{:0>3d}'.format(abs(self.jsonstatus["battery"]["battery_level"])) # Mike: 2021/07/30
                            total_pos += '{:0>4d}'.format(int(100*self.jsonstatus["battery"]["battery_voltage"]))
                            total_pos += '{:0>3d}'.format(int(self.jsonstatus["battery"]["battery_temperature"]))

                            #print(total_pos)
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                           
                          except:
                              traceback.print_exc()
                              pass
                           
                        elif(raw_rx[1:4] == "P83"): # robot control
                            # total_pos="S84"
                            total_pos += "0"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            #need add P23, P25, P53
                            self.robotThread=threading.Thread(target=self.robot_request)
                            self.robotThread.setDaemon(True)
                            self.robotThread.start()
                           
                        elif(raw_rx[1:4] == "P87"): # robot control
                            # total_pos="S88"
                            print('get > ', raw_rx)
                            from_port=raw_rx[raw_rx.find('<')+1:raw_rx.find('>')]
                            to_port=raw_rx[raw_rx.rfind('<')+1:raw_rx.rfind('>')]
                            if self.use_readfail_carrier:
                                if 'BUFFER' in from_port:
                                    idx=int(from_port[6:])-1
                                    self.jsonstatus["cassette"][idx]["id"]=''
                                    self.jsonstatus["cassette"][idx]["port"]=4
                                else:
                                    idx=int(to_port[6:])-1
                                    self.jsonstatus["cassette"][idx]["id"]='ReadIdFail'
                                    self.jsonstatus["cassette"][idx]["port"]=5
                            total_pos += "0"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            #need add P23, P25, P53
                            self.robotThread=threading.Thread(target=self.robot_request)
                            self.robotThread.setDaemon(True)
                            self.robotThread.start()
                           
                        elif(raw_rx[1:4] == "P45"): # robot control
                            # total_pos="S46"
                            print('get > ', raw_rx)
                            from_port=raw_rx[raw_rx.find('<')+1:raw_rx.find('>')]
                            to_port=raw_rx[raw_rx.rfind('<')+1:raw_rx.rfind('>')]
                            if self.use_readfail_carrier:
                                if 'BUFFER' in from_port:
                                    idx=int(from_port[6:])-1
                                    self.jsonstatus["cassette"][idx]["id"]=''
                                    self.jsonstatus["cassette"][idx]["port"]=4
                                else:
                                    idx=int(to_port[6:])-1
                                    self.jsonstatus["cassette"][idx]["id"]='ReadIdFail'
                                    self.jsonstatus["cassette"][idx]["port"]=5
                            total_pos += "0"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            #need add P23, P25, P53
                            self.robotThread=threading.Thread(target=self.robot_request)
                            self.robotThread.setDaemon(True)
                            self.robotThread.start()
                           
                        elif(raw_rx[1:4] == "P27"): # cassette rename
                            idx=int(raw_rx[4:6])-1
                            self.jsonstatus["cassette"][idx]["id"]=raw_rx[6:-4]
                            print('Rename {}: {}'.format(idx+1, self.jsonstatus["cassette"][idx]["id"]))
                            # total_pos="S28"
                            total_pos += "0"
                            self.output_buffer.appendleft((total_pos, bytearray(raw_rx[-4:].encode())))
                            self.cassette_status_report()

                        elif (raw_rx[1:4] == "P17"): # version Request # Mike: 2021/07/16
                            total_pos += 'Sw{:<13}Sp{}'.format(self.soft_ver, self.spec_ver)
                            self.output_buffer.appendleft(total_pos)

                        elif (raw_rx[1:4] == "S18"): # version Request
                            print('version: {}'.format(raw_rx[4:]))
                            
                    except:
                        traceback.print_exc()
                        pass

            time.sleep(0.005)
        print("exit input_handler")


    def sendMessage(self, msg, system_byte=None):
        #print('sendMessage:', msg)
        lendata=len(msg)
        if(system_byte == None):
            system_byte=bytearray('{:04d}'.format(self.system_byte_counter).encode())
            self.system_byte_counter += 1
            self.system_byte_counter=self.system_byte_counter % 10000
            #self.system_byte_counter=self.system_byte_counter % 0x10000
            
            my_bytes=bytearray([lendata]) + bytearray(msg, encoding='utf-8') + system_byte
            #my_bytes=bytearray([lendata]) + bytearray(msg)
        else:
            my_bytes=bytearray([lendata]) + bytearray(msg, encoding='utf-8') + system_byte

        self.socket.send(my_bytes)
        

    def output_sending(self):
        print("start output_sending")
        while(self.keepThreadAlive):
            try:
                if(len(self.output_buffer) > 0):
                    output=self.output_buffer.pop()
                    if(isinstance(output, tuple)):
                        self.sendMessage(output[0], output[1])
                    else:
                        self.sendMessage(output)

                time.sleep(0.01)
            except Exception as e:
                traceback.print_exc()
                print("Exception found in output thread:\n")
                
        print("exit output_sending")


    #Tis is a thread
    def move_cmd_handling(self): # Mike: 2021/03/11
        print("start move cmd handling")
        path=[]
        while(self.keepThreadAlive):
            try:
                if(len(self.move_cmd_queue) > 0): 
                    obj=self.move_cmd_queue.pop()
                    path.append(obj['move_cmd'])
                    if obj['move_cmd'][5] == 'G':
                        print(path)
                        self.move_simulate(path)
                        time.sleep(self.go_delay) # Mike: 2021/08/25
                        path=[]

                time.sleep(0.01)
            except Exception as e:
                traceback.print_exc()
                print("Exception found in cmd handling thread:\n")
                path=[]
               
        print("exit move cmd handling")


    def battery_simulate(self): # Mike: 2021/07/30
        print("start battery simulate")
        path=[]
        cnt=0
        self.jsonstatus["battery"]["battery_level"]=80+random.randint(-10, 10)
        while(self.keepThreadAlive):
            if self.charge_status == 1:
                #print('charging', cnt)
                cnt += 1
                if cnt >= self.charge_rate+random.randint(0, 3):
                    if self.jsonstatus["battery"]["battery_level"] < 100:
                        self.jsonstatus["battery"]["battery_level"] += 1
                    else:
                        #self.dischargeThread=threading.Thread(target=self.discharge_request)
                        #self.dischargeThread.setDaemon(True)
                        #self.dischargeThread.start()
                        pass
                    cnt=0
            else:
                #print('discharging', cnt)
                cnt += 1
                if cnt >= self.discharge_rate+random.randint(0, 10):
                    if self.jsonstatus["battery"]["battery_level"] > 0:
                        self.jsonstatus["battery"]["battery_level"] -= 1
                    cnt=0
            time.sleep(1)
            
        print("exit battery simulate")


    def tcp_bridge_start(self):
        self.KeepRunning=True

        self.ReceiverThread=threading.Thread(target=self.NormalProcess)
        self.ReceiverThread.setDaemon(True)
        self.ReceiverThread.start()


    def NormalProcess(self):
        print("========NormalProcess========")
        # self.server.settimeout(100)
        self.server.bind((self.bind_ip, self.bind_port))
        self.server.listen(5)  # max backlog of connections
        self.keepThreadAlive=True

        print('Listening on {}:{}'.format(self.bind_ip, self.bind_port))
       
        while self.KeepRunning:
            time.sleep(0.005)
            try:
                with open('../pose_table.txt', 'r') as inFile:
                    print('\nLoad map data. \n')
                    obj=json.load(inFile)
                    for key, data in obj.items():
                        pose_mapping[key]=[data['x'], data['y'], data['z'], data['w'], data['route']]
            
                
                print(pose_mapping)
            except Exception as e:
                    print(e)
                    pass

            try:
                #print 'self.KeepRunning'
                client_sock, address=self.server.accept()
                self.socket=client_sock
                print('\nAccepted connection from {}:{}\n'.format(address[0], address[1]))

                #close all thread first
                if self.client_handler:
                    print("Restart thread.\n")
                    self.keepThreadAlive=False
                    while self.client_handler.is_alive() or \
                          self.output_sending_thread.is_alive() or \
                          self.input_handler_thread.is_alive() or \
                          self.move_cmd_handling_thread.is_alive() or \
                          self.battery_simulate_thread.is_alive():
                        time.sleep(0.1)
                    self.jsonstatus["cassette"]=[
                        {
                            "id" : "",
                            "old_id":"",
                            "port":4,
                            "loading": False
                        } for i in range(self.buffer_num)
                    ]

                self.keepThreadAlive=True
                #get cmd into in_queue
                self.client_handler=threading.Thread(
                    target=self.handle_client_connection,
                    args=(client_sock,)  # without comma you'd get a... TypeError: handle_client_connection() argument after * must be a sequence, not _socketobject
                )
                self.client_handler.start()
                #deal cmd from in_queue
                self.input_handler_thread=threading.Thread(
                    target=self.input_handler,
                    args=(client_sock,)
                )
                self.input_handler_thread.start()

                #send cmd from out_queue
                self.output_sending_thread=threading.Thread(
                    target=self.output_sending
                )
                self.output_sending_thread.start()

                #deal move cmd from move_cmd_queue
                self.move_cmd_handling_thread=threading.Thread(
                    target=self.move_cmd_handling
                )
                self.move_cmd_handling_thread.start()

                #simulate battery state
                self.battery_simulate_thread=threading.Thread(
                    target=self.battery_simulate
                )
                self.battery_simulate_thread.start()

                
                self.reset_all_alarm_request()
                self.try_auto_request()

            except:

                pass

#############################################################################################
    def try_auto_request(self):
        total_pos="P11"
        self.automode=True
        self.output_buffer.appendleft(total_pos)

    def set_manual_request(self):
        total_pos="P13"
        self.automode=False
        self.output_buffer.appendleft(total_pos)

    def robot_cmd_status_report(self, status):
        print('>robot_cmd_status_report')
        if(status == 0):
            # self.cassette_status_report()
            total_pos="P53Finished"
        elif(status == 1):
            total_pos="P53InterlockError"
        else:
            total_pos="P53RobotError"

        self.output_buffer.appendleft(total_pos)

    def exchange_cmd_status_report(self, exchange_result=0):
        total_pos="P73" + str(exchange_result)
        self.output_buffer.appendleft(total_pos)

    def map_cmd_status_report(self, map_result=0):
        total_pos="P95" + str(map_result)
        self.output_buffer.appendleft(total_pos)

    def move_status_report(self):
        print('>move_status_report')
        w_pos='{:0>3d}'.format(self.jsonstatus["pose"][3])
        car_state="7"
        if self.jsonstatus["error"]:
            car_state="6"
        elif(self.jsonstatus["stop_status"] == "Pause"):
            car_state="3"
        elif(self.jsonstatus["state"] == "moving" and self.jsonstatus["wheelpwms"][4] == 0 and (self.jsonstatus["speed"]["angular"][3] != 0 or self.jsonstatus["speed"]["linear"][3] != 0)):
            car_state="5"
        elif(self.jsonstatus["state"] == "standby" or self.jsonstatus["state"] == "initial"):
            car_state="0"
        else:
            car_state="1"

        total_pos="P21" + car_state + w_pos
        self.output_buffer.appendleft(total_pos)


    def robot_status_report(self):
        print('>robot_status_report')
        total_pos="P23" + self.jsonstatus["robot"]["status"] + self.jsonstatus["robot"]["home"]
        self.output_buffer.appendleft(total_pos)


    def blocking_status_report(self):
        print('>blocking_status_report')
        total_pos="P65" + str(self.is_block)
        self.output_buffer.appendleft(total_pos)


    def robot_status_report(self):
        print('>robot_status_report')
        total_pos="P23" + self.jsonstatus["robot"]["status"] + self.jsonstatus["robot"]["home"]
        self.output_buffer.appendleft(total_pos)


    def map_report(self):
        print('>map_report')
        total_pos="P91" + self.current_map
        self.output_buffer.appendleft(total_pos)


    def cassette_status_report(self):
        print('>cassette_status_report')
        port_name=[str(i+1) for i in range(self.buffer_num)]
        for i in range(len(self.jsonstatus["cassette"])):
            #......................................................
            print('Processing cassette {}: {}'.format(i, self.jsonstatus["cassette"][i]))
            if self.jsonstatus["cassette"][i]["id"] == 'Unknown':
                self.jsonstatus["cassette"][i]["id"]='None'
            self.output_buffer.appendleft("P25"+port_name[i]+str(self.jsonstatus["cassette"][i]["port"])+self.jsonstatus["cassette"][i]["id"])
            '''if (self.jsonstatus["cassette"][i]["id"] != ''):
                if (self.jsonstatus["cassette"][i]["id"] == 'ReadIdFail'):
                    self.output_buffer.appendleft("P25"+port_name[i]+"2")

                elif (self.jsonstatus["cassette"][i]["id"] == 'PositionError'):
                    self.output_buffer.appendleft("P25"+port_name[i]+"3")

                elif (self.jsonstatus["cassette"][i]["id"] == 'Unknown'): #chocp:2021/3/01
                    self.output_buffer.appendleft("P25"+port_name[i]+"4")
                else:
                    self.output_buffer.appendleft("P25"+port_name[i]+"1"+self.jsonstatus["cassette"][i]["id"])

            else:
                self.output_buffer.appendleft("P25"+port_name[i]+"0")'''

    def reset_all_alarm_request(self):
        self.move_cmd_queue.clear()
        self.jsonstatus["error"]=False

        total_pos="P63"
        self.output_buffer.appendleft(total_pos)

    def setalarm(self, errorname, status):
        if(status):
            #self.output_buffer.appendleft("P611"+self.errorcode_dict[errorname])
            self.output_buffer.appendleft("P611"+errorname)
            self.jsonstatus["error"]=True
        else:
            #self.output_buffer.appendleft("P610"+self.errorcode_dict[errorname])
            self.output_buffer.appendleft("P611"+errorname)
            self.jsonstatus["error"]=True

    def battery_status_report(self, system_byte):
        total_pos="S36"
        # minimum_remain_capacity=min(self.jsonstatus["battery"]["battery_remain_capacity"])
        maximum_remain_capacity=max(self.jsonstatus["battery"]["battery_remain_capacity"])

        total_pos += '{:0>3d}'.format(abs(int(maximum_remain_capacity)))
        total_pos += '{:0>4d}'.format(int(100*self.jsonstatus["battery"]["battery_voltage"]))
        total_pos += '{:0>3d}'.format(int(self.jsonstatus["battery"]["battery_temperature"]))
        self.output_buffer.appendleft((total_pos, system_byte))

    def charge_status_report(self, charge_status=0):
        total_pos="P29" + str(charge_status)
        self.output_buffer.appendleft(total_pos)

    def exchange_status_report(self, exchange_status=0):
        total_pos="P75" + str(exchange_status)
        self.output_buffer.appendleft(total_pos)

    def move_append_arrival_report(self, endpoint=False, error=False, station_id=""):
        arrival="0"
        if(error):
            arrival="0"
        elif(endpoint):
            arrival="2"
        elif(not endpoint):
            arrival="1"
        x_pos=self.jsonstatus["pose"][0]
        y_pos=self.jsonstatus["pose"][1]
        w_pos=self.jsonstatus["pose"][3]
        moving_direction='{:0>3d}'.format(int(self.jsonstatus["speed"]["angular"][2]))
        speed='{:0>4d}'.format(int(self.jsonstatus["speed"]["linear"][0]))

        total_pos="P43"+arrival
        if(x_pos > 0):
            total_pos += "P"
            total_pos += "{:0>8d}".format(int(x_pos))
        else:
            total_pos += "N"
            total_pos += "{:0>8d}".format(int(0-x_pos))

        if(y_pos > 0):
            total_pos += "P"
            total_pos += "{:0>8d}".format(int(y_pos))
        else:
            total_pos += "N"
            total_pos += "{:0>8d}".format(int(0-y_pos))
        total_pos += "{:0>3d}".format(w_pos)
        total_pos += moving_direction
        total_pos += speed
        if(station_id != ""):
            total_pos += station_id

        if endpoint:
            time.sleep(self.end_delay)
        print("=====Send arrival Report=====")
        print("Arrive station, speed:{}, end:{}, arrival:{}".format(station_id, endpoint, arrival))
        print(total_pos)

        self.output_buffer.appendleft(total_pos)

    
    def robot_request(self):
        #(goal_x, goal_y, goal_w, speed_limit, endpoint, gokeep)=args

        print("robot start") 
        self.jsonstatus["robot"]["status"]="1"
        self.jsonstatus["robot"]["home"]="0"
        self.robot_status_report()
        if self.use_readfail_carrier:
            self.cassette_status_report()

        time.sleep(self.robot_time) # Mike: 2021/08/25
        self.jsonstatus["robot"]["status"]="0"
        self.jsonstatus["robot"]["home"]="1"

        self.robot_cmd_status_report(0)
        print("robot complete") 


    def charge_request(self):
        print("charger on") 
        self.charge_status=1
        self.charge_status_report(self.charge_status)
           

    def discharge_request(self):
        self.charge_status=0
        self.charge_status_report(self.charge_status)
        print("charger off complete")  


    def exchange_request(self):
        #(goal_x, goal_y, goal_w, speed_limit, endpoint, gokeep)=args

        print("exchange start") 
        self.exchange_status=1
        self.exchange_status_report(self.exchange_status)

        time.sleep(self.exchange_time)
        self.exchange_status=0
        self.exchange_status_report(self.exchange_status)

        self.exchange_cmd_status_report(0)
        print("exchange complete")


    def map_change_request(self):
        #(goal_x, goal_y, goal_w, speed_limit, endpoint, gokeep)=args

        print("map change")
        self.map_cmd_status_report(1)
        self.map_report()


    def move_simulate(self, path): # Mike: 2021/03/11

        i=0
        time_interval=1.0
        while i < len(path):
            if self.jsonstatus["error"]:
                break
            
            if self.is_block:
                time.sleep(0.5)
                continue

            if self.stop_move:
                self.stop_move=False
                break

            is_arrival=True
            dx=path[i][0]-self.jsonstatus["pose"][0]
            dy=path[i][1]-self.jsonstatus["pose"][1]
            dtheta=path[i][2]-self.jsonstatus["pose"][3]
            try:
                max_speed=float(path[i][3])
            except IndexError:
                max_speed=float(path[i][3])
            if dtheta > 180:
                dtheta -= 360
            if dtheta < -180:
                dtheta += 360
            delta=max(abs(dx), abs(dy))
            if abs(dx) > max_speed or abs(dy) > max_speed:
                dx *= max_speed/delta
                dy *= max_speed/delta
                dx=int(dx)
                dy=int(dy)
                is_arrival=False
            delta=max(abs(dx), abs(dy))
            if dtheta > self.angular_speed:
                dtheta=self.angular_speed
                is_arrival=False
            elif dtheta < -self.angular_speed:
                dtheta=-self.angular_speed
                is_arrival=False
            else:
                pass
            print(i, dx, dy, dtheta, max_speed, is_arrival, path[i][5])
            self.jsonstatus["pose"][0] += dx
            self.jsonstatus["pose"][1] += dy
            self.jsonstatus["pose"][3] += dtheta
            if self.jsonstatus["pose"][3] < 0:
                self.jsonstatus["pose"][3] += 360
            self.jsonstatus["speed"]["angular"][2]=0
            self.jsonstatus["speed"]["linear"][0]=path[i][3]

            if is_arrival:
                pointID=''
                for key, value in pose_mapping.items():
                    if value[0] == path[i][0] and value[1] == path[i][1] and value[3] == path[i][2] and value[4] == self.current_map: ######
                        pointID=key
                        break
                else:
                    print('Can not map pointID')
                
                self.move_append_arrival_report(path[i][4] == "1", False, pointID)
                i += 1
            
            if delta > 0 and max_speed > 0:
                time_interval=delta/max_speed
            else:
                time_interval=1.0
            time.sleep(time_interval)
        return



pose_mapping={}
'''
pose_mapping={
            "p1":[1, 2, 3, 4, 1, 1, groupID], # w, y, z, w, go, enable, groupID
            "p2":[1, 2, 3, 4, 1],
            "p3":[1, 2, 3, 4, 1],
            "p4":[1, 2, 3, 4, 1],
            "p5":[1, 2, 3, 4, 1],
            "p6":[1, 2, 3, 4, 1]
            }
'''
####################################################################################################################################
if __name__ =='__main__':

    try:
        with open('../pose_table.txt', 'r') as inFile:
            obj=json.load(inFile)
            
            for key, data in obj.items():
                pose_mapping[key]=[data['x'], data['y'], data['z'], data['w'], data['route']]

                if key == 'C001':
                    print(data['x'], data['y'], data['z'], data['w'])
    
        
        #print(pose_mapping)
    except Exception as e:
            print(e)
            pass


    parser=argparse.ArgumentParser()
    parser.add_argument('-p',  help='port')
    parser.add_argument('-i',  help='initial point') #chocp, 2021/3/7
    args=parser.parse_args()
    port=6789
    initial_point='C001'
    try:
        port=int(args.p)
    except:
        pass

    try:
        initial_point=args.i
    except:
        pass

    h=tcp_bridge(port, initial_point)
    h.tcp_bridge_start()
    try:
        while True:
            time.sleep(0.005)
            try:
                if six.PY2:
                    res=raw_input('input cmd') #go,215,300,180
                else:
                    res=input('input cmd') #go,215,300,180
            except EOFError:
                time.sleep(5)
                continue
            
            cmds=res.split(',')
            #print('\n\n')
            if cmds[0] == 'man': #man
                h.set_manual_request()
                print("manual mode")

            elif cmds[0] == 'auto': #auto
                h.reset_all_alarm_request() 
                h.try_auto_request()
                print("auto mode")

            elif cmds[0] == 'error': #error, 100009
                #h.setalarm("MoveFail", True)
                h.setalarm(cmds[1], True)

            elif cmds[0] == 'alarm': #error, 100009
                #h.setalarm("MoveFail", True)
                h.setalarm(cmds[1], True)
                print("reset alarm")

            elif cmds[0] == 'reset':
                h.reset_all_alarm_request()
                print("reset alarm")

            elif cmds[0] == 'battery':
                battery=int(cmds[1])
                h.jsonstatus["battery"]["battery_level"]=battery
                print("battery is {} now".format(h.jsonstatus["battery"]["battery_level"]))
                #h.jsonstatus["battery"]["battery_remain_capacity"][0]=battery
                #h.jsonstatus["battery"]["battery_remain_capacity"][1]=battery

            elif cmds[0] == 'rfid':
                if len(cmds) == 3:
                    h.jsonstatus["cassette"][int(cmds[1])-1]["port"] = 3
                    h.cassette_status_report()
                    time.sleep(3)
                    h.jsonstatus["cassette"][int(cmds[1])-1]["id"] = cmds[2]
                    h.jsonstatus["cassette"][int(cmds[1])-1]["port"] = 5
                    h.cassette_status_report()
                    print('buffer{}: {}'.format(cmds[1], cmds[2]))
                elif len(cmds) == 2:
                    h.jsonstatus["cassette"][int(cmds[1])-1]["port"] = 3
                    h.cassette_status_report()
                    time.sleep(3)
                    h.jsonstatus["cassette"][int(cmds[1])-1]["id"]=''
                    h.jsonstatus["cassette"][int(cmds[1])-1]["port"]=4
                    h.cassette_status_report()
                    print('buffer{}: {}'.format(cmds[1], ''))

            elif cmds[0] == 'pose':
                h.jsonstatus["pose"][0]=int(cmds[1])
                h.jsonstatus["pose"][1]=int(cmds[2])
                h.jsonstatus["pose"][2]=int(cmds[3])
                h.jsonstatus["pose"][3]=int(cmds[4])
                print('current pose: ({}, {}, {}, {})'.format(cmds[1], cmds[2], cmds[3], cmds[4]))

            elif cmds[0] == 'block':
                h.is_block=int(cmds[1])
                print('block: {}'.format(cmds[1]))
                h.blocking_status_report()

            elif cmds[0] == 'robottime':
                h.robot_time=int(cmds[1])
                print('robot time change to {}'.format(cmds[1]))

            elif cmds[0] == 'exchangetime':
                h.robot_time=int(cmds[1])
                print('exchange time change to {}'.format(cmds[1]))

            elif cmds[0] == 'map':
                h.current_map=cmds[1]
                h.map_report()
                print('map change to {}'.format(cmds[1]))


    except:
        traceback.print_exc()
        pass



