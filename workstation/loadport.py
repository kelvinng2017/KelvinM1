
import threading
import traceback
import collections
import socket
import json
import time
from global_variables import output
from global_variables import remotecmd_queue
from global_variables import output

class MyException(Exception):
    pass

class SocketNullStringWarning(MyException):
    def __init__(self, txt='receive null string'):
        self.alarm_set='Error'
        self.code=30001
        self.txt=txt


class ConnectFailWarning(MyException):
    def __init__(self, txt='connect fail'):
        self.alarm_set='Error'
        self.code=30002
        self.txt=txt
        
class LinkLostWarning(MyException):
    def __init__(self, txt='linking timeout'):
        self.alarm_set='Error'
        self.code=30003
        self.txt=txt

class LoadPort(threading.Thread):

    def __init__(self, setting, callback=None, check_timeout=10, retry_timeout=5, socket_timeout=2):
        
        self.retry_timeout=retry_timeout
        self.socket_timeout=socket_timeout
        self.check_timeout=check_timeout

        self.enter_standby_time=0
        self.enter_unloaded_time=0

        self.listeners=[]
        self.workstation_type=setting.get('type', 'LotIn&LotOut') 
        self.zoneID=setting.get('zoneID', '')
        self.stage=setting.get('stage', '')
        self.workstationID=setting.get('portID', '')
        self.back_erack=setting.get('return', '') 
        self.carrier_source=setting.get('from', '')
        self.valid_input=setting.get('validInput', True)

        self.BufConstrain=setting.get('bufConstrain', False) #for Buf Constrain
        self.open_door_assist=setting.get('openDoorAssist', False) #for req open door assist
        self.limitBuf=setting.get('limitBuf', 'All')

        state=setting.get('state')
        self.state= state if state else 'Unknown'
        
        carrierID=setting.get('carrierID')
        self.carrierID=carrierID if carrierID else 'Unknown'

        alarm=setting.get('alarm')
        self.alarm=alarm if alarm else False

        self.ip=setting.get('ip', '127.0.0.1')
        self.port=setting.get('port', 5500)

        self.code=0
        self.extend_code=0
        self.msg=''

        self.callback=callback

        self.state='Disable'
        self.carrierID='Unknown'
        
        self.loadport={ 
                        'link':'Disconnect',
                        'state':'Error',
                        'msg':'',
                        'code':'',
                        'ps':False,
                        'pl1':False,
                        'pl2':False,
                        'pl3':False,
                        'clamp':False,
                        'cmd_queue':collections.deque(maxlen=100),
                        'syncing_time':0
                        }

        self.notify('initial') #choc add 2021/10/13

        self.thread_stop=False
        threading.Thread.__init__(self)

    def add_listener(self, obj):
        self.listeners.append(obj)
        obj.on_notify(self, 'sync')

    def notify(self, event):
        for obj in self.listeners:
            obj.on_notify(self, event)

    def enter_unknown_state(self, event):
        self.state='Unknown'
        self.carrierID='Unknown'
        self.notify(event)
        
    def enter_unloaded_state(self, event):
        self.state='UnLoaded'
        self.carrierID='Unknown'
        self.enter_unloaded_time=time.time()
        self.notify(event)
        self.callback(self.stage, self, False)

    def enter_loaded_state(self, event):
        self.state='Loaded'
        self.notify(event)
        self.callback(self.stage, self, True)

    def enter_other_state(self, event, next_state):
        self.state=next_state
        self.notify(event)

    def change_state(self, event, data='None'):
        #print(self.workstationID, self.state, event)
        if self.state == 'Disable':
            if event == 'enable':
                self.enter_unknown_state(event)

        elif self.state == 'Unknown':
            if event == 'loadport_sync': # event from loadport
                if self.loadport['state'] == 'ReadyToUnload':
                    self.enter_loaded_state(event)

                elif self.loadport['state'] == 'ReadyToLoad': 
                    self.enter_unloaded_state(event)

                elif self.loadport['state'] == 'Error': 
                    self.loadport['cmd_queue'].append({'cmd':'e84_reset'})

            elif event == 'load_transfer_cmd':
                self.enter_other_state(event, 'CallLoad')
            
            elif event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'CallReplace')

            elif event == 'unload_transfer_cmd':
                self.enter_other_state(event, 'CallUnLoad')

            elif event == 'manual_port_state_set': #new
                next_state=data.get('next_state')
                if next_state == 'Loaded':
                    self.enter_loaded_state(event)

                elif next_state == 'UnLoaded':
                    self.enter_unloaded_state(event)

                elif next_state in ['CallLoad', 'CallReplace', 'CallUnLoad', 'Loading', 'Exchange', 'UnLoading', 'Running']:
                    self.enter_other_state(event, next_state)
    
        elif self.state == 'UnLoaded': #need cycle trigger dispatch
            if event == 'load_transfer_cmd':
                self.enter_other_state(event, 'CallLoad')

            elif event == 'loadport_sync':
		#print('here', self.enter_unloaded_time)
                if self.enter_unloaded_time and (time.time()-self.enter_unloaded_time)>self.check_timeout:
                    self.enter_unloaded_state(event)

        elif self.state == 'Loaded': #need cycle trigger dispatch
            if event == 'replace_transfer_cmd':
                self.enter_other_state(event, 'CallReplace')

            elif event == 'unload_transfer_cmd':
                self.enter_other_state(event, 'CallUnLoad')

        elif self.state == 'CallReplace':
            if event == 'acquire_start_evt':
                self.enter_other_state(event, 'Exchange')

        elif self.state == 'CallLoad':
            if event == 'deposit_start_evt':
                self.enter_other_state(event, 'Loading')

        elif self.state == 'CallUnLoad':
            if event == 'acquire_start_evt':
                self.enter_other_state(event, 'UnLoading')

        elif self.state == 'UnLoading':
            if event == 'acquire_complete_evt':
                self.enter_unloaded_state(event)

        elif self.state == 'Loading':
            if event == 'deposit_complete_evt':
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_standby_time=time.time()
                self.enter_other_state(event, 'Standby')

        elif self.state == 'Exchange':
            if event == 'deposit_complete_evt':
                self.carrierID=data.get('carrierID')
                self.carrier_source=data.get('source', '') #chocp add 9/1
                self.enter_standby_time=time.time()
                self.enter_other_state(event, 'Standby') #................

        elif self.state == 'Standby':
            if event == 'loadport_sync':
                if self.loadport['clamp']: # event from loadport
                    self.enter_other_state(event, 'Running')

                elif self.enter_standby_time and (time.time()-self.enter_standby_time)>self.check_timeout:
                    self.enter_unknown_state(event)
            #add timeout

        elif self.state == 'Running':
            if event == 'loadport_sync' and not self.loadport['clamp']: # event from loadport
                self.enter_loaded_state(event)
             
        if event == 'alarm_set':
            self.alarm=True
            self.state='Alarm'
            self.code=50000
            self.msg='Loadport {}: caused by vehicle'.format(self.workstationID)
            self.notify('alarm_set')

        elif event == 'alarm_reset':
            self.alarm=False
            self.enter_unknown_state(event)


    def run(self):
        raw_rx=''
        #self.change_state('enable')
        while not self.thread_stop:
            try:
                if self.loadport['link'] == 'Disconnect':
                    print('LoadPort {} connectting:{}, port:{}'.format(self.workstationID, self.ip, self.port))
                    try:
                        self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.settimeout(10)
                        self.sock.connect((self.ip, self.port))
                    except:
                        raise ConnectFailWarning()
                        
                    print('LoadPort Connected:', self.workstationID, self.ip, self.port)

                    self.loadport['link']='UnSynced'
                    self.loadport['syncing_time']=time.time()
                    #self.sock.send(bytearray(json.dumps({'cmd': 'simulation'}), encoding='utf-8'))
                    self.sock.send(bytearray(json.dumps({'cmd': 'sync'}), encoding='utf-8'))
                else: 
                    try:
                        self.sock.settimeout(self.socket_timeout) #2sec
                        raw_rx=self.sock.recv(2048).decode('utf-8')

                        if raw_rx!='':
                            if raw_rx.count('{') == 1:
                                payload=json.loads(raw_rx)
                            
                                if payload['head'] == 'update':
                                    self.loadport['state']=payload['state']
                                    self.loadport['ps']=payload['ps']
                                    self.loadport['pl1']=payload['pl1']
                                    self.loadport['pl2']=payload['pl2']
                                    self.loadport['pl3']=payload['pl3']
                                    self.loadport['clamp']=payload['clamp']
                                    self.loadport['link']='Synced'
                                    #self.sock.send(bytearray(json.dumps({'result': 'ok'}), encoding='utf-8'))
                                    self.loadport['syncing_time']=time.time()
                                
                                    self.change_state('loadport_sync')

                            if len(self.loadport['cmd_queue']) > 0:
                                cmd=self.loadport['cmd_queue'].popleft()
                                self.sock.send(bytearray(json.dumps(cmd), encoding='utf-8'))
                        else:
                            print('get null string')
                            raise SocketNullStringWarning()

                    except (socket.timeout, SocketNullStringWarning):
                        self.loadport['link']='UnSynced'
                        if time.time()-self.loadport['syncing_time']>self.retry_timeout*self.socket_timeout: #5x2=10sec:
                            raise LinkLostWarning()
                        else:
                            self.sock.send(bytearray(json.dumps({'cmd': 'sync'}), encoding='utf-8'))

                    except: #chocp: 2021/4/15 for other exception
                        raise ConnectFailWarning()
                    time.sleep(0.1)

            except: #ErackOffLineWarning
                #setalarm
                traceback.print_exc()
                self.loadport['link']='Disconnect'
                self.sock.close()
                self.change_state('link_lost')
                time.sleep(1)




if __name__ == '__main__':

    h=LoadPort(idx=0, workstationID='S1P1', enable=True, ip='127.0.0.1', retry_timeout=1, socket_timeout=2)
    #h.setDaemon(True)
    #h.start()
    try:
        while True:
            res=raw_input('please input:') #go,215,300,180
            cmds=res.split(',')
  
            if cmds[0] == 'i':
                print('query info')
                print('...')

            elif cmds[0] == 'r':

                print('get e84 reset cmd')
                h.loadport['cmd_queue'].append({'cmd':'e84_reset'})
                h.change_state('alarm_reset')
            
            elif cmds[0] == 's':
                print('get simulation cmd')
                h.loadport['cmd_queue'].append({'cmd':'simulation'})

            else:
                value=cmds[0]
                h.loadport['cmd_queue'].append({'cmd':value})          
    except:
        traceback.print_exc()
        pass













    


  
