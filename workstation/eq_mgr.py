import os
import global_variables
from global_variables import output
from workstation.dummyport import DummyPort
from workstation.dummyportSTK import DummyPortSTKE88, DummyPortSTKE82
from workstation.dummyport_for_asecl_ab2 import DummyPortAB
from workstation.dummyport_for_hh import DummyPortHuahong
from workstation.dummyport_for_jcet import DummyPortJcet
from workstation.dummyport_for_utac import DummyPortUtac
from workstation.dummyport_for_asecl import DummyPortAsecl
from workstation.dummyport_for_umc import DummyPortUMC
from workstation.dummyport_for_umc_stocker import DummyPortUMCStocker

from workstation.order_mgr import OrderMgr

import time
import threading
import traceback
from semi.SecsHostMgr import E82_Host
from semi.SecsHostMgr import E88_STK_Host
import tools

import queue
import logging.handlers as log_handler
import logging
import alarms

class EqView():
    __instance=None

    @staticmethod
    def getInstance():
        #print('call MCS_VIEW getInstance')
        if EqView.__instance == None:
            EqView()
        return EqView.__instance

    def __init__(self):
        self.logger=logging.getLogger("EqView")
        self.logger.setLevel(logging.DEBUG)
        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_EqView.log"), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s")) 
        self.logger.addHandler(fileHandler)

        EqView.__instance=self

    def on_notify(self, obj, event):
        #chocp 2021/10/23 cancel loadport report alarm
        #should change 'portID' => 'workstationID'
        info={
        'portID':obj.workstationID,
        'enable':obj.enable,
        'state':obj.state,
        'carrierID':obj.carrierID,
        'from':obj.carrier_source,
        'alarm':obj.alarm,
        'msg':obj.msg,
        'equipmentState':getattr(obj, 'equipmentState', 'PM')
        }
        if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes' or\
        global_variables.TSCSettings.get('Other', {}).get('EAPConnect') == 'yes': #2023/11/3 fix
            output('MCSLoadportView', info)
            #print('MCSLoadportView=>', info)

            self.logger.debug('<<<MCSLoadportView>>>: info: {}'.format(info))


class EqMgr(threading.Thread):
    __instance=None

    @staticmethod
    def getInstance():
        if EqMgr.__instance == None:
            EqMgr()
        return EqMgr.__instance

    def add_listener(self, obj):
        for workstationID, h in self.workstations.items():
            h.add_listener(obj)

    def trigger(self, portID, event, data={}): #chocp 8/24
        print('->call trigger: ', portID, event, data)
        h=self.workstations.get(portID)
        self.logger.debug('->call trigger: {}, {}, {}, {}'.format(portID, event, data, getattr(h, 'enable') if h else 'h=None'))
        if h and getattr(h, 'enable', True):
            h.change_state(event, data)
            #self.logger.debug('workstation_change_state: portID:{}, event:{}, data:{}'.format(portID, event, data))
            #use queue
    def __init__(self):
        self.logger=logging.getLogger("EqMgr")
        self.logger.setLevel(logging.DEBUG)
        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_EqMgr.log"), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s"))
        self.logger.addHandler(fileHandler)
        self.tsclogger=logging.getLogger("tsc")


        self.api_queue=queue.Queue()
        self.workstations={}
        self.equipments={} #for K25
        self.orderMgr=OrderMgr(self)

        EqMgr.__instance=self
        threading.Thread.__init__(self)

    #for thread
    def run(self):
        
        while(True):
            try:
                obj=self.api_queue.get() #if none, will hold
                if obj['cmd'] == 'start' or obj['cmd'] == 'restart':
                    self.tsclogger.info('{} '.format('<<< get EQSettings >>>'))
                    tmp_workstations={}
                    tmp_equipments={}
                    #print('********************************************')
                    #print(obj['config'])
                    #print('********************************************')
                    for idx, setting in enumerate(obj['config']):
                        setting['logger']=self.logger
                        workstation_id=setting.get('portID', '')
                        equipment_id=setting.get('equipmentID', '')
                        if not workstation_id or not equipment_id: #if ID not null continue
                            print("<<< {} ignore: {} {}>>>".format(idx, workstation_id, equipment_id))
                            continue

                        try:
                            h_workstation=self.workstations.pop(workstation_id)
                        except:
                            h_workstation=0

                        if h_workstation: #if have created h_workstation before
                            if setting['enable']:
                                if not h_workstation.is_alive(): #if h_workstation thread start, so need start
                                    if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes' or\
                                    global_variables.TSCSettings.get('Other', {}).get('EAPConnect') == 'yes': #2023/11/3 fix
                                        #h_workstation.setDaemon(True)
                                        h_workstation.start()
                                        print("<<< start: {} >>>".format(workstation_id))

                                h_workstation.update_params(setting)
                                tmp_workstations[workstation_id]=h_workstation #end
                                if tmp_equipments.get(equipment_id):
                                    tmp_equipments[equipment_id].append(h_workstation)
                                else:
                                    tmp_equipments[equipment_id]=[h_workstation]

                                continue
                            else:
                                if not h_workstation.is_alive(): #if h_workstation thread not start, so keep not start
                                    #print("<<< continue: {} >>>".format(workstation_id))
                                    h_workstation.update_params(setting)
                                    tmp_workstations[workstation_id]=h_workstation #end
                                    if tmp_equipments.get(equipment_id):
                                        tmp_equipments[equipment_id].append(h_workstation)
                                    else:
                                        tmp_equipments[equipment_id]=[h_workstation]

                                    continue
                                #if h_workstation thread start before , need close
                                print("<<< stop: {} >>>".format(workstation_id))
                                h_workstation.thread_stop=True
                        #else:
                        #    print('h_workstation not found', workstation_id)

                        secsgem_e82_h=E82_Host.getInstance(setting['zoneID'])
                        secsgem_e88_h=E88_STK_Host.getInstance(setting['zoneID'])

                        if setting['type'] == 'StockPort' and 'v4' in global_variables.api_spec:
                            h_workstation=DummyPortSTKE88(self.orderMgr, secsgem_e88_h, setting)
                            tmp_workstations[workstation_id]=h_workstation
                        elif setting['type'] == 'LifterPort':
                            h_workstation=DummyPortSTKE82(self.orderMgr, secsgem_e82_h, setting)
                            tmp_workstations[workstation_id]=h_workstation
                        elif global_variables.loadport_version == "ASECL":
                            h_workstation=DummyPortAsecl(self.orderMgr, secsgem_e82_h, setting)
                            tmp_workstations[workstation_id]=h_workstation
                        elif global_variables.loadport_version == "JCET":
                            h_workstation=DummyPortJcet(self.orderMgr, secsgem_e82_h, setting)
                            tmp_workstations[workstation_id]=h_workstation

                        elif  global_variables.loadport_version == "HH":
                            h_workstation=DummyPortHuahong(self.orderMgr, secsgem_e82_h, setting)
                            tmp_workstations[workstation_id]=h_workstation

                        elif  global_variables.loadport_version == "UTAC":
                            h_workstation=DummyPortUtac(self.orderMgr, secsgem_e82_h, setting)
                            tmp_workstations[workstation_id]=h_workstation
                        elif global_variables.loadport_version == "UMC":
                            if 'Stock' in setting.get('type'):
                                h_workstation=DummyPortUMCStocker(self.orderMgr, secsgem_e82_h, setting) #chocp 2024/03/25
                                if setting.get('type') == 'StockOut':
                                    global_variables.default_stock_out_port=workstation_id #chocp 2024/03/25
                            else:
                                h_workstation=DummyPortUMC(self.orderMgr, secsgem_e82_h, setting)

                            tmp_workstations[workstation_id]=h_workstation
                        else:
                            if setting['type'] == 'A&B' and global_variables.loadport_version == "ASECL": #fix
                                #h_workstation=DummyPortAB(secsgem_e82_h, setting)
                                h_workstation=DummyPortAB(self.orderMgr, secsgem_e82_h, setting)
                                tmp_workstations[workstation_id]=h_workstation
                                #tmp_workstations[workstation_id+'A']=h_workstation
                                #tmp_workstations[workstation_id+'B']=h_workstation
                            else:
                                h_workstation=DummyPort(self.orderMgr, secsgem_e82_h, setting)
                                tmp_workstations[workstation_id]=h_workstation

                        tmp_workstations[workstation_id]=h_workstation #end
                        if tmp_equipments.get(equipment_id):
                            tmp_equipments[equipment_id].append(h_workstation)
                        else:
                            tmp_equipments[equipment_id]=[h_workstation]

                        h_workstation.add_listener(EqView.getInstance())

                        if setting['enable']:
                            if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes' or\
                                    global_variables.TSCSettings.get('Other', {}).get('EAPConnect') == 'yes':
                                print("<<< new: {} >>>".format(workstation_id))
                                h_workstation.name=str(equipment_id)
                                h_workstation.setDaemon(True)
                                h_workstation.start()

                    #residual thread need clear ....
                    for workstation_id, h_workstation in self.workstations.items():
                        print("<<< stop: {} >>>".format(workstation_id))
                        h_workstation.thread_stop=True
                        
                    self.workstations=tmp_workstations
                    self.equipments=tmp_equipments

            except:
                self.tsclogger.error('{} {} '.format('EQ mgr error', traceback.format_exc()))












