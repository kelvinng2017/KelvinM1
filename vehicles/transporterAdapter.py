import collections
import sys
import traceback
import threading
from threading import Timer
import time
import socket
from global_variables import output

import tools
import re
import alarms

# Mike: 2021/02/18
import global_variables
from global_variables import PoseTable
from global_variables import PortsTable
from global_variables import Route
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host
from global_variables import global_junction_neighbor # Mike: 2021/08/09
from global_variables import global_moveout_request # Mike: 2021/08/09carriers
from global_variables import global_plan_route # Mike: 2021/08/09
from global_variables import global_elevator_entrance
from global_variables import global_map_mapping
from global_variables import global_route_mapping
import math
import random # Mike: 2021/04/12
import os
import logging
import logging.handlers as log_handler
from algorithm.vehicleRoutePlanner import RoutePlanner as Planner

def version_check(source, requirement): # Mike: 2021/06/18
    s=source.split('.')
    r=requirement.split('.')
    # print(source, requirement)
    if int(s[0]) < int(r[0]):
        return False
    if int(s[0]) == int(r[0]) and int(s[1]) < int(r[1]):
        return False
    return True

class mWarning(Exception):
    def __init__(self, code, txt):
        self.code=code
        self.txt=txt
        pass


class Adapter(threading.Thread):

    def __init__(self, secsgem_e88_h, vehicle_instance, id, ip, port, max_speed=500, retry_count_limit=20):
        self.nak_list=collections.deque(maxlen=10) # Mike: 2021/09/07
        self.non_blocking_mode=True # Mike: 2021/09/22
        self.msg_retry=False # Mike: 2021/09/22
        self.msg_retry_cnt_limit=3 # Mike: 2021/09/22

        soft_ver='' # Mike: 2021/11/12
        try:
            f=open('version.txt','r')
            soft_ver=f.readline()
            f.close()
        except:
            pass


        self.vehicle_instance=vehicle_instance

        # Mike: 2021/05/27
        self.soft_ver=soft_ver
        self.spec_ver="2.6"
        # Mike: 2021/06/15
        self.mr_soft_ver="None"
        self.mr_spec_ver="1.0"

        # Mike: 2021/03/05
        ### param ###
        self.enable_traffic_point=True
        self.get_right_timeout=180
        self.enable_find_way=True
        self.find_way_time=3
        self.max_find_way_cost=60000
        self.dynamic_release_right=True
        self.release_right_base_on_location=True

        self.id=id
        self.ip=ip
        self.port=port
        self.max_speed=max_speed

        self.is_moving=False # Mike: 2021/08/02

        self.last_point=''
        self.last_alarm_point=''

        # self.get_right_th=None
        self.segment_end={}

        self.retry_count_limit=retry_count_limit

        self.online={
            'status':'Error', #'Error' communication error, 'Idle': get vehicle position
            'connected':False,
            'sync':False,
            'man_mode':True,
            'last_recive':0,
            }

        self.move={
            'status':'Error',
            'arrival':'EndArrival',
            'pose':{'x':0, 'y':0, 'z':0, 'h':0},
            'velocity':{'w':0, 'speed':0},
            'at_point':'', # Mike: 2021/03/03
            'obstacles':False, #chi 2022/05/04
            'into_obstacles':0
            }
        self.move['pose']['z']=vehicle_instance.defaultFloor

        self.robot={
            'command':'', # Mike: 2021/05/27
            'status':'Error',
            'finished':False,
            'at_home':False
            }

        self.battery={
            'charge':False,
            'exchange':False,
            'error':False,
            'percentage':100,
            'voltage':30.0,
            'temperature':16,
            'SOH':0, # Mike: 2021/05/11
            'current':0 #chi 2023/02/09
            }

        self.carriers=[
            {'status':'None', 'port':'OutOfService'}, #chocp:2021/3/10 set default to None
            {'status':'None', 'port':'OutOfService'} #'Fail', 'None', 'CarrierID'
            ] #chocp new for >8 slot, 2022/8/20
        '''
            {'status':'Fail'},
            {'status':'PSD2013'}
        '''

        self.alarm={
            'reset':False,
            'error_code':'',
            'error_txt':''
            }

        self.route_status={
            'current':global_variables.global_map_mapping.get(vehicle_instance.defaultFloor, ''),
            'exchange':'None'
            }

        self.cmd_queue=collections.deque(maxlen=40)
        self.cmd_ack_queue={} # Mike: 2021/03/26
        self.sock=0
        self.systemId=0

        # Mike: 2021/02/18
        self.occupied_route=[]
        self.last_group_point={} # Mike: 2022/01/19
        self.cmd_sending=False # Mike: 2021/03/11
        self.cmd_path=[] # Mike: 2021/03/04

        # Mike: 2021/02/22
        self.find_way=True
        self.find_way_cnt=0 # Mike: 2021/04/08
        self.is_update_location=False # Mike:2021/03/17
        self.robot_get_lock=False

        self.move_cmd_reject=False # Mike: 2021/04/09
        self.move_cmd_nak=False # Mike: 2024/01/15

        self.buf_idx_estimate=0
        self.buf_status_estimate='Unknown' #chocp:2021/4/1

        self.logger=logging.getLogger(self.id) # Mike: 2021/05/17
        for h in self.logger.handlers[:]: # Mike: 2021/09/22
            self.logger.removeHandler(h)
            h.close()
        self.logger.setLevel(logging.DEBUG)

        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_{}.log".format(self.id)), when='midnight', interval=1, backupCount=30)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(fileHandler)

        # For console. Mike: 2021/07/16
        streamHandler=logging.StreamHandler()
        streamHandler.setLevel(logging.INFO)
        streamHandler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
        self.logger.addHandler(streamHandler)

        self.relay_on=False #chocp:2021/4/14
        self.stop=False

        self.systemID_mem={}
        self.systemID_gen_lock=threading.Lock()
        self.robot_cmd_id=0

        self.move_control_lock=threading.Lock()

        self.wait_alarm_th=None
        self.alarm_list={'TM':[], 'TS':[], 'EC':[], 'BS':[], 'CB':[], 'RM':[], 'TB':[], 'IM':[], 'TS9':[], 'other':[]}

        global_moveout_request[self.id]='' # Mike: 2021/08/13
        global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12

        self.planner=Planner(self)

        self.heart_beat=0
        threading.Thread.__init__(self)

    def alarm_reset(self): #new 2021/2/22
        self.alarm['reset']=False
        self.alarm['error_code']=''
        self.alarm['error_txt']=''
        # Mike: 2021/03/25
        # self.planner.update_location(True)
        self.planner.current_route.clear() # Mike: 2023/05/31
        self.planner.current_go_list.clear() # Mike: 2023/05/31
        self.planner.clean_right(False)
        self.reset_all_alarm()
        #can send reset cmd to MR

####################################################
    ''' Message receiver '''
    def msg_decode(self, msg, systemId):
        #self.logger.info('{}'.format(msg))
        self.online['last_recive']=time.time()

        try:
            head=msg[0:3]
            data=msg[2:] # set msg[3]=data[1]

            # Mike: 2021/05/27
            if head in self.systemID_mem:
                if systemId == self.systemID_mem[head]:
                    return ''
            self.systemID_mem[head]=systemId

            ###################
            #                 #
            #   spec report   #
            #                 #
            ###################

            # Mike: 2021/05/27
            if (head == 'P17'):    # Spec Request
                return 'Sw{:<13}Sp{}'.format(self.soft_ver[:13], self.spec_ver)

            # Mike: 2021/06/15
            elif (head == 'S18'):    # Spec cmd response
                Sw_index=data.find('Sw')
                Sp_index=data.rfind('Sp')
                self.mr_soft_ver=data[Sw_index+2:Sp_index].rstrip(' ')
                self.mr_spec_ver=data[Sp_index+2:]
                if self.mr_spec_ver[0].lower() == 'v':
                    self.mr_spec_ver=self.mr_spec_ver[1:]
                self.logger.info('{} {} {} {}'.format('[{}] '.format(self.id), 'MR spec:', self.mr_soft_ver,  self.mr_spec_ver))

            #####################
            #                   #
            #   auto / manual   #
            #                   #
            #####################

            elif (head == "P11"): # Auto request
                self.online['man_mode']=False
                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'Get auto mode:'))
                self.new_data=False # Mike: 2021/03/28
                self.last_alarm_point=''
                th=threading.Thread(target=self.planner.update_location, args=(True,))
                th.setDaemon(True)
                th.start()
                self.all_status_query()

            elif (head == "P13"): # Man request
                self.online['man_mode']=True
                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'Get man mode:'))
                self.planner.current_route.clear() # Mike: 2021/03/17
                self.planner.current_go_list.clear() # Mike: 2021/03/17
                th=threading.Thread(target=self.planner.clean_right,)
                th.setDaemon(True)
                th.start()

            ##############
            #            #
            #   moving   #
            #            #
            ##############

            elif (head == 'P21'):    # Move Status Report
                if data[1] == '0':
                    self.move['status']='Idle'
                elif data[1] == '1':
                    self.move['status']='Working'
                elif data[1] == '2':
                    self.move['status']='Pausing'
                elif data[1] == '3':
                    self.move['status']='Pause'
                elif data[1] == '4':
                    self.move['status']='Stopping'
                elif data[1] == '5':
                    self.move['status']='Block'
                else:
                    self.move['status']='Error'

                self.move['pose']['h']=int(data[2:5])
                #self.logger.info('{} {} {}'.format('move:', self.move['status'], self.move['pose']['h']))

            elif (head == "P43"):    # Move Append Arrival Report #????
                if data[1] == '1':
                    self.move['arrival']='Arrival'
                    output('VehiclePointUpdate',{
                            'Point':self.last_point,
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState}) #chocp
 
                elif data[1] == '2':
                    self.move['arrival']='EndArrival'
                else:
                    self.move['arrival']='Fail'
                    self.move['status']='Error'

                s=1 if data[2] == 'P' else -1
                self.move['pose']['x']=int(data[3:11])*s

                s=1 if data[11] == 'P' else -1
                self.move['pose']['y']=int(data[12:20])*s

                self.move['pose']['h']=int(data[20:23])
                self.move['velocity']['w']=int(data[23:26])
                self.move['velocity']['speed']=int(data[26:30])
                self.move['at_point']=data[30:] if data[30:] else tools.round_a_point_new([self.move['pose']['x'], self.move['pose']['y'], self.move['pose']['z'], self.move['pose']['h']])[0] #chocp 2021/3/4 # Mike: 2021/09/28
                self.last_point=self.move['at_point'] # Mike: 2021/09/30
                self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'Arrival point: ', self.move['at_point'], self.move['arrival'])) # Mike: 2020/02/18
                self.new_data=True # Mike: 2020/02/18

                '''output('VehiclePoseUpdate',{ #'VehiclePointUpdate'
                        'VehicleID':self.id,
                        'VehicleState':self.vehicle_instance.AgvState,
                        #'VehicleState':'Enroute',
                        'Pose':[self.move['pose']['x'], self.move['pose']['y'],  self.move['pose']['h'], self.move['pose']['z']],
                        'Battery':self.battery['percentage'],
                        'Charge':self.battery['charge'],
                        'Connected':self.online['connected'], # Mike: 2022/05/31
                        'Health':self.battery['SOH'],
                        'MoveStatus':self.move['status'],
                        'RobotStatus':self.robot['status'],
                        'RobotAtHome':self.robot['at_home']})''' #2024/1/3 chocp

                # Mike: 2021/03/04
                if data[1] == '1':
                    if len(self.cmd_path): #chocp : 2021/3/18 for manual move
                        if self.move['at_point'] == self.cmd_path[-1] and not self.cmd_sending: # Mike: 2021/03/11
                            # Mike: 2021/02/22
                            # self.planner.update_location(False)
                            self.planner.is_moving=False
                        if self.dynamic_release_right or self.move['at_point'] == self.cmd_path[-1]: # Mike: 2020/03/05
                            self.planner.clean_path(self.move['at_point'])
                    else:
                        th=threading.Thread(target=self.planner.update_location, args=(False,))
                        th.setDaemon(True)
                        th.start()
                        self.new_data=True # Mike: 2020/02/18

                elif data[1] == '2':
                    self.planner.update_location(False)
                    self.planner.clean_path(self.move['at_point'])
                    self.is_moving=False
                else:
                    # Mike: 2021/02/22
                    self.planner.update_location(False)
                    th=threading.Thread(target=self.planner.clean_right,)
                    th.setDaemon(True)
                    th.start()
                    self.is_moving=False

            elif (head == 'P65'):  #chi 22/05/04  check obstacles when Enroute
                if self.vehicle_instance.AgvState =='Enroute' and data[1] == '1':
                    self.move['obstacles']=True
                    self.move['into_obstacles']=time.time()
                    self.logger.warning('{} {} '.format('=>P65', 'MR move with route obstacles'))
                    if self.occupied_route:
                        # self.new_data=True
                        # self.planner.update_location(True)
                        if self.last_point == self.occupied_route[0] and len(self.occupied_route)>1:
                            self.last_alarm_point=self.occupied_route[1]
                        else:
                            self.last_alarm_point=self.occupied_route[0]
                elif data[1] == '0':
                    self.move['obstacles']= False
                    self.last_alarm_point=''

            elif (head == "S34"): # Position response

                if data[1] == '0':
                    self.move['status']='Idle'
                elif data[1] == '1':
                    self.move['status']='Working'
                elif data[1] == '2':
                    self.move['status']='Pausing'
                elif data[1] == '3':
                    self.move['status']='Pause'
                elif data[1] == '4':
                    self.move['status']='Stopping'
                elif data[1] == '5':
                    self.move['status']='Block'
                else:
                    self.move['status']='Error'

                s=1 if data[2] == 'P' else -1
                self.move['pose']['x']=int(data[3:11])*s

                s=1 if data[11] == 'P' else -1
                self.move['pose']['y']=int(data[12:20])*s

                self.move['pose']['h']=int(data[20:23])
                self.move['velocity']['w']=int(data[23:26])
                self.move['velocity']['speed']=int(data[26:30])
                self.new_data=True # Mike: 2020/03/04
                #self.logger.info('{} {}'.format('move:', self.move['status']))

                if self.dynamic_release_right: # Mike: 2020/03/05
                    if self.planner.current_route or self.occupied_route: # Mike: 2020/03/04
                        self.planner.clean_path()

                #self.logger.info(''.format('position:', self.move['pose']['x'],\
                #                   self.move['pose']['y'],\
                #                   self.move['pose']['h'])
                #self.logger.info(''.format('velocity',  self.move['velocity']['w'],\
                #                   self.move['velocity']['speed'])
                '''output('VehiclePoseUpdate',{ #'VehiclePointUpdate'
                        'VehicleID':self.id,
                        'VehicleState':self.vehicle_instance.AgvState,
                        #'VehicleState':'Enroute',
                        'Pose':[self.move['pose']['x'], self.move['pose']['y'],  self.move['pose']['h'], self.move['pose']['z']],
                        'Battery':self.battery['percentage'],
                        'Charge':self.battery['charge'],
                        'Connected':self.online['connected'], # Mike: 2022/05/31
                        'Health':self.battery['SOH'],
                        'MoveStatus':self.move['status'],
                        'RobotStatus':self.robot['status'],
                        'RobotAtHome':self.robot['at_home']})''' #2024/1/3 chocp

                self.online['status']='Ready'

            elif (head == "S42"): # Vehicle move cmd response
                res='Reject' if data[1] == '0' else 'Ok'

                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), systemId, res))
                if res == 'Reject':
                    self.move_cmd_reject=True

            elif (head == "S52"): # Vehicle stop cmd response
                res='Reject' if data[1] == '0' else 'Ok'

                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), systemId, res))
                if res == 'Reject':
                    self.wait_stop=False

            #############
            #           #
            #   robot   #
            #           #
            #############

            elif (head == 'P23'):    # Robot Status Report
                if data[1] == '0':
                    self.robot['status']='Idle'
                elif data[1] == '1':
                    self.robot['status']='Busy'
                else:
                    self.robot['status']='Error'

                if data[2] == '1':
                    self.robot['at_home']=True
                else:
                    self.robot['at_home']=False

                #self.logger.info('{} {} {}'.format('robot:', self.robot['status'], self.robot['at_home']))

            elif (head == 'P25'):    # Cassette Status Report
                slot=int(data[1]) #1,2,3,4
                if data[2] == '1':
                    self.carriers[slot-1]['port']='OutOfService'
                elif data[2] == '2':
                    self.carriers[slot-1]['port']='InService'
                elif data[2] == '3':
                    self.carriers[slot-1]['port']='TransferBlocked'
                elif data[2] == '4':
                    self.carriers[slot-1]['port']='ReadyToLoad'
                elif data[2] == '5':
                    self.carriers[slot-1]['port']='ReadyToUnload'
                else:
                    self.carriers[slot-1]['port']='None'

                if 'Fail' in data[3:]: # Mike: 2022/02/23
                    self.carriers[slot-1]['status']='ReadFail'
                else:
                    self.carriers[slot-1]['status']=data[3:].lstrip(' ')

                # if not self.carriers[slot-1]['status'] and self.carriers[slot-1]['port'] == 'ReadyToLoad':
                if not self.carriers[slot-1]['status']:
                    if data[2] == '5':
                        self.carriers[slot-1]['status']='ReadFail'
                    else:
                        self.carriers[slot-1]['status']='None'

                self.logger.info('{} {} {} {} {} {}'.format('[{}] '.format(self.id), 'cassete ', slot,' status change:',  self.carriers[slot-1]['port'], data[3:]))
                pass

            elif (head == "S28"): # Cassette ID Change Report
                self.logger.debug('{} {}'.format('[{}] '.format(self.id), systemId))

            elif (head == "S46"): # Robot cmd response # Mike: 2023/07/31
                res='Ok' if data[1] == '0' else 'Reject'
                self.logger.debug('{} {:04d} {} {}'.format('[{}] '.format(self.id), systemId, data[2:6], res))
                if res == 'Reject' and self.robot['command'] == data[2:6]:
                    self.robot['finished']='InterlockError'

            elif (head == 'P53'):    # Robot Finished Report, format???
                # if not version_check(self.mr_spec_ver, '1.0') or data[16:20] == self.robot['command']: # Mike: 2021/05/27
                if data[1] == 'F':
                    self.robot['finished']='Finished'
                    #chocp:2012/4/1, only for test, very dangerous
                    if global_variables.TSCSettings.get('Safety',{}).get('BufferNoRFIDCheck', 'no') == 'yes':
                        self.carriers[self.buf_idx_estimate]['status']=self.buf_status_estimate

                elif data[1] == 'I':
                    self.robot['finished']='InterlockError'
                else:
                    self.robot['finished']='Fail'
                    self.robot['status']='Error'
                if self.robot_get_lock:
                    self.planner.clean_right(False)

            elif (head == "S84"): # Robot cmd response # Mike: 2021/05/27
                res='Ok' if data[1] == '0' else 'Reject'
                self.logger.debug('{} {:04d} {}'.format('[{}] '.format(self.id), systemId, res))
                if res == 'Reject':
                    self.robot['finished']='InterlockError'

            elif (head == "S88"): # Robot cmd response # Mike: 2021/05/27
                res='Ok' if data[1] == '0' else 'Reject'
                self.logger.debug('{} {:04d} {} {}'.format('[{}] '.format(self.id), systemId, data[2:6], res))
                if res == 'Reject' and self.robot['command'] == data[2:6]:
                    self.robot['finished']='InterlockError'

            elif (head == "P89"): # Robot cmd check for EQ # Chi: 2023/03/15
                if data[1] == '1':
                    self.robot['finished']='wait_trback'


            ###############
            #             #
            #   battery   #
            #             #
            ###############

            elif (head == 'P29'):    # Charge Status Report
                if data[1] == '0':
                    self.battery['charge']=False
                    output('VehicleChargeEnd',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Battery':self.battery['percentage'],
                            'Charge':self.battery['charge'],
                            'Health':self.battery['SOH']
                            }) #chocp 2022/1/19
                else:
                    if global_variables.RackNaming == 18:
                        
                        if self.last_point == "C001":
                            if global_variables.cs_find_by["TBS01"] == self.id:
                                global_variables.cs_find_by["TBS01"]=""
                        elif self.last_point == "C002":
                            if global_variables.cs_find_by["TBS02"] == self.id:
                                global_variables.cs_find_by["TBS02"]=""
                        elif self.last_point == "C003":
                            if global_variables.cs_find_by["TBS03"] == self.id:
                                global_variables.cs_find_by["TBS03"]=""
                        elif self.last_point == "C004":
                            if global_variables.cs_find_by["TBS04"] == self.id:
                                global_variables.cs_find_by["TBS04"]=""

                    self.battery['charge']=True
                    output('VehicleChargeBegin',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Battery':self.battery['percentage'],
                            'Charge':self.battery['charge'],
                            'Connected':self.online['connected'],
                            'Health':self.battery['SOH']
                            }) #chocp 2022/1/19


                self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'charge:', self.battery['charge']))

            elif (head == 'P73'):    # Exchange Finished Report
                if data[1] == '0':
                    self.battery['error']=False
                    self.battery['exchange']=False
                else:
                    self.battery['error']=True
                    # self.battery['exchange']=False

                self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'exchange finished report:', data[1]))

            elif (head == 'P75'):    # Exchange Status Report
                if data[1] == '0':
                    self.battery['exchange']=False
                    output('VehicleExchangeEnd',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Battery':self.battery['percentage'],
                            'Exchange':self.battery['exchange'],
                            'Health':self.battery['SOH']
                            }) #chocp 2022/1/19
                else:
                    self.battery['exchange']=True
                    output('VehicleExchangeBegin',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Battery':self.battery['percentage'],
                            'Exchange':self.battery['exchange'],
                            'Connected':self.online['connected'],
                            'Health':self.battery['SOH']
                            }) #chocp 2022/1/19

                self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'exchange:', self.battery['exchange']))

            elif (head == "S36"): # Battery status response
                self.battery['percentage']=int(data[1:4])
                self.battery['voltage']=int(data[4:8])
                self.battery['temperature']=int(data[8:11])

            elif (head == "S72"): # Exchange cmd response
                res='Reject' if data[1] == '0' else 'OK'

                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), systemId, res))
                if res == 'OK':
                    self.battery['exchange']=True

            ###########
            #         #
            #  route  #
            #         #
            ###########

            elif (head == "P91"): # Current route report
                route_name=data[1:]
                if route_name in global_variables.global_route_mapping:
                    self.move['pose']['z']=global_variables.global_map_mapping[global_variables.global_route_mapping[route_name]]
                    self.route_status['current']=route_name
                    self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), 'current moveappend route:', route_name, global_variables.global_route_mapping[route_name], self.move['pose']['z']))
                    self.info_query()
                else:
                    self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'current moveappend route:', route_name, 'NG'))

            elif (head == "S94"): # Map change cmd response 
                res='Reject' if data[1] == '0' else 'OK'
                if res == 'OK':
                    self.route_status['exchange']='OK'
                else:
                    self.route_status['exchange']='NG'

                self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route exchange', systemId, res))

            elif (head == "P95"): # Map change Report
                res='NG' if data[1] == '0' else 'OK'
                if res == 'OK':
                    self.route_status['exchange']='Done'
                else:
                    self.route_status['exchange']='NG'

                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'route exchange result:', res))

            #############
            #           #
            #   alarm   #
            #           #
            #############

            elif (head == 'P61'):    # Alarm Report
                self.logger.error('{} {}'.format('=>P61', data[1], data[2:8]))
                # Mike: 2021/02/22
                if version_check(self.mr_spec_ver, '2.4') and data[1] in ['2', '3']:
                    command_id=self.vehicle_instance.action_in_run.get('local_tr_cmd', {}).get('uuid', '')
                    target=self.vehicle_instance.action_in_run.get('target', '')
                    alarms.BaseOtherWarning(self.id, command_id, target, data[2:8], handler=self.vehicle_instance.secsgem_e88_h)
                else:
                    if data[1] == '0':
                        self.alarm['reset']=False
                        self.alarm['error_code']=''
                    else:
                        self.logger.error('{} {} {}'.format('alarm:', self.alarm['reset'], data[2:8]))
                        if data[2:5] == 'TS9':
                            self.alarm_list[data[2:5]].append(data[2:8])
                        elif data[2:4] in self.alarm_list:
                            self.alarm_list[data[2:4]].append(data[2:8])
                        else:
                            self.alarm_list['other'].append(data[2:8])
                        if not self.wait_alarm_th or not self.wait_alarm_th.is_alive():
                            self.is_moving=False
                            self.is_update_location=False
                            self.new_data=False # Mike: 2021/03/28
                            th=threading.Thread(target=self.planner.update_location, args=(True,))
                            th.setDaemon(True)
                            th.start()
                            self.planner.current_route.clear() # Mike: 2021/03/17
                            self.planner.current_go_list.clear() # Mike: 2021/03/17
                            th=threading.Thread(target=self.planner.clean_right, args=(True,))
                            th.setDaemon(True)
                            th.start()
                            self.wait_alarm_th=threading.Timer(1, self.alarm_report)
                            self.wait_alarm_th.setDaemon(True)
                            self.wait_alarm_th.start()

            elif (head == 'P63'):    # Reset Alarm
                self.alarm['reset']=False
                self.alarm['error_code']=''
                self.last_alarm_point=''
                if global_variables.TSCSettings.get('Recovery', {}).get('ResetSyncWithMR', 'no').lower() == 'yes' and \
                    self.vehicle_instance.AgvState == 'Pause': # Mike: 2022/04/15
                    self.vehicle_instance.error_reset_cmd=True
                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'Get reset alarm:'))

            elif (head == "S64"): # Reset cmd response

                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'reset ok'))

            #############
            #           #
            #   other   #
            #           #
            #############

            elif (head == "S82"): # All Info response

                if self.alarm['error_code'] or self.online['man_mode']: # Mike: 2021/11/08
                    if global_variables.RackNaming == 18:
                        for cs_station, vehicleID in global_variables.cs_find_by.items():
                            if vehicleID == self.id:
                                if cs_station == "TBS01":
                                    
                                    global_variables.cs_find_by["TBS01"]=""
                                    break
                                elif cs_station == "TBS02":
                                  
                                    global_variables.cs_find_by["TBS02"]=""
                                    break
                                elif cs_station == "TBS03":
                                    
                                    global_variables.cs_find_by["TBS03"]=""
                                    break
                                elif cs_station == "TBS04":
                                   
                                    global_variables.cs_find_by["TBS04"]=""
                                    break
                    self.new_data=False # Mike: 2021/03/28
                    th=threading.Thread(target=self.planner.update_location, args=(True, True, 1500, False)) # Mike: 2022/02/08 # Mike: 2022/02/25
                    th.setDaemon(True)
                    th.start()

                if data[1] == '0':
                    self.move['status']='Idle'
                elif data[1] == '1':
                    self.move['status']='Working'
                elif data[1] == '2':
                    self.move['status']='Pausing'
                elif data[1] == '3':
                    self.move['status']='Pause'
                elif data[1] == '4':
                    self.move['status']='Stopping'
                elif data[1] == '5':
                    self.move['status']='Block'
                else:
                    self.move['status']='Error'

                s=1 if data[2] == 'P' else -1
                self.move['pose']['x']=int(data[3:11])*s

                s=1 if data[11] == 'P' else -1
                self.move['pose']['y']=int(data[12:20])*s

                self.move['pose']['h']=int(data[20:23])
                self.move['velocity']['w']=int(data[23:26])
                self.move['velocity']['speed']=int(data[26:30])
                self.new_data=True # Mike: 2020/03/04

                if self.dynamic_release_right: # Mike: 2020/03/05
                    if self.planner.current_route or self.occupied_route:
                        self.planner.clean_path()

                #self.logger.info(''.format('move:', self.move['status'])

                #self.logger.info(''.format('position:', self.move['pose']['x'],\
                #                   self.move['pose']['y'],\
                #                   self.move['pose']['h'])
                #self.logger.info(''.format('velocity',  self.move['velocity']['w'],\
                #                   self.move['velocity']['speed'])

                if data[30] == '0':
                    self.robot['status']='Idle'
                elif data[30] == '1':
                    self.robot['status']='Busy'
                else:
                    self.robot['status']='Error'

                if data[31] == '1':
                    self.robot['at_home']=True
                else:
                    self.robot['at_home']=False

                #self.logger.info('{} {} {}'.format('robot:', self.robot['status'], self.robot['at_home']))

                self.battery['percentage']=int(data[32:35])
                self.battery['voltage']=int(data[35:39])
                self.battery['temperature']=int(data[39:42])
                if data[42:45]: # Mike: 2021/05/11
                    SOH=int(data[42:45])
                else:
                    SOH=100
                # chi: 2023/02/09
                if data[45:51]: 
                    current=1 if data[45] == 'P' else -1
                    self.battery['current']=int(data[46:51])*current
                else:
                    self.battery['current']=0

                # Mike: 2021/05/14
                '''ActiveVehicles=E82.get_variables(SecsGem.h, 'ActiveVehicles')
                if self.id in ActiveVehicles:
                    ActiveVehicles[self.id]["VehicleInfo"]["SOH"]=SOH
                    E82.update_variables(SecsGem.h, {'ActiveVehicles': ActiveVehicles})'''
                if SOH != self.battery['SOH']: # Mike: 2021/05/12
                    self.battery['SOH']=SOH
                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Vehicle SOH: ', SOH)) # Mike: 2020/05/19
                    '''E82.report_event(SecsGem.h,
                                     E82.VehicleBatteryHealth,{
                                     'VehicleID':self.id,
                                     'VehicleSOH':self.battery['SOH']})'''

                #self.logger.info(''.format(self.battery['percentage'], self.battery['voltage']/100.0, self.battery['temperature'])
                #self.logger.info(''.format('{}%, {}V, {}deg'.format(self.battery['percentage'], self.battery['voltage']/100.0, self.battery['temperature']))
                '''output('VehiclePoseUpdate',{ #'VehiclePointUpdate'
                        'VehicleID':self.id,
                        'VehicleState':self.vehicle_instance.AgvState,
                        #'VehicleState':'Enroute',
                        'Pose':[self.move['pose']['x'], self.move['pose']['y'],  self.move['pose']['h'], self.move['pose']['z']],
                        'Battery':self.battery['percentage'],
                        'Charge':self.battery['charge'],
                        'Connected':self.online['connected'], # Mike: 2022/05/31
                        'Health':self.battery['SOH'],
                        'MoveStatus':self.move['status'],
                        'RobotStatus':self.robot['status'],
                        'RobotAtHome':self.robot['at_home'],
                        'Voltage':self.battery['voltage'],
                        'Temperature':self.battery['temperature'],
                        'Current':self.battery['current'],
                        'RealTime':True }) ''' #2024/1/3 chocp

                self.online['status']='Ready'
                    
            else:
                self.logger.info('{} {} {} {}'.format('[{}] '.format(self.id), 'Get other message:', msg[0:3], data[1:]))

            return '' # Mike: 2021/05/27
        except:
            traceback.print_exc()
            self.logger.warning('{} {} {}, {}, {}'.format('[{}] '.format(self.id), 1, 'decode msg error', msg, systemId))
            raise mWarning(1, 'decode msg error')
            pass

    def recv_message(self, timeout=10):

        self.sock.settimeout(timeout)
        raw_rx=self.sock.recv(1024).decode('utf-8')
        #self.logger.info(''.format(raw_rx)
        if raw_rx == '':
            self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 2, 'recv_status: get null string'))
            raise mWarning(2, 'recv_status: get null string')
            #return #chocp: 2021/3/9

        offset=0
        while len(raw_rx) >= (offset+8): #may have \n
            size=ord(raw_rx[offset])
            msg=raw_rx[offset+1:offset+1+size]
            systemId=int(raw_rx[offset+1+size:offset+1+size+4])
            #self.logger.debug('{} >> {}'.format('[{}] '.format(self.id), raw_rx))
            res='' # Mike: 2022/05/04
            try:
                res=self.msg_decode(msg, systemId) # Mike: 2021/05/27
            except:
                pass
            if msg[0] == 'P': #echo ack only for P mas
                payload='%c%02d'%('S', int(msg[1:3])+1)+res # Mike: 2021/05/27
                string=bytearray([len(payload)])+\
                        bytearray(payload, encoding='utf-8')+\
                        bytearray('%04d'%systemId, encoding='utf-8')
                self.sock.send(string)
            else:
                if systemId in self.cmd_ack_queue: # Mike: 2021/10/08
                    try:
                        del self.cmd_ack_queue[systemId]
                    except:
                        pass

            offset+=(size+1+4)

        else:
            #self.logger.info(''.format('end recv message', len(raw_rx), offset)
            pass

####################################################
    ''' Direct cmd '''
    def systemID_gen(self):
        ret=0

        self.systemID_gen_lock.acquire()
        self.systemId+=1
        self.systemId%=10000
        self.systemID_gen_lock.release()

        ret=self.systemId
        
        return ret

    def go(self, x, y, h, go, end, speed=500, auto_avoid=0):

        p=[0,0,0,0]
        p[0]=int(x)
        p[1]=int(y)
        p[3]=int(h)
        cmd='P41'
        cmd+='{}'.format(end)
        cmd+='P' if p[0]>0 else 'N'
        cmd+='%.8d'%(abs(p[0]))
        cmd+='P' if p[1]>0 else 'N'
        cmd+='%.8d'%(abs(p[1]))
        cmd+='%.3d'%p[3]
        cmd+='%.4d'%int(speed)
        cmd+='0'
        #cmd+='G' if end or go else 'K'
        cmd+=go # Mike: 2021/03/11
        cmd+='%.1d'%int(auto_avoid) # Mike: 2021/03/11

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)

    def change(self, x, y, h, go, end, speed=500): # Mike:2021/06/16

        p=[0,0,0,0]
        p[0]=int(x)
        p[1]=int(y)
        p[3]=int(h)
        cmd='P85'
        cmd+='{}'.format(end)
        cmd+='P' if p[0]>0 else 'N'
        cmd+='%.8d'%(abs(p[0]))
        cmd+='P' if p[1]>0 else 'N'
        cmd+='%.8d'%(abs(p[1]))
        cmd+='%.3d'%p[3]
        cmd+='%.4d'%int(speed)
        cmd+='0'
        #cmd+='G' if end or go else 'K'
        cmd+=go # Mike: 2021/03/11

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)

    def robot_control(self, from_port, to_port, command='0000', e84=0, cs=0, cont=0, pn=1, ct=0): # Mike: 2021/05/27
        self.robot['finished']='Waiting'
        #cmd='P45'
        if version_check(self.mr_spec_ver, '2.5') and global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes':
            carrierTypeList=global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypePrefix').split(',')
            cmd='P45{}{}{}{}{}<{}><{}>'.format(
                e84, cs, cont, pn, ct,
                from_port, to_port)
        elif version_check(self.mr_spec_ver, '1.3'):
            cmd='P87{}{}<{}><{}>'.format(0, command, from_port, to_port) # Mike: 2021/05/27
        else:
            cmd='P83'
            cmd+='0' #no pio
            cmd+='%7s'%from_port[:7] #BUFFER1
            cmd+='%7s'%to_port[:7] #S001P01

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)

    def robot_check_control(self, check=True): # Mike: 2022/02/23

        if version_check(self.mr_spec_ver, '1.5'):
            cmd='P89'+('1' if check else '0')

            sysID=self.systemID_gen()

            cmd_obj={
                'cmd':cmd,
                'systemId':sysID,
                'timeout':10,
                'sync':True
            }
            self.cmd_queue.append(cmd_obj)
            #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'robot_check_control:', check))
        return

    def charge_control(self, charge_on=True):

        cmd='P47'+('1' if charge_on else '0')

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        self.relay_on=charge_on #chocp, 2021/4/14
        return

    def exchange_control(self):

        cmd='P71'

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def route_control(self, route_name):

        cmd='P93'+route_name

        sysID=self.systemID_gen()

        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def stop_control(self):
        self.wait_stop=True
        cmd='P512'

        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':False
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return
    
    def host_stop_control(self):
        cmd='P514'

        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':False
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def alarm_control(self, alarm, state):
        cmd='P61' + '1' if state else '0'
        cmd += '{:06d}'.format(alarm)[:6]

        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':False
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def reset_all_alarm(self, timeout=3):
        cmd='P63'
        
        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':3,
            'sync':True
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def rfid_control(self, buf, carrierID):
        if not version_check(self.mr_spec_ver, '2.6'):
            return
        cmd='P27{:02d}{}'.format(buf, carrierID)

        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':False
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

####################################################
    ''' Enroute '''
    def move_cmd(self, path, go_list): # Mike: 2021/02/18
        self.logger.info('{} {}'.format('[{}] '.format(self.id), 'move_cmd....'))

        output('VehicleRoutesPlan', {
                'VehicleID':self.id,
                'VehicleState':self.vehicle_instance.AgvState,
                'Cost':Route.h.get_path_cost(path),
                'Routes':self.planner.occupied_route })  #chocp add:2022/1/25

        if self.battery['charge']: #chocp, re-check again 2021/11/17
            if not self.charge_end(): # Mike: 2021/04/09
                self.move_cmd_reject=True
                return

        self.cmd_sending=True # Mike: 2021/03/11
        self.cmd_path=[] # Mike: 2021/03/04
        self.move_cmd_reject=False # Mike: 2021/04/09
        self.move_cmd_nak=False # Mike: 2024/01/15
        change_buf=()

        speed=self.max_speed
        auto_avoid=0
        while path:
            a=path[0]
            b=go_list[0]
            pose=tools.get_pose(a)
            if pose['go']:
                b='G'
            c=2 if self.begin else 1 if ((len(path) == 1)&(len(self.planner.current_route) == 0)&self.end) else 0

            '''try:
                speed=self.max_speed if len(path)<2 else int((Route.h.get_edge_detail(a, path[1]).speed/100.0)*self.max_speed)
            except Exception:
                self.logger.warning('{} {} {} {}'.format('[{}] '.format(self.id), 'speed bug: ', a, path[1]))'''
            self.logger.debug('{} {} {} {} {} {} {} {} {}'.format('[{}] '.format(self.id), a, pose['x'], pose['y'], pose['z'], pose['w'], b, c, speed))
            if b == 'C': # Mike: 2021/06/16
                bb='K'
                if len(self.planner.occupied_route) > 0 and version_check(self.mr_spec_ver, '1.4'):
                    # self.change(pose['x'], pose['y'], pose['w'], bb, c, speed)
                    change_buf=(pose['x'], pose['y'], pose['w'], 'G', c, speed)
                else:
                    pass
                    # self.go(pose['x'], pose['y'], pose['w'], bb, c, speed)
            else:
                self.go(pose['x'], pose['y'], pose['w'], b, c, speed, auto_avoid)
                if b == 'G' and change_buf:
                    self.logger.debug('{} change {} {} {} {} {} {}'.format('[{}] '.format(self.id), *change_buf))
                    self.change(*change_buf)
                    change_buf=()
            path=path[1:]
            go_list=go_list[1:]
            # self.logger.debug('{} {} {} {} {} {} {} {} {}'.format('[{}] '.format(self.id), a, pose['x'], pose['y'], pose['z'], pose['w'], b, c, speed))
            self.begin=False
            self.cmd_path.append(a) # Mike: 2021/03/04
            try:
                auto_avoid=0 if not path else getattr(Route.h.get_edge_detail(a, path[0]), 'dynamic_avoid', 0)
                speed=self.max_speed if not path else int((Route.h.get_edge_detail(a, path[0])['speed']/100.0)*self.max_speed)
            except Exception:
                print(Route.h.get_edge_detail(a, path[0]))
                traceback.print_exc()
                self.logger.warning('{} {} {} {}'.format('[{}] '.format(self.id), 'speed bug: ', a, path[0]))


            time.sleep(0.01)
        self.cmd_sending=False # Mike: 2021/03/11
        return

    def move_control(self, path, is_begin=True, is_end=True): # Mike: 2021/02/18
        self.logger.info('{} {} {} {}'.format('[{}] '.format(self.id), 'get move_control....', is_begin, is_end))

        while not self.move_control_lock.acquire():
            time.sleep(0.1)

        if self.planner.get_right_th and self.planner.get_right_th.is_alive():
            time.sleep(0.5)
            if self.planner.get_right_th.is_alive():
                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'MR still routing....'))
                self.move_control_lock.release()
                return False

        self.charge_end() #make relay off chocp 2021/11/17

        self.begin=is_begin # Mike: 2021/10/26
        if is_begin or path[0][0] in ['c', 'C']:
            self.begin=True
        self.end=is_end

        ### param ###
        self.planner.enable_traffic_point=True if global_variables.TSCSettings.get('TrafficControl', {}).get('EnableTrafficPoint', 'yes').lower() == 'yes' else False
        self.planner.get_right_timeout=global_variables.TSCSettings.get('TrafficControl', {}).get('GetRightTimeout', 180)
        self.planner.enable_find_way= True if global_variables.TSCSettings.get('TrafficControl', {}).get('EnableFindWay', 'yes').lower() == 'yes' else False
        self.planner.find_way_time=global_variables.TSCSettings.get('TrafficControl',{}).get('FindWayTime', 3)
        self.planner.max_find_way_cost=global_variables.TSCSettings.get('TrafficControl',{}).get('MaxFindWayCost', 60000)
        self.planner.dynamic_release_right=True if global_variables.TSCSettings.get('TrafficControl', {}).get('DynamicReleaseRight', 'yes').lower() == 'yes' else False
        self.planner.release_right_base_on_location=True if global_variables.TSCSettings.get('TrafficControl', {}).get('ReleaseRightBaseOnLocation', 'yes').lower() == 'yes' else False
        self.planner.enable_avoid_node=True if global_variables.TSCSettings.get('TrafficControl',{}).get('EnableAvoidNode', 'yes').lower() == 'yes' else False # Mike: 2021/04/06
        self.planner.keep_angle=global_variables.TSCSettings.get('TrafficControl', {}).get('KeepAngle', 20.0)
        try:
            self.planner.keep_angle=float(self.planner.keep_angle)
        except:
            self.planner.keep_angle=20.0
        self.logger.debug('{} {} {} {} {} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'param: ', self.planner.enable_traffic_point, \
                                                                                                     self.planner.keep_angle, \
                                                                                                     self.planner.get_right_timeout, \
                                                                                                     self.planner.enable_find_way, \
                                                                                                     self.planner.find_way_time, \
                                                                                                     self.planner.max_find_way_cost, \
                                                                                                     self.planner.dynamic_release_right, \
                                                                                                     self.planner.release_right_base_on_location, \
                                                                                                     self.planner.enable_avoid_node))

        self.move['arrival']=''

        # Mike: 2021/08/14
        self.junction_list=collections.deque() # Mike: 2021/08/13
        r, g, j=self.planner.path_calculate(path)
        r, g=self.planner.process_check(r, g)
        self.planner.current_go_list += g
        self.planner.current_route += r
        self.junction_list += j

        self.planner.find_way=True
        self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'path: ', self.planner.current_route, self.planner.current_go_list))
        self.planner.get_right_th=threading.Thread(target=self.planner.get_right,)
        self.planner.get_right_th.setDaemon(True)
        self.planner.get_right_th.start()
        self.move_control_lock.release()
        return True

    def vehicle_stop(self):
        self.stop_control()
        for i in range(120):
            if not self.wait_stop:
                return False
            if self.move['status'] == 'Idle':
                break
            time.sleep(0.5)
        else:
            self.wait_stop=False
            return False

        self.wait_stop=False
        self.logger.info('{} {}'.format('[{}] '.format(self.id), 'Vehicle stop cmd'))

        self.planner.current_route.clear() # Mike: 2021/03/17
        self.planner.current_go_list.clear() # Mike: 2021/03/17
        th=threading.Thread(target=self.planner.clean_right,)
        th.setDaemon(True)
        th.start()
        if self.planner.get_right_th:
            while self.planner.get_right_th.is_alive():
                time.sleep(0.5)

        return True

####################################################
    ''' Robot '''
    def acquire_control(self, eq_port, loc, carrierID, e84=0, cs=0, cont=0, pn=1, ct=0, no_check=False):
        print('acquire_control', eq_port, loc, carrierID)
        return False

    def deposite_control(self, eq_port, loc, carrierID, e84=0, cs=0, cont=0, pn=1, ct=0, no_check=False):
        print('deposite_control', eq_port, loc, carrierID)
        return False

    def shift_control(self, from_port, to_port, carrierID, e84=0, cs=0, cont=0, fpn=1, tpn=2, ct=0, no_check=False):
        if self.version_check(self.mr_spec_ver, '4.0'):
            return False
        print('shift_control', from_port, fpn, to_port, tpn, carrierID)
        return False

####################################################
    ''' Battery '''
    def charge_start(self):
        #self.battery['charge']='On' #chocp:2021/3/28
        self.charge_control(charge_on=True)
        for i in range(120):
            if self.battery['charge']:
                return True
            if not self.online['sync']:
                return False
            time.sleep(0.5)
        return False

    def charge_end(self):
        #self.battery['charge']='Off' #chocp:2021/3/28
        self.charge_control(charge_on=False)
        for i in range(120):
            if not self.battery['charge']:
                return True
            if not self.online['sync']:
                return False
            time.sleep(0.5)
        return False

    def exchange_start(self):
        self.exchange_control()
        for i in range(120):
            if self.battery['exchange']:
                return True
            if not self.online['sync']:
                return False
            time.sleep(0.5)

        return False

####################################################
    ''' Others '''
    def route_change(self, route_name):
        self.route_control(route_name)
        cnt=0
        for i in range(120):
            if self.route_status['exchange'] == 'NG':
                self.route_status['exchange'] == 'None'
                if cnt > 3:
                    return False
                else:
                    cnt += 1
                    self.route_control(route_name)
            if self.route_status['exchange'] == 'Done':
                self.route_status['exchange'] == 'None'
                return True
            time.sleep(0.5)

        return False

    def alarm_report(self):
        code=''
        if self.alarm_list['TM']:
            code=self.alarm_list['TM'][0]
        elif self.alarm_list['TS']:
            code=self.alarm_list['TS'][0]
        elif self.alarm_list['EC']:
            code=self.alarm_list['EC'][0]
        elif self.alarm_list['BS']:
            code=self.alarm_list['BS'][0]
        elif self.alarm_list['CB']:
            code=self.alarm_list['CB'][0]
        elif self.alarm_list['RM']:
            code=self.alarm_list['RM'][0]
        elif self.alarm_list['TB']:
            code=self.alarm_list['TB'][0]
        elif self.alarm_list['IM']:
            code=self.alarm_list['IM'][0]
        elif self.alarm_list['TS9']:
            code=self.alarm_list['TS9'][0]
        elif self.alarm_list['other']:
            code=self.alarm_list['other'][0]
        else:
            pass
        for key in self.alarm_list:
            self.alarm_list[key]=[]
        self.alarm['error_code']=code
        if code:
            command_id=self.vehicle_instance.action_in_run.get('local_tr_cmd', {}).get('uuid', '')
            target=self.vehicle_instance.action_in_run.get('target', '')
            # alarms.BaseOtherAlertWarning(self.id, command_id, target, self.alarm['error_code'])

####################################################
    ''' Others '''
    def info_query(self, timeout=3):
        cmd='P81'
        
        sysID=self.systemID_gen()
        cmd_obj={
            'cmd':cmd,
            'systemId':sysID,
            'timeout':10,
            'sync':False
        }
        self.cmd_queue.append(cmd_obj)
        #self.send_cmd_wait_ack(cmd, self.systemId, timeout=2, sync=False)
        return

    def all_status_query(self, timeout=3):
        cmd='P31'+'0'
        
        sysID=self.systemID_gen()
        self.send_cmd_wait_ack(cmd, sysID, timeout, sync=False)
        return

    def version_query(self, timeout=3):
        cmd='P17'
        
        sysID=self.systemID_gen()
        self.send_cmd_wait_ack(cmd, sysID, timeout, sync=False)
        return

    def map_query(self, timeout=3):
        cmd='P315'
        
        sysID=self.systemID_gen()
        self.send_cmd_wait_ack(cmd, sysID, timeout, sync=False)
        return

    '''
    def position_query(self, timeout=2):
        cmd='P33'
        self.systemId+=1
        self.systemId%=10000
        self.send_cmd_wait_ack(cmd, self.systemId, timeout, sync=False)
        return
    '''

    '''
    def battery_query(self, timeout=2):
        cmd='P35'
        self.systemId+=1
        self.systemId%=10000
        self.send_cmd_wait_ack(cmd, self.systemId, timeout, sync=False)
        return
    '''

    def date_and_time_setting(self):
        return

####################################################
    ''' Message sender '''
    def wait_ack(self, systemId=0, timeout=10, sync=True, retry_cnt=0): # Mike: 2021/04/20
        if sync:
            tic=time.time()
            toc=tic
            while toc-tic < timeout:
                if systemId not in self.cmd_ack_queue:
                    break
                time.sleep(0.1)
                toc=time.time() # Mike: 2021/09/07
            else:
                if not self.msg_retry: # or retry_cnt >= self.msg_retry_cnt_limit: # Mike: 2021/09/22
                    if self.cmd_ack_queue[systemId]['cmd'][:3] == 'P41': # Mike: 2021/04/09
                        print('move_cmd_nak', systemId)
                        self.move_cmd_nak=True
                    try:
                        del self.cmd_ack_queue[systemId]
                    except:
                        pass
                    self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 3, 'recv_ack:timeout'))
                    self.nak_list.append(mWarning(3, 'recv_ack:timeout')) # Mike: 2021/09/07
                else:
                    self.send_cmd_wait_ack(self.cmd_ack_queue[systemId]['cmd'], self.cmd_ack_queue[systemId]['systemId'], self.cmd_ack_queue[systemId]['timeout'], self.cmd_ack_queue[systemId]['sync'], retry_cnt+1) # Mike: 2021/09/22
        else:
            try:
                del self.cmd_ack_queue[systemId]
            except:
                pass

    def send_cmd_wait_ack(self, cmd, systemId=0, timeout=10, sync=True, retry_cnt=0):
        size=len(cmd) if len(cmd) else 255
        systemBytes=bytearray('%04d'%systemId, encoding='utf-8')
        string=bytearray([size])+bytearray(cmd, encoding='utf-8')+systemBytes

        # Mike: 2021/03/26 # Mike: 2021/04/20
        try:
            self.sock.send(string)
            #self.logger.debug('{} {}'.format('[{}] '.format(self.id), string))
            if self.non_blocking_mode: # Mike: 2021/09/22
                th=threading.Thread(target=self.wait_ack, args=(systemId, timeout, sync, retry_cnt))
                th.setDaemon(True)
                th.start()
            else:
                self.wait_ack(systemId, timeout, sync)
        except socket.timeout:
            #traceback.print_exc()
            if self.cmd_ack_queue[systemId]['cmd'][:3] == 'P41': # Mike: 2021/04/09
                print('move_cmd_nak', systemId)
                self.move_cmd_nak=True
            raise mWarning(3, 'recv_ack:timeout')
            pass

####################################################
    ''' Main loop '''
    #for thread
    def run(self):
        count=0
        disconnect_count=0
        th=None
        while not self.vehicle_instance.thread_stop and self.vehicle_instance.is_alive():
            try:
                self.heart_beat=time.time()
                if not self.online['connected'] and not self.online['sync']: #step 1 #2022/6/9
                    self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'MR connecting:{},{}...'.format(self.ip, self.port)))
                    try:
                        self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.sock.settimeout(10)
                        self.sock.connect((self.ip, self.port))
                    except:
                        traceback.print_exc()
                        self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 4, 'connect fail'))
                        raise mWarning(4, 'connect fail')

                    self.online['last_recive']=time.time()
                    self.online['connected']=True

                    disconnect_count=0

                    self.cmd_ack_queue={} #mike fix
                    self.systemID_mem={}


                    self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'MR connected:{},{}'.format(self.ip, self.port)))

                elif not self.online['sync']: #step 2

                    self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'MR start sync:{},{}...'.format(self.ip, self.port)))
                    self.all_status_query()
                    #self.info_query()
                    self.version_query() # Mike: 2021/07/16
                    # self.vehicle_stop()

                    if not th or not th.is_alive():
                        th=threading.Thread(target=self.vehicle_stop, args=())
                        th.setDaemon(True)
                        th.start()

                    if len(self.cmd_queue)>0:
                        cmd_obj=self.cmd_queue[0] #try send
                        # Mike: 2021/03/26 # Mike: 2021/04/20
                        self.cmd_ack_queue[cmd_obj['systemId']]=cmd_obj
                        self.send_cmd_wait_ack(cmd_obj['cmd'], cmd_obj['systemId'], cmd_obj['timeout'], cmd_obj['sync'])
                        self.cmd_queue.popleft() #if success
                    try:
                        self.recv_message(timeout=1)
                    except socket.timeout: #allow the exception
                        continue

                    self.online['sync']=True

                    self.new_data=False
                    th=threading.Thread(target=self.planner.update_location, args=(True,))
                    th.setDaemon(True)
                    th.start()

                else: #step 3

                    if len(self.cmd_queue)>0:
                        cmd_obj=self.cmd_queue[0] #try send
                        # Mike: 2021/03/26 # Mike: 2021/04/20
                        self.cmd_ack_queue[cmd_obj['systemId']]=cmd_obj
                        self.send_cmd_wait_ack(cmd_obj['cmd'], cmd_obj['systemId'], cmd_obj['timeout'], cmd_obj['sync'])
                        self.cmd_queue.popleft() #if success
                    else: #chocp: 2021/3/18 fix latency too long when manay node in a route
                        if count>= (10 if self.is_moving else 50):
                            self.info_query()
                            count=0
                        else:
                            count+=1

                        try:
                            self.recv_message(timeout=0.1)
                        except socket.timeout: #allow the exception
                            pass

                    if (time.time()- self.online['last_recive']) >= 50: # Mike: 2022/06/01
                        self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 5, 'linklost'))
                        raise mWarning(5, 'linklost')

                    if self.nak_list:
                        self.nak_list.popleft()
                        # raise self.nak_list.popleft()


                    #print(self.last_point, self.move['pose'])
                    disconnect_count=0
                time.sleep(0.01) #8.25.14-3



            except:
                traceback.print_exc()

                if disconnect_count == 0:
                    alarms.BaseOffLineNotifyWarning(self.id, '')

                self.alarm['error_txt']=traceback.format_exc()
                try:
                    self.sock.close()
                    #chocp 2022/6/9 for disconnected display
                    if self.online['connected']:
                        self.online['connected']=False

                        '''output('VehiclePoseUpdate',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Pose':[self.move['pose']['x'], self.move['pose']['y'],  self.move['pose']['h'], self.move['pose']['z']],
                            'Battery':self.battery['percentage'],
                            'Charge':self.battery['charge'],
                            'Connected':self.online['connected'], # Mike: 2022/05/31
                            'Health':self.battery['SOH'],
                            'MoveStatus':self.move['status'],
                            'RobotStatus':self.robot['status'],
                            'RobotAtHome':self.robot['at_home']})''' #2024/1/3 chocp

                except:
                    pass
                try:
                    time.sleep(1)
                    self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.settimeout(10)
                    self.sock.connect((self.ip, self.port))
                    self.online['connected']=True
                except:
                    pass
                disconnect_count+=1

                if disconnect_count == self.retry_count_limit+1:
                    self.online['status']='Error'
                    self.online['man_mode']=True
                    self.move['status']=''
                    self.robot['status']=''
                    self.battery['charge']=False
                    self.cmd_queue.clear()
                    
                    #chocp 2022/6/9 for disconnected display
                    if self.online['connected']:
                        self.online['connected']=False

                        '''output('VehiclePoseUpdate',{
                            'VehicleID':self.id,
                            'VehicleState':self.vehicle_instance.AgvState,
                            'Pose':[self.move['pose']['x'], self.move['pose']['y'],  self.move['pose']['h'], self.move['pose']['z']],
                            'Battery':self.battery['percentage'],
                            'Charge':self.battery['charge'],
                            'Connected':self.online['connected'], # Mike: 2022/05/31
                            'Health':self.battery['SOH'],
                            'MoveStatus':self.move['status'],
                            'RobotStatus':self.robot['status'],
                            'RobotAtHome':self.robot['at_home']})''' #2024/1/3 chocp
                    
                    self.online['sync']=False
                    

                time.sleep(2)
            '''
            except: #must, conection reset by peer
                traceback.print_exc()
                sleep(1)
            '''
        else:
            # Mike: 2021/11/24
            self.planner.current_route.clear()
            self.planner.current_go_list.clear()
            self.planner.clean_right(False)
            if self.last_point:
                if self.planner.memory_group:
                    for group in self.planner.memory_group.split("|"):
                        if group not in global_variables.global_vehicles_location:
                            global_variables.global_vehicles_location[group]=''
                        if global_variables.global_vehicles_location[group] == self.id:
                            global_variables.global_vehicles_location[group]=''
                    global_variables.global_vehicles_location_index[self.id]=''
            self.sock.close()
            self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'stop transporter adapter thread'))




if __name__ == '__main__':

    #h=Adapter('MR001','10.0.4.35', 6789)
    h=Adapter('MR001','192.168.123.10', 6789)
    #h=Adapter('192.168.0.119', 6789)
    h.setDaemon(True)
    h.start()


    try:
        while True:
            res=raw_input('please input:') #go,215,300,180

            cmds=res.split(',')
            #self.logger.info(''.format('\n\n')
            print(cmds)
            if cmds[0] == 'm' and len(cmds)>3:

                h.go(cmds[1], cmds[2], cmds[3])

            elif cmds[0] == 'r' and len(cmds)>2:
                h.robot_control(cmds[1], cmds[2])

            #elif cmds[0] == 'p':
            #    h.position_query()
            #elif cmds[0] == 'b':
            #    h.battery_query()

            elif cmds[0] == 'i':
                h.info_query()

            elif cmds[0] == 'r':
                h.reset_all_alarm()

            else:
                h.all_status_query()


    except:
        traceback.print_exc()
        pass



