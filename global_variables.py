import collections
import json
import threading
import time
from datetime import datetime

import logging

import protocol.erack_data_normal as erack_normal
import protocol.erack_data_jcet as erack_jcet
import protocol.erack_data_sj as erack_sj
import protocol.erack_data_qualcomm as erack_qualcomm
import protocol.erack_date_ti as erack_ti
import protocol.erack_data_skyworksSG as erack_skyworksSG
import protocol.erack_data_skyworksMX as erack_skyworksMX
import protocol.erack_data_CHIPMOS as  erack_chipmos

#need config zone
#step 1:divide zone
#step 2:for diff zone create E82 insatnce
default_stock_out_port=''
api_spec='v3.0'
loadport_version=''
controller_id='tsc'

WhiteCarriersMask={}

WaterLevel={'waterLevelLow':30, 'waterLevelHigh':80}

# 9/19
RackPortFormat=[
    [r'E(\d+)P(\d+)',                               'E%dP%d',       r'E(\d+)',                              'E%.3d', ''], #1. ASECL, 
    [r'(GRA\d+)-(\d+)',                             '%s-%.3d',      r'(GRA\d+)',                            '%s',    r'(.+)-L(\d+)'], #2. GRA
    [r'(ER\d+)P(\d+)',                              '%sP%d',        r'(ER\d+)',                             '%s',    ''], #3. TFME JCAP
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    r'(.+)-LP(\d+)'], #4. SPIL CY 2021/10/20, not(\d+) for *
    [r'(.+ER)-(.+)',                                '%s-%.2d',      r'(.+ER)',                              '%s',    ''], #5. SPIL LG 2021/1020, not(\d+) for *
    [r'(EH.+)_SL(.+)',                              '%s_SL%.3d',    r'(EH.+)',                              '%s',    ''], #6. SPIL CP 2021/1020, not(\d+) for *
    [r'(T[ABC][DE].+)-(.+)',                        '%s-%.2d',      r'(T[ABC][DE].+)',                      '%s',    ''], #7. GPM
    [r'(.+ER\d\d)(\d+)',                            '%s%.2d',       r'(.+ER\d\d)',                          '%s',    ''], #8. FPC 1
    [r'([TN]ER.+)-(\d+)',                           '%s-%.2d',      r'([TN]ER.+)',                          '%s',    ''], #9. QUALCOMM
    [r'(EX.+)_SL(.+)',                              '%s_SL%.3d',    r'(EX.+)',                              '%s',    ''], #10. SPIL ZG
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    r'(.+)_LP(\d+)'], #11 JCET SCS
    [r'(ER\d+)P(\d+)',                              '%sP%d',        r'(ER\d+)',                             '%s',    r'(.+).(\d+)'], #12. HH 3rd factory
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    r'(.+)_(\d+)'], #13 UTAC USG1
    [r'(PS.+)_(.+)',                                '%s_%.2d',      r'(PS.+)',                              '%s',    r'(.+)_(\d+)'], #14 KYEC
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    r'(.+)_LP(\d+)'], #15 GB, GF
    [r'F(\d+)P(\d+)',                               'F%dP%d',       r'F(\d+)',                              'F%.3d', ''], #16 SJSEMI 2F
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #17 JCET eWLB
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #18 K25
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #19 UMC 8S
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #20 UMC SG
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #21 ASECL WB
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #22 ASECL OVEN
    [r'E(\d+)P(\d+)',                               'E%dP%d',       r'E(\d+)',                              'E%.3d', ''], #23 SJSEMI bumping 1F
    [r'(\d\dRT.+)L(\d)C(\d)R\d',                    '%s%s',         r'(\d\dRT.+)',                          '%s',    ''], #24 SKYWORKS SG
    [r'(((ET)|(DT)|(PH)|(TF))[LCR].+)-(.+)',        '%s-%.2d',      r'(((ET)|(DT)|(PH)|(TF))[LCR].+)-(.+)', '%s',    ''], #25 TI FAB
    [r'(((EP)|(CH)|(BA)|(ET)|(MP)|(AS)|(BI)|(CF)|(PH)|(IO)|(PB)|(EV)|(ME))[LU].+)-(.+)',    '%s-%.2d', 
                     r'(((EP)|(CH)|(BA)|(ET)|(MP)|(AS)|(BI)|(CF)|(PH)|(IO)|(PB)|(EV)|(ME))[LU].+)-(.+)',    '%s',    ''], #26 TI BUMP
    [r'([BS]R\d[A-Z][IO]\d\d\d)L(\d)C(\d)R\d',      '%s%s',         r'([BS]R\d[A-Z][IO]\d\d\d)',            '%s',    ''], #27 SKYWORKS JP
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #28 SPIL CROSSING
    [r'(P\d-.+-PD-E-\d)(\d\d)',                     '%s%.2d',       r'(P\d-.+-PD-E-\d)',                    '%s',    ''], #29 TPW
    [r'(.+E\d+)-(\d\d)',                            '%s-%.2d',      r'(.+E\d+)',                            '%s',    ''], #30 BOE
    [r'(FRG\d+)-(.+)',                              '%s-%.2d',      r'(FRG\d+)',                            '%s',    ''], #31. ASECL FRG
    [r'(((FW)|(CW)|(FO)|(PO))[P].+)-(.+)',          '%s-%.2d',      r'(((FW)|(CW)|(FO)|(PO))[P].+)-(.+)',   '%s',    ''], #32 TI AT
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #33. Renesas JP FT (OT NS)
    [r'D(\d+)P(\d+)',                               'D%dP%d',       r'D(\d+)',                              'D%.3d', ''], #34 SJSEMI bumping 3F
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    r'(.+)_(\d+)'], #35 UTAC USG3
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #36 K9
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #37 K11
    [r'(ER.+)_LP(.+)',                              '%s_LP%.2d',    r'(ER.+)',                              '%s',    ''], #38 K8
    [r'(ESZ.+)_SL(.+)',                             '%s_SL%.3d',    r'(ESZ.+)',                             '%s',    ''], #39 SPIL SH
    [r'BJ(\d+)RS(\d+)',                             'BJ%dRS%d',     r'BJ(\d+)',                             'BJ%.2d',''], #40 Renesas BJ
    [r'SZ(\d+)RS(\d+)',                             'SZ%dRS%d',     r'SZ(\d+)',                             'SZ%.2d',''], #41 Renesas SH FT
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #42 Renesas JP FCBGA
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #43 Mirle MCS
    [r'(ER\d+)P(\d+)',                              '%sP%d',        r'(ER\d+)',                             '%s',    r'(.+).(\d+)'], #44. HH 1st factory
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #45 Renesas JP WB
    [r'(EWB.+)-(.+)-(.+)',                          '%s-%.1d-%.1d', r'(EWB.+)',                             '%s',    ''], #46 TI  Baguio BUMP
    [r'(EBE.+)-(.+)-(.+)',                          '%s-%.1d-%.1d', r'(EBE.+)',                             '%s',    ''], #47 TI  Clark SWART
    [r'^(PR\d+_\d+R\d+)-P(\d+)$',                   '%s-P%.2d',     r'^(PR\d+_\d+R\d+)',                    '%s',    ''], #48 TI  Malacca
    [r'(BIA.+)-(.+)',                               '%s-%.2d',      r'(BIA.+)',                             '%s',    ''], #49 TI  Dallas
    [r'(SRK.+)-(.+)',                               '%s-%.2d',      r'(SRK.+)',                             '%s',    ''], #50 TI  Aizu
    [r'(ER\d\d\d)(\d\d)',                           '%s%.2d',       r'(ER\d\d\d)',                          '%s',    ''], #51 TI  Miho
    [r'(.+-FTFT-.{3})(\w)',                         '%s%s',         r'(.+-FTFT-.+)',                        '%s',    ''], #52 KYEC FT
    [r'(SER.+)-(.+)-(.+)',                          '%s-%s',        r'(SER.+)',                             '%s',    ''], #53 Kumamoto TPB
    [r'B(\d+)P(\d+)',                               'B%dP%d',       r'B(\d+)',                              'B%.3d', ''], #54 SJSEMI J2B
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #55 Intel chris
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #56 Intel tim
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #57 Malta
    [r'(ER-.+)-(.+)',                               '%s-%.2d',      r'(ER.+)',                              '%s',    ''], #58. Renesas JP FT YZ
    [r'(ER\d+)P(\d+)',                              '%sP%d',        r'(ER\d+)',                             '%s',    ''], #59. SKYWORKSMX
    [r'(EX.+)_SL(.+)',                              '%s_SL%.3d',    r'(EX.+)',                              '%s',    ''], #60. Amkor
    [r'(.+-LSLS-.{3})(\w)',                         '%s%s',         r'(.+-LSLS-.+)',                        '%s',    ''], #61 KYEC F2L1_FT
]

Format_RackPort_Parse=r'E(\d+)P(\d+)'
Format_RackPort_Print='E%dP%d'
Format_Rack_Parse=r'E(\d+)'
Format_Rack_Print='E%.3d'

PSProtocol=1
HostProtocol=1
RackNaming=1
RouteAlgo='A*'

controller_id='tsc'
max_size=100000
OtherZoneSetting= {}

logger=logging.getLogger("tsc")

zmq_h=0 #chocp 2024/8/12

import traceback
import queue


'''
OutputLock=threading.Lock()
WaitLock=threading.Lock()
SeqCountLock=threading.Lock()
SeqCount=0
Pool=[]

class Display(threading.Thread):
    __instance=None
    @staticmethod
    def getInstance():
        if Display.__instance == None:
            Display()
        return Display.__instance

    def __init__(self):
        Display.__instance=self
        self.api_queue=queue.Queue(maxsize=max_size) #not good, dequeue better
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.start()
    #for thread
    def run(self):
        while(True):
            try:
                if SocketIO.connected:
                    [event, obj, sync]=self.api_queue.get() #if none, will hold
                    if zmq_h:
                        zmq_h.send_json((event, obj, SeqCount))

                    if sync:
                        sync_output(event, obj, timeout=5.0)
                    else:
                        async_output(event, obj)
                        #sync_output(event, obj, timeout=5.0)
                time.sleep(0.01) # An average of 100 events per second.

            except:
                traceback.print_exc()
                pass

def output(event, obj, sync=False):
    h=Display.getInstance()
    try:
        if h.api_queue.full():
            [event_1, obj_1, sync_1]=h.api_queue.get()
            logger.info('socketIO queue is full: {} and event {} being discarded {}'.format(h.api_queue.qsize(),event_1,sync_1))
        h.api_queue.put([event, obj, sync])
    except:
        logger.error('Queue have exception {}'.format(traceback.format_exc()))



def async_output(event, obj):
    global SeqCount
    global SeqCountLock

    SeqCountLock.acquire()
    SeqCount=(SeqCount+1)%10000
    obj['seq']=datetime.now().strftime('%Y%m%d%H%M%S')+'{:04d}'.format(SeqCount)
    obj['ControllerID']=controller_id
    SeqCountLock.release()

    #if SocketIO.connected:
    SocketIO.h.emit(event, obj, namespace='/{}'.format(controller_id))
    #SocketIO.h.emit(event, obj, namespace='/{}'.format(global_variables.controller_id), callback=response)

def response(*args):
    try:
        if args[1] in Pool:
            Pool.remove(args[1])
    except:
        print('args', args)#?????


#def sync_output(event, obj):
def sync_output(event, obj, timeout=1.0):
    global SeqCount
    global SeqCountLock
    global OutputLock
    global WaitLock

    OutputLock.acquire()

    SeqCountLock.acquire()
    SeqCount=(SeqCount+1)%10000
    obj['seq']=datetime.now().strftime('%Y%m%d%H%M%S')+'{:04d}'.format(SeqCount)
    obj['timestamp']=time.time()
    obj['ControllerID']=controller_id
    SeqCountLock.release()

    Pool.append(obj['seq'])

    begin_time=0
    retry=0
    #print('debug msg: ', event, obj)
    while True:
        #print('<<obj>>', obj, '<<SocketIO.connected>>:', SocketIO.connected)
        if obj['seq'] in Pool: #need rewrite???????
            if time.time()-begin_time>timeout: #should 1 sec
                if retry:
                    #logger=logging.getLogger("tsc")
                    logger.info('socketIO retry:{}, {}, retry:{}'.format(obj['seq'], event, retry))

                begin_time=time.time()
                if not SocketIO.connected:
                    if not retry:
                        retry+=1
                    time.sleep(2)
                    continue
                try:
                    SocketIO.h.emit(event, obj, namespace='/{}'.format(controller_id), callback=response)
                    print('<<namespace>>: ', "namespace='/{}'".format(controller_id))
                    #SocketIO.h.emit(event, obj, namespace='/{}'.format(global_variables.controller_id))
                except: # ex: /tsc is not a connected namespace
                    traceback.print_exc()
                    time.sleep(2)
                    pass

                retry=retry+1
                continue

            time.sleep(0.1)
        else:
            break

    OutputLock.release()

'''

def score_func(start_vertex, end_vertex):
    """ return the h score with start_vertex and end_vertex """
    return 0



class SocketIO():
    h=0
    connected=False


class Route():
    h=0

class Vehicle():
    h=0

class Equipment():
    h=0

class Iot(): # Mike: 2022/07/01
    h=0

class Erack():
    h=0


view_to_tsc_queue=collections.deque() #('update', 'tsc_setting', index)
tsc_to_view=collections.deque()
remotecmd_queue=collections.deque()


VehicleSettings=[]
eRackSettings=[]
EqSettings=[]
WSSettings=[] #Jwo: 2023/02/24 for SPIL LG SampleDestSector
IotSettings=[] # Mike: 2022/07/01

tsc_map={}

color_sectors={}
SectorSettings={} # Mike: 2022/06/13

class PoseTable():
    mapping={}
#ports_table={}

class PortsTable():
    mapping={}
    reverse_mapping={}

class EdgesTable():
    mapping={}

class PortBufferPriorityTable():
    mapping={}

global_vehicles_location={} # Mike: 2021/02/18
global_vehicles_location_index={} # Mike: 2021/04/06
global_occupied_station={} # Mike: 2021/02/18
global_occupied_lock=threading.Lock() # Mike: 2021/02/18
global_moveout_request={} # Mike: 2021/08/09
global_plan_route={} # Mike: 2021/11/12
global_junction_neighbor={} # Mike: 2021/08/09
global_disable_nodes=[] # Mike: 2021/04/15
global_disable_edges=[] # Mike: 2021/04/15
global_group_to_node={} # Mike: 2021/12/08
global_map_mapping={} # Mike: 2022/08/24
global_elevator_entrance=[] # Mike: 2023/12/02
global_route_mapping={} # Mike: 2023/12/04
global_generate_routes=True #2024/03/08
global_auto_group=False
global_vehicles_priority={}
global_port_transfer_table_mem=[]
global_crossZoneLink={}
global_nearDistance=150

global_cassetteType=['A12', 'B12', 'C08', 'D08', 'C12', '12S', '8S', '08S', 'MC', 'FOUP', 'FOSB']

global_erack_item={
    'NORMAL':erack_normal,
    'SJ':erack_sj,
    'JCET':erack_jcet,
    'QUALCOMM':erack_qualcomm,
    'TI':erack_ti,
    'SKYWORKSSG':erack_skyworksSG,
    'SKYWORKSMX':erack_skyworksMX,
    'CHIPMOS':erack_chipmos
}


TBS01_is_find=False
TBS02_is_find=False
TBS03_is_find=False
TBS04_is_find=False
cs_find_by={
    "TBS01":"",
    "TBS02":"",
    "TBS03":"",
    "TBS04":"",
}

class SaveStockerInDestPortByVehicleId():#kelvin
    save_dest_port={
        "AGV01":"",
        "AGV02":"",
        "AGV03":"",
        "AGV04":""

    }

#socketIO flow control 2024/1022
from bridge.sender import MessageController
Display=MessageController
output=MessageController.output

k11_ng_fault_port={#peter 240807
    "AMR01":'',
    "AMR02":'',
    "AMR03":'',
    "AMR04":'',
}
odd_buflist=["BUF{:02d}".format(buf) for buf in range(1, 13, 2)]
even_buflist=["BUF{:02d}".format(buf) for buf in range(2, 13, 2)]
K11_armsort=odd_buflist+even_buflist
k11_DoorStateM=[
    ['open_door','','OPEN','OPENED'],
    ['close_door','OPENED','CLOSE','CLOSED'],
    ['pass_door','','OPEN','OPENED'],
    ['pass_door','OPENED','CLOSE','CLOSED'],
    ['pass_door','AIRSHOWED','CLOSE','CLOSED'],
    ['air_show','OPENED','AIRSHOW','AIRSHOWED']]


class SaveK11_AMR_STATUS():#kelvinng 20250305
    K11_AMR_STATUS={

    }

class M1_global_variables():
    vsc_point = ["MGZ_ERACK_01", "CST_Erack_left"]

   

    need_do_more_times_arm_EQ={
        "EQ_3670_P01_LEFT":3670,
        "EQ_3670_P01_RIGHT":3670,
        "EQ_3670_P01":3670,
        "MGZ_3670_P01":3670,
        "EQ_3670_P01_LP1":3670,
        "EQ_3670_P01_LP2":3670
        
        
    }

    oven_door={
        "DOOR_4110":"",
        "DOOR_4305":""
    }

    MAG_TYPE=["1","2","3","4","5"]

    Development_Environment=True

    re_pattern_of_eq_3910=r'^EQ_3910_P(\d+)_LP1$'
    re_pattern_of_LP=r'_LP\d+$'

