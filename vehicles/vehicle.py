import collections
import traceback
import threading
import time
import datetime
import vehicles.vehicleAdapter as adapterMR
import re
import copy

import tools

import alarms
import global_variables
from workstation.eq_mgr import EqMgr

#Erack.h
from global_variables import Erack

import algorithm.schedule_by_lowest_cost as schedule_by_lowest_cost
#for oven process
import algorithm.schedule_by_fix_order as schedule_by_fix_order
import algorithm.schedule_by_priority as schedule_by_priority
import algorithm.schedule_by_auto_order as schedule_by_auto_order
import algorithm.schedule_by_better_cost as schedule_by_better_cost
import algorithm.schedule_by_mix_lowest_cost_priority as schedule_by_mix_lowest_cost_priority
import algorithm.schedule_by_point_cost as schedule_by_point_cost
import semi.e82_equipment as E82

from global_variables import PortsTable
from global_variables import PoseTable
from global_variables import Route

from global_variables import Iot
from global_variables import output
from global_variables import SaveStockerInDestPortByVehicleId #K25
from global_variables import SaveK11_AMR_STATUS #K11 kelvinng 202503035
from global_variables import M1_global_variables #K11 kelvinng 202503035

from alarms import get_sub_error_msg

import math
from pprint import pformat

from tr_wq_lib import TransferWaitQueue #for StockOut
import json
import requests
#from web_service_log import * 


#['Unknown','Removed','Unassigned','Enroute','Parked','Acquiring','Depositing','Pause','TrLoadReq','TrUnloadReq']

Max_Buffer_Num=16

class Vehicle(threading.Thread):

    def __init__(self, VehicleMgr, secsgem_e82_h, setting):

        self.secsgem_e82_h=secsgem_e82_h

        self.token=threading.Lock()


        self.vehicle_bufID=['BUF{:02d}'.format(i+1) for i in range(Max_Buffer_Num)]
        self.enableBuffer=['yes' for i in range(Max_Buffer_Num)] #chocp add 2022/1/5

        self.last_bufs_status=[{'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}} for i in range(Max_Buffer_Num)]
        
        self.bufs_status=[{'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False} for i in range(Max_Buffer_Num)]

        self.bufNum=4 #need check
        self.carrier_status_list=[] #chocp 2022/8/30

        self.connect_retry=3
        self.priority=0

        self.update_params(setting)

        self.next_buf_idx=-1

        self.inhibit=False
        self.manual=False #chocp:2021/3/9

        #self.auto_assign_dest=''
        self.recovery_cmd=False #chocp 2021/10/30
        self.charge_cmd=False
        self.force_charge=False
        self.tr_cmds=[]
        self.CommandIDList=[]

        self.actions=collections.deque()
        self.use_schedule_algo='by_lowest_cost'
        self.with_buf_contrain_batch=True



        self.action_in_run={}
        self.host_call_params={}
        self.last_action_is_for_workstation=False #8.21H-4
        self.last_action_eqID=""#BAGUIO TI WB kelvinng
        self.wq=None #8.21H-4
        self.old_point="" #Yuri 2024/12/18

        self.robot_timeout=200 #chocp 2022/4/22
        self.call_support_delay=0
        self.call_support_time=0

        self.tr_cmd_assign_timeout=0 #chocp 8/21
        self.ExpectedDurationExpiredTime=0
        self.TrLoadReqTime=0
        self.TrUnLoadReqTime=0
        self.TrSwapReqTime=0
        self.TrShiftReqTime=0
        self.ValidInputLastReqTime=0

        self.TrBackReqTime=0
        self.charge_start_time=0
        self.charging_schedule=300
        self.enter_charging_schedule=0
        self.enter_unassigned_state_time=0
        self.enter_acquiring_state_time=0
        self.enter_depositing_state_time=0
        self.enter_swapping_state_time=0
        self.host_call_waiting_time=0
        self.enter_host_call_waiting_time=0
        self.enter_wait_eq_operation_time=0 #for renesas WB 


        self.tr_assert={}
        self.input_cmd_open=False #for K25
        self.input_cmd_open_again=False #for K25
        self.wait_eq_operation=False #for renesas WB 

        #self.AgvNextState='Removed'
        self.doPreDispatchCmd=False #for StockOut
        self.assignable=False # for preDispatch
        self.waiting_run=False
        self.stop_command=False
        self.change_target=False
        self.wait_stop=False
        self.no_begin=False
        self.findchargestation=False #chi 2022/11/18
        self.findstandbystation=False
        self.tr_back_req=False #chi 2023/03/15
        self.tr_back_timeout=False
        self.one_buf_for_swap=False #8.27.8
        self.host_call_cmd=False
        self.emergency_evacuation_cmd=False
        self.emergency_situation=''
        self.emergency_evacuation_stop=False
        self.tsc_paused=False
        
        self.ControlPhase='GoTransfer' #GoTransfer, GoRecovery, #GoCharge, #GoStandby
        self.AgvLastState='Removed'
        self.LastAcquireTarget=''
        self.host_call_target=''
        
        self.AgvState='Removed'
        self.AgvSubState=''
        self.at_station=''

        self.message='Start up ...'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''
        self.wait_error_code=0 # Mike: 2023/04/28

        self.error_txt=''

        self.error_reset_cmd=False
        self.error_retry_cmd=False
        self.error_skip_tr_req=False
        self.tr_assert_result=''
        self.host_stop=False #chi 2023/03/15
        #self.ResultCode=0

        #self.exception_deque=collections.deque(maxlen=1)
        self.alarm_node=[]
        self.alarm_edge=[]
        self.alsv=[]

        self.h_eRackMgr=Erack.h

        self.h_vehicleMgr=VehicleMgr.getInstance() #chocp add 2021/10/14

        self.adapter=0
        
        self.go_to_vcs=False
        self.NewEQ=""
        self.OldEQ=""

        output('VehicleInit', {
            'VehicleID':self.id,
            'Pose':[0, 0, 0, -1],              
            'TransferTask':{'VehicleID':self.id, 'Action':'', 'CommandID':'', 'CarrierID':'', 'Dest':'', 'ToPoint':''},
            'VehicleState':'Removed',
            'ForceCharge':self.force_charge,
            'Message':'',
            'Point':'',
            'Station':'',
            'Battery':0,
            'Charge':False, #chocp 2022/5/20
            'Connected':False, # Mike: 2022/05/31
            'Health':'',
            'MoveStatus':'',
            'RobotStatus':'',
            'RobotAtHome':'',
            'AlarmCode':0
            })

        output('CarrierRemoved', {
            'VehicleID':self.id,
            'CommandID':'', #chocp add 10/30
            'Carriers':self.carrier_status_list #chocp 2022/8/30
            })

        output('VehiclePoseUpdate',{
            'VehicleID':self.id,
            'Pose':[0, 0, 0, -1],
            'Message':'',
            'ForceCharge':self.force_charge, #???
            'Point':'',
            'Station':'',
            'Battery':0,
            'Charge':False, #chocp 2022/5/20
            'Connected':False, # Mike: 2022/05/31
            'Health':'',
            'MoveStatus':'',
            'RobotStatus':'',
            'RobotAtHome':'',
            'AlarmCode':0,
            'Speed':0
            })

        # Mike: 2021/05/14
        VehicleInfo={"VehicleInfo":{"VehicleID": self.id, "VehicleState": 0, "SOH":100}}
        ActiveVehicles=E82.get_variables(self.secsgem_e82_h, 'ActiveVehicles')
        ActiveVehicles[self.id]=VehicleInfo
        E82.update_variables(self.secsgem_e82_h, {'ActiveVehicles': ActiveVehicles})
        
        EnhancedALID={'ALID':'', 'AlarmText':'','UnitInfo':{"VehicleID": self.id, "VehicleState": 0}}
        AlarmsSetDescription=E82.get_variables(self.secsgem_e82_h, 'AlarmsSetDescription')
        AlarmsSetDescription[self.id]=EnhancedALID
        E82.update_variables(self.secsgem_e82_h, {'AlarmsSetDescription': AlarmsSetDescription})

        self.adapter=adapterMR.Adapter(self.secsgem_e82_h, self, self.id, self.ip, self.port, self.max_speed, self.connect_retry) #vehicle_instance=self

        self.update_params(setting)

        self.heart_beat=0
        self.thread_stop=False
        threading.Thread.__init__(self)
        return

    def update_params(self, setting):

        self.id=setting['vehicleID']
        self.ip=setting['ip']
        self.port=setting['port']

        serviceZone=[]
        for raw_zone in setting.get('serviceZone', '').split(','):
            serviceZone.append(raw_zone.strip().split('|')) #chocp 9/10
        if len(serviceZone) == 1:
            serviceZone.append('')
        self.serviceZone=serviceZone

        # print('{} service zone list: {}'.format(self.id, self.serviceZone))

        #self.fault_erack=setting.get('faultErack', '')
        self.load_fault_erack=setting.get('loadFaultErack', '')
        self.unload_fault_erack=setting.get('unloadFaultErack', '')

        self.max_speed=setting['speed_limit']
        try:
            self.adapter.max_speed=setting['speed_limit'] # Mike: 2022/01/19
        except:
            pass

        self.model=setting['model'] #chocp add 2022/1/5

        if self.model == 'Type_B': #new for >8 slot begin
            self.bufNum=2
            self.vehicle_onTopBufs=['BUF01', 'BUF02']

        elif self.model == 'Type_C':
            self.bufNum=6
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06']

        elif self.model == 'Type_D':
            self.bufNum=8
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF05', 'BUF06']

        elif self.model == 'Type_E':
            self.bufNum=12
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06', 'BUF07', 'BUF08', 'BUF09', 'BUF10', 'BUF11', 'BUF12']

        elif self.model == 'Type_L':
            self.bufNum=1
            self.vehicle_onTopBufs=['BUF01']
            
        elif self.model == 'Type_F':
            self.bufNum=3
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03']
            
        elif self.model == 'Type_G':
            self.bufNum=16
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06', 'BUF07', 'BUF08', 'BUF09', 'BUF10', 'BUF11', 'BUF12', 'BUF13', 'BUF14', 'BUF15', 'BUF16']
            
        elif self.model == 'Type_H':
            self.bufNum=10
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06', 'BUF07', 'BUF08', 'BUF09', 'BUF10']
            
        elif self.model == 'Type_I':
            self.bufNum=1
            self.vehicle_onTopBufs=['BUF01']
            
        elif self.model == 'Type_J':
            self.bufNum=12
            self.vehicle_onTopBufs=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06', 'BUF07', 'BUF08', 'BUF09', 'BUF10', 'BUF11', 'BUF12']

        else:
            self.bufNum=4 
            self.vehicle_onTopBufs=['BUF01', 'BUF03']

        self.vehicle_bufID=['BUF{:02d}'.format(i+1) for i in range(self.bufNum)]

        self.carrier_status_list=[] #for >8 slot
        self.dynamicBufferMapping={}
        self.LastdynamicBufferMapping={}
        for i in range(self.bufNum):
            self.carrier_status_list.append('Unknown') #chocp 2022/8/30
            self.dynamicBufferMapping[self.vehicle_bufID[i]]='All'
            if global_variables.RackNaming == 42 and i in [0,1]:
                self.dynamicBufferMapping[self.vehicle_bufID[i]]='TRAY'

        self.enableBuffer=setting.get('enableBuffer', []) #chocp add 2022/1/5       
        self.enable_begin_flag=setting.get('enableBeginFlag', 'no')
        print('We get model:{}, bufNum:{}, begin flag:{}'.format(self.model, self.bufNum, self.enable_begin_flag))

        self.appendTransferAllowed=setting.get('appendTransferAllowed', 'no')
        self.appendTransferAlgo=setting.get('appendTransferAlgo','appendTransfer') # default='appendTransfer'  option='appendTransferMovePath' or 'appendTransferMoving'
        global_variables.global_vehicles_priority[self.id]=setting.get('priority', 0)
        self.priority=setting.get('priority', 0)

        charge_station=[]
        try:
            charge_station=setting['chargeStation'].strip(',').split(',')
        except:
            pass
        self.charge_station=charge_station

        standby_station=[] #chocp 2021/10/25
        try:
            standby_station=setting['standbyStation'].strip(',').split(',')
        except:
            pass
        self.standby_station=standby_station
                
        evacuate_station=[] #chocp 2021/10/25
        try:
            evacuate_station=setting['evacuateStation'].strip(',').split(',')
            if not evacuate_station[0] and standby_station:
                evacuate_station=standby_station
        except:
            pass
        self.evacuate_station=evacuate_station

        print('{} standby_station init: '.format(self.id), self.standby_station)
        self.bufferDirection={}
        try:
            buffer_direction = setting.get("bufferDirection", {})
            if buffer_direction:
                for direction, values in buffer_direction.items():
                    self.bufferDirection[direction] = ["BUF%02d" % num for num in values]
        except:
            pass

        #charge
        self.ChargeAuto=setting.get('Charge', {}).get('Auto', 'yes')
        self.EveryRound=setting.get('Charge', {}).get('EveryRound', 'yes')
        self.ChargeWhenIdle=setting.get('Charge', {}).get('ChargeWhenIdle', 'yes')
        self.MinimumChargeTime=int(setting.get('Charge', {}).get('MinimumChargeTime', 10))
        self.IntoIdleTime=int(setting.get('Charge', {}).get('IntoIdleTime', 10))
        self.ChargeBelowPower=int(setting.get('Charge', {}).get('ChargeBelowPower', 30))
        self.BatteryHighLevel=int(setting.get('Charge', {}).get('BatteryHighLevel', 90))   
        self.RunAfterMinimumPower=int(setting.get('Charge', {}).get('RunAfterMinimumPower', 50))
        self.EnableScheduleCharging=setting.get('Charge', {}).get('EnableScheduleCharging', 'no')
        ScheduleChargingTime=[]

        try:
            ScheduleChargingTime=setting.get('Charge', {}).get('ScheduleChargingTime', '').strip(',').split(',')
        except:
            pass

        self.ScheduleChargingTime=ScheduleChargingTime

        #park algo
        self.ParkWhenStandby=setting.get('Park', {}).get('ParkWhenStandby', 'yes')
        self.IntoStandbyTime=int(setting.get('Park', {}).get('IntoStandbyTime', 10))

        self.warningBlockTime=int(setting.get('Route', {}).get('warningBlockTime', 180))
        self.autoReroute=setting.get('Route', {}).get('autoRerouting', 'no')

        self.robot_timeout=int(setting.get('RobotTimeout', 200)) #chocp 2022/4/12
        self.call_support_delay=int(setting.get('CallSupportDelay', 0)) #chocp 2022/4/12

        self.defaultFloor=int(setting.get('defaultFloor', 0)) # Mike: 2022/08/24


        self.ChargeTimeMax=int(setting.get('Charge', {}).get('ChargeTimeMax', 7200)) #chi 2023/02/09
        self.ChargeSafetyCheck=setting.get('Charge', {}).get('ChargeSafetyCheck', 'no')
        # Mike: 2022/04/18
        self.connect_retry=setting['connect_retry']
        try:
            self.adapter.retry_count_limit=self.connect_retry
            self.adapter.fromToOnly=setting.get('Route', {}).get('fromToOnly', 'no') == 'yes'
        except:
            pass
        self.check_carrier_type=setting.get('carrierTypeCheck', 'no')
        self.carriertypedict={}
        try:
            bufferType=setting.get('bufferType', [])
            if bufferType:
                for i in range(len(self.vehicle_bufID)):        
                    self.carriertypedict[self.vehicle_bufID[i]]=bufferType[i].split('|')

        except:
            pass

    def update_dynamic_buffer_mapping(self, idx, state):
        
        buffer_pairs={
            "BUF01": "BUF02",
            "BUF02": "BUF01",
            "BUF03": "BUF04",
            "BUF04": "BUF03",
            "BUF05": "BUF06",
            "BUF06": "BUF05"
        }

        buf_id=self.vehicle_bufID[idx]
        if buf_id in ["BUF01", "BUF02"]:
            return

        if buf_id in self.dynamicBufferMapping:
            paired_buf=buffer_pairs.get(buf_id) 
            
            if paired_buf:
                paired_idx=self.vehicle_bufID.index(paired_buf)
                
            if self.bufs_status[idx]['stockID'] =='None' and self.bufs_status[paired_idx]['stockID'] =='None':
                if self.actions:
                    for action in self.actions:
                        if action['loc'] in [buf_id, paired_buf] and action != self.action_in_run:
                            return
                self.dynamicBufferMapping[buf_id]="All"
                if paired_buf:
                    self.dynamicBufferMapping[paired_buf]="All"
            if state != 'Empty':
                self.dynamicBufferMapping[buf_id]=state
                if paired_buf:
                    self.dynamicBufferMapping[paired_buf]=state
                print("Updated {} and {} to state: {}".format(buf_id, paired_buf, state))
        else:
            print("Buffer ID {} not found in dynamicBufferMapping.".format(buf_id))
        if self.dynamicBufferMapping != self.LastdynamicBufferMapping:
            self.adapter.logger.info("Updated dynamicBufferMapping {}".format(self.dynamicBufferMapping))
            self.LastdynamicBufferMapping = copy.deepcopy(self.dynamicBufferMapping)

    def query_vehicle_state(self):
        pass

    def add_executing_transfer_queue(self, local_tr_cmd):

        #need check source, notify eRack machine
        #need check dest, notify eRack book flags
        #if book unavailable need set alarm
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        output('TransferExecuteQueueAdd', {
                    'VehicleID':self.id,
                    'CommandID':uuid,
                    'CarrierID':carrierID,
                    'Loc':local_tr_cmd.get('loc', ''),
                    'CarrierType':local_tr_cmd.get('TransferInfo', {}).get('CarrierType', ''), #chocp 2022/2/24
                    'Source':local_tr_cmd['source'],
                    'Dest':local_tr_cmd['dest'],
                    'Priority':local_tr_cmd['priority'],
                    'OperatorID':local_tr_cmd.get('host_tr_cmd', {}).get('operatorID', '')
                    }, True)
        self.tr_cmds.append(local_tr_cmd)
        self.tr_cmd_assign_timeout=0

        # Mike: 2022/12/02
        try:
            ActiveTransfers=E82.get_variables(self.secsgem_e82_h, 'ActiveTransfers')
            ActiveTransfers[uuid]['CommandInfo']['TransferState']=2
            E82.update_variables(self.secsgem_e82_h, {'ActiveTransfers': ActiveTransfers})
        except:
            pass

        if not local_tr_cmd.get('host_tr_cmd', {}).get('stage', 0):
            # Mike: 2022/05/23
            if '-LOAD' not in uuid:
                E82.report_event(self.secsgem_e82_h, E82.Transferring, {'CommandID':local_tr_cmd['host_tr_cmd']['uuid'],'CarrierID':carrierID,'VehicleID':self.id}) #8.24B-4

            output('Transferring', {
                    'CommandID':uuid})

        if self.id+'BUF' in local_tr_cmd['source']:
            idx=int(local_tr_cmd['source'][-2:])-1
            self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
            if self.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'): #8.25.7-1
                local_tr_cmd['host_tr_cmd']['preTransfer']=True

        # for buf in self.bufs_status: #remove command note, for auto recovery!
        for idx, buf in enumerate(self.bufs_status): #remove command note, for auto recovery!
            if local_tr_cmd['carrierID'] == buf['stockID']:
                if buf['stockID'] not in ['Unknown', '']:
                    self.adapter.cmd_control(0, local_tr_cmd['host_tr_cmd']['uuid'], local_tr_cmd['host_tr_cmd'].get('original_source',''), local_tr_cmd['host_tr_cmd'].get('dest',''), idx+1, buf['stockID'], lotID='')
                    break

        return


    def BufferUpdate(self):
        for i in range(self.bufNum): #chocp fix
            if self.enableBuffer[i] == 'yes': #chocp 2022/1/6
                status=self.bufs_status[i]
                if status['stockID'] != self.adapter.carriers[i]['status']:
                    #print("############ update buf ##########", i, status, self.adapter.carriers[i]['status'])
                    self.last_bufs_status[i]['stockID']=self.bufs_status[i]['stockID']
                    self.last_bufs_status[i]['type']=self.bufs_status[i]['type']
                    self.last_bufs_status[i]['local_tr_cmd']=self.bufs_status[i]['local_tr_cmd']
                    self.bufs_status[i]['stockID']=self.adapter.carriers[i]['status']
                    if self.bufs_status[i]['stockID'] in ['None', 'Unknown']:
                        self.bufs_status[i]['type']='None'
                    self.bufs_status[i]['read_fail_warn']=self.bufs_status[i]['stockID'] in ['ReadFail', 'ReadIdFail'] # Mike: 2022/03/23
                    self.bufs_status[i]['pos_err_warn']=self.bufs_status[i]['stockID'] in ['PositionError'] # Mike: 2022/03/23

                    local_command_id=''
                    host_command_id=''

                    if self.bufs_status[i]['stockID'] == 'None':
                        if self.last_bufs_status[i]['stockID'] not in ['Unknown', '']:
                            E82.report_event(self.secsgem_e82_h,
                                                E82.CarrierRemoved, {
                                                'VehicleID':self.id,
                                                'CommandID':host_command_id,
                                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                                'CarrierID':self.last_bufs_status[i]['stockID']}) #fix 7
                            self.secsgem_e82_h.rm_carrier(self.last_bufs_status[i]['stockID'])

                        self.carrier_status_list=[] #chocp for >8 slot 2022/8/30
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        output('CarrierRemoved', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                'CarrierID':self.last_bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list
                                })

                        self.bufs_status[i]['type']='None'
                        if global_variables.RackNaming == 42:
                            self.update_dynamic_buffer_mapping(i,'Empty')

                    else: 

                        now=datetime.datetime.now()
                        formatted_time=now.strftime("%Y%m%d%H%M%S%f")[:16]

                        E82.report_event(self.secsgem_e82_h,
                                             E82.CarrierInstalled, {
                                             'VehicleID':self.id,
                                             'CommandID':host_command_id,
                                             'CarrierLoc':self.id+self.vehicle_bufID[i],
                                             'CarrierID':self.bufs_status[i]['stockID']})

                        if self.last_bufs_status[i]['stockID'] not in ['', 'None', 'Unknown']:
                            self.secsgem_e82_h.rm_carrier(self.last_bufs_status[i]['stockID'])

                        self.secsgem_e82_h.add_carrier(self.bufs_status[i]['stockID'], {
                                             'RackID':self.id,
                                             'SlotID':self.vehicle_bufID[i],
                                             'CarrierID':self.bufs_status[i]['stockID']})
                        
                        self.secsgem_e82_h.enhanced_add_carrier(self.bufs_status[i]['stockID'], {
                                             'RackID':self.id,
                                             'SlotID':self.vehicle_bufID[i],
                                             'CarrierID':self.bufs_status[i]['stockID'],
                                             'InstallTime':formatted_time,
                                             'CarrierState':6})

                        self.carrier_status_list=[] #for >8 slot
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        output('CarrierInstalled', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                'CarrierID':self.bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list
                                })

                        print('CarrierInstalled', self.bufs_status[i]['stockID'], self.adapter.carriers[i]['status'])

                        self.bufs_status[i]['type']=self.bufs_status[i]['local_tr_cmd'].get('TransferInfo', {}).get('CarrierType', '')
                        print(self.bufs_status[i]['type'])
                        
                        if not self.bufs_status[i]['local_tr_cmd'] and global_variables.RackNaming == 42:
                            self.update_dynamic_buffer_mapping(i,'Unknown')

    def AgvErrorCheck(self, mr_state):
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd.get('carrierID', '')
        target=self.action_in_run.get('target', '')

        if self.adapter.last_point and self.adapter.last_point not in PoseTable.mapping: #8.28.26
            self.wait_error_code=0
            raise alarms.PointNotInMapWarning(self.adapter.last_point, handler=self.secsgem_e82_h)
        
        elif self.manual:
            self.wait_error_code=0
            raise alarms.OperateManualTestWarning(self.id, uuid, handler=self.secsgem_e82_h)

        elif self.adapter.online['status']!='Ready': #disconnect
            self.wait_error_code=0
            raise alarms.BaseOffLineWarning(self.id, uuid, handler=self.secsgem_e82_h)

        elif self.adapter.alarm['error_code']: #one time alarm, chocp fix hex code
            #"900001":"GetRouteTimeout",
            sub_code=self.adapter.alarm['error_code']
            self.wait_error_code=0
            if self.adapter.alarm['error_code'] == '900001': #Mike: 2022/10/21
                raise alarms.GetRouteTimeoutWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h)
            elif self.adapter.alarm['error_code'] == 'TSC031':
                if global_variables.RackNaming == 36:
                    self.adapter.alarm_control(10004, True)
                    try: #2024/08/29 for Mirle mCS
                        EnhancedALID={'ALID':self.error_code, 'AlarmText':self.error_txt,'UnitInfo':{"VehicleID": self.id, "VehicleState": 4}}
                        AlarmsSetDescription=E82.get_variables(self.secsgem_e82_h, 'AlarmsSetDescription')
                        AlarmsSetDescription[self.id]=EnhancedALID
                        E82.update_variables(self.secsgem_e82_h, {'AlarmsSetDescription': AlarmsSetDescription})
                    except:
                        pass
                    raise alarms.BaseMoveWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

            raise alarms.BaseOtherAlertWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

        elif self.adapter.robot['status'] == 'Error': #robot error
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            sub_code=self.adapter.alarm['error_code']
            raise alarms.BaseRobotWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

        elif self.adapter.move['status'] == 'Error':
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            sub_code=self.adapter.alarm['error_code']
            raise alarms.BaseMoveWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

        elif self.adapter.online['man_mode']: #control offline
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            if global_variables.RackNaming == 2: #for nxcp
                raise alarms.BaseNotAutoModeWarning(self.id, uuid, 'Serious', handler=self.secsgem_e82_h)
            else:
                raise alarms.BaseNotAutoModeWarning(self.id, uuid, 'Error', handler=self.secsgem_e82_h)

        elif mr_state == 'Unassigned' or mr_state == 'Parked': #chocp 2021/7/16
            
            if self.adapter.move['status']!='Idle':
                self.adapter.logger.info("amrid:{},move status:{}".format(self.id,self.adapter.move['status']))
                sub_code=self.adapter.alarm['error_code']
                raise alarms.BaseMoveCheckWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

            if self.adapter.robot['status']!='Idle':
                sub_code=self.adapter.alarm['error_code']
                raise alarms.BaseRobotCheckWarning(self.id, uuid, target, sub_code, handler=self.secsgem_e82_h) #fix 2022/2/10

 
        for i in range(self.bufNum): #chocp fix
            #print(self.adapter.carriers[i]['status'])
            if self.enableBuffer[i] == 'yes': #chocp 2022/1/6
                status=self.bufs_status[i]
                if status['stockID'] != self.adapter.carriers[i]['status']:
                    #print("############ update buf ##########", i, status, self.adapter.carriers[i]['status'])
                    self.last_bufs_status[i]['stockID']=self.bufs_status[i]['stockID']
                    self.last_bufs_status[i]['type']=self.bufs_status[i]['type']
                    self.last_bufs_status[i]['local_tr_cmd']=self.bufs_status[i]['local_tr_cmd']
                    self.bufs_status[i]['stockID']=self.adapter.carriers[i]['status']
                    if self.bufs_status[i]['stockID'] in ['None', 'Unknown']:
                        self.bufs_status[i]['type']='None'
                    self.bufs_status[i]['read_fail_warn']=self.bufs_status[i]['stockID'] in ['ReadFail', 'ReadIdFail'] # Mike: 2022/03/23
                    self.bufs_status[i]['pos_err_warn']=self.bufs_status[i]['stockID'] in ['PositionError'] # Mike: 2022/03/23

                    local_command_id=''
                    host_command_id=''
                    try:
                        local_command_id=uuid
                        host_command_id=local_tr_cmd['host_tr_cmd']['uuid']
                    except:
                        pass

                    if self.bufs_status[i]['stockID'] == 'None':
                        if self.last_bufs_status[i]['stockID'] not in ['Unknown', '']:
                            E82.report_event(self.secsgem_e82_h,
                                                E82.CarrierRemoved, {
                                                'VehicleID':self.id,
                                                'CommandID':host_command_id,
                                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                                'CarrierID':self.last_bufs_status[i]['stockID']}) #fix 7
                            self.secsgem_e82_h.rm_carrier(self.last_bufs_status[i]['stockID'])

                        self.carrier_status_list=[] #chocp for >8 slot 2022/8/30
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        output('CarrierRemoved', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                'CarrierID':self.last_bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list
                                })

                        self.bufs_status[i]['type']='None'

                        if self.bufs_status[i]['local_tr_cmd']:
                            self.bufs_status[i]['local_tr_cmd']['carrierLoc']=self.bufs_status[i]['local_tr_cmd'].get('dest', '')
                        if global_variables.RackNaming == 42:
                            self.update_dynamic_buffer_mapping(i,'Empty')

                    else: 
                        now=datetime.datetime.now()
                        formatted_time=now.strftime("%Y%m%d%H%M%S%f")[:16]

                        if self.last_bufs_status[i]['stockID'] not in ['', 'None', 'Unknown']:
                            self.secsgem_e82_h.rm_carrier(self.last_bufs_status[i]['stockID'])
                            if self.last_bufs_status[i]['stockID'] != 'ReadFail' or\
                                global_variables.TSCSettings.get('Safety',{}).get('RenameFailedID', 'no') == 'no':
                                E82.report_event(self.secsgem_e82_h,
                                                    E82.CarrierRemoved, {
                                                    'VehicleID':self.id,
                                                    'CommandID':host_command_id,
                                                    'CarrierLoc':self.id+self.vehicle_bufID[i],
                                                    'CarrierID':self.last_bufs_status[i]['stockID']}) #fix 7

                        self.secsgem_e82_h.add_carrier(self.bufs_status[i]['stockID'], {
                                             'RackID':self.id,
                                             'SlotID':self.vehicle_bufID[i],
                                             'CarrierID':self.bufs_status[i]['stockID']})

                        self.secsgem_e82_h.enhanced_add_carrier(self.bufs_status[i]['stockID'], {
                                             'RackID':self.id,
                                             'SlotID':self.vehicle_bufID[i],
                                             'CarrierID':self.bufs_status[i]['stockID'],
                                             'InstallTime':formatted_time,
                                             'CarrierState':6})

                        self.carrier_status_list=[] #for >8 slot
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        output('CarrierInstalled', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                'CarrierID':self.bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list
                                })

                        print('CarrierInstalled', self.bufs_status[i]['stockID'], self.adapter.carriers[i]['status'])

                        if self.bufs_status[i]['local_tr_cmd']:
                            self.bufs_status[i]['local_tr_cmd']['carrierLoc']=self.id+self.vehicle_bufID[i]
                            
                        elif not self.bufs_status[i]['local_tr_cmd'] and global_variables.RackNaming == 42:
                            self.update_dynamic_buffer_mapping(i,'Unknown')

                        if self.bufs_status[i]['local_tr_cmd'].get('host_tr_cmd', {}):
                            if '-UNLOAD' in self.bufs_status[i]['local_tr_cmd']['uuid']:
                                source=self.bufs_status[i]['local_tr_cmd']['host_tr_cmd'].get('dest','')
                                dest=self.bufs_status[i]['local_tr_cmd']['host_tr_cmd'].get('back','')
                            else:
                                source=self.bufs_status[i]['local_tr_cmd']['host_tr_cmd'].get('original_source','')
                                dest=self.bufs_status[i]['local_tr_cmd']['host_tr_cmd'].get('dest','')
                            self.adapter.cmd_control(0, self.bufs_status[i]['local_tr_cmd']['host_tr_cmd']['uuid'], source, dest, i+1, self.bufs_status[i]['stockID'], lotID='')

                        self.bufs_status[i]['type']=self.bufs_status[i]['local_tr_cmd'].get('TransferInfo', {}).get('CarrierType', '')
                        if not self.bufs_status[i]['type'] and self.action_in_run.get('local_tr_cmd', {}).get('uuid', '') == self.bufs_status[i]['local_tr_cmd_mem'].get('uuid', ''):
                            self.bufs_status[i]['type']=self.bufs_status[i]['local_tr_cmd_mem'].get('TransferInfo', {}).get('CarrierType', '')
                        if global_variables.RackNaming == 42 and i == 0: #Renesas FCBGA Buf01 only for CoverTray
                            self.bufs_status[i]['type']='CoverTray'
                        print(self.bufs_status[i]['type'])

                        '''if global_variables.TSCSettings.get('Safety',{}).get('RenameFailedID', 'no') == 'yes'\
                                and self.bufs_status[i]['stockID'] == 'ReadFail':
                            self.adapter.rfid_control(i+1, carrierID)'''

                        if self.bufs_status[i]['stockID'] == 'ReadFail':
                            if global_variables.TSCSettings.get('Safety',{}).get('RenameFailedID', 'no') == 'yes':
                                rename_id=self.bufs_status[i]['local_tr_cmd_mem'].get('TransferInfo', {}).get('CarrierID', carrierID)
                                self.adapter.rfid_control(i+1, rename_id)
                            else:
                                E82.report_event(self.secsgem_e82_h,
                                                    E82.CarrierInstalled, {
                                                    'VehicleID':self.id,
                                                    'CommandID':host_command_id,
                                                    'CarrierLoc':self.id+self.vehicle_bufID[i],
                                                    'CarrierID':self.bufs_status[i]['stockID']})
                        else:
                            E82.report_event(self.secsgem_e82_h,
                                                E82.CarrierInstalled, {
                                                'VehicleID':self.id,
                                                'CommandID':host_command_id,
                                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                                'CarrierID':self.bufs_status[i]['stockID']})

                #if self.bufs_status[i]['stockID'] == 'ReadFail' and mr_state not in ['Acquiring','Depositing','Pause'] and not global_variables.TSCSettings.get('Safety', {}).get('BufferNoRFIDCheck', 'no') == 'yes':
                if self.bufs_status[i]['read_fail_warn'] and\
                  mr_state not in ['Acquiring','Depositing','Pause'] and not global_variables.TSCSettings.get('Safety', {}).get('BufferNoRFIDCheck', 'no') == 'yes': #2022/2/22
                    if global_variables.RackNaming not in [18, 42]:
                        alarms.BaseCarrRfidFailWarning(self.id, uuid, self.vehicle_bufID[i], carrierID)
                        self.bufs_status[i]['read_fail_warn']=False

                if self.bufs_status[i]['pos_err_warn'] and mr_state not in ['Acquiring','Depositing','Pause']:
                    self.bufs_status[i]['pos_err_warn']=False
                    if global_variables.TSCSettings.get('Safety', {}).get('BufferPosCheck', 'yes') == 'yes':
                        raise alarms.BaseCarrPosErrWarning(self.id, uuid, self.vehicle_bufID[i], carrierID)
                    alarms.BaseCarrPosErrWarning(self.id, uuid, self.vehicle_bufID[i], carrierID)


        return False #chocp fix 2021/11/26

    #will abort all relative local_tr_cmds and actions
    def abort_tr_cmds_and_actions(self, local_command_id, result_code, result_txt, cause='by alarm', check_link=True): #fix 6

        res=False
        del_actions=[]

        for action in self.actions:
            if action['local_tr_cmd']['host_tr_cmd']['uuid'] in local_command_id:
                del_actions.append(action)

        for action in del_actions:
            self.actions.remove(action)

        if self.action_in_run and self.action_in_run['local_tr_cmd']['host_tr_cmd']['uuid'] in local_command_id:
            self.tr_assert={'Result':'CANCEL','CommandID':local_command_id} #???
            if self.AgvState == 'Waiting':
                print('Stage abort or expired, stop waiting.')
                self.AgvState='Parked'
                self.host_call_target=''
                self.host_call_waiting_time=0

        del_tr_cmds=[]
        del_tr_cmds_id=[]
        for local_tr_cmd in self.tr_cmds:
            if local_tr_cmd['host_tr_cmd']['uuid'] in local_command_id:
                del_tr_cmds.append(local_tr_cmd)
                del_tr_cmds_id.append(local_command_id)
                if local_tr_cmd['host_tr_cmd'].get('link'): #8.22J-2
                    link_local_tr_cmd=local_tr_cmd['host_tr_cmd'].get('link')
                    if check_link:
                        link_uuid=link_local_tr_cmd.get('uuid', '')
                        if local_tr_cmd['host_tr_cmd'].get('sourceType') == 'StockOut' or local_tr_cmd['host_tr_cmd'].get('sourceType') == 'ErackOut': #Chi 2022/12/29
                            #E82.report_event(self.secsgem_e82_h, E82.TransferCancelInitiated, {'CommandID':link_uuid,'CommandInfo':link_local_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':link_local_tr_cmd.get('OriginalTransferCompleteInfo','')})
                            for queue_id, zone_wq in TransferWaitQueue.getAllInstance().items():
                                if queue_id == link_local_tr_cmd['zoneID'] or queue_id == local_tr_cmd['source']:
                                    zone_wq.preferVehicle=''
                                if link_local_tr_cmd['sourceType'] == 'FromVehicle' and queue_id == self.id:
                                    res, tmp_host_tr_cmd=zone_wq.remove_waiting_transfer_by_commandID(link_uuid, cause='by link')
                                    if res:
                                        # self.doPreDispatchCmd=False
                                        for transferinfo in link_local_tr_cmd['OriginalTransferInfoList']:
                                            link_local_tr_cmd['OriginalTransferCompleteInfo'].append({'TransferInfo': transferinfo, 'CarrierLoc':transferinfo['SourcePort']}) #bug, need check
                                        link_local_tr_cmd['OriginalTransferCompleteInfo'][0]['CarrierLoc']=local_tr_cmd['carrierLoc']

                                        E82.report_event(self.secsgem_e82_h,
                                            E82.TransferCompleted, {
                                            'CommandInfo':link_local_tr_cmd.get('CommandInfo',''),
                                            'VehicleID':self.id,
                                            'TransferCompleteInfo':link_local_tr_cmd.get('OriginalTransferCompleteInfo', []), #9/13
                                            'TransferInfo':link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd['OriginalTransferInfoList'] else {},
                                            'CommandID':link_local_tr_cmd['CommandInfo'].get('CommandID', ''),
                                            'Priority':link_local_tr_cmd['CommandInfo'].get('Priority', 0),
                                            'Replace':link_local_tr_cmd['CommandInfo'].get('Replace', 0),
                                            'CarrierID':link_local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                            'SourcePort':link_local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                            'DestPort':link_local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                            #'CarrierLoc':self.action_in_run['loc'],
                                            'CarrierLoc':link_local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                            'ResultCode':result_code})
                                        '''E82.report_event(self.secsgem_e82_h, E82.TransferCancelCompleted, {
                                            'CommandInfo':link_local_tr_cmd.get('CommandInfo',''),
                                            'TransferCompleteInfo':link_local_tr_cmd.get('OriginalTransferCompleteInfo', []), #9/13
                                            'TransferInfo':link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd['OriginalTransferInfoList'] else {},
                                            'CommandID':link_local_tr_cmd['CommandInfo'].get('CommandID', ''),
                                            'Priority':link_local_tr_cmd['CommandInfo'].get('Priority', 0),
                                            'Replace':link_local_tr_cmd['CommandInfo'].get('Replace', 0),
                                            'CarrierID':link_local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                            'SourcePort':link_local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                            'DestPort':link_local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                            #'CarrierLoc':self.action_in_run['loc'],
                                            'CarrierLoc':link_local_tr_cmd['dest']}) #chocp fix for tfme 2021/10/23'''
                                        output('TransferCancelCompleted', {'CommandID':link_uuid})
                                    else:
                                        E82.report_event(self.secsgem_e82_h, E82.TransferCancelFailed, {'CommandID':link_uuid,'CommandInfo':link_local_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':link_local_tr_cmd.get('OriginalTransferCompleteInfo','')})
                        else:
                            if global_variables.TSCSettings.get('Safety', {}).get('SkipAbortLoadWhenUnloadAbort', 'no') == 'no':
                                #E82.report_event(self.secsgem_e82_h, E82.TransferAbortInitiated, {'CommandID':link_uuid,'CommandInfo':link_local_tr_cmd.get('CommandInfo',''),'TransferCompleteInfo':link_local_tr_cmd.get('OriginalTransferCompleteInfo','')})
                                self.abort_tr_cmds_and_actions(link_uuid, 40002, 'Transfer command in exectuing queue be aborted', cause='by link')
                    else:
                        link_local_tr_cmd['last']=True

                if local_tr_cmd['host_tr_cmd'].get('preTransfer',''):
                    for idx in range(self.bufNum):
                        if local_command_id == self.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('uuid'):
                            if self.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'):
                                self.bufs_status[idx]['local_tr_cmd_mem']['host_tr_cmd']['preTransfer']=False

                # elif 'MR' in local_tr_cmd['host_tr_cmd'].get('zoneID',''): #8.25.7-1
                #if 'MR' in local_tr_cmd['host_tr_cmd'].get('source',''):
                if self.id in local_tr_cmd['host_tr_cmd'].get('source',''):
                    buf_num=int(local_tr_cmd['host_tr_cmd'].get('source','').split('BUF')[1])
                    for idx in range(self.bufNum):
                        if idx+1 == buf_num:
                            if self.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'):
                                self.bufs_status[idx]['local_tr_cmd_mem']['host_tr_cmd']['preTransfer']=False

        # print('Gonna delete: ', del_tr_cmds_id)
        for local_tr_cmd in del_tr_cmds: #why can't bind above
            res=True
            uuid=local_tr_cmd.get('uuid', '')
            local_tr_cmd['uuid']=''

            if cause not in ['by alarm', 'by stage']:
                alarms.CommandAbortWarning(cause, uuid, handler=self.secsgem_e82_h) #set alarm by host or by web abort
                
            if global_variables.RackNaming == 43:
                if result_code == 10016:
                    if self.error_sub_code == 'TSC002':
                        result_code=72
                    elif self.error_sub_code == 'TSC027':
                        result_code=71
                    else:
                        result_code=1
                elif result_code == 10007:
                    if self.error_sub_code == 'TSC029':
                        result_code=64
                    elif self.error_sub_code == 'TSC030':
                        result_code=65
                    else:
                        result_code=1
                else:
                    result_code=1

            if not local_tr_cmd.get('host_tr_cmd', {}).get('stage', 0):
                output('TransferCompleted', {
                        'VehicleID':self.id,
                        'DestType':local_tr_cmd.get('dest_type', 'other'),
                        'Travel':local_tr_cmd.get('travel', 0),
                        'CommandID':uuid,
                        #'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                        'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                        'ResultCode':result_code,
                        'Message':result_txt }, True)


            output('TransferExecuteQueueRemove', {'CommandID':uuid}, True)

            print('<<Abort, TransferExecuteQueueRemove>>', {'CommandID':uuid})


            if global_variables.RackNaming != 7:#kelvinng 20240619
                tools.reset_indicate_slot(local_tr_cmd.get('source'))
                tools.reset_book_slot(local_tr_cmd.get('dest'))
                tools.reset_book_slot(local_tr_cmd.get('TransferInfo', {}).get('DestPort')) # zhangpeng 2025-02-14 # fix the latest dest port is not be reset book after the dest is changed.
            else:
                tools.reset_indicate_slot(local_tr_cmd.get('source'),carrierID=local_tr_cmd.get("carrierID",""))
                tools.reset_book_slot(local_tr_cmd.get('dest'))
                tools.reset_book_slot(local_tr_cmd.get('TransferInfo', {}).get('DestPort')) # zhangpeng 2025-02-14 # fix the latest dest port is not be reset book after the dest is changed.

            self.tr_cmds.remove(local_tr_cmd)
            self.adapter.planner.clean_route()


            #9/13 chocp fix from tfme
            #local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':self.action_in_run['loc']})
            local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']}) #bug, need check
            local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['OriginalTransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']}) #bug, need check

            # print('In abort... local_tr_cmd is: ', local_tr_cmd)
            if local_tr_cmd['last']:
                if cause == 'by alarm': #fix 6
                    #E82 transfer complete
                    if not local_tr_cmd.get('host_tr_cmd', {}).get('stage', 0):
                        E82.report_event(self.secsgem_e82_h,
                                    E82.TransferCompleted, {
                                    'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                    'VehicleID':self.id,
                                    'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                    'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                    'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                    'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                    'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                    'CarrierID':local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                    'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                    'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                    #'CarrierLoc':self.action_in_run['loc'],
                                    'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                    'ResultCode':result_code})
                    self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''))
                else:
                    #E82 cancel complete
                    if local_tr_cmd['host_tr_cmd']['uuid']+'-LOAD' not in del_tr_cmds_id:
                        if not local_tr_cmd.get('host_tr_cmd', {}).get('stage', 0):
                            E82.report_event(self.secsgem_e82_h,
                                        E82.TransferAbortCompleted, {
                                        'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                        'CommandID':local_tr_cmd['host_tr_cmd']['uuid'],
                                        'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                        'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                        'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                        'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                        'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                        'CarrierID':local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                        'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                        'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                        #'CarrierLoc':self.action_in_run['loc'],
                                        'VehicleID':self.id, #8.25.13-1
                                        'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                        'ResultCode':result_code }) #chocp fix for tfme 2021/10/23

                        self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['uuid'])

                
                #EqMgr.getInstance().trigger(local_tr_cmd['source'], 'alarm_set', {'vehicleID':self.id, 'CommandID':uuid, 'Message':result_txt }) #chocp add 2022/11/10
                #EqMgr.getInstance().trigger(local_tr_cmd['dest'], 'alarm_set', {'vehicleID':self.id, 'CommandID':uuid, 'Message':result_txt }) #chocp add 2022/11/10
                if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes': #only for RTD mode
                    if '-UNLOAD' not in local_tr_cmd['host_tr_cmd']['uuid']:
                        EqMgr.getInstance().orderMgr.update_work_status(local_tr_cmd['host_tr_cmd']['uuid'], 'FAIL', result_txt)
            else:
                if cause!='by alarm': #fix 6
                    if local_tr_cmd['host_tr_cmd']['uuid']+'-LOAD' == uuid:
                        if not local_tr_cmd.get('host_tr_cmd', {}).get('stage', 0):
                            E82.report_event(self.secsgem_e82_h,
                                        E82.TransferAbortCompleted, {
                                        'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                        'CommandID':local_tr_cmd['host_tr_cmd']['uuid'],
                                        'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                        'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                        'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                        'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                        'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                        'CarrierID':local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                        'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                        'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                        #'CarrierLoc':self.action_in_run['loc'],
                                        'VehicleID':self.id, #8.25.13-1
                                        'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                        'ResultCode':result_code }) #chocp fix for tfme 2021/10/23

                        self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['uuid'])


        # for i in range(self.bufNum):
        #     if self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-') == local_command_id :
        #         self.bufs_status[i]['do_auto_recovery']=True

        # for buf in self.bufs_status: #remove command note, for auto recovery!
        for idx, buf in enumerate(self.bufs_status): #remove command note, for auto recovery!
            if buf['local_tr_cmd'] in del_tr_cmds:
                print('remove ...................')
                local_tr_cmd=buf['local_tr_cmd']
                if buf['stockID'] not in ['Unknown', '']:
                    self.adapter.cmd_control(1, local_tr_cmd['host_tr_cmd']['uuid'], local_tr_cmd['host_tr_cmd'].get('original_source',''), local_tr_cmd['host_tr_cmd'].get('dest',''), idx+1, buf['stockID'], lotID='')
                buf['local_tr_cmd']={} #chocp

        return res

    def reset_traffic_jam(self):
        print('reset_traffic_jam')

        self.release_alarm()

        #go stanby
        wait_vehicle='' # Mike: 2021/11/12
        for vehicle_id, h_vehicle in self.h_vehicleMgr.vehicles.items(): #chocp fix, 2021/10/14
            if h_vehicle.id!=self.id:
                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                    self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id)) 
                    wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                    break
      
        self.return_standby_cmd(wait_vehicle, tmpPark=True, from_unassigned=False) # Mike: 2021/11/12
        return
    
    def retry_action(self):
        print('<<<retry_action>>>')
        self.adapter.logger.info('{} {} '.format(self.id, '<<<retry_action>>>')) 
        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''
        self.error_txt=''
        self.message='None'
        self.alsv=[]
        self.error_skip_tr_req=True
        self.adapter.alarm_reset()

        return   

    def release_alarm(self):
        print('release_alarm')

        if self.alarm_set!='Info' and self.error_code:
            if self.secsgem_e82_h.MDLN == 'v3_MIRLE':
                mirle_list=['VehicleID','CommandID','CarrierID','CarrierLoc']
                for i in mirle_list:
                    if i not in self.alsv:
                        if i == 'VehicleID':
                            VehicleInfo={"VehicleID": '', "VehicleState": 0}
                            E82.update_variables(self.secsgem_e82_h, {'VehicleInfo': VehicleInfo})
                        else:
                            E82.update_variables(self.secsgem_e82_h, {str(i): ''})
            self.secsgem_e82_h.clear_alarm(self.error_code,self.alarm_set)
            
        try: #2024/08/29 for Mirle MCS
            EnhancedALID={'ALID':'', 'AlarmText':'','UnitInfo':{"VehicleID": self.id, "VehicleState": 0}}
            AlarmsSetDescription=E82.get_variables(self.secsgem_e82_h, 'AlarmsSetDescription')
            AlarmsSetDescription[self.id]=EnhancedALID
            E82.update_variables(self.secsgem_e82_h, {'AlarmsSetDescription': AlarmsSetDescription})
        except:
            pass
        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''
        self.error_txt=''
        self.message='None'
        self.alsv=[]


        self.adapter.alarm_reset()
   
        output('VehiclePauseClear',{
                'Point':self.adapter.last_point, #2021/1/4
                'Station':self.at_station,
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleID':self.id,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge})

        return   



    def reset_alarm(self):

        print('reset_alarm and clear commans')
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')

        #if global_variables.RackNaming == 4 and (self.alarm_set == 'Serious' or global_variables.TSCSettings['Recovery']['Auto']!='yes') : #abort all trnasfers
        '''if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenSeriousAlarm') == 'yes' and\
         (self.alarm_set == 'Serious' or global_variables.TSCSettings.get('Recovery', {}).get('Auto')!='yes') : #abort all trnasfers'''

        abort_all=False #8.21K
        if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenErrorAlarm') == 'yes' and self.alarm_set in ['Serious', 'Error']:
            abort_all=True
        if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenSeriousAlarm') == 'yes' and self.alarm_set == 'Serious':
            abort_all=True

        if abort_all: #abort all trnasfers
            self.abort_tr_cmds_and_actions(uuid, self.error_code, self.error_txt, cause='by alarm')
            del_command_id_list=[] #chocp 2022/6/29
            for del_tr_cmd in self.tr_cmds:
                del_command_id_list.append(del_tr_cmd.get('uuid', ''))

            for del_command_id in del_command_id_list:
                self.abort_tr_cmds_and_actions(del_command_id, self.error_code, self.error_txt, cause='by other cmd')

        elif self.action_in_run: #chocp 2021/11/28
            self.abort_tr_cmds_and_actions(uuid, self.error_code, self.error_txt, cause='by alarm')
            
            ## check valid buffer

        if self.alarm_set!='Info' and self.error_code:
            if self.secsgem_e82_h.MDLN == 'v3_MIRLE':
                mirle_list=['VehicleID','CommandID','CarrierID','CarrierLoc']
                for i in mirle_list:
                    if i not in self.alsv:
                        if i == 'VehicleID':
                            VehicleInfo={"VehicleID": '', "VehicleState": 0}
                            E82.update_variables(self.secsgem_e82_h, {'VehicleInfo': VehicleInfo})
                        else:
                            E82.update_variables(self.secsgem_e82_h, {str(i): ''})

            self.secsgem_e82_h.clear_alarm(self.error_code, self.alarm_set)
        try:
            EnhancedALID={'ALID':'', 'AlarmText':'','UnitInfo':{"VehicleID": self.id, "VehicleState": 0}}
            AlarmsSetDescription=E82.get_variables(self.secsgem_e82_h, 'AlarmsSetDescription')
            AlarmsSetDescription[self.id]=EnhancedALID
            E82.update_variables(self.secsgem_e82_h, {'AlarmsSetDescription': AlarmsSetDescription})
        except:
            pass
 
        #self.ResultCode=self.error_code
        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''

        self.error_txt=''
        self.message='None'
        
        self.alsv=[]
        self.alarm_node=[]
        self.alarm_edge=[]

        #self.waiting_run=False #chocp add 2021/11/7
        self.stop_command=False #chocp add for stop_command 2022/10/17

        self.at_station='' #2021/1/4

        #need add reset ....
        self.adapter.alarm_reset() #2021/2/22
        self.host_stop=False #Chi 2023/03/15
        self.emergency_evacuation_cmd=False
        self.emergency_evacuation_stop=False

        # self.manual=False #chocp:2021/3/9

        #self.adapter.last_point=tools.round_a_point([self.adapter.move['pose']['x'], self.adapter.move['pose']['y']])

        print('reset to point:{}'.format(self.adapter.last_point))

        output('VehiclePauseClear',{
                'Point':self.adapter.last_point, #2021/1/4
                'Station':self.at_station,
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleID':self.id,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge})

        return

    def alarm_handler(self, alarm_instance):
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')

        self.alarm_set=alarm_instance.level
        self.error_code=alarm_instance.code
        self.error_sub_code=alarm_instance.sub_code #chocp add 2021/12/11
        self.error_txt=alarm_instance.txt
        self.message=alarm_instance.more_txt
        self.alsv=alarm_instance.alsv

        self.error_reset_cmd=False
        self.error_retry_cmd=False
        self.AgvLastState=self.AgvState
        self.AgvState='Pause'
        if not self.adapter.online['connected']:
            self.AgvSubState='Disconnected'
        elif (self.adapter.online['man_mode'] and self.error_code == 10008) or self.manual:
            self.AgvSubState='Manual'
        else:
            self.AgvSubState='Pause'
        self.call_support_time=time.time()

        self.force_charge=False

        #self.adapter.charge_end() #chocp fix 2021/11/26

        self.at_station='' #2020/12/10 chocp

        output('VehiclePauseSet',{
                'VehicleID':self.id,
                'CommandID':uuid,
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleState':self.AgvState,
                'VehicleSubState':self.AgvSubState,
                'ForceCharge':self.force_charge,
                'Message':self.message},True)

        # Mike: 2021/03/15
        print('In alarm_handler clean right')

        #self.adapter.clean_right(True)
        if self.adapter.online['connected'] or global_variables.TSCSettings.get('Safety', {}).get('ReleaseRightWhenDisconnected','no') == 'yes':
            self.adapter.planner.clean_right(False) #chocp 2021/12/31

        #if self.action_in_run: #may move to clear alarm
        #    EqMgr.getInstance().trigger(local_tr_cmd['source'], 'alarm_set', {'vehicleID':self.id, 'CommandID':uuid, 'Message':alarm_instance.more_txt})
        #    EqMgr.getInstance().trigger(local_tr_cmd['dest'], 'alarm_set', {'vehicleID':self.id, 'CommandID':uuid, 'Message':alarm_instance.more_txt})
        
        return

    def sub_alarm_state_handler(self, state):
        # self.AgvLastState=self.AgvState
        # self.AgvState=state

        output('VehiclePauseClear',{
                'Point':self.adapter.last_point, #2021/1/4
                'Station':self.at_station,
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleID':self.id,
                'VehicleState':self.AgvState,
                'VehicleSubState':self.AgvSubState,
                'Message':self.message,
                'ForceCharge':self.force_charge})

        self.AgvSubState=state

        output('VehiclePauseSet',{
                'VehicleID':self.id,
                'CommandID':'',
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleState':self.AgvState,
                'VehicleSubState':self.AgvSubState,
                'ForceCharge':self.force_charge,
                'Message':self.message},True)

    def action_loc_assign(self, action):
        local_tr_cmd=action.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '') #2023/12/29
        target=action.get('target', '')
        priorityBuf=local_tr_cmd.get('host_tr_cmd','').get('priorityBuf', '')
        self.adapter.logger.info("action['type']6:{}".format(action['type']))
        if action['type'] == 'ACQUIRE':
            available_buffer_list =tools.sort_buffers_bypriority(self, local_tr_cmd=local_tr_cmd, from_action_loc_assign=True)
            # available_buffer_list=range(self.bufNum)
            # if self.with_buf_contrain_batch:
            #     available_buffer_list=range(self.bufNum)[::-1]
            #     tmp=available_buffer_list[1] # need to check if can modify at begin
            #     available_buffer_list[1]=available_buffer_list[2]
            #     available_buffer_list[2]=tmp
                
            # if global_variables.RackNaming == 30: #for BOE fixed order
            #     available_buffer_list=[1,3,0,2]

            # if global_variables.RackNaming == 36: #peter 241211
            #     pass
            #     # if self.model == "Type_A":
            #     #     num, buf_list=self.buf_available2()
            #     #     self.adapter.logger.debug("buf_list//:{}".format(buf_list))
            #     #     #['BUF02', 'BUF03', 'BUF04']
            #     #     new_available_buffer_list=[]
            #     #     for buf_list_index in buf_list:
            #     #         if "BUF02" == buf_list_index:
            #     #             new_available_buffer_list.append(1)
            #     #         elif "BUF03" == buf_list_index:
            #     #             new_available_buffer_list.append(2)
            #     #         elif "BUF04" == buf_list_index:
            #     #             new_available_buffer_list.append(4)
            #     #     available_buffer_list=[0,2,1,3]
            #     # if self.model == "Type_G":
            #     #     available_buffer_list=[9,10,11,12,13,1,2,3,4,5,6,7]
                
            # if global_variables.RackNaming == 42: 
            #     available_buffer_list=[1,2,3,4,5]
                
            # if global_variables.RackNaming in [33, 58] and priorityBuf:
            #     if priorityBuf == 'Front':
            #         available_buffer_list=[0,1,2,6,7,8,3,4,5,9,10,11] if global_variables.RackNaming == 58 else [0,1,2,3,4,5,6,7,8,9,10,11]
            #     elif priorityBuf == 'Rear': 
            #         available_buffer_list=[6,7,8,0,1,2,9,10,11,3,4,5] if global_variables.RackNaming == 58 else [11,10,9,8,7,6,5,4,3,2,1,0]     

            if global_variables.RackNaming == 15: # JWO 2023/09/20 for GF
                # Check if 'DestPort' contains "BUF" for GF
                dest_port=local_tr_cmd.get('TransferInfo', {}).get('DestPort', '')
                if "BUF" in dest_port :
                    # Extract the buffer number
                    try:
                        buf_number=int(dest_port[-2:])  # Assuming the format is always "BUFXX"
                        print('MRBUF_NUM',  buf_number)
                    except:
                        #raise ValueError("Invalid DestPort format: {}".format(dest_port))
                        raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)


                    # Check if the buffer number is in available_buffer_list
                    print("***BUFFER_LIS***T:",self.adapter.carriers, '***dest_buf_number***', self.adapter.carriers[buf_number])
                    if self.enableBuffer[buf_number-1] == 'yes' and self.adapter.carriers[buf_number-1]['status'] == 'None':
                        print("Buffer number {} is available.".format(buf_number), '+++++++++++++',self.adapter.carriers[buf_number-1]['status'], '++++', self.adapter.carriers )
                        action['loc']="BUF0" + str(buf_number)
                        local_tr_cmd["start_time"]=time.time()#2024/9/12 Yuri
                        self.bufs_status[buf_number]['local_tr_cmd']=local_tr_cmd
                        self.bufs_status[buf_number]['local_tr_cmd_mem']=local_tr_cmd
                        print('***add_MRBUF_cmd', local_tr_cmd)
                    else:
                        print("Buffer number {} is not available.".format(buf_number))
                        raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

                else:
                    for idx in available_buffer_list: #select a buffer form last buffer
                        if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None':

                            action['loc']=self.vehicle_bufID[idx]
                            local_tr_cmd["start_time"]=time.time()#2024/9/12 Yuri
                            self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
                            self.bufs_status[idx]['local_tr_cmd_mem']=local_tr_cmd

                            break
                    else:
                        raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

            else:
                for idx in available_buffer_list: #select a buffer form last buffer
                    if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None':

                        action['loc']=self.vehicle_bufID[idx]
                        local_tr_cmd["start_time"]=time.time()#2024/9/12 Yuri
                        self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
                        self.bufs_status[idx]['local_tr_cmd_mem']=local_tr_cmd                        
                        break
                else: #chocp fix
                    raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

        elif action['type'] == 'DEPOSIT':
            if global_variables.RackNaming == 15: # JWO 2023/09/20 for GF
                # Check if 'SourcePort' contains "BUF"
                source_port=local_tr_cmd.get('TransferInfo', {}).get('SourcePort', '')
                print("SOURCE:", source_port)
                if "BUF" in source_port:
                    # Extract the buffer number
                    try:
                        buf_number=int(source_port[-2:])  # Assuming the format is always "BUFXX"
                        print('MRBUF_NUM',  buf_number)
                    except:
                        #raise
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

                    if self.enableBuffer[buf_number-1] == 'yes' and self.adapter.carriers[buf_number-1]['status'] not in ['None', 'Unknown', 'PositionError']:
                        action['loc']=self.vehicle_bufID[buf_number-1]

                    else:
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

                else:
                    for i in range(self.bufNum):
                        carrier=self.adapter.carriers[i]

                        #fix support for stocker out
                        record_command_id=self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-')
                        print('check AMR {}, record commandID={}, but buf carrier status={}, and deposit commandID={}'.format(self.vehicle_bufID[i], record_command_id, carrier['status'], uuid))
                        if record_command_id and record_command_id in uuid: #2022/12/29 support replace -load/-unload
                            if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'Unknown', 'PositionError']:
                                if carrierID and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                    if carrier['status'] == carrierID:
                                        action['loc']=self.vehicle_bufID[i]
                                        break
                                else:
                                    action['loc']=self.vehicle_bufID[i]
                                    break
                    else:
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID) #chocp fix 2021/11/23

            else:
                for i in range(self.bufNum):
                    carrier=self.adapter.carriers[i]

                    #fix support for stocker out
                    record_command_id=self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-')
                    print('check AMR {}, record commandID={}, but buf carrier status={}, and deposit commandID={}'.format(self.vehicle_bufID[i], record_command_id, carrier['status'], uuid))
                    if record_command_id and record_command_id in uuid: #2022/12/29 support replace -load/-unload
                        #if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'Unknown', 'PositionError']:
                        if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'PositionError']:  #chocp 2024/03/27 
                            
                            if carrierID and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                if carrier['status'] == carrierID:
                                    action['loc']=self.vehicle_bufID[i]
                                    
                                    break
                            else:
                                action['loc']=self.vehicle_bufID[i]
                                
                                break
                else:
                    raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID) #chocp fix 2021/11/23
                
        elif action['type'] == 'SWAP':
            link_local_tr_cmd=local_tr_cmd.get('host_tr_cmd','').get('link','')
            if link_local_tr_cmd:
                uuid=link_local_tr_cmd.get('uuid','')
                carrierID=link_local_tr_cmd['carrierID']
            elif local_tr_cmd.get('host_tr_cmd','').get('replace', ''):
                carrierID=local_tr_cmd.get('host_tr_cmd','').get('carrierID')
            for i in range(self.bufNum):
                carrier=self.adapter.carriers[i]
                #fix support for stocker out
                record_command_id=self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-').rstrip('-LOAD')
                print('check AMR {}, record commandID={}, but buf carrier status={}, and link commandID={}'.format(self.vehicle_bufID[i], record_command_id, carrier['status'], uuid))
                if record_command_id and record_command_id in uuid: #2022/12/29 support replace -load/-unload
                    #if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'Unknown', 'PositionError']:
                    if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'PositionError']:  #chocp 2024/03/27 
                        if carrierID and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                            if carrier['status'] == carrierID:
                                action['loc']=self.vehicle_bufID[i]
                                break
                        else:
                            action['loc']=self.vehicle_bufID[i]
                            break
            else:
                raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID) #chocp fix 2021/11/23
        else:
            pass

    def enter_acquiring_state(self):
        self.AgvLastState=self.AgvState
        self.AgvState='Acquiring'
        self.enter_acquiring_state_time=time.time()

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '') #2023/12/29
        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
        to_point=tools.find_point(target)
        
        res_1, rack_id, port_no=tools.rackport_format_parse(target)
        if res_1: #8.22H1 for turntable
            h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
            if h_eRack and h_eRack.zonetype == 3 and h_eRack.carriers[port_no-1]['direction'] !='B':
                raise alarms.TurnTableCheckWarning(self.id, uuid, target, carrierID)

            if h_eRack and global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('ErackCassetteTypeCheck') == 'yes': #2023/12/29
                res_1=tools.erack_slot_type_verify(h_eRack, port_no, carrierType)
                if not res_1:
                    raise alarms.CommandSourceErackCarrierTypefailWarning(uuid, carrierID, carrierType, target, h_eRack.validSlotType)


        if not self.action_in_run['loc'] or self.action_in_run['loc']=='BUF00': #for not Buf prefer
            self.adapter.logger.info("why also me1111111111")
            self.action_loc_assign(self.action_in_run)

            

        else: #for Buf prefer
            try:
                print('GF bug', self.action_in_run['loc'])
                idx=self.vehicle_bufID.index(self.action_in_run['loc'])
                print(idx)
                print(self.vehicle_bufID)
                if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None':
                    local_tr_cmd["start_time"]=time.time()#2024/9/12 Yuri
                    self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
                    self.bufs_status[idx]['local_tr_cmd_mem']=local_tr_cmd
                else:
                    raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)
            except:
                raise alarms.BufferAcquireCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)


        EqMgr.getInstance().trigger(target, 'acquire_start_evt')
        self.h_eRackMgr.trigger(target, 'acquire_start_evt')

        E82.report_event(self.secsgem_e82_h,
                        E82.VehicleAcquireStarted,{
                        'VehicleID':self.id,
                        'CommandID':uuid, #chocp add 10/30
                        'TransferPort':target,
                        'CarrierID':carrierID,
                        'BatteryValue':self.adapter.battery['percentage']}) #change target carrierID.....

        output('VehicleAcquireStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':uuid,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge, #???
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':carrierID})

        res=False
        port=PortsTable.mapping[target]
        cont=0
        payload={}
        if global_variables.RackNaming == 36 and self.id in ["AMR04"]:
            check_source_is_or_not_3670=False
            check_dest_is_or_not_3670=False
            check_dest_is_or_not_erack=False
            h_workstation_target=EqMgr.getInstance().workstations.get(target)
            if h_workstation_target:
                if h_workstation_target.equipmentID in M1_global_variables.need_do_more_times_arm_EQ.keys():
                    
                    check_dest_is_or_not_erack=True
                else:
                    if h_workstation_target.workstation_type == "ErackPort":
                        check_dest_is_or_not_3670=True
                    else:
                        
                        
                        check_dest_is_or_not_3670=True
            else:
                check_source_is_or_not_3670=True

            
            if check_dest_is_or_not_3670:
                
                h_workstation_need_do_dest_port=EqMgr.getInstance().workstations.get(self.action_in_run.get("local_tr_cmd", {}).get("dest", ""))
                if h_workstation_need_do_dest_port:
                    if h_workstation_need_do_dest_port.equipmentID in M1_global_variables.need_do_more_times_arm_EQ.keys():
                        payload["EQ"]=M1_global_variables.need_do_more_times_arm_EQ.get(h_workstation_need_do_dest_port.equipmentID,0)
                        
                    else:
                        payload["EQ"]=0
                        
                else:
                    payload["EQ"]=0

            if check_dest_is_or_not_erack:
                
                
                h_workstation_check_dest_is_erack_port=EqMgr.getInstance().workstations.get(self.action_in_run.get("local_tr_cmd", {}).get("dest", ""))
                if h_workstation_check_dest_is_erack_port:#.workstation_type
                    if h_workstation_check_dest_is_erack_port.workstation_type == "ErackPort":
                        
                        payload["EQ"]=1
                    else:
                        check_source_is_or_not_3670=True
                        
                else:
                    payload["EQ"]=1
            if check_source_is_or_not_3670:
                h_workstation_need_do_source_port=EqMgr.getInstance().workstations.get(self.action_in_run.get("local_tr_cmd", {}).get("source", ""))
                if h_workstation_need_do_source_port:
                    if h_workstation_need_do_source_port.equipmentID in M1_global_variables.need_do_more_times_arm_EQ.keys():
                        payload["EQ"]=M1_global_variables.need_do_more_times_arm_EQ.get(h_workstation_need_do_source_port.equipmentID,0)
                        
                    else:
                        payload["EQ"]=0
                        
                else:
                    payload["EQ"]=0
            

                    
            transfer_info=local_tr_cmd.get("TransferInfo", {})
            carrier_ids=transfer_info.get("CarrierID", "")
            payload['pick']=len(carrier_ids.split(",")) if carrier_ids else 0

            if transfer_info.get("TOTAL"):
                payload['total']=transfer_info.get("TOTAL",0)
            else:
                payload['total']=len(carrier_ids.split(",")) if carrier_ids else 0

            
            
            
        self.adapter.logger.info("payload:{}".format(payload))
        carrier_type_index=1
        if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
            port=PortsTable.mapping[target]
            cont=0
            current_stop=port[0]
            current_direct=port[4]
            next_stop=PortsTable.mapping[self.actions[1].get('target', '')][0] if len(self.actions) > 1 else ''
            next_direct=PortsTable.mapping[self.actions[1].get('target', '')][4] if len(self.actions) > 1 else -1
            if current_stop == next_stop:
                if global_variables.TSCSettings.get('Other', {}).get('E84Continue', 'yes') == 'yes':
                    cont=1
                if self.actions[1]['type'] == 'DEPOSIT':
                    if carrierID and carrierID == self.actions[1]['local_tr_cmd']['carrierID']:
                        payload['NextBuffer']='BUFFER{:02d}'.format(self.vehicle_bufID.index(self.actions[0]['loc']))
                    else:
                        self.action_loc_assign(self.actions[1])
                        if self.actions[1]['loc']:
                            payload['NextBuffer']='BUFFER{:02d}'.format(self.vehicle_bufID.index(self.actions[1]['loc']))

        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            if carrierType not in global_variables.global_cassetteType and global_variables.RackNaming != 36:
                raise alarms.CarrierTypeCheckWarning(self.id, uuid, carrierID, carrierType)
            if carrierType:
                carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1
            #print('current_stop:{} {}, next_stop:{} {}, port_info:{}, carrierType_index:{}'.format(current_stop, current_direct, next_stop, next_direct, port, carrier_type_index))
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'):#8.28.9
                res=self.adapter.acquire_control(current_stop, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)
            else:
                res=self.adapter.acquire_control(target+'#'+carrierType, self.action_in_run['loc'], carrierID)
        else:
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'):
                target=current_stop
            res=self.adapter.acquire_control(target, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)

        if not res: # Mike: 2022/05/23
            raise alarms.RobotGetRightCheckWarning(self.id, uuid, self.action_in_run.get('target', ''))

        return

    def enter_shifting_state(self): #chocp 2024/8/21 for shift
        self.AgvLastState=self.AgvState
        self.AgvState='Shifting'
        self.enter_shifting_state_time=time.time() 

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '') #2023/12/29
        target=self.action_in_run.get('target', '')
        target2=self.action_in_run.get('target2', '')
        to_point=tools.find_point(target)

        cont=0
        carrier_type_index=1
        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            if carrierType not in global_variables.global_cassetteType and global_variables.RackNaming != 36:
                raise alarms.CarrierTypeCheckWarning(self.id, uuid, carrierID, carrierType)
            if carrierType:
                carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1
        if not self.adapter.version_check(self.adapter.mr_spec_ver, '4.0') or global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'no':
            raise alarms.ActionNotSupportWarning(self.id, uuid, self.action_in_run.get('target', ''))

        E82.report_event(self.secsgem_e82_h,
            E82.VehicleShiftStarted, {
            'VehicleID':self.id,
            'FromPort':target,
            'TransferPort':target2,
            'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
            'CommandID':uuid, # jason  add 10/30
            'ResultCode':0})


        output('VehicleShiftStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':uuid,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge, #???
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Source':target, 'Dest':target2, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':carrierID})

        res=False
        port=PortsTable.mapping[target]
        cont=0
        carrier_type_index=1
        current_stop=port[0]
        current_direct=port[4]
        next_stop=PortsTable.mapping[self.actions[1].get('target', '')][0] if len(self.actions) > 1 else ''
        next_direct=PortsTable.mapping[self.actions[1].get('target', '')][4] if len(self.actions) > 1 else -1
        if current_stop == next_stop and global_variables.TSCSettings.get('Other', {}).get('E84Continue', 'yes') == 'yes':
            cont=1

        res=False
        port=PortsTable.mapping[target]
        cont=0
        payload={}
        carrier_type_index=1

        if global_variables.RackNaming == 36 and self.id in ["AMR04"]:
            transfer_info=local_tr_cmd.get("TransferInfo", {})
            carrier_ids=transfer_info.get("CarrierID", "")
            payload['pick']=len(carrier_ids.split(",")) if carrier_ids else 0

            if transfer_info.get("TOTAL"):
                payload['total']=transfer_info.get("TOTAL",0)
            else:
                payload['total']=len(carrier_ids.split(",")) if carrier_ids else 0

        if global_variables.RackNaming == 33 and carrierID:
            payload['CarrierID'] = str(carrierID)
        if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
            port=PortsTable.mapping[target]
            cont=0
            current_stop=port[0]
            current_direct=port[4]
            next_stop=PortsTable.mapping[self.actions[1].get('target', '')][0] if len(self.actions) > 1 else ''
            next_direct=PortsTable.mapping[self.actions[1].get('target', '')][4] if len(self.actions) > 1 else -1
            if current_stop == next_stop:
                if global_variables.TSCSettings.get('Other', {}).get('E84Continue', 'yes') == 'yes':
                    cont=1
                if self.actions[1]['type'] == 'DEPOSIT':
                    self.action_loc_assign(self.actions[1])
                    if self.actions[1]['loc']:
                        payload['NextBuffer']='BUFFER{:02d}'.format(self.vehicle_bufID.index(self.actions[1]['loc']))

        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            if carrierType not in global_variables.global_cassetteType and global_variables.RackNaming != 36:
                raise alarms.CarrierTypeCheckWarning(self.id, uuid, carrierID, carrierType)
            if carrierType:
                carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1

        try:
            port2=PortsTable.mapping[target2]
            target=port[0]
            target2=port2[0]
            res=self.adapter.shift_control(target, target2, carrierID, e84=port[4], cs=port[5], cont=cont, fpn=port[6], tpn=port2[6], ct=carrier_type_index)
        except:
            pass

        if not res: # Mike: 2022/05/23
            raise alarms.RobotGetRightCheckWarning(self.id, uuid, self.action_in_run.get('target', ''))

        return

    def enter_depositing_state(self, height=0):
        self.AgvLastState=self.AgvState
        self.AgvState='Depositing'
        self.enter_depositing_state_time=time.time() 

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '') #2023/12/29
        target=self.action_in_run.get('target', '')
        to_point=tools.find_point(target)

        res_1, rack_id, port_no=tools.rackport_format_parse(target)
        if res_1:
            h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
            if h_eRack and h_eRack.zonetype ==3 and h_eRack.carriers[port_no-1]['direction'] !='F':
                raise alarms.TurnTableCheckWarning(self.id, uuid, target, carrierID)

            if h_eRack and global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('ErackCassetteTypeCheck') == 'yes': #2023/12/29
                res_1=tools.erack_slot_type_verify(h_eRack, port_no, carrierType)
                if not res_1:
                    raise alarms.CommandDestErackCarrierTypefailWarning(uuid, carrierID, carrierType, target, h_eRack.validSlotType)
                    
        if not self.action_in_run['loc']: #select a buffer for deposit, need check
            self.action_loc_assign(self.action_in_run)

            """if global_variables.RackNaming == 15: # JWO 2023/09/20 for GF
                # Check if 'SourcePort' contains "BUF"
                source_port=local_tr_cmd.get('TransferInfo', {}).get('SourcePort', '')
                print("SOURCE:", source_port)
                if "BUF" in source_port:
                    # Extract the buffer number
                    try:
                        buf_number=int(source_port[-2:])  # Assuming the format is always "BUFXX"
                        print('MRBUF_NUM',  buf_number)
                    except:
                        #raise
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

                    if self.enableBuffer[buf_number-1] == 'yes' and self.adapter.carriers[buf_number-1]['status'] not in ['None', 'Unknown', 'PositionError']:
                        self.action_in_run['loc']=self.vehicle_bufID[buf_number-1]

                    else:
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID)

                else:
                    for i in range(self.bufNum):
                        carrier=self.adapter.carriers[i]

                        #fix support for stocker out
                        record_command_id=self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-')
                        print('check AMR {}, record commandID={}, but buf carrier status={}, and deposit commandID={}'.format(self.vehicle_bufID[i], record_command_id, carrier['status'], uuid))
                        if record_command_id and record_command_id in uuid: #2022/12/29 support replace -load/-unload
                            if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'Unknown', 'PositionError']:
                                if carrierID and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                    if carrier['status'] == carrierID:
                                        self.action_in_run['loc']=self.vehicle_bufID[i]
                                        break
                                else:
                                    self.action_in_run['loc']=self.vehicle_bufID[i]
                                    break
                    else:
                        raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID) #chocp fix 2021/11/23

            else:
                for i in range(self.bufNum):
                    carrier=self.adapter.carriers[i]

                    #fix support for stocker out
                    record_command_id=self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-')
                    print('check AMR {}, record commandID={}, but buf carrier status={}, and deposit commandID={}'.format(self.vehicle_bufID[i], record_command_id, carrier['status'], uuid))
                    if record_command_id and record_command_id in uuid: #2022/12/29 support replace -load/-unload
                        #if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'Unknown', 'PositionError']:
                        if self.enableBuffer[i] == 'yes' and carrier['status'] not in ['None', 'PositionError']:  #chocp 2024/03/27 
                            
                            if carrierID and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                if carrier['status'] == carrierID:
                                    self.action_in_run['loc']=self.vehicle_bufID[i]
                                    
                                    break
                            else:
                                self.action_in_run['loc']=self.vehicle_bufID[i]
                                
                                break
                else:
                    raise alarms.BufferDepositCheckWarning(self.id, uuid, 'NO_VALID_BUF', carrierID) #chocp fix 2021/11/23"""

        
        if carrierID == '' or carrierID == 'None': #chocp fix for tfme 2021/10/23
            carrierID=self.re_assign_carrierID(self.action_in_run['loc'])
            local_tr_cmd['carrierID']=carrierID
            local_tr_cmd['TransferInfo']['CarrierID']=carrierID

        EqMgr.getInstance().trigger(target, 'deposit_start_evt')
        self.h_eRackMgr.trigger(target, 'deposit_start_evt')

        E82.report_event(self.secsgem_e82_h,
                        E82.VehicleDepositStarted,{
                        'VehicleID':self.id,
                        'CommandID':uuid, #chocp add 10/30
                        'TransferPort':target,
                        'CarrierID':carrierID,
                        'BatteryValue':self.adapter.battery['percentage']})

        output('VehicleDepositStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':uuid,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge,
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':carrierID})

        res=False
        port=PortsTable.mapping[target]
        cont=0
        payload={}
        if global_variables.RackNaming == 36 and self.id in ["AMR04"]:

            h_workstation_target=EqMgr.getInstance().workstations.get(target)
            if h_workstation_target:
                if h_workstation_target.workstation_type == "ErackPort":
                    h_workstation_check_source_is_3670=EqMgr.getInstance().workstations.get(self.action_in_run.get("local_tr_cmd", {}).get("source", ""))
                    if h_workstation_check_source_is_3670:
                        if h_workstation_check_source_is_3670.equipmentID in M1_global_variables.need_do_more_times_arm_EQ.keys():
                            payload["EQ"]=3670
                        else:
                            payload["EQ"]=0
                    else:
                        payload["EQ"]=0
                else:
                    payload["EQ"]=0
            else:
                payload["EQ"]=0

            transfer_info=local_tr_cmd.get("TransferInfo", {})
            carrier_ids=transfer_info.get("CarrierID", "")
            payload['pick']=len(carrier_ids.split(",")) if carrier_ids else 0

            if transfer_info.get("TOTAL"):
                payload['total']=transfer_info.get("TOTAL",0)
            else:
                payload['total']=len(carrier_ids.split(",")) if carrier_ids else 0
                
            

            
        if height:
            payload['Height']=height
        carrier_type_index=1
        if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
            port=PortsTable.mapping[target]
            cont=0
            current_stop=port[0]
            current_direct=port[4]
            next_stop=PortsTable.mapping[self.actions[1].get('target', '')][0] if len(self.actions) > 1 else ''
            next_direct=PortsTable.mapping[self.actions[1].get('target', '')][4] if len(self.actions) > 1 else -1
            if current_stop == next_stop:
                if global_variables.TSCSettings.get('Other', {}).get('E84Continue', 'yes') == 'yes':
                    cont=1
                if self.actions[1]['type'] == 'DEPOSIT':
                    self.action_loc_assign(self.actions[1])
                    if self.actions[1]['loc']:
                        payload['NextBuffer']='BUFFER{:02d}'.format(self.vehicle_bufID.index(self.actions[1]['loc']))

        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            if carrierType not in global_variables.global_cassetteType and global_variables.RackNaming != 36:
                raise alarms.CarrierTypeCheckWarning(self.id, uuid, carrierID, carrierType)
            if carrierType:
                carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1
            #print('current_stop:{} {}, next_stop:{} {}, port_info:{}, carrierType_index:{}'.format(current_stop, current_direct, next_stop, next_direct, port, carrier_type_index))
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'): #8.28.9
                res=self.adapter.deposite_control(current_stop, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)
            else:
                res=self.adapter.deposite_control(target+'#'+carrierType, self.action_in_run['loc'], carrierID)
        else:
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'):
                target=current_stop
            res=self.adapter.deposite_control(target, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)

        
        if not res: # Mike: 2022/05/23
            raise alarms.RobotGetRightCheckWarning(self.id, uuid, self.action_in_run.get('target', ''))

        return

    def enter_swap_state(self):
        self.AgvLastState=self.AgvState
        self.AgvState='Swapping'
        self.enter_swapping_state_time=time.time() 

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '') #2023/12/29
        target=self.action_in_run.get('target', '')
        to_point=tools.find_point(target)
        
        res_1, rack_id, port_no=tools.rackport_format_parse(target)
        if res_1:
            h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
            if h_eRack and global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('ErackCassetteTypeCheck') == 'yes': #2023/12/29
                res_1=tools.erack_slot_type_verify(h_eRack, port_no, carrierType)
                if not res_1:
                    raise alarms.CommandDestErackCarrierTypefailWarning(uuid, carrierID, carrierType, target, h_eRack.validSlotType)
                    
        if not self.action_in_run['loc']: #select a buffer for deposit, need check
            self.action_loc_assign(self.action_in_run)
        

        E82.report_event(self.secsgem_e82_h,
                        E82.VehicleSwapStarted,{
                        'VehicleID':self.id,
                        #'CommandID':uuid, #chocp add 10/30
                        'TransferPort':target,
                        #'CarrierID':carrierID,
                        'BatteryValue':self.adapter.battery['percentage']})

        output('VehicleSwapStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':uuid,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge,
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':carrierID})

        res=False
        port=PortsTable.mapping[target]
        cont=0
        payload={}
        payload['Swap']=True
        
        carrier_type_index=1
        if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
            port=PortsTable.mapping[target]
            cont=0
            current_stop=port[0]

        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            if carrierType not in global_variables.global_cassetteType:
                raise alarms.CarrierTypeCheckWarning(self.id, uuid, carrierID, carrierType)

            carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1
            #print('current_stop:{} {}, next_stop:{} {}, port_info:{}, carrierType_index:{}'.format(current_stop, current_direct, next_stop, next_direct, port, carrier_type_index))
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'): #8.28.9
                res=self.adapter.swap_control(current_stop, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)
            else:
                res=self.adapter.swap_control(target+'#'+carrierType, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)
        else:
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7 and self.adapter.version_check(self.adapter.mr_spec_ver, '2.5'):
                target=current_stop
            res=self.adapter.swap_control(target, self.action_in_run['loc'], carrierID, e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index, **payload)

        
        if not res: # Mike: 2022/05/23
            raise alarms.RobotGetRightCheckWarning(self.id, uuid, self.action_in_run.get('target', ''))

        return

    def execute_action(self, force_route=False, force_cost= -1, force_path=[]): #fix 8/20
        #self.ResultCode=0
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd.get('carrierID', '') # '' == 'None'
        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '')

        target=self.action_in_run.get('target', '')
        #to_station=self.action_in_run['target']
        to_point=tools.find_point(target)
        

        if force_route or self.action_in_run['type'] in ['GOTO'] or self.at_station == '' or (self.adapter.last_point!=to_point): #fix 8/20
            
            if self.actions:
                if self.actions[0]['type'] == 'EXCHANGE':
                    h_ABCS=Iot.h.devices.get(target, None)
                    if h_ABCS:
                        h_ABCS.put_batt()
                        
            block_nodes=[] # Mike: 2021/12/07
            for car in global_variables.global_vehicles_location_index: # Mike: 2021/04/06
                if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                    group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                    for group in group_list:
                        block_nodes += global_variables.global_group_to_node.get(group, [])

            if force_cost >=0:
                cost=force_cost
                path=force_path
                self.adapter.logger.info('{} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_force:', cost, path, self.adapter.last_point, to_point, algo=global_variables.RouteAlgo))
            else:
                cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                self.adapter.logger.info('{} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route:', cost, path, self.adapter.last_point, to_point, algo=global_variables.RouteAlgo))
                if cost == -2:
                    self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, to_point), global_variables.global_disable_nodes, global_variables.global_disable_edges))

            # Mike: 2022/02/08
            cost_b, path_b=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+block_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
            self.adapter.logger.info('{} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block:', cost_b, path_b, self.adapter.last_point, to_point))
            if cost_b == -2:
                self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, to_point), global_variables.global_disable_nodes+block_nodes, global_variables.global_disable_edges))

            # Mike: 2022/02/08
            if cost_b > 0 and (cost_b-cost) < global_variables.TSCSettings.get('TrafficControl',{}).get('MaxFindWayCost', 60000) and global_variables.TSCSettings.get('TrafficControl', {}).get('EnableFindWay', 'yes').lower() == 'yes':
                cost, path=cost_b, path_b
                
            if cost < 0:
                raise alarms.BaseRouteWarning(self.id, uuid, self.adapter.last_point, to_point, handler=self.secsgem_e82_h)
                  
            if self.appendTransferAllowed == 'yes' and self.appendTransferAlgo == 'appendTransferMovePath' and tools.appendTransferJudgment(self.actions,self.adapter.last_point):# Yuri 2024/11/27
                num, buf_list=self.buf_available()
                if num:
                    if self.wq and tools.acquire_lock_with_timeout(self.wq.wq_lock,3):
                    #self.wq.wq_lock.acquire()
                        try:
                            command_id_list=[]
                            enroute_append_tr=self.wq.tr_point.keys()
                            point_list=[x for x in path if x in enroute_append_tr][::-1]
                            #point_list=list((set(copy.deepcopy(path)) & set(copy.deepcopy(enroute_append_tr))))
                            if enroute_append_tr and point_list:
                                for point in point_list:
                                    host_tr_cmd=self.wq.tr_point[point]
                                    if num <= 0:
                                        break
                                    if len(host_tr_cmd) > 1:                        
                                        for local_host_tr_cmd in host_tr_cmd:
                                            if num <= 0:
                                                break
                                            buf=tools.allocate_buffer(buf_list,local_host_tr_cmd[1],self.check_carrier_type,self.vehicle_onTopBufs,self.carriertypedict,self.bufferDirection)
                                            if not buf:
                                                self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'No  CarrierType or BufConstrain buffer',local_host_tr_cmd[1].get("uuid","")))
                                                continue
                                            buf_list.remove(buf)
                                            self.wq.remove_waiting_transfer_by_idx(local_host_tr_cmd[1], local_host_tr_cmd[0],remove_directly=True)
                                            self.append_transfer(local_host_tr_cmd[1],buf)
                                            command_id_list.append(local_host_tr_cmd[1].get("uuid",""))
                                            num -= 1                      
                                    else:
                                        buf=tools.allocate_buffer(buf_list,host_tr_cmd[0][1],self.check_carrier_type,self.vehicle_onTopBufs,self.carriertypedict,self.bufferDirection)
                                        if not buf:
                                            self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'No  CarrierType or BufConstrain buffer',host_tr_cmd[0][1].get("uuid","")))
                                            continue
                                        buf_list.remove(buf)
                                        self.wq.remove_waiting_transfer_by_idx(host_tr_cmd[0][1], host_tr_cmd[0][0],remove_directly=True)
                                        self.append_transfer(host_tr_cmd[0][1],buf)
                                        command_id_list.append(host_tr_cmd[0][1].get("uuid",""))
                                        num -= 1
                                if command_id_list:
                                    self.CommandIDList.extend(command_id_list)
                                    self.adapter.logger.info("{} appendTransferMovePath by {}".format('[{}] '.format(self.id),','.join(str(command_id) for command_id in command_id_list)))
                                    E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleAssigned,{
                                                'VehicleID':self.id,
                                                'CommandIDList':self.CommandIDList,
                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                'BatteryValue':self.adapter.battery['percentage']})

                                    output('VehicleAssigned',{
                                                'Battery':self.adapter.battery['percentage'],
                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                'Connected':self.adapter.online['connected'],
                                                'Health':self.adapter.battery['SOH'],
                                                'MoveStatus':self.adapter.move['status'],
                                                'RobotStatus':self.adapter.robot['status'],
                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                'VehicleID':self.id,
                                                'VehicleState':self.AgvState,
                                                'Message':self.message,
                                                'ForceCharge':self.force_charge, #???
                                                'CommandIDList':self.CommandIDList})

                                self.wq.wq_lock.release()
                                self.AgvLastState=self.AgvState  #fix 8/20
                                self.AgvState="Parked"

                                #self.action_in_run=self.actions[0]
                                #return self.execute_action()
                                return

                            self.wq.wq_lock.release()
                        except:
                            self.wq.wq_lock.release()
                            msg=traceback.format_exc()
                            self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))


            self.AgvLastState=self.AgvState
            self.AgvState='Enroute'

            #need fix
            if carrierID == '' or carrierID == 'None': #chocp fix for tfme 2021/10/23
                carrierID=self.re_assign_carrierID(self.action_in_run['loc'])
                local_tr_cmd['carrierID']=carrierID
                local_tr_cmd['TransferInfo']['CarrierID']=carrierID

            #event if un-assigned also add departed!
            if PortsTable.reverse_mapping[self.adapter.last_point]:
                TransferPort=PortsTable.reverse_mapping[self.adapter.last_point][0]
                if len(PortsTable.reverse_mapping[self.adapter.last_point]) > 1:
                    if self.at_station in PortsTable.reverse_mapping[self.adapter.last_point]:
                        TransferPort=self.at_station
            else:
                TransferPort=self.adapter.last_point
                
            if global_variables.RackNaming == 53: #Kumamoto TPB
                #Open Erack Door when Departed Sean 241030
                result, rack_id, port_no=tools.rackport_format_parse(target)
                h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
                if carrierID and h_eRack:
                    result=h_eRack.open_erack_door(port_no)
                    if not result:
                        pass
                
                h_eRack.check_door_operation()

            #if global_variables.RackNaming == 3: #for tfme
            if global_variables.RackNaming != 36:#K11 alway need report VehicleDeparted
                if not force_route:
                    if global_variables.TSCSettings.get('Other', {}).get('ReportFromPortWhenVehicleDeparted') == 'yes':
                        E82.report_event(self.secsgem_e82_h, #fix 
                                        E82.VehicleDeparted, {
                                        'VehicleID':self.id,
                                        'CommandID':uuid,
                                        'TransferPort':target,
                                        'BatteryValue':self.adapter.battery['percentage']})
                    else:
                        E82.report_event(self.secsgem_e82_h,
                                        E82.VehicleDeparted, {
                                        'VehicleID':self.id,
                                        'CommandID':uuid,
                                        'TransferPort':TransferPort,
                                        'TransferPortList':PortsTable.reverse_mapping[self.adapter.last_point],
                                        'BatteryValue':self.adapter.battery['percentage']}) #fix 8/20
            else:
                E82.report_event(self.secsgem_e82_h, #fix 
                    E82.VehicleDeparted, {
                    'VehicleID':self.id,
                    'CommandID':uuid,
                    'TransferPort':target,
                    'TransferPortList':PortsTable.reverse_mapping[self.adapter.last_point],
                    'BatteryValue':self.adapter.battery['percentage']})

            travel=local_tr_cmd.get('travel', 0)
            local_tr_cmd['travel']=travel+cost

            output('VehicleDeparted', {
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'VehicleID':self.id,
                    'CommandID':uuid,
                    'Travel':cost,
                    'VehicleState':self.AgvState,
                    'Message':self.message,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                    'TransferPort':target})
            #for K25
            '''if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                if self.at_station and self.adapter.last_point == to_point and PoseTable.mapping[self.adapter.last_point].get('type') == 'chargestation':
                    pass
                else:
                    if self.enable_begin_flag == 'yes' and not self.no_begin:
                        self.adapter.move_control(path, True, True)
                    else:
                        self.no_begin=False
                        self.adapter.move_control(path, False, True)'''
            h_workstation=EqMgr.getInstance().workstations.get(target)
            check=False
            if h_workstation and h_workstation.workstation_type == 'LifterPort':
                check=True
            if self.at_station and self.adapter.last_point == to_point and self.adapter.move['arrival'] == 'EndArrival' and not check:
                pass
            else:
                if self.enable_begin_flag == 'yes' and not self.no_begin:
                    self.adapter.move_control(path, True, True)
                else:
                    self.no_begin=False
                    self.adapter.move_control(path, False, True)


        elif self.action_in_run['type'] == 'ACQUIRE_STANDBY':
            self.AgvLastState=self.AgvState
            self.AgvState='Waiting'

        elif self.action_in_run['type'] == 'HostMove':
            self.actions.popleft() #unknown action type
            if self.host_call_waiting_time and self.host_call_target == self.at_station:
                self.AgvLastState=self.AgvState  #fix 8/20
                self.AgvState='Waiting'
                self.enter_host_call_waiting_time=time.time()

        elif self.action_in_run['type'] == 'ACQUIRE':
            
            for i in range(self.bufNum): #2024/09/20 
                if self.enableBuffer[i] == 'yes' and carrierID and carrierID == self.adapter.carriers[i]['status']:#execute acquire action but carrier already on MR buf
                    try:
                        if self.action_in_run == self.actions[0]: 
                            if not self.bufs_status[i]['local_tr_cmd']:
                                self.bufs_status[i]['local_tr_cmd']=self.action_in_run.get('local_tr_cmd', {})
                            self.actions.popleft()
                            self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'execute acquire action but carrier already on MR buf', carrierID))
                            E82.report_event(self.secsgem_e82_h,
                                E82.VehicleAcquireStarted,{
                                'VehicleID':self.id,
                                'CommandID':uuid, 
                                'TransferPort':target,
                                'CarrierID':carrierID}) 
                            
                            E82.report_event(self.secsgem_e82_h,
                                E82.VehicleAcquireCompleted, {
                                'VehicleID':self.id,
                                'CarrierLoc':self.id+self.vehicle_bufID[i],
                                'CommandID':uuid, 
                                'TransferPort':target,
                                'CarrierID':carrierID, 
                                'ResultCode':0}) 
                            return
                    except:
                        self.adapter.logger.error('{} {} {}'.format('[{}] '.format(self.id), 'Vehicle remove acquire action fail', traceback.format_exc())) 
            h_workstation=EqMgr.getInstance().workstations.get(target) #8.21H-4
            if h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                self.last_action_is_for_workstation=True
            else:
                self.last_action_is_for_workstation=False
    
            target_pt=tools.find_point(target)
            target_pose=[PoseTable.mapping[target_pt]['x'], PoseTable.mapping[target_pt]['y']]

            near_pt=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']])[0]
            real_pose=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
            real_diff=math.sqrt((target_pose[0] - real_pose[0])**2 + (target_pose[1] - real_pose[1])**2)
            self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'unload station check', target_pt, near_pt, real_diff))

            if (target_pt != near_pt) and real_diff > global_variables.TSCSettings.get('TrafficControl', {}).get('NearDistance'): #100mm
                raise alarms.PortNotReachWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

            res, rack_id, port_no=tools.rackport_format_parse(target)
            if res:
                if self.eRackPortStatusUnloadCheck(target, carrierID):# carrierID corrected and checked?
                    self.enter_acquiring_state()
                else:
                    raise alarms.RackAcquireCheckWarning(self.id, uuid, target, carrierID, handler=self.secsgem_e82_h)


            elif global_variables.TSCSettings.get('Safety', {}).get('TrUnLoadReqCheck')!='yes':
                self.enter_acquiring_state()
            else:
                #add validinput mask fo LG
                valid_input=getattr(h_workstation, 'valid_input', True)
                if not valid_input: #chocp add 2022/4/14
                    self.enter_acquiring_state() 
                    return
                if global_variables.RackNaming in [33, 42, 58] and self.error_skip_tr_req and self.tr_assert_result and self.tr_assert_result == target:
                    self.error_skip_tr_req=False
                    self.enter_acquiring_state() 
                    return
                self.AgvLastState=self.AgvState
                self.AgvState='TrUnLoadReq'
                self.TrUnLoadReqTime=time.time()
                self.tr_assert={}

                if getattr(h_workstation, 'open_door_assist', False):
                    E82.report_event(self.secsgem_e82_h,
                                 E82.TrUnLoadWithGateReq,{
                                 'VehicleID':self.id,
                                 'TransferPort':target,
                                 'CarrierID':carrierID,
                                 'CommandID':uuid,
                                 'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})
                else:
                    if global_variables.RackNaming == 20 and 'Stock' in h_workstation.workstation_type: #chocp 2024/03/29
                        if h_workstation.state == 'Loaded':
                            self.tr_assert={'Request':'UnLoad', 'Result':'OK', 'TransferPort':target, 'CarrierID':carrierID,'SendBy':'by host'}  
                    else:
                        E82.report_event(self.secsgem_e82_h,
                                    E82.TrUnLoadReq,{
                                    'VehicleID':self.id,
                                    'TransferPort':target,
                                    'CarrierID':carrierID,
                                    'CommandID':uuid,
                                    'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                output('TrUnLoadReq',{
                        'VehicleID':self.id,
                        'VehicleState':self.AgvState,
                        'Station':self.at_station,
                        'Message':self.message,
                        'TransferPort':target,
                        'CarrierID':carrierID})

                self.ValidInputLastReqTime=time.time()

        elif self.action_in_run['type'] == 'SHIFT': #chocp 2024/8/21 for shift
            if global_variables.RackNaming in [36,46,47]:
                h_workstation=EqMgr.getInstance().workstations.get(self.action_in_run['target2'])

                if h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                    self.last_action_is_for_workstation=True
                    self.last_action_eqID=h_workstation.equipmentID
                else:
                    self.last_action_is_for_workstation=False
            target2=self.action_in_run['target2']

            target_pt=self.action_in_run['point']
            target_pose=[PoseTable.mapping[target_pt]['x'], PoseTable.mapping[target_pt]['y']]

            near_pt=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']])[0]
            real_pose=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
            real_diff=math.sqrt((target_pose[0] - real_pose[0])**2 + (target_pose[1] - real_pose[1])**2)

            self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'shift station check', target_pt, near_pt, real_diff))

            if (target_pt != near_pt) and real_diff > global_variables.TSCSettings.get('TrafficControl', {}).get('NearDistance'): #100mm
                raise alarms.PortNotReachWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14
            res, rack_id, port_no=tools.rackport_format_parse(target)
            if res:
                if self.eRackPortStatusUnloadCheck(target, carrierID):# carrierID corrected and checked?
                    self.enter_shifting_state()
                else:
                    raise alarms.RackAcquireCheckWarning(self.id, uuid, target, carrierID, handler=self.secsgem_e82_h)
            elif global_variables.TSCSettings.get('Safety', {}).get('TrShiftReqCheck','no')!='yes':
                
                self.enter_shifting_state()
            else:
                #add validinput mask fo LG
                valid_input=getattr(h_workstation, 'valid_input', True)
                if not valid_input: #chocp add 2022/4/14
                    self.enter_shifting_state()
                    return

                self.AgvLastState=self.AgvState
                self.AgvState='TrShiftReqCheck'
                self.TrShiftReqTime=time.time()
                self.tr_assert={}

                
                E82.report_event(self.secsgem_e82_h,
                            E82.TrShiftReq,{
                            'VehicleID':self.id,
                            'TransferPort':target,
                            'CarrierID':carrierID,
                            'CommandID':uuid,
                            'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})
                self.ValidInputLastReqTime=time.time()

        elif self.action_in_run['type'] == 'DEPOSIT':
            h_workstation=EqMgr.getInstance().workstations.get(target) #8.21H-4
            if h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                self.last_action_is_for_workstation=True
            else:
                self.last_action_is_for_workstation=False

            target_pt=tools.find_point(target)
            target_pose=[PoseTable.mapping[target_pt]['x'], PoseTable.mapping[target_pt]['y']]

            near_pt=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']])[0]
            real_pose=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
            real_diff=math.sqrt((target_pose[0] - real_pose[0])**2 + (target_pose[1] - real_pose[1])**2)
            self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'load station check', target_pt, near_pt, real_diff))

            if (target_pt != near_pt) and real_diff > global_variables.TSCSettings.get('TrafficControl', {}).get('NearDistance'): #100mm
                raise alarms.PortNotReachWarning(self.id, uuid, target, handler=self.secsgem_e82_h)

            res, rack_id, port_no=tools.rackport_format_parse(target)
            if res:
                if self.eRackPortStatusEmpty(target):
                    self.enter_depositing_state()
                    return
                #else: #dynamic assign
                elif global_variables.TSCSettings.get('Recovery', {}).get('ReAssignErackDestPortWhenOccupied') == 'yes':
                    #chocp 9/1 add if rack port be occupied try reassign to another port in same rack

                    port_areas_revert=getattr(self.h_eRackMgr, 'port_areas_revert', {}) #chocp add 2022/4/12 for LG, GMP
                    area_id=port_areas_revert.get(target)
                    if area_id:
                        res, target=tools.new_auto_assign_dest_port(area_id, carrierType) 
                    else:
                        res, target=tools.new_auto_assign_dest_port(rack_id, carrierType)

                    if res:
                        tools.book_slot(target, self.id)
                        alarms.RackEmptyCheckWarning(self.id, uuid, target, carrierID) #chocp fix 2022/4/14
                        self.actions[0]['target']=target

                        local_tr_cmd['TransferInfo']['DestPort']=target #chocp fix 2022/2/8

                        self.AgvLastState=self.AgvState
                        self.AgvState='Parked'
                    else: #dynamic assign fail
                        raise alarms.RackDepositCheckWarning(self.id, uuid, target, carrierID)
                else:
                    raise alarms.RackDepositCheckWarning(self.id, uuid, target, carrierID)

 
            #elif global_variables.TSCSettings.get('Safety', {}).get('TrLoadReqCheck')!='yes': #chocp fix for spil LG(5)
            #    self.enter_depositing_state()
            #    return

            #chocp fix for spil LG(5)
            elif global_variables.TSCSettings.get('Safety', {}).get('TrLoadReqCheck')!='yes':
                self.enter_depositing_state()
                return

            #elif global_variables.RackNaming not in [5,6] and \
            elif global_variables.TSCSettings.get('Safety', {}).get('SkipTrLoadReqWhenSwapTask') == 'yes' and\
                (self.AgvLastState == 'Acquiring' and target == self.LastAcquireTarget): #bug need check???????????
                self.enter_depositing_state()
                return
                
            else:
                #add validinput mask fo LG
                valid_input=getattr(h_workstation, 'valid_input', True)
                if not valid_input: #chocp add 2022/4/14
                    self.enter_depositing_state()
                    return
                if global_variables.RackNaming in [33, 42, 58] and self.error_skip_tr_req and self.tr_assert_result and self.tr_assert_result == target:
                    self.error_skip_tr_req=False
                    self.enter_depositing_state()  
                    return
                self.AgvLastState=self.AgvState
                self.AgvState='TrLoadReq'
                self.TrLoadReqTime=time.time()
                self.tr_assert={}

                if getattr(h_workstation, 'open_door_assist', False):
                    E82.report_event(self.secsgem_e82_h,
                                 E82.TrLoadWithGateReq, {
                                 'VehicleID':self.id,
                                 'TransferPort':target,
                                 'CarrierID':carrierID,
                                 'CommandID':uuid,
                                 'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})
                else:
                    if global_variables.RackNaming == 20 and 'Stock' in h_workstation.workstation_type: #chocp 2024/03/29
                        if h_workstation.state == 'UnLoaded':
                            self.tr_assert={'Request':'Load', 'Result':'OK', 'TransferPort':target, 'CarrierID':carrierID,'SendBy':'by host'}  
                    else:
                        E82.report_event(self.secsgem_e82_h,
                                    E82.TrLoadReq, {
                                    'VehicleID':self.id,
                                    'TransferPort':target,
                                    'CarrierID':carrierID,
                                    'CommandID':uuid,
                                    'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                output('TrLoadReq',{
                        'VehicleID':self.id,
                        'VehicleState':self.AgvState,
                        'Station':self.at_station,
                        'Message':self.message,
                        'TransferPort':target,
                        'CarrierID':carrierID})

                self.ValidInputLastReqTime=time.time()
                
        elif self.action_in_run['type'] == 'SWAP':
            h_workstation=EqMgr.getInstance().workstations.get(target) #8.21H-4
            target_pt=tools.find_point(target)
            target_pose=[PoseTable.mapping[target_pt]['x'], PoseTable.mapping[target_pt]['y']]

            near_pt=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']])[0]
            real_pose=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
            real_diff=math.sqrt((target_pose[0] - real_pose[0])**2 + (target_pose[1] - real_pose[1])**2)
            self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'swap station check', target_pt, near_pt, real_diff))

            if (target_pt != near_pt) and real_diff > global_variables.TSCSettings.get('TrafficControl', {}).get('NearDistance'): #100mm
                raise alarms.PortNotReachWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

            res, rack_id, port_no=tools.rackport_format_parse(target)
            if res:
                if self.eRackPortStatusUnloadCheck(target, carrierID):# carrierID corrected and checked?
                    self.enter_swap_state()
                else:
                    raise alarms.RackAcquireCheckWarning(self.id, uuid, target, carrierID, handler=self.secsgem_e82_h)


            elif global_variables.TSCSettings.get('Safety', {}).get('TrSwapReqCheck','')!='yes':
                self.enter_swap_state()
            else:
                #add validinput mask fo LG
                valid_input=getattr(h_workstation, 'valid_input', True)
                if not valid_input: #chocp add 2022/4/14
                    self.enter_swap_state() 
                    return

                self.AgvLastState=self.AgvState
                self.AgvState='TrSwapReq'
                self.TrSwapReqTime=time.time()
                self.tr_assert={}

                E82.report_event(self.secsgem_e82_h,
                            E82.TrSwapReq,{
                            'VehicleID':self.id,
                            'TransferPort':target,
                            'CarrierID':carrierID,
                            'CommandID':uuid,
                            'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                output('TrSwapReq',{
                        'VehicleID':self.id,
                        'VehicleState':self.AgvState,
                        'Station':self.at_station,
                        'Message':self.message,
                        'TransferPort':target,
                        'CarrierID':carrierID})

                self.ValidInputLastReqTime=time.time()

        elif self.action_in_run['type'] == 'CHARGE':
            #need add go
            self.AgvLastState=self.AgvState
            self.AgvState='Charging'
            self.call_support_time=time.time() #chocp 2022/4/12

            E82.report_event(self.secsgem_e82_h,
                             E82.VehicleChargeStarted, {
                             'VehicleID':self.id,
                             'BatteryValue':self.adapter.battery['percentage']})

            output('VehicleChargeStarted',{
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'TransferPort':target,
                    'VehicleID':self.id,
                    'CommandID':uuid,
                    'VehicleState':self.AgvState,
                    'Station':self.at_station,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':to_point},
                    'Message':self.message})

            self.charge_start_time=time.time()
            if not self.adapter.charge_start():
                alarms.ChargeCommandTimeoutWarning(self.id, uuid, self.at_station) #chocp 2021/12/10


        elif self.action_in_run['type'] == 'EXCHANGE':
            #need add go
            self.AgvLastState=self.AgvState
            self.AgvState='Exchanging'
            # self.call_support_time=time.time() #chocp 2022/4/12

            # h_ABCS=Iot.h.devices.get(target, None)
            # if h_ABCS:
            #     h_ABCS.put_batt()

            E82.report_event(self.secsgem_e82_h,
                             E82.VehicleExchangeStarted, {
                             'VehicleID':self.id,
                             'BatteryValue':self.adapter.battery['percentage']})

            output('VehicleExchangeStarted',{
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'TransferPort':target,
                    'VehicleID':self.id,
                    'CommandID':uuid,
                    'VehicleState':self.AgvState,
                    'Station':self.at_station,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':uuid, 'CarrierID':carrierID, 'Dest':target, 'ToPoint':to_point},
                    'Message':self.message})

            self.charge_start_time=time.time()
            if not self.adapter.exchange_start():
                # warning
                pass

        elif self.action_in_run['type'] == 'INPUT': #for K25
            try:
                if self.action_in_run == self.actions[0]: #if same obj do pop, to avoid pop other valid action #chocp 2022/7/11
                    self.actions.popleft()
                
                h_workstation=EqMgr.getInstance().workstations.get(target) 
                if h_workstation:
                    if 'Stock' in h_workstation.workstation_type:
                        self.input_cmd_open_again=True
            except:
                pass
        else:
            self.actions.popleft() #unknown action type
            pass

        from_port=local_tr_cmd.get('TransferInfo', {}).get('SourcePort', '')
        to_port=local_tr_cmd.get('TransferInfo', {}).get('DestPort', '')
        self.adapter.current_cmd_control(0, uuid, from_port, to_port, carrierID)

        return

    def buf_residual(self):
        residual=0
        if self.emergency_evacuation_cmd == True:
            return residual

        for i in range(self.bufNum):
            if self.enableBuffer[i] == 'yes' and self.adapter.carriers[i]['status']!='None' and self.bufs_status[i]['type']!='CoverTray':
                local_tr_cmd=self.bufs_status[i].get('local_tr_cmd_mem', {})
                check=local_tr_cmd.get('dest', '') == '' or local_tr_cmd.get('dest', '') == '*' or local_tr_cmd.get('dest', '')[:-5] == self.id or local_tr_cmd.get('host_tr_cmd', {}).get('preTransfer')
                # if not self.bufs_status[i].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'): #chocp add for preDispatch and preTansfer
                if not check: #chocp add for preDispatch and preTansfer
                    residual+=1
                elif global_variables.RackNaming == 25:
                    if self.adapter.battery['percentage'] < self.ChargeBelowPower:
                        self.bufs_status[i]['local_tr_cmd_mem']['host_tr_cmd']['preTransfer']=False
                        residual+=1
                    elif time.time()-self.bufs_status[i].get('local_tr_cmd_mem', {}).get("start_time",0) >= self.bufs_status[i]['local_tr_cmd_mem']['host_tr_cmd']['Residence_Time']:#Yuri
                        self.bufs_status[i]['local_tr_cmd_mem']['host_tr_cmd']['preTransfer']=False
                        residual+=1

        #print('residual', residual)
        return residual

    '''def buf_available(self):
        avaliable=0

        for idx in range(self.bufNum):
            #if self.adapter.carriers[idx]['status'] == 'None':
            if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None': #chocp 2022/1/6
                avaliable+=1

        print('avaliable', avaliable)
        return avaliable'''
    
    def buf_available(self): #for BufContrain fix
        avaliable=0
        array=[]

        for idx in range(self.bufNum):
            #if self.adapter.carriers[idx]['status'] == 'None':
            if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None': #chocp 2022/1/6
                avaliable+=1
                array.append(self.vehicle_bufID[idx])

        # print('avaliable', avaliable)
        # print(array)

        return avaliable, array
    
    def buf_available2(self): #peter 240704,fix for same eq bug
        avaliable=0
        append_cmd_loc=[]
        array=[]
        for action in self.actions:
            if action.get("loc"):
                append_cmd_loc.append(action['loc'])
        for idx in range(self.bufNum):
            if self.enableBuffer[idx] == 'yes': #chocp 2022/1/6
                avaliable+=1
                if self.adapter.carriers[idx]['status'] == 'None'\
                      and self.vehicle_bufID[idx] not in append_cmd_loc:
                    array.append(self.vehicle_bufID[idx])
        # if global_variables.RackNaming == 36 and self.id in ["AMR01","AMR03"]:
        #     array=sorted(array, key=lambda x: global_variables.K11_armsort.index(x))
        avaliable-=len(self.tr_cmds)
        if avaliable<0:avaliable=0
        print('avaliable', avaliable)
        print(array)
        return avaliable, array    
    
    def find_buf_idx(self, target):
        return self.vehicle_bufID.index(target)
    
    def re_assign_carrierID(self, buf_id, wrong_id_allow=False):
        carrierID=''
        try:
            idx=self.vehicle_bufID.index(buf_id)
            if self.bufs_status[idx]['stockID'] not in ['None', 'ReadFail', 'Unknown'] or wrong_id_allow: # Mike 2022/09/21 
                carrierID=self.bufs_status[idx]['stockID']
        except:
            pass
        return carrierID


    def query_empty_buf_id(self): #need enchance, not by sequence
        res=False
        bufID=''

        for idx in range(self.bufNum):
            self.next_buf_idx=(self.next_buf_idx+1)%self.bufNum
            if self.enableBuffer[self.next_buf_idx] == 'yes': #chocp add 2022/1/5
                print('query_empty_buf_id', self.next_buf_idx, self.enableBuffer[self.next_buf_idx])
                if self.adapter.carriers[self.next_buf_idx]['status'] == 'None': #only support 4 buffer
                    bufID=self.vehicle_bufID[self.next_buf_idx]
                    res=True
                    break

        return res, bufID

    def find_buf_idx_by_carrierID(self, carrierID): #8.27.14-1
        bufID=''
        for i in range(self.bufNum):
            if self.bufs_status[i]['stockID'] not in ['None', 'ReadFail', 'Unknown'] and self.bufs_status[i]['stockID'] == carrierID:
                bufID=self.vehicle_bufID[i]
                break
        return bufID
    
    def eRackPortStatusEmpty(self, source): #E001P01 #for load
        res=False
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
                
        res, rack_id, port_no=tools.rackport_format_parse(source)
        if res:
            #h_eRack=self.h_eRackMgr.eRacks[rack_id]
            h_eRack=self.h_eRackMgr.eRacks.get(rack_id) #chocp 2022/5/24, avoid no Rack
            
            res=h_eRack and \
                h_eRack.erack_status == 'UP' and \
                h_eRack.carriers[port_no-1]['status'] == 'up' and \
                h_eRack.carriers[port_no-1]['carrierID'] == ''

            if res: #chocp 2022/5/24 fix
                pass_booked_check=False
                if h_eRack.lots[port_no-1]['booked']:
                    if h_eRack.lots[port_no-1]['booked_for'] == self.id:
                        pass_booked_check=True
                else:
                    pass_booked_check=True

                print('eRackPortStatusEmpty', source, res, h_eRack.lots[port_no-1]['booked_for'], self.id, pass_booked_check)
                res=res and pass_booked_check               
        else:
            raise alarms.SelectRackWarning(self.id, uuid, source, handler=self.secsgem_e82_h)

        return res


    def eRackPortStatusUnloadCheck(self, source, carrierID): #for unload
        res=False
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        uuid=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd['carrierID']

        res, rack_id, port_no=tools.rackport_format_parse(source)
        if res:
            #h_eRack=self.h_eRackMgr.eRacks[rack_id]
            h_eRack=self.h_eRackMgr.eRacks.get(rack_id) #chocp 2022/5/24, avoid no Rack

            res=h_eRack and \
                h_eRack.erack_status == 'UP' and \
                h_eRack.carriers[port_no-1]['status'] == 'up' and \
                h_eRack.carriers[port_no-1]['carrierID']
            
            if res and carrierID and global_variables.TSCSettings.get('Safety', {}).get('ErackStatusCheck') == 'yes': #chocp 2022/11/2
                res=h_eRack.carriers[port_no-1].get('checked', True) and (h_eRack.carriers[port_no-1]['carrierID'] == carrierID)
                if not res:
                    raise alarms.RackAcquireCheckCarrierIDWarning(self.id, uuid, source, carrierID, handler=self.secsgem_e82_h) #8.28.7

            print('eRackPortStatusUnloadCheck', source, carrierID, res)

        else:

            raise alarms.SelectRackWarning(self.id, uuid, source, handler=self.secsgem_e82_h)

        return res


    def get_dist_empty_rack_port(self, port):
        dist=1000000 

        h_eRack=port.get('h', 0)
        rack_id=port.get('rack_id', '')
        slot_no=port.get('slot_no', 0)

        if h_eRack and rack_id and slot_no:
            res, port_id=tools.print_rackport_format(rack_id, int(slot_no), h_eRack.rows, h_eRack.columns)
            if res: #port_id valid
                try: #chocp 2022/5/4
                    dist=global_variables.dist[self.adapter.last_point][tools.find_point(port_id)]
                except:
                    pass

        return dist

    def do_fault_recovery(self, force=False):
        #print('do_fault_recovery...')
        target=''
        carrierID=''
        loc=''
        command_id='' #peter

        for idx in range(self.bufNum):
            local_tr_cmd=self.bufs_status[idx].get('local_tr_cmd_mem', {})
            print(idx, 'local_tr_cmd_mem', local_tr_cmd.get('uuid'))

            if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] not in ['None', 'Unknown'] and self.bufs_status[idx]['type']!='CoverTray':
                # if force or not self.bufs_status[idx].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'):
                check=local_tr_cmd.get('dest', '') == '' or local_tr_cmd.get('dest', '') == '*' or local_tr_cmd.get('dest', '')[:-5] == self.id or local_tr_cmd.get('host_tr_cmd', {}).get('preTransfer')
                if force or not check: # !!!
                    carrierID=self.adapter.carriers[idx]['status']
                    loc=self.vehicle_bufID[idx]
                    break

        # if force_recovery:
        #     for i in range(self.bufNum):
        #         if self.enableBuffer[i] == 'yes' and self.adapter.carriers[i]['status']!='None' and self.bufs_status[i]['do_auto_recovery'] == False:
        #             carrierID=self.adapter.carriers[i]['status']
        #             loc=self.vehicle_bufID[i]
        #             break
        # else:
        #     if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status']!='None':
        #         carrierID=self.adapter.carriers[idx]['status']
        #         loc=self.vehicle_bufID[idx]


        if loc:
            self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'do_fault_recovery for:', loc))

            uuid=100*time.time()
            uuid%=1000000000000
            if global_variables.RackNaming!=36:
                command_id='R%.12d'%uuid
            CommandInfo={'CommandID':command_id, 'Priority':0, 'Replace':0}

            local_tr_cmd=self.bufs_status[idx].get('local_tr_cmd_mem', {})
            carrier_transfer_info=local_tr_cmd.get('TransferInfo', {}) #chocp fix 2022/2/24
            carrierType=self.bufs_status[idx].get('type', '')
            carrierFrom=carrier_transfer_info.get('SourcePort', '')
            carrierTo=carrier_transfer_info.get('DestPort', '')
            tmp_sourceType=carrier_transfer_info.get('sourceType', '')

            if global_variables.RackNaming not in [18,36]:
                if local_tr_cmd.get('source_type') == 'workstation':
                    dest_erack=self.unload_fault_erack
                else:
                    dest_erack=self.load_fault_erack
                self.adapter.logger.debug("fault_station:{},{}".format(dest_erack,type(dest_erack)))
            else:#peter 240807
                if global_variables.RackNaming == 18:
                    fault_station=str(self.unload_fault_erack).split("|")
                if global_variables.RackNaming == 36:
                    if global_variables.k11_ng_fault_port[self.id]!='':
                        fault_station=(global_variables.k11_ng_fault_port[self.id]).split("|")
                    else:
                        fault_station=str(self.unload_fault_erack).split("|")
                fault_station_cost={}
                for fault_station_index in fault_station:
                    self.adapter.logger.debug("fault_station_index:{}".format(fault_station_index))

                    to_point=tools.find_point(fault_station_index)
                            #Sean 23/03/16
                    cost=tools.calculate_distance(self.adapter.last_point, to_point)
                    fault_station_cost[fault_station_index]=cost
                                
                self.adapter.logger.debug("fault_station_cost:{} for {}".format(fault_station_cost, self.id))                
                dest_erack=min(fault_station_cost, key=fault_station_cost.get)
                self.adapter.logger.debug("dest_erack:{}".format(dest_erack))
                # if local_tr_cmd.get('source_type') == 'workstation':
                #     dest_erack=self.unload_fault_erack
                # else:
                #     dest_erack=self.load_fault_erack

            if global_variables.TSCSettings.get('Recovery', {}).get('ResidualReturnTo') == 'DefaultErack':
                for target in [carrierFrom, carrierTo]: #need check if target have a area
                    res, rack_id, port_no=tools.rackport_format_parse(target)
                    if res:
                        if global_variables.RackNaming == 9:
                            h_eRack=Erack.h.eRacks.get(rack_id)
                            dest_erack=h_eRack.carriers[port_no-1]['area_id']
                        else:
                            dest_erack=rack_id
                            break

            res=False
            if global_variables.TSCSettings.get('Recovery', {}).get('FaultyErackCarrierTypeCheck') == 'yes': #chi 2022/08/30 check faulterack carrier type
                '''for i in dest_erack.split('|'):
                    try:
                        h_eRack=Erack.h.eRacks.get(i)
                        if h_eRack and carrierType in h_eRack.validSlotType:
                            res, target=tools.new_auto_assign_dest_port(h_eRack.device_id, carrierType)
                    except:
                        pass'''
                res, target=tools.new_auto_assign_dest_port(dest_erack, carrierType)
            #for GPM/LG  select neaby port to return #chocp 2022/4/29
            else:
                if Erack.h.port_areas.get(dest_erack): #for select nearby
                    nearby_sector_ports=sorted(Erack.h.port_areas.get(dest_erack), key=self.get_dist_empty_rack_port, reverse=False)
                    for port in nearby_sector_ports:
                        h_eRack=port.get('h', 0)
                        rack_id=port.get('rack_id', '')
                        slot_no=port.get('slot_no', 0)

                        if h_eRack and rack_id and slot_no: #chocp fix 2021/12/7
                            carrier=h_eRack.carriers[slot_no-1] #need add last idx, to avoid collision
                            lot=h_eRack.lots[slot_no-1]

                            if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                                res, target=tools.print_rackport_format(rack_id, slot_no, h_eRack.rows, h_eRack.columns)
                                if res and h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                                    target=target+'I'
                                break
                else:
                    res, target=tools.new_auto_assign_dest_port(dest_erack, '')
                    if target in EqMgr.getInstance().workstations and global_variables.RackNaming != 36:#peter 241105
                        print('Faulty dest cannot be a workstation!')
                        res=False

            if res:
                #TransferInfo={'CarrierID':carrierID, 'SourcePort':'', 'DestPort':target} #bug:2021/7/20
                # self.bufs_status[idx]['do_auto_recovery']=False
                TransferInfo={'CarrierID':carrierID, 'SourcePort':'%s%s'%(self.id, loc), 'DestPort':target, 'CarrierType': carrierType}

                host_tr_cmd={
                    'primary':1,
                    'uuid':CommandInfo['CommandID'],
                    'carrierID':carrierID,
                    'source':TransferInfo["SourcePort"],
                    'dest':TransferInfo["DestPort"],
                    'zoneID':'other', #9/14
                    'priority':100,
                    'replace':0,
                    'CommandInfo':CommandInfo,
                    'TransferCompleteInfo':[],
                    'OriginalTransferCompleteInfo':[],
                    'TransferInfoList':[TransferInfo],
                    'OriginalTransferInfoList':[TransferInfo],
                    'link':None,
                    'sourceType':tmp_sourceType
                }
                
                local_tr_cmd={
                    'uuid':host_tr_cmd['uuid'],
                    'carrierID':carrierID,
                    'carrierLoc':host_tr_cmd['source'],
                    'source':host_tr_cmd['source'],
                    'dest':host_tr_cmd['dest'],
                    'priority':host_tr_cmd['priority'],
                    'first':True, #chocp 2022/5/11
                    'last':True,
                    'TransferInfo':TransferInfo,
                    'OriginalTransferInfo':TransferInfo,
                    'host_tr_cmd':host_tr_cmd
                }
                local_tr_cmd['type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

                if hasattr(self.secsgem_e82_h, 'add_transfer_cmd'):
                    self.secsgem_e82_h.add_transfer_cmd(CommandInfo['CommandID'], {'CommandInfo': CommandInfo, 'TransferInfo': [TransferInfo]}) # Mike: 2021/09/22

                self.add_executing_transfer_queue(local_tr_cmd) #chocp add 2022/5/11

                action={
                    'type':'DEPOSIT',
                    'target':target,
                    'carrierID':carrierID,
                    'loc':loc,
                    'order':0,
                    'local_tr_cmd':local_tr_cmd
                    } #chocp 2022/4/14 remove uuid
                self.actions.append(action)
                self.action_in_run=self.actions[0]

                self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
                self.bufs_status[idx]['local_tr_cmd_mem']=local_tr_cmd

                stk_collection=[] # Mike: 2024/03/08
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and h_workstation.workstation_type in ['StockIn', 'StockIn&StockOut', 'LifterPort']:
                    stk_collection.append(action['local_tr_cmd']['host_tr_cmd']['uuid'])
                if global_variables.RackNaming == 27 and stk_collection:
                    E82.report_event(self.secsgem_e82_h,
                                    E82.LoadBackOrder, {
                                    'CommandIDList':stk_collection })

                #add book
                tools.book_slot(target, self.id)
                self.adapter.logger.debug("in do_fault_recovery call execute_action")

                self.execute_action() #fix 8/20'''

            else:
                raise alarms.FaultRackFullWarning(self.id, command_id, dest_erack, handler=self.secsgem_e82_h)

        return

    def return_standby_cmd(self, wait_vehicle='', tmpPark=False, from_unassigned=True, situation='Normal'): # Mike: 2021/11/12 #Sean: 23/3/16

        uuid=100*time.time()
        uuid%=1000000000000
        command_id='G%.12d'%uuid
        CommandInfo={'CommandID':command_id, 'Priority':100}
        route_cost=-1
        force_cost=-1
        force_path=[]
        route_station=''
        block_nodes=[] # Mike: 2021/04/06
        block_group_list=[] # Sean: 23/3/16

        for car in global_variables.global_vehicles_location_index:
            if car != self.id or wait_vehicle: # Sean #23/11/23 park when standby not selecting current point #8.28.3-2
                block_nodes.append(global_variables.global_vehicles_location_index[car]) # Sean #23/3/16
            
            if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                block_group_list += group_list
                #for group in group_list:
                    #block_nodes += global_variables.global_group_to_node.get(group, [])

        plan_route_group=[]
        if wait_vehicle: # Mike: 2021/11/12
            for route in global_variables.global_plan_route[wait_vehicle]:
                for group in PoseTable.mapping[route]['group'].split("|"):
                    plan_route_group.append(group)
                
            final_point = global_variables.global_plan_route[wait_vehicle][-1]
            final_point_pose = tools.get_pose(final_point)
            Route_Lock_Point = final_point_pose.get('RobotRouteLock','')
            if Route_Lock_Point:
                Route_Lock_Point = Route_Lock_Point.split(',')
                for point in Route_Lock_Point:
                    if point not in PoseTable.mapping:
                        continue
                    park_point_pose = tools.get_pose(point)
                    park_point_group = park_point_pose.get('group', '')
                    plan_route_group.extend(park_point_group.split("|"))
        
        #optional_standby_station=[]
        sorted_station=[] #Sean 23/3/13
        tmpPark_station=[]
        vehicle_in_station=[] #Sean 2023/11/15
        use_station=self.evacuate_station if situation == 'Evacuation' else self.standby_station
        for station in use_station:
            if global_variables.RackNaming == 18:#kelvin 20230716
                #self.adapter.logger.debug("global_variables.cs_find_by:{}".format(global_variables.cs_find_by))
                #self.adapter.logger.info("station:{}".format(station))
                if station in list(global_variables.cs_find_by.keys()):
                    self.adapter.logger.debug("station:{} charge order by:{}".format(station,global_variables.cs_find_by[station]))
                    if global_variables.cs_find_by[station] == "":
                        to_point=tools.find_point(station)
                        #Sean 23/03/16
                        cost=tools.calculate_distance(self.adapter.last_point, to_point) 
                        sorted_station.append( {'station' : station, 'point' : to_point, 'cost' : cost} )
                else:
                    to_point=tools.find_point(station)
                    #Sean 23/03/16
                    cost=tools.calculate_distance(self.adapter.last_point, to_point) 
                    sorted_station.append( {'station' : station, 'point' : to_point, 'cost' : cost} )
                        
                    
            else:
                to_point=tools.find_point(station)
                #Sean 23/03/16
                cost=tools.calculate_distance(self.adapter.last_point, to_point) 
                if PoseTable.mapping[to_point]['park']:
                    tmpPark_station.append( {'station' : station, 'point' : to_point, 'cost' : cost} )
                else:
                    sorted_station.append( {'station' : station, 'point' : to_point, 'cost' : cost} )

        if tmpPark: #8.25.14-1
            for i in tmpPark_station:
                sorted_station.append(i)
        sorted_key=lambda Dict : Dict['cost'] if (Dict['cost'] >= 0) else float('inf') #Sean 23/3/29
        sorted_station.sort(key=sorted_key)  #sorted by cost ascendantly

        self.adapter.logger.debug("sorted_station:{}".format(sorted_station))
        print('\nsorted route {}'.format([[station['station'], station['cost']] for station in sorted_station]))
        print(wait_vehicle, global_variables.global_plan_route)

        for count in range(0, 20):
            if count >= len(sorted_station):
                break
            station=sorted_station[count] #Sean 23/03/16 10 low cost stations
            self.adapter.logger.info("return_standby_cmd: try route to {} cost: {}".format(station['station'], station['cost']))
            #if wait_vehicle: # Mike: 2021/11/12 #Sean 2023/11/15
            cont=False
            for group in PoseTable.mapping[station['point']]['group'].split("|"):
                if group in plan_route_group or station['point'] in block_nodes:
                    self.adapter.logger.info("return_standby_cmd: route {} is currently occupied".format(station['station']))
                    cont=True
                    break
                if group in block_group_list:
                    cont=True
                    self.adapter.logger.info("return_standby_cmd: route {} has other vehicles standby (need to wait)".format(station['station']))
            if cont:
                vehicle_in_station.append(station) #Sean 2023/11/15
                continue

            #optional_standby_station.append(station)
            #cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+block_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo)
            if station['cost'] < 0 or station['cost'] == float('inf'): #fix from <=0 to <0 for temp
                self.adapter.logger.info("return_standby_cmd: can't not route to {}, cost {}".format(station['station'], station['cost']))
            else:
                force_cost, force_path=Route.h.get_a_route(self.adapter.last_point, station['point'], block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                if force_cost >= 0:
                    self.adapter.logger.info("return_standby_cmd: route {} GO".format(station['station']))
                    route_cost=station['cost']
                    route_station=station['station']
                    vehicle_in_station=[]
                    break
                else:
                    self.adapter.logger.info("return_standby_cmd: try route {} fail".format(station['station']))
                    if cost == -2:
                        self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, station['point']), global_variables.global_disable_nodes, global_variables.global_disable_edges))
                    continue

        if vehicle_in_station: #Sean 2023/11/15
            for i in range(vehicle_in_station):
                if vehicle_in_station[i]['cost'] < 0:
                   continue 
                route_station=vehicle_in_station[i]['station']
                self.adapter.logger.info("return_standby_cmd: no other route, go to {}".format(route_station))
                break
        
        # if wait_vehicle and not route_station and optional_standby_station:
        #     for station in optional_standby_station:
        #         #cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo)
        #         if cost < 0: #fix from <=0 to <0 for temp
        #             self.adapter.logger.info("return_standby_cmd*: can't not route to {}, cost {}".format(station, cost))
        #         else:
        #             self.adapter.logger.info("return_standby_cmd*: route to {} cost: {}".format(station, cost))
        #             if cost < route_cost or route_cost < 0:
        #                 route_cost=cost
        #                 route_station=station

        if not route_station and not self.findstandbystation:
            self.findstandbystation=True
            alarms.BaseTryStandbyFailWarning(self.id, command_id, self.adapter.last_point, 'None')
        elif route_station:
            self.findstandbystation=False
            self.adapter.logger.info('return_standby_cmd to: {}'.format(route_station))
            TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': route_station}

            host_tr_cmd={
                'primary':1,
                'uuid':command_id,
                'carrierID':TransferInfo['CarrierID'],
                'source':TransferInfo["SourcePort"],
                'dest':TransferInfo["DestPort"],
                'zoneID':'other', #9/14
                'priority':99,
                'replace':0,
                'CommandInfo':CommandInfo,
                'TransferCompleteInfo':[],
                'OriginalTransferCompleteInfo':[],
                'TransferInfoList':[TransferInfo],
                'OriginalTransferInfoList':[TransferInfo],
                'link':None,
                'sourceType':'Normal', #8.21-7
            }

            local_tr_cmd={
                'uuid':host_tr_cmd['uuid'],
                'carrierID':host_tr_cmd['carrierID'],
                'carrierLoc':host_tr_cmd['source'],
                'source':host_tr_cmd['source'],
                'dest':host_tr_cmd['dest'],
                'priority':host_tr_cmd['priority'],
                'last':True,
                'TransferInfo':TransferInfo,
                'OriginalTransferInfo':TransferInfo,
                'host_tr_cmd':host_tr_cmd
            }

            local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
            local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

            if global_variables.RackNaming == 36:
                self.adapter.logger.debug("route_station:{}".format(route_station))


            self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target':route_station, 'local_tr_cmd':local_tr_cmd} #chocp 2022/4/14 remove uuid

            self.CommandIDList.append(command_id) #new standby cmd
            if from_unassigned:
                #self.CommandIDList=[CommandID]
                E82.report_event(self.secsgem_e82_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                            'BatteryValue':self.adapter.battery['percentage']})

                output('VehicleAssigned',{
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'VehicleID':self.id,
                    'VehicleState':self.AgvState,
                    'Message':self.message,
                    'ForceCharge':self.force_charge, #???
                    'CommandIDList':self.CommandIDList}, True)

                self.execute_action(True, force_cost, force_path) #fix 8/20
            else:
                self.execute_action(False, force_cost, force_path) #fix 8/20
            self.findstandbystation=False

    def reroute(self):
        print('reroute_cmd')
        if len(self.adapter.planner.occupied_route)>0:

            if self.adapter.last_point and self.adapter.last_point == self.adapter.planner.occupied_route[0]:
                block_edges=(self.adapter.planner.occupied_route[0], self.adapter.planner.occupied_route[1])
            else:
                block_edges=(self.adapter.last_point, self.adapter.planner.occupied_route[0])
            if block_edges not in self.alarm_edge:
                self.alarm_edge.append(block_edges)

            local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
            uuid=local_tr_cmd.get('uuid', '')

            target=self.action_in_run.get('target', '')
            to_point=tools.find_point(target)

            block_nodes=[] # Mike: 2021/12/07
            for car in global_variables.global_vehicles_location_index: # Mike: 2021/04/06
                if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                    group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                    for group in group_list:
                        block_nodes += global_variables.global_group_to_node.get(group, [])
            if self.adapter.last_alarm_point and self.adapter.last_alarm_point not in self.alarm_node:
                self.alarm_node.append(self.adapter.last_alarm_point)
            for node in self.alarm_node:
                for group in PoseTable.mapping[node]['group'].split("|"):
                    block_nodes += global_variables.global_group_to_node.get(group, [])


            # Mike: 2022/02/08
            cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+block_nodes, block_edges=global_variables.global_disable_edges+self.alarm_edge, algo=global_variables.RouteAlgo,score_func=global_variables.score_func)
            self.adapter.logger.info('{} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block_group:', cost, path, self.alarm_node, to_point, self.alarm_edge))
            if cost == -2:
                self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, to_point), global_variables.global_disable_nodes+block_nodes, global_variables.global_disable_edges+self.alarm_edge))

            if cost < 0:
                cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+self.alarm_node, block_edges=global_variables.global_disable_edges+self.alarm_edge, algo=global_variables.RouteAlgo,score_func=global_variables.score_func)
                self.adapter.logger.info('{} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block_node:', cost, path, self.alarm_node, to_point, self.alarm_edge))
                if cost == -2:
                    self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, to_point), global_variables.global_disable_nodes+self.alarm_node, global_variables.global_disable_edges+self.alarm_edge))

            if cost < 0:
                cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges+self.alarm_edge, algo=global_variables.RouteAlgo,score_func=global_variables.score_func)
                self.adapter.logger.info('{} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block_edge:', cost, path, self.alarm_node, to_point, self.alarm_edge))
                if cost == -2:
                    self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, to_point), global_variables.global_disable_nodes, global_variables.global_disable_edges+self.alarm_edge))

            if cost < 0:
                alarms.BaseRouteWarning(self.id, uuid, self.adapter.last_alarm_point, to_point, handler=self.secsgem_e82_h)
            else:
                if not self.adapter.vehicle_stop():
                    # warning
                    return
                self.adapter.move_control(path, False, True)


    def find_charge_station(self): #Sean 23/3/29
        #nearby_abcs=''
        nearby_cs=''
        #abcs_route_cost=-1
        cs_route_cost=-1
        block_nodes=[] # Mike: 2021/04/06
        block_group_list=[] # Sean: 23/3/29
        for car in global_variables.global_vehicles_location_index:
            block_nodes.append(global_variables.global_vehicles_location_index[car]) # Sean #23/3/16
            if car != self.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                block_group_list += group_list
                #for group in group_list:
                    #block_nodes += global_variables.global_group_to_node.get(group, [])
        #Sean 23/3/29
        for occupied in global_variables.global_occupied_station:
            if global_variables.global_occupied_station[occupied] not in ['' ,self.id]: #23/12/15
                block_group_list.append(occupied)
                
        sorted_station=[] 
        for station in self.charge_station:
            to_point=tools.find_point(station)
            #cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+block_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo)
            cost=tools.calculate_distance(self.adapter.last_point, to_point)
            
            isABCS=False
            if PoseTable.mapping[PortsTable.mapping[station][0]].get('type', 'chargestation') == 'autobatterychangestation':
                #isABCS=True #for test
                h_ABCS=Iot.h.devices.get(station, None)
                if h_ABCS:
                    isABCS=(getattr(h_ABCS, 'device_type') == 'ABCS' and getattr(h_ABCS, 'ABCS')["state"] == 'Standby')
                if not isABCS:
                    continue
            sorted_station.append( {'station' : station, 'point' : to_point, 'cost' : cost, 'ABCS' : isABCS} )

        if self.force_charge: #8.23F-2
            sort_key=lambda Dict : float('inf') \
                if (Dict['cost'] < 0) \
                else (Dict['cost'] \
                if not Dict['ABCS'] \
                else (Dict['cost']-10000000))
        else:
            sort_key=lambda Dict : float('inf') \
                if (Dict['cost'] < 0) \
                else (Dict['cost'] \
                if not Dict['ABCS'] \
                else (Dict['cost']+10000000))
        #put avalliable ABCS in front order (cost-10000000)
        #put stations cannot arrived(cost:-1) in last order(cost inf)
        if global_variables.RackNaming != 36:
            sorted_station.sort(key=sort_key) #sorted by cost and ABCS
        else:
            if self.id not in ["AMR01","AMR04"]:# need change tp config
                sorted_station.sort(key=sort_key) #sorted by cost and ABCS
                

        print('\nsorted route {}'.format([[station['station'], station['cost']] for station in sorted_station]))



        
        alerady_find_group_check=False
        for station in sorted_station:
            cont=False
            for group in PoseTable.mapping[station['point']]['group'].split("|"):
                if group in block_group_list:
                    cont=True
                    break
            if cont:
                continue
            if station['cost'] < 0 or station['cost'] == float('inf'): #fix from <=0 to <0 for temp
                self.adapter.logger.info("find_charge_station: can't not route to {}, cost {}".format(station['station'], station['cost']))
                # self.adapter.logger.info("exec_charge_cmd: can't not route to {}, cost {}".format(station, cost))
                pass
            else:
                self.adapter.logger.info("find_charge_station: select route to {}".format(station['station']))
                #nearby_cs=station['station']
                if global_variables.RackNaming == 18:
                    self.adapter.logger.info("global_variables.cs_find_by:{}".format(global_variables.cs_find_by))    
                    if station['station'] == "TBS01":
                        if global_variables.cs_find_by["TBS01"] == "":
                            # self.adapter.logger.info("TBS01_is_find:{}".format(global_variables.TBS01_is_find))
                            nearby_cs=station['station']
                            cs_route_cost=station['cost']
                            
                            global_variables.cs_find_by["TBS01"]=self.id
                            break
                        else:
                            # self.adapter.logger.info("TBS01_is_find:{}".format(global_variables.TBS01_is_find))
                            continue
                            
                    elif station['station'] == "TBS02":
                        if global_variables.cs_find_by["TBS02"] == "":
                            # self.adapter.logger.info("TBS02_is_find:{}".format(global_variables.TBS02_is_find))
                            nearby_cs=station['station']
                            cs_route_cost=station['cost']
                           
                            global_variables.cs_find_by["TBS02"]=self.id
                            break
                        else:
                            # self.adapter.logger.info("TBS02_is_find:{}".format(global_variables.TBS02_is_find))
                            continue
                    elif station['station'] == "TBS03":
                        if global_variables.cs_find_by["TBS03"] == "":
                            # self.adapter.logger.info("TBS03_is_find:{}".format(global_variables.TBS03_is_find))
                            nearby_cs=station['station']
                            cs_route_cost=station['cost']
                            
                            global_variables.cs_find_by["TBS03"]=self.id
                            break
                        else:
                            # self.adapter.logger.info("TBS03_is_find:{}".format(global_variables.TBS03_is_find))
                            continue
                    elif station['station'] == "TBS04":
                        if global_variables.cs_find_by["TBS04"] == "":
                            # self.adapter.logger.info("TBS04_is_find:{}".format(global_variables.TBS04_is_find))

                            nearby_cs=station['station']
                            cs_route_cost=station['cost']
                            global_variables.cs_find_by["TBS04"]=self.id
                            
                            break
                        else:
                            # self.adapter.logger.info("TBS04_is_find:{}".format(global_variables.TBS04_is_find))

                            continue

                    isABCS=station['ABCS']
                    break 
                else:
                    force_cost, force_path=Route.h.get_a_route(self.adapter.last_point, station['point'], block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                    if force_cost >= 0:
                        self.adapter.logger.info("find_charge_station:route to {} GO".format(station['station']))
                        nearby_cs=station['station']
                        cs_route_cost=station['cost']
                        isABCS=station['ABCS']
                        break
                    else:
                        self.adapter.logger.info("find_charge_station:route to {} fail".format(station['station']))
                        if force_cost == -2:
                            self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'route from {} to {} failed, block:'.format(self.adapter.last_point, station['point']), global_variables.global_disable_nodes, global_variables.global_disable_edges))
                        continue

   
        return (isABCS, nearby_cs)       
        # if not nearby_abcs and not nearby_cs:
        #     for station in self.charge_station:
        #         to_point=tools.find_point(station)
        #         cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo)
        #         if cost < 0: #fix from <=0 to <0 for temp
        #             # self.adapter.logger.info("exec_charge_cmd: can't not route to {}, cost {}".format(station, cost))
        #             pass
        #         else:
        #             # self.adapter.logger.info("exec_charge_cmd: route to {} cost: {}".format(station, cost))
        #             if PoseTable.mapping[PortsTable.mapping[station][0]].get('type', 'chargestation') == 'autobatterychangestation':
        #                 if cost < abcs_route_cost or abcs_route_cost < 0:
        #                     h_ABCS=Iot.h.devices.get(station, None)
        #                     if h_ABCS and getattr(h_ABCS, 'device_type') == 'ABCS' and getattr(h_ABCS, 'ABCS')["state"] == 'Standby':
        #                         abcs_route_cost=cost
        #                         nearby_abcs=station
        #             else:
        #                 #self.adapter.logger.info("exec_charge_cmd: route to {} cost: {}".format(station, cost))
        #                 if cost < cs_route_cost or cs_route_cost < 0:
        #                     cs_route_cost=cost
        #                     nearby_cs=station


        #return (True, nearby_abcs) if nearby_abcs else (False, nearby_cs)

    def exec_charge_cmd(self, station, from_unassigned=True):
        print('exec_charge_cmd')
        self.ControlPhase='GoCharge' #chocp add 2021/11/22
        
        uuid=100*time.time()
        uuid%=1000000000000
        command_id='C%.12d'%uuid
        CommandInfo={'CommandID':command_id, 'Priority':99}
        TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': station}
        self.adapter.logger.info('exec_charge_cmd to: {}'.format(station))

        self.charge_cmd=False
        if not station:
            raise alarms.BaseTryChargeFailWarning(self.id, command_id, self.adapter.last_point, 'None', handler=self.secsgem_e82_h)
            
        if not self.adapter.charge_end(): #avoid move at breakon at C001
            raise alarms.DischargeCommandFailedWarning(self.id, command_id, self.at_station, handler=self.secsgem_e82_h) #chocp 2021/12/10

        host_tr_cmd={
            'primary':1,
            'uuid':CommandInfo['CommandID'],
            'carrierID':TransferInfo['CarrierID'],
            'source':TransferInfo["SourcePort"],
            'dest':TransferInfo["DestPort"],
            'zoneID':'other', #9/14
            'priority':100,
            'replace':0,
            'CommandInfo':CommandInfo,
            'TransferCompleteInfo':[],
            'OriginalTransferCompleteInfo':[],
            'TransferInfoList':[TransferInfo],
            'OriginalTransferInfoList':[TransferInfo],
            'link':None,
            'sourceType':'Normal', #8.21-7
        }

        local_tr_cmd={
            'uuid':host_tr_cmd['uuid'],
            'carrierID':host_tr_cmd['carrierID'],
            'carrierLoc':host_tr_cmd['source'],
            'source':host_tr_cmd['source'],
            'dest':host_tr_cmd['dest'],
            'priority':host_tr_cmd['priority'],
            'last':True,
            'TransferInfo':TransferInfo,
            'OriginalTransferInfo':TransferInfo,
            'host_tr_cmd':host_tr_cmd
            }
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
        if global_variables.RackNaming != 36:
            self.actions.append({'type':'CHARGE', 'carrierID':'', 'loc':'', 'order':0, 'target': station, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid
        else:
            if "VCS" not in station:
                self.adapter.logger.info("why station:{}".format(station))
                self.actions.append({'type':'CHARGE', 'carrierID':'', 'loc':'', 'order':0, 'target': station, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid
            else:
                self.force_charge=False
                self.go_to_vcs=True #vcs

        self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target': station, 'local_tr_cmd':local_tr_cmd}

        self.CommandIDList.append(command_id) #new_charge_cmd
        if from_unassigned:
            # self.CommandIDList=[command_id]

            E82.report_event(self.secsgem_e82_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                            'BatteryValue':self.adapter.battery['percentage']})

            output('VehicleAssigned',{
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'VehicleID':self.id,
                    'VehicleState':self.AgvState,
                    'Message':self.message,
                    'ForceCharge':self.force_charge, #???
                    'CommandIDList':self.CommandIDList}, True)

            self.execute_action(force_route=True) #fix 8/20
        else:
            self.execute_action(force_route=False) #fix 8/20

    def exec_exchange_cmd(self, station, from_unassigned=True):
        print('exec_exchange_cmd')
        self.ControlPhase='GoExchange' #chocp add 2021/11/22
        
        uuid=100*time.time()
        uuid%=1000000000000
        command_id='C%.12d'%uuid
        CommandInfo={'CommandID':command_id, 'Priority':99}
        TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': station}

        self.charge_cmd=False
        if not station:
            raise alarms.BaseTryChargeFailWarning(self.id, command_id, self.adapter.last_point, 'None', handler=self.secsgem_e82_h)

        host_tr_cmd={
            'primary':1,
            'uuid':CommandInfo['CommandID'],
            'carrierID':TransferInfo['CarrierID'],
            'source':TransferInfo["SourcePort"],
            'dest':TransferInfo["DestPort"],
            'zoneID':'other', #9/14
            'priority':100,
            'replace':0,
            'CommandInfo':CommandInfo,
            'TransferCompleteInfo':[],
            'OriginalTransferCompleteInfo':[],
            'TransferInfoList':[TransferInfo],
            'OriginalTransferInfoList':[TransferInfo],
            'link':None,
            'sourceType':'Normal', #8.21-7
        }

        local_tr_cmd={
            'uuid':host_tr_cmd['uuid'],
            'carrierID':host_tr_cmd['carrierID'],
            'carrierLoc':host_tr_cmd['source'],
            'source':host_tr_cmd['source'],
            'dest':host_tr_cmd['dest'],
            'priority':host_tr_cmd['priority'],
            'last':True,
            'TransferInfo':TransferInfo,
            'OriginalTransferInfo':TransferInfo,
            'host_tr_cmd':host_tr_cmd
            }

        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

        self.actions.append({'type':'EXCHANGE', 'carrierID':'', 'loc':'', 'order':0, 'target':station, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid
        self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target':station, 'local_tr_cmd':local_tr_cmd}

        self.CommandIDList.append(command_id) #new exchange cmd
        if from_unassigned:
            #self.CommandIDList=[CommandID]

            E82.report_event(self.secsgem_e82_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                            'BatteryValue':self.adapter.battery['percentage']})

            output('VehicleAssigned',{
                    'Battery':self.adapter.battery['percentage'],
                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                    'Connected':self.adapter.online['connected'],
                    'Health':self.adapter.battery['SOH'],
                    'MoveStatus':self.adapter.move['status'],
                    'RobotStatus':self.adapter.robot['status'],
                    'RobotAtHome':self.adapter.robot['at_home'],
                    'VehicleID':self.id,
                    'VehicleState':self.AgvState,
                    'Message':self.message,
                    'ForceCharge':self.force_charge, #???
                    'CommandIDList':self.CommandIDList}, True)

            self.execute_action(force_route=True) #fix 8/20
        else:
            self.execute_action(force_route=False) #fix 8/20

    def trbackreq_cmd(self):
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {}) #chocp 2022/4/14
        uuid=local_tr_cmd.get('uuid', '')

        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
        carrierID=local_tr_cmd['carrierID'] #chocp 2022/4/14
        self.tr_back_timeout=True

        if self.tr_assert:
            if self.tr_assert['Result'] == 'OK' and\
            (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'Back') and\
            (self.tr_assert['TransferPort'] == target or self.tr_assert['SendBy'] == 'by web'): #chocp add 2021/12/21
                self.adapter.robot_check_control(True)
                self.tr_back_req=True
                            
            #else: #NG or FAIL or PENDING
            elif self.tr_assert['Result'] == 'NG' and (self.tr_assert['TransferPort'] == target): #for spil, no waiting
                self.adapter.robot_check_control(False)
                raise alarms.EqBackCheckFailWarning(self.id, uuid, target) #chocp fix 2022/4/14     

        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
        if not pending_timeout:
            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrBackReqTimeout', 0)

        if self.TrBackReqTime and (time.time()-self.TrBackReqTime > pending_timeout):
            raise alarms.EqCheckTimeoutWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

        elif self.ValidInputLastReqTime and (time.time()-self.ValidInputLastReqTime > 10):
            E82.report_event(self.secsgem_e82_h,
                            E82.TrBackReq, {
                            'VehicleID':self.id,
                            'TransferPort':target, # zhangpeng 2025-04-17 fix the error of TrBackReq using "at_station" as the TransferPort
                            'CarrierID':carrierID})

            output('TrBackReq',{
                    'VehicleID':self.id,
                    'VehicleState':self.AgvState,
                    'Station':self.at_station,
                    'TransferPort':target,
                    'CarrierID':carrierID})

            self.ValidInputLastReqTime=time.time()

    #def set_exception_deque(self, alarm):
    #    self.exception_deque=alarm

    def append_transfer(self, host_tr_cmd, bufID, byTheWay=True,fromvehicle=False,swp=0): #8.21H-4
        
        if swp:# Yuri 2024/10/11
            local_tr_cmd=host_tr_cmd
        else:
            local_tr_cmd={
                        'uuid':host_tr_cmd['uuid'],
                        'carrierID':host_tr_cmd['carrierID'],
                        'carrierLoc':host_tr_cmd['source'],
                        'source':host_tr_cmd['source'],
                        'dest':host_tr_cmd['dest'],
                        'priority':host_tr_cmd['priority'],
                        'first':True,
                        'last':True,
                        'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                        'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                        'host_tr_cmd':host_tr_cmd
                    }
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

        self.add_executing_transfer_queue(local_tr_cmd)

        source_port=local_tr_cmd['source']
        dest_port=local_tr_cmd['dest']
        if 'BUF'  in source_port:
            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd['carrierID'])


        action1={
                'type':'ACQUIRE',
                'target':source_port,
                'point':tools.find_point(source_port) if 'BUF' not in source_port else '',
                'order':0,
                'loc':bufID,
                'local_tr_cmd':local_tr_cmd,
                'records':[local_tr_cmd]#peter 241106
                }

        action2={
                'type':'DEPOSIT',
                'target':dest_port,
                'point':tools.find_point(dest_port),
                'order':0,
                'loc':bufID,
                'local_tr_cmd':local_tr_cmd,
                'records':[local_tr_cmd]
                }
        
        action3={
                'type':'SHIFT',
                'target':source_port,
                'target2':dest_port,
                'point':tools.find_point(source_port), 
                'order':0,
                'loc':'',
                'local_tr_cmd':local_tr_cmd,
                'records':[local_tr_cmd]
                
            }

        if host_tr_cmd.get('shiftTransfer',False):
            self.actions.appendleft(action3)
        else:
            if local_tr_cmd['dest_type'] == 'workstation' and byTheWay and not fromvehicle:
                self.actions.appendleft(action2)
            elif fromvehicle:
                self.actions=collections.deque(list(self.actions)[:1] + [action2] + list(self.actions)[1:])
            else:
                self.actions.append(action2)
            if 'BUF' not in source_port:
                self.actions.appendleft(action1)

        tools.book_slot(local_tr_cmd['dest'], self.id, local_tr_cmd['source'])  #book for MR, may cause delay
        tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'], self.id)

    def append_transfer_BaguioWB(self, host_tr_cmd, bufID, byTheWay=True,fromvehicle=False,need_sort=False,swp=0):#Baguio WB append_transfer_BaguioWB
        if swp:# Yuri 2024/10/11
            local_tr_cmd=host_tr_cmd
        else:
            local_tr_cmd={
                        'uuid':host_tr_cmd['uuid'],
                        'carrierID':host_tr_cmd['carrierID'],
                        'carrierLoc':host_tr_cmd['source'],
                        'source':host_tr_cmd['source'],
                        'dest':host_tr_cmd['dest'],
                        'priority':host_tr_cmd['priority'],
                        'first':True,
                        'last':True,
                        'TransferInfo':host_tr_cmd['TransferInfoList'][0],
                        'OriginalTransferInfo':host_tr_cmd['OriginalTransferInfoList'][0],
                        'host_tr_cmd':host_tr_cmd
                    }
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
        
        self.add_executing_transfer_queue(local_tr_cmd)

        source_port=local_tr_cmd['source']
        dest_port=local_tr_cmd['dest']
        if host_tr_cmd.get('shiftTransfer'):
            point=tools.find_point(source_port) #chocp 2024/8/21 for shift
            

            action={
                'type':'SHIFT',
                'target':source_port,
                'target2':dest_port,
                'point':point, 
                'order':0,
                'loc':'',
                'local_tr_cmd':local_tr_cmd,
                
                }
            self.actions.appendleft(action)
        else:
            if 'BUF'  in source_port:
                bufID=self.find_buf_idx_by_carrierID(host_tr_cmd['carrierID'])

            if 'BUF' in dest_port or dest_port == '*':
                action1={
                        'type':'ACQUIRE',
                        'target':source_port,
                        'point':tools.find_point(source_port) if 'BUF' not in source_port else '',
                        'order':0,
                        'loc':bufID,
                        'local_tr_cmd':local_tr_cmd
                        }
                try:
                    point=tools.find_point(source_port) #DestPort MRXXXBUF00
                except:
                    point=self.adapter.last_point

                action2={
                    'type':'NULL',
                    'target':source_port,
                    'point':point,
                    'order':0, #order
                    'loc':'',
                    'local_tr_cmd':local_tr_cmd,
                    
                    }
                self.actions.appendleft(action2)
                self.actions.appendleft(action1)
            else:
                action1={
                        'type':'ACQUIRE',
                        'target':source_port,
                        'point':tools.find_point(source_port) if 'BUF' not in source_port else '',
                        'order':0,
                        'loc':bufID,
                        'local_tr_cmd':local_tr_cmd
                        }

                action2={
                        'type':'DEPOSIT',
                        'target':dest_port,
                        'point':tools.find_point(dest_port),
                        'order':0,
                        'loc':bufID,
                        'local_tr_cmd':local_tr_cmd
                        }
                h_workstation=EqMgr.getInstance().workstations.get(dest_port)

                
                


                if local_tr_cmd['dest_type'] == 'workstation' and byTheWay and not fromvehicle:
                    if h_workstation.workstation_type != "ErackPort":
                        self.actions.appendleft(action2)
                    else:
                        self.actions.append(action2)
                elif fromvehicle:
                    self.actions=collections.deque(list(self.actions)[:1] + [action2] + list(self.actions)[1:])
                else:
                    self.actions.append(action2)
                if 'BUF' not in source_port:
                    self.actions.appendleft(action1)


                if need_sort:
                    self.adapter.logger.debug("wwwwwwwwwwwww")
                    
                    tmp_back_to_erack_action=collections.defaultdict(lambda: collections.defaultdict(list))
                    tmp_naormal_action = collections.deque()
                    while self.actions:
                        action=self.actions.popleft()
                        pt=action.get("point")
                        action_type=action.get("type")
                        
                        if pt and "EWB" in pt and action_type and action_type=="DEPOSIT":
                            root = pt.rsplit("-", 1)[0]
                            
                            tmp_back_to_erack_action[root][pt].append(action)
                        else:
                            
                            tmp_naormal_action.append(action)
                    
                    self.actions = tmp_naormal_action
                    tmp_back_to_erack_action = {k: dict(v) for k, v in tmp_back_to_erack_action.items()}

                    if tmp_back_to_erack_action:
                        for root, subdict in tmp_back_to_erack_action.items():
                            print("Root key: {}".format(root))            
                            for point, action_list in subdict.items():
                                print("Point: {}".format(point))        
                            
                                for action in action_list:
                                    self.adapter.logger.debug("wwwwwwwwwwwww1")
                                    self.actions.append(action)
                                    print("target:{}".format(action.get("target")))
                            print()

                

                tools.book_slot(local_tr_cmd['dest'], self.id, local_tr_cmd['source'])  #book for MR, may cause delay
                tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'], self.id)



    def host_call_move_cmd(self): #8.27.13
        target=self.host_call_params.get('Destport', '')
        waittimeout=self.host_call_params.get('WaitTimeout', 0)
        self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'get_host_move_cmd',target, 'waiting:', waittimeout))
        uuid=100*time.time()
        uuid%=1000000000000
        CommandID='M%.12d'%uuid
        CommandInfo={'CommandID':CommandID, 'Priority':0, 'Replace':0}
        TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort':target , 'CarrierType': ''}

        new_host_tr_cmd={
            'primary':1,
            'received_time':time.time(),
            'uuid':CommandInfo['CommandID'],
            'carrierID':TransferInfo['CarrierID'],
            'source':TransferInfo['SourcePort'],
            'dest':TransferInfo['DestPort'],
            'zoneID':'other', #9/14
            'priority':0,
            'replace':0,
            'back': '',
            'CommandInfo':CommandInfo,
            'TransferCompleteInfo':[],
            'OriginalTransferCompleteInfo':[],
            'TransferInfoList':[TransferInfo],
            'OriginalTransferInfoList':[TransferInfo],
            'credit':1,
            'link':None,  #2022/12/09
            'sourceType':'Normal' #chocp 2022/12/23
                }
        
        local_tr_cmd={
            'uuid':CommandID,
            'carrierID':'',
            'carrierLoc':'',
            'source':'',
            'dest':target,
            'priority':0,
            'last':True,
            'TransferInfo':new_host_tr_cmd['TransferInfoList'][0],
            'OriginalTransferInfo':new_host_tr_cmd['TransferInfoList'][0],
            'host_tr_cmd':new_host_tr_cmd
        }


        self.actions.append({'type':'HostMove', 'carrierID':'', 'loc':'', 'order':0, 'target': target, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid
        self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target': target, 'local_tr_cmd':local_tr_cmd}

        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.host_call_cmd=False
        self.host_call_params={}
        if waittimeout:
            self.host_call_waiting_time=waittimeout
            self.host_call_target=target

    def append_transfer_report_assign(self): #peter 241211
        E82.report_event(self.secsgem_e82_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                            'BatteryValue':self.adapter.battery['percentage']})

        output('VehicleAssigned',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge, #???
                'CommandIDList':self.CommandIDList})

    def append_transfer_allowed_for_TI_Baguio(self, actions): #8.27.14-2 #need_a
        vehicle_wq=TransferWaitQueue.getInstance(self.id)
        
        is_back_to_erack_action=False
        # if self.last_action_is_for_workstation and self.appendTransferAllowed == 'yes': #append transfer 2023/3/23
        if self.appendTransferAllowed == 'yes' and self.appendTransferAlgo == 'appendTransfer':
        
            try_append_transfer=False
            back_erack_do_desposit=False
            action_is_ACQUIR_count=0
            first_target_is_eq=False
            first_target_eqID=""
            
            num, buf_list=self.buf_available2()
            self.adapter.logger.debug("in append_transfer_allowed_for_TI_Baguio buf_list:{}".format(buf_list))
            
            
            if actions[0].get('type') == 'DEPOSIT': #8.21K
                
                target=actions[0].get('target', '')#
                h_workstation=EqMgr.getInstance().workstations.get(target)#Use the first action target to determine if it belongs to the workstation.
                
                if h_workstation:
                    '''
                    in h_workstation 
                    '''
                    if h_workstation.workstation_type != "ErackPort":
                        target_is_eq=True 
                        first_target_eqID=h_workstation.equipmentID
                        try_append_transfer=True
                    else:
                        try_append_transfer=False
                else:
                    try_append_transfer=False                
                    
                target_point=tools.find_point(target) #8.21-5
                if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                    try_append_transfer=False
                    
                elif actions[0].get('type') == 'SHIFT': #8.21K
                    
                    target=actions[0].get('target', '')
                    h_workstation=EqMgr.getInstance().workstations.get(target)
                    
                    if h_workstation:
                        if h_workstation.workstation_type != "ErackPort":
                            target_is_eq=True
                            first_target_eqID=h_workstation.equipmentID
                            try_append_transfer=True
                        else:
                            try_append_transfer=False
                    else:
                        try_append_transfer=False
                        
                    target_point=tools.find_point(target) #8.21-5
                    if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                        try_append_transfer=False

                elif actions[0].get('type') == 'ACQUIRE': #8.21K
                    
                    target=actions[0].get('target', '')
                    h_workstation=EqMgr.getInstance().workstations.get(target) 
                    
                    if h_workstation:
                        if h_workstation.workstation_type != "ErackPort":
                            target_is_eq=True
                            first_target_eqID=h_workstation.equipmentID
                            try_append_transfer=True
                        else:
                            try_append_transfer=False
                    else:
                        try_append_transfer=False

                    target_point=tools.find_point(target) #8.21-5
                    if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                        try_append_transfer=False
                        
                        
            
            TransferAllowed=True
            if try_append_transfer and vehicle_wq:
                if tools.acquire_lock_with_timeout(vehicle_wq.wq_lock,3):
                    #vehicle_wq.wq_lock.acquire()
                    try:
                        major_candidates=[]
                        swap_commandID=[]
                        num, buf_list=self.buf_available()
                        if num and len(vehicle_wq.queue):
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if host_tr_cmd.get('link'):
                                    swap_commandID.append( host_tr_cmd.get('link').get('uuid'))
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if self.id  in host_tr_cmd.get('dest') or '*' in host_tr_cmd['dest']:
                                    continue
                                if host_tr_cmd.get('link'):
                                    source_port=host_tr_cmd['source']
                                    distance=tools.calculate_distance(self.adapter.last_point, source_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])
                                elif not host_tr_cmd.get('link') and host_tr_cmd.get('uuid') not in swap_commandID:
                                    dest_port=host_tr_cmd['dest']
                                    distance=tools.calculate_distance(self.adapter.last_point, dest_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])

                            temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])
                            if temp_major_candidates:
                                for host_tr_cmd in temp_major_candidates:
                                    if self.check_carrier_type == 'yes':
                                        if host_tr_cmd.get('HostSpecifyMR',''):
                                            continue
                                        vaildcarriertype={buf: self.carriertypedict[buf] for buf in buf_list}
                                        bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                        carriertype=host_tr_cmd[1]['TransferInfoList'][0].get('CarrierType', '')
                                        linkcarriertype=''
                                        bufID_carriertype=''
                                        bufID_linkcarriertype=''
                                        if host_tr_cmd[1].get('link'):
                                            linkcarriertype=host_tr_cmd[1].get('link')['TransferInfoList'][0].get('CarrierType', '')
                                        print(vaildcarriertype,bufID,carriertype,linkcarriertype)

                                        if (not bufID and not carriertype) or \
                                        (not bufID and all(carriertype not in v and 'All' not in v for v in vaildcarriertype.values())) or \
                                        (linkcarriertype and all(linkcarriertype not in v and 'All' not in v for v in vaildcarriertype.values())):
                                            continue

                                        for buf, v_carriertype_list in vaildcarriertype.items():
                                            if carriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_carriertype:
                                                bufID_carriertype=buf
                                            elif linkcarriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_linkcarriertype:
                                                if buf != bufID_carriertype:
                                                    bufID_linkcarriertype=buf
                                            if bufID_carriertype and bufID_linkcarriertype:
                                                break

                                        if linkcarriertype and not bufID_linkcarriertype:
                                            continue

                                        if bufID_carriertype:
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer_BaguioWB(host_tr_cmd[1], bufID_carriertype,need_sort=True)
                                            self.adapter.logger.info("vehicle_wq with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if linkcarriertype:
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer_BaguioWB(host_tr_cmd_1, bufID_linkcarriertype, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])
                                            self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                            break
    
                                    else:
                                        if host_tr_cmd[1].get('replace'):#Yuri 2024/10/11
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            local_tr_cmd_1={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-UNLOAD',
                                                    'carrierID':host_tr_cmd[1]['TransferInfoList'][1].get('CarrierID', ''),
                                                    'carrierLoc':host_tr_cmd[1]['dest'],
                                                    'source':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'dest':host_tr_cmd[1].get('back', '*'), #chocp 9/3
                                                    'first':False,
                                                    'last':True,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][1],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][1],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer_BaguioWB(local_tr_cmd_1, buf_list[0],swp=1)

                                            local_tr_cmd_2={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-LOAD',
                                                    'carrierID':host_tr_cmd[1]['carrierID'],
                                                    'carrierLoc':host_tr_cmd[1]['source'],
                                                    'source':host_tr_cmd[1]['source'],
                                                    'dest':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'first':True,
                                                    'last':False,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][0],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][0],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer_BaguioWB(local_tr_cmd_2, bufID ,fromvehicle=True,swp=1)
                                        else:
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer_BaguioWB(host_tr_cmd[1], buf_list[0] )
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if host_tr_cmd[1].get('link'):
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer_BaguioWB(host_tr_cmd_1, bufID, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])

                                        self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                        E82.report_event(self.secsgem_e82_h,
                                                            E82.VehicleAssigned,{
                                                            'VehicleID':self.id,
                                                            'CommandIDList':self.CommandIDList,
                                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                            'BatteryValue':self.adapter.battery['percentage']})

                                        output('VehicleAssigned',{
                                                'Battery':self.adapter.battery['percentage'],
                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                'Connected':self.adapter.online['connected'],
                                                'Health':self.adapter.battery['SOH'],
                                                'MoveStatus':self.adapter.move['status'],
                                                'RobotStatus':self.adapter.robot['status'],
                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                'VehicleID':self.id,
                                                'VehicleState':self.AgvState,
                                                'Message':self.message,
                                                'ForceCharge':self.force_charge, #???
                                                'CommandIDList':self.CommandIDList}, True)
                                        break

                        vehicle_wq.wq_lock.release()
                    except:
                        vehicle_wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))

            if try_append_transfer and self.wq and TransferAllowed:
                self.wq.wq_lock.acquire()
                try:
                    major_candidates=[]
                    num, buf_list=self.buf_available2()
                    
                    
                    if num and len(self.wq.queue):
                        for idx, host_tr_cmd in enumerate(self.wq.queue):
                            source_port=host_tr_cmd['source']
                            TransferAllowe_dest_port=host_tr_cmd['dest']
                            
                            h_workstation=EqMgr.getInstance().workstations.get(source_port)
                            distance=tools.calculate_distance(self.adapter.last_point, source_port)
                            if not host_tr_cmd.get('link') and h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                                if first_target_eqID == h_workstation.equipmentID:
                                    major_candidates.append([idx,host_tr_cmd,distance])

                                else:
                                    if first_target_eqID=="":
                                        if distance<=5000:
                                            
                                            h_workstation_TransferAllowe_source_port=EqMgr.getInstance().workstations.get(host_tr_cmd['source'])
                                            self.adapter.logger.info("first_target_eqID:{}".format(first_target_eqID))
                                            self.adapter.logger.info("***host_tr_cmd['source']:{}".format(host_tr_cmd['source']))
                                            if h_workstation_TransferAllowe_source_port: # h_workstation_TransferAllowe_source_port is
                                                h_workstation_TransferAllowe_equipmentID=h_workstation_TransferAllowe_source_port.equipmentID
                                                

                                                can_add_major_candidates=True
                                                check_Transfer_allowed_destport="{}-L-1".format(h_workstation_TransferAllowe_equipmentID)
                                                self.adapter.logger.info("***check_Transfer_allowed_destport:{}".format(check_Transfer_allowed_destport))
                                                for idx_check, host_tr_cmd_check in enumerate(self.wq.queue):
                                                    self.adapter.logger.info("***host_tr_cmd_check['dest']:{}".format(host_tr_cmd_check['dest']))
                                                    
                                                    if check_Transfer_allowed_destport==host_tr_cmd_check['dest']:
                                                        can_add_major_candidates = False
                                                        break
                                                    
                                                if can_add_major_candidates:
                                                    major_candidates.append([idx,host_tr_cmd,distance])
                                            else:
                                                continue
                                    
                            else:  
                                major_candidates.append([idx,host_tr_cmd,distance])
                            if idx>10:
                                break
                        
                        temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])
                        
                        i=0
                        length_of_temp_major_candidates=len(temp_major_candidates)
                        can_use_buffer_list=buf_list
                        while TransferAllowed and temp_major_candidates:
                            host_tr_cmd_1 =temp_major_candidates[i]
                            self.adapter.ogger.debug("can_use_buffer_list:{}".format(can_use_buffer_list))

                            for bufID in buf_list:
                                if host_tr_cmd_1[1].get('BufConstrain'):
                                    bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections','')
                                    if bufferAllowedDirections and bufferAllowedDirections != 'All':
                                        if bufID not in self.bufferDirection[bufferAllowedDirections]:
                                            continue
                                    else:
                                        if bufID not in self.vehicle_onTopBufs:
                                            continue
                                    if self.check_carrier_type == 'yes':
                                        if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                            continue
                                    self.adapter.logger.info("before insert")
                                    for action in self.actions:
                                        self.adapter.logger.info(action)
                                    self.wq.remove_waiting_transfer_by_idx(host_tr_cmd_1[1], host_tr_cmd_1[0])
                                    self.append_transfer_BaguioWB(host_tr_cmd_1[1], bufID)
                                    TransferAllowed=False
                                    break
                                else:
                                    if self.check_carrier_type == 'yes':
                                        if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                            continue
                                    
                                    if host_tr_cmd_1[1].get('uuid'):
                                        
                                        self.CommandIDList.append(host_tr_cmd_1[1]['uuid'])
                                        self.adapter.logger.info("appendTransferAllowed by {}".format(host_tr_cmd_1[1].get("CommandInfo").get("CommandID")))
                                        E82.report_event(self.secsgem_e82_h,
                                                            E82.VehicleAssigned,{
                                                            'VehicleID':self.id,
                                                            'CommandIDList':self.CommandIDList,
                                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                            'BatteryValue':self.adapter.battery['percentage']})

                                        output('VehicleAssigned',{
                                                'Battery':self.adapter.battery['percentage'],
                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                'Connected':self.adapter.online['connected'],
                                                'Health':self.adapter.battery['SOH'],
                                                'MoveStatus':self.adapter.move['status'],
                                                'RobotStatus':self.adapter.robot['status'],
                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                'VehicleID':self.id,
                                                'VehicleState':self.AgvState,
                                                'Message':self.message,
                                                'ForceCharge':self.force_charge, #???
                                                'CommandIDList':self.CommandIDList})
                                    
                                    can_use_buffer_list.pop(0)
                                    i+=1
                                    if i<length_of_temp_major_candidates:
                                        TransferAllowed=True
                                    else:
                                        TransferAllowed=False
                                    break
                            else:
                                i+=1
                                continue
            
                    self.wq.wq_lock.release()
                except:
                    self.wq.wq_lock.release()
                    msg=traceback.format_exc()
                    self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))
                    pass
        
    def append_transfer_allowed_for_ASE_K11(self, actions):#kelvinng20250406
        print('into append_transfer_allowed_for_K11')
        vehicle_wq=TransferWaitQueue.getInstance(self.id)
        if self.last_action_is_for_workstation and self.appendTransferAllowed == 'yes' and self.appendTransferAlgo == 'appendTransfer': #append transfer 2023/3/23
            try_append_transfer=False
            target=actions[0].get('target', '')
            at_equipmentID=''
            h_workstation=EqMgr.getInstance().workstations.get(target) 
            if actions[0].get('point', '') != self.adapter.last_point:
                point_to_port=PortsTable.reverse_mapping[self.adapter.last_point]
                if len(point_to_port):
                    at_station=EqMgr.getInstance().workstations.get(point_to_port[0])
                    if at_station:
                        at_equipmentID=at_station.equipmentID
                        t_equipmentID=EqMgr.getInstance().workstations.get(actions[0]['target']).equipmentID
                        if at_equipmentID != t_equipmentID:
                            if len(self.actions)<2:
                                try_append_transfer=True
                            else:
                                if self.actions[0]["target"] == self.actions[1]["target"]:
                                    self.adapter.logger.info("find swap already")
                                else:
                                    try_append_transfer=True#peter 241101
            elif actions[0].get('type') == 'DEPOSIT': #8.21K
                if h_workstation:
                    if 'Stock' in h_workstation.workstation_type:
                        try_append_transfer=True
                else:
                    try_append_transfer=True

                target_point=tools.find_point(target) #8.21-5
                if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                    try_append_transfer=False
            
            TransferAllowed=True
            if try_append_transfer and vehicle_wq:
                if tools.acquire_lock_with_timeout(vehicle_wq.wq_lock,3):
                    #vehicle_wq.wq_lock.acquire()
                    try:
                        major_candidates=[]
                        swap_commandID=[]
                        num, buf_list=self.buf_available()
                        if num and len(vehicle_wq.queue):
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if host_tr_cmd.get('link'):
                                    swap_commandID.append( host_tr_cmd.get('link').get('uuid'))
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if self.id  in host_tr_cmd.get('dest') or '*' in host_tr_cmd['dest']:
                                    continue
                                if host_tr_cmd.get('link'):
                                    source_port=host_tr_cmd['source']
                                    distance=tools.calculate_distance(self.adapter.last_point, source_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])
                                elif not host_tr_cmd.get('link') and host_tr_cmd.get('uuid') not in swap_commandID:
                                    dest_port=host_tr_cmd['dest']
                                    distance=tools.calculate_distance(self.adapter.last_point, dest_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])

                            temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])
                            if temp_major_candidates:
                                for host_tr_cmd in temp_major_candidates:
                                    if self.check_carrier_type == 'yes':
                                        if host_tr_cmd.get('HostSpecifyMR',''):
                                            continue
                                        vaildcarriertype={buf: self.carriertypedict[buf] for buf in buf_list}
                                        bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                        carriertype=host_tr_cmd[1]['TransferInfoList'][0].get('CarrierType', '')
                                        linkcarriertype=''
                                        bufID_carriertype=''
                                        bufID_linkcarriertype=''
                                        if host_tr_cmd[1].get('link'):
                                            linkcarriertype=host_tr_cmd[1].get('link')['TransferInfoList'][0].get('CarrierType', '')
                                        print(vaildcarriertype,bufID,carriertype,linkcarriertype)

                                        if (not bufID and not carriertype) or \
                                        (not bufID and all(carriertype not in v and 'All' not in v for v in vaildcarriertype.values())) or \
                                        (linkcarriertype and all(linkcarriertype not in v and 'All' not in v for v in vaildcarriertype.values())):
                                            continue

                                        for buf, v_carriertype_list in vaildcarriertype.items():
                                            if carriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_carriertype:
                                                bufID_carriertype=buf
                                            elif linkcarriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_linkcarriertype:
                                                if buf != bufID_carriertype:
                                                    bufID_linkcarriertype=buf
                                            if bufID_carriertype and bufID_linkcarriertype:
                                                break

                                        if linkcarriertype and not bufID_linkcarriertype:
                                            continue

                                        if bufID_carriertype:
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer(host_tr_cmd[1], bufID_carriertype )
                                            self.adapter.logger.info("vehicle_wq with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if linkcarriertype:
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer(host_tr_cmd_1, bufID_linkcarriertype, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])
                                            self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                            break
    
                                    else:
                                        if host_tr_cmd[1].get('replace'):#Yuri 2024/10/11
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            local_tr_cmd_1={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-UNLOAD',
                                                    'carrierID':host_tr_cmd[1]['TransferInfoList'][1].get('CarrierID', ''),
                                                    'carrierLoc':host_tr_cmd[1]['dest'],
                                                    'source':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'dest':host_tr_cmd[1].get('back', '*'), #chocp 9/3
                                                    'first':False,
                                                    'last':True,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][1],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][1],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer(local_tr_cmd_1, buf_list[0],swp=1)

                                            local_tr_cmd_2={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-LOAD',
                                                    'carrierID':host_tr_cmd[1]['carrierID'],
                                                    'carrierLoc':host_tr_cmd[1]['source'],
                                                    'source':host_tr_cmd[1]['source'],
                                                    'dest':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'first':True,
                                                    'last':False,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][0],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][0],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer(local_tr_cmd_2, bufID ,fromvehicle=True,swp=1)
                                        else:
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer(host_tr_cmd[1], buf_list[0] )
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if host_tr_cmd[1].get('link'):
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer(host_tr_cmd_1, bufID, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])

                                        self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                        E82.report_event(self.secsgem_e82_h,
                                                            E82.VehicleAssigned,{
                                                            'VehicleID':self.id,
                                                            'CommandIDList':self.CommandIDList,
                                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                            'BatteryValue':self.adapter.battery['percentage']})

                                        output('VehicleAssigned',{
                                                'Battery':self.adapter.battery['percentage'],
                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                'Connected':self.adapter.online['connected'],
                                                'Health':self.adapter.battery['SOH'],
                                                'MoveStatus':self.adapter.move['status'],
                                                'RobotStatus':self.adapter.robot['status'],
                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                'VehicleID':self.id,
                                                'VehicleState':self.AgvState,
                                                'Message':self.message,
                                                'ForceCharge':self.force_charge, #???
                                                'CommandIDList':self.CommandIDList}, True)
                                        break

                        vehicle_wq.wq_lock.release()
                    except:
                        vehicle_wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))

            if try_append_transfer and self.wq and TransferAllowed:
                if tools.acquire_lock_with_timeout(self.wq.wq_lock,3):
                    try:
                        major_candidates=[]
                        num, buf_list=self.buf_available2()
                        distanc2=tools.calculate_distance(self.adapter.last_point, self.actions[0]["target"])
                        self.adapter.logger.info("{},{},{}".format(num,distanc2,len(self.wq.queue)))

                        if num and len(self.wq.queue):
                            for idx, host_tr_cmd in enumerate(self.wq.queue):
                                source_port=host_tr_cmd['source']
                                h_workstation=EqMgr.getInstance().workstations.get(source_port)
                                distance=tools.calculate_distance(self.adapter.last_point, source_port)
                                if (not host_tr_cmd.get('link') or (host_tr_cmd.get('link') and global_variables.RackNaming==36)) and h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                                    self.adapter.logger.debug("last_point:{},sourceport:{},distance:{}".format(self.adapter.last_point,source_port,distance))
                                    if host_tr_cmd['priority']>=2:
                                        host_tr_cmd['insert_type']="high_priority"
                                        major_candidates.append([idx,host_tr_cmd,distance])
                                        break
                                    elif distance<=distanc2:
                                        s_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd['source']).equipmentID 
                                        d_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd['dest']).equipmentID
                                        if s_equipmentID == d_equipmentID and not host_tr_cmd.get('shiftTransfer',False):
                                            host_tr_cmd['insert_type']="continuous_action"
                                            major_candidates.append([idx,host_tr_cmd,distance])
                                        elif self.actions[0]["target"] == host_tr_cmd["source"] and self.actions[0]['type'] == "DEPOSIT":
                                            host_tr_cmd['insert_type']="getlink"
                                            major_candidates.append([idx,host_tr_cmd,distance])
                                        else:
                                            host_tr_cmd['insert_type']="normal_insert"
                                            major_candidates.append([idx,host_tr_cmd,distance])
                                if idx>10: #only search 10 cmds  #8.21K
                                    break
                            
                            self.adapter.logger.info("major_candidates:{}".format(major_candidates))
                            flattened_candidates=[candidate[1] for candidate in major_candidates]
                            if any(candidate["insert_type"] == "high_priority" for candidate in flattened_candidates):
                                major_candidates=[candidate for candidate in major_candidates if candidate[1].get("insert_type") == "high_priority"]   
                            elif any(candidate["insert_type"] == "continuous_action" for candidate in flattened_candidates):
                                major_candidates=[candidate for candidate in major_candidates if candidate[1].get("insert_type") == "continuous_action"]  
                            elif any(candidate["insert_type"] == "getlink" for candidate in flattened_candidates):
                                major_candidates=[candidate for candidate in major_candidates if candidate[1].get("insert_type") == "getlink"]  
                            
                            temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])

                            i=0
                            while TransferAllowed and temp_major_candidates:
                                host_tr_cmd_1 =temp_major_candidates[i]
                                carriertype=host_tr_cmd_1[1]['TransferInfoList'][0].get('CarrierType', '')
                                self.adapter.logger.info("before insert")
                                for action in self.actions:
                                    self.adapter.logger.info(action)

                                
                               
                                for bufID in buf_list:
                                    
                                        

                                    if host_tr_cmd_1[1].get('BufConstrain'):
                                        bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections','')
                                        if bufferAllowedDirections and bufferAllowedDirections != 'All':
                                            if bufID not in self.bufferDirection[bufferAllowedDirections]:
                                                continue
                                        else:
                                            if bufID not in self.vehicle_onTopBufs:
                                                continue
                                        if self.check_carrier_type == 'yes':
                                            if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                                continue
                                            
                                            
                                        
                                        self.wq.remove_waiting_transfer_by_idx(host_tr_cmd_1[1], host_tr_cmd_1[0])
                                        byTheWay=True
                                        self.adapter.logger.info("insert_type:{}".format(host_tr_cmd_1[1].get("insert_type")))
                                        s_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd_1[1]['source']).equipmentID
                                        d_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd_1[1]['dest']).equipmentID
                                        if host_tr_cmd_1[1].get("insert_type") in ["normal_insert","getlink"]:
                                            byTheWay=False
                                        
                                    
                                        self.append_transfer(host_tr_cmd_1[1], bufID,byTheWay=byTheWay)
                                        buf_list=buf_list[1:]
                                        TransferAllowed=False
                                        self.adapter.logger.info("after insert in BufConstrain")
                                        self.adapter.logger.info("last point:{}".format(self.adapter.last_point))
                                        for action in self.actions:
                                            
                                            self.adapter.logger.info("loc:{},target:{},type:{},uuid:{},priority:{},received_time:{}".format(action.get("loc"),action.get("target"),action.get("type"),action.get("local_tr_cmd").get("host_tr_cmd").get("uuid"),action.get("local_tr_cmd").get("host_tr_cmd").get("priority"),action.get("local_tr_cmd").get("host_tr_cmd").get("received_time")))
                                        

                                        if host_tr_cmd_1[1].get('uuid'):
                                            #self.CommandIDList=[host_tr_cmd_1[1].get("CommandInfo").get("CommandID")]
                                            self.CommandIDList.append(host_tr_cmd_1[1]['uuid'])
                                            #IN appendTransferAllowed add VehicleAssigned
                                            self.adapter.logger.info("appendTransferAllowed by {}".format(host_tr_cmd_1[1].get("CommandInfo").get("CommandID")))
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                        TransferAllowed=False
                                        break
                                    else:
                                        if self.check_carrier_type == 'yes':
                                            if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                                continue

                                        self.wq.remove_waiting_transfer_by_idx(host_tr_cmd_1[1], host_tr_cmd_1[0])
                                        byTheWay=True
                                        
                                        self.adapter.logger.info("insert_type:{}".format(host_tr_cmd_1[1].get("insert_type")))
                                        s_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd_1[1]['source']).equipmentID
                                        d_equipmentID=EqMgr.getInstance().workstations.get(host_tr_cmd_1[1]['dest']).equipmentID
                                        if host_tr_cmd_1[1].get("insert_type") in ["normal_insert","getlink"]:
                                            byTheWay=False
                                            
                                        
                                        self.append_transfer(host_tr_cmd_1[1], bufID,byTheWay=byTheWay)
                                        buf_list=buf_list[1:]
                                        # if host_tr_cmd_1[1].get('uuid'):
                                        #     self.CommandIDList.append(host_tr_cmd_1[1]['uuid'])
                                            # self.adapter.logger.info("appendTransferAllowed by {}".format(host_tr_cmd_1[1].get("CommandInfo").get("CommandID")))
                                            # self.append_transfer_report_assign()
                                        TransferAllowed=False
                                        self.adapter.logger.info("after insert in no BufConstrain")
                                        self.adapter.logger.info("last point:{}".format(self.adapter.last_point))
                                        for action in self.actions:
                                            
                                            self.adapter.logger.info("loc:{},target:{},type:{},uuid:{},priority:{},received_time:{}".format(action.get("loc"),action.get("target"),action.get("type"),action.get("local_tr_cmd").get("host_tr_cmd").get("uuid"),action.get("local_tr_cmd").get("host_tr_cmd").get("priority"),action.get("local_tr_cmd").get("host_tr_cmd").get("received_time")))
                                        

                                        if host_tr_cmd_1[1].get('uuid'):
                                            #self.CommandIDList=[host_tr_cmd_1[1].get("CommandInfo").get("CommandID")]
                                            self.CommandIDList.append(host_tr_cmd_1[1]['uuid'])
                                            #IN appendTransferAllowed add VehicleAssigned
                                            self.adapter.logger.info("appendTransferAllowed by {}".format(host_tr_cmd_1[1].get("CommandInfo").get("CommandID")))
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                        TransferAllowed=False
                                        break
                                else:
                                    i+=1
                                    continue
                        self.wq.wq_lock.release()

                    except:
                        self.wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))
                        pass
    
    def append_transfer_allowed_for_Renesas(self, actions):
        print('into append_transfer_allowed_for_Renesas')
        vehicle_wq=TransferWaitQueue.getInstance(self.id)
        if self.last_action_is_for_workstation and self.appendTransferAllowed == 'yes' and self.appendTransferAlgo == 'appendTransfer':
            try_append_transfer=False
            target=actions[0].get('target', '')
            at_equipmentID=''
            h_workstation=EqMgr.getInstance().workstations.get(target)
            target_point=tools.find_point(target) #8.21-5
            point_to_port=PortsTable.reverse_mapping[self.adapter.last_point]
            if len(point_to_port):
                at_station=EqMgr.getInstance().workstations.get(point_to_port[0])
                if at_station:
                    at_equipmentID=at_station.equipmentID
                    if at_equipmentID and at_station.valid_input and not self.error_skip_tr_req:
                    #if at_equipmentID and not at_station.valid_input and not actions[0].get('type') == 'DEPOSIT':
                        try_append_transfer=True
            if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                if actions[0].get('type') == 'ACQUIRE':
                    try_append_transfer=False
                    
            print('parmater',target,target_point,at_equipmentID,self.adapter.last_point,actions[0].get('type'),try_append_transfer)   
            if try_append_transfer and vehicle_wq:
                if len(vehicle_wq.queue):
                    try:
                        if tools.acquire_lock_with_timeout(vehicle_wq.wq_lock,3):
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if self.id+'BUF' in host_tr_cmd['source'] and at_equipmentID in host_tr_cmd['dest'] and '_OUT_OK' in host_tr_cmd['dest']:
                                    vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd, idx)
                                    self.append_transfer(host_tr_cmd, 'BUF00')
                                    self.adapter.logger.info("vehicle_wq get appendTransferAllowed(Renesas) by {}".format(host_tr_cmd.get("CommandInfo").get("CommandID")))
                                    self.CommandIDList.append(host_tr_cmd['uuid'])
                                    E82.report_event(self.secsgem_e82_h,
                                                        E82.VehicleAssigned,{
                                                        'VehicleID':self.id,
                                                        'CommandIDList':self.CommandIDList,
                                                        'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                        'BatteryValue':self.adapter.battery['percentage']})

                                    output('VehicleAssigned',{
                                            'Battery':self.adapter.battery['percentage'],
                                            'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                            'Connected':self.adapter.online['connected'],
                                            'Health':self.adapter.battery['SOH'],
                                            'MoveStatus':self.adapter.move['status'],
                                            'RobotStatus':self.adapter.robot['status'],
                                            'RobotAtHome':self.adapter.robot['at_home'],
                                            'VehicleID':self.id,
                                            'VehicleState':self.AgvState,
                                            'Message':self.message,
                                            'ForceCharge':self.force_charge, #???
                                            'CommandIDList':self.CommandIDList}, True)
                                    vehicle_wq.wq_lock.release()
                                    return True
                            vehicle_wq.wq_lock.release()        
                    except:
                        vehicle_wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer (renesas) code with a exception:\n {}'.format(self.wq.queueID, msg))
        return False

    def append_transfer_allowed(self, actions): #8.27.14-2
        vehicle_wq=TransferWaitQueue.getInstance(self.id)
        if self.last_action_is_for_workstation and self.appendTransferAllowed == 'yes' and self.appendTransferAlgo == 'appendTransfer': #append transfer 2023/3/23
            try_append_transfer=False
            target=actions[0].get('target', '')
            at_equipmentID=''
            h_workstation=EqMgr.getInstance().workstations.get(target) 
            if global_variables.RackNaming==36 and actions[0].get('point', '')!=self.adapter.last_point:
                point_to_port=PortsTable.reverse_mapping[self.adapter.last_point]
                if len(point_to_port):
                    at_station=EqMgr.getInstance().workstations.get(point_to_port[0])
                    if at_station:
                        at_equipmentID=at_station.equipmentID
                        t_equipmentID=EqMgr.getInstance().workstations.get(actions[0]['target']).equipmentID
                        if at_equipmentID!=t_equipmentID:
                            if len(self.actions)<2:try_append_transfer=True
                            else:
                                if self.actions[0]["target"]==self.actions[1]["target"]:self.adapter.logger.info("find swap already")
                                else:try_append_transfer=True#peter 241101
            elif actions[0].get('type') == 'DEPOSIT': #8.21K
                if h_workstation:
                    if 'Stock' in h_workstation.workstation_type:
                        try_append_transfer=True
                else:
                    try_append_transfer=True

                target_point=tools.find_point(target) #8.21-5
                if target_point == self.adapter.last_point: #when MR in erack don't try_append_transfer
                    try_append_transfer=False
                    
            if global_variables.RackNaming!=36:      
                for action in actions:
                    if action.get('type') == 'ACQUIRE':
                        try_append_transfer=False
            # if global_variables.RackNaming in [16, 23, 34, 54]: # zhangpeng 2025/02/24 # Fix transfer will be appended to the execution queue when there is a task with priority 101 in the execution queue.
            if actions[0].get('local_tr_cmd', {}).get('host_tr_cmd', {}).get('priority', '') == 101:
                try_append_transfer=False

            TransferAllowed=True
            if try_append_transfer and vehicle_wq:
                if tools.acquire_lock_with_timeout(vehicle_wq.wq_lock,3):
                    #vehicle_wq.wq_lock.acquire()
                    try:
                        major_candidates=[]
                        swap_commandID=[]
                        num, buf_list=self.buf_available()
                        if num and len(vehicle_wq.queue):
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if host_tr_cmd.get('link'):
                                    swap_commandID.append( host_tr_cmd.get('link').get('uuid'))
                            for idx, host_tr_cmd in enumerate(vehicle_wq.queue):
                                if self.id  in host_tr_cmd.get('dest') or '*' in host_tr_cmd['dest']:
                                    continue
                                if host_tr_cmd.get('link'):
                                    source_port=host_tr_cmd['source']
                                    distance=tools.calculate_distance(self.adapter.last_point, source_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])
                                elif not host_tr_cmd.get('link') and host_tr_cmd.get('uuid') not in swap_commandID:
                                    dest_port=host_tr_cmd['dest']
                                    distance=tools.calculate_distance(self.adapter.last_point, dest_port)
                                    major_candidates.append([idx,host_tr_cmd,distance])

                            temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])
                            if temp_major_candidates:
                                for host_tr_cmd in temp_major_candidates:
                                    if self.check_carrier_type == 'yes':
                                        if host_tr_cmd.get('HostSpecifyMR',''):
                                            continue
                                        vaildcarriertype={buf: self.carriertypedict[buf] for buf in buf_list}
                                        bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                        carriertype=host_tr_cmd[1]['TransferInfoList'][0].get('CarrierType', '')
                                        linkcarriertype=''
                                        bufID_carriertype=''
                                        bufID_linkcarriertype=''
                                        if host_tr_cmd[1].get('link'):
                                            linkcarriertype=host_tr_cmd[1].get('link')['TransferInfoList'][0].get('CarrierType', '')
                                        print(vaildcarriertype,bufID,carriertype,linkcarriertype)

                                        if (not bufID and not carriertype) or \
                                        (not bufID and all(carriertype not in v and 'All' not in v for v in vaildcarriertype.values())) or \
                                        (linkcarriertype and all(linkcarriertype not in v and 'All' not in v for v in vaildcarriertype.values())):
                                            continue

                                        for buf, v_carriertype_list in vaildcarriertype.items():
                                            if carriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_carriertype:
                                                bufID_carriertype=buf
                                            elif linkcarriertype in v_carriertype_list or 'All' in v_carriertype_list and not bufID_linkcarriertype:
                                                if buf != bufID_carriertype:
                                                    bufID_linkcarriertype=buf
                                            if bufID_carriertype and bufID_linkcarriertype:
                                                break

                                        if linkcarriertype and not bufID_linkcarriertype:
                                            continue

                                        if bufID_carriertype:
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer(host_tr_cmd[1], bufID_carriertype )
                                            self.adapter.logger.info("vehicle_wq with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if linkcarriertype:
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer(host_tr_cmd_1, bufID_linkcarriertype, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link with check_carrier_type get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])
                                            self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                            break
    
                                    else:
                                        if host_tr_cmd[1].get('replace'):#Yuri 2024/10/11
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            local_tr_cmd_1={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-UNLOAD',
                                                    'carrierID':host_tr_cmd[1]['TransferInfoList'][1].get('CarrierID', ''),
                                                    'carrierLoc':host_tr_cmd[1]['dest'],
                                                    'source':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'dest':host_tr_cmd[1].get('back', '*'), #chocp 9/3
                                                    'first':False,
                                                    'last':True,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][1],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][1],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer(local_tr_cmd_1, buf_list[0],swp=1)

                                            local_tr_cmd_2={
                                                    'uuid':host_tr_cmd[1]['uuid']+'-LOAD',
                                                    'carrierID':host_tr_cmd[1]['carrierID'],
                                                    'carrierLoc':host_tr_cmd[1]['source'],
                                                    'source':host_tr_cmd[1]['source'],
                                                    'dest':host_tr_cmd[1]['dest'],
                                                    'priority':host_tr_cmd[1]['priority'],
                                                    'first':True,
                                                    'last':False,
                                                    'TransferInfo':host_tr_cmd[1]['TransferInfoList'][0],
                                                    'OriginalTransferInfo':host_tr_cmd[1]['OriginalTransferInfoList'][0],
                                                    'host_tr_cmd':host_tr_cmd[1]
                                                    }
                                            self.append_transfer(local_tr_cmd_2, bufID ,fromvehicle=True,swp=1)
                                        else:
                                            bufID=self.find_buf_idx_by_carrierID(host_tr_cmd[1]['carrierID'])
                                            vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd[1], host_tr_cmd[0])
                                            self.append_transfer(host_tr_cmd[1], buf_list[0] )
                                            self.adapter.logger.info("vehicle_wq get appendTransferAllowed by {}".format(host_tr_cmd[1].get("CommandInfo").get("CommandID")))
                                            TransferAllowed=False
                                            if host_tr_cmd[1].get('link'):
                                                for idx, host_tr_cmd_1 in enumerate(vehicle_wq.queue):
                                                    if host_tr_cmd[1].get('link').get('uuid','') == host_tr_cmd_1.get('uuid'): 
                                                        vehicle_wq.remove_waiting_transfer_by_idx(host_tr_cmd_1, idx)                                    
                                                        self.append_transfer(host_tr_cmd_1, bufID, fromvehicle=True)
                                                        self.adapter.logger.info("vehicle_wq link get appendTransferAllowed by {}".format(host_tr_cmd_1.get('uuid')))
                                                        self.CommandIDList.append(host_tr_cmd_1['uuid'])

                                        self.CommandIDList.append(host_tr_cmd[1]['uuid'])
                                        E82.report_event(self.secsgem_e82_h,
                                                            E82.VehicleAssigned,{
                                                            'VehicleID':self.id,
                                                            'CommandIDList':self.CommandIDList,
                                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                            'BatteryValue':self.adapter.battery['percentage']})

                                        output('VehicleAssigned',{
                                                'Battery':self.adapter.battery['percentage'],
                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                'Connected':self.adapter.online['connected'],
                                                'Health':self.adapter.battery['SOH'],
                                                'MoveStatus':self.adapter.move['status'],
                                                'RobotStatus':self.adapter.robot['status'],
                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                'VehicleID':self.id,
                                                'VehicleState':self.AgvState,
                                                'Message':self.message,
                                                'ForceCharge':self.force_charge, #???
                                                'CommandIDList':self.CommandIDList}, True)
                                        break

                        vehicle_wq.wq_lock.release()
                    except:
                        vehicle_wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))

            if try_append_transfer and self.wq and TransferAllowed:
                if tools.acquire_lock_with_timeout(self.wq.wq_lock,3):
                #self.wq.wq_lock.acquire()
                    try:
                        major_candidates=[]
                        if global_variables.RackNaming == 36:
                            num, buf_list=self.buf_available2()
                            distanc2=tools.calculate_distance(self.adapter.last_point, self.actions[0]["target"])
                            self.adapter.logger.info("{},{},{}".format(num,distanc2,len(self.wq.queue)))
                        else:
                            num, buf_list=self.buf_available()
                            
                        if num and len(self.wq.queue):
                            for idx, host_tr_cmd in enumerate(self.wq.queue):
                                source_port=host_tr_cmd['source']
                                h_workstation=EqMgr.getInstance().workstations.get(source_port)
                                distance=tools.calculate_distance(self.adapter.last_point, source_port)
                                if (not host_tr_cmd.get('link') or (host_tr_cmd.get('link') and global_variables.RackNaming==36)) and h_workstation and 'Stock' not in h_workstation.workstation_type: #8.21K
                                    self.adapter.logger.debug("last_point:{},sourceport:{},distance:{}".format(self.adapter.last_point,source_port,distance))
                                    if global_variables.RackNaming == 18:
                                        if distance<=10000:
                                            self.adapter.logger.info("last_point:{},sourceport:{},distance:{}".format(self.adapter.last_point,source_port,distance))
                                            major_candidates.append([idx,host_tr_cmd,distance])
                                    elif global_variables.RackNaming == 21: #Hshuo 240708 for ASECL M11 when sourceport is plasma don't do append transfer
                                        if source_port not in ['A','B','C','D']:
                                            self.adapter.logger.info("last_point:{},sourceport:{},distance:{}".format(self.adapter.last_point,source_port,distance))
                                            major_candidates.append([idx,host_tr_cmd,distance]) 
                                    elif global_variables.RackNaming==36:
                                        if distance<=distanc2:
                                            if self.actions[0]["target"]==host_tr_cmd["source"]:
                                                host_tr_cmd['insert_type']="getlink"
                                                major_candidates.append([idx,host_tr_cmd,distance])
                                                break
                                            else:
                                                host_tr_cmd['insert_type']="normal_insert"
                                                major_candidates.append([idx,host_tr_cmd,distance])
                                    else:
                                        major_candidates.append([idx,host_tr_cmd,distance])
                                if idx>10: #only search 10 cmds  #8.21K
                                    break
                            if global_variables.RackNaming==36:
                                self.adapter.logger.info("major_candidates:{}".format(major_candidates))
                                flattened_candidates = [candidate[1] for candidate in major_candidates]
                                if any(candidate["insert_type"] == "getlink" for candidate in flattened_candidates):
                                    major_candidates = [candidate for candidate in major_candidates if candidate[1].get("insert_type") == "getlink"]    
                            #temp_major_candidates=major_candidates_vehicle if major_candidates_vehicle else major_candidates
                            temp_major_candidates=sorted(major_candidates, key=lambda h: h[2])
                            i=0
                            
                            while TransferAllowed and temp_major_candidates:
                                host_tr_cmd_1 =temp_major_candidates[i]
                                carriertype=host_tr_cmd_1[1]['TransferInfoList'][0].get('CarrierType', '')
                                for bufID in buf_list:
                                    if host_tr_cmd_1[1].get('BufConstrain'):
                                        bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections','')
                                        if bufferAllowedDirections and bufferAllowedDirections != 'All':
                                            if bufID not in self.bufferDirection[bufferAllowedDirections]:
                                                continue
                                        else:
                                            if bufID not in self.vehicle_onTopBufs:
                                                continue
                                        if self.check_carrier_type == 'yes':
                                            if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                                continue
                                        self.adapter.logger.info("before insert")
                                        for action in self.actions:
                                            self.adapter.logger.info(action)
                                        self.wq.remove_waiting_transfer_by_idx(host_tr_cmd_1[1], host_tr_cmd_1[0])
                                        self.append_transfer(host_tr_cmd_1[1], bufID)
                                        TransferAllowed=False
                                        break
                                    else:
                                        if self.check_carrier_type == 'yes':
                                            if carriertype not in self.carriertypedict[bufID] and 'All' not in self.carriertypedict[bufID]:
                                                continue
                                        self.wq.remove_waiting_transfer_by_idx(host_tr_cmd_1[1], host_tr_cmd_1[0])
                                        if global_variables.RackNaming!=18:
                                            if global_variables.RackNaming == 36:
                                                self.append_transfer(host_tr_cmd_1[1], bufID,byTheWay=False)
                                                self.adapter.logger.info("after insert")
                                                for action in self.actions:
                                                    self.adapter.logger.info(action)
                                            else:
                                                self.append_transfer(host_tr_cmd_1[1], bufID)

                                        else: #for K25
                                            h_workstation_check=EqMgr.getInstance().workstations.get(host_tr_cmd_1[1].get("dest"))
                                            if h_workstation_check:
                                                if "StockIn" in h_workstation_check.workstation_type:                                                           
                                                    if SaveStockerInDestPortByVehicleId.save_dest_port.get(self.id) !=None:
                                                        if SaveStockerInDestPortByVehicleId.save_dest_port.get(self.id)!="":#kelvin
                                                            if host_tr_cmd_1[1].get("dest")!=SaveStockerInDestPortByVehicleId.save_dest_port.get(self.id,""):
                                                                
                                                                host_tr_cmd_1[1]["dest"]=SaveStockerInDestPortByVehicleId.save_dest_port.get(self.id,"")#kelvin
                                                                host_tr_cmd_1[1]['TransferInfoList'][0]["DestPort"]=SaveStockerInDestPortByVehicleId.save_dest_port.get(self.id,"")#kelvin
                                                            
                                                                self.append_transfer(host_tr_cmd_1[1], bufID)
                                                            else:
                                                                self.append_transfer(host_tr_cmd_1[1], bufID)
                                                                
                                                        else:
                                                            SaveStockerInDestPortByVehicleId.save_dest_port[self.id]=host_tr_cmd_1[1].get("dest")#kelvin
                                                            self.append_transfer(host_tr_cmd_1[1], bufID)
                                                    else:
                                                        SaveStockerInDestPortByVehicleId.save_dest_port[self.id]=host_tr_cmd_1[1].get("dest")

                                                else:
                                                    self.append_transfer(host_tr_cmd_1[1], bufID)
                                            else:
                                                self.append_transfer(host_tr_cmd_1[1], bufID)

                                        #if host_tr_cmd_1[1].get("CommandInfo").get("CommandID")!="":
                                        if host_tr_cmd_1[1].get('uuid'):
                                            #self.CommandIDList=[host_tr_cmd_1[1].get("CommandInfo").get("CommandID")]
                                            self.CommandIDList.append(host_tr_cmd_1[1]['uuid'])
                                            #IN appendTransferAllowed add VehicleAssigned
                                            self.adapter.logger.info("appendTransferAllowed by {}".format(host_tr_cmd_1[1].get("CommandInfo").get("CommandID")))
                                            E82.report_event(self.secsgem_e82_h,
                                                                E82.VehicleAssigned,{
                                                                'VehicleID':self.id,
                                                                'CommandIDList':self.CommandIDList,
                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                'BatteryValue':self.adapter.battery['percentage']})

                                            output('VehicleAssigned',{
                                                    'Battery':self.adapter.battery['percentage'],
                                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                    'Connected':self.adapter.online['connected'],
                                                    'Health':self.adapter.battery['SOH'],
                                                    'MoveStatus':self.adapter.move['status'],
                                                    'RobotStatus':self.adapter.robot['status'],
                                                    'RobotAtHome':self.adapter.robot['at_home'],
                                                    'VehicleID':self.id,
                                                    'VehicleState':self.AgvState,
                                                    'Message':self.message,
                                                    'ForceCharge':self.force_charge, #???
                                                    'CommandIDList':self.CommandIDList}, True)
                                        TransferAllowed=False
                                        break
                                else:
                                    i+=1
                                    continue
                
                        self.wq.wq_lock.release()
                    except:
                        self.wq.wq_lock.release()
                        msg=traceback.format_exc()
                        self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))
                        pass

    def emergency_evacuation(self,Situation):
        self.emergency_evacuation_cmd=True
        self.emergency_situation=Situation # FireDisaster  EarthQuake
        self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'Get emergency evacuation cmd and start abort all transfer cmd', Situation))
        del_command_id_list=[] 
        for del_tr_cmd in self.tr_cmds:
            del_command_id_list.append(del_tr_cmd.get('uuid', ''))

        for del_command_id in del_command_id_list:
            self.abort_tr_cmds_and_actions(del_command_id, self.error_code, self.error_txt, cause='by emergency evacuation')
            
    def enroute_append_transfer(self,num,buf_list,point):
        num=num
        buf_list=buf_list
        command_id_list=[]
        host_tr_cmd=self.wq.tr_point[point]
        if len(host_tr_cmd) > 1:                        
            for local_host_tr_cmd in host_tr_cmd:
                if num <= 0:
                    break
                buf=tools.allocate_buffer(buf_list,local_host_tr_cmd[1],self.check_carrier_type,self.vehicle_onTopBufs,self.carriertypedict,self.bufferDirection)
                if not buf:
                    self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'No CarrierType or BufConstrain buffer',local_host_tr_cmd[1].get("uuid","")))
                    continue
                buf_list.remove(buf)
                self.wq.remove_waiting_transfer_by_idx(local_host_tr_cmd[1], local_host_tr_cmd[0],remove_directly=True)
                self.append_transfer(local_host_tr_cmd[1],buf)
                command_id_list.append(local_host_tr_cmd[1].get("uuid",""))
                num -= 1                     
        else:
            buf=tools.allocate_buffer(buf_list,host_tr_cmd[0][1],self.check_carrier_type,self.vehicle_onTopBufs,self.carriertypedict,self.bufferDirection)
            if not buf:
                self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'No  CarrierType or BufConstrain buffer',host_tr_cmd[0][1].get("uuid","")))
                return
            self.wq.remove_waiting_transfer_by_idx(host_tr_cmd[0][1], host_tr_cmd[0][0],remove_directly=True)
            self.append_transfer(host_tr_cmd[0][1],buf)
            command_id_list.append(host_tr_cmd[0][1].get("uuid",""))
        if command_id_list:
            #self.CommandIDList=[host_tr_cmd_1[1].get("CommandInfo").get("CommandID")]
            self.CommandIDList.extend(command_id_list)
            #IN appendTransferAllowed add VehicleAssigned
            self.adapter.logger.info("{} enroute_append_transfer_allowed by {}".format('[{}] '.format(self.id),','.join(str(command_id) for command_id in command_id_list)))
            E82.report_event(self.secsgem_e82_h,
                                        E82.VehicleAssigned,{
                                        'VehicleID':self.id,
                                        'CommandIDList':self.CommandIDList,
                                        'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                        'BatteryValue':self.adapter.battery['percentage']})

            output('VehicleAssigned',{
                                'Battery':self.adapter.battery['percentage'],
                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                'Connected':self.adapter.online['connected'],
                                'Health':self.adapter.battery['SOH'],
                                'MoveStatus':self.adapter.move['status'],
                                'RobotStatus':self.adapter.robot['status'],
                                'RobotAtHome':self.adapter.robot['at_home'],
                                'VehicleID':self.id,
                                'VehicleState':self.AgvState,
                                'Message':self.message,
                                'ForceCharge':self.force_charge, #???
                                'CommandIDList':self.CommandIDList})
            
    def enroute_append_transfer_allowed(self):#2024/10/29 Yuri
        point=self.adapter.reach_point
        self.old_point=point
        num, buf_list=self.buf_available()
        if self.wq and num and tools.appendTransferJudgment(self.actions,self.adapter.last_point):
            if tools.acquire_lock_with_timeout(self.wq.wq_lock,3):
                #self.wq.wq_lock.acquire()
                try:
                    if len(self.wq.tr_point) and point in self.wq.tr_point:
                        if self.adapter.vehicle_stop(Stime=0.41,check_stop=0):
                            self.enroute_append_transfer(num,buf_list,point)
                            self.wq.wq_lock.release()
                            return True
                        time.sleep(0.5)
                        if self.adapter.wait_stop==2:
                            self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'Stop cmd Reject'))
                        elif self.adapter.move['status'] == 'Idle' and self.adapter.wait_stop==1:
                            self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'Stop cmd Response timeout'))
                            self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'Vehicle stop cmd'))
                            self.adapter.planner.route_right_lock.acquire(True)
                            self.adapter.planner.current_route.clear() # Mike: 2021/03/17
                            self.adapter.planner.current_go_list.clear() # Mike: 2021/03/17
                            self.adapter.planner.route_right_lock.release()
                            th3=threading.Thread(target=self.adapter.planner.clean_right,)
                            th3.setDaemon(True)
                            th3.start()
                            if self.adapter.planner.get_right_th:
                                self.adapter.planner.get_right_th.join()
                            th3.join()
                            self.adapter.wait_stop=0
                            #self.old_point=""
                            self.enroute_append_transfer(num,buf_list,point)
                            self.wq.wq_lock.release()
                            return True

                    self.wq.wq_lock.release()
                    return False
                except:
                    self.wq.wq_lock.release()
                    msg=traceback.format_exc()
                    self.adapter.logger.info('Handling queue:{} in append transfer code with a exception:\n {}'.format(self.wq.queueID, msg))

            self.adapter.logger.debug('{} {} {}'.format('[{}] '.format(self.id), self.wq.queueID,'acquire lock with timeout'))      



    #how to remove vehicle dynamically???
    def run(self):
        self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'start loop thread'))

        #self.adapter=adapterMR.Adapter(self, self.id, self.ip, self.port, self.max_speed) #vehicle_instance=self

        self.adapter.setDaemon(True)
        self.adapter.start()

        time.sleep(3) #add delay for MR connecting
        last_AgvState='Unknown'
        last_AgvSubState=''
        last_stop_flag=None
        start_charge=False
        end_charge=False
        send_alarm=False
        AgvStateIndex=['Unknown','Removed','Unassigned','Enroute','Parked','Acquiring','Depositing','Pause','Charging','TrLoadReq','TrUnloadReq','Exchanging','Waiting','Evacuation','Shifting','Suspend','Swapping','TrSwapReq']
        
        while not self.thread_stop:
            try:
                self.heart_beat=time.time()
                if self.adapter.heart_beat > 0 and time.time() - self.adapter.heart_beat > 60:
                    self.adapter.heart_beat=0
                    self.adapter.logger.info('{}'.format("<<<  VehicleAdapter {} is dead. >>>".format(self.id)))
                if last_AgvState != self.AgvState or last_AgvSubState != self.AgvSubState or last_stop_flag != self.thread_stop:
                    try:
                        self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'Vehicle state: ', self.AgvState, self.AgvSubState, self.thread_stop, self.thread_stop))
                        E82.report_event(self.secsgem_e82_h,
                                        E82.VehicleStateChange,{
                                        'VehicleID':self.id,
                                        'VehicleInfo':{
                                            "VehicleID":self.id, 
                                            "VehicleState":AgvStateIndex.index(self.AgvState), 
                                            "VehicleLastState":AgvStateIndex.index(last_AgvState)
                                        }})
                    except:
                        pass
                    last_AgvState=self.AgvState
                    last_AgvSubState=self.AgvSubState
                    last_stop_flag=self.thread_stop
                #print(self.AgvState, self.adapter.online['sync'])
                time.sleep(0.1)
                # Mike: 2021/05/14
                ActiveVehicles=E82.get_variables(self.secsgem_e82_h, 'ActiveVehicles')
                if self.id in ActiveVehicles:
                    AgvState=0
                    try:
                        AgvState=AgvStateIndex.index(self.AgvState)
                    except:
                        pass
                    ActiveVehicles[self.id]["VehicleInfo"]["VehicleState"]=AgvState
                    E82.update_variables(self.secsgem_e82_h, {'ActiveVehicles': ActiveVehicles})
                if global_variables.global_generate_routes == False:

                    if self.AgvState == 'Removed':
                        if self.adapter.online['sync']:

                            # output('VehiclePoseUpdate',{
                            #         'VehicleID':self.id,
                            #         'Pose':[self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['h'], self.adapter.move['pose']['z']],
                            #         'Battery':self.adapter.battery['percentage'],
                            #         'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                            #         'Connected':self.adapter.online['connected'], # Mike: 2022/05/31
                            #         'Health':self.adapter.battery['SOH'],
                            #         'MoveStatus':self.adapter.move['status'],
                            #         'ForceCharge':self.force_charge,
                            #         'RobotStatus':self.adapter.robot['status'],
                            #         'RobotAtHome':self.adapter.robot['at_home']
                            #         })


                            output('VehicleInstalled',{
                                    'Point':self.adapter.last_point,
                                    'Station':self.at_station,
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'VehicleState':'Pause',
                                    'ForceCharge':self.force_charge,
                                    'Message':self.message})

                            E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleInstalled,{
                                            'VehicleID':self.id,
                                            'BatteryValue':self.adapter.battery['percentage']})

                            self.action_in_run={}
                            #self.tr_cmds=[]
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear()
                            self.AgvLastState=self.AgvState #fix 8/20
                            self.AgvState='Pause'
                            self.call_support_time=time.time()

                    elif self.AgvState == 'Pause': # with alarm
                        if self.AgvSubState == 'Disconnected': # with alarm
                            self.BufferUpdate()
                            time.sleep(1)
                            if self.adapter.online['connected'] and self.adapter.online['sync']:
                                if self.adapter.online['man_mode'] or self.manual:
                                    self.sub_alarm_state_handler('Manual')
                                else:
                                    self.sub_alarm_state_handler('Pause')

                        elif self.AgvSubState == 'Manual': # with alarm
                            self.BufferUpdate()
                            time.sleep(1)
                            if not self.adapter.online['connected']:
                                self.sub_alarm_state_handler('Disconnected')
                            elif not self.adapter.online['man_mode'] and not self.manual:
                                self.sub_alarm_state_handler('Pause')

                            if self.error_reset_cmd:
                                self.error_reset_cmd=False
                                if not self.manual:
                                    print(self.error_reset_cmd,self.AgvState)
                                    self.reset_alarm()

                        else:
                            self.BufferUpdate()
                            time.sleep(1)
                            
                            if not self.adapter.online['connected']:
                                # self.AgvLastState=self.AgvState
                                # self.AgvState='Disconnected'
                                self.sub_alarm_state_handler('Disconnected')

                            if self.adapter.online['man_mode']:
                                self.sub_alarm_state_handler('Manual') # zhangjunxian 2025-03-04 report state to UI

                            #print(self.error_code, self.adapter.alarm['error_code'], self.adapter.online['man_mode'], self.adapter.online['connected'])
                            if self.error_reset_cmd:
                                print(self.error_reset_cmd,self.AgvState)
                                self.error_reset_cmd=False
                                self.reset_alarm()
                                send_alarm=False

                            elif global_variables.TSCSettings.get('Recovery', {}).get('RetryBackThenForwardWhenJam') == 'yes' and self.error_code == 10009 and self.error_sub_code == '900001':#chocp 2021/12/
                                self.reset_traffic_jam()
                            
                            elif global_variables.TSCSettings.get('Recovery', {}).get('Auto') == 'yes' and not self.adapter.online['man_mode'] and self.adapter.online['connected'] and self.adapter.online['sync'] and\
                                    self.adapter.move['status'] == 'Idle' and self.adapter.robot['status'] == 'Idle':
                                #if self.error_code!=10001 and self.error_code!=10003 and self.error_code!=10004 and self.error_code!=10006 and self.error_code!=10010: #fix 5
                                if not self.alarm_set == 'Serious':
                                    #not robot error, base error, other error, internal error, manual test
                                    self.reset_alarm() #auto reset

                                else:
                                    #if global_variables.RackNaming == 6 or global_variables.RackNaming == 7: #????
                                    if global_variables.TSCSettings.get('Recovery', {}).get('RetryMoveWhenAlarmReset') == 'yes':
                                        if self.error_code == 10004 and not self.adapter.alarm['error_code'] and self.adapter.move['status'] == 'Idle' and self.adapter.robot['status'] == 'Idle': #chocp add 2021/1/21
                                            #from base error rset and continue
                                            self.release_alarm()
                                    if global_variables.TSCSettings.get('Recovery', {}).get('ReturnToFaultyErackWhenNoValidBuf') == 'yes':
                                        if self.error_code == 10018:
                                            self.alarm_set='Error'
                                            self.reset_alarm()
                                            
                            if self.error_retry_cmd and not self.adapter.alarm['error_code'] and self.adapter.move['status'] == 'Idle' and self.adapter.robot['status'] == 'Idle' and not self.adapter.online['man_mode']:
                                self.error_retry_cmd=False
                                self.retry_action()

                            #elif self.error_code == 10016 and self.adapter.online['connected']:
                            #   self.reset_alarm()????

                            if global_variables.TSCSettings.get('Recovery', {}).get('Auto') == 'no' or self.alarm_set == 'Serious':
                                if not send_alarm and self.error_code not in [0, 10008, 10009, 10010]:
                                    send_alarm=True
                                    self.adapter.alarm_control(self.error_code, True)
                                try: #2024/08/29 for Mirle mCS
                                    EnhancedALID={'ALID':self.error_code, 'AlarmText':self.error_txt,'UnitInfo':{"VehicleID": self.id, "VehicleState": 4}}
                                    AlarmsSetDescription=E82.get_variables(self.secsgem_e82_h, 'AlarmsSetDescription')
                                    AlarmsSetDescription[self.id]=EnhancedALID
                                    E82.update_variables(self.secsgem_e82_h, {'AlarmsSetDescription': AlarmsSetDescription})
                                except:
                                    pass

                    elif self.AgvErrorCheck(self.AgvState):
                        #self.alarm_handler(self.AgvState) #chocp
                        if self.wait_error_code == 1:
                            self.adapter.logger.info('AgvErrorCheck func error')
                        continue #chocp
                    
                    elif self.AgvState == 'Evacuation':
                        go_park=False
                        tmpPark=False
                        wait_vehicle='' # Mike: 2021/11/12
                        self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'Into Evacuation state and try return to standby station'))
                        for vehicle_id, h_vehicle in self.h_vehicleMgr.vehicles.items(): #chocp fix, 2021/10/14
                            if h_vehicle.id!=self.id:
                                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                                    self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id))
                                    go_park=True
                                    tmpPark=True
                                    wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                                    break
                        else:
                            if self.at_station  in self.evacuate_station:
                                raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)
                            elif not self.adapter.relay_on:
                                go_park=True
                        if go_park and self.evacuate_station:
                            if self.token.acquire(False):
                                try:
                                    self.AgvSubState='InStandbyCmdStatus'
                                    print('go_park', self.adapter.relay_on, self.evacuate_station)
                                    self.return_standby_cmd(wait_vehicle, tmpPark, from_unassigned=True , situation='Evacuation')
                                    self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()

                    elif self.AgvState == 'Waiting':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        dispatch_success=False
                        try_dispatch=False
                        if self.action_in_run.get('type', '') == 'ACQUIRE':
                            self.execute_action()
                        elif self.action_in_run.get('type', '') == 'ACQUIRE_STANDBY':
                            received_time=self.action_in_run['local_tr_cmd'].get('host_tr_cmd', {}).get('received_time', 0)
                            CommandInfo=self.action_in_run['local_tr_cmd'].get('host_tr_cmd', {}).get('CommandInfo', {})
                            if received_time and CommandInfo:
                                if time.time() > received_time + CommandInfo['WaitTimeout']:
                                    # timeout
                                    # unassign for stage
                                    '''E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleUnassigned,{
                                                'VehicleID':self.id,
                                                'CommandIDList':[CommandInfo['StageID']],
                                                'CommandID':CommandInfo['StageID'],
                                                'BatteryValue':self.adapter.battery['percentage']})'''
                                    # remove stage and links?
                                    self.abort_tr_cmds_and_actions(CommandInfo['CommandID'], 0, 'Stage command timeout', cause='by stage')
                                    # self.AgvLastState=self.AgvState
                                    # self.AgvState='Parked'
                                    print('Timeout expired for {}'.format(CommandInfo['CommandID']))
                            else:
                                # error
                                # unassign for stage
                                '''E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleUnassigned,{
                                            'VehicleID':self.id,
                                            'CommandIDList':[CommandInfo['StageID']],
                                            'CommandID':CommandInfo['StageID'],
                                            'BatteryValue':self.adapter.battery['percentage']})'''
                                # remove stage and links?
                                self.abort_tr_cmds_and_actions(CommandInfo['CommandID'], 0, 'Stage command timeout', cause='by stage')
                                # self.AgvLastState=self.AgvState
                                # self.AgvState='Parked'
                                print('Stage error for {}'.format(CommandInfo['CommandID']))
                        elif self.action_in_run.get('type', '') == 'HostMove':
                            if time.time()-self.enter_host_call_waiting_time < self.host_call_waiting_time:
                                num, buf_list=self.buf_available()
                                for queueID, zone_wq in TransferWaitQueue.getAllInstance().items(): #7. check if carrierID duplicator in waiting queue
                                    if queueID in self.serviceZone[0] or self.id == queueID:
                                        if zone_wq.wq_lock.acquire(False):
                                            try:
                                                for idx, host_tr_cmd in enumerate(zone_wq.queue):
                                                    res, primary_cmd_count, single_cmd_count, buf_reserved, buf_assigned, unload_buf_assigned=tools.buf_allocate_test(self, host_tr_cmd, buf_list, False, 'by_lowest_cost')
                                                    if res and host_tr_cmd['source'] ==self.host_call_target:
                                                        if global_variables.TSCSettings.get('Other', {}).get('PreDispatch','') == 'yes' and not host_tr_cmd.get('preTransfer') and (host_tr_cmd.get('sourceType', '') in ['StockOut', 'ErackOut', 'StockIn&StockOut', 'LifterPort']):
                                                            if zone_wq.dispatch_transfer(self):
                                                                self.AgvState='Parked'
                                                                self.host_call_target=''
                                                                self.host_call_waiting_time=0
                                                                dispatch_success=True
                                                                break
                                                        else:
                                                            bufID=buf_assigned.pop(-1) if buf_assigned else buf_list.pop(-1)
                                                            try_dispatch=True

                                                    elif host_tr_cmd['dest'] ==self.host_call_target and host_tr_cmd['source'][:-5] in self.h_vehicleMgr.vehicles:
                                                        r=re.match(r'(.+)(BUF\d+)', host_tr_cmd['source'])
                                                        if not r or r.group(2) == 'BUF00':
                                                            continue
                                                        bufID=r.group(2)
                                                        try_dispatch=True
                                                    
                                                    if try_dispatch:
                                                        zone_wq.remove_waiting_transfer_by_idx(host_tr_cmd, idx)
                                                        self.append_transfer(host_tr_cmd, bufID)
                                                        self.ControlPhase='GoTransfer'
                                                        self.CommandIDList.append(host_tr_cmd['uuid'])
                                                        E82.report_event(self.secsgem_e82_h,
                                                                            E82.VehicleAssigned,{
                                                                            'VehicleID':self.id,
                                                                            'CommandIDList':self.CommandIDList,
                                                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                            'BatteryValue':self.adapter.battery['percentage']})

                                                        output('VehicleAssigned',{
                                                                'Battery':self.adapter.battery['percentage'],
                                                                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                                'Connected':self.adapter.online['connected'],
                                                                'Health':self.adapter.battery['SOH'],
                                                                'MoveStatus':self.adapter.move['status'],
                                                                'RobotStatus':self.adapter.robot['status'],
                                                                'RobotAtHome':self.adapter.robot['at_home'],
                                                                'VehicleID':self.id,
                                                                'VehicleState':self.AgvState,
                                                                'Message':self.message,
                                                                'ForceCharge':self.force_charge, #???
                                                                'CommandIDList':self.CommandIDList})
                                                        self.AgvState='Parked'
                                                        self.host_call_target=''
                                                        self.host_call_waiting_time=0
                                                        dispatch_success=True
                                                        self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'Vehicle append transfer from waiting stste success'))
                                                        break
                                                zone_wq.wq_lock.release()
                                            except:
                                                zone_wq.wq_lock.release()
                                                self.adapter.logger.error('{} {} {}'.format('[{}] '.format(self.id), 'Vehicle append transfer from waiting stste fail', traceback.format_exc())) 
                                    if dispatch_success:
                                        break
                                if dispatch_success:
                                    continue  
                                # except:
                                #     self.adapter.logger.error('{} {} {}'.format('[{}] '.format(self.id), 'Vehicle append transfer from waiting stste fail', traceback.format_exc())) 
                            else:
                                self.AgvState='Parked'
                                self.host_call_target=''
                                self.host_call_waiting_time=0
                        else:
                            self.AgvState='Parked'
                            self.host_call_target=''
                            self.host_call_waiting_time=0

                    elif self.AgvState == 'Unassigned':
                        #print('Unassigned',len(self.tr_cmds))
                        self.message='None'
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        # do_faulty_cmd=False
                        #check recovery cmd
                        if self.recovery_cmd: #from UUI
                            self.recovery_cmd=False
                            if self.token.acquire(False): #blocking
                                try:
                                    if self.AgvSubState == 'InWaitCmdStatus':
                                        self.AgvSubState='InRecoveryCmdStatus'
                                        self.do_fault_recovery(force=True) #????
                                        self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                    
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()
                                    #add something more
                        if global_variables.RackNaming == 25:           
                            if self.buf_residual(): #from system Yuri 2024/10/11
                                self.AgvLastState=self.AgvState
                                self.AgvState='Parked'
                                self.ControlPhase='GoTransfer'
                                E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleAssigned,{
                                            'VehicleID':self.id,
                                            'CommandIDList':self.CommandIDList,
                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                            'BatteryValue':self.adapter.battery['percentage']})

                                output('VehicleAssigned',{
                                        'Battery':self.adapter.battery['percentage'],
                                        'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                        'Connected':self.adapter.online['connected'],
                                        'Health':self.adapter.battery['SOH'],
                                        'MoveStatus':self.adapter.move['status'],
                                        'RobotStatus':self.adapter.robot['status'],
                                        'RobotAtHome':self.adapter.robot['at_home'],
                                        'VehicleID':self.id,
                                        'VehicleState':self.AgvState,
                                        'Message':self.message,
                                        'ForceCharge':self.force_charge, #???
                                        'CommandIDList':self.CommandIDList})
                                continue

                        # if global_variables.TSCSettings.get('Recovery', {}).get('Auto') == 'yes' and self.buf_residual() and global_variables.TSCSettings.get('Recovery', {}).get('KeepCarrierOnTheVehicle')!='yes':
                        #     for idx in range(self.bufNum): #8.22-3
                        #         if self.bufs_status[idx]['do_auto_recovery'] == True:
                        #             self.do_fault_recovery(False,idx)
                        #             do_faulty_cmd=True
                        #             break

                        # if do_faulty_cmd: #8.22C-3
                        #     continue

                        #check transfer cmd
                        if self.waiting_run:
                            self.actions.clear()
                            fail_tr_cmds_id=''
                            actions=[]
                            #chocp 2022/8/30
                            try:
                                # if global_variables.RackNaming==36:#peter 24114
                                #     point_to_port=PortsTable.reverse_mapping[self.adapter.last_point]
                                #     if len(point_to_port):
                                #         point_to_port=point_to_port[0]
                                #         at_equipmentID=EqMgr.getInstance().workstations.get(point_to_port).equipmentID
                                #     for tr_cmd in self.tr_cmds:
                                #         s_equipmentID=EqMgr.getInstance().workstations.get(tr_cmd['source']).equipmentID
                                #         d_equipmentID=EqMgr.getInstance().workstations.get(tr_cmd['dest']).equipmentID
                                #         if at_equipmentID==s_equipmentID and at_equipmentID==d_equipmentID:
                                #             tr_cmd['continuous_action']=True
                                if self.use_schedule_algo == 'by_fix_order':
                                    fail_tr_cmds_id, actions=schedule_by_fix_order.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)
                                elif self.use_schedule_algo == 'by_priority':
                                    fail_tr_cmds_id, actions=schedule_by_priority.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)
                                elif self.use_schedule_algo == 'by_mix_lowest_cost_priority':
                                    fail_tr_cmds_id, actions=schedule_by_mix_lowest_cost_priority.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)
                                elif self.bufNum<=8 and self.use_schedule_algo == 'by_lowest_cost': #chocp 2024/8/21 for shift
                                    fail_tr_cmds_id, actions=schedule_by_lowest_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point, self.model)
                                elif self.bufNum>=12:
                                    self.adapter.logger.info("self.tr_cmds:{}".format(self.tr_cmds))
                                    fail_tr_cmds_id, actions=schedule_by_point_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)
                                    #fail_tr_cmds_id, actions=schedule_by_better_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point, self.model)
                                else:
                                    fail_tr_cmds_id, actions=schedule_by_better_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point, self.model)
                                # if global_variables.RackNaming==36:
                                #     try:
                                #         if at_equipmentID:
                                #             actions_at_station_acquire=[]
                                #             actions_high_priority=[]
                                #             actions_other=[]
                                #             actions_continuous=[]
                                #             self.adapter.logger.info("before sort:{}".format(at_equipmentID))
                                #             for action in actions:
                                #                 self.adapter.logger.info(action)
                                #                 if action['local_tr_cmd'].get('continuous_action'):
                                #                     actions_continuous.append(action)
                                #                 elif action['type']=="ACQUIRE" and action["local_tr_cmd"]["host_tr_cmd"]["equipmentID"]==at_equipmentID:
                                #                     actions_at_station_acquire.append(action)
                                #                 elif action["local_tr_cmd"]["priority"]>0:
                                #                     actions_high_priority.append(action)
                                #                 else:
                                #                     actions_other.append(action)
                                #             actions=[]
                                #             if len(actions_continuous):
                                #                 actions.extend(actions_continuous)
                                #             if len(actions_at_station_acquire):
                                #                 actions.extend(actions_at_station_acquire)
                                #             if len(actions_high_priority):
                                #                 actions.extend(actions_high_priority)
                                #             if len(actions_other):
                                #                 actions.extend(actions_other)
                                #             self.adapter.logger.info("after sort")
                                #             for action in actions:
                                #                 self.adapter.logger.info(action)
                                #     except:pass
                            except:
                                self.adapter.logger.error('{} {} {}'.format('[{}] '.format(self.id), 'Vehicle task_generate fail: ', traceback.format_exc()))
                                for local_command in self.tr_cmds:
                                    local_command_id=local_command.get('uuid','')
                                    alarms.TscActionGenWarning(self.id, local_command_id, handler=self.secsgem_e82_h)
                                    self.abort_tr_cmds_and_actions(local_command_id, 10002, 'TSC generate action fail or no buffer left', cause='by alarm') #del all relative command
                                self.waiting_run= False
                                self.AgvSubState='InWaitCmdStatus'
                            
                            #print(fail_tr_cmds_id)
                            for local_command_id in fail_tr_cmds_id:
                                alarms.TscActionGenWarning(self.id, local_command_id, handler=self.secsgem_e82_h)
                                self.abort_tr_cmds_and_actions(local_command_id, 10002, 'TSC generate action fail or no buffer left', cause='by alarm') #del all relative command

                            if actions:
                                self.actions.extend(actions) #self.actions is dequeue
                            
                            #vehicle assigned
                            if len(self.actions):
                                self.CommandIDList=[] #from unassigned
                                self.NewEQ=""
                                for local_tr_cmd in self.tr_cmds:
                                    if local_tr_cmd['host_tr_cmd']['uuid'] not in self.CommandIDList:#fix 5
                                        self.CommandIDList.append(local_tr_cmd['host_tr_cmd']['uuid']) #release commandID
                                        if global_variables.RackNaming == 43:  # Mirle can't accept CommandIDList need one cmd one VehicleAssigned
                                            E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleAssigned,{
                                            'VehicleID':self.id,
                                            'CommandID':local_tr_cmd['host_tr_cmd']['uuid']})
                                            
                                if global_variables.RackNaming != 43: 
                                    E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleAssigned,{
                                                'VehicleID':self.id,
                                                'CommandIDList':self.CommandIDList,
                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                'BatteryValue':self.adapter.battery['percentage']})

                                output('VehicleAssigned',{
                                        'Battery':self.adapter.battery['percentage'],
                                        'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                        'Connected':self.adapter.online['connected'],
                                        'Health':self.adapter.battery['SOH'],
                                        'MoveStatus':self.adapter.move['status'],
                                        'RobotStatus':self.adapter.robot['status'],
                                        'RobotAtHome':self.adapter.robot['at_home'],
                                        'VehicleID':self.id,
                                        'VehicleState':self.AgvState,
                                        'Message':self.message,
                                        'ForceCharge':self.force_charge, #???
                                        'CommandIDList':self.CommandIDList}, True)

                                stk_collection=[] # Mike: 2024/03/08
                                for action in self.actions:
                                    h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                                    if h_workstation and h_workstation.workstation_type in ['StockIn', 'StockIn&StockOut', 'LifterPort'] and action['type'] == 'DEPOSIT':
                                        stk_collection.append(action['local_tr_cmd']['host_tr_cmd']['uuid'])
                                if global_variables.RackNaming == 27 and stk_collection:
                                    E82.report_event(self.secsgem_e82_h,
                                                    E82.LoadBackOrder, {
                                                    'CommandIDList':stk_collection })

                                #print('VehicleAssigned', self.CommandIDList)
                                self.tr_cmd_assign_timeout=time.time() #chocp 8/21
                                self.action_in_run=self.actions[0] #fix 8/20
                                self.execute_action(force_route=True) #fix 8/20

                            self.waiting_run=False
                            continue

                        elif self.host_call_cmd:
                            self.host_call_move_cmd()
                            continue

                        #check charge cmd, 8.21H-6
                        check=False
                        if self.charge_cmd:
                            self.force_charge=True
                            check=True
    

                        elif self.adapter.battery['percentage'] < self.ChargeBelowPower:
                            self.force_charge=True
                            check=True
                            
                        elif self.EnableScheduleCharging == "yes" and tools.Timed_charging(self.ScheduleChargingTime):#zsg 2024/6/27
                            if self.adapter.battery['percentage'] < self.RunAfterMinimumPower:
                                self.force_charge=True
                                check=True

                        elif not self.adapter.relay_on:
                            if global_variables.RackNaming != 36:
                                if self.ChargeWhenIdle == 'yes' and self.adapter.battery['percentage'] <= self.BatteryHighLevel:
                                    if self.enter_unassigned_state_time and\
                                        (time.time()-self.enter_unassigned_state_time) > self.IntoIdleTime:
                                            check=True
                            else:
                                if not self.go_to_vcs:
                                    if self.ChargeWhenIdle == 'yes' and self.adapter.battery['percentage'] <= self.BatteryHighLevel:
                                        if self.enter_unassigned_state_time and\
                                            (time.time()-self.enter_unassigned_state_time) > self.IntoIdleTime:
                                                check=True

                        elif self.adapter.relay_on: # Mike: 2023/11/29
                            if not self.adapter.battery['charge']:
                                self.adapter.relay_on=False
                            elif self.adapter.battery['percentage'] > self.BatteryHighLevel: #8.28.7
                                self.adapter.charge_end()

                        if self.force_charge and global_variables.RackNaming == 30: #8.28.29
                            res,h_vehicle=tools.find_other_charge_vehicle_for_BOE(self)
                            if res and self.adapter.battery['percentage']>20:
                                self.force_charge=False
                                check=False
                            elif res and h_vehicle and self.adapter.battery['percentage']<20:
                                h_vehicle.force_charge=False

                        
                                




                        #if self.force_charge or (check and not self.doPreDispatchCmd):#8.21N-4
                        if check and not self.doPreDispatchCmd and not self.tsc_paused:
                            is_abcs, chargeStation=self.find_charge_station()
                            if self.token.acquire(False):
                                try:
                                    if self.AgvSubState == 'InWaitCmdStatus':
                                        if not chargeStation and not self.findchargestation: #chi 2022/11/18
                                            self.findchargestation=True
                                            alarms.BaseTryChargeFailWarning(self.id, 'C00000000', self.adapter.last_point, 'None', handler=self.secsgem_e82_h)
                                        elif chargeStation:
                                            self.findchargestation=False
                                            if is_abcs:
                                                self.AgvSubState='InWaitExchangeStatus'
                                                print('go_exchange', self.adapter.relay_on)
                                                self.exec_exchange_cmd(chargeStation, from_unassigned=True)
                                            else:
                                                self.AgvSubState='InWaitChargeStatus'
                                                print('go_charge', self.adapter.relay_on)
                                                self.exec_charge_cmd(chargeStation, from_unassigned=True)
                                        self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()

                        #check park cmd
                        go_park=False
                        tmpPark=False
                        force_go_park=False
                        wait_vehicle='' # Mike: 2021/11/12
                        for vehicle_id, h_vehicle in self.h_vehicleMgr.vehicles.items(): #chocp fix, 2021/10/14
                            if h_vehicle.id!=self.id:
                                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                                    self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id))
                                    go_park=True
                                    tmpPark=True
                                    force_go_park=True
                                    wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                                    break
                        else: 
                            station_list=[]
                            for station in self.standby_station:
                                to_point=tools.find_point(station)
                                if not PoseTable.mapping[to_point]['park']:
                                    station_list.append(station)

                            if not self.adapter.relay_on and (self.at_station not in station_list) and self.ParkWhenStandby == 'yes':
                                if self.enter_unassigned_state_time and\
                                    (time.time()-self.enter_unassigned_state_time) > self.IntoStandbyTime:
                                    go_park=True

                        if (force_go_park and self.standby_station) or (go_park and self.standby_station and not self.doPreDispatchCmd and not self.tsc_paused):
                            if self.token.acquire(False):
                                try:
                                    if self.AgvSubState == 'InWaitCmdStatus':
                                        self.AgvSubState='InStandbyCmdStatus'
                                        print('go_park', self.adapter.relay_on, self.standby_station)
                                        self.return_standby_cmd(wait_vehicle, tmpPark, from_unassigned=True )
                                        self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()

                        if self.doPreDispatchCmd:
                            self.force_charge=False
                            vehicle_wq=TransferWaitQueue.getInstance(self.id)
                            if not len(vehicle_wq.queue):
                                if time.time() - self.enter_unassigned_state_time > vehicle_wq.collect_timeout:
                                    self.doPreDispatchCmd=False
                                    print('Release doPreDispatchCmd flag')

                    #Parked
                    elif self.AgvState == 'Parked':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue

                        self.tr_back_req=False
                        self.tr_back_timeout=False
                        # do_faulty_cmd=False
                        
                        '''if self.host_call_waiting_time and self.host_call_target == self.at_station:
                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Waiting'
                            self.enter_host_call_waiting_time=time.time()
                            continue'''

                        if global_variables.RackNaming == 18 and (self.input_cmd_open or self.input_cmd_open_again): #for K25, only single cmd    
                            self.adapter.logger.info("~~~agv_id~~~:{}".format(self.id))
                            self.adapter.logger.info("self.input_cmd_open:{}".format(self.input_cmd_open))
                            self.adapter.logger.info("self.input_cmd_open_again:{}".format(self.input_cmd_open_again))
                            self.adapter.logger.info("self.at_station:{}".format(self.at_station))

                            h_workstation=EqMgr.getInstance().workstations.get(self.at_station) 
                            if h_workstation:
                                self.adapter.logger.info("H_workstation_type:{}".format(h_workstation.workstation_type))
                                stocker_queue_h=TransferWaitQueue.getInstance(h_workstation.equipmentID)#for K25
                                #print(1, stocker_queue_h.queueID, len(stocker_queue_h.queue))
                                if len(stocker_queue_h.queue):
                                    stocker_queue_h.wq_lock.acquire()
                                    try:
                                        num, buf_list=self.buf_available()

                                        input_action_inserted=False #for K25
                                        action_inserted=False
                                        self.adapter.logger.debug("input_action_inserted:{}".format(input_action_inserted))
                                        self.adapter.logger.debug("action_inserted:{}".format(action_inserted))
                                        
                                        self.adapter.logger.debug("num:{}".format(num))
                                        self.adapter.logger.debug("buf_list:{}".format(buf_list))

                                        idx=0
                                        while num and len(stocker_queue_h.queue[idx:]): #fix 2023/6/30
                                            host_tr_cmd=stocker_queue_h.queue[idx]
                                            source_port=host_tr_cmd['source']
                                            self.adapter.logger.debug("source_port:{}".format(source_port))
                                            self.adapter.logger.debug("self.at_station:{}".format(self.at_station))
                                            #print(2, host_tr_cmd['uuid'], source_port)
                                            h_workstation=EqMgr.getInstance().workstations.get(source_port) 
                                            if h_workstation:
                                                if 'Stock' in h_workstation.workstation_type and tools.find_point(source_port) == tools.find_point(self.at_station):
                                                    for bufID in buf_list:
                                                        if host_tr_cmd.get('BufConstrain'):
                                                            if bufID not in self.vehicle_onTopBufs:
                                                                if not input_action_inserted and self.input_cmd_open:
                                                                    input_action_inserted=True
                                                                    self.actions.append(tools.input_action_gen(self.at_station))

                                                                stocker_queue_h.remove_waiting_transfer_by_idx(host_tr_cmd, idx)        
                                                                self.append_transfer(host_tr_cmd, bufID, byTheWay=False)
                                                                action_inserted=True
                                                                buf_list.remove(bufID)
                                                                break
                                                        else:
                                                            #print(3, input_action_inserted)
                                                            if not input_action_inserted and self.input_cmd_open:
                                                                input_action_inserted=True
                                                                self.adapter.logger.info("input_action_inserted:{}".format(input_action_inserted))
                                                                self.actions.append(tools.input_action_gen(self.at_station))
                                                                
                                                            stocker_queue_h.remove_waiting_transfer_by_idx(host_tr_cmd, idx)
                                                            self.append_transfer(host_tr_cmd, bufID, byTheWay=False)
                                                            action_inserted=True
                                                            self.adapter.logger.info("action_inserted:{}".format(action_inserted))
                                                            buf_list.remove(bufID)
                                                            #if host_tr_cmd.get("CommandInfo").get("CommandID") !="":
                                                            if host_tr_cmd.get("uuid"):
                                                                #self.CommandIDList=[host_tr_cmd.get("CommandInfo").get("CommandID")]
                                                                self.CommandIDList.append(host_tr_cmd['uuid'])

                                                                E82.report_event(self.secsgem_e82_h,
                                                                                E82.VehicleAssigned,{
                                                                                'VehicleID':self.id,
                                                                                'CommandIDList':self.CommandIDList,
                                                                                'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                                                                'BatteryValue':self.adapter.battery['percentage']})

                                                                output('VehicleAssigned',{
                                                                        'Battery':self.adapter.battery['percentage'],
                                                                        'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                                                        'Connected':self.adapter.online['connected'],
                                                                        'Health':self.adapter.battery['SOH'],
                                                                        'MoveStatus':self.adapter.move['status'],
                                                                        'RobotStatus':self.adapter.robot['status'],
                                                                        'RobotAtHome':self.adapter.robot['at_home'],
                                                                        'VehicleID':self.id,
                                                                        'VehicleState':self.AgvState,
                                                                        'Message':self.message,
                                                                        'ForceCharge':self.force_charge, #???
                                                                        'CommandIDList':self.CommandIDList}, True)
                                                            self.adapter.logger.debug("in break1")
                                                            break
                                                    else:#no avaiable buf
                                                        self.adapter.logger.debug("in break2")
                                                        break
                                                else: #test next host_tr_cmd  
                                                    self.adapter.logger.debug("in plus idx1")
                                                    idx+=1 
                                            else:  #test next host_tr_cmd
                                                self.adapter.logger.debug("in plus idx2")   
                                                idx+=1

                                        if self.input_cmd_open_again and action_inserted: #8.24F chocp
                                            try:
                                                tools.reschedule_to_eq_actions(self.actions, self.adapter.last_point, self.at_station, self.adapter.logger) #for K25
                                            except:
                                                traceback.print_exc()
                                                pass

                                        stocker_queue_h.wq_lock.release()
                                    except:
                                        stocker_queue_h.wq_lock.release()
                                        msg=traceback.format_exc()
                                        self.adapter.logger.info('Handling queue:{} in fetch input cmd with a exception:\n {}'.format(stocker_queue_h.queueID, msg))
                                        pass

                            

                            self.input_cmd_open=False
                            self.input_cmd_open_again=False
                            self.adapter.logger.debug("last self.input_cmd_open:{}".format(self.input_cmd_open))
                            self.adapter.logger.debug("last self.input_cmd_open_again:{}".format(self.input_cmd_open_again))


                        elif len(self.actions):
                            go_park=False
                            tmpPark=True
                            try:
                                to_point=tools.find_point(self.actions[0]['target'])
                                last_point = self.adapter.last_point
                                last_point_pose = tools.get_pose(last_point)
                                last_point_priority = int(last_point_pose.get('point_priority', 0))
                                to_point_pose = tools.get_pose(to_point)
                                to_point_group = to_point_pose.get('group', '')
                                to_point_groups = [g for g in to_point_group.split('|') if g]
                                to_group_set = set(to_point_groups)
                                if to_point != self.adapter.last_point:
                                    #check park cmd
                                    wait_vehicle='' # Mike: 2021/11/12
                                    for vehicle_id, h_vehicle in self.h_vehicleMgr.vehicles.items(): #chocp fix, 2021/10/14
                                        if h_vehicle.actions:
                                            h_to_point = tools.find_point(h_vehicle.actions[0]['target'])
                                            h_to_point_pose = tools.get_pose(h_to_point)
                                            h_to_point_group = h_to_point_pose.get('group', '')
                                            h_to_point_groups = [g for g in h_to_point_group.split('|') if g]
                                            if h_vehicle.id!=self.id:
                                                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                                                    if to_group_set.isdisjoint(h_to_point_groups):
                                                        if global_variables.global_vehicles_priority.get(h_vehicle.id, 0) > self.priority + last_point_priority:
                                                            self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id))
                                                            go_park=True
                                                            wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                                                            break
                            except:
                                traceback.print_exc()
                                pass
                            if go_park:
                                print('>>> go_avoid', self.adapter.relay_on, self.standby_station)
                                self.return_standby_cmd(wait_vehicle, tmpPark, from_unassigned=False)
                                continue
                            if global_variables.RackNaming in [33, 58]:
                                self.append_transfer_allowed_for_Renesas(self.actions)
                            elif global_variables.RackNaming in [36]:
                                self.append_transfer_allowed_for_ASE_K11(self.actions)
                            elif global_variables.RackNaming in [46]:
                                self.append_transfer_allowed_for_TI_Baguio(self.actions)
                            else:
                                self.append_transfer_allowed(self.actions)

                            self.action_in_run=self.actions[0]

                            if self.action_in_run['type'] == 'NULL': #preDispatch, preTransfer
                                local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                                uuid=local_tr_cmd.get('uuid', '')
                                carrierID=local_tr_cmd['carrierID']

                                target=self.action_in_run.get('target', '')
                                #to_point=tools.find_point(target)

                                self.actions.popleft()

                                vehicle_wq=TransferWaitQueue.getInstance(self.id)
                                vehicle_wq.last_add_time=time.time()

                                local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']}) #8.25.10-1
                                local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['OriginalTransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']}) #8.25.10-1
                                E82.report_event(self.secsgem_e82_h,
                                                E82.TransferCompleted,{
                                                'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                                'VehicleID':self.id,
                                                'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                                'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                                'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                                'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                                'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                                'CarrierID':carrierID, #chocp fix for tfme 2021/10/23

                                                'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                                'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                                #'CarrierLoc':self.action_in_run['loc'],
                                                'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                                'ResultCode':0})

                                output('TransferCompleted', {
                                        'VehicleID':self.id,
                                        'DestType':local_tr_cmd.get('dest_type', 'other'),
                                        'Travel':local_tr_cmd.get('travel', 0),
                                        'CommandID':uuid,
                                        'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                                        'ResultCode':0,
                                        'Message':'' }, True)

                                #tools.reset_book_slot(local_tr_cmd.get('dest')) #not correct for re-deposit

                                # for buf in self.bufs_status: #remove command note, for auto recovery!
                                for idx, buf in enumerate(self.bufs_status): #remove command note, for auto recovery!
                                    if buf['local_tr_cmd'] == local_tr_cmd:
                                        print('remove ...................')
                                        if buf['stockID'] not in ['Unknown', '']:
                                            self.adapter.cmd_control(1, local_tr_cmd['host_tr_cmd']['uuid'], local_tr_cmd['host_tr_cmd'].get('original_source',''), local_tr_cmd['host_tr_cmd'].get('dest',''), idx+1, buf['stockID'], lotID='')
                                        buf['local_tr_cmd']={} #chocp

                                if local_tr_cmd in self.tr_cmds:
                                    self.tr_cmds.remove(local_tr_cmd) #only output for host transfer cmds, if R cmd will have exception

                                output('TransferExecuteQueueRemove', {'CommandID':uuid}, True)
                                print('<<Null action, TransferExecuteQueueRemove>>', {'CommandID':uuid})
                                self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''))
                            else:
                                self.execute_action()

                            continue #double check
                        else:
                            if self.ControlPhase == 'GoTransfer' and not self.doPreDispatchCmd: #chocp for StockOut ????
                                print('To GoRecovery:')
                                if global_variables.TSCSettings.get('Recovery', {}).get('Auto') == 'yes' and self.buf_residual():
                                    if global_variables.TSCSettings.get('Recovery', {}).get('KeepCarrierOnTheVehicle') == 'yes': #chi 2022/11/8 for keep carrier on vehicle when auto recovery
                                        self.ControlPhase='GoRecovery'
                                    else:
                                        self.do_fault_recovery()
                                else:
                                    self.ControlPhase='GoRecovery'

                            # if do_faulty_cmd: #8.22C-3
                            #     continue

                            elif self.ControlPhase == 'GoRecovery' and not self.doPreDispatchCmd: #chocp for StockOut:

                                self.ControlPhase='GoUnassigned'

                                check=False
                                if self.adapter.battery['percentage'] < self.ChargeBelowPower:
                                    self.force_charge=True
                                    check=True

                                if self.force_charge and global_variables.RackNaming == 30: #8.28.29
                                    res,h_vehicle=tools.find_other_charge_vehicle_for_BOE(self)
                                    if res and self.adapter.battery['percentage']>20:
                                        self.force_charge=False
                                        check=False
                                    elif res and h_vehicle and self.adapter.battery['percentage']<20:
                                        h_vehicle.force_charge=False

                                if check or self.EveryRound == 'yes' and not self.tsc_paused:
                                    is_abcs, chargeStation=self.find_charge_station()
                                    if not chargeStation and not self.findchargestation: #chi 2022/11/18
                                        self.findchargestation=True
                                        alarms.BaseTryChargeFailWarning(self.id, 'C00000000', self.adapter.last_point, 'None', handler=self.secsgem_e82_h)
                                    elif chargeStation:
                                        self.findchargestation=False
                                        if is_abcs and check:
                                            self.ControlPhase='GoExchange'
                                            print('To GoExchange')
                                            self.exec_exchange_cmd(chargeStation, from_unassigned=True)
                                        else:
                                            self.ControlPhase='GoCharge'
                                            print('To GoCharge')
                                            self.exec_charge_cmd(chargeStation, from_unassigned=True)

                            else:
                                self.ControlPhase='GoUnassigned'

                                time.sleep(1) #???
                                print('To GoUnassigned:')

                                if global_variables.RackNaming == 36:

                                    if "VCS" in self.action_in_run.get('target', ''):
                                        self.adapter.logger.info("vcs in:{}".format(self.action_in_run.get('target', '')))
                                        self.go_to_vcs=True
                                    else:
                                        self.go_to_vcs=False

                                self.message='MR_Spec_Ver: <%s>,  MR_Soft_Ver: <%s>'%(self.adapter.mr_spec_ver, self.adapter.mr_soft_ver)
                                output('VehicleUnassigned',{
                                        'Battery':self.adapter.battery['percentage'],
                                        'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                        'Connected':self.adapter.online['connected'],
                                        'Health':self.adapter.battery['SOH'],
                                        'MoveStatus':self.adapter.move['status'],
                                        'RobotStatus':self.adapter.robot['status'],
                                        'RobotAtHome':self.adapter.robot['at_home'],
                                        'VehicleID':self.id,
                                        'VehicleState':'Unassigned',
                                        'TransferTask':{'VehicleID':self.id, 'Action':'', 'CommandID':'', 'CarrierID':'', 'Dest':'', 'ToPoint':''},
                                        'Message':self.message,
                                        'ForceCharge':self.force_charge,
                                        'CommandIDList':self.CommandIDList}) #may be include fail cmd

                                E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleUnassigned,{
                                            'VehicleID':self.id,
                                            'CommandIDList':self.CommandIDList,
                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else '',
                                            'BatteryValue':self.adapter.battery['percentage']})
                                if global_variables.TSCSettings.get('Other', {}).get('ImmediatelyAssignedReq','no') == 'yes':
                                    if self.doPreDispatchCmd:
                                        self.assignable=False
                                        print('VehicleAssignReq')
                                        E82.report_event(self.secsgem_e82_h,
                                                    E82.VehicleAssignReq,{
                                                    'VehicleID':self.id,
                                                    'TransferPort':self.action_in_run.get('target', '',),
                                                    'BatteryValue':self.adapter.battery['percentage']})

                                self.adapter.current_cmd_control(1, self.action_in_run.get('uuid', ''), '', '', '')

                                print('Unassigned', self.doPreDispatchCmd, self.CommandIDList)
                                self.CommandIDList=[]
                                self.action_in_run={}
                                #self.tr_cmds=[] #double check # bug check??????
                                self.tr_cmd_assign_timeout=0 #chocp 8/21

                                self.actions.clear() #double check

                                self.AgvLastState=self.AgvState  #fix 8/20
                                self.AgvState='Unassigned'
                                if self.wq:
                                    if self.id in self.wq.dispatchedMRList:
                                        self.wq.dispatchedMRList.remove(self.id)
                                    print('MR dispatchedMRList',self.wq.dispatchedMRList)
                                self.wq=None #8.21H-4
                                self.last_action_is_for_workstation=False #8.21H-4
                                self.AgvSubState='InWaitCmdStatus'
                                self.error_skip_tr_req=False
                                
                                if global_variables.RackNaming == 42:
                                    for i in range(self.bufNum):
                                        if self.bufs_status[i]['stockID'] =='None' and self.enableBuffer[i] == 'yes':
                                            self.update_dynamic_buffer_mapping(i,'Empty')

                    elif self.AgvState == 'Enroute':
                        #if self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.current_route and not self.adapter.is_moving): #????  need cancel it
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '')

                        if self.change_target:
                            print('change target')
                            self.change_target=False
                            self.adapter.planner.clean_route()
                            self.wait_stop=True
                            # self.execute_action()
                            ###### execute new action
                            continue

                        if self.wait_stop and not self.adapter.planner.occupied_route:
                            print('reroute')
                            self.wait_stop=False
                            self.execute_action()
                            continue

                        if (self.stop_command and not self.adapter.cmd_sending) or (self.emergency_evacuation_cmd and not self.emergency_evacuation_stop and self.AgvLastState !='Evacuation'): #8.21N-6:
                            self.logger.debug('why alaso me6')
                            if not self.adapter.vehicle_stop(): #blocking
                                continue
                            
                            #self.stop_command=False
                            self.no_begin=True
                            
                            if self.emergency_evacuation_cmd:
                                self.emergency_evacuation_stop=True
                                self.AgvState='Parked'
                                continue
                            else:
                                raise alarms.BaseReplaceJobWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #20211001 chocp fix

                        #if self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.current_route and not self.adapter.is_moving): #????  need cancel it
                        if self.adapter.move['obstacles']: #chi 22/05/04 check obstacles when Enroute
                            now_time=time.time()
                            if now_time - self.adapter.move['into_obstacles'] > self.warningBlockTime and not self.adapter.cmd_sending: #3min
                                self.adapter.move['obstacles']=False
                                alarms.MoveRouteObstaclesWarning(self.id, uuid)

                                if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) == 18:
                                    command_id_list=[]
                                    TransferInfoList=[]
                                    for carr in self.bufs_status:
                                        if carr['stockID'] not in ['', 'None', 'Unknown', 'PositionError']:
                                            command_id_list.append(carr['local_tr_cmd'].get('uuid', ''))
                                            TransferInfoList.append({'CarrierID':carr['stockID'], 'SourcePort':carr['local_tr_cmd'].get('source', ''), 'DestPort':carr['local_tr_cmd'].get('dest', '')})

                                    ## get data
                                    E82.report_event(self.secsgem_e82_h,
                                                    E82.VehicleBlocking,{
                                                    'VehicleID':self.id,
                                                    'CommandIDList':command_id_list,
                                                    'TransferInfoList':TransferInfoList})

                                if self.autoReroute == 'yes': # Mike: 2022/08/20
                                    self.message='MR move with route obstacles and into reroute'
                                    self.reroute()
                        #point=self.adapter.move["at_point"]
                        point=self.adapter.reach_point     
                        if self.appendTransferAllowed == "yes" and self.appendTransferAlgo == 'appendTransferMoving' and tools.find_port(point) and (self.old_point != point) and self.enroute_append_transfer_allowed():#Yuri
                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'
                            continue

                        #dangeous, will have a bug
                        if (self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.planner.occupied_route and not self.adapter.planner.current_route and not self.adapter.planner.is_moving))\
                            and self.adapter.move['status'] == 'Idle': #chocp 8/30

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'
                            self.at_station=target
                            
                            self.alarm_edge=[]
                            self.alarm_node=[]

                            E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleArrived,{
                                                'VehicleID':self.id,
                                                'CommandID':uuid,
                                                'TransferPort':target,
                                                'ResultCode':0,
                                                'BatteryValue':self.adapter.battery['percentage']}) #chocp fix

                            output('VehicleArrived',{
                                        'Point':self.adapter.last_point,
                                        'Station':self.at_station,
                                        'Battery':self.adapter.battery['percentage'],
                                        'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                        'Connected':self.adapter.online['connected'],
                                        'Health':self.adapter.battery['SOH'],
                                        'MoveStatus':self.adapter.move['status'],
                                        'RobotStatus':self.adapter.robot['status'],
                                        'RobotAtHome':self.adapter.robot['at_home'],
                                        'VehicleID':self.id,
                                        'CommandID':uuid,
                                        'VehicleState':self.AgvState,
                                        'Message':self.message,
                                        'ForceCharge':self.force_charge,
                                        'TransferPort':target,
                                        'ResultCode':0}) #chocp fix
                            if self.emergency_evacuation_cmd and self.at_station in self.standby_station:
                                raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)
                            
                            if global_variables.RackNaming == 53: #Kumamoto TPB
                                result, rack_id, port_no=tools.rackport_format_parse(target)
                                h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
                                if result and carrierID:
                                    result=h_eRack.check_door_operation(h_eRack.OPEN_CMD) #check erack open status
                                    if not result:
                                        raise alarms.RackDepositCheckWarning(self.id, uuid, target, carrierID)
                                
                                h_eRack.check_door_operation()

                    elif self.AgvState == 'TrUnLoadReq':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        #need check position
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        carrierID=local_tr_cmd['carrierID'] #chocp 2022/4/14
                        
                        if self.tr_assert:
                            if self.tr_assert['Result'] == 'CANCEL' and self.tr_assert.get('CommandID','') == uuid:
                                self.AgvState='Parked'
                                continue
                            
                            elif self.tr_assert['Result'] == 'OK':
                                if global_variables.RackNaming == 43:
                                    if self.tr_assert['TransferPort'] == 'None' or self.tr_assert['SendBy'] == 'by web': #chocp add 2021/12/21
                                        self.enter_acquiring_state()
                                        continue
                                #ASECL OVEN Richard 250220
                                elif global_variables.RackNaming == 22:
                                    pose=tools.get_pose(self.adapter.last_point)
                                    print("pose: {}".format(pose))
                                    deviceID=pose["DeviceParam"]["DeviceID"]
                                    print("deviceID: {}".format(deviceID))
                                    h_OVEN = Iot.h.devices.get(deviceID, None)
                                    print("Iot.h.devices.keys: {}".format(Iot.h.devices.keys()))
                                    if h_OVEN:
                                        print("In h_OVEN")
                                        if h_OVEN.ULD_RequestTransport() and h_OVEN.ULD_ApproveTransport():
                                            print("in function")
                                            self.enter_acquiring_state()
                                            continue
                                        else:
                                            print("h_OVEN  ULD_RequestTransport ULD_ApproveTransport ")
                                else:
                                    if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'UnLoad') and\
                                    (self.tr_assert['TransferPort'] == target or self.tr_assert['SendBy'] == 'by web'): #chocp add 2021/12/21
                                        self.tr_assert_result=target
                                        self.enter_acquiring_state()
                                        continue
                            elif self.tr_assert['Result'] == 'NG': # richard 250428
                                if global_variables.RackNaming == 43:
                                    raise alarms.EqUnLoadCheckFailWarning(self.id, uuid, target) 
                                else:
                                    if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'UnLoad') and\
                                    (self.tr_assert['TransferPort'] == target): #for spil, no waiting
                                        raise alarms.EqUnLoadCheckFailWarning(self.id, uuid, target) #chocp fix 2022/4/14
                                        continue
                            elif global_variables.RackNaming in [1,21,22] and self.tr_assert['Result'] == 'FAIL'  and (self.tr_assert['TransferPort'] in [target,'None']):
                                if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'UnLoad') and\
                                (self.tr_assert['TransferPort'] == target): #for spil, no waiting
                                    raise alarms.EqUnLoadCheckFailWarning(self.id, uuid, target) #chocp fix 2022/4/14
                                    continue

                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        if global_variables.RackNaming == 42:
                            EventInterval=30
                        elif global_variables.RackNaming == 36:
                            h_workstation=EqMgr.getInstance().workstations.get(target)
                            if h_workstation:
                                if "LONG" in h_workstation.equipmentID:
                                    EventInterval=60
                                else:
                                    EventInterval=10
                            else:
                                EventInterval=10
                        else:
                            EventInterval=10
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrUnLoadReqTimeout', 0)

                        if self.TrUnLoadReqTime and (time.time()-self.TrUnLoadReqTime > pending_timeout):
                            raise alarms.EqCheckTimeoutWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

                        elif self.ValidInputLastReqTime and (time.time()-self.ValidInputLastReqTime > EventInterval):

                            h_workstation=EqMgr.getInstance().workstations.get(target)
                            if getattr(h_workstation, 'open_door_assist', False):
                                E82.report_event(self.secsgem_e82_h,
                                            E82.TrUnLoadWithGateReq, {
                                            'VehicleID':self.id,
                                            #'TransferPort':self.at_station, #fix bug 2022/10/11
                                            'TransferPort':target,
                                            'CarrierID':carrierID})

                            else:
                                if global_variables.RackNaming == 20 and 'Stock' in h_workstation.workstation_type: #chocp 2024/03/29
                                    if h_workstation.state == 'Loaded':
                                        self.tr_assert={'Request':'UnLoad', 'Result':'OK', 'TransferPort':target, 'CarrierID':carrierID,'SendBy':'by host'}  
                                else:
                                    E82.report_event(self.secsgem_e82_h,
                                                E82.TrUnLoadReq, {
                                                'VehicleID':self.id,
                                                #'TransferPort':self.at_station, #fix bug 2022/10/11
                                                'TransferPort':target,
                                                'CarrierID':carrierID,
                                                'CommandID':uuid,
                                                'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                            output('TrUnLoadReq',{
                                    'VehicleID':self.id,
                                    'VehicleState':self.AgvState,
                                    'Station':self.at_station,
                                    'TransferPort':target,
                                    'CarrierID':carrierID})

                            self.ValidInputLastReqTime=time.time()

                    elif self.AgvState == 'Acquiring':
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27

                        if self.adapter.robot['finished'] == 'InterlockError':
                            if global_variables.RackNaming == 8:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Serious', handler=self.secsgem_e82_h)
                            elif global_variables.RackNaming == 43:
                                raise alarms.BaseSourceInterlockWarning(self.id, uuid, target, handler=self.secsgem_e82_h)
                            else:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Error', handler=self.secsgem_e82_h)

                        elif self.enter_acquiring_state_time and time.time()-self.enter_acquiring_state_time>self.robot_timeout: #timeout 200sec
                            raise alarms.RobotTimeoutCheckWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #20211001 chocp fix

                        elif self.adapter.robot['finished'] == 'Finished' and self.adapter.robot['status'] == 'Idle':
                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass

                            res, rack_id, port_no=tools.rackport_format_parse(target)
                            if res: #8.22H-1 for turntable
                                h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
                                if h_eRack and h_eRack.zonetype ==3:
                                    h_eRack.carriers[port_no-1]['direction_target']='F'
                            #   ASECL Richard 250220 after robot aquiring 
                            if global_variables.RackNaming == 22:
                                pose=tools.get_pose(self.adapter.last_point)
                                # deviceID=pose["DeviceParam"]["DeviceID"]
                                deviceID = pose.get('DeviceParam', {}).get('DeviceID')
                                if deviceID is not None:
                                    h_OVEN = Iot.h.devices.get(deviceID, None)
                                    if h_OVEN:
                                        if h_OVEN.ULD_CheckPresence() and h_OVEN.ULD_VerifyDevicePins():
                                            pass
                                        else:
                                            continue
                            # before status output

                            self.AgvLastState=self.AgvState
                            
                            if self.wait_eq_operation == True:
                                self.enter_wait_eq_operation_time=time.time()
                                self.AgvState='Suspend'
                            else:
                                self.AgvState='Parked'
                            self.tr_assert_result=''
                            #8.22G-1 chocp rewrite for jcet CIS PreBindCheck...
                            carrierID_from_cmd=local_tr_cmd['carrierID']
                            carrierID_from_rfid=self.re_assign_carrierID(self.action_in_run['loc']) if global_variables.RackNaming != 43 else self.re_assign_carrierID(self.action_in_run['loc'],wrong_id_allow=True)

                            if carrierID_from_cmd == '' or carrierID_from_cmd == 'None': #chocp fix for tfme 2021/10/23
                                local_tr_cmd['carrierID']=carrierID_from_rfid
                                local_tr_cmd['TransferInfo']['CarrierID']=carrierID_from_rfid
                                if carrierID_from_rfid not in ['None', 'ReadFail', 'Unknown']:
                                    carrierID_from_cmd=carrierID_from_rfid
                                    local_tr_cmd['carrierID']=carrierID_from_rfid

                            '''buf_idx=self.vehicle_bufID.index(self.action_in_run['loc'])
                            # print(global_variables.TSCSettings.get('Safety',{}), self.vehicle_bufID.index(self.action_in_run['loc']), self.bufs_status[buf_idx]['stockID'])
                            if global_variables.TSCSettings.get('Safety',{}).get('RenameFailedID', 'no') == 'yes'\
                                    and self.bufs_status[buf_idx]['stockID'] == 'ReadFail':
                                self.adapter.rfid_control(buf_idx+1, local_tr_cmd['carrierID'])
                                for i in range(30):
                                    self.AgvErrorCheck(self.AgvState)
                                    if self.bufs_status[buf_idx]['stockID'] != 'ReadFail':
                                        break
                                    time.sleep(0.1)
                                carrierID_from_rfid=self.re_assign_carrierID(self.action_in_run['loc'])'''
                            self.go_to_vcs=False
                            E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleAcquireCompleted, {
                                                'VehicleID':self.id,
                                                'CarrierLoc':self.id+self.action_in_run['loc'],
                                                'CommandID':uuid, #chocp add 10/30
                                                'TransferPort':target,
                                                'CarrierID':carrierID_from_cmd, #chocp fix for tfme 2021/10/23
                                                'ResultCode':0,
                                                'BatteryValue':self.adapter.battery['percentage']}) #chocp fix
                            
                            if global_variables.field_id == 'USG3':  #for USG3 2023/12/15
                                global_variables.bridge_h.report({'event':'VehicleAcquireCompleted', 'data':{
                                            'VehicleID':self.id,
                                            'CarrierLoc':self.action_in_run['loc'],
                                            'CommandID':uuid,
                                            'TransferPort':target,
                                            'CarrierID':carrierID_from_cmd,
                                            'ResultCode':0}})

                            output('VehicleAcquireCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], 
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':uuid,
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target,
                                    'CarrierID':carrierID_from_cmd, #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'ResultCode':0}) #chocp fix

                            self.LastAcquireTarget=target
                            carrierID_read_state=0
                            
                            # if global_variables.RackNaming == 43:
                            #     if carrierID_from_rfid =='ReadFail':
                            #         carrierID_read_state=1
                            #     elif carrierID_from_cmd != carrierID_from_rfid:
                            #         carrierID_read_state=3
                            #     else:
                            #         for vehicle_id, h_vehicle in self.h_vehicleMgr.vehicles.items(): #chocp fix, 2021/10/14
                            #             if h_vehicle.id!=self.id:
                            #                 for buf in h_vehicle.bufs_status:
                            #                     stockID=buf['stockID']
                            #                     if carrierID_from_rfid == stockID:
                            #                         carrierID_read_state=2
                            #     E82.report_event(self.secsgem_e82_h,
                            #                     E82.CarrierIDRead, {
                            #                     'VehicleID':self.id,
                            #                     'CarrierLoc':self.id+self.action_in_run['loc'],
                            #                     'CommandID':uuid, #chocp add 10/30
                            #                     'TransferPort':target,
                            #                     'CarrierID':carrierID_from_cmd, #chocp fix for tfme 2021/10/23
                            #                     'IDReadStatus':carrierID_read_state,
                            #                     'ResultCode':0}) #chocp fix

                            h_workstation=EqMgr.getInstance().workstations.get(target) 
                            if h_workstation:
                                try:
                                    if getattr(h_workstation, 'open_door_assist', False):
                                        if self.actions[0]['target'] == target and self.actions[0]['type'] == 'DEPOSIT':
                                            pass
                                        else:
                                            E82.report_event(self.secsgem_e82_h, E82.AssistCloseDoorReq, {'VehicleID':self.id,'TransferPort':target})
                                    elif getattr(h_workstation, "ip", "") and getattr(h_workstation, "port", ""): # zhangpeng 2025-03-10 close door for unload
                                        if global_variables.RackNaming in [16,23,34,54]:
                                            door_opened, err=h_workstation.door_action(uuid, 2, timeout=30) # zhangpeng 2025-03-13 close door for unload
                                            self.adapter.logger.info('door_action {}, result {}, msg {}'.format("CLOSE", door_opened, err))
                                except:
                                    pass

                                if carrierID_from_cmd and global_variables.TSCSettings.get('Safety', {}).get('PreBindCheck','no') == 'yes':
                                    if carrierID_from_cmd != carrierID_from_rfid:
                                        #for jcet should set serious error and alarm
                                        raise alarms.BaseCarrRfidConflictWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_rfid, handler=self.secsgem_e82_h)
                            
                            '''if carrierID_from_cmd and global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                if carrierID_from_cmd != carrierID_from_rfid:
                                    raise alarms.BaseCarrRfiddifferentWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_rfid, handler=self.secsgem_e82_h)

                            if self.re_assign_carrierID(self.action_in_run['loc'], wrong_id_allow=True) in ['None', 'Unknown']:
                                raise alarms.BaseCarrPosErrWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_cmd, handler=self.secsgem_e82_h)'''

                            #chocp 2024/03/27
                            if  global_variables.TSCSettings.get('Safety', {}).get('BufferStatusCheck','yes') == 'yes':
                                print(1, carrierID_from_cmd, carrierID_from_rfid)
                                print(2, local_tr_cmd['carrierID'])

                                if self.re_assign_carrierID(self.action_in_run['loc'], wrong_id_allow=True) in ['None', 'Unknown']:
                                    raise alarms.BaseCarrPosErrWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_cmd, handler=self.secsgem_e82_h)
                                
                                if carrierID_from_cmd and carrierID_from_cmd != carrierID_from_rfid:
                                    if carrierID_from_rfid is None or carrierID_from_rfid == '' : #richard 250430 For trigger rfid is empty or none" 
                                        raise alarms.BaseCarrRfidEmptyOrNoneWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_cmd, handler=self.secsgem_e82_h)
                                    else:
                                        raise alarms.BaseCarrRfiddifferentWarning(self.id, uuid, self.action_in_run['loc'], carrierID_from_rfid, handler=self.secsgem_e82_h)

                            EqMgr.getInstance().trigger(target, 'acquire_complete_evt', {'vehicleID':self.id, 'carrierID':carrierID_from_cmd})

                    elif self.AgvState == 'TrLoadReq':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {}) #chocp 2022/4/14
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        
                        carrierID=local_tr_cmd['carrierID'] #chocp 2022/4/14
                        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '')

                        if self.tr_assert:
                            if self.tr_assert['Result'] == 'CANCEL' and self.tr_assert.get('CommandID','') ==uuid:
                                self.AgvState='Parked'
                                continue

                            elif self.tr_assert['Result'] == 'OK':
                                if global_variables.RackNaming ==43:
                                    if self.tr_assert['TransferPort'] == 'None' or self.tr_assert['SendBy'] == 'by web': #chocp add 2021/12/21
                                        self.enter_depositing_state()
                                        continue
                                # ASECL Richard after
                                elif global_variables.RackNaming == 22:
                                    pose=tools.get_pose(self.adapter.last_point)
                                    print("pose: {}".format(pose))
                                    deviceID=pose["DeviceParam"]["DeviceID"]
                                    print("deviceID: {}".format(deviceID))
                                    h_OVEN = Iot.h.devices.get(deviceID, None)
                                    print("Iot.h.devices.keys: {}".format(Iot.h.devices.keys()))
                                    if h_OVEN:
                                        print("In h_OVEN")
                                        if h_OVEN.LD_RequestTransport() and h_OVEN.LD_ApproveTransport():
                                            print("in function")
                                            self.enter_depositing_state()#
                                            continue
                                        else:
                                            print("h_OVEN  LD_RequestTransport LD_ApproveTransport ")
                                    else:
                                        print("not ok")
                                        
                                # before
                                else:    
                                    if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'Load') and\
                                    (self.tr_assert['TransferPort'] == target or self.tr_assert['SendBy'] == 'by web'): #chocp add 2021/12/21
                                        self.tr_assert_result=target
                                        h_workstation=EqMgr.getInstance().workstations.get(target) # zhangpeng change 2025-03-10 request open door for load action
                                        if getattr(h_workstation, "ip", "") and getattr(h_workstation, "port", ""): #by zhenghao zhou
                                            if global_variables.RackNaming in [16,23,34,54]:
                                                door_opened, err=h_workstation.door_action(local_tr_cmd.get('uuid', '')) # zhangpeng 2025-03-13 open door for load
                                                self.adapter.logger.info('door_action {}, result {}, msg {}'.format("OPEN", door_opened, err))
                                                if door_opened != 1:
                                                    raise alarms.EqDoorReqFailWarning(self.id, uuid, target, handler=self.secsgem_e82_h)
                                        if self.tr_assert.get('Height',''):
                                            Height=self.tr_assert.get('Height')
                                            self.enter_depositing_state(Height)
                                        else:
                                            self.enter_depositing_state()
                                        continue
                                
                            elif self.tr_assert['Result'] == 'CHANGE' and self.tr_assert['CarrierID'] == carrierID: #chocp add 2021/1/6
                                #tools.reset_book_slot(local_tr_cmd.get('dest'))
                                tools.reset_book_slot(target) #chocp fix 2022/4/14
                                new_dest=self.tr_assert['NewDestPort']

                                if global_variables.RackNaming!=18:
                                    alarms.CommandDestPortChangedWarning(uuid, new_dest, handler=self.secsgem_e82_h)
                                task=self.actions[0]

                                task['target']=new_dest
                                task['local_tr_cmd']['dest']=new_dest
                                task['local_tr_cmd']['TransferInfo']['DestPort']=new_dest
                                
                                tools.book_slot(new_dest, self.id) #Chi 2022/07/26 fix
                            
                                self.AgvLastState=self.AgvState
                                self.AgvState='Parked'
                                continue
                                
                            #else: #NG or FAIL or PENDING
                            elif self.tr_assert['Result'] == 'NG'  and (self.tr_assert['TransferPort'] in [target,'None']): #for spil, no waiting
                                raise alarms.EqLoadCheckFailWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14
                                continue
                            
                            #richard for ASECL 250506
                            elif global_variables.RackNaming in [1,21,22] and self.tr_assert['Result'] == 'FAIL'  and (self.tr_assert['TransferPort'] in [target,'None']):
                                raise alarms.EqLoadCheckFailWarning(self.id, uuid, target, handler=self.secsgem_e82_h)
                                continue

                            elif global_variables.RackNaming == 18 and self.tr_assert['Result'] == 'PENDING': #8.22J-1 for K25 change load to get cmd
                                h_workstation=EqMgr.getInstance().workstations.get(target) 
                                if h_workstation:
                                    if 'Stock' in h_workstation.workstation_type:
                                        self.input_cmd_open=True
                                        self.AgvLastState=self.AgvState
                                        self.AgvState='Parked'
                                        print('<input cmd open>', self.input_cmd_open)
                                        continue

                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        if global_variables.RackNaming == 42:
                            EventInterval=30
                        elif global_variables.RackNaming == 36:
                            h_workstation=EqMgr.getInstance().workstations.get(target)
                            if h_workstation:
                                if "LONG" in h_workstation.equipmentID:
                                    EventInterval=60
                                else:
                                    EventInterval=10
                            else:
                                EventInterval=10
                        else:
                            EventInterval=10
                        
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrLoadReqTimeout', 0)

                        if self.TrLoadReqTime and (time.time()-self.TrLoadReqTime > pending_timeout):
                            raise alarms.EqCheckTimeoutWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

                        elif self.ValidInputLastReqTime and (time.time()-self.ValidInputLastReqTime > EventInterval):

                            h_workstation=EqMgr.getInstance().workstations.get(target) 
                            if getattr(h_workstation, 'open_door_assist', False):
                                E82.report_event(self.secsgem_e82_h,
                                            E82.TrLoadWithGateReq, {
                                            'VehicleID':self.id,
                                            'TransferPort':target,  #8.25.0-1
                                            'CarrierID':carrierID})
                            else:
                                if global_variables.RackNaming == 20 and 'Stock' in h_workstation.workstation_type: #chocp 2024/03/29
                                    if h_workstation.state == 'UnLoaded':
                                        self.tr_assert={'Request':'Load', 'Result':'OK', 'TransferPort':target, 'CarrierID':carrierID,'SendBy':'by host'}  

                                else:
                                    E82.report_event(self.secsgem_e82_h,
                                                E82.TrLoadReq, {
                                                'VehicleID':self.id,
                                                'TransferPort':target, #8.25.0-1
                                                'CarrierID':carrierID,
                                                'CommandID':uuid,
                                                'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                            output('TrLoadReq',{
                                    'VehicleID':self.id,
                                    'VehicleState':self.AgvState,
                                    'Station':self.at_station,
                                    'TransferPort':target,
                                    'CarrierID':carrierID})

                            self.ValidInputLastReqTime=time.time()
                    elif self.AgvState == "TrShiftReqCheck":# kelvinng 2024/11/04 TrShiftCheck    
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {}) #chocp 2022/4/14
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        
                        carrierID=local_tr_cmd['carrierID'] #chocp 2022/4/14
                        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '')

                        if self.tr_assert:
                            if self.tr_assert['Result'] == 'CANCEL' and self.tr_assert.get('CommandID','')  == uuid:
                                self.AgvState='Parked'
                                continue

                            elif self.tr_assert['Result'] == 'OK':
                                
                                 
                                if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'Shift') and (self.tr_assert['TransferPort'] == target or self.tr_assert['SendBy'] == 'by web'): #chocp add 2021/12/21
                                       
                                    self.enter_shifting_state()

                            elif self.tr_assert['Result'] == 'NG': 
                                
                                if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'UnLoad') and (self.tr_assert['TransferPort'] == target): #for spil, no waiting
                                    raise alarms.EqShiftCheckFailWarning(self.id, uuid, target) #chocp fix 2022/4/14
                                    continue
                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        if global_variables.RackNaming == 42:
                            EventInterval=30
                        elif global_variables.RackNaming == 36:
                            h_workstation=EqMgr.getInstance().workstations.get(target)
                            if h_workstation:
                                if "LONG" in h_workstation.equipmentID:
                                    EventInterval=60
                                else:
                                    EventInterval=10
                            else:
                                EventInterval=10
                        else:
                            EventInterval=10
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrUnLoadReqTimeout', 300)

                        if self.TrShiftReqTime and (time.time()-self.TrShiftReqTime > pending_timeout):
                            raise alarms.EqShiftCheckTimeoutWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

                        elif self.ValidInputLastReqTime and (time.time()-self.ValidInputLastReqTime > EventInterval):

                            h_workstation=EqMgr.getInstance().workstations.get(target)
                            if getattr(h_workstation, 'open_door_assist', False):
                                pass
                                

                            else:
                                 
                                
                                E82.report_event(self.secsgem_e82_h,
                                            E82.TrShiftReq, {
                                            'VehicleID':self.id,
                                            #'TransferPort':self.at_station, #fix bug 2022/10/11
                                            'TransferPort':target,
                                            'CarrierID':carrierID,
                                            'CommandID':uuid,
                                            'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                            # output('TrShiftReqCheck',{
                            #         'VehicleID':self.id,
                            #         'VehicleState':self.AgvState,
                            #         'Station':self.at_station,
                            #         'TransferPort':target,
                            #         'CarrierID':carrierID})

                            self.ValidInputLastReqTime=time.time()
                        
                                        

                    elif self.AgvState == 'Shifting': #chocp 2024/8/21 for shift
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')
                        carrierID=local_tr_cmd['carrierID']

                        target=self.action_in_run.get('target', '')
                        target2=self.action_in_run.get('target2', '')

                        if self.adapter.robot['finished'] == 'InterlockError':
                            if global_variables.RackNaming == 8:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Serious', handler=self.secsgem_e82_h)
                            elif global_variables.RackNaming == 43:
                                raise alarms.BaseShiftInterlockWarning(self.id, uuid, target, handler=self.secsgem_e82_h)
                            else:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Error', handler=self.secsgem_e82_h)

                        elif self.enter_shifting_state_time and time.time()-self.enter_shifting_state_time>self.robot_timeout: #timeout 200sec
                            raise alarms.RobotTimeoutCheckWarning(self.id, uuid, target) #20211001 chocp fix

                        elif self.adapter.robot['finished'] == 'Finished' and self.adapter.robot['status'] == 'Idle':

                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass

                            self.AgvLastState=self.AgvState
                            self.AgvState='Parked'
                            
                            #9/13 chocp fix from tfme
                            local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']})
                            local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['OriginalTransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']})

                            E82.report_event(self.secsgem_e82_h,
                                        E82.VehicleShiftCompleted, {
                                        'VehicleID':self.id,
                                        'FromPort':target,
                                        'TransferPort':target2,
                                        'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                        'CommandID':uuid, # jason  add 10/30
                                        'ResultCode':0})

                            output('VehicleShiftCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':uuid,
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target2,
                                    'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'ResultCode':0})

                            self.go_to_vcs=False

                            E82.report_event(self.secsgem_e82_h,
                                            E82.TransferCompleted,{
                                            'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                            'VehicleID':self.id,
                                            'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                            'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                            'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                            'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                            'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                            'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                            'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                            'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                            #'CarrierLoc':self.action_in_run['loc'],
                                            'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                            'ResultCode':0})

                            self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''))

                            try:
                                output('TransferCompleted', {
                                    'VehicleID':self.id,
                                    'DestType':local_tr_cmd.get('dest_type', 'other'),
                                    'Travel':local_tr_cmd.get('travel', 0),
                                    'CommandID':uuid,
                                    'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                                    'ResultCode':0,
                                    'Message':'' }, True)

                                if local_tr_cmd in self.tr_cmds:
                                    self.tr_cmds.remove(local_tr_cmd) #only output for host transfer cmds, if R cmd will have exception

                                output('TransferExecuteQueueRemove', {'CommandID':uuid}, True)
                                print('<<TransferComplete, TransferExecuteQueueRemove>>', {'CommandID':uuid})
                            except: #if no tr_cmd, like fault recovery action
                                traceback.print_exc()
                                pass

                    elif self.AgvState == 'Depositing':
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')
                        carrierID=local_tr_cmd['carrierID']

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27

                        if global_variables.TSCSettings.get('Safety', {}).get('TrBackReqCheckForEQ', 'no').lower() == 'yes' and not self.tr_back_req:
                            if self.adapter.robot['finished'] == 'wait_trback':
                                if not self.tr_back_timeout:
                                    self.TrBackReqTime=time.time()
                                self.trbackreq_cmd()

                        if self.adapter.robot['finished'] == 'InterlockError':
                            if global_variables.RackNaming == 8:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Serious', handler=self.secsgem_e82_h)
                            elif global_variables.RackNaming == 43:
                                raise alarms.BaseDestInterlockWarning(self.id, uuid, target, handler=self.secsgem_e82_h)
                            else:
                                raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Error', handler=self.secsgem_e82_h)

                        elif self.enter_depositing_state_time and time.time()-self.enter_depositing_state_time>self.robot_timeout: #timeout 200sec
                            raise alarms.RobotTimeoutCheckWarning(self.id, uuid, target) #20211001 chocp fix

                        elif self.adapter.robot['finished'] == 'Finished' and self.adapter.robot['status'] == 'Idle':
                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass
                            
                            if global_variables.RackNaming == 40:
                                advanceAreaUnlock=0
                                h_workstation_zone=''
                                for action in self.actions:
                                    if action['type'] != 'DEPOSIT':
                                        advanceAreaUnlock+=1
                                if not advanceAreaUnlock:
                                    h_workstation=EqMgr.getInstance().workstations.get(target)
                                    if h_workstation:
                                        h_workstation_zone=getattr(h_workstation, 'zoneID', 'other') 
                                    if self.wq and h_workstation_zone == 'other':
                                        if self.id in self.wq.dispatchedMRList:
                                            self.wq.dispatchedMRList.remove(self.id)
                                        print('MR dispatchedMRList',self.wq.dispatchedMRList)

                            res, rack_id, port_no=tools.rackport_format_parse(target)
                            if res: #8.22H-1 for turntable
                                h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
                                if h_eRack and h_eRack.zonetype ==3:
                                    h_eRack.carriers[port_no-1]['direction_target']='B'
                            # ASECL Richard after robot depositing
                            if global_variables.RackNaming == 22:
                                pose=tools.get_pose(self.adapter.last_point)
                                print("pose: {}".format(pose))
                                # deviceID=pose["DeviceParam"]["DeviceID"]
                                deviceID = pose.get('DeviceParam', {}).get('DeviceID')
                                print("deviceID: {}".format(deviceID))
                                if deviceID is not None:
                                    h_OVEN = Iot.h.devices.get(deviceID, None)
                                    if h_OVEN:
                                        print("In h_OVEN")
                                        if h_OVEN.LD_CheckPresence() and h_OVEN.LD_VerifyDevicePins():
                                            print("in function")
                                            pass
                                        else:
                                            continue
                            # before status output

                            self.AgvLastState=self.AgvState
                            
                            if self.wait_eq_operation == True:
                                self.enter_wait_eq_operation_time=time.time()
                                self.AgvState='Suspend'
                            else:
                                self.AgvState='Parked'
                            self.tr_assert_result=''  
                            
                            if carrierID == '' or carrierID == 'None': #chocp fix for tfme 2021/10/23
                                carrierID=self.re_assign_carrierID(self.action_in_run['loc'])
                                local_tr_cmd['carrierID']=carrierID
                                local_tr_cmd['TransferInfo']['CarrierID']=carrierID
                                
                            if carrierID and global_variables.RackNaming in [33, 58]:
                                buf_carrierID=self.re_assign_carrierID(self.action_in_run['loc'])
                                if carrierID == buf_carrierID:
                                    buf_idx=self.find_buf_idx(self.action_in_run['loc'])
                                    self.bufs_status[buf_idx]['type']='CoverTray'
                            
                            EqMgr.getInstance().trigger(target, 'deposit_complete_evt', {'vehicleID':self.id, 'carrierID':carrierID, 'source':local_tr_cmd['source'] })

                            E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleDepositCompleted, {
                                            'VehicleID':self.id,
                                            'TransferPort':target,
                                            'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                            'CommandID':uuid, # jason  add 10/30
                                            'ResultCode':0})
                            
                            if global_variables.field_id == 'USG3':  #for USG3 2023/12/15
                                global_variables.bridge_h.report({'event':'VehicleDepositCompleted', 'data':{
                                            'VehicleID':self.id,
                                            'TransferPort':target,
                                            'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                            'CommandID':uuid, # jason  add 10/30
                                            'ResultCode':0}})
                                
                            if global_variables.RackNaming == 53: #for Kumamoto TPB 24/10/29
                                #Close Erack Door when Deposit Completed Sean 241029
                                result, rack_id, port_no=tools.rackport_format_parse(target)
                                h_eRack=self.h_eRackMgr.eRacks.get(rack_id)
                                if result and carrierID:
                                    result=h_eRack.close_erack_door(port_no)

                            self.go_to_vcs=False

                            output('VehicleDepositCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':uuid,
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target,
                                    'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'ResultCode':0})

                            try:
                                h_workstation=EqMgr.getInstance().workstations.get(self.action_in_run['target']) 
                                if getattr(h_workstation, 'open_door_assist', False):
                                    E82.report_event(self.secsgem_e82_h,
                                            E82.AssistCloseDoorReq, {
                                            'VehicleID':self.id,
                                            'TransferPort':self.action_in_run['target']})
                                elif getattr(h_workstation, "ip", "") and getattr(h_workstation, "port", ""):
                                    if global_variables.RackNaming in [16,23,34,54]:
                                        door_opened, err=h_workstation.door_action(uuid, 5, timeout=30) # zhangpeng 2025-03-13 close door for load
                                        self.adapter.logger.info('door_action {}, result {}, msg {}'.format("CLOSE", door_opened, err))
                            except:
                                pass

                            #9/13 chocp fix from tfme
                            local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']})
                            local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['OriginalTransferInfo'], 'CarrierLoc':local_tr_cmd['carrierLoc']})

                            if local_tr_cmd['last']:

                                E82.report_event(self.secsgem_e82_h,
                                                E82.TransferCompleted,{
                                                'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                                'VehicleID':self.id,
                                                'TransferCompleteInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'], #9/13
                                                'TransferInfo':local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0] if local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'] else {},
                                                'CommandID':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''),
                                                'Priority':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Priority', 0),
                                                'Replace':local_tr_cmd['host_tr_cmd']['CommandInfo'].get('Replace', 0),
                                                'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                                'SourcePort':local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                                'DestPort':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                                #'CarrierLoc':self.action_in_run['loc'],
                                                'CarrierLoc':local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                                'ResultCode':0 })

                                self.secsgem_e82_h.rm_transfer_cmd(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''))

                                if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes': #only for RTD mode
                                    EqMgr.getInstance().orderMgr.update_work_status(local_tr_cmd.get('host_tr_cmd', {}).get('uuid', ''), 'SUCCESS', 0) #chocp fix 8/31

                            try:
                                output('TransferCompleted', {
                                    'VehicleID':self.id,
                                    'DestType':local_tr_cmd.get('dest_type', 'other'),
                                    'Travel':local_tr_cmd.get('travel', 0),
                                    'CommandID':uuid,
                                    'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                                    'ResultCode':0,
                                    'Message':'' }, True)

                                if global_variables.TSCSettings.get('Other', {}).get('AutoResetBooked') == 'yes':
                                    tools.reset_indicate_slot(local_tr_cmd.get('source')) #chocp fix 2022/6/2, leave for Erack update
                                    tools.reset_book_slot(target) #chocp fix 2022/6/2, leave for Erack update

                                #tools.reset_book_slot(local_tr_cmd.get('dest')) #not correct for re-deposit

                                # for buf in self.bufs_status: #remove command note, for auto recovery!
                                for idx, buf in enumerate(self.bufs_status): #remove command note, for auto recovery!
                                    if buf['local_tr_cmd'] == local_tr_cmd:
                                        print('remove ...................')
                                        if buf['stockID'] not in ['Unknown', '']:
                                            self.adapter.cmd_control(1, local_tr_cmd['host_tr_cmd']['uuid'], local_tr_cmd['host_tr_cmd'].get('original_source',''), local_tr_cmd['host_tr_cmd'].get('dest',''), idx+1, local_tr_cmd['carrierID'], lotID='')
                                        buf['local_tr_cmd']={} #chocp

                                if local_tr_cmd in self.tr_cmds:
                                    self.tr_cmds.remove(local_tr_cmd) #only output for host transfer cmds, if R cmd will have exception

                                output('TransferExecuteQueueRemove', {'CommandID':uuid}, True)

                                print('<<TransferComplete, TransferExecuteQueueRemove>>', {'CommandID':uuid})

                            except: #if no tr_cmd, like fault recovery action
                                traceback.print_exc()
                                pass
                    elif self.AgvState == 'TrSwapReq':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {}) #chocp 2022/4/14
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        
                        carrierID=local_tr_cmd['carrierID'] #chocp 2022/4/14
                        carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', '')

                        if self.tr_assert:
                            if self.tr_assert['Result'] == 'CANCEL' and self.tr_assert.get('CommandID','') ==uuid:
                                self.AgvState='Parked'
                                continue

                            elif self.tr_assert['Result'] == 'OK':
                                if (not self.tr_assert['Request'] or self.tr_assert['Request'] == 'Swap') and\
                                (self.tr_assert['TransferPort'] == target or self.tr_assert['SendBy'] == 'by web'): #chocp add 2021/12/21
                                    self.enter_swap_state()
                                    continue
                                
                            #else: #NG or FAIL or PENDING
                            elif self.tr_assert['Result'] == 'NG' and (self.tr_assert['TransferPort'] in [target,'None']): #for spil, no waiting
                                raise alarms.EqLoadCheckFailWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14
                                continue


                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        EventInterval=10
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrSwapReqTimeout', 0)

                        if self.TrSwapReqTime and (time.time()-self.TrSwapReqTime > pending_timeout):
                            raise alarms.EqCheckTimeoutWarning(self.id, uuid, target, handler=self.secsgem_e82_h) #chocp fix 2022/4/14

                        elif self.ValidInputLastReqTime and (time.time()-self.ValidInputLastReqTime > EventInterval):

                            E82.report_event(self.secsgem_e82_h,
                                        E82.TrSwapReq, {
                                        'VehicleID':self.id,
                                        'TransferPort':target, #8.25.0-1
                                        'CarrierID':carrierID,
                                        'CommandID':uuid,
                                        'ExecuteTime':str(local_tr_cmd.get('TransferInfo',{}).get('ExecuteTime',0))})

                            output('TrSwapReq',{
                                    'VehicleID':self.id,
                                    'VehicleState':self.AgvState,
                                    'Station':self.at_station,
                                    'TransferPort':target,
                                    'CarrierID':carrierID})

                            self.ValidInputLastReqTime=time.time()
                            
                    elif self.AgvState == 'Swapping':
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id, handler=self.secsgem_e82_h)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        # uuid=local_tr_cmd.get('uuid', '')
                        # carrierID=local_tr_cmd['carrierID']
                        
                        link_local_tr_cmd=local_tr_cmd.get('host_tr_cmd','').get('link','')
                        if link_local_tr_cmd:
                            uuid=link_local_tr_cmd.get('uuid','')
                            carrierID=link_local_tr_cmd['carrierID']
                        elif local_tr_cmd.get('host_tr_cmd','').get('replace', ''):
                            uuid=local_tr_cmd.get('uuid', '').rstrip('-UNLOAD')+'-LOAD'
                            carrierID=local_tr_cmd.get('host_tr_cmd','').get('carrierID')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27

                        if self.adapter.robot['finished'] == 'InterlockError':
                            raise alarms.BaseRobotInterlockWarning(self.id, uuid, target, 'Error', handler=self.secsgem_e82_h)

                        elif self.enter_swapping_state_time and time.time()-self.enter_swapping_state_time>self.robot_timeout: #timeout 200sec
                            raise alarms.RobotTimeoutCheckWarning(self.id, uuid, target) #20211001 chocp fix

                        elif self.adapter.robot['finished'] == 'Finished' and self.adapter.robot['status'] == 'Idle':
                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass

                            self.AgvLastState=self.AgvState
                            self.AgvState='Parked'
                            
                            bufid=self.find_buf_idx_by_carrierID(local_tr_cmd['carrierID'])
                            if bufid:
                                idx=self.vehicle_bufID.index(bufid)
                                self.bufs_status[idx]['local_tr_cmd']=local_tr_cmd
                            else:
                                raise alarms.SwapCarrierIDErrWarning(self.id, local_tr_cmd['carrierID'])
                            #EqMgr.getInstance().trigger(target, 'deposit_complete_evt', {'vehicleID':self.id, 'carrierID':carrierID, 'source':local_tr_cmd['source'] })

                            E82.report_event(self.secsgem_e82_h,
                                            E82.VehicleSwapCompleted, {
                                            'VehicleID':self.id,
                                            'TransferPort':target,
                                            'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                            #'CommandID':uuid, # jason  add 10/30
                                            'ResultCode':0})

                            output('VehicleSwapCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':uuid,
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target,
                                    'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'ResultCode':0})
                            if link_local_tr_cmd:
                                link_local_tr_cmd['TransferCompleteInfo'].append({'TransferInfo': link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd['OriginalTransferInfoList'] else {}, 'CarrierLoc':target})
                                link_local_tr_cmd['OriginalTransferCompleteInfo'].append({'TransferInfo': link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd['OriginalTransferInfoList'] else {}, 'CarrierLoc':target})
                            else:
                                local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0], 'CarrierLoc':target})
                                local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0], 'CarrierLoc':target})

                            if local_tr_cmd['last'] and link_local_tr_cmd:

                                E82.report_event(self.secsgem_e82_h,
                                                E82.TransferCompleted,{
                                                'CommandInfo':link_local_tr_cmd['CommandInfo'] if link_local_tr_cmd else local_tr_cmd['host_tr_cmd']['CommandInfo'],
                                                'VehicleID':self.id,
                                                'TransferCompleteInfo':link_local_tr_cmd['OriginalTransferCompleteInfo'] if link_local_tr_cmd else local_tr_cmd['host_tr_cmd']['OriginalTransferCompleteInfo'] , #9/13
                                                'TransferInfo':link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd else local_tr_cmd['host_tr_cmd']['OriginalTransferInfoList'][0],
                                                'CommandID':link_local_tr_cmd['CommandInfo'].get('CommandID', '') if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('CommandID', ''),
                                                'Priority':link_local_tr_cmd['CommandInfo'].get('Priority', 0) if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('Priority', 0),
                                                'Replace':link_local_tr_cmd['CommandInfo'].get('Replace', 0) if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('Replace', 0),
                                                'CarrierID':carrierID, #chocp fix for tfme 2021/10/23
                                                'SourcePort':link_local_tr_cmd['source'] if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('source', 0), #chocp fix for tfme 2021/10/23
                                                'DestPort':link_local_tr_cmd['dest']if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('dest', 0), #chocp fix for tfme 2021/10/23
                                                #'CarrierLoc':self.action_in_run['loc'],
                                                'CarrierLoc':link_local_tr_cmd['dest']if link_local_tr_cmd else local_tr_cmd['host_tr_cmd'].get('dest', 0), #chocp fix for tfme 2021/10/23
                                                'ResultCode':0 })

                                self.secsgem_e82_h.rm_transfer_cmd(link_local_tr_cmd['CommandInfo'].get('CommandID', '') if link_local_tr_cmd else local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''))


                            try:
                                output('TransferCompleted', {
                                    'VehicleID':self.id,
                                    'DestType':link_local_tr_cmd.get('dest_type', 'other')if link_local_tr_cmd else local_tr_cmd.get('dest_type', 'other'),
                                    'Travel':link_local_tr_cmd.get('travel', 0)if link_local_tr_cmd else local_tr_cmd.get('travel', 0),
                                    'CommandID':uuid,
                                    'TransferCompleteInfo':[{'TransferInfo':link_local_tr_cmd['OriginalTransferInfoList'][0] if link_local_tr_cmd else local_tr_cmd['host_tr_cmd']['TransferCompleteInfo']}],
                                    'ResultCode':0,
                                    'Message':'' }, True)

                                for tr_cmd in self.tr_cmds:
                                    if uuid == tr_cmd['uuid']:
                                        self.tr_cmds.remove(tr_cmd) #only output for host transfer cmds, if R cmd will have exception
                                        break

                                output('TransferExecuteQueueRemove', {'CommandID':uuid}, True)
                                
                                print('<<TransferComplete, TransferExecuteQueueRemove>>', {'CommandID':uuid})
                                
                            except: #if no tr_cmd, like fault recovery action
                                traceback.print_exc()
                                pass

                    elif self.AgvState == 'Charging':
                        
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        end_charge=False
                        #chocp fix end_charge=True from pause

                        if self.ChargeSafetyCheck == 'yes': #chi 2023/02/09
                            if time.time() - self.charge_start_time > self.ChargeTimeMax:
                                raise alarms.ChargeCommandTimeTooLongWarning(self.id, uuid, self.at_station)

                        if self.adapter.battery['charge']: #chocp fix 2022/6/1
                            start_charge=True
                        elif start_charge and not self.adapter.battery['charge']: #chocp fix 2022/6/1
                            start_charge=False
                            end_charge=True
                            #trigger a warning
                            self.adapter.move['arrival']='Fail'
                            alarms.ChargeCommandBreakOffWarning(self.id, uuid, self.at_station) #chocp 2022/6/29
                        else:
                            pass

                        if self.force_charge:
                            if (self.adapter.battery['percentage'] > self.RunAfterMinimumPower) and \
                            (self.charge_start_time and (time.time()-self.charge_start_time > self.MinimumChargeTime)):
                                end_charge=True

                        elif (self.charge_start_time and (time.time()-self.charge_start_time > self.MinimumChargeTime)):
                            end_charge=True

                            '''if (self.adapter.battery['percentage'] > self.RunAfterMinimumPower) and \
                                (self.charge_start_time and (time.time()-self.charge_start_time > self.MinimumChargeTime)): #fix charge algo 2022/6/27
                                    end_charge=True'''
                        else:
                            print(self.adapter.battery['percentage'], self.RunAfterMinimumPower)
                            print('In charging...', self.adapter.battery['percentage'] > self.RunAfterMinimumPower,\
                                time.time()-self.charge_start_time, self.MinimumChargeTime)
                            time.sleep(5)

                        if end_charge:
                            # self.adapter.charge_end() # Mike: 2021/08/25
                            if self.adapter.battery['percentage'] > self.ChargeBelowPower: # Mike: 2022/12/07
                                self.force_charge=False

                            E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleChargeCompleted, {
                                                'VehicleID':self.id,
                                                'BatteryValue':self.adapter.battery['percentage']}) #chocp 9/28 for tfme

                            output('VehicleChargeCompleted', {
                                    'VehicleID':self.id,
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'], #2022/6/1
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleState':'Parked',
                                    'Message':self.message,
                                    'ForceCharge':self.force_charge, #???
                                    'CommandID':uuid,
                                    'TransferPort':target,
                                    'ResultCode':0})
                            #bug
                            #self.tr_cmds=[] #double check #bug................
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check
                            self.action_in_run={} #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'

                    elif self.AgvState == 'Exchanging': # Mike: 2022/07/25
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        uuid=local_tr_cmd.get('uuid', '')

                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        end_charge=False
                        #chocp fix end_charge=True from pause

                        if self.adapter.battery['exchange']: #chocp fix 2022/6/1
                            start_charge=True
                        elif start_charge and not self.adapter.battery['exchange']: #chocp fix 2022/6/1
                            start_charge=False
                            end_charge=True
                        else:
                            pass

                        if self.adapter.battery['error']:
                            start_charge=False
                            end_charge=False
                            self.adapter.battery['error']=False
                            # raise exchange error
                            self.adapter.move['arrival']='Fail'

                        elif end_charge:
                            #if self.adapter.battery['percentage'] > self.ChargeBelowPower: # Mike: 2022/12/07
                            self.force_charge=False
                            end_charge=False

                            E82.report_event(self.secsgem_e82_h,
                                                E82.VehicleExchangeCompleted, {
                                                'VehicleID':self.id,
                                                'BatteryValue':self.adapter.battery['percentage']}) #chocp 9/28 for tfme

                            output('VehicleExchangeCompleted', {
                                    'VehicleID':self.id,
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'], #2022/6/1
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleState':'Parked',
                                    'Message':self.message,
                                    'ForceCharge':self.force_charge, #???
                                    'CommandID':uuid,
                                    'TransferPort':target,
                                    'ResultCode':0})
                            #bug
                            #self.tr_cmds=[] #double check #bug................
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check
                            self.action_in_run={} #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'
                            if self.adapter.version_check(self.adapter.mr_spec_ver, '5.1'):
                                self.adapter.battery_id_query()
                            
                    elif self.AgvState == 'Suspend':
                        if time.time()-self.enter_wait_eq_operation_time > global_variables.TSCSettings.get('Safety', {}).get('WaitEQTimeout', 30) or self.wait_eq_operation == False:
                            self.wait_eq_operation =False
                            self.AgvLastState=self.AgvState
                            self.AgvState='Parked'
    
            except alarms.MyException as alarm_instance:
                traceback.print_exc()

                self.alarm_handler(alarm_instance) #test
                time.sleep(1)
            
            except:
                traceback.print_exc()
                sub_code=traceback.format_exc()
                alarm_instance=alarms.VehicleInternalWarning(self.id, sub_code, handler=self.secsgem_e82_h) #chocp fix 2021/11/26
                #self.alarm_handler('Removed')
                self.alarm_handler(alarm_instance)
                time.sleep(1)
        else:
            self.adapter.thread_stop=True
            #self.adapter.stop=True #chocp:2021/3/9
            self.AgvState='Removed'
            ActiveVehicles[self.id]["VehicleInfo"]["VehicleState"]=1
            E82.update_variables(self.secsgem_e82_h, {'ActiveVehicles': ActiveVehicles})
            E82.report_event(self.secsgem_e82_h,
                E82.VehicleRemoved,{
                'VehicleID':self.id})
            self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'end vehicle thread'))
            if self.tr_cmds:
                del_command_id_list=[]
                for del_tr_cmd in self.tr_cmds:
                    del_command_id_list.append(del_tr_cmd.get('uuid', ''))
                for del_command_id in del_command_id_list:
                    self.abort_tr_cmds_and_actions(del_command_id, 40002, 'Transfer command in exectuing queue be aborted', cause='by disable vehicle')
            if self.wq:
                if self.id in self.wq.dispatchedMRList:
                    self.wq.dispatchedMRList.remove(self.id)
                print('MR dispatchedMRList',self.wq.dispatchedMRList)
