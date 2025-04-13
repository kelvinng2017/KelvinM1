
import threading
import traceback
import collections
import socket
import json
import time
from global_variables import output
import uuid
from datetime import datetime
import os
import logging
import logging.handlers as log_handler
import alarms

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
    '0x1001':'Firefighting: Smoke detected',
    '0x1002':'Ceiling over temperature',
    '0x1003':'Over temperature between charger 1 and 2',
    '0x1004':'Over temperature between charger 3 and 4',
    '0x1005':'System emergency stop',
    '0x1006':'CDA error',
    '0x1007':'X-axis servo not ready',
    '0x1008':'X-axis servo failure',
    '0x1009':'X-axis initialization timeout',
    '0x1010':'X-axis running timeout',
    '0x1011':'X-axis_uninitialized',
    '0x1012':'Y-axis servo not ready',
    '0x1013':'Y-axis servo failure',
    '0x1014':'Y-axis initialization timeout',
    '0x1015':'Y-axis running timeout',
    '0x1016':'Y-axis_uninitialized',
    '0x1017':'Z-axis servo not ready',
    '0x1018':'Z-axis servo failure',
    '0x1019':'Z-axis initialization timeout',
    '0x1020':'Z-axis running timeout',
    '0x1021':'Z-axis uninitialized',
    '0x1022':'Y-axis gripper open timeout',
    '0x1023':'Y-axis gripper grip timeout',
    '0x1024':'Z-axis gripper open timeout',
    '0x1025':'Z-axis gripper grip timeout',
    '0x1026':'X-axis servo positive limit',
    '0x1027':'X-axis servo negative limit',
    '0x1028':'Y-axis servo positive limit',
    '0x1029':'Y-axis servo negative limit',
    '0x1030':'Z-axis servo positive limit',
    '0x1031':'Z-axis servo negative limit',
    '0x1032':'Ramp stretched out timeout',
    '0x1033':'Ramp back timeout',
    '0x1034':'Temporary storage battery push timeout',
    '0x1035':'Pusher back timeout',
    '0x1036':'Platform 1 back timeout',
    '0x1037':'Platform 1 stretched out timeout',
    '0x1038':'Plug 1 unplug timeout',
    '0x1039':'Plug 1 inserted timeout',
    '0x1040':'Plug 1 back timeout',
    '0x1041':'Plug 1 stretched out timeout',
    '0x1042':'Platform 2 back timeout',
    '0x1043':'Platform 2 stretched out timeout',
    '0x1044':'Plug 2 unplug timeout',
    '0x1045':'Plug 2 inserted timeout',
    '0x1046':'Plug 2 back timeout',
    '0x1047':'Plug 2 stretched out timeout',
    '0x1048':'Platform 3 back timeout',
    '0x1049':'Platform 3 stretched out timeout',
    '0x1050':'Plug 3 unplug timeout',
    '0x1051':'Plug 3 inserted timeout',
    '0x1052':'Plug 3 back timeout',
    '0x1053':'Plug 3 stretched out timeout',
    '0x1054':'Platform 4 back timeout',
    '0x1055':'Platform 4 stretched out timeout',
    '0x1056':'Plug 4 unplug timeout',
    '0x1057':'Plug 4 inserted timeout',
    '0x1058':'Plug 4 back timeout',
    '0x1059':'Plug 4 stretched out timeout',
    '0x1060':'AGV Plug unplug timeout',
    '0x1061':'AGV Plug inserted timeout',
    '0x4062':'PMbus.1 alarm',
    '0x4063':'PMbus.2 alarm',
    '0x4064':'PMbus.3 alarm',
    '0x4065':'PMbus.4 alarm',
    '0x4066':'AGV_PMbus alarm',
    '0x4067':'SBP 1 alarm',
    '0x4068':'SBP 2 alarm',
    '0x4069':'SBP 3 alarm',
    '0x4070':'SBP 4 alarm',
    '0x4071':'SBP of AGV alarm',
    '0x4072':'Plug 1 over temperature',
    '0x4073':'Plug 2 over temperature',
    '0x4074':'Plug 3 over temperature',
    '0x4075':'Plug 4 over temperature',
    '0x4076':'AGV Plug over temperature',
    '0x4077':'PMbus 1 over temperature',
    '0x4078':'PMbus 2 over temperature',
    '0x4079':'PMbus 3 over temperature',
    '0x4080':'PMbus 4 over temperature',
    '0x4081':'PMbus for AGV over temperature',
    '0x3082':'E84_EMO',
    '0x3083':'E84_ERROR',
    '0x2084':'Battery.1 Alarm',
    '0x2085':'Battery.1_overvoltage',
    '0x2086':'Battery.1 undervoltage',
    '0x2087':'Battery.1 overcurrent',
    '0x2088':'Battery.1 undercurrent',
    '0x2089':'Battery.1 over temperature',
    '0x2090':'Battery.2 Alarm',
    '0x2091':'Battery.2 overvoltage',
    '0x2092':'Battery.2 undervoltage',
    '0x2093':'Battery.2 overcurrent',
    '0x2094':'Battery.2 undercurrent',
    '0x2095':'Battery.2 over temperature',
    '0x2096':'Battery.3 Alarm',
    '0x2097':'Battery.3 overvoltage',
    '0x2098':'Battery.3 undervoltage',
    '0x2099':'Battery.3 overcurrent',
    '0x2100':'Battery.3 undercurrent',
    '0x2101':'Battery.3 over temperature',
    '0x2102':'Battery.4Alarm',
    '0x2103':'Battery.4 overvoltage',
    '0x2104':'Battery.4 undervoltage',
    '0x2105':'Battery.4 overcurrent',
    '0x2106':'Battery.4 undercurrent',
    '0x2107':'Battery.4 over temperature',
    '0x3108':'IPC & PLC connect error',
    '0x1109':'Component not ready',
    '0x1110':'Did not have full charge battery, cannot switch to auto mode',
    '0x3111':'Did not receive AMR msg in auto mode(44)',
    '0x1112':'Failed to extract battery from AMR in auto mode(45)',
    '0x1113':'AMR disconnect in auto mode(46)',
    '0x1114':'AMR disconnect in auto mode(47)',
    '0x1115':'FLIR error',
    '0x1116':'FLIR_platform 1 over temperature',
    '0x1117':'FLIR_platform 2 over temperature',
    '0x1118':'FLIR_platform 3 over temperature',
    '0x1119':'FLIR_platform 4 over temperature',
    '0x1120':'Charger1 batt detect failed',
    '0x1121':'Charger2 batt detect failed',
    '0x1122':'Charger3 batt detect failed',
    '0x1123':'Charger4 batt detect failed',
    '0x2124':'Batt1 charge error',
    '0x2125':'Batt2 charge error',
    '0x2126':'Batt3 charge error',
    '0x2127':'Batt4 charge error',
    '0x1128':'Batt move space detect failed',
}

class ABCS(threading.Thread):

    def __init__(self, setting, callback=None):

        self.listeners=[]

        self.retry_time=setting.get('retry_time', 5)
        self.socket_timeout=setting.get('socket_timeout', 2)

        self.device_id=setting.get('device_id', 'ABCS')
        self.device_type=setting.get('device_type', 'ABCS')
        self.ip=setting.get('ip', '127.0.0.1')
        self.port=setting.get('port', 5500)

        self.code=0
        self.extend_code=0
        self.msg=''

        self.ABCS=collections.OrderedDict({
                    "device_id":self.device_id,
                    "link":"Disconnect",
                    "syncing_time":0,
                    "state": "Unknown",
                    "substate": "Idle",
                    "alarm_list": [],
                    "env": {
                        "AGVChargeConnecterTemp": 0,
                        "1_2SinkTemp": 0,
                        "3_4SinkTemp": 0,
                        "RoofTemp": 0,
                        "RoofSmokeDetect": "Unknown"
                    },
                    "sink":[
                    ]
                })

        self.req=collections.OrderedDict()
        self.req["version"]="1.0"
        self.req["head"]={
                    "date": "",
                    "uuid": "",
                    "service": "request"
                }
        self.req["data"]={
                    "typename": "GetInfo",
                    "id": 0,
                    "status": {}
                }

        self.logger=logging.getLogger(self.device_id) # Mike: 2021/05/17
        self.logger.setLevel(logging.DEBUG)

        for h in self.logger.handlers[:]: # Mike: 2021/09/22
            self.logger.removeHandler(h)
            h.close()

        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_{}.log".format(self.device_id)), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(fileHandler)

        # For console. Mike: 2021/07/16
        streamHandler=logging.StreamHandler()
        streamHandler.setLevel(logging.INFO)
        streamHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(streamHandler)

        self.updateinfo() #choc add 2021/10/13

        self.lock=threading.Lock()

        self.heart_beat=0
        self.thread_stop=False
        threading.Thread.__init__(self)

    def add_listener(self, obj):
        self.listeners.append(obj)

    def notify(self, event):
        # self.logger.debug('[notify] {}'.format(event))
        # print(('[notify] {}'.format(event)))
        for obj in self.listeners:
            obj.on_notify(*event)

    def updateinfo(self):
        self.notify(('ABCSStatusUpdate', self.ABCS))

    def update_params(self, setting):
        self.device_id=setting.get('device_id', 'ABCS')
        self.device_type=setting.get('device_type', 'ABCS')

    def put_batt(self): # Mike: 2023/11/28
        print('PutBatt')
        try:
            self.send_cmd('PutBatt')
        except:
            pass

    def send_cmd(self, service): # Mike: 2023/11/28
        while not self.lock.acquire():
            time.sleep(0.01)
        self.req['head']['uuid']=str(uuid.uuid4())
        self.req['head']['date']=datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.req['data']['typename']=service
        data=json.dumps(self.req)
        self.logger.debug('[send] ' + data)
        self.lock.release()
        self.sock.send(bytearray(data+'^', encoding='utf-8'))


    def event_handler(self, event_list):
        self.ABCS['alarm_list']=[]
        for event in event_list:
            if event in alarm_list:
                self.ABCS['alarm_list'].append(event)
                alarms.ABCSWithAlarmWarning(self.device_id, event)
            elif event == '0x0001':
                self.ABCS['alarm_list']=[]
                self.updateinfo()
            elif event == '0x0002':
                self.ABCS['state']='Standby'
                self.updateinfo()
            elif event == '0x0003':
                self.ABCS['state']='Busy'
                self.updateinfo()
            elif event == '0x0004':
                self.ABCS['state']='Manual'
                self.updateinfo()
            elif event == '0x5003':
                self.ABCS['substate']='Exchanging'
                self.updateinfo()
            elif event == '0x5002':
                self.ABCS['substate']='Idle'
                self.updateinfo()

    def run(self):
        raw_rx=''
        self.last_state=''
        req_toc=0
        #self.change_state('enable')
        while not self.thread_stop:
            try:
                self.heart_beat=time.time()
                if self.ABCS['link'] == 'Disconnect':
                    self.logger.info('ABCS {} connectting:{}, port:{}'.format(self.device_id, self.ip, self.port))
                    try:
                        self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.settimeout(10)
                        self.sock.connect((self.ip, self.port))
                    except:
                        traceback.print_exc()
                        raise alarms.ABCSConnectFailWarning(self.device_id)
                        
                    self.logger.info('ABCS Connected: {}, {}:{}'.format(self.device_id, self.ip, self.port))

                    self.ABCS['link']='Unsynced'
                    self.ABCS['syncing_time']=time.time()
                    #self.sock.send(bytearray(json.dumps({'cmd': 'simulation'}), encoding='utf-8'))
                    self.send_cmd('GetInfo') # Mike: 2023/11/28
                    req_toc=time.time()
                else: 
                    try:
                        if time.time()-req_toc > 5:
                            self.send_cmd('GetInfo') # Mike: 2023/11/28
                            req_toc=time.time()

                        self.sock.settimeout(self.socket_timeout) #2sec
                        buf=self.sock.recv(4096).decode('utf-8')
                        if buf:
                            self.logger.debug('[raw] ' + str(buf))
                        raw_rx+=buf

                        while True:
                            if raw_rx!='':
                                # print(raw_rx)
                                payload=None
                                if raw_rx.count('^') > 0:
                                    raw_data=raw_rx[:raw_rx.find("^")]
                                    raw_rx=raw_rx[raw_rx.find("^")+1:]
                                    payload=json.loads(raw_data)

                                if payload:
                                    self.logger.debug('[recv] ' + str(payload))
                                    if payload['head']['service'] == 'reply':
                                        if payload['data']['typename'] == 'GetInfo':
                                            data=payload['data']['status']
                                            keys=['state', 'env', 'sink']
                                            check=False
                                            for key in keys:
                                                if self.ABCS[key] != data[key]:
                                                    self.ABCS[key]=data[key]
                                                    check=True
                                            self.ABCS['link']='Synced'
                                            self.ABCS['syncing_time']=time.time()
                                            #self.sock.send(bytearray(json.dumps({'result': 'ok'}), encoding='utf-8'))

                                            if check:
                                                self.updateinfo()

                                    elif payload['head']['service'] == 'notification':
                                        data=payload['data']['status']
                                        event_list=[]
                                        for event in data['event']:
                                            event_list.append(event['code'])

                                        self.event_handler(event_list)
                                else:
                                    break
                            else:
                                break
                                # print('get null string')
                                # raise SocketNullStringWarning()

                    except socket.timeout:
                        self.ABCS['link']='Unsynced'
                        if time.time()-self.ABCS['syncing_time']>self.retry_time*self.socket_timeout: #5x2=10sec:
                            raise alarms.LinkLostWarning(self.device_id)

                    except: #chocp: 2021/4/15 for other exception
                        # traceback.print_exc()
                        self.logger.warning('\n'+traceback.format_exc())
                        raise alarms.ABCSConnectFailWarning(self.device_id)
                    time.sleep(0.1)

            except: #ErackOffLineWarning
                #setalarm
                #traceback.print_exc()
                self.logger.warning('\n'+traceback.format_exc())
                self.ABCS['link']='Disconnect'
                self.ABCS['state']='Alarm'
                self.sock.close()
                time.sleep(1)




if __name__ == '__main__':

    setting={}
    setting['ip']='127.0.0.1'
    setting['port']=5003
    setting['device_id']='ABCS1'
    setting['device_type']='ABCS'
    setting['retry_time']=10
    setting['socket_timeout']=2
    h=ABCS(setting)
    h.setDaemon(True)
    h.start()
    try:
        while True:
            res=raw_input('please input:') #go,215,300,180
            cmds=res.split(',')
            
            print(h.ABCS)
    except:
        traceback.print_exc()
        pass













    


  
