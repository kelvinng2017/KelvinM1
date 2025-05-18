import global_variables
from global_variables import output

from .iot_module import module_list

import time
import threading
import traceback
import logging
import semi.e82_equipment as E82
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E88_STK_Host
from semi.SecsHostMgr import E82_Host
from global_variables import remotecmd_queue
from global_variables import Equipment
from global_variables import Erack
from global_variables import Vehicle

import tools

import re
import queue


import alarms

my_lock=threading.Lock()

class IotView():
    __instance=None

    @staticmethod
    def getInstance():
        #print('call MCS_VIEW getInstance')
        if IotView.__instance == None:
            IotView()
        return IotView.__instance

    def __init__(self):
        IotView.__instance=self

    def on_notify(self, event, param):

        #chocp 2021/10/23 cancel loadport report alarm
        #should change 'portID' => 'workstationID'
        output(event, param)


work_list=[]

#only accept carrier schedule to tools
#if receive carrier unload from tools, then direct pass to transfer waiting queue

class IotMgr(threading.Thread):

    __instance=None

    @staticmethod
    def getInstance():
        #print('call IotMgr getInstance')
        if IotMgr.__instance == None:
            IotMgr(config=[])
        return IotMgr.__instance

    def __init__(self, config=[]):
        self.api_queue=queue.Queue()
        self.devices={}
        self.tsclogger=logging.getLogger("tsc")

        IotMgr.__instance=self
        threading.Thread.__init__(self)

    def add_listener(self, obj):
        for deviceID, h in self.devices.items():
            h.add_listener(obj)

    #for thread
    def run(self):
        while(True):
            for iot_id, h in self.devices.items():
                if h.heart_beat > 0 and time.time() - h.heart_beat > 60:
                    h.heart_beat=0
                    self.tsclogger.info('{}'.format("<<<  IotAdapter {} is dead. >>>".format(iot_id)))

            obj=None
            try:
                obj=self.api_queue.get(timeout=1)
            except:
                continue
            tmp={}

            """if obj['cmd'] == 'start' or obj['cmd'] == 'restart':
                for deviceID, h in self.devices.items():
                    h.thread_stop=True

                time.sleep(1)

                self.devices={}

                for idx, setting in enumerate(obj['config']): #eq_settings->workstation

                    if setting['enable']:
                        '''
                        if setting['portID'] == 'WSD137': # for test only
                            print(setting)
                        '''
                        h=module_list[setting['controller']](setting)

                        h.setDaemon(True)
                        h.start()
                        h.add_listener(IotView.getInstance())


            elif obj['cmd'] == 'stop':
                for deviceID, h in self.devices.items():
                    h.thread_stop=True"""

            if obj['cmd'] == 'start' or obj['cmd'] == 'restart':
                self.tsclogger.info('{} '.format('<<< get IOTSettings >>>'))
                for idx, setting in enumerate(obj['config']):

                    device_model=setting['device_model']
                    device_id=setting['device_id']
                    try:
                        h_device=self.devices.pop(device_id)
                    except:
                        h_device=0

                    if device_id in tmp: # zhangpeng 2025-02-13 # Prevent duplicate creation of threads with the same vehicle id
                        continue

                    if h_device:
                        if h_device.ip == setting['ip'] and h_device.port == setting['port']:
                            if setting['enable']:
                                if not h_device.is_alive():
                                    h_device.start()
                                print("<<< continue: {} >>>".format(device_id))
                                h_device.update_params(setting)
                                tmp[device_id]=h_device #end
                                continue
                            else:
                                if not h_device.is_alive():
                                    print("<<< continue: {} >>>".format(device_id))
                                    h_device.update_params(setting)
                                    tmp[device_id]=h_device #end
                                    continue
                                print("<<< stop: {} >>>".format(device_id))
                                h_device.thread_stop=True
                                #time.sleep(5) #can't change vehicleID
                        else:
                            print("<<< stop: {} >>>".format(device_id))
                            h_device.thread_stop=True

                    #no obj or no thread alive
                    if device_model=='ELV':
                        secsgem_e88_stk_h=E88_STK_Host.getInstance(device_id)
                        h_device=module_list[setting['controller']](secsgem_e88_stk_h, setting)
                    else:
                        h_device=module_list[setting['controller']](setting)
                    h_device.add_listener(IotView.getInstance())
                    if setting['enable']:
                        print("<<< new: {} >>>".format(device_id))
                        # h_vehicle=Vehicle(setting) #avoid adapter not enable, with erack different
                        h_device.name=str(device_id)
                        h_device.setDaemon(True)
                        h_device.start()

                    tmp[device_id]=h_device #end
                #need clear ....
                for device_id, h_device in self.devices.items():
                    print("<<< stop: {} >>>".format(device_id))
                    h_device.thread_stop=True
                    
                self.devices=tmp

            print('=================')
            print(self.devices)
            print('=================')
