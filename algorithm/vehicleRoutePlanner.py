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
import semi.e82_equipment as E82
import alarms

# Mike: 2021/02/18
import global_variables
from global_variables import PoseTable
from global_variables import PortsTable
from global_variables import Route
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host
from global_variables import Iot
from global_variables import global_junction_neighbor # Mike: 2021/08/09
from global_variables import global_moveout_request # Mike: 2021/08/09carriers
from global_variables import global_plan_route # Mike: 2021/08/09
from global_variables import global_elevator_entrance # Mike: 2023/12/02
from global_variables import global_map_mapping
from global_variables import global_route_mapping
import math
import random # Mike: 2021/04/12
import os
from web_service_log import *
from global_variables import M1_global_variables #K11 kelvinng 202503035
import re

def p_angle(p_from, p_to): # Mike: 2021/02/18
    if (p_to[0]-p_from[0]) == 0:
        if p_to[1]-p_from[1]>0:
            return 90.0
        else:
            return 270.0
    angle=math.atan((p_to[1]-p_from[1])/float(p_to[0]-p_from[0]))*180.0/math.pi
    if p_to[0]-p_from[0] < 0.0:
        angle += 180
    if angle < 0:
        angle += 360.0

    return angle

# Mike: 2021/05/18
lock_order={}
lock_order_fix={}
def get_lock(lock, MR, wait_time, cost):
    global lock_order

    if wait_time < 0:
        wait_time=0
    order=(round(wait_time/10)+1)*(round(30000/cost)+1)
    lock_order[MR]=order - lock_order_fix[MR]
    if lock_order[MR] < 0:
        print('Oops!')
        lock_order[MR]=0

    max_cost=-2
    for key, value in lock_order.items():
        if value > max_cost:
            max_cost=value

    print("\npriority: {}\n".format(lock_order))
    if lock_order[MR] == max_cost:
        if lock.acquire(True):
            if lock_order_fix[MR] + round(wait_time/10) < order:
                lock_order_fix[MR]=lock_order_fix[MR] + round(wait_time/10)
            return True
    return False

class mWarning(Exception):
    def __init__(self, code, txt):
        self.code=code
        self.txt=txt
        pass

macro_list=['open_door', 'close_door', #peter 240705
              'go_elevator', 'close_elevator', 'go_floor', 'open_elevator', 'leave_elevator',
              'open_gate', 'close_gate','open_oven','after_Poven','after_Noven','pass_door','air_show']

class RoutePlanner(threading.Thread):

    def __init__(self, adapter):
        self.adapter=adapter
        self.id=adapter.id
        self.logger=adapter.logger

        self.current_route=collections.deque()
        self.current_go_list=collections.deque()
        self.occupied_route=[]
        self.last_group_point={} # Mike: 2022/01/19

        # Mike: 2021/03/05
        ### param ###
        self.enable_traffic_point=True
        self.get_right_timeout=180
        self.enable_find_way=True
        self.find_way_time=3
        self.max_find_way_cost=60000
        self.dynamic_release_right=True
        self.release_right_base_on_location=True
        self.keep_angle=20.0

        self.find_way=True
        self.find_way_cnt=0

        lock_order[self.id]=-1
        lock_order_fix[self.id]=0

        self.route_right_lock=threading.Lock() # Mike: 2024/01/05
        self.stop_cmd_lock=threading.Lock()
        self.is_moving=False

        self.memory_group=''

        self.get_right_th=None
        self.segment_end={}

        self.thread_stop=False

        threading.Thread.__init__(self)

####################################################
    ''' Process '''
    def process_check(self, current_route, current_go_list):
        new_current_route=collections.deque()
        new_current_go_list=collections.deque()
        self.adapter.logger.info("in process_check:{},{}".format(current_route,current_go_list))
        for i in range(len(current_route)):
            start_route=current_route[i][0]
            end_route=current_route[i][-1]
            if i > 0:
                r, g=self.get_pre_process(start_route, current_route[i-1][-1])
                if r:
                    new_current_route.append(r)
                    new_current_go_list.append(g)
            r, g=self.get_pre_process(start_route)
            if r:
                new_current_route.append(r)
                new_current_go_list.append(g)
            new_current_route.append(current_route[i])
            new_current_go_list.append(current_go_list[i])
            if len(current_route[i]) > 1:
                r, g=self.get_post_process(end_route, current_route[i][-2])
            else:
                if i > 0:
                    r, g=self.get_post_process(end_route, current_route[i-1][-1])
                else:
                    r = None
            if r:
                new_current_route.append(r)
                new_current_go_list.append(g)
            r, g=self.get_post_process(end_route)
            if r:
                new_current_route.append(r)
                new_current_go_list.append(g)
        return new_current_route, new_current_go_list

    def get_pre_process(self, route, previous_route=None):
        self.adapter.logger.info("route1:{}".format(route))
        self.adapter.logger.info("previous_route1:{}".format(previous_route))
        r=None
        g=None
        pose=tools.get_pose(route)
        if not previous_route:
            process=pose['PreProcess']
            params=pose['PreProcessParam']
            # print('In get_pre_process', route, process)
        else:
            detail=Route.h.get_edge_detail(previous_route, route)
            if detail:
                process=detail.get('PreProcess', '')
                params=detail.get('PreProcessParam', {})
            else:
                process=''
                params={}
            # print('In get_pre_process', previous_route, route, detail, process)
        # if False: # check what macro is
        #     r=collections.deque(['wait', ('process_name', {'paramkey':'paramval'}), route]) #???
        #     g=collections.deque(['W', 'P', 'I'])
        
        if global_variables.RackNaming==36:#peter 240705
            if pose['PreProcess'] in macro_list:
                self.adapter.logger.info("get_pre_process_with_point{}".format(route))
                
                
                r = collections.deque([pose['PreProcess']])
                g = collections.deque(['P'])
            elif process in macro_list:
                self.adapter.logger.info("get_pre_process_with_line:{}".format(route))
                # r = collections.deque([(process,params.get("point",""))])
                # g = collections.deque(['P'])
                r=collections.deque(['wait',(process,params),route])
                g=collections.deque(['W', 'P', 'I'])
        elif process == 'go_elevator':
            device_id=pose['group']
            floor=pose.get('floor', global_map_mapping[global_route_mapping[pose['route']]]+1)
            params={'DeviceID':device_id, 'Floor':floor}
            r=collections.deque([('call_elevator', params), ('elevator_open', params), 'wait', ('moving_in_elevator', params), route]) #???
            g=collections.deque(['P', 'P', 'W', 'P', 'I'])
        elif process == 'go_floor':
            device_id=pose['group']
            floor=pose.get('floor', global_map_mapping[global_route_mapping[pose['route']]]+1)
            params={'DeviceID':device_id, 'Floor':floor}
            r=collections.deque([('change_route', {}), ('elevator_move', params), route]) #???
            g=collections.deque(['P', 'P', 'I'])
        elif process == 'open_elevator':
            pose=tools.get_pose(previous_route)
            device_id=pose['group']
            floor=pose.get('floor', global_map_mapping[global_route_mapping[pose['route']]]+1)
            params={'DeviceID':device_id, 'Floor':floor}
            r=collections.deque([('elevator_open', params), ('moving_out_elevator', params), route]) #???
            g=collections.deque(['P', 'P', 'I'])
        elif process == 'leave_elevator':
            device_id=pose['group']
            floor=pose.get('floor', global_map_mapping[global_route_mapping[pose['route']]]+1)
            params={'DeviceID':device_id, 'Floor':floor}
            r=collections.deque(['Wait', ('move_out_elevator_complete', params), ('elevator_close', params), route]) #???
            g=collections.deque(['W', 'P', 'P', 'I'])
        elif process == "open_gate":
            r = collections.deque([('gate_open', params), 'wait', ('is_gate_opened', params), route]) #???
            g = collections.deque(['P', 'W', 'P', 'I'])
        elif process == 'open_oven':#richard 0219
            print('oven check', process)
            # pose=tools.get_pose(previous_route)
            # device_id = params
            print('in pre process params:',params)
            r = collections.deque(['wait', ('oven_open', params),  route]) 
            g = collections.deque(['W','P', 'I'])
        elif len(route) == 1:
            if PortsTable.reverse_mapping[route]:
                Port=PortsTable.reverse_mapping[route][0]
                h_workstation=global_variables.Equipment.h.workstations.get(Port)
                if h_workstation and h_workstation.workstation_type == 'LifterPort':
                    r=collections.deque(['wait', ('wait_port_state', {}), route]) #???
                    g=collections.deque(['W', 'P', 'I'])
        else:
            pass
        return r, g

    def get_post_process(self, route, previous_route=None):
        r=None
        g=None
        pose=tools.get_pose(route)
        if not previous_route:
            process=pose['PostProcess']
            params=pose['PostProcessParam']
            # print('In get_post_process', route, process)
        else:
            detail=Route.h.get_edge_detail(previous_route, route)
            if detail:
                process=detail.get('PostProcess', '')
                params=detail.get('PostProcessParam', {})
            else:
                process=''
                params={}
            # print('In get_post_process', previous_route, route, detail, process)
        # if False: # check what macro is
        #     r=collections.deque(['wait', ('process_name', {'paramkey':'paramval'}), route]) #???
        #     g=collections.deque(['W', 'P', 'I'])
        path_logger.info("process:{}".format(process))
        path_logger.info("params:{}".format(params))
        if global_variables.RackNaming==36:#peter 240705
            if process in macro_list:
                path_logger.debug("get_post_process")
                r=collections.deque(['wait',(process,params),route])
                g=collections.deque(['W', 'P', 'I'])
        elif process == 'close_elevator':
            pose=tools.get_pose(previous_route)
            device_id=pose['group']
            floor=pose.get('floor', global_map_mapping[global_route_mapping[pose['route']]]+1)
            params={'DeviceID':device_id, 'Floor':floor}
            r=collections.deque(['wait', ('move_in_elevator_complete', params), ('elevator_close', params), route]) #???
            g=collections.deque(['W', 'P', 'P', 'I'])
        elif process == "open_gate":
            r = collections.deque([('gate_open', params), 'wait', ('is_gate_opened', params), route]) #???
            g = collections.deque(['P', 'W', 'P', 'I'])
        elif process == "close_gate":
            r = collections.deque(['wait', ('gate_close', params), route]) #???
            g = collections.deque(['W', 'P', 'I'])
        elif process == 'after_Poven':#richard 0219
            print('oven_check',process )
            # pose=tools.get_pose(previous_route)
            # device_id = params
            print('in pre process params:',params)
            r = collections.deque(['wait', ('oven_close', params), ('oven_start', params), route]) 
            g = collections.deque(['W', 'P' ,'P' , 'I'])
        elif process == 'after_Noven':#richard 0219
            print('oven_check',process )
            # pose=tools.get_pose(previous_route)
            # device_id = params
            print('in pre process params:',params)
            r = collections.deque(['wait', ('oven_end', params), ('oven_close', params), ('oven_start', params), route]) 
            g = collections.deque(['W','P','P','P', 'I'])
        else:
            pass
        return r, g

    def process(self):
        if self.current_go_list[0][0] == 'W': # Wait
            self.current_route[0].popleft()
            self.current_go_list[0].popleft()
        elif self.current_go_list[0][0] == 'I': # Info
            self.current_route[0].popleft()
            self.current_go_list[0].popleft()
        elif self.current_go_list[0][0] == 'P': # Process
            process, params=self.current_route[0][0]
            if process == 'change_route': #???
                pose=tools.get_pose(self.current_route[1][0])
                if not self.adapter.route_change(pose['route']):
                    return
            elif process in ['open_door','close_door','pass_door','air_show']:#peter 240705
                
                self.logger.info("self.adapter.vehicle_instance.action_in_run in vrp:{}".format(self.adapter.vehicle_instance.action_in_run))
                self.logger.info("self.adapter.last_point:{}".format(self.adapter.last_point))
                now_action_in_run=self.adapter.vehicle_instance.action_in_run
                now_action_in_run_taget=now_action_in_run.get("target","")
                new_door_action={}
                if self.adapter.last_point in M1_global_variables.oven_door.keys():
                    action_type=params.get("action", "")
                    if action_type == "OPEN":
                        match=re.match(r'^(\w+?)_(O|I)\d+$', now_action_in_run_taget)
                        if match:
                            base=match.group(1)
                            open_correct_door="DOOR_{}".format(base)
                            self.logger.info("open_correct_door:{}".format(open_correct_door))
                            M1_global_variables.oven_door[self.adapter.last_point]=open_correct_door
                            new_door_action={"point": open_correct_door, "action": "OPEN"}
                        else:
                            self.logger.warning("Cannot parse target:{}".format(now_action_in_run_taget))
                            M1_global_variables.oven_door[self.adapter.last_point]=params.get("point", "")
                            new_door_action={"point": params.get("point", ""), "action": "OPEN"}
                    elif action_type == "CLOSE":
                        close_correct_door=M1_global_variables.oven_door.get(self.adapter.last_point,"")
                        if close_correct_door != "":
                            self.logger.info("close_correct_door:{}".format(close_correct_door))
                            new_door_action = {"point": close_correct_door, "action": "CLOSE"}
                        else:
                            new_door_action={"point": params.get("point", ""), "action": "CLOSE"}
                else:
                    new_door_action = {
                        "point": params.get("point", ""),
                        "action": params.get("action", "")
                    }


                self.logger.info("DOOR PROCESS:{},last STATE:{},point:{},pose:{}".format(process,self.adapter.DoorState,new_door_action,self.adapter.move['pose']))
                E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.OpenDoorAcquire,{
                                        'VehicleID':self.id,
                                        'TransferPort':new_door_action.get("point",""),
                                        'DoorState':new_door_action.get("action","")})
                
                for i in range(60):
                    time.sleep(1)

                    resultDoorState=""
                    if params.get("action","") == "OPEN":
                        resultDoorState="{}ED".format(params.get("action",""))
                    elif params.get("action","") == "CLOSE":
                        resultDoorState="{}D".format(params.get("action",""))
                    elif params.get("action","") == "AIRSHOW":#AIRSHOWED
                        resultDoorState="{}ED".format(params.get("action",""))
                    
                    self.logger.info("resultDoorState:{}".format(resultDoorState))
                    self.logger.info("self.adapter.DoorState:{}".format(self.adapter.DoorState))
                    if self.adapter.DoorState == resultDoorState:
                        self.logger.info("DOOR PASS SUCCESS")
                        break
                    elif self.adapter.DoorState == "NG":
                        self.logger.error("MCS REPLY DOOR EVENT NG")
                        self.adapter.DoorState=""
                        self.adapter.move['arrival']='Arrival'
                        self.adapter.move['status']='Idle'
                        self.adapter.alarm['reset']=False
                        self.adapter.alarm['error_code']='TSC031'
                        self.logger.error('{} {} {} {}'.format('[{}] '.format(self.id), 'alarm:', self.adapter.alarm['reset'], self.adapter.alarm['error_code']))
                        # self.update_location(False)
                        self.current_route.clear() # Mike: 2021/03/17
                        self.current_go_list.clear() # Mike: 2021/03/17
                        self.logger.error('{} {}'.format('[{}] '.format(self.id), 'NG do process.'))
                        self.logger.error('{} {} {} {} {}'.format('[     ] ', '\nlocation:', global_variables.global_vehicles_location, '\noccupied route:', global_variables.global_occupied_station))
                        self.is_moving=False
                        self.update_location(False)
                        
                        global_moveout_request[self.id]='' # Mike: 2021/11/12
                        global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                        th=threading.Thread(target=self.clean_right,)
                        th.setDaemon(True)
                        th.start()
                        return 
                else:
                    self.logger.error("DOOR EVENT TIMEOUT")
                    self.adapter.DoorState=""
                    self.adapter.move['arrival']='Arrival'
                    self.adapter.move['status']='Idle'
                    self.adapter.alarm['reset']=False
                    self.adapter.alarm['error_code']='TSC031'
                    self.logger.error('{} {} {} {}'.format('[{}] '.format(self.id), 'alarm:', self.adapter.alarm['reset'], self.adapter.alarm['error_code']))
                    # self.update_location(False)
                    self.current_route.clear() # Mike: 2021/03/17
                    self.current_go_list.clear() # Mike: 2021/03/17
                    self.logger.error('{} {}'.format('[{}] '.format(self.id), 'Time out do process.'))
                    self.logger.error('{} {} {} {} {}'.format('[     ] ', '\nlocation:', global_variables.global_vehicles_location, '\noccupied route:', global_variables.global_occupied_station))
                    self.is_moving=False
                    self.update_location(False)
                    
                    global_moveout_request[self.id]='' # Mike: 2021/11/12
                    global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                    th=threading.Thread(target=self.clean_right,)
                    th.setDaemon(True)
                    th.start()
                    return 

                
                
                
            elif process == 'call_elevator': #???
                pose=tools.get_pose(self.current_route[1][0])
                elv_name=params['DeviceID']
                print('> Call elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    if not h_ELV.call_elv(params['Floor']): # elevator not ready
                        return
            elif process == 'elevator_move': #???
                pose=tools.get_pose(self.current_route[1][0])
                elv_name=params['DeviceID']
                print('> Elevator {} move to {}, {}!'.format(elv_name, global_map_mapping[global_route_mapping[pose['route']]], pose['route']))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    if not h_ELV.go_floor(params['Floor']): # elevator not reach
                        return
            elif process == 'check_elevator_floor': #???
                pose=tools.get_pose(self.current_route[1][0])
                elv_name=params['DeviceID']
                print('> Check elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    if not h_ELV.check_elv(params['Floor']): # elevator not stop
                        return
            elif process == 'elevator_open': #???
                elv_name=params['DeviceID']
                print('> Open elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    if not h_ELV.open_door(): # elevator not open
                        return
            elif process == 'elevator_close': #???
                elv_name=params['DeviceID']
                print('> Close elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    if not h_ELV.close_door(): # elevator not close
                        return
            elif process == 'moving_in_elevator': #???
                elv_name=params['DeviceID']
                print('> Moving in elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    h_ELV.mr_move(True, False)
            elif process == 'moving_out_elevator': #???
                elv_name=params['DeviceID']
                print('> Moving out elevator {}!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    h_ELV.mr_move(False, False)
            elif process == 'move_in_elevator_complete': #???
                elv_name=params['DeviceID']
                print('> Move in elevator {} completed!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    h_ELV.mr_move(True, True)
            elif process == 'move_out_elevator_complete': #???
                elv_name=params['DeviceID']
                print('> Move out elevator {} completed!'.format(elv_name))
                h_ELV=Iot.h.devices.get(elv_name, None)
                # print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_ELV)
                if h_ELV:
                    h_ELV.mr_move(False, True)
            elif process == 'wait_port_state': #???
                print('> wait port!')
                for port in PortsTable.reverse_mapping[self.current_route[0][-1]]:
                    h_workstation=global_variables.Equipment.h.workstations.get(port)
                    if h_workstation and h_workstation.enable and h_workstation.state in ['ReadyToLoad', 'ReadyToUnload']:
                        break
                else:
                    return
                print('> yes!')
            elif process == 'open_door':#peter 240705
                self.logger.info("open_door:{}".format(self.adapter.last_point))
                self.adapter.DoorState="OPEN"
                E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.OpenDoorAcquire,{
                                        'VehicleID':self.id,
                                        'TransferPort':self.adapter.last_point,
                                        'DoorState':self.adapter.DoorState})
                for i in range(60):
                    time.sleep(1)
                    if self.adapter.DoorState == "OPENED":
                        self.logger.info("door_opened:{}".format(self.adapter.last_point))
                        break
                else:
                    self.logger.error("DOORSTATE:{}".self.adapter.DoorState)
                    return
            elif process == 'close_door':#peter 240705
                if self.adapter.DoorState == "OPENED":
                    self.logger.info("close_door:{}".format(self.adapter.last_point))
                    self.adapter.DoorState="CLOSE"
                    E82.report_event(self.adapter.secsgem_e82_h,
                                            E82.OpenDoorAcquire,{
                                            'VehicleID':self.id,
                                            'TransferPort':self.adapter.last_point,
                                            'DoorState':self.adapter.DoorState})
                    for i in range(60):
                        time.sleep(1)
                        if self.adapter.DoorState == "CLOSED":
                            self.logger.info("door_closed:{}".format(self.adapter.last_point))
                            self.adapter.DoorState=""
                            break
                    else:
                        self.logger.error("DOORSTATE:{}".self.adapter.DoorState)
                        return
                else:
                    self.logger.error("DOORSTATE:{}".self.adapter.DoorState)
                    return
            elif process == "is_gate_opened": #YUCHUN
                gate_name = params['DeviceID']
                print('> Query gate status {}!, param {}'.format(gate_name, params))
                h_GATE = Iot.h.devices.get(gate_name, None)
                if h_GATE:
                    if not h_GATE.is_gate_opened(params): # elevator not close
                        return
            elif process == "gate_open":
                gate_name = params['DeviceID']
                print('> Call gate open {}!, param {}'.format(gate_name, params))
                h_GATE = Iot.h.devices.get(gate_name, None)
                if h_GATE:
                    h_GATE.gate_open(params)
            elif process == "gate_close":
                gate_name = params['DeviceID']
                print('> Call gate close {}!, param {}'.format(gate_name, params))
                h_GATE = Iot.h.devices.get(gate_name, None)
                if h_GATE:
                    h_GATE.gate_close(params)
            elif process == 'oven_open': #Richard 250219
                print('oven open check' ,process)
                deviceid = params['DeviceID']
                oven_id = params['OvenID']
                print('> Open oven {} from PLC {}!'.format(oven_id, deviceid))
                h_OVEN = Iot.h.devices.get(deviceid, None)
                print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_OVEN)
                if h_OVEN:
                    if not h_OVEN.open_door(oven_id):   #   call oven id
                        return
            elif process == 'oven_close': #Richard 250219
                print('oven close check' ,process)
                deviceid = params['DeviceID']
                oven_id = params['OvenID']
                print('> Close oven {} from PLC {}!'.format(oven_id, deviceid))
                h_OVEN = Iot.h.devices.get(deviceid, None)
                print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_OVEN)
                if h_OVEN:
                    if not h_OVEN.close_door(oven_id):   #   call oven id
                        return
            elif process == 'oven_start': #Richard 250219
                print('oven start check' ,process)
                deviceid = params['DeviceID']
                oven_id = params['OvenID']
                print('> start oven {} from PLC {}!'.format(oven_id, deviceid))
                h_OVEN = Iot.h.devices.get(deviceid, None)
                print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_OVEN)
                if h_OVEN:
                    if not h_OVEN.oven_start(oven_id):   #   call oven id
                        return
            elif process == 'oven_end': #Richard 250219
                print('oven end check' ,process)
                deviceid = params['DeviceID']
                oven_id = params['OvenID']
                print('> end oven {} from PLC {}!'.format(oven_id, deviceid))
                h_OVEN = Iot.h.devices.get(deviceid, None)
                print(PoseTable.mapping[self.current_route[0][-1]]['group'], ' => ', h_OVEN)
                if h_OVEN:
                    if not h_OVEN.Reset_temperatureController(oven_id):#  call oven id
                        return
            else:
                pass
            self.current_route[0].popleft()
            self.current_go_list[0].popleft()
        else:
            pass
        if not self.current_route[0]:
            self.current_route.popleft()
            self.current_go_list.popleft()
        pass

####################################################
    ''' Enroute '''
    def euclidean_distance(self,x1, y1, x2, y2):#peter 240827
        return (x2 - x1) *(x2 - x1) + (y2 - y1) *(y2 - y1)
    def path_calculate(self, path, ignore_junction=False): # Mike: 2021/08/14
        current_go_list=collections.deque()
        current_route=collections.deque()
        junction_list=collections.deque()
        go_list=[]
        # group_list=[]
        is_last_point_junction=False # Mike: 2021/10/01
        is_last_point_elevator=False
        check=False
        from_index=0
        # Route.h.get_edge_detail(a, path[0])['speed'] ???
        if len(path)>2:
            go_list=['G']
            from_index=1
            pose=PoseTable.mapping[tools.find_point(path[0])]
            # group_list.append(pose['group'])
            P1=[pose['x'], pose['y'], pose['z'], pose['w']]
            if pose['junction']:
                junction_list.append(path[0])
                is_last_point_junction=True
            if pose['PostProcess'] in macro_list:
                current_route.append([path[0]])
                from_index=2
                current_go_list.append(['G'])
                go_list=[]
            pose=PoseTable.mapping[tools.find_point(path[1])]
            # group_list.append(pose['group'])
            P2=[pose['x'], pose['y'], pose['z'], pose['w']]
            if pose['junction']:
                if not is_last_point_junction:
                    junction_list.append(path[1])
                is_last_point_junction=True
            else:
                is_last_point_junction=False
            '''if pose['PreProcess'] and from_index != 1:
                current_route.append(path[from_index:1])
                from_index=2
                current_go_list.append(['G'])
            if pose['PostProcess']:
                current_route.append(path[from_index:2])
                from_index=3
                go_list.append('G')
                current_go_list.append(go_list)
                go_list=[]
                check=True'''

            dist=Route.h.get_path_cost([path[0], path[1]])
            direction=[p_angle(P1, P2), P2[3]-P1[3]]
            P1=P2
            for i in range(1, len(path)-1):
                # print(path[i], go_list)
                # print(current_route, current_go_list)
                is_post_process=check
                pose=tools.get_pose(path[i])
                pose2=tools.get_pose(path[i+1])
                keep_go=pose['go'] # Mike: 2021/07/21
                if pose['junction'] and not ignore_junction: # Mike: 2021/08/13
                    if not is_last_point_junction:
                        junction_list.append(path[i])
                detail=Route.h.get_edge_detail(path[i-1], path[i])
                if pose['PreProcess'] in macro_list or detail and detail.get('PreProcess') in macro_list and len(go_list): # B pre # AB pre
                    # if len(go_list) > 0:
                    current_route.append(path[from_index-1:i])
                    from_index=i+1
                    go_list[-1]='G'
                    current_go_list.append(go_list)
                    go_list=[]
                if pose['PostProcess'] in macro_list or detail and detail.get('PostProcess') in macro_list: # B post # AB post
                    # if len(go_list) > 0:
                    is_post_process=True
                    current_route.append(path[from_index-1:i+1])
                    from_index=i+2
                    go_list.append('G')
                    current_go_list.append(go_list)
                    go_list=[]
                if pose['junction'] and i<len(path)-1 and self.enable_traffic_point and not ignore_junction and not is_last_point_junction: # Mike: 2021/05/04 # Mike: 2021/10/01
                    if i-from_index > 0:
                        # if not (pose['PreProcess'] in macro_list):
                        if not is_post_process:
                            current_route.append(path[from_index-1:i])
                            from_index=i
                            if go_list[-1] == 'K': # Mike: 2021/06/17
                                go_list[-1]='G'
                                current_go_list.append(go_list)
                                go_list=['C']
                            else:
                                go_list[-1]='G'
                                current_go_list.append(go_list)
                                go_list=['K']
                    # P2=PoseTable.mapping[tools.find_point(path[i+1])]
                    # direction=[p_angle(P1, P2), P2[3]-P1[3]]
                    # self.logger.debug(''.format("====== {}".format(i))
                    # self.logger.debug(''.format("name: ", path[i], path[i+1])
                    # self.logger.debug(''.format("P1, P2: ", P1, P2)
                    # self.logger.debug(''.format("Direction: ", direction)
                    # self.logger.debug(''.format("======")
                    # P1=P2
                    # continue
                if pose['junction']: # Mike: 2021/10/01
                    is_last_point_junction=True
                else:
                    is_last_point_junction=False

                pose=PoseTable.mapping[tools.find_point(path[i+1])]
                # group_list.append(pose['group'])
                P2=[pose['x'], pose['y'], pose['z'], pose['w']]
                new_dist=Route.h.get_path_cost([path[i], path[i+1]]) # Mike: 2021/04/20
                new_direction=[p_angle(P1, P2), (P2[3]-P1[3])]
                # self.logger.debug(''.format("====== {}".format(i+1))
                # self.logger.debug(''.format("name: ", path[i], path[i+1])
                # self.logger.debug(''.format("P1, P2: ", P1, P2)
                # self.logger.debug(''.format("Direction: ", direction)
                # self.logger.debug(''.format("New Direction: ", new_direction)
                # self.logger.debug(''.format("======")
                if not is_post_process:
                    angle_diff=abs(new_direction[0]-direction[0]) # Mike: 2021/03/22
                    if angle_diff > 180:
                        angle_diff -= 360
                    '''if dist < 200: # Mike: 2021/04/20
                        go_list.append('K')'''
                    if direction[1] != new_direction[1] or abs(angle_diff) > self.keep_angle or P2[2] != P1[2]:
                        go_list.append('G')
                    else:
                        go_list.append('K')
                P1=P2
                dist=new_dist
                direction=new_direction
                # print(path[i], go_list)
                # print(current_route, current_go_list)
            detail=Route.h.get_edge_detail(path[-2], path[-1])
            if pose['PreProcess'] in macro_list or detail and detail.get('PreProcess') in macro_list and len(go_list): # B pre # AB pre
                # if len(go_list) > 0:
                current_route.append(path[from_index-1:-1])
                from_index=0
                go_list[-1]='G'
                current_go_list.append(go_list)
                go_list=[]
            go_list.append('G')
            current_go_list.append(go_list)
            current_route.append(path[from_index-1:])
        else:
            pose1=PoseTable.mapping[tools.find_point(path[0])]
            pose2=PoseTable.mapping[tools.find_point(path[1])]
            detail=Route.h.get_edge_detail(path[0], path[1])
            if pose1['PostProcess'] in macro_list or pose2['PreProcess'] in macro_list or detail and detail.get('PreProcess') in macro_list:
                current_go_list.append(['G'])
                current_route.append([path[0]])
                current_go_list.append(['G'])
                current_route.append([path[1]])
            else:
                go_list=['G', 'G']
                current_go_list.append(go_list)
                current_route.append(path)
        try:
            Port=PortsTable.reverse_mapping[path[-1]][0]
            h_workstation=global_variables.Equipment.h.workstations.get(Port)
            if h_workstation and h_workstation.workstation_type == 'LifterPort' and self.adapter.vehicle_instance.model != 'Type_T':
                current_go_list.append(['G'])
                current_route.append([path[-1]])
        except:
            pass
        return current_route, current_go_list, junction_list

    def get_right(self): # Mike: 2021/02/18

        self.logger.info('{} {}'.format('[{}] '.format(self.id), 'get_right....'))
        # self.logger.debug(''.format('occupied_route: ', global_variables.global_occupied_station)

        self.is_moving=False
        self.send_block=False
        if self.find_way: # Mike: 2021/04/06
            self.find_way_cnt=0
            self.tic=time.time()
        self.toc=time.time()
        self.find_way=True
        force_find_way=False # Mike: 2021/08/24
        get_route_timeout=False # Mike: 2021/12/21
        dead_lock=time.time() # Mike: 2021/12/21
        block_by_still_car=False
        block_by_mem='' # Mike: 2022/05/04
        block_nodes=[]
        block_group_mem=''
        block_node_mem=''
        at_avoid_node=False # Mike: 2021/05/07
        avoid_node=''
        avoid_node_location=''
        is_junction_avoid=False
        path_mem=[]
        go_list_mem=[]
        global_moveout_request[self.id]='' # Mike: 2021/08/14
        global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
        while self.current_route and not self.thread_stop and self.adapter.is_alive():
            start_run=False
            get_route=True
            path=[]
            go_list=[]
            # global global_variables.global_occupied_lock
            # global global_variables.global_occupied_station
            # if not self.is_moving or len(self.occupied_route)<4:
            goal_diff=0
            if self.occupied_route:
                goal=PoseTable.mapping[self.occupied_route[-1]]
                goal_diff=abs(self.adapter.move['pose']['x']-goal['x'])+abs(self.adapter.move['pose']['y']-goal['y'])
            if self.adapter.online['man_mode'] or self.adapter.alarm['error_code']: #8.25.18-3
                self.current_route.clear() 
                self.current_go_list.clear()
                return
            if not self.adapter.cmd_sending and (not self.is_moving or (goal_diff < global_variables.TSCSettings.get('TrafficControl',{}).get('KeepGoingRange', 4000)) and not is_junction_avoid):
                # self.logger.debug(''.format('[{}] '.format(self.id), 'current_route: ',self.current_route)
                # self.logger.debug(''.format('occupied_route: ', global_variables.global_occupied_station)
                if self.current_go_list[0][0] == 'W' and self.is_moving:
                    pass
                elif self.current_go_list[0][0] not in ['K', 'G', 'C']:
                    self.process()
                elif global_variables.global_occupied_lock.acquire(True):
                    try: # Mike: 2021/07/27
                        # if get_lock(global_variables.global_occupied_lock, self.id, self.toc - self.tic, Route.h.get_path_cost(self.current_route[0])): # Mike: 2021/05/18
                        self.logger.debug('{} {}'.format('[{}] '.format(self.id), 'Get lock')) # Mike: 2021/03/22
                        # print('{} {} {} {}'.format('[{}] '.format(self.id), 'occupied_route: ', global_variables.global_occupied_station, global_variables.global_vehicles_location))
                        global_moveout_request[self.id]='' # Mike: 2021/08/14
                        is_junction_avoid=False
                        global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                        route=self.current_route[0][0]
                        if PoseTable.mapping[route]['AltPointID']:
                            if Route.h.get_edge_detail(route, PoseTable.mapping[route]['AltPointID']) and Route.h.get_edge_detail(PoseTable.mapping[route]['AltPointID'], route):
                                try:
                                    group_list=PoseTable.mapping[PoseTable.mapping[route]['AltPointID']]['group'].split("|")
                                    for group in group_list:
                                        if global_variables.global_occupied_station[group] not in ['', self.id]: # Mike: 2021/04/27
                                            break
                                        if global_variables.global_vehicles_location[group] not in ['', self.id]:
                                            break
                                    else:
                                        avoid_node=PoseTable.mapping[route]['AltPointID']
                                        avoid_node_location=route
                                except KeyError:
                                    avoid_node=PoseTable.mapping[route]['AltPointID']
                                    avoid_node_location=route
                        if self.adapter.fromToOnly:
                            junction_routes=[]
                            junction_go_list=[]
                            is_last_junction=False
                            if len(self.current_route[0]) > 1:
                                for idx, point in enumerate(self.current_route[0][1:-1]):
                                    if PoseTable.mapping[point]['junction']:
                                        if not is_last_junction:
                                            junction_routes.append(point)
                                            junction_go_list.append(self.current_go_list[0][idx+1])
                                        elif PoseTable.mapping[point]['go']:
                                            junction_routes.append(point)
                                            junction_go_list.append(self.current_go_list[0][idx+1])
                                        is_last_junction=True
                                    elif is_last_junction:
                                        is_last_junction=False
                                        junction_routes.append(point)
                                        # junction_go_list.append(self.current_go_list[0][idx+1])
                                        junction_go_list.append('G')
                                    elif PoseTable.mapping[point]['go']:
                                        junction_routes.append(point)
                                        junction_go_list.append(self.current_go_list[0][idx+1])
                                    else:
                                        pass
                                self.current_route[0]=[self.current_route[0][0]]+junction_routes+[self.current_route[0][-1]]
                                self.current_go_list[0]=[self.current_go_list[0][0]]+junction_go_list+[self.current_go_list[0][-1]]
                            self.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'new route:', self.current_route[0], 'new go:', self.current_go_list[0]))
                        routes=self.current_route[0]
                        additional_routes=[]
                        last_point=routes[-1]
                        try:
                            # print(self.current_go_list)
                            for idx in range(len(self.current_go_list)-1):
                                go_list=self.current_go_list[idx+1]
                                if go_list[0] not in ['K', 'G', 'C']:
                                    continue
                                if len(self.current_route[idx+1]) > 1:
                                    point=self.current_route[idx+1][1]
                                    if PoseTable.mapping[point]['junction'] and not PoseTable.mapping[last_point]['junction']:
                                        break
                                else:
                                    point=self.current_route[idx+1][0]
                                    if PoseTable.mapping[point]['junction'] and not PoseTable.mapping[last_point]['junction']:
                                        break
                                additional_routes=additional_routes+self.current_route[idx+1]
                                last_point=self.current_route[idx+1][-1]
                        except:
                            # traceback.print_exc()
                            pass
                        # print(routes, additional_routes)
                        for route in routes[1:]+additional_routes:
                            group_list=PoseTable.mapping[route]['group'].split("|")
                            for group in group_list: # Mike: 2021/04/08
                                try:
                                    if global_variables.global_occupied_station[group] not in ['', self.id]:
                                        if block_group_mem != group:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), 'Blocked at ', [route, group], ' by ', global_variables.global_occupied_station[group])) # Mike: 2021/03/22
                                            block_group_mem=group
                                            block_node_mem=route
                                        elif block_node_mem != route:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), 'Blocked at ', [route, group], ' by ', global_variables.global_occupied_station[group])) # Mike: 2021/03/22
                                            block_node_mem=route
                                        elif block_by_mem and block_by_mem != global_variables.global_occupied_station[group]:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), 'Blocked at ', [route, group], ' by ', global_variables.global_occupied_station[group])) # Mike: 2021/03/22
                                        else:
                                            block_by_still_car=False # Mike: 2021/05/11
                                        block_by_mem=global_variables.global_occupied_station[group] # Mike: 2022/05/04
                                        get_route=False
                                        global_variables.global_plan_route[self.id]=sum(self.current_route,[]) # Mike: 2021/11/12
                                        break
                                except KeyError:
                                    global_variables.global_occupied_station[group]=''
                                try:
                                    if global_variables.global_vehicles_location[group] not in ['', self.id]:
                                        if block_group_mem != group:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), '*Blocked at ', [route, group], ' by ', global_variables.global_vehicles_location[group])) # Mike: 2021/03/22
                                            block_group_mem=group
                                            block_node_mem=route
                                        elif block_group_mem != group:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), '*Blocked at ', [route, group], ' by ', global_variables.global_vehicles_location[group])) # Mike: 2021/03/22
                                            block_node_mem=route
                                        elif block_by_mem and block_by_mem != global_variables.global_vehicles_location[group]:
                                            self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), '*Blocked at ', [route, group], ' by ', global_variables.global_occupied_station[group])) # Mike: 2021/03/22
                                        block_by_mem=global_variables.global_vehicles_location[group] # Mike: 2022/05/04
                                        block_by_still_car=True
                                        get_route=False
                                        global_moveout_request[self.id]=global_variables.global_vehicles_location[group]
                                        global_variables.global_plan_route[self.id]=sum(self.current_route,[]) # Mike: 2021/11/12
                                        break
                                except KeyError:
                                    pass
                            if not get_route:
                                break
                            if PoseTable.mapping[route]['AltPointID']: # Mike: 2021/04/06
                                if Route.h.get_edge_detail(route, PoseTable.mapping[route]['AltPointID']) and Route.h.get_edge_detail(PoseTable.mapping[route]['AltPointID'], route):
                                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'avoid node update: ', PoseTable.mapping[route]['AltPointID']))
                                    try:
                                        group_list=PoseTable.mapping[PoseTable.mapping[route]['AltPointID']]['group'].split("|")
                                        check=True
                                        for group in group_list: # Mike: 2021/04/28
                                            if global_variables.global_occupied_station[group] not in ['', self.id]:
                                                check=False
                                                break
                                            if global_variables.global_vehicles_location[group] not in ['', self.id]:
                                                check=False
                                                break
                                        if check:
                                            avoid_node=PoseTable.mapping[route]['AltPointID']
                                            avoid_node_location=route
                                    except KeyError:
                                        avoid_node=PoseTable.mapping[route]['AltPointID']
                                        avoid_node_location=route
                        # print('{} {} {}'.format('[{}] '.format(self.id), 'avoid node: ', avoid_node))
                        if get_route:
                            self.route_right_lock.acquire(True) # Mike: 2024/01/05
                            self.stop_cmd_lock.acquire(True)
                            if len(self.current_route) == 0 and len(self.current_go_list) == 0: #Yuri 2024/12/1
                                self.route_right_lock.release()
                                self.stop_cmd_lock.release()
                                global_variables.global_occupied_lock.release()
                                self.logger.info('{} {}'.format('[{}] '.format(self.id), 'get_route... but no current route ... release route'))
                                return
                            try:
                                for route in routes+additional_routes: # Mike: 2021/05/11
                                    group_list=PoseTable.mapping[route]['group'].split("|")
                                    for group in group_list:
                                        global_variables.global_occupied_station[group]=self.id
                                        self.last_group_point[group]=route # Mike: 2022/01/19
                                    if route in self.occupied_route:
                                        self.occupied_route.remove(route)
                                    self.occupied_route.append(route)
                                    '''if len(self.occupied_route) == 0 or self.occupied_route[-1] != route:
                                        self.occupied_route.append(route) # Mike: 2021/04/26'''
                            except:
                                pass
                            self.route_right_lock.release()
                            self.stop_cmd_lock.release()
                            self.adapter.move['arrival']=''
                            path=self.current_route.popleft()
                            go_list=self.current_go_list.popleft()
                            # self.occupied_route=list(path) # Mike: 2021/04/21
                            start_run=True
                            at_avoid_node=False
                        else:
                            if self.enable_avoid_node and avoid_node and avoid_node != self.adapter.last_point: # Mike: 2021/04/06
                                if self.adapter.last_point == avoid_node_location: # Mike: 2021/04/12
                                    if not self.is_moving:
                                        self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'go avoid node: ', avoid_node))
                                        avoid_node_location_index=self.current_route[0].index(avoid_node_location)
                                        path=[avoid_node_location, avoid_node]
                                        go_list=['K', 'G']
                                        for route in path: # Mike: 2021/05/07
                                            group_list=PoseTable.mapping[route]['group'].split("|")
                                            for group in group_list: # Mike: 2021/04/27
                                                global_variables.global_occupied_station[group]=self.id
                                                self.last_group_point[group]=route # Mike: 2022/01/19
                                            self.occupied_route.append(route) # Mike: 2021/04/27
                                        self.adapter.move['arrival']=''
                                        self.current_route[0]=[avoid_node] + self.current_route[0]
                                        self.current_go_list[0]=['K', 'G'] + self.current_go_list[0][1:]
                                        at_avoid_node=True
                                        start_run=True
                                        get_route=True
                                else:
                                    if avoid_node_location not in self.occupied_route:
                                        self.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'go avoid node location: ', avoid_node_location))
                                        avoid_node_location_index=self.current_route[0].index(avoid_node_location)
                                        path=self.current_route[0][:avoid_node_location_index+1]
                                        go_list=self.current_go_list[0][:avoid_node_location_index]+['G']
                                        for route in path: # Mike: 2021/04/27
                                            group_list=PoseTable.mapping[route]['group'].split("|")
                                            for group in group_list:
                                                global_variables.global_occupied_station[group]=self.id
                                                self.last_group_point[group]=route # Mike: 2022/01/19
                                            self.occupied_route.append(route) # Mike: 2021/04/27
                                        self.adapter.move['arrival']=''
                                        if self.current_go_list[0][avoid_node_location_index] == 'K':
                                            self.current_route[0]=self.current_route[0][avoid_node_location_index:]
                                            self.current_go_list[0]=['C'] + self.current_go_list[0][avoid_node_location_index+1:]
                                        else:
                                            self.current_route[0]=self.current_route[0][avoid_node_location_index:]
                                            self.current_go_list[0]=['K'] + self.current_go_list[0][avoid_node_location_index+1:]
                                        at_avoid_node=False
                                        start_run=True
                                        get_route=True
                            if self.adapter.junction_list and not get_route and not self.is_moving: # Mike: 2021/08/24
                                check=False
                                check_list=[]
                                check_id=self.id
                                last_check_id=self.id
                                priority=global_variables.global_vehicles_priority.get(self.id, 0)
                                comp_priority=priority
                                while check_id:
                                    last_check_id=check_id
                                    check_list.append(check_id)
                                    check_id=global_moveout_request[check_id]
                                    comp_priority=min(comp_priority, global_variables.global_vehicles_priority.get(check_id, 0))
                                    if check_id in check_list:
                                        if check_id == self.id and priority == comp_priority:
                                            check=True
                                        break

                                junction=''
                                for j in self.adapter.junction_list:
                                    if j in self.current_route[0]:
                                        junction=j
                                        break

                                # print(junction, check_id)
                                if junction and check:
                                    check=False
                                    plan_route_group=[]
                                    for route in global_variables.global_plan_route[last_check_id]: # Mike: 2022/01/17
                                        for group in PoseTable.mapping[route]['group'].split("|"):
                                            plan_route_group.append(group)
                                    neighbor_list=list(global_variables.global_junction_neighbor[junction])
                                    random.shuffle(neighbor_list)
                                    self.logger.info("before_sort")#peter 240827
                                    for neighbor in neighbor_list:
                                        self.logger.info(neighbor)
                                    neighbor_list.sort(key=lambda point: self.euclidean_distance(self.adapter.move['pose']['x'], self.adapter.move['pose']['x'], PoseTable.mapping[point]['x'], PoseTable.mapping[point]['y']))
                                    self.logger.info("after_sort")
                                    for neighbor in neighbor_list:
                                        self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Junction neighbor check:', neighbor)) # Mike: 2022/01/19
                                        group_list=PoseTable.mapping[neighbor]['group'].split("|")
                                        for group in group_list:
                                            try:
                                                if global_variables.global_occupied_station[group] not in [self.id, '']:
                                                    break
                                            except KeyError:
                                                pass
                                            try:
                                                if global_variables.global_vehicles_location[group] not in [self.id, '']:
                                                    break
                                            except KeyError:
                                                pass
                                            try:
                                                if group in plan_route_group:
                                                    break
                                            except KeyError:
                                                pass
                                        else:
                                            '''block_nodes=[]
                                            group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[last_check_id]]['group'].split("|")
                                            for group in group_list:
                                                block_nodes += global_variables.global_group_to_node.get(group, [])'''
                                            block_nodes=[]
                                            for car in global_variables.global_vehicles_location_index: # Mike: 2021/04/06
                                                if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                                                    group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                                                    for group in group_list:
                                                        block_nodes += global_variables.global_group_to_node.get(group, [])
                                            _, avoid_path=Route.h.get_a_route(self.current_route[0][0], neighbor, block_nodes=block_nodes+global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                                            _, back_path=Route.h.get_a_route(neighbor, self.current_route[0][-1], block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                                            print(self.id, neighbor, avoid_path, back_path, block_nodes)
                                            # self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), , neighbor, avoid_path, back_path, block_nodes)) # Mike: 2021/08/24
                                            if avoid_path and back_path and self.current_route[-1][-1] not in avoid_path:
                                                a_route, a_go, _=self.path_calculate(avoid_path, True)
                                                a_route, a_go=self.process_check(a_route, a_go)
                                                b_route, b_go, _=self.path_calculate(back_path, True)
                                                b_route, b_go=self.process_check(b_route, b_go)
                                                self.current_route.appendleft(a_route[0])
                                                self.current_go_list.appendleft(a_go[0])
                                                self.current_route[1]=b_route[0]
                                                self.current_go_list[1]=b_go[0]
                                                if len(self.current_go_list) > 2: #Mike 2022/10/30
                                                    self.current_go_list[2][0]='K'
                                                global_moveout_request[self.id]='' # Mike: 2021/08/14
                                                global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                                                self.adapter.junction_list.remove(junction)
                                                self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'Junction avoid.', self.current_route[0], self.current_route[1])) # Mike: 2021/08/24
                                                check=True
                                                is_junction_avoid=True
                                                break
                                    else: # Mike: 2021/12/21
                                        force_find_way=True
                        avoid_node=''
                        avoid_node_location=''
                        global_variables.global_occupied_lock.release()
                    except Exception as e: # Mike: 2021/07/27
                        global_variables.global_occupied_lock.release()
                        self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 'Exception found: ', traceback.format_exc()))
                    if not get_route:
                        time.sleep(1)
                if start_run:
                    if self.memory_group: # Mike: 2021/02/19
                        for group in self.memory_group.split("|"):
                            if group not in global_variables.global_vehicles_location:
                                global_variables.global_vehicles_location[group]=''
                            if global_variables.global_vehicles_location[group] == self.id:
                                global_variables.global_vehicles_location[group]=''
                                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'clean location 1: ', group))
                        global_variables.global_vehicles_location_index[self.id]='' # Mike: 2021/04/06
                        self.memory_group=''
                    # self.logger.debug(''.format('location: ', global_variables.global_vehicles_location, self.adapter.last_point)
                    path_mem=list(path)
                    go_list_mem=list(go_list)
                    '''th2=threading.Thread(target=self.adapter.move_cmd, args=(path, go_list,))
                    th2.setDaemon(True)
                    th2.start()'''
                    self.is_moving=True
                    if is_junction_avoid == 1:
                        is_junction_avoid=2
                    self.adapter.move_cmd(path, go_list)
                    # self.move_cmd(path, go_list)
                    # self.logger.debug(''.format('[{}] '.format(self.id), 'current_route: ', self.occupied_route)
                    # self.logger.debug(''.format('occupied_route: ', global_variables.global_occupied_station)
                    if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                        E82.report_event(self.adapter.secsgem_e82_h,
                                         E82.VehicleEnterSegment,{
                                         'VehicleID':self.id,
                                         'Routes':str(path)})
                    self.segment_end[path[-1]]=path
            if self.is_moving:
                if self.send_block:
                    E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.VehicleTrafficRelease,{
                                        'VehicleID':self.id})
                self.send_block=False
                time.sleep(1)
                '''if self.adapter.move_cmd_nak and not self.adapter.cmd_sending and path_mem: # Mike: 2021/04/09
                    self.logger.debug('move command nak!')
                    self.current_route.appendleft(path_mem)
                    self.current_go_list.appendleft(go_list_mem)
                    path_mem=[]
                    go_list_mem=[]
                    self.is_moving=False
                    if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                        E82.report_event(self.adapter.secsgem_e82_h,
                                         E82.VehicleExitSegment,{
                                         'VehicleID':self.id,
                                         'Routes':str(path_mem)})'''
                if (self.adapter.move_cmd_nak or self.adapter.move_cmd_reject) and not self.adapter.cmd_sending:
                    if self.adapter.move_cmd_nak:
                        self.logger.debug('move command nak!')
                    if self.adapter.move_cmd_reject:
                        self.logger.debug('move command reject!')
                    '''self.clean_route()
                    th=threading.Thread(target=self.clean_right,)
                    th.setDaemon(True)
                    th.start()'''
                    # self.adapter.vehicle_stop()
                    '''th=threading.Thread(target=self.adapter.vehicle_stop,)
                    th.setDaemon(True)
                    th.start()'''
                    if not self.adapter.vehicle_stop(check_stop=0, check_get_right_th=False):
                        if self.adapter.wait_stop == 1:
                            continue
                        elif self.adapter.wait_stop == 2:
                            self.clean_route()
                    self.is_moving=False
                    self.clean_right(True)
                    if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                        E82.report_event(self.adapter.secsgem_e82_h,
                                         E82.VehicleExitSegment,{
                                         'VehicleID':self.id,
                                         'Routes':str(path_mem)})
                    return
                self.tic=time.time()
                self.find_way=True
                self.find_way_cnt=0
            else:
                if not self.send_block:
                    output('VehicleBlocking', {
                            'VehicleID':self.id,
                            'BlockedBy':block_by_mem, # Mike: 2022/05/04
                            'BlockedByStillCar':block_by_still_car, # Mike: 2022/05/04
                            'BlockedAt':self.adapter.last_point, # Mike: 2022/05/04
                            'VehicleState':self.adapter.vehicle_instance.AgvState})  #chocp add:2022/1/25
                    E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.VehicleTrafficBlocking,{
                                        'VehicleID':self.id})
                    self.send_block=True

                if self.toc - self.tic > self.get_right_timeout+random.randint(0, 20) or get_route_timeout: # Mike: 2021/02/19 # Mike: 2021/12/21
                    self.adapter.move['arrival']='Arrival'
                    self.adapter.move['status']='Idle'
                    self.adapter.alarm['reset']=False
                    self.adapter.alarm['error_code']='900001'
                    self.logger.error('{} {} {} {}'.format('[{}] '.format(self.id), 'alarm:', self.adapter.alarm['reset'], self.adapter.alarm['error_code']))
                    # self.update_location(False)
                    self.current_route.clear() # Mike: 2021/03/17
                    self.current_go_list.clear() # Mike: 2021/03/17
                    self.logger.error('{} {}'.format('[{}] '.format(self.id), 'Get right timeout.'))
                    self.logger.error('{} {} {} {} {}'.format('[     ] ', '\nlocation:', global_variables.global_vehicles_location, '\noccupied route:', global_variables.global_occupied_station))
                    self.is_moving=False
                    self.update_location(False)
                    global_moveout_request[self.id]='' # Mike: 2021/11/12
                    global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                    th=threading.Thread(target=self.clean_right,)
                    th.setDaemon(True)
                    th.start()
                elif (self.toc-self.tic>self.find_way_time*(self.find_way_cnt+1+at_avoid_node*3)) and block_by_still_car and self.enable_find_way and not is_junction_avoid or force_find_way:
                    self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'Find new route.'))
                    
                    check=False
                    check_list=[]
                    check_id=self.id
                    priority=global_variables.global_vehicles_priority.get(self.id, 0)
                    comp_priority=priority
                    while check_id:
                        check_list.append(check_id)
                        check_id=global_moveout_request[check_id]
                        comp_priority=min(comp_priority, global_variables.global_vehicles_priority.get(check_id, 0))
                        if check_id in check_list:
                            if check_id == self.id and priority == comp_priority:
                                check=True
                            break
                    if check:
                        if time.time() - dead_lock > 10:
                            global_moveout_request[self.id]='' # Mike: 2021/11/12
                            global_variables.global_plan_route[self.id]=[] # Mike: 2021/11/12
                            get_route_timeout=True
                    else:
                        dead_lock=time.time()

                    self.find_way=False
                    at_avoid_node=False
                    self.find_way_cnt += 1
                    origin_cost=0
                    for route in self.current_route:
                        origin_cost += Route.h.get_path_cost(route)
                    block_nodes=[]
                    for car in global_variables.global_vehicles_location_index: # Mike: 2021/04/06
                        if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                            group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                            for group in group_list:
                                block_nodes += global_variables.global_group_to_node.get(group, [])
                    new_cost, new_path=Route.h.get_a_route(self.current_route[0][0], self.current_route[-1][-1], block_nodes=block_nodes+global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'origin path: ', self.current_route))
                    self.logger.debug('{} {} {} {} {}'.format('[{}] '.format(self.id), 'new path: ', new_path, 'block: ', block_nodes))
                    self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'Cost(old, new):', origin_cost, new_cost))
                    if new_cost > 0:
                        if new_cost - origin_cost < self.max_find_way_cost: # Mike: 2021/04/06
                            self.is_moving=True # Mike: 2022/05/04
                            self.current_route.clear() # Mike: 2021/03/17
                            self.current_go_list.clear() # Mike: 2021/03/17
                            th3=threading.Thread(target=self.adapter.move_control, args=(new_path,self.adapter.begin,self.adapter.end))
                            th3.setDaemon(True)
                            th3.start()
                            return

                    if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18 and len(self.current_route) == 1: # check stocker check K25
                        h_workstation=global_variables.Equipment.h.workstations.get(self.adapter.vehicle_instance.action_in_run.get('target', ''))
                        if h_workstation and 'Stock' in h_workstation.workstation_type:
                            CommandIDList=[]
                            TransferInfoList=[]
                            for carr in self.adapter.vehicle_instance.bufs_status:
                                if carr['stockID'] not in ['', 'None', 'Unknown', 'PositionError']:
                                    CommandIDList.append(carr['local_tr_cmd'].get('uuid', ''))
                                    TransferInfoList.append({'CarrierID':carr['stockID'], 'SourcePort':carr['local_tr_cmd'].get('source', ''), 'DestPort':carr['local_tr_cmd'].get('dest', '')})

                            ## get data
                            E82.report_event(self.adapter.secsgem_e82_h,
                                             E82.VehicleRouteFailed,{
                                             'VehicleID':self.id,
                                             'CommandIDList':CommandIDList,
                                             'TransferInfoList':TransferInfoList})

                self.toc=time.time()
                #time.sleep(0.1) # Mike: 2021/04/12
                time.sleep(random.uniform(0.1, 0.3)) # Mike: 2021/04/12
        return

    def clean_route(self): # Mike: 2021/08/02
        while True:
            if global_variables.global_occupied_lock.acquire(True):
                self.current_route.clear()
                self.current_go_list.clear()
                global_variables.global_occupied_lock.release()
                break

    def clean_right(self, wait_update=False): # Mike: 2021/02/18

        # Mike: 2021/03/17
        '''if wait_update:
            while not self.is_update_location:
                time.sleep(0.5)'''

        if self.occupied_route:
            self.adapter.last_alarm_point=self.occupied_route[0]

        if wait_update:
            self.adapter.new_data=False # Mike: 2021/03/28
        self.update_location(wait_update)

        self.logger.info('{} {}'.format('[{}] '.format(self.id), 'clean_right....'))

        if self.occupied_route:
            # global global_occupied_station
            for route in self.occupied_route:
                group_list=PoseTable.mapping[route]['group'].split("|")
                for group in group_list:
                    global_variables.global_occupied_station[group]=''
            self.occupied_route=[]
            global_moveout_request[self.id]='' # Mike: 2022/05/17
            global_variables.global_plan_route[self.id]=[] # Mike: 2022/05/17
            # self.logger.debug(''.format('current_route: ', self.occupied_route)
            # self.logger.debug(''.format('occupied_route: ', global_variables.global_occupied_station)

        #for test
        output('VehicleRoutesUpdate', {
                'VehicleID':self.id,
                'VehicleState':self.adapter.vehicle_instance.AgvState,
                'Routes':self.occupied_route })

        return

    def clean_path(self, station=''): # Mike: 2021/03/04

        '''if not self.is_moving: # Mike: 2021/08/14
            return'''
        if station:
            P=station
        else:
            try:
                P=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']], find_nearest=False)[0]
            except IndexError:
                P=''
        index=-1
        try:
            index=self.occupied_route.index(P)
            if self.occupied_route[index+1] == P: # Mike: 2021/06/08
                self.occupied_route.remove(P) # Mike: 2022/01/20
        except ValueError:
            pass
        except IndexError:
            pass
        self.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), P, index, self.occupied_route))
        if P:
            if P != self.adapter.last_point:
                if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 3:
                    E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.VehicleLocationReport,{
                                        'VehicleID':self.id,
                                        'VehiclePose':'({},{},{},{})'.format(self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['h'], self.adapter.move['pose']['z']),
                                        'PointID':P})
            self.adapter.last_point=P
        # self.logger.debug(''.format('location: ', global_variables.global_vehicles_location)

        self.route_right_lock.acquire(True) # Mike: 2024/01/05
        try:
            if index >= 0:
                for i in range(index+(index == (len(self.occupied_route)-1))):
                    route=self.occupied_route[i]
                    if route in self.occupied_route[i+1:]:
                        continue
                    group_list=PoseTable.mapping[route]['group'].split("|")
                    try:
                        if route in self.segment_end and global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                            E82.report_event(self.adapter.secsgem_e82_h,
                                            E82.VehicleExitSegment,{
                                            'VehicleID':self.id,
                                            'Routes':str(self.segment_end[route])})
                            del self.segment_end[route]
                        if route == self.occupied_route[-1]: # Mike: 2022/01/20
                            self.adapter.last_point=self.occupied_route[-1]
                            self.update_location(False)
                            for group in group_list:
                                global_variables.global_occupied_station[group]=''
                                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), '*Release:', group))
                            index += 1
                        else:
                            for group in group_list:
                                if group in self.last_group_point and self.last_group_point[group] in self.occupied_route: # Mike: 2022/01/19
                                    if route == self.last_group_point[group]:
                                        global_variables.global_occupied_station[group]=''
                                        self.last_group_point[group]=''
                                        self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Release:', group))
                                elif group not in PoseTable.mapping[self.occupied_route[1]]['group'].split("|"):
                                    global_variables.global_occupied_station[group]=''
                                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Release:', group))
                                else:
                                    pass
                    except IndexError:
                        self.adapter.last_point=self.occupied_route[-1]
                        self.update_location(False)
                        for group in group_list:
                            global_variables.global_occupied_station[group]=''
                            self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), '*Release:', group))
                        index += 1 # Mike: 2021/03/08
                self.occupied_route=self.occupied_route[index:]
            else:
                if len(self.occupied_route) > 1 and self.release_right_base_on_location:
                    pose=PoseTable.mapping[self.occupied_route[0]]
                    p_route0=[pose['x'], pose['y'], pose['z'], pose['w']]
                    pose=PoseTable.mapping[self.occupied_route[1]]
                    p_route1=[pose['x'], pose['y'], pose['z'], pose['w']]
                    check=True
                    is_vtheta=not (p_route0[3] == p_route1[3])
                    if not is_vtheta: # Mike: 2021/04/06
                        '''dist_r=Route.h.get_path_cost(self.occupied_route[:2])
                        cos_r=(p_route1[0]-p_route0[0])/dist_r
                        sin_r=(p_route1[1]-p_route0[1])/dist_r
                        p_relative=[self.move['pose']['x']-p_route0[0], self.move['pose']['y']-p_route0[1]]
                        p_trans=[p_relative[0]*cos_r-p_relative[1]*sin_r, p_relative[0]*sin_r+p_relative[1]*cos_r]
                        if p_trans[0] < 200:
                            check=False'''

                        p_now=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
                        distance2=((p_now[0]-p_route0[0])**2 + (p_now[1]-p_route0[1])**2)
                        # self.logger.debug(''.format('[{}] '.format(self.id), 'distance2', distance2)
                        if distance2 < 1500**2:
                            check=False
                        else:
                            angle=abs(p_angle(p_route0, p_now)-p_angle(p_route1, p_now))
                            # self.logger.debug(''.format('[{}] '.format(self.id), 'angle:', angle)
                            if angle > 180:
                                angle=360 - angle
                            if angle < 90:
                                angle=abs(p_angle(p_route0, p_route1)-p_angle(p_route1, p_now))
                                # self.logger.debug(''.format('[{}] '.format(self.id), '*angle:', angle)
                                if angle > 180:
                                    angle=360 - angle
                                if angle > 15:
                                    check=False
                    else:
                        check=False
                    # self.logger.debug(''.format('[{}] '.format(self.id), 'Check:', check)

                    if check:
                        route=self.occupied_route[0]
                        group_list=PoseTable.mapping[route]['group'].split("|")
                        try:
                            if route == self.occupied_route[-1]: # Mike: 2022/01/20
                                self.adapter.last_point=self.occupied_route[-1]
                                self.update_location(False)
                                for group in group_list:
                                    global_variables.global_occupied_station[group]=''
                                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), '*Release:', group))
                                index += 1
                            else:
                                for group in group_list:
                                    if group in self.last_group_point and self.last_group_point[group] in self.occupied_route: # Mike: 2022/01/19
                                        if route == self.last_group_point[group]:
                                            global_variables.global_occupied_station[group]=''
                                            self.last_group_point[group]=''
                                            self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Release:', group))
                                    elif group not in PoseTable.mapping[self.occupied_route[1]]['group'].split("|"):
                                        global_variables.global_occupied_station[group]=''
                                        self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'Release:', group))
                                    else:
                                        pass
                        except IndexError:
                            self.adapter.last_point=self.occupied_route[-1]
                            self.update_location(False)
                            for group in group_list:
                                global_variables.global_occupied_station[group]=''
                                self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), '*Release:', group))
                            index += 1 # Mike: 2021/03/08
                        self.occupied_route.remove(route)
        except:
            self.logger.warning('{} {} {}'.format('[{}] '.format(self.id), 'Exception found: ', traceback.format_exc()))
        self.route_right_lock.release() # Mike: 2024/01/05

        # print('{} {} {} {}'.format('[{}] '.format(self.id), 'occupied_route: ', global_variables.global_occupied_station, global_variables.global_vehicles_location))
        #for test

        if self.adapter.last_point and self.adapter.last_point in PoseTable.mapping:
            self.adapter.move['pose']['z']=PoseTable.mapping[self.adapter.last_point]['z']

        output('VehicleRoutesUpdate', {
                'VehicleID':self.id,
                'VehicleState':self.adapter.vehicle_instance.AgvState,
                'Routes':self.occupied_route })

    def update_location(self, use_new_data, allow_no_point=False, max_dist=100, check_head=True): # Mike: 2021/02/18 # Mike: 2022/02/08 # Mike: 2022/02/25

        self.logger.debug('{} {}'.format('[{}] '.format(self.id), 'update_location....'))

        if use_new_data:
            for i in range(100): # Mike: 2021/04/19
                if self.adapter.new_data:
                    break
                if not self.adapter.online['connected']:
                    return
                time.sleep(0.5)
            else:
                return

            at_point=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']], find_nearest=not allow_no_point, max_dist=max_dist, check_head=check_head)[0] # Mike: 2022/02/25
            if at_point and self.adapter.last_point != at_point:
                if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 3:
                    E82.report_event(self.adapter.secsgem_e82_h,
                                        E82.VehicleLocationReport,{
                                        'VehicleID':self.id,
                                        'VehiclePose':'({},{},{},{})'.format(self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['h'], self.adapter.move['pose']['z']),
                                        'PointID':at_point})
            self.adapter.last_point=at_point

        if not self.adapter.last_point and self.adapter.last_alarm_point:
            self.adapter.last_point=self.adapter.last_alarm_point

        if self.adapter.last_point and self.adapter.last_point in PoseTable.mapping: # Mike: 2022/02/10
            group_list=PoseTable.mapping[self.adapter.last_point]['group'].split("|")
            for group in group_list:
                    # global_variables.global_vehicles_location[group]=self.id
                    # self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'update location: ', group))
                # global_variables.global_vehicles_location_index[self.id]=self.adapter.last_point # Mike: 2021/04/06
                if self.thread_stop:
                    self.logger.debug('{} {}'.format('[{}] '.format(self.id), 'stop thread, do not update location'))
                else:
                    global_variables.global_vehicles_location[group] = self.id
                    self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'update location: ', group))
            if self.thread_stop:
                pass
            else:
                global_variables.global_vehicles_location_index[self.id] = self.adapter.last_point # Mike: 2021/04/06
            if self.memory_group:
                for group in self.memory_group.split("|"):
                    if group not in global_variables.global_vehicles_location:
                        global_variables.global_vehicles_location[group]=''
                    if global_variables.global_vehicles_location[group] == self.id and group not in group_list:
                        global_variables.global_vehicles_location[group]=''
                        self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'clean location 2: ', group))
            self.memory_group=PoseTable.mapping[self.adapter.last_point]['group']
            if self.adapter.last_alarm_point and self.adapter.last_alarm_point != self.adapter.last_point:
                self.adapter.last_alarm_point=''
        elif allow_no_point:
            at_point=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']], max_dist=max_dist, check_head=check_head)[0] # Mike: 2022/02/25
            self.adapter.last_point=at_point
            group_list=PoseTable.mapping[self.adapter.last_point]['group'].split("|") if at_point else []
            if self.memory_group:
                for group in self.memory_group.split("|"):
                    if group not in global_variables.global_vehicles_location:
                        global_variables.global_vehicles_location[group]=''
                    if global_variables.global_vehicles_location[group] == self.id and group not in group_list:
                        global_variables.global_vehicles_location[group]=''
                        self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'clean location 3: ', group))
                global_variables.global_vehicles_location_index[self.id]='' # Mike: 2021/04/06
            self.memory_group=PoseTable.mapping[self.adapter.last_point]['group'] if at_point else ''
        else:
            pass
        # print('{} last point:{}, pose:({}, {}, {})'.format(time.time(), self.adapter.last_point, self.move['pose']['x'], self.move['pose']['y'], self.move['pose']['h']))

        if self.adapter.last_point and self.adapter.last_point in PoseTable.mapping:
            self.adapter.move['pose']['z']=PoseTable.mapping[self.adapter.last_point]['z']

        #self.logger.debug(''.format('location: ', global_variables.global_vehicles_location)

        #for test
        output('VehicleRoutesUpdate', {
                'VehicleID':self.id,
                'VehicleState':self.adapter.vehicle_instance.AgvState,
                'Routes':self.occupied_route })

        return

####################################################
    ''' Main loop '''
    #for thread
    def run(self):
        while not self.thread_stop and self.adapter.is_alive():
            time.sleep(1)
        else:
            # Mike: 2021/11/24
            if self.get_right_th:
                self.get_right_th.join()
            self.current_route.clear()
            self.current_go_list.clear()
            self.clean_right(False)
            if self.adapter.last_point:
                if self.memory_group:
                    for group in self.memory_group.split("|"):
                        if group not in global_variables.global_vehicles_location:
                            global_variables.global_vehicles_location[group]=''
                        if global_variables.global_vehicles_location[group] == self.id:
                            global_variables.global_vehicles_location[group]=''
                            self.logger.debug('{} {} {}'.format('[{}] '.format(self.id), 'clean location 4', group))
                    global_variables.global_vehicles_location_index[self.id]=''
            self.logger.warning('{} {}'.format('[{}] '.format(self.id), 'stop vehicle route planner thread'))


