import argparse
import collections
import sys
import traceback
import threading
import time

import socket


import json

class mWarning(Exception):
    pass

'''
if self.id == 'E01':
            self.status[0] ='GY001'
            self.status[11]='GY002'
'''

class eRackSimulator(threading.Thread):
    
    def __init__(self, ip, port, slot_datasets):

        self.ip=ip
        self.port=port
        #EMPTY'(light dark), 'IDENTIFIED'(light gray), 'ASSOCIATED'(green),'ERROR'(red)
        
        threading.Thread.__init__(self)
     
    def run(self):
        clientsock=0
        tcpsock=0

        print('start remote thread')
        tcpsock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #tcpsock.bind((eth0_ip or wlan0_ip, 5000))
        tcpsock.bind(('', self.port))
        tcpsock.listen(10)
        remote_status='off'

        while True:
          try:
            time.sleep(1)
            if remote_status == 'off':
                print('Accepting')
                (clientsock, (self.ip, self.port))=tcpsock.accept() #blocking
                remote_status='on'
            else:
                query_payload=[]
                for slot_idx in range(12):
                    query_payload.append({'status':slot_datasets[slot_idx]['status'],\
                                          'carrierID':slot_datasets[slot_idx]['carrierID'],\
                                          'lotID':slot_datasets[slot_idx]['lotID'],\
                                          'order':slot_datasets[slot_idx]['order'],\
                                          'stage':slot_datasets[slot_idx]['stage']})
                #print(query_payload)
                clientsock.send(json.dumps(query_payload))
                clientsock.settimeout(60)
                raw_data=clientsock.recv(2048).decode('utf-8')

                if raw_data == '':
                    print('comm break: get null string from socket')
                    raise mWarning('comm break: get null string from socket')
                else: #new for associate data
                    doc=json.loads(raw_data)
                    print(doc)
                    #doc={'res':'found', 'datasets':datasets, 'time':time.time()}
                    if doc['res'] == 'found':
                        for info in doc['datasets']:
                            slot_datasets[info['index']]['lotID']=info['lotID']
                            slot_datasets[info['index']]['stage']=info['stage']
 
                        
          except Exception as e:
            traceback.print_exc()  

            remote_status='off'
            if clientsock != 0:
                clientsock.close()
            time.sleep(1)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('port', metavar='PORT', type=int, nargs=1, help='eRack Port')
    parser.add_argument('-s', '-slot', metavar='FILENAME', type=argparse.FileType('r'), nargs=1, help='slot data setting file', default=[None])

    if len(sys.argv) == 1:
        print('Please enter port number')
        sys.exit(1)

    args=parser.parse_args()

    if args.s[0]:
        slot_datasets=json.load(args.s[0])
    else:
        slot_datasets=[\
            {'carrierID':'GY001', 'lotID':'LOT001', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'IDENTIFIED', 'lastQueryTime': 0},
            {'carrierID':'GY002', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'GY003', 'lotID':'LOT003', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'IDENTIFIED', 'lastQueryTime': 0},
            {'carrierID':'GY004', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            
            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},

            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},
            {'carrierID':'GY011', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'IDENTIFIED', 'lastQueryTime': 0},
            #{'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0},]
            {'carrierID':'GY012', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'IDENTIFIED', 'lastQueryTime': 0}]
    print(slot_datasets)

    h=eRackSimulator('127.0.0.1', args.port[0], slot_datasets)
    h.setDaemon(True)
    h.start()

    while True:
        try:
            res=input()
        except:
            pass
        time.sleep(5)

