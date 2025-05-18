
import threading
import traceback
import collections
import socket
import json
import time
# from global_variables import output
import uuid
from datetime import datetime
import os
import logging
import logging.handlers as log_handler
import global_variables
import alarms
import re

class MyException(Exception):
    pass

class NullStringWarning(MyException):
    def __init__(self, txt='receive null string'):
        self.alarm_set='Error'
        self.code=50001
        self.txt=txt


class ConnectFailWarning(MyException):
    def __init__(self, txt='connect fail'):
        self.alarm_set='Error'
        self.code=50002
        self.txt=txt

class LinkLostWarning(MyException):
    def __init__(self, txt='linking timeout'):
        self.alarm_set='Error'
        self.code=50003
        self.txt=txt

alarm_list={
}

class ELV(threading.Thread):

    def __init__(self, secsgem_e88_stk_h, setting, callback=None):

        self.listeners=[]
        self.secsgem_e88_stk_h=secsgem_e88_stk_h
        self.retry_time=setting.get('retry_time', 5)
        self.socket_timeout=setting.get('socket_timeout', 2)

        self.device_id=setting.get('device_id', 'ELV')
        self.device_type=setting.get('device_type', 'ELV')
        self.ip=setting.get('ip', '127.0.0.1')
        self.port=setting.get('port', 5501)

        self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket=None

        self.sock=None # 2024/02/23 no attribute bug

        self.code=0
        self.extend_code=0
        self.msg=''

        self.ELV=collections.OrderedDict({
                    "device_id":self.device_id,
                    "link":"Disconnect",
                    "syncing_time":0,
                    "PM": "Out_Service", # In_Service, Out_Service
                    "OP": "Manual", # Auto, Manual
                    "CMD": "Immediate_Stop", # Move_In, Move_Out, Immediate_Stop
                    "Status": "Lifter_Error" # Stopped_UpStair, Stopped_DownStair, Moving_Up, Moving_Down, Door_Opening, Door_Closing, Door_Opened, Door_Closed, Lifter_Error
                })

        self.cmd={
                    "PM": "Out_Service" if global_variables.RackNaming == 14 else "In_Service", # In_Service, Out_Service
                    "OP": "Auto", # Auto, Manual
                    "CMD": None if global_variables.RackNaming == 14 else "Door_Close", # Move_Up, Move_Down, Door_Open, Door_Close, Immediate_Stop, Call_Lifter_Up, Call_Lifter_Down
                    "Status": "Waiting" # Moving_In, Moving_Out, MoveIn_Complete, MoveOut_Complete, Safety_Stopped, Error_Stopped, Waiting
                }
        self.cmd_parse="[PM_Mode:{PM}][Operation_Mode:{OP}][Status:{Status}][Command:{CMD}]"
        self.cmd_executing=False
        self.cmd_current=None # {"function": "function_name", "floor": "floor"}
        self.cmd_send_time=0
        # self.last_send_time=0

        self.logger=logging.getLogger(self.device_id) # Mike: 2021/05/17
        for h in self.logger.handlers[:]: # Mike: 2021/09/22
            self.logger.removeHandler(h)
            h.close()
        self.logger.setLevel(logging.DEBUG)

        filename=os.path.join("log", "Gyro_{}.log".format(self.device_id))
        MRLogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30)
        MRLogFileHandler.setLevel(logging.DEBUG)
        MRLogFileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(MRLogFileHandler)

        # For console. Mike: 2021/07/16
        streamLogHandler=logging.StreamHandler()
        streamLogHandler.setLevel(logging.INFO)
        streamLogHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(streamLogHandler)

        self.updateinfo() #choc add 2021/10/13

        self.lock=threading.Lock()

        self.heart_beat=0
        self.thread_stop=False
        # threading.Thread.__init__(self)
        super(ELV, self).__init__()
        self.daemon=True

    def add_listener(self, obj):
        self.listeners.append(obj)

    def notify(self, event):
        # self.logger.debug('[notify] {}'.format(event))
        # print(('[notify] {}'.format(event)))
        for obj in self.listeners:
            obj.on_notify(*event)

    def updateinfo(self):
        self.notify(('ELVStatusUpdate', self.ELV))

    def update_params(self, setting):
        self.device_id=setting.get('device_id', 'ELV')
        self.device_type=setting.get('device_type', 'ELV')

    def event_handler(self):
        pass

    # for sock.send
    def safe_send(self, data):
        if self.sock is None:
            self.logger.warning('Attempted to send data on a non-existent socket connection.')
            return False
        try:
            time.sleep(0.05)
            # self.sock.send(bytearray(data, encoding='utf-8'))
            self.sock.sendall(bytearray(data, encoding='utf-8'))
            time.sleep(0.05)
            # self.last_send_time=time.time()
            return True
        # except (OSError, IOError) as e:
        #     self.logger.error('Socket error, closing connection: {}'.format(e))
        #     self._close_connection()
        #     # return False
        except Exception as e:
            self.logger.error('Error sending data: {}'.format(e))
            self._close_connection()
            return False


    def check_command_completion(self):
        function=self.cmd_current.get('function')
        floor=self.cmd_current['param'].get('floor')
        self.logger.info('call check_command_completion, function: {}, floor: {} '.format(function, floor))
        if function == "go_floor":
            if global_variables.RackNaming == 14 and (self.ELV['PM'] == 'In_Service' and self.ELV['Status'] == "Stopped_{}F".format(floor)):
                self.logger.info('go floor {} completed'.format(floor))
                return True
            elif (floor, self.ELV['Status'], self.ELV['OP']) in [(1, "Stopped_DownStair", "Auto"), (2, "Stopped_UpStair", "Auto")]:
                self.logger.info('go floor {} completed'.format(floor))
                return True
        elif function == "open_door" and (self.ELV['Status'], self.ELV['OP']) == ('Door_Opened', 'Auto'):
            self.logger.info('open door completed')
            return True
        elif function == "close_door" and (self.ELV['Status'], self.ELV['OP']) == ('Door_Closed', 'Auto'):
            self.logger.info('close door completed')
            return True
        elif function == "call_elv":
            if global_variables.RackNaming == 14 and (self.ELV['PM'] == 'In_Service' and self.ELV['Status'] == "Stopped_{}F".format(floor)):
                self.logger.info('call floor to {} completed'.format(floor))
                return True
            elif (floor, self.ELV['Status'], self.ELV['OP']) in [(1, "Stopped_DownStair", "Auto"), (2, "Stopped_UpStair", "Auto")]:
                self.logger.info('call floor to {} completed'.format(floor))
                return True
        return False

    def in_service(self):
        self.logger.info('in_service')
        acquired = False
        # while not self.lock.acquire(False):
        #     time.sleep(0.01)
        try:

            self.lock.acquire()
            acquired = True

            if self.ELV['PM'] == 'In_Service' and global_variables.RackNaming == 14:
                self.logger.info('In_Service takeover: {}'.format(self.ELV['PM']))
                return True
            else:
                self.cmd['PM']='In_Service'
                self.cmd['Status']="Waiting"
                data=json.dumps(self.cmd_parse.format(**self.cmd))
                self.logger.debug('[send] ' + data)
                self.safe_send(data)
                self.lock.release()
                self.cmd_send_time=time.time()
                # self.cmd_executing=True
                return False
        finally:
            if acquired:
                self.lock.release()

    def out_service(self):
        self.logger.info('out_service')
        acquired = False
        # while not self.lock.acquire(False):
        #     time.sleep(0.01)
        try:

            self.lock.acquire()
            acquired = True

            if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:
                self.logger.info('Out_Service return: {}'.format(self.ELV['PM']))
                return True
            else:
                self.cmd['PM']='Out_Service'
                self.cmd['Status']="MoveOut_Complete"
                data=json.dumps(self.cmd_parse.format(**self.cmd))
                self.logger.debug('[send] ' + data)
                self.safe_send(data)
                self.lock.release()
                self.cmd_send_time=time.time()
                # self.cmd_executing=True
                return False
        finally:
            if acquired:
                self.lock.release()

    def auto(self):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('auto_fail: {}'.format(self.ELV['PM']))
            return False
        self.logger.info('auto')
        while not self.lock.acquire(False):
            time.sleep(0.01)
        self.cmd['OP']='Auto'
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        # self.cmd_executing=True

    def man(self):
        self.logger.info('manual')
        while not self.lock.acquire(False):
            time.sleep(0.01)
        self.cmd['OP']='Manual'
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        # self.cmd_executing=True

    def reset(self):
        self.logger.info('reset')
        while not self.lock.acquire(False):
            time.sleep(0.01)
        # self.cmd['OP']='Auto'
        self.cmd['CMD']="Immediate_Stop"
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        self.cmd_executing=False

    def mr_stop(self, error):
        # if self.cmd['OP'] == 'Manual':  #20240827
        #     self.logger.info('mr_move_fail: {}'.format(self.cmd['OP']))
        #     return False
        self.logger.info('mr stop: {}'.format(error))
        while not self.lock.acquire(False):
            time.sleep(0.01)
        self.cmd['OP']='Auto'
        self.cmd['Status']="Error_Stopped" if error else "Safety_Stopped"
        # self.cmd['CMD']="Immediate_Stop"
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        # self.cmd_executing=True

    def mr_move(self, go_in, completed):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('mr_move_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('mr_move_fail: {}'.format(self.ELV['OP']))
            return False
        self.logger.info('mr_move: go_in:{}, completed:{}'.format(go_in, completed))
        while not self.lock.acquire(False):
            time.sleep(0.01)
        self.cmd['OP']='Auto'
        status=''
        if (go_in, completed) == (False, False):
            status='Moving_Out'
        elif (go_in, completed) == (False, True):
            status='MoveOut_Complete'
            if global_variables.RackNaming == 14:
                self.cmd['PM']='Out_Service'
        elif (go_in, completed) == (True, False):
            status='Moving_In'
        elif (go_in, completed) == (True, True):
            status='MoveIn_Complete'
        self.cmd['Status']=status
        #self.cmd['CMD']="Immediate_Stop"
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        # self.cmd_executing=True

    def stop_elv(self):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('call_elv_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('stop_ELV_fail: {}'.format(self.ELV['OP']))
            return False
        self.logger.info('stop')
        while not self.lock.acquire(False):
            time.sleep(0.01)
        self.cmd['OP']='Auto'
        # self.cmd['Status']="Safety_Stopped"
        self.cmd['CMD']="Immediate_Stop"
        data=json.dumps(self.cmd_parse.format(**self.cmd))
        self.logger.debug('[send] ' + data)
        self.safe_send(data)
        self.lock.release()
        # self.sock.send(bytearray(data, encoding='utf-8'))
        #
        # self.safe_send(data)
        self.cmd_send_time=time.time()
        # self.cmd_executing=True

    def go_floor(self, floor):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('call_elv_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('go_floor_fail: {}'.format(self.ELV['OP']))
            return False
        if global_variables.RackNaming == 14 and (self.ELV['PM'] == 'In_Service' and self.ELV['Status'] == "Stopped_{}F".format(floor)):
            self.logger.info('go floor check')
            # self.cmd_executing=False
            return True
        elif (floor, self.ELV['Status'], self.ELV['OP']) in [(1, "Stopped_DownStair", "Auto"), (2, "Stopped_UpStair", "Auto")]:
            self.logger.info('go floor check')
            # self.cmd_executing=False
            return True
        if not self.cmd_executing:
            self.logger.info('go floor {}'.format(floor))
            while not self.lock.acquire(False):
                time.sleep(0.01)
            self.cmd['OP']='Auto'
            self.cmd['Status']="MoveIn_Complete"
            if global_variables.RackNaming == 14: # KYEC
                self.cmd['CMD']="Move_{}F".format(floor)
            else:
                self.cmd['CMD']="Move_Up" if floor==2 else "Move_Down"
            data=json.dumps(self.cmd_parse.format(**self.cmd))
            self.logger.debug('[send] ' + data)
            self.safe_send(data)
            self.lock.release()
            # self.sock.send(bytearray(data, encoding='utf-8'))
            #
            # self.safe_send(data)
            self.cmd_send_time=time.time()
            self.cmd_executing=True
            self.cmd_current={
                                "function": "go_floor",
                                "param": {
                                            "floor": floor
                                            }
                                }
        return False

    def open_door(self):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('call_elv_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('open_door_fail: {}'.format(self.ELV['OP']))
            return False
        # if self.ELV['Status'] == 'Door_Opened':
        if global_variables.RackNaming == 14:
            if self.ELV['Status'] == 'Door_Opened' and self.ELV['PM'] == 'In_Service':
                self.logger.info('open door check')
                # self.cmd_executing=False
                return True
        else:
            if (self.ELV['Status'], self.ELV['OP']) == ('Door_Opened', 'Auto'):
                self.logger.info('open door check')
                # self.cmd_executing=False
                return True
        if not self.cmd_executing:
            self.logger.info('open door')
            while not self.lock.acquire(False):
                time.sleep(0.01)
            self.cmd['OP']='Auto'
            # self.cmd['Status']="MoveIn_Complete"
            self.cmd['CMD']="Door_Open"
            data=json.dumps(self.cmd_parse.format(**self.cmd))
            self.logger.debug('[send] ' + data)
            self.safe_send(data)
            self.lock.release()
            # self.sock.send(bytearray(data, encoding='utf-8'))
            #
            # self.safe_send(data)
            self.cmd_send_time=time.time()
            self.cmd_executing=True
            self.cmd_current={
                                "function": "open_door",
                                "param": {
                                            }
                                }
        return False

    def close_door(self):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('call_elv_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('close_door_fail: {}'.format(self.ELV['OP']))
            return False
        # if self.ELV['Status'] == 'Door_Closed':
        if global_variables.RackNaming == 14:
            if self.ELV['Status'] == 'Door_Closed' and self.ELV['PM'] == 'In_Service':
                self.logger.info('close door check')
                # self.cmd_executing=False
                return True
        else:
            if (self.ELV['Status'], self.ELV['OP']) == ('Door_Closed', 'Auto'):
                self.logger.info('close door check')
                # self.cmd_executing=False
                return True
        if not self.cmd_executing:
            self.logger.info('close door')
            while not self.lock.acquire(False):
                time.sleep(0.01)
            self.cmd['OP']='Auto'
            # self.cmd['Status']="MoveIn_Complete"
            self.cmd['CMD']="Door_Close"
            data=json.dumps(self.cmd_parse.format(**self.cmd))
            self.logger.debug('[send] ' + data)
            self.safe_send(data)
            self.lock.release()
            # self.sock.send(bytearray(data, encoding='utf-8'))
            #
            # self.safe_send(data)
            self.cmd_send_time=time.time()
            self.cmd_executing=True
            self.cmd_current={
                                "function": "close_door",
                                "param": {
                                            }
                                }
        return False

    def call_elv(self, floor):
        if self.ELV['PM'] == 'Out_Service' and global_variables.RackNaming == 14:  # DeanJwo for KYEC 20250506
            self.logger.info('call_elv_fail: {}'.format(self.ELV['PM']))
            return False
        if self.ELV['OP'] == 'Manual':  #20240829
            self.logger.info('call_elv_fail: {}'.format(self.ELV['OP']))
            return False
        if global_variables.RackNaming == 14 and (self.ELV['PM'] == 'In_Service' and self.ELV['Status'] == "Stopped_{}F".format(floor)):
            self.logger.info('call floor to {} check'.format(floor))
            # self.cmd_executing=False
            return True
        # if (floor, self.ELV['Status']) in [(1, "Stopped_DownStair"), (2, "Stopped_UpStair")]:
        elif (floor, self.ELV['Status'], self.ELV['OP']) in [(1, "Stopped_DownStair", "Auto"), (2, "Stopped_UpStair", "Auto")]:
            self.logger.info('call floor to {} check'.format(floor))
            # self.cmd_executing=False
            return True

        if not self.cmd_executing:
            self.logger.info('call to floor {}'.format(floor))
            while not self.lock.acquire(False):
                time.sleep(0.01)
            self.cmd['OP']='Auto'
            self.cmd['Status']="Waiting"
            if global_variables.RackNaming == 14: # KYEC
                self.cmd['CMD']="Call_Lifter_{}F".format(floor)
            else:
                self.cmd['CMD']="Call_Lifter_Up" if floor==2 else "Call_Lifter_Down"
            data=json.dumps(self.cmd_parse.format(**self.cmd))
            self.logger.debug('[send] ' + data)
            self.safe_send(data)
            self.lock.release()
            # self.sock.send(bytearray(data, encoding='utf-8'))
            #
            # self.safe_send(data)
            self.cmd_send_time=time.time()
            self.cmd_executing=True
            self.cmd_current={"function": "call_elv", "param": {"floor": floor}}
        return False

    def check_elv(self, floor):
        if global_variables.RackNaming == 14 and ( self.ELV['PM'] == 'In_Service' and self.ELV['Status'] == "Stopped_{}F".format(floor)):
            self.logger.info('check elevator at {}.format(floor): OK')
            return True
        elif (floor, self.ELV['Status'], self.ELV['OP']) in [(1, "Stopped_DownStair", "Auto"), (2, "Stopped_UpStair", "Auto")]:
            self.logger.info('check elevator at {}: OK'.format(floor))
            return True
        self.logger.info('check elevator at {}: NG'.format(floor))
        return False

    def _close_connection(self):
        if self.sock:
            try:
                self.logger.info("Closing socket.")
                self.sock.close()
                self.logger.info("Socket closed.")
            except Exception as e:
                self.logger.warning('Error closing socket: {}'.format(e))
            finally:
                self.sock=None
        else:
            self.logger.info('<<Socket already Closed>>')
        self.ELV['link']='Disconnect'

    def run(self):
        raw_rx=''
        self.last_state=''
        req_toc=0
        #self.change_state('enable')
        self.logger.info('Start Binding...')
        self.server.bind((self.ip, self.port))
        self.server.listen(1)  # max backlog of connections
        # self.server.setblocking(False) # test non-blocking
        self.server.settimeout(self.socket_timeout)
        self.keepThreadAlive=True
        self.logger.info('Listening on {}:{}'.format(self.ip, self.port))

        while not self.thread_stop:
            try:
                self.heart_beat=time.time()
                if self.ELV['link']=='Disconnect':
                    # self.logger.info('ELV {} connectting:{}, port:{}'.format(self.device_id, self.ip, self.port))
                    try:
                        client_sock, address=self.server.accept()
                        self.sock=client_sock
                        # self.sock.setblocking(False)  # test non-blocking
                        self.sock.settimeout(self.socket_timeout)
                        self.logger.info('\nAccepted connection from {}:{}\n'.format(address[0], address[1]))

                        '''self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.settimeout(10)
                        self.sock.connect((self.ip, self.port))'''
                    except socket.timeout:
                        self.logger.debug("Waiting for connection timed out.")
                        continue
                    except Exception as e:
                        # traceback.print_exc()
                        self.logger.warning("Failed to accept connection: {}".format(e))
                        time.sleep(1)
                        continue
                        # raise alarms.ELVConnectFailWarning(self.device_id)

                    self.logger.info('ELV Connected: {}, {}:{}'.format(self.device_id, self.ip, self.port))

                    self.ELV['link']='Unsynced'
                    self.ELV['syncing_time']=time.time()

                    self.auto()
                else:
                    try:
                        # if self.sock is None:
                        #     self.logger.warning("Socket is None, skipping settimeout and recv.")
                        #     time.sleep(1)
                        #     continue
                        if not self.sock:
                            self.logger.warning("No client socket-retrying accept.")
                            time.sleep(1)
                            continue
                        if time.time() - self.cmd_send_time  > 3 :
                            acquired = self.lock.acquire(False)
                            # if self.lock.acquire(False):
                            try:
                                if not acquired:
                                    self.logger.warning('Thread is busy, skipping send.')
                                    continue

                                data=json.dumps(self.cmd_parse.format(**self.cmd))
                                # self.sock.send(bytearray(data, encoding='utf-8'))
                                sent = self.safe_send(data)
                                if not sent:
                                    raise alarms.ELVWithAlarmWarning(self.device_id)
                                # self.safe_send(data)
                                # sent=self.safe_send(data)
                                # if not sent:
                                #     continue
                                self.logger.debug('[TSC_send] ' + data)
                                self.cmd_send_time=time.time()
                            except Exception as e:
                                self.logger.error("Send failed:\n{}".format(traceback.format_exc()))
                                raise alarms.ELVWithAlarmWarning(self.device_id)

                            finally:
                                if acquired:
                                    self.lock.release()
                        if self.sock is not None:
                            self.sock.settimeout(self.socket_timeout)
                        else:
                            self.logger.warning("Skipping settimeout: socket is None")
                            continue
                        # self.sock.settimeout(self.socket_timeout) #2sec
                        buf=self.sock.recv(4096).decode('utf-8')
                        # if buf == '':
                        #     self.logger.warning('Socket closed by peer')
                        #     self._close_connection()
                        #     raise alarms.ELVConnectFailWarning(self.device_id)
                        #     # time.sleep(1)
                        if buf:
                            self.logger.debug('debug: '+ str(buf))
                            self.logger.debug('[PLC_raw] ' + str(buf))
                        raw_rx+=buf

                        while not self.thread_stop:
                            if raw_rx!='':
                                # print(raw_rx)
                                payload=None
                                ''''if raw_rx.count('^') > 0_
                                    raw_data=raw_rx[:raw_rx.find("^")]
                                    raw_rx=raw_rx[raw_rx.find("^")+1:]
                                    payload=json.loads(raw_data)'''

                                # if raw_rx.count('Command') > 0:
                                if raw_rx.count('Location') > 0:
                                    # idx=raw_rx.find("]", raw_rx.find("Command"))+
                                    idx=raw_rx.find("]", raw_rx.find("Location"))+1
                                    raw_data=raw_rx[:idx]
                                    raw_rx=raw_rx[idx:]
                                    # raw_data=re.sub(r"\[Location:.*?\]", "", raw_data)
                                    # print('raw_data:', raw_data)
                                    # res=re.match("\[PM_Mode:(.+)\]\[Operation_Mode:(.+)\]\[Status:(.+)\]\[Command:(.+)\]", raw_data)
                                    res=re.match("\[PM_Mode:(.+)\]\[Operation_Mode:(.+)\]\[Status:(.+)\]\[Command:(.+)\]\[Location:(.+)\]", raw_data)
                                    # print('res:', res)
                                    if res:
                                        # payload={"PM":res.group(1), "OP":res.group(2), "Status":res.group(3), "CMD":res.group(4)}
                                        payload={"PM":res.group(1), "OP":res.group(2), "Status":res.group(3), "CMD":res.group(4), "Location":res.group(5)}

                                if payload:
                                    self.logger.debug('[TSC_recv] ' + str(payload))
                                    data=payload
                                    keys=['PM', 'OP', 'Status', 'CMD']
                                    check=False
                                    for key in keys:
                                        if self.ELV[key]!=payload[key]:
                                            self.logger.debug("Updating ELV[{}] from {} to {}".format(key, self.ELV[key], payload[key]))
                                            self.ELV[key]=payload[key]
                                            check=True
                                    self.ELV['link']='Synced'
                                    self.ELV['syncing_time']=time.time()

                                    if self.cmd_executing:  # go_floor, open_door, close_door, call_elv

                                        if self.check_command_completion(): # Check cmd_executing
                                            self.cmd_executing=False
                                    if check:
                                        self.logger.debug("ELV state changed, calling updateinfo")

                                        self.updateinfo()
                                    # else:
                                    #     self.logger.debug("No changes in ELV")

                                else:
                                    break
                            else:
                                break
                                # print('get null string')
                                # raise SocketNullStringWarning()

                    except socket.timeout:
                        self.ELV['link']='Unsynced'
                        if time.time()-self.ELV['syncing_time']>self.retry_time*self.socket_timeout: #5x2=10sec:
                            raise alarms.ELVLinkLostWarning(self.device_id)

                    except socket.error as e:
                        self.logger.warning('Socket error occurred: {}'.format(e))
                        self._close_connection()
                        time.sleep(1)
                        continue

                    except Exception: #chocp: 2021/4/15 for other exception
                        # traceback.print_exc()
                        self.logger.warning('\n'+traceback.format_exc())
                        raise alarms.ELVWithAlarmWarning(self.device_id)

                    time.sleep(0.1)

            except Exception: #ELVOffLineWarning
                #setalarm
                # traceback.print_exc()
                self.logger.warning('\n'+traceback.format_exc())
                self.ELV['link']='Disconnect'
                self.ELV['state']='Alarm'
                self.logger.info('<<Ready to close socket>>')
                # print('<<Ready to close socket>>')
                # self.sock.close()
                # if self.sock:
                self._close_connection()
                #     self.sock.close()
                #     self.logger.info('<<Socket Closed>>')
                #     self.sock=None
                # else:
                #     self.logger.info('<<Socket already Closed>>')
                # time.sleep(1)
                # print('<<Socket Closed>>')
                # self.logger.info('<<Socket Closed>>')
                time.sleep(1)

        self.server.close()
        self._close_connection()
        # if self.sock:
        #     self.sock.close()
        #     self.logger.info('<<Socket Closed>>')
        self.logger.info('{} end.'.format(self.device_id))



if __name__ == '__main__':

    setting={}
    setting['ip']=''
    setting['port']=4096
    setting['device_id']='ELV1'
    setting['device_type']='ELV'
    setting['retry_time']=10
    setting['socket_timeout']=2
    h=ELV(setting)
    h.setDaemon(True)
    h.start()
    try:
        while True:
            res=input('please input:') #go,215,300,180
            if res:
                cmds=res.split(',')
                if cmds[0] == 'auto':
                    h.auto()
                if cmds[0] == 'man':
                    h.man()
                if cmds[0] == 'stop':
                    h.stop_elv()
                if cmds[0] == 'open':
                    h.open_door()
                if cmds[0] == 'close':
                    h.close_door()
                if cmds[0] == 'call':
                    h.call_elv(int(cmds[1]))
                if cmds[0] == 'go':
                    h.go_floor(int(cmds[1]))
                if cmds[0] == 'check':
                    h.check_elv(int(cmds[1]))
                if cmds[0] == 'move':
                    h.mr_move(bool(int(cmds[1])), bool(int(cmds[2])))
                if cmds[0] == 'mr_stop':
                    h.mr_stop(bool(int(cmds[1])))
            print(h.ELV)
    except:
        traceback.print_exc()
        pass

















