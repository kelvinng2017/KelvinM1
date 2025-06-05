import collections
from copy import deepcopy
from datetime import datetime
from hashlib import md5
import json
import logging
import logging.handlers as log_handler
import os
import re
import requests
from requests.models import Response
import socket
import threading
import time
import traceback
import uuid
import six
if six.PY3:
    from bs4 import BeautifulSoup

import alarms
# from iot.iot_mgr import IotView

class MyException(Exception):
    pass

class NullStringWarning(MyException):
    def __init__(self, txt="receive null string"):
        self.alarm_set = "Error"
        self.code = 50001
        self.txt = txt

class ConnectFailWarning(MyException):
    def __init__(self, txt="connect fail"):
        self.alarm_set = "Error"
        self.code = 50002
        self.txt = txt

class LinkLostWarning(MyException):
    def __init__(self, txt="linking timeout"):
        self.alarm_set = "Error"
        self.code = 50003
        self.txt = txt

alarm_list = {

}

class GATE(threading.Thread):
    def __init__(self, iot, callback=None):
        self.listeners = []
        self.device_id = iot.get("device_id", "GATE")
        self.device_type = iot.get("device_type", "GATE")
        self.device_model = iot.get("device_model", "WISE-4060")
        self.comm_type = iot.get("comm_type", "restful") # restful, socket        
        self.ip = iot.get("ip", "127.0.0.1")
        self.port = iot.get("port", 5501)
        self.retry_time = iot.get('retry_time', 5)
        self.socket_timeout = iot.get('socket_timeout', 2)
        self.setting = json.loads(iot.get("setting"))
        self.enable = iot.get("enable", False)
        self.IOT_OD = collections.OrderedDict({
            "device_type": self.device_type,
            "device_id": self.device_id,
            "link": "Disconnect",
            "start_time": 0,
            "last_sync_time": 0,
            "status": "DISABLED", # DISCONNECTED, CONNECTED, OPENED, CLOSED
            "last_error_code": "",
            "last_error_code_time": 0,
            "msg": ""
        })
        self.thread = None
        self.thread_stop = False
        self.heart_beat = 0
        self.logger = self._setup_logger(self.device_id)
        self.comm = None  

        if self.comm_type == "restful":
            self.comm = RestAPIComm(self, self.logger)
        elif self.comm_type == "socket":
            self.comm = SocketClientComm(self, self.logger)
        else:
            raise ValueError("Unsupported communication type. Use 'restful' or 'socket'.")
        threading.Thread.__init__(self)

    def _setup_logger(self, device_id):

        logger = logging.getLogger(device_id)
        logger.setLevel(logging.DEBUG)
      
        for handler in logger.handlers:
            logger.removeHandler(handler)
            handler.close()
        filename = os.path.join("log", "Gyro_{}.log".format(self.device_id))
        GATELogFileHandler = log_handler.TimedRotatingFileHandler(filename, when="midnight", interval=1, backupCount=30)
        GATELogFileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        
        streamLogHandler = logging.StreamHandler()
        streamLogHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        logger.addHandler(streamLogHandler)
        return logger

    def add_listener(self, obj):
        self.listeners.append(obj)

    def notify(self, event, param):
        for obj in self.listeners:
            obj.on_notify(event, param)

    def updateinfo(self):
        self.notify("GATEStatusUpdate", self.IOT_OD)

    def update_params(self, iot):
        self.comm_type = iot.get("comm_type", "restful")
        self.device_type = iot.get("device_type", "GATE")
        self.device_model = iot.get("device_model", "WISE-4060")
        self.device_id = iot.get("device_id", "GATE")
        self.ip = iot.get("ip", "127.0.0.1")
        self.port = iot.get("port", 5501)
        self.IOT_OD["device_type"] = self.device_type
        self.IOT_OD["device_id"] = self.device_id
        self.setting = json.loads(iot.get("setting"))
        self.enable = iot.get("enable", False)
    
    def is_gate_opened(self, params):
        if self.comm_type == 'restful':
            action = deepcopy(self.setting.get("api").get("gate_status"))
            response = self.comm.send(action)
            if response.status_code == 200:
                response_data = response.json()
                if self.device_model == "WISE-4060":
                    DOVal_ch_list = response_data.get("DOVal") # WISE-4060 module
                    if DOVal_ch_list:
                        for ch in DOVal_ch_list:
                            if ch.get("Ch") == params.get("Ch"):
                                if ch.get("Stat") == 0:
                                    return False
                                else:
                                    return True
                            
        elif self.comm_type == "socket":
            return False
        else:
            return False
    
    def gate_open(self, params):
        if self.comm_type == 'restful':
            # api_url = f"{self.ip}:{self.port}{self.setting.get('api').get('open_door')}"
            # api_json = self.setting.get("api").get("open_door_json")
            action = deepcopy(self.setting.get("api").get("gate_open")) # deepcopy 
            if self.device_model == "WISE-4060":
                action["path"] = "{}/ch_{}".format(action['path'], params.get('Ch'))
                action["data"] = {
                    "Ch": params.get("Ch"),
                    "Val": 1
                }
            
            response = self.comm.send(action)
            if response.status_code == 200:
                return
            else:
                pass
        else:
            pass

    def gate_close(self, params):
        if self.comm_type == 'restful':
            # api_url = f"{self.ip}:{self.port}{self.setting.get('api').get('open_door')}"
            # api_json = self.setting.get("api").get("open_door_json")
            action = deepcopy(self.setting.get("api").get("gate_open"))
            if self.device_model == "WISE-4060":
                action["path"] = "{}/ch_{}".format(action['path'], params.get('Ch'))
                action["data"] = {
                    "Ch": params.get("Ch"),
                    "Val": 0
                }
            
            response = self.comm.send(action)
            if response.status_code == 200:
                pass
            else:
                pass
        else:
            pass

    def run(self):

        self.logger.info("Starting iot device {} thread.".format(self.device_id))
        while not self.thread_stop:
            try:
                self.logger.info("IOT GATE device_id <{}> on {}:{} is connecting.".format(self.device_id, self.ip, self.port))
                self.comm.run()
                self.logger.info("IOT GATE device_id <{}> on {}:{} disconnected.".format(self.device_id, self.ip, self.port))
            except:
                self.logger.warning(traceback.format_exc())
                self.IOT_OD["link"] = "Disconnect"
                self.IOT_OD["status"] = "ALARM"
        self.logger.info("Iot device {} thread stopped.".format(self.device_id))
    # def disable(self):
        # self.comm.stop()
        # self.logger.info("GATE disabled.")

class RestAPIComm:
    def __init__(self, iot, logger):

        self.iot = iot
        self.logger = logger
        self.need_login= self.iot.setting.get("need_login", False)
        self.session = requests.Session()
        # self.session.headers.update({
        #     "Content-Type": "application/x-www-form-urlencoded",
        #     "User-Agent": "PostmanRuntime/7.29.0",
        #     "Accept": "*/*",
        #     "Host": f"{self.iot.ip}:{self.iot.port}",
        #     "Accept-Encoding": "gzip, deflate, br",
        #     "Connection": "keep-alive",
        # })
    
    def connect(self):
        try:
            action = self.iot.setting.get("api").get("connect")
            response = self.send(action)
            if response.status_code == 200:
                if self.iot.IOT_OD["link"] != "Connect": 
                    self.iot.IOT_OD["link"] = "Connect"
                    self.iot.IOT_OD["status"] = "CONNECTED"
                self.iot.IOT_OD["last_sync_time"] = time.time()
            elif response.status_code == 408:
                if self.iot.IOT_OD["link"] != "Disconnect":
                    self.iot.IOT_OD["link"] = "Disconnect"
                    self.iot.IOT_OD["status"] = "TIMEOUT"
            elif response.status_code == 500:
                if self.iot.IOT_OD["link"] != "Disconnect":
                    self.iot.IOT_OD["link"] = "Disconnect"
                    self.iot.IOT_OD["status"] = "ERROR"
        except Exception:
            self.logger.error("Connecting IOT device IP {}:{} Failed, {}".format(self.iot.ip, self.iot.port, traceback.format_exc()))
            if self.iot.IOT_OD["link"] != "Disconnect":
                self.iot.IOT_OD["link"] = "Disconnect"
                self.iot.IOT_OD["status"] = "DISCONNECTED"
    
    def login(self):
        try:
            action = self.iot.setting.get("api").get("login")
            response = self.send(action)
            if response.status_code == 200:
                # print(response.text)
                if self.iot.device_model == "WISE-4060": # WISE-4060 model login process
                    soup = BeautifulSoup(response.text, "html.parser")
                    seeddata_input = soup.find("input", {"name": "seeddata"})
                    if not seeddata_input:
                        self.logger.warning("Failed to retrieve IOT device_id: {} seeddata.".format(self.iot.device_id))
                        return
                    seeddata = seeddata_input["value"]
                    username = action.get("data", {}).get("username", "root")
                    password = action.get("data", {}).get("password", "00000000")
                    oridata = "{}:{}:{}".format(seeddata, username, password)
                    authdata = md5(oridata.encode()).hexdigest()
                    action = {
                        "path": "/config/index.html",
                        "method": "POST",
                        "data": {
                            "seeddata": seeddata,
                            "authdata": authdata
                        }
                    }
                    response = self.send(action)
                    if response.status_code == 200 and "Set-Cookie" in response.headers:
                        print("Cookie: {}".format(response.headers['Set-Cookie']))
                        print("IOT device login successfully")
                    else:
                        print("error", response, response.text)
            else:
                self.logger.warning("Failed to load IOT device_id: {} login page with status code {}".format(self.iot.device_id, response.status_code))
        except Exception as e:
            print(e)
            pass

    def send(self, action):

        url = "http://{}:{}{}".format(self.iot.ip, self.iot.port, action.get('path', '/'))
        method = action.get("method", "GET").upper() 
        data = action.get("data", {})
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise requests.exceptions.RequestException()
            
            if response.status_code == 200 and response.headers["Content-Type"] == "application/json":
                # self.logger.debug(f"Success: `{response.status_code}`, URL: `{url}`, JSON: {json.dumps(response.json())}.")
                self.iot.IOT_OD["last_sync_time"] = time.time()
            elif response.status_code == 400 and response.headers["Content-Type"] == "application/json":
                response_json = response.json()
                if response_json.get("Err") == 1000 and response_json.get("Msg") == "":
                    self.session.cookies.clear()
            elif response.headers["Content-Type"] == "application/json":
                self.logger.warning("Fail: `{}`, URL: `{}`, JSON: {}.".format(response.status_code, url, json.dumps(response.json())))
            elif response.status_code != 200:
                self.logger.warning("status code: `{}`, URL: `{}`, Header: {}.".format(response.status_code, url, response.headers))
            
        except requests.exceptions.Timeout:
            self.logger.error("Client API Timeout. URL: `{}`.".format(url))
            custom_response = Response()
            custom_response.status_code = 408 # 408 Request Timeout
            custom_response._content = b'{"error": "Request timeout"}'
            return custom_response
        except requests.exceptions.RequestException as e:
            self.logger.error("Client API RequestException. Method: `{}`. `URL: `{}` Reason: {}.".format(method, url, e))
            custom_response = Response()
            custom_response.status_code = 500 # 500 Internal Server Error
            custom_response._content = b'{"error": "Client API RequestException"}'
            return custom_response
        except Exception as e:
            print("Line 284", str(e))
        return response
    
    def run(self):

        while not self.iot.thread_stop:
            self.iot.heart_beat = time.time()
            if self.need_login and not self.session.cookies:
                
                self.logger.info("No cookies found. Attempting to login.")
                self.login()
            if time.time() - self.iot.IOT_OD["last_sync_time"] >= 30:
                self.connect()
            time.sleep(10)


class SocketClientComm:
    def __init__(self, iot, logger):


        self.iot = iot
        self.sock = None # IOT socket 
        self.lock = threading.Lock()
        self.logger = logger

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.iot.ip, self.iot.port))
            self.logger.info("Connected to server at {}:{}".format(self.iot.ip, self.iot.port))
            self.iot.IOT_OD["link"] = "Unsynced"
            self.iot.IOT_OD["start_time"] = time.time()
            self.iot.IOT_OD["last_sync_time"] = time.time()
            self.iot.IOT_OD['status'] = "CONNECTING"
        except socket.error as e:
            self.iot.IOT_OD["link"] = "Disconnect"
            self.iot.IOT_OD["start_time"] = time.time()
            self.iot.IOT_OD["last_sync_time"] = time.time()
            self.iot.IOT_OD['status'] = "DISCONNECTED"
            self.logger.error("Failed to connect to server: {}".format(e))

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
                self.logger.info("Socket connection closed.")
            except socket.error as e:
                self.logger.error("Error while closing socket: {}".format(e))
            self.iot.IOT_OD["link"] = "Disconnect"
            self.iot.IOT_OD["last_sync_time"] = time.time()
            self.iot.IOT_OD['status'] = "DISCONNECTED"
        self.sock = None
        self.iot.IOT_OD["link"] = "Disconnect"

    def send(self, action):

        if not self.sock:
            self.logger.warning("Cannot send data, socket is not connected.")
            return
        
        try:
            with self.lock:
                message = json.dumps(action)
                self.sock.sendall(message.encode("utf-8"))
                self.logger.info("Sent: {}".format(message))
                # response = self.sock.recv(4096).decode("utf-8")
                # self.logger.info(f"Received: {response}")
                # return json.loads(response)
        except socket.error as e:
            self.logger.error("Failed to send data: {}".format(e))
            self.iot.IOT_OD["status"] = "Failed"

    def run(self):

        raw_rx = ""
        raw_rx_buffer = []
        req_toc = 0

        while not self.iot.thread_stop:
            self.iot.heart_beat = time.time()

            if self.iot.IOT_OD["link"] == "Disconnect":
                self.connect()
                self.send("GetInfo")
                req_toc = time.time()
            else:
                try:
                    if time.time() - req_toc > 5:
                        self.send("GetInfo")
                        req_toc = time.time()
                    self.sock.settimeout(self.iot.setting.get("timeout", 2))
                    buf = self.sock.recv(4096).decode("utf-8")
                    if buf:
                        self.logger.debug("[raw] {}".format(str(buf)))
                        raw_rx_buffer.append(buf)
                        if "^" in buf:
                            raw_rx = "".join(raw_rx_buffer)
                            while "^" in raw_rx:
                                carnet_index = raw_rx.find("^")
                                raw_data = raw_rx[:carnet_index]
                                raw_rx = raw_rx[carnet_index+1:]
                                self.handle_payload(raw_data)
                            raw_rx_buffer = [raw_rx]
                except socket.timeout:
                    self.iot.IOT_OD["link"] = "Unsynced"
                    if time.time() - self.iot.IOT_OD["last_sync_time"] > self.iot.setting.get("retry_time", 3)* self.iot.setting.get("timeout", 2):
                        raise LinkLostWarning(self.iot.device_id)
                except:
                    self.logger.warning("\n{}".format(traceback.format_exc()))
                    raise ConnectFailWarning(self.iot.device_id)
            
            time.sleep(1)

    def handle_payload(self, raw_data):
        # if self.iot.setting.get("rack_naming", 0)
        try:
            payload = json.loads(raw_data)
            if payload:
                if payload["head"]["service"] == "reply":
                    if payload["data"]["typename"] == "GetInfo":
                        data = payload["data"]["status"]
                        keys = ["state", "env", "sink"]
                        check = False
                        for key in keys:
                            if self.iot.IOT_OD.setdefault(key, None) != data[key]:
                                self.iot.IOT_OD[key] = data[key]
                                check = True
                        self.iot.IOT_OD["link"] = "Synced"
                        self.iot.IOT_OD["last_sync_time"] = time.time()
                        if check:
                            self.iot.updateinfo()
                elif payload["head"]["service"] == "notification":
                    data = payload["data"]["status"]
                    event_list = []
                    for event in data["event"]:
                        event_list.append(event["code"])
                    self.event_handler(event_list)
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON data: {}".format(raw_data))
    
    def event_handler(self, event_list):
        state_updates = {
            '0x0002': {'state': 'Standby'},
            '0x0003': {'state': 'Busy'},
            '0x0004': {'state': 'Manual'},
        }

        substate_updates = {
            '0x5003': {'substate': 'Exchanging'},
            '0x5002': {'substate': 'Idle'},
        }

        for event in event_list:
            if event in alarm_list:
                self.iot.IOT_OD.setdefault('alarm_list', []).append(event)
                alarms.ABCSWithAlarmWarning(self.device_id, event)
            elif event == '0x0001':
                self.iot.IOT_OD.setdefault('alarm_list', []).clear()
            elif event in state_updates:
                self.iot.IOT_OD.update(state_updates[event])
            elif event in substate_updates:
                self.iot.IOT_OD.update(substate_updates[event])

        self.iot.updateinfo()
    