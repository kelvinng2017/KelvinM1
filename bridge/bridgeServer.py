import threading
from global_variables import remotecmd_queue
from global_variables import Erack
import zmq
import requests

class BridgeServer(threading.Thread):
    __instance=None
    def getInstance():
        return __instance

    def __init__(self, port):
        self.socket=zmq.Context().socket(zmq.PAIR)
        self.socket.bind('tcp://*:{}'.format(port))
        self.socket.setsockopt(zmq.RCVTIMEO, 1000)
        self.thread_stop=False

        BridgeServer.__instance=self
        threading.Thread.__init__(self)

    def disable(self):
        self.thread_stop=True

    def report(self, msg):
        self.socket.send_json(msg)

    def run(self):
        while not self.thread_stop:
            try:
                msg=self.socket.recv_json()
                if msg.get('cmd') == 'EQState':
                    obj=msg.get('data')
                    obj['remote_cmd']='EQState'

                    remotecmd_queue.append(obj)

                elif msg.get('cmd') == 'Infoupdate':
                    obj={}
                    obj['remote_cmd']='infoupdate'
                    obj['CarrierID']=msg['data'].get('CarrierID')
                    obj['Data']={}
                    for key, value in msg.get('data', {}).items():
                        obj['Data'][key]=value

                    Erack.h.remote_command_callback(obj)
                elif msg:
                    print('<Warn: Receive invaild message from zero MQ...>')
            except zmq.Again:
                # print("Timeout occurred, attempting to reconnect")
                pass
               