#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import traceback
#from typing import Counter
#import serial
import tkinter as tk
import tkinter.messagebox as tkMessageBox
from tkinter import *
import threading
import json
#import queue 
#import requests
import xml.etree.ElementTree as ET
from time import clock_settime, sleep, time
from tkinter import ttk
from tkinter.messagebox import showinfo
import socket
#from numpy import * 
#from functools import partial
import argparse
import sys

carbutton=[]
window=0
loading_state_handle=0
load_carrierid_handle=[]
load_lotid_handle=[]
slot_no_label_handle=[]        
slot_carrierid_label_handle=[]
slot_carrierid_label1_handle=[]
slot_title_value1_handle=[]
slot_title_value2_handle=[]
slot_title_value3_handle=[]
slot_title_value4_handle=[]
carcombobox=[]
slot_lotid_label_handle=[]
slot_lotid_value_handle=[]
slot_operation_label_handle=[]
slot_operation_value_handle=[]
vv={}
selected=None
carrierNO=None
carrierID_status_list=[]
slot_datasets=[]
action_flag=1
clear_flag=0
row=3
col=4

slot_datasets=[{'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0} for i in range(row*col)]

class mWarning(Exception):
    pass

class eRackSimulator(threading.Thread):
    def startup(self):
        global window
        global loading_state_handle
        global carrierID
        global c
            
        def close_window():
            #self.tcpsock.close()
            window.destroy()
            sys.exit()

    #取carrierID status&value======================================================
        def get_id(c):
            global carrierNO
            carrierNO=slot_title_value2_handle[c-1].get() 

            if slot_datasets[c-1]["status"] == 'EMPTY':
                   
                if carrierNO == "":
                    slot_title_value3_handle[c-1].config(text='ERROR')
                    slot_datasets[c-1]['status']='ERROR'
                else:
                    slot_title_value3_handle[c-1].config(text=carrierNO)
                    slot_datasets[c-1]['carrierID']=carrierNO
                    slot_datasets[c-1]['status']='IDENTIFIED'
                    slot_title_value2_handle[c-1].delete(0,END)

                slot_carrierid_label_handle[c-1].config(text="unload")

            else:
                slot_datasets[c-1]['carrierID']=""
                slot_datasets[c-1]['status']='EMPTY'
                slot_title_value3_handle[c-1].config(text='EMPTY')
                slot_title_value2_handle[c-1].delete(0,END)

                slot_carrierid_label_handle[c-1].config(text=" load ")
         
  
        window=tk.Tk()
        window.geometry("100x50")
        window.title(self.name1)
        window.geometry("")
        window.config(bg='white')
        root=tk.Frame(window, bg='white')
        root.pack()

        f=tk.Frame(root, padx=8, pady=7, bg='LightBlue')
        #robot mmessage view
        f=tk.Frame(root, padx=8, pady=7, bg='LightBlue' )
        f.pack(side='bottom', fill='x')
        
        tk.Label(f, text="Link:", font=("Arial",15),  bg='LightBlue' ).pack(side='left')
        vv['robot_link_handle']=tk.Label(f, text=self.ip , fg='red', font=("Arial",15), bg='LightBlue' )
        vv['robot_link_handle'].pack(side='left')

        tk.Label(f, text="port:", font=("Arial",15),  bg='LightBlue' ).pack(side='left')
        vv['robot_port_handle']=tk.Label(f, text=self.port , fg='red', font=("Arial",15), bg='LightBlue' )
        vv['robot_port_handle'].pack(side='left')
        
        tk.Label(f, text=" Connection status:", font=("Arial",15),  bg='LightBlue' ).pack(side='left')
        vv['Connection_status1']=tk.Label(f, text="offline", fg='red', font=("Arial",15), bg='LightBlue' )
        vv['Connection_status1'].pack(side='left')

        button=tk.Button(f, text='Exit', font=("Arial",15), bg='LightBlue', command= close_window)
        button.pack(side='right')
 
        mf=tk.Frame(root, bg='LightYellow')
        mf.pack(side='left')
        for i in range(row):
            for j in range(col):
                n=i*col+j+1
                carrierID=None
                m=tk.Frame(mf, padx=3, pady=3, borderwidth=2, relief='groove')
                m.grid(row=i,column=j)
                f=tk.Frame(m)
                f.pack(side='left')        
    #CarrierID
                CarrierID=tk.Label(f, text="1-"+str(n), font=("Arial", 14), width=10, height=1, relief='groove', bg='LightYellow')
                CarrierID.pack(anchor='w')   

    #CarrierID input
                carrierID=tk.Entry(f, font=("Arial",14), width=10, bg='LightGray')#手動輸入貨號
                carrierID.pack()
                slot_title_value2_handle.append(carrierID)
                slot_title_value2_handle[n-1].pack()
                f=tk.Frame(m)
                f.pack(side='left')
    #status
                status=tk.Label(f, font=("Arial",14), width=10, bg='LightGray')
                status.pack()
                slot_title_value3_handle.append(status)
                slot_title_value3_handle[n-1].config(text="EMPTY")
                slot_title_value3_handle[n-1].pack()
                if args.s[0]:
                    if slot_datasets[n-1]["carrierID"] != '':
                        slot_title_value3_handle[n-1].config(text=slot_datasets[n-1]["carrierID"])
                    else:
                        slot_title_value3_handle[n-1].config(text="EMPTY")      
    #CarrierID button-----------------------------------------------------------------------------------------------------------------------------------------------------------
                carrierID_state=tk.Button(f, text="load" , font=("Arial",13), width=8, height=1, relief='groove', bg='LightYellow', command= lambda m=n: get_id(m))
                carrierID_state.pack()
                slot_carrierid_label_handle.append(carrierID_state)
                slot_carrierid_label_handle[n-1].pack()
                if args.s[0]:
                    if slot_datasets[n-1]["carrierID"] != '':
                        slot_carrierid_label_handle[n-1].config(text="unload")
                    else:
                        slot_carrierid_label_handle[n-1].config(text="load")
                f=tk.Frame(m)
                f.pack(side='left')
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------  
    def runloop(self):        
        window.mainloop()

    def __init__(self, ip, port, name1, slot_datasets):
        self.ip=ip
        self.port=port
        self.name1=name1
        threading.Thread.__init__(self)
    
    def run(self):
        global selected
        clientsock=0
        self.tcpsock=0

        print('start remote thread')
        self.tcpsock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcpsock.bind(('', self.port))
        self.tcpsock.listen(10)
        remote_status='off'

        while True:
          try:
            sleep(1)
            if remote_status == 'off':               
                print('Accepting')#
                (clientsock, (self.ip, self.port))=self.tcpsock.accept() #blocking
                remote_status='on'
                vv['Connection_status1'].configure(text='online')

            else:
                query_payload=[]
                for slot_idx in range(row*col):
                    query_payload.append({'status':slot_datasets[slot_idx]['status'],\
                                          'carrierID':slot_datasets[slot_idx]['carrierID'],\
                                          'lotID':slot_datasets[slot_idx]['lotID'],\
                                          'order':slot_datasets[slot_idx]['order'],\
                                          'stage':slot_datasets[slot_idx]['stage']})
                #print(query_payload)
                clientsock.send(bytearray(json.dumps(query_payload).encode('utf-8')))
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
            #tcpsock.close()
#---------------------------------------------------------------------------------------------------
          except Exception as e:
            traceback.print_exc()  
            remote_status='off'
            vv['Connection_status1'].configure(text='offline')
            if clientsock != 0:
                clientsock.close()
            sleep(1)
    
if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('port', metavar='PORT', type=int, nargs=1, help='eRack Port')
    parser.add_argument('name1', metavar='Robot', type=str, nargs=1, help='eRack name')
    parser.add_argument('-s', '-slot', metavar='FILENAME', type=argparse.FileType('r'), nargs=1, help='slot data setting file', default=[None])
    parser.add_argument('-r', '-row', metavar='Row', type=int, nargs=1, help='eRack row number', default=[3], dest="row")
    parser.add_argument('-c', '-col', metavar='Col', type=int, nargs=1, help='eRack column number', default=[4], dest="col")

    if len(sys.argv) == 1:
        print('Please enter port number and Erack name')
        sys.exit(1)

    args=parser.parse_args()
    row=args.row[0]
    col=args.col[0]

    if args.s[0]:
        slot_datasets=json.load(args.s[0])
    else:
        slot_datasets=[{'carrierID':'', 'lotID':'', 'stage':'', 'order':'', 'machine':'', 'errorCode':'0000', 'led_status':'0000', 'status':'EMPTY', 'lastQueryTime': 0} for i in range(row*col)]
    print(slot_datasets)

    h=eRackSimulator('127.0.0.1', args.port[0], args.name1[0], slot_datasets)
    h.setDaemon(True)
    h.start()
    h.startup()
    h.runloop()

    while True:
        try:
            res=input()
        except:
            pass
        sleep(5)
    
