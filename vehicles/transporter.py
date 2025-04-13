import collections
import traceback
import threading
import time
import vehicles.transporterAdapter as adapterMR

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

import semi.e82_equipment as E82
import semi.e88_stk_equipment as E88

from global_variables import PortsTable
from global_variables import PoseTable
from global_variables import Route

from global_variables import Equipment
from global_variables import Iot
from global_variables import output

from alarms import get_sub_error_msg

import math
from pprint import pformat

from tr_wq_lib import TransferWaitQueue #for StockOut
#from web_service_log import * 


#['Unknown','Removed','Unassigned','Enroute','Parked','Acquiring','Depositing','Pause','TrLoadReq','TrUnloadReq']

class Transporter(threading.Thread):

    def __init__(self, TransporterMgr, secsgem_e88_h, setting):

        self.secsgem_e88_h=secsgem_e88_h

        self.token=threading.Lock()


        self.Transporter_bufID=['BUF01', 'BUF02', 'BUF03', 'BUF04', 'BUF05', 'BUF06', 'BUF07', 'BUF08', 'BUF09', 'BUF10', 'BUF11', 'BUF12']
        self.enableBuffer=['yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes'] #chocp add 2022/1/5

        self.last_bufs_status=[{'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}},\
                                {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}}]

        self.bufs_status=[{'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False},\
                    {'stockID':'Unknown', 'type':'None', 'local_tr_cmd':{}, 'local_tr_cmd_mem':{}, 'read_fail_warn':False, 'pos_err_warn':False, 'do_auto_recovery':False}] #chocp fix, 2022/1/20

        self.carrier_dest=['']*12

        self.bufNum=4 #need check
        self.carrier_status_list=[] #chocp 2022/8/30

        self.connect_retry=3

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
        self.wq=None #8.21H-4

        self.robot_timeout=200 #chocp 2022/4/22
        self.call_support_delay=0
        self.call_support_time=0

        self.tr_cmd_assign_timeout=0 #chocp 8/21
        self.ExpectedDurationExpiredTime=0
        self.TrLoadReqTime=0
        self.TrUnLoadReqTime=0
        self.ValidInputLastReqTime=0

        self.TrBackReqTime=0
        self.charge_start_time=0
        self.enter_unassigned_state_time=0
        self.enter_acquiring_state_time=0
        self.enter_depositing_state_time=0


        self.tr_assert={}
        self.input_cmd_open=False #for K25
        self.input_cmd_open_again=False #for K25

        #self.AgvNextState='Removed'
        self.doPreDispatchCmd=False #for StockOut
        self.waiting_run=False
        self.stop_command=False
        self.change_target=False
        self.wait_stop=False
        self.no_begin=False
        self.findchargestation=False #chi 2022/11/18
        self.findstandbystation=False
        self.tr_back_req=False #chi 2023/03/15
        self.tr_back_timeout=False
        self.host_call_cmd=False
        self.emergency_evacuation_cmd=False
        self.emergency_situation=''
        self.emergency_evacuation_stop=False
        self.tsc_paused=False
        self.ControlPhase='GoTransfer' #GoTransfer, GoRecovery, #GoCharge, #GoStandby
        self.AgvLastState='Removed'
        self.LastAcquireTarget=''
        self.goTrUnLoadReq=0
        
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
        self.host_stop=False #chi 2023/03/15
        #self.ResultCode=0
        
        self.alarm_node=[]
        self.alarm_edge=[]
        #self.exception_deque=collections.deque(maxlen=1)

        self.h_eRackMgr=Erack.h

        self.h_transporterMgr=TransporterMgr.getInstance() #chocp add 2021/10/14

        self.adapter=0

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
            'Speed':0 #K11 Speed 20241122 kelvinng
            })

        # Mike: 2021/05/14
        '''VehicleInfo={"VehicleInfo":{"VehicleID": self.id, "VehicleState": 0, "SOH":100}}
        ActiveVehicles=E82.get_variables(self.secsgem_e88_h, 'ActiveVehicles')
        ActiveVehicles[self.id]=VehicleInfo
        E82.update_variables(self.secsgem_e88_h, {'ActiveVehicles': ActiveVehicles})'''

        self.secsgem_e88_h.Zones.add(self.id)
        zone_list={}
        for i in range(self.bufNum):
            CarrierLoc=self.id+"BUF{:02d}".format(i+1)
            zone_list[CarrierLoc]={'StockerUnitID':CarrierLoc, 'StockerUnitState':0, 'CarrierID':''}
        datasets={}
        datasets['ZoneSize']=self.bufNum
        datasets['ZoneCapacity']=self.bufNum
        datasets['ZoneType']=3
        datasets['StockerUnit']=dict(zone_list)
        datasets['ZoneUnitState']={self.id:1}
        self.secsgem_e88_h.Zones.set(self.id, datasets)

        self.adapter=adapterMR.Adapter(self.secsgem_e88_h, self, self.id, self.ip, self.port, self.max_speed, self.connect_retry) #vehicle_instance=self

        self.update_params(setting)

        self.thread_stop=False
        self.heart_beat=0
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

        if self.model == 'Type_T': #new for >8 slot begin
            self.bufNum=2
            self.vehicle_bufID=['BUF01', 'BUF02']
            self.vehicle_onTopBufs=['BUF01']

        else:
            self.bufNum=2
            self.vehicle_bufID=['BUF01', 'BUF02']
            self.vehicle_onTopBufs=['BUF01']

        self.carrier_status_list=[] #for >8 slot
        for i in range(self.bufNum):
            self.carrier_status_list.append('Unknown') #chocp 2022/8/30

        self.enableBuffer=setting.get('enableBuffer', []) #chocp add 2022/1/5       
        self.enable_begin_flag=setting.get('enableBeginFlag', 'no')
        print('We get model:{}, bufNum:{}, begin flag:{}'.format(self.model, self.bufNum, self.enable_begin_flag))

        self.appendTransferAllowed=setting.get('appendTransferAllowed', 'no')
        global_variables.global_vehicles_priority[self.id]=setting.get('priority', 0)

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
        self.TimeChargeingWhen=setting.get('Charge', {}).get('timeChargWhen', 'no')
        TimeChargeing=[]

        try:
            TimeChargeing=setting.get('Charge', {}).get('timecharging', '').strip(',').split(',')
        except:
            pass

        self.TimeChargeing=TimeChargeing

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



    def query_vehicle_state(self):
        pass

    def add_executing_transfer_queue(self, local_tr_cmd):

        #need check source, notify eRack machine
        #need check dest, notify eRack book flags
        #if book unavailable need set alarm

        output('TransferExecuteQueueAdd', {
                    'VehicleID':self.id,
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    'CarrierID':local_tr_cmd['carrierID'],
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
        # self.secsgem_e88_h.transfer_start(local_tr_cmd.get('uuid', ''))
        '''try:
            ActiveTransfers=E82.get_variables(self.secsgem_e88_h, 'ActiveTransfers')
            ActiveTransfers[local_tr_cmd.get('uuid', '')]['CommandInfo']['TransferState']=2
            E82.update_variables(self.secsgem_e88_h, {'ActiveTransfers': ActiveTransfers})
        except:
            pass'''

        # Mike: 2022/05/23
        # E82.report_event(self.secsgem_e88_h, E82.Transferring, {'CommandID':local_tr_cmd['host_tr_cmd']['uuid'],'CarrierID':local_tr_cmd['carrierID'],'VehicleID':self.id}) #8.24B-4

        if local_tr_cmd.get('uuid', ''):
            self.secsgem_e88_h.transfer_start(local_tr_cmd.get('uuid', ''), self.id)
        output('Transferring', {
                'CommandID':local_tr_cmd.get('uuid', '')})

        return


    def AgvErrorCheck(self, mr_state):
        #print('AgvErrorCheck', self.adapter.move['status'], self.adapter.robot['status'], self.adapter.alarm['error_code'])
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        command_id=local_tr_cmd.get('uuid', '')
        carrierID=local_tr_cmd.get('carrierID', '')
        target=self.action_in_run.get('target', '')
        
        if self.adapter.last_point and self.adapter.last_point not in PoseTable.mapping: #8.28.26
            raise alarms.PointNotInMapWarning(self.adapter.last_point, handler=self.secsgem_e88_h)
        
        elif self.manual:
            raise alarms.OperateManualTestWarning(self.id, command_id, handler=self.secsgem_e88_h)

        elif self.adapter.online['status']!='Ready': #disconnect
            raise alarms.BaseOffLineWarning(self.id, command_id)

        elif self.adapter.alarm['error_code']: #one time alarm, chocp fix hex code
            #"900001":"GetRouteTimeout",
            sub_code=self.adapter.alarm['error_code']
            if self.adapter.alarm['error_code'] == '900001': #Mike: 2022/10/21
                raise alarms.GetRouteTimeoutWarning(self.id, command_id, target, sub_code)
            raise alarms.BaseOtherAlertWarning(self.id, command_id, target, sub_code) #fix 2022/2/10

        elif self.adapter.robot['status'] == 'Error': #robot error
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            sub_code=self.adapter.alarm['error_code']
            raise alarms.BaseRobotWarning(self.id, command_id, target, sub_code) #fix 2022/2/10

        elif self.adapter.move['status'] == 'Error':
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            sub_code=self.adapter.alarm['error_code']
            raise alarms.BaseMoveWarning(self.id, command_id, target, sub_code) #fix 2022/2/10

        elif self.adapter.online['man_mode']: #control offline
            if self.wait_error_code < 30: # Mike: 2023/04/28
                self.wait_error_code += 1
                return True
            self.wait_error_code=0
            if global_variables.RackNaming == 2: #for nxcp
                raise alarms.BaseNotAutoModeWarning(self.id, command_id, 'Serious')
            else:
                raise alarms.BaseNotAutoModeWarning(self.id, command_id, 'Error')

        #elif len(self.exception_deque):
        #    raise self.exception_deque.popleft()

        elif mr_state == 'Unassigned' or mr_state == 'Parked': #chocp 2021/7/16
            if self.adapter.move['status']!='Idle':
                sub_code=self.adapter.alarm['error_code']
                raise alarms.BaseMoveCheckWarning(self.id, command_id, target, sub_code) #fix 2022/2/10

            if self.adapter.robot['status']!='Idle':
                sub_code=self.adapter.alarm['error_code']
                raise alarms.BaseRobotCheckWarning(self.id, command_id, target, sub_code) #fix 2022/2/10

 
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
                        local_command_id=command_id
                        host_command_id=local_tr_cmd['host_tr_cmd']['uuid']
                    except:
                        pass

                    if self.bufs_status[i]['stockID'] == 'None':
                        if self.last_bufs_status[i]['stockID'] not in ['Unknown', '']:
                            if self.secsgem_e88_h.Carriers.Data[self.last_bufs_status[i]['stockID']].CarrierState in [3]:
                                self.secsgem_e88_h.carrier_remove(self.last_bufs_status[i]['stockID'], 
                                                    2 if self.AgvState == 'Acquiring' else 1)
                            else:
                                self.secsgem_e88_h.carrier_kill(self.last_bufs_status[i]['stockID'])

                        '''E82.report_event(self.secsgem_e88_h,
                                             E82.CarrierRemoved, {
                                             'VehicleID':self.id,
                                             'CommandID':host_command_id,
                                             'CarrierLoc':self.vehicle_bufID[i],
                                             'CarrierID':self.last_bufs_status[i]['stockID']}) #fix 7
                        self.secsgem_e88_h.rm_carrier(self.last_bufs_status[i]['stockID'])'''

                        self.carrier_status_list=[] #chocp for >8 slot 2022/8/30
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        self.carrier_port_status_list=[] #for >8 slot
                        for j in range(self.bufNum):
                            self.carrier_port_status_list.append(self.adapter.carriers[j]['port'])

                        output('CarrierRemoved', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.vehicle_bufID[i],
                                'CarrierID':self.last_bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list,
                                'Ports':self.carrier_port_status_list
                                })

                        self.bufs_status[i]['type']='None'
                        self.carrier_dest[i]=''

                    else:
                        if self.bufs_status[i]['stockID']:
                            if self.last_bufs_status[i]['stockID'] not in ['', 'None', 'Unknown']:
                                self.secsgem_e88_h.carrier_kill(self.last_bufs_status[i]['stockID'])

                            if self.AgvState == 'Depositing':
                                self.secsgem_e88_h.carrier_wait_in(self.bufs_status[i]['stockID'], 
                                                    self.id+self.vehicle_bufID[i],
                                                    self.id, 
                                                    NoIDRead=False)
                            else:
                                self.secsgem_e88_h.carrier_add(self.bufs_status[i]['stockID'], 
                                                    self.id+self.vehicle_bufID[i],
                                                    self.id)

                        self.carrier_status_list=[] #for >8 slot
                        for j in range(self.bufNum):
                            self.carrier_status_list.append(self.bufs_status[j]['stockID'])

                        self.carrier_port_status_list=[] #for >8 slot
                        for j in range(self.bufNum):
                            self.carrier_port_status_list.append(self.adapter.carriers[j]['port'])

                        output('CarrierInstalled', {
                                'VehicleID':self.id,
                                'CommandID':local_command_id,
                                'CarrierLoc':self.vehicle_bufID[i],
                                'CarrierID':self.bufs_status[i]['stockID'],
                                'Carriers':self.carrier_status_list,
                                'Ports':self.carrier_port_status_list
                                })

                        print('CarrierInstalled', self.bufs_status[i]['stockID'], self.adapter.carriers[i]['status'])

                        self.bufs_status[i]['type']=self.bufs_status[i]['local_tr_cmd'].get('TransferInfo', {}).get('CarrierType', '')
                        print(self.bufs_status[i]['type'])

                        if global_variables.TSCSettings.get('Safety',{}).get('RenameFailedID', 'no') == 'yes'\
                                and self.bufs_status[i]['stockID'] == 'ReadFail':
                            carrierID = self.bufs_status[i]['local_tr_cmd'].get('TransferInfo', {}).get('CarrierID', local_tr_cmd['carrierID'])
                            self.adapter.rfid_control(i+1, carrierID)

                #if self.bufs_status[i]['stockID'] == 'ReadFail' and mr_state not in ['Acquiring','Depositing','Pause'] and not global_variables.TSCSettings.get('Safety', {}).get('BufferNoRFIDCheck', 'no') == 'yes':
                if self.bufs_status[i]['read_fail_warn'] and\
                  mr_state not in ['Acquiring','Depositing','Pause'] and not global_variables.TSCSettings.get('Safety', {}).get('BufferNoRFIDCheck', 'no') == 'yes': #2022/2/22
                    if global_variables.RackNaming!=18:
                        alarms.BaseCarrRfidFailWarning(self.id, command_id, self.vehicle_bufID[i], carrierID)
                        self.bufs_status[i]['read_fail_warn']=False

                if self.bufs_status[i]['pos_err_warn'] and mr_state not in ['Acquiring','Depositing','Pause']:
                    self.bufs_status[i]['pos_err_warn']=False
                    if global_variables.TSCSettings.get('Safety', {}).get('BufferPosCheck', 'yes') == 'yes':
                        raise alarms.BaseCarrPosErrWarning(self.id, command_id, self.vehicle_bufID[i], carrierID)
                    alarms.BaseCarrPosErrWarning(self.id, command_id, self.vehicle_bufID[i], carrierID)


        return False #chocp fix 2021/11/26

    #will abort all relative local_tr_cmds and actions
    def abort_tr_cmds_and_actions(self, local_command_id, result_code, result_txt, cause='by alarm'): #fix 6

        res=False
        del_actions=[]

        for action in self.actions:
            if action['local_tr_cmd']['host_tr_cmd']['uuid'] in local_command_id:
                del_actions.append(action)

        for action in del_actions:
            self.actions.remove(action)

        if self.action_in_run and self.action_in_run['local_tr_cmd'] and self.action_in_run['local_tr_cmd']['host_tr_cmd']['uuid'] in local_command_id:
            self.tr_assert={'Result':'CANCEL'} #???

        del_tr_cmds=[]
        for local_tr_cmd in self.tr_cmds:
            if local_tr_cmd['host_tr_cmd']['uuid'] in local_command_id:
                del_tr_cmds.append(local_tr_cmd)
                if local_tr_cmd['host_tr_cmd'].get('link'): #8.22J-2
                    link_local_tr_cmd=local_tr_cmd['host_tr_cmd'].get('link')
                    if local_tr_cmd['host_tr_cmd'].get('sourceType') == 'StockOut' or local_tr_cmd['host_tr_cmd'].get('sourceType') == 'ErackOut': #Chi 2022/12/29
                        # E82.report_event(self.secsgem_e88_h, E82.TransferCancelInitiated, {'CommandID':link_local_tr_cmd.get('uuid', '')})
                        self.secsgem_e88_h.transfer_cancel({'CommandID':link_local_tr_cmd.get('uuid', '')})
                        for queue_id, zone_wq in TransferWaitQueue.getAllInstance().items():
                            if queue_id ==link_local_tr_cmd['zoneID'] or queue_id ==local_tr_cmd['source']:
                                zone_wq.preferVehicle=''
                            if link_local_tr_cmd['sourceType'] == 'FromVehicle' and queue_id == self.id:
                                res, host_tr_cmd=zone_wq.remove_waiting_transfer_by_commandID(link_local_tr_cmd.get('uuid', ''))
                                if res:
                                    self.doPreDispatchCmd=False
                                    '''E82.report_event(self.secsgem_e88_h, E82.TransferCancelCompleted, {
                                        'CommandID':link_local_tr_cmd.get('uuid', ''),
                                        'TransferCompleteInfo':link_local_tr_cmd.get('TransferCompleteInfo', ''), #9/13
                                        'TransferInfo':link_local_tr_cmd['TransferInfoList'][0] if link_local_tr_cmd['TransferInfoList'] else {},
                                        'CommandID':link_local_tr_cmd['CommandInfo'].get('CommandID', ''),
                                        'Priority':link_local_tr_cmd['CommandInfo'].get('Priority', 0),
                                        'Replace':link_local_tr_cmd['CommandInfo'].get('Replace', 0),
                                        'CarrierID':link_local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                        'SourcePort':link_local_tr_cmd['source'], #chocp fix for tfme 2021/10/23
                                        'DestPort':link_local_tr_cmd['dest'], #chocp fix for tfme 2021/10/23
                                        #'CarrierLoc':self.action_in_run['loc'],
                                        'CarrierLoc':link_local_tr_cmd['dest']}) #chocp fix for tfme 2021/10/23'''
                                    self.secsgem_e88_h.transfer_cancel_succ({'CommandID':link_local_tr_cmd.get('uuid', '')})
                                    output('TransferCancelCompleted', {'CommandID':link_local_tr_cmd.get('uuid', '')})
                                else:
                                    # E82.report_event(self.secsgem_e88_h, E82.TransferCancelFailed, {'CommandID':link_local_tr_cmd.get('uuid', '')})
                                    self.secsgem_e88_h.transfer_cancel_failed({'CommandID':link_local_tr_cmd.get('uuid', '')})
                    else:
                        if global_variables.TSCSettings.get('Safety', {}).get('SkipAbortLoadWhenUnloadAlarm', 'no') == 'no':
                            # E82.report_event(self.secsgem_e88_h, E82.TransferAbortInitiated, {'CommandID':link_local_tr_cmd.get('uuid', '')})
                            self.secsgem_e88_h.transfer_abort(link_local_tr_cmd.get('uuid', ''))
                            self.secsgem_e88_h.transfer_abort_succ(link_local_tr_cmd.get('uuid', ''))
                            self.abort_tr_cmds_and_actions(link_local_tr_cmd.get('uuid', ''), 40002, 'Transfer command in exectuing queue be aborted', cause='by link')


        for local_tr_cmd in del_tr_cmds: #why can't bind above
            res=True
            
            if cause!='by alarm':
                alarms.CommandAbortWarning(cause, local_tr_cmd.get('uuid', '')) #set alarm by host or by web abort

            if local_tr_cmd.get('uuid', ''):
                self.secsgem_e88_h.transfer_complete(local_tr_cmd.get('uuid', ''), RESULTCODE=result_code)
            output('TransferCompleted', {
                    'VehicleID':self.id,
                    'DestType':local_tr_cmd.get('dest_type', 'other'),
                    'Travel':local_tr_cmd.get('travel', 0),
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    #'CommandInfo':local_tr_cmd['host_tr_cmd']['CommandInfo'],
                    'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                    'ResultCode':result_code,
                    'Message':result_txt }, True)


            output('TransferExecuteQueueRemove', {'CommandID':local_tr_cmd.get('uuid', '')}, True)

            print('<<Abort, TransferExecuteQueueRemove>>', {'CommandID':local_tr_cmd.get('uuid', '')})


            tools.reset_indicate_slot(local_tr_cmd.get('source'))
            tools.reset_book_slot(local_tr_cmd.get('dest'))

            self.tr_cmds.remove(local_tr_cmd)
            # self.adapter.clean_route()


            #9/13 chocp fix from tfme
            #local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':self.action_in_run['loc']})
            local_tr_cmd['host_tr_cmd']['TransferCompleteInfo'].append({'TransferInfo': local_tr_cmd['TransferInfo'], 'CarrierLoc':local_tr_cmd['dest']}) #bug, need check
   
            if local_tr_cmd['last']:
                
                if cause == 'by alarm': #fix 6
                    #E82 transfer complete
                    self.secsgem_e88_h.transfer_complete(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''), RESULTCODE=result_code)
                else:
                    #E82 cancel complete
                    self.secsgem_e88_h.transfer_complete(local_tr_cmd['host_tr_cmd']['CommandInfo'].get('CommandID', ''), RESULTCODE=40002)

        # for i in range(self.bufNum):
        #     if self.bufs_status[i]['local_tr_cmd'].get('uuid', '').lstrip('PRE-') == local_command_id :
        #         self.bufs_status[i]['do_auto_recovery']=True

        for buf in self.bufs_status: #remove command note, for auto recovery!
            if buf['local_tr_cmd'] in del_tr_cmds:
                print('remove ...................')
                buf['local_tr_cmd']={} #chocp

        return res

    def reset_traffic_jam(self):
        print('reset_traffic_jam')

        self.release_alarm()

        #go stanby
        wait_vehicle='' # Mike: 2021/11/12
        for vehicle_id, h_vehicle in self.h_transporterMgr.vehicles.items(): #chocp fix, 2021/10/14
            if h_vehicle.id!=self.id:
                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                    self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id)) 
                    wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                    break
      
        self.return_standby_cmd(wait_vehicle, from_unassigned=False) # Mike: 2021/11/12
        return


    def release_alarm(self):
        print('release_alarm')

        if self.alarm_set!='Info' and self.error_code:
            pass
            # self.secsgem_e88_h.clear_alarm(self.error_code)
 
        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''
        self.error_txt=''
        self.message='None'


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

        #if global_variables.RackNaming == 4 and (self.alarm_set == 'Serious' or global_variables.TSCSettings['Recovery']['Auto']!='yes') : #abort all trnasfers
        '''if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenSeriousAlarm') == 'yes' and\
         (self.alarm_set == 'Serious' or global_variables.TSCSettings.get('Recovery', {}).get('Auto')!='yes') : #abort all trnasfers'''

        abort_all=False #8.21K
        if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenErrorAlarm') == 'yes' and self.alarm_set in ['Serious', 'Error']:
            abort_all=True
        if global_variables.TSCSettings.get('Recovery', {}).get('AbortAllCommandsWhenSeriousAlarm') == 'yes' and self.alarm_set == 'Serious':
            abort_all=True

        if abort_all: #abort all trnasfers
            self.abort_tr_cmds_and_actions(local_tr_cmd.get('uuid', ''), self.error_code, self.error_txt, cause='by alarm')
            del_command_id_list=[] #chocp 2022/6/29
            for local_tr_cmd in self.tr_cmds:
                del_command_id_list.append(local_tr_cmd.get('uuid', ''))

            for command_id in del_command_id_list:
                self.abort_tr_cmds_and_actions(command_id, self.error_code, self.error_txt, cause='by other cmd')

        elif self.action_in_run: #chocp 2021/11/28
            self.abort_tr_cmds_and_actions(local_tr_cmd.get('uuid', ''), self.error_code, self.error_txt, cause='by alarm')
            
            ## check valid buffer

        if self.alarm_set!='Info' and self.error_code:
            pass
            # self.secsgem_e88_h.clear_alarm(self.error_code)
 
        #self.ResultCode=self.error_code
        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.alarm_set=''
        self.error_code=0
        self.error_sub_code=''

        self.error_txt=''
        self.message='None'
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
        self.alarm_set=alarm_instance.level
        self.error_code=alarm_instance.code
        self.error_sub_code=alarm_instance.sub_code #chocp add 2021/12/11
        self.error_txt=alarm_instance.txt
        self.message=alarm_instance.more_txt

        self.error_reset_cmd=False
        self.AgvLastState=self.AgvState
        self.AgvState='Pause'
        self.call_support_time=time.time()

        self.force_charge=False

        #self.adapter.charge_end() #chocp fix 2021/11/26

        self.at_station='' #2020/12/10 chocp

        output('VehiclePauseSet',{
                'VehicleID':self.id,
                'CommandID':self.action_in_run.get('local_tr_cmd', {}).get('uuid', ''),
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'AlarmCode':self.error_code,
                'VehicleState':self.AgvState,
                'ForceCharge':self.force_charge,
                'Message':self.message})

        # Mike: 2021/03/15
        print('In alarm_handler clean right')

        #self.adapter.clean_right(True)
        if self.adapter.online['connected'] or global_variables.TSCSettings.get('Safety', {}).get('ReleaseRightWhenDisconnected','yes') == 'yes':
            self.adapter.planner.clean_right(False) #chocp 2021/12/31

        if self.action_in_run: #may move to clear alarm
            pass
            # EqMgr.getInstance().trigger(local_tr_cmd['source'], 'alarm_set', {'vehicleID':self.id, 'CommandID':local_tr_cmd.get('uuid', ''), 'Message':alarm_instance.more_txt})
            # EqMgr.getInstance().trigger(local_tr_cmd['dest'], 'alarm_set', {'vehicleID':self.id, 'CommandID':local_tr_cmd.get('uuid', ''), 'Message':alarm_instance.more_txt})
        
        return

    def enter_acquiring_state(self):
        self.AgvLastState=self.AgvState
        self.AgvState='Acquiring'

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        commandID=local_tr_cmd.get('uuid', '')
        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
        to_point=tools.find_point(target)

        self.enter_acquiring_state_time=time.time()

        output('VehicleAcquireStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Connected':self.adapter.online['connected'],
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':local_tr_cmd.get('uuid', ''),
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge, #???
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':local_tr_cmd['carrierID'], 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':local_tr_cmd['carrierID']})

        '''res=False
        port=PortsTable.mapping[target]
        cont=0
        carrier_type_index=1
        if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
            port=PortsTable.mapping[target]
            cont=0
            current_stop=port[0]
            current_direct=port[4]
            next_stop=PortsTable.mapping[self.actions[1].get('target', '')][0] if len(self.actions) > 1 else ''
            next_direct=PortsTable.mapping[self.actions[1].get('target', '')][4] if len(self.actions) > 1 else -1
            if current_stop == next_stop and global_variables.TSCSettings.get('Other', {}).get('E84Continue', 'yes') == 'yes':
                cont=1

        if global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypeSensitiveEnable') == 'yes':
            carrierType=local_tr_cmd.get('TransferInfo', {}).get('CarrierType', 'None') #chocp 2022/1/4
            print('carrierType', carrierType)
            if carrierType not in global_variables.global_cassetteType:
                raise alarms.CarrierTypeCheckWarning(self.id, commandID, local_tr_cmd['carrierID'], carrierType)

            carrier_type_index=global_variables.global_cassetteType.index(carrierType)+1
            print('current_stop:{} {}, next_stop:{} {}, port_info:{}, carrierType_index:{}'.format(current_stop, current_direct, next_stop, next_direct, port, carrier_type_index))
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
                res=self.adapter.acquire_control(current_stop, self.action_in_run['loc'], local_tr_cmd['carrierID'], e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index)
            else:
                res=self.adapter.acquire_control(target+'#'+carrierType, self.action_in_run['loc'], local_tr_cmd['carrierID'])
        else:
            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and len(PortsTable.mapping.get(target, [])) >= 7:
                target=current_stop
            res=self.adapter.acquire_control(target, self.action_in_run['loc'], local_tr_cmd['carrierID'], e84=port[4], cs=port[5], cont=cont, pn=port[6], ct=carrier_type_index)

        if not res: # Mike: 2022/05/23
            raise alarms.RobotGetRightCheckWarning(self.id, commandID, target)'''

        return
        


    def enter_depositing_state(self):
        self.AgvLastState=self.AgvState
        self.AgvState='Depositing'

        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        commandID=local_tr_cmd.get('uuid', '')
        target=self.action_in_run.get('target', '')
        to_point=tools.find_point(target)

        self.enter_depositing_state_time=time.time() 

        output('VehicleDepositStarted',{
                'Battery':self.adapter.battery['percentage'],
                'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                'Health':self.adapter.battery['SOH'],
                'MoveStatus':self.adapter.move['status'],
                'RobotStatus':self.adapter.robot['status'],
                'RobotAtHome':self.adapter.robot['at_home'],
                'VehicleID':self.id,
                'CommandID':local_tr_cmd.get('uuid', ''),
                'VehicleState':self.AgvState,
                'Message':self.message,
                'ForceCharge':self.force_charge,
                'CarrierLoc':self.action_in_run['loc'],
                'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':'', 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                'TransferPort':target,
                'CarrierID':''})

        return


    def execute_action(self, force_route=False, force_cost= -1, force_path=[]):
        #self.ResultCode=0
        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
        target=self.action_in_run.get('target', '')
        #to_station=self.action_in_run['target']
        to_point=tools.find_point(target)
        print('>>> check : ', self.action_in_run['type'])

        if force_route or not self.goTrUnLoadReq and (self.action_in_run['type'] == 'GOTO' or self.at_station == '' or (self.adapter.last_point!=to_point)): #fix 8/20
            if self.action_in_run['type'] == 'GOTO':
                self.actions.popleft()
                
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

            # Mike: 2022/02/08
            cost_b, path_b=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+block_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
            self.adapter.logger.info('{} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block:', cost_b, path_b, self.adapter.last_point, to_point))

            # Mike: 2022/02/08
            if cost_b > 0 and (cost_b-cost) < global_variables.TSCSettings.get('TrafficControl',{}).get('MaxFindWayCost', 60000) and global_variables.TSCSettings.get('TrafficControl', {}).get('EnableFindWay', 'yes').lower() == 'yes':
                cost, path=cost_b, path_b

            if cost < 0:
                raise alarms.BaseRouteWarning(self.id, local_tr_cmd.get('uuid', ''), self.adapter.last_point, to_point)

            self.AgvLastState=self.AgvState
            self.AgvState='Enroute'

            if local_tr_cmd:
                if local_tr_cmd['carrierID'] == '' or local_tr_cmd['carrierID'] == 'None': #chocp fix for tfme 2021/10/23
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

            if local_tr_cmd:
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
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    'Travel':cost,
                    'VehicleState':self.AgvState,
                    'Message':self.message,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':local_tr_cmd.get('carrierID'), 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                    'TransferPort':target})

            if self.at_station and self.adapter.last_point == to_point and self.adapter.move['arrival'] == 'EndArrival':
                pass
            else:
                if self.enable_begin_flag == 'yes' and not self.no_begin:
                    self.adapter.move_control(path, True, True)
                else:
                    self.no_begin=False
                    self.adapter.move_control(path, False, True)

            if local_tr_cmd:
                if self.secsgem_e88_h.Carriers.Data[local_tr_cmd['carrierID']].CarrierState in [1, 4]:
                    self.secsgem_e88_h.carrier_transfer(local_tr_cmd['carrierID'],
                                                    target,
                                                    self.id,
                                                    local_tr_cmd.get('uuid', ''))

        elif self.action_in_run['type'] in ['DEPOSIT']:
            self.actions.popleft()
            try:
                if local_tr_cmd.get('uuid', ''):
                    self.secsgem_e88_h.transfer_complete(local_tr_cmd.get('uuid', ''), RESULTCODE=0)
                output('TransferCompleted', {
                    'VehicleID':self.id,
                    'DestType':local_tr_cmd.get('dest_type', 'other'),
                    'Travel':local_tr_cmd.get('travel', 0),
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    'TransferCompleteInfo':[{'TransferInfo':local_tr_cmd['TransferInfo'], 'CarrierLoc':''}],
                    'ResultCode':0,
                    'Message':'' }, True)

                if local_tr_cmd in self.tr_cmds:
                    self.tr_cmds.remove(local_tr_cmd) #only output for host transfer cmds, if R cmd will have exception

                output('TransferExecuteQueueRemove', {'CommandID':local_tr_cmd.get('uuid', '')}, True)

                print('<<TransferComplete, TransferExecuteQueueRemove>>', {'CommandID':local_tr_cmd.get('uuid', '')})

            except: #if no tr_cmd, like fault recovery action
                traceback.print_exc()
                pass

            if target:

                target_pt=tools.find_point(target)
                target_pose=[PoseTable.mapping[target_pt]['x'], PoseTable.mapping[target_pt]['y']]

                near_pt=tools.round_a_point_new([self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['z'], self.adapter.move['pose']['h']])[0]
                real_pose=[self.adapter.move['pose']['x'], self.adapter.move['pose']['y']]
                real_diff=math.sqrt((target_pose[0] - real_pose[0])**2 + (target_pose[1] - real_pose[1])**2)
                self.adapter.logger.info('{} {} {} {} {}'.format('[{}] '.format(self.id), 'unload station check', target_pt, near_pt, real_diff))

                if (target_pt != near_pt) and real_diff > global_variables.TSCSettings.get('TrafficControl', {}).get('NearDistance'): #100mm
                    raise alarms.PortNotReachWarning(self.id, local_tr_cmd.get('uuid', ''), target) #chocp fix 2022/4/14

                idx=PortsTable.mapping[target][6]-1
                if self.adapter.carriers[idx]['port'] == 'ReadyToUnload':
                    '''print(">>> ready_to_unload", target)
                    self.secsgem_e88_h.Ports.Data[target].ready_to_unload()'''
                    EqMgr.getInstance().trigger(target, 'ready_to_unload_evt', {})
                    if local_tr_cmd['carrierID']:
                        if self.secsgem_e88_h.Carriers.Data[local_tr_cmd['carrierID']].CarrierState == 2:
                            self.secsgem_e88_h.carrier_wait_out(local_tr_cmd['carrierID'], 
                                                            target,
                                                            self.id,
                                                            'TP')

                self.carrier_dest[idx]=target
                self.goTrUnLoadReq += 1
                self.TrUnLoadReqTime=time.time()
                self.tr_assert={}

                output('TrUnLoadReq',{
                        'VehicleID':self.id,
                        'VehicleState':self.AgvState,
                        'Station':self.at_station,
                        'Message':self.message,
                        'TransferPort':target,
                        'CarrierID':local_tr_cmd['carrierID']})

                self.ValidInputLastReqTime=time.time()

            return

        elif self.action_in_run['type'] == 'CHARGE':
            print('QQ')
            #need add go
            self.AgvLastState=self.AgvState
            self.AgvState='Charging'
            self.call_support_time=time.time() #chocp 2022/4/12

            '''E82.report_event(self.secsgem_e88_h,
                             E82.VehicleChargeStarted, {
                             'VehicleID':self.id })'''

            '''E88.report_event(self.secsgem_e88_h,
                                E88.CraneOutOfService,{
                                'StockerCraneID':self.id})'''

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
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    'VehicleState':self.AgvState,
                    'Station':self.at_station,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':local_tr_cmd['carrierID'], 'Dest':target, 'ToPoint':to_point},
                    'Message':self.message})

            self.charge_start_time=time.time()
            if not self.adapter.charge_start():
                alarms.ChargeCommandTimeoutWarning(self.id, local_tr_cmd.get('uuid', ''), self.at_station) #chocp 2021/12/10


        elif self.action_in_run['type'] == 'EXCHANGE':
            #need add go
            self.AgvLastState=self.AgvState
            self.AgvState='Exchanging'
            # self.call_support_time=time.time() #chocp 2022/4/12

            '''E82.report_event(self.secsgem_e88_h,
                             E82.VehicleExchangeStarted, {
                             'VehicleID':self.id })'''

            '''E88.report_event(self.secsgem_e88_h,
                                E88.CraneOutOfService,{
                                'StockerCraneID':self.id})'''

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
                    'CommandID':local_tr_cmd.get('uuid', ''),
                    'VehicleState':self.AgvState,
                    'Station':self.at_station,
                    'ForceCharge':self.force_charge,
                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':local_tr_cmd['carrierID'], 'Dest':target, 'ToPoint':to_point},
                    'Message':self.message})

            self.charge_start_time=time.time()
            if not self.adapter.exchange_start():
                # warning
                pass

        else:
            self.actions.popleft() #unknown action type
            pass

        return

    def buf_residual(self):
        residual=0
        
        if self.emergency_evacuation_cmd == True:
            return residual
        
        for i in range(self.bufNum):
            if self.enableBuffer[i] == 'yes' and self.adapter.carriers[i]['status']!='None':
                if not self.bufs_status[i].get('local_tr_cmd_mem', {}).get('host_tr_cmd', {}).get('preTransfer'): #chocp add for preDispatch and preTansfer
                    residual+=1

        #print('residual', residual)
        return residual
 
    def buf_available(self): #for BufContrain fix
        avaliable=0
        array=[]

        for idx in range(self.bufNum):
            #if self.adapter.carriers[idx]['status'] == 'None':
            if self.enableBuffer[idx] == 'yes' and self.adapter.carriers[idx]['status'] == 'None': #chocp 2022/1/6
                avaliable+=1
                array.append(self.vehicle_bufID[idx])

        print('avaliable', avaliable)
        print(array)

        return avaliable, array




    def find_buf_idx(self, target):
        return self.vehicle_bufID.index(target)
    
    def re_assign_carrierID(self, buf_id):
        carrierID=''
        try:
            idx=self.vehicle_bufID.index(buf_id)
            if self.bufs_status[idx]['stockID'] not in ['None', 'ReadFail', 'Unknown']: # Mike 2022/09/21 
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

    def return_standby_cmd(self, wait_vehicle='', tmpPark=False, from_unassigned=True,situation='Normal'): # Mike: 2021/11/12 #Sean: 23/3/16
        
        uuid=100*time.time()
        uuid%=1000000000000
        CommandID='G%.12d'%uuid
        CommandInfo={'CommandID':CommandID, 'Priority':100}
        route_cost=-1
        force_cost=-1
        force_path=[]
        route_station=''
        block_nodes=[] # Mike: 2021/04/06
        block_group_list=[] # Sean: 23/3/16

        for car in global_variables.global_vehicles_location_index:
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
        
        #optional_standby_station=[]
        sorted_station=[] #Sean 23/3/13
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
                sorted_station.append( {'station' : station, 'point' : to_point, 'cost' : cost} )
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
            if wait_vehicle: # Mike: 2021/11/12
                cont=False
                for group in PoseTable.mapping[station['point']]['group'].split("|"):
                    if group in plan_route_group or station['point'] in block_nodes:
                        self.adapter.logger.info("return_standby_cmd: route {} is occupied".format(station['station']))
                        cont=True
                        break
                    if group in block_group_list:
                        self.adapter.logger.info("return_standby_cmd: route {} has other vehicles standby (need to wait)".format(station['station']))
                if cont:
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
                    break
                else:
                    self.adapter.logger.info("return_standby_cmd: try route {} fail".format(station['station']))
                    continue

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
            alarms.BaseTryStandbyFailWarning(self.id, CommandID, self.adapter.last_point, 'None')
        elif route_station:
            self.findstandbystation=False
            self.adapter.logger.info('return_standby_cmd to: {}'.format(route_station))
            TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': route_station}

            host_tr_cmd={
                'primary':1,
                'uuid':CommandID,
                'carrierID':TransferInfo['CarrierID'],
                'source':TransferInfo["SourcePort"],
                'dest':TransferInfo["DestPort"],
                'zoneID':'other', #9/14
                'priority':99,
                'replace':0,
                'CommandInfo':CommandInfo,
                'TransferCompleteInfo':[],
                'TransferInfoList':[TransferInfo],
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
                'first':True,
                'last':True,
                'TransferInfo':TransferInfo,
                'host_tr_cmd':host_tr_cmd
            }

            local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
            local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

            self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target':route_station, 'local_tr_cmd':local_tr_cmd} #chocp 2022/4/14 remove uuid

            self.CommandIDList.append(CommandID) #new standby cmd
            if from_unassigned:
                #self.CommandIDList=[CommandID]
                '''E82.report_event(self.secsgem_e88_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})'''

                E88.report_event(self.secsgem_e88_h,
                                    E88.CraneActive,{
                                    'CommandID':CommandID,
                                    'StockerCraneID':self.id})

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

            if cost < 0:
                cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes+self.alarm_node, block_edges=global_variables.global_disable_edges+self.alarm_edge, algo=global_variables.RouteAlgo,score_func=global_variables.score_func)
                self.adapter.logger.info('{} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block_node:', cost, path, self.alarm_node, to_point, self.alarm_edge))

            if cost < 0:
                cost, path=Route.h.get_a_route(self.adapter.last_point, to_point, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges+self.alarm_edge, algo=global_variables.RouteAlgo,score_func=global_variables.score_func)
                self.adapter.logger.info('{} {} {} {} {} {} {}'.format('[{}] '.format(self.id), 'get_a_route_with_block_edge:', cost, path, self.alarm_node, to_point, self.alarm_edge))

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
            if global_variables.global_occupied_station[occupied] != '':
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
        sorted_station.sort(key=sort_key) #sorted by cost and ABCS
        print('\nsorted route {}'.format([[station['station'], station['cost']] for station in sorted_station]))
        
        
        for station in sorted_station:
            cont=False
            for group in PoseTable.mapping[station['point']]['group'].split("|"):
                if group in block_group_list:
                    self.adapter.logger.info("find_charge_station: route {} has other vehicles standby".format(station['station']))
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
                        continue

        # self.adapter.logger.info("global_variables.cs_find_by:{}".format(global_variables.cs_find_by))
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
        CommandID='C%.12d'%uuid
        CommandInfo={'CommandID':CommandID, 'Priority':99}
        TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': station}
        self.adapter.logger.info('exec_charge_cmd to: {}'.format(station))

        self.charge_cmd=False
        if not station:
            raise alarms.BaseTryChargeFailWarning(self.id, CommandID, self.adapter.last_point, 'None')
            
        if not self.adapter.charge_end(): #avoid move at breakon at C001
            raise alarms.DischargeCommandFailedWarning(self.id, CommandID, self.at_station) #chocp 2021/12/10

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
            'TransferInfoList':[TransferInfo],
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
            'first':True,
            'last':True,
            'TransferInfo':TransferInfo,
            'host_tr_cmd':host_tr_cmd
            }
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'
        self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target': station, 'local_tr_cmd':local_tr_cmd}
        self.actions.append(self.action_in_run)
        self.actions.append({'type':'CHARGE', 'carrierID':'', 'loc':'', 'order':0, 'target': station, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid

        self.CommandIDList.append(CommandID) #new_charge_cmd
        if from_unassigned:
            # self.CommandIDList=[CommandID]

            '''E82.report_event(self.secsgem_e88_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})'''

            E88.report_event(self.secsgem_e88_h,
                                E88.CraneOutOfService,{
                                'StockerCraneID':self.id})

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
        CommandID='C%.12d'%uuid
        CommandInfo={'CommandID':CommandID, 'Priority':99}
        TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort': station}

        self.charge_cmd=False
        if not station:
            raise alarms.BaseTryChargeFailWarning(self.id, CommandID, self.adapter.last_point, 'None')

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
            'TransferInfoList':[TransferInfo],
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
            'first':True,
            'last':True,
            'TransferInfo':TransferInfo,
            'host_tr_cmd':host_tr_cmd
            }

        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

        self.action_in_run={'type':'GOTO', 'carrierID':'', 'loc':'', 'order':0, 'target':station, 'local_tr_cmd':local_tr_cmd}
        self.actions.append(self.action_in_run)
        self.actions.append({'type':'EXCHANGE', 'carrierID':'', 'loc':'', 'order':0, 'target':station, 'local_tr_cmd':local_tr_cmd}) #chocp 2022/4/14 remove uuid

        self.CommandIDList.append(CommandID) #new exchange cmd
        if from_unassigned:
            #self.CommandIDList=[CommandID]

            '''E82.report_event(self.secsgem_e88_h,
                            E82.VehicleAssigned,{
                            'VehicleID':self.id,
                            'CommandIDList':self.CommandIDList,
                            'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})'''

            E88.report_event(self.secsgem_e88_h,
                                E88.CraneOutOfService,{
                                'StockerCraneID':self.id})

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

    def append_transfer(self, host_tr_cmd, bufID, byTheWay=True): #8.21H-4
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
                    'host_tr_cmd':host_tr_cmd
                }
        local_tr_cmd['source_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['source'], '')  else 'other'
        local_tr_cmd['dest_type']='workstation' if EqMgr.getInstance().workstations.get(local_tr_cmd['dest'], '')  else 'other'

        self.add_executing_transfer_queue(local_tr_cmd)

        source_port=local_tr_cmd['source']
        dest_port=local_tr_cmd['dest']

        action1={
                'type':'ACQUIRE',
                'target':source_port,
                'point':tools.find_point(source_port),
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


        if local_tr_cmd['dest_type'] == 'workstation' and byTheWay:
            self.actions.appendleft(action2)
        else:
            self.actions.append(action2)

        self.actions.appendleft(action1)

        tools.book_slot(local_tr_cmd['dest'], self.id, local_tr_cmd['source'])  #book for MR, may cause delay
        tools.indicate_slot(local_tr_cmd['source'], local_tr_cmd['dest'])

    def host_call_move_cmd(self): #8.27.13
        print('>>> host_call_move_cmd')
        action={
            'type':'GOTO',
            'carrierID':'',
            'target':self.host_call_params.get('PortID', ''),
            'order':0,
            'loc':'',  #Buf Constrain
            'local_tr_cmd':{}
        }
        self.actions.append(action)

        self.AgvLastState=self.AgvState
        self.AgvState='Parked'

        self.host_call_cmd=False
        self.host_call_params={}

    def emergency_evacuation(self,Situation):
        self.emergency_evacuation_cmd=True
        self.emergency_situation=Situation # FireDisaster  EarthQuake
        self.adapter.logger.info('{} {} {}'.format('[{}] '.format(self.id), 'Get emergency evacuation cmd and start abort all transfer cmd', Situation))
        del_command_id_list=[] 
        for del_tr_cmd in self.tr_cmds:
            del_command_id_list.append(del_tr_cmd.get('uuid', ''))

        for del_command_id in del_command_id_list:
            self.abort_tr_cmds_and_actions(del_command_id, self.error_code, self.error_txt, cause='by emergency evacuation')
            
    #how to remove vehicle dynamically???
    def run(self):
        self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'start loop thread'))

        #self.adapter=adapterMR.Adapter(self, self.id, self.ip, self.port, self.max_speed) #vehicle_instance=self

        self.adapter.setDaemon(True)
        self.adapter.start()

        time.sleep(3) #add delay for MR connecting
        last_AgvState=''
        last_AgvSubState=''
        last_stop_flag=None
        start_charge=False
        end_charge=False
        send_alarm=False
        while not self.thread_stop:
            try:
                self.heart_beat=time.time()
                if self.adapter.heart_beat > 0 and time.time() - self.adapter.heart_beat > 60:
                    self.adapter.heart_beat=0
                    self.adapter.logger.info('{}'.format("<<<  TransporterAdapter {} is dead. >>>".format(self.id)))
                if last_AgvState != self.AgvState or last_AgvSubState != self.AgvSubState or last_stop_flag != self.thread_stop:
                    try:
                        self.adapter.logger.debug('{} {} {} {}'.format('[{}] '.format(self.id), 'Vehicle state: ', self.AgvState, self.AgvSubState, self.thread_stop, self.thread_stop))
                    except:
                        pass
                    last_AgvState=self.AgvState
                    last_AgvSubState=self.AgvSubState
                    last_stop_flag=self.thread_stop
                #print(self.AgvState, self.adapter.online['sync'])
                time.sleep(0.1)
                # Mike: 2021/05/14
                if global_variables.global_generate_routes == False:

                    if self.AgvState == 'Removed':
                        if self.adapter.online['sync']:

                            '''output('VehiclePoseUpdate',{
                                    'VehicleID':self.id,
                                    'Pose':[self.adapter.move['pose']['x'], self.adapter.move['pose']['y'], self.adapter.move['pose']['h'], self.adapter.move['pose']['z']],
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'], # Mike: 2022/05/31
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'ForceCharge':self.force_charge,
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home']
                                    })''' #2024/1/3 chocp


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

                            E88.report_event(self.secsgem_e88_h,
                                            E88.CraneOutOfService,{
                                            'StockerCraneID':self.id})

                            self.action_in_run={}
                            #self.tr_cmds=[]
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear()
                            self.AgvLastState=self.AgvState #fix 8/20
                            self.AgvState='Pause'
                            self.call_support_time=time.time()


                    elif self.AgvState == 'Pause': # with alarm
                        time.sleep(1)

                        #print(self.error_code, self.adapter.alarm['error_code'], self.adapter.online['man_mode'], self.adapter.online['connected'])
                        if self.error_reset_cmd:
                            self.goTrUnLoadReq=0
                            for port in PortsTable.reverse_mapping[self.adapter.last_point]:
                                if port in self.secsgem_e88_h.Ports.Data:
                                    self.secsgem_e88_h.Ports.Data[port].PortBook=False
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

                        #elif self.error_code == 10016 and self.adapter.online['connected']:
                        #   self.reset_alarm()????

                        if global_variables.TSCSettings.get('Recovery', {}).get('Auto') == 'no' or self.alarm_set == 'Serious':
                            if not send_alarm and self.error_code not in [0, 10008, 10009, 10010]:
                                send_alarm=True
                                self.adapter.alarm_control(self.error_code, True)
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
                                raise alarms.EmergencyEvacuationWarning(self.id)
                            elif not self.adapter.relay_on:
                                go_park=True
                        if go_park and self.evacuate_station:
                            if self.token.acquire(False):
                                try:
                                    self.AgvSubState='InStandbyCmdStatus'
                                    print('go_park', self.adapter.relay_on, self.evacuate_station)
                                    self.return_standby_cmd(wait_vehicle, tmpPark, from_unassigned=True, situation='Evacuation')
                                    self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()

                    elif self.AgvState == 'Unassigned':
                        #print('Unassigned',len(self.tr_cmds))
                        self.message='None'
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue

                        #check transfer cmd
                        if self.waiting_run:
                            self.actions.clear()
                            #chocp 2022/8/30
                            if self.use_schedule_algo == 'by_fix_order':
                                fail_tr_cmds_id, actions=schedule_by_fix_order.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)
                            elif self.bufNum<=4:
                                fail_tr_cmds_id, actions=schedule_by_lowest_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point) #how to fail order?
                            else:
                                fail_tr_cmds_id, actions=schedule_by_better_cost.task_generate(self.tr_cmds, self.buf_available, self.adapter.last_point)

                            print(fail_tr_cmds_id)
                            for local_command_id in fail_tr_cmds_id:
                                alarms.TscActionGenWarning(self.id, local_command_id)
                                self.abort_tr_cmds_and_actions(local_command_id, 10002, 'TSC generate action fail or no buffer left', cause='by alarm') #del all relative command

                            if actions:
                                self.actions.extend(actions) #self.actions is dequeue
                            
                            #vehicle assigned
                            if len(self.actions):
                                self.CommandIDList=[] #from unassigned
                                for local_tr_cmd in self.tr_cmds:
                                    if local_tr_cmd['host_tr_cmd']['uuid'] not in self.CommandIDList:#fix 5
                                        self.CommandIDList.append(local_tr_cmd['host_tr_cmd']['uuid']) #release commandID

                                '''E88.report_event(self.secsgem_e88_h,
                                            E88.CraneActive,{
                                            'StockerCraneID':self.id,
                                            'CommandIDList':self.CommandIDList,
                                            'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})'''

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

                                #print('VehicleAssigned', self.CommandIDList)
                                self.tr_cmd_assign_timeout=time.time() #chocp 8/21
                                self.action_in_run=self.actions[0] #fix 8/20
                                self.execute_action(force_route=True) #fix 8/20

                            self.waiting_run=False
                            continue

                        elif self.host_call_cmd:
                            self.host_call_move_cmd()
                            continue

                        '''target=
                        if self.secsgem_e88_h.Ports.Data[target].PortBook == True or True:

                            self.AgvLastState=self.AgvState

                            self.AgvState='Acquiring'
                            self.enter_acquiring_state_time=time.time()

                            output('VehicleAcquireStarted',{
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':local_tr_cmd.get('uuid', ''),
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'ForceCharge':self.force_charge, #???
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'TransferTask':{'VehicleID':self.id, 'Action':self.action_in_run['type'], 'CommandID':local_tr_cmd.get('uuid', ''), 'CarrierID':local_tr_cmd['carrierID'], 'Dest':target, 'ToPoint':self.action_in_run['loc']},
                                    'TransferPort':target,
                                    'CarrierID':local_tr_cmd['carrierID']})

                            continue'''


                        #check charge cmd, 8.21H-6
                        check=False
                        if self.charge_cmd:
                            self.force_charge=True
                            check=True
    

                        elif self.adapter.battery['percentage'] < self.ChargeBelowPower:
                            self.force_charge=True
                            check=True
                            
                        elif self.TimeChargeingWhen == "yes" and tools.Timed_charging(self.TimeChargeing):#zsg 2024/6/27
                            if not self.adapter.battery['percentage'] > self.BatteryHighLevel:
                                self.force_charge=True
                                check=True

                        elif not self.adapter.relay_on: 
                            if self.ChargeWhenIdle == 'yes' and self.adapter.battery['percentage'] <= self.BatteryHighLevel:
                                if self.enter_unassigned_state_time and\
                                    (time.time()-self.enter_unassigned_state_time) > self.IntoIdleTime:
                                        check=True

                        elif self.adapter.relay_on and not self.adapter.battery['charge']:
                            self.adapter.relay_on=False

                        #if self.force_charge or (check and not self.doPreDispatchCmd):#8.21N-4
                        if check and not self.doPreDispatchCmd and not self.tsc_paused: #8.24B-3
                            is_abcs, chargeStation=self.find_charge_station()
                            if self.token.acquire(False):
                                try:
                                    if self.AgvSubState == 'InWaitCmdStatus':
                                        if not chargeStation and not self.findchargestation: #chi 2022/11/18
                                            self.findchargestation=True
                                            alarms.BaseTryChargeFailWarning(self.id, 'C00000000', self.adapter.last_point, 'None')
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
                        force_go_park=False
                        wait_vehicle='' # Mike: 2021/11/12
                        for vehicle_id, h_vehicle in self.h_transporterMgr.vehicles.items(): #chocp fix, 2021/10/14
                            if h_vehicle.id!=self.id:
                                if global_variables.global_moveout_request.get(h_vehicle.id, '') == self.id: #one vehicle wait for me release right
                                    self.adapter.logger.info('{} {} {}'.format(h_vehicle.id, ' wait ', self.id))
                                    go_park=True
                                    force_go_park=True
                                    wait_vehicle=h_vehicle.id # Mike: 2021/11/12
                                    break
                        else: 
                            if not self.adapter.relay_on and (self.at_station not in self.standby_station) and self.ParkWhenStandby == 'yes':
                                if self.enter_unassigned_state_time and\
                                    (time.time()-self.enter_unassigned_state_time) > self.IntoStandbyTime:
                                    go_park=True

                        #if go_park and self.standby_station and not self.doPreDispatchCmd:
                        if (go_park and not self.tsc_paused) or force_go_park and self.standby_station and not self.doPreDispatchCmd:
                            if self.token.acquire(False):
                                try:
                                    if self.AgvSubState == 'InWaitCmdStatus':
                                        self.AgvSubState='InStandbyCmdStatus'
                                        print('go_park', self.adapter.relay_on, self.standby_station)
                                        self.return_standby_cmd(wait_vehicle, from_unassigned=True)
                                        self.AgvSubState='InWaitCmdStatus'
                                    self.token.release()
                                    continue #chocp 2022/2/11 fix
                                except:
                                    self.AgvSubState='InWaitCmdStatus' #chocp fix 2022/1/21
                                    self.token.release()

                    #Parked
                    elif self.AgvState == 'Parked':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        if len(self.actions):
                            self.action_in_run=self.actions[0]

                            self.execute_action()

                            if self.AgvState == 'Enroute':
                                print('>>> check ', self.adapter.last_point, PortsTable.reverse_mapping[self.adapter.last_point])
                                for target in PortsTable.reverse_mapping[self.adapter.last_point]:
                                    if target in self.secsgem_e88_h.Ports.Data:
                                        port=self.secsgem_e88_h.Ports.Data[target]
                                        '''if [port.PortState, port.PortServiceState] != [3, 2]:
                                            print(">>> transfer_block", target)
                                            port.transfer_block()'''
                                        EqMgr.getInstance().trigger(target, 'transfer_block_evt', {})

                            continue #double check

                            '''elif self.host_call_cmd:
                                self.host_call_cmd=False

                                self.AgvLastState=self.AgvState  #fix 8/20
                                self.AgvState='TrLoadReq'

                                continue'''

                        elif self.goTrUnLoadReq:
                            self.goTrUnLoadReq -= 1
                            self.AgvLastState=self.AgvState
                            self.AgvState='TrUnLoadReq'
                            self.TrUnLoadReqTime=time.time()
                            print('To TrUnLoadReq')
                            continue

                        else:
                            check=False

                            for port in PortsTable.reverse_mapping[self.adapter.last_point]:
                                if port in self.secsgem_e88_h.Ports.Data and self.secsgem_e88_h.Ports.Data[port].PortBook:
                                    if port in self.carrier_dest:
                                        self.goTrUnLoadReq += 1
                                        check=True
                                    else:
                                        check=True
                                        break

                            if check:
                                if self.goTrUnLoadReq:
                                    self.goTrUnLoadReq -= 1
                                    self.AgvLastState=self.AgvState
                                    self.AgvState='TrUnLoadReq'
                                    self.TrUnLoadReqTime=time.time()
                                    print('To TrUnLoadReq')
                                    continue
                                else:
                                    self.AgvLastState=self.AgvState  #fix 8/20
                                    self.AgvState='TrLoadReq'
                                    self.TrLoadReqTime=time.time()
                                    print('To TrLoadReq')
                                    continue

                            time.sleep(1) #???
                            print('To GoUnassigned:')

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

                            E88.report_event(self.secsgem_e88_h,
                                        E88.CraneIdle,{
                                        'StockerCraneID':self.id,
                                        'CommandIDList':self.CommandIDList,
                                        'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})

                            print('Unassigned',self.CommandIDList)
                            self.CommandIDList=[]
                            self.action_in_run={}
                            #self.tr_cmds=[] #double check # bug check??????
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Unassigned'
                            self.wq=None #8.21H-4
                            self.last_action_is_for_workstation=False #8.21H-4
                            self.AgvSubState='InWaitCmdStatus'
                            self.enter_unassigned_state_time=time.time()
                                
                    elif self.AgvState == 'Enroute':
                        #if self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.current_route and not self.adapter.is_moving): #????  need cancel it
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '')

                        if self.change_target:
                            print('change target')
                            self.change_target=False
                            self.adapter.planner.clean_route()
                            self.wait_stop=True
                            # self.execute_action()
                            ###### execute new action
                            continue

                        if self.wait_stop and not self.adapter.occupied_route:
                            print('reroute')
                            self.wait_stop=False
                            self.execute_action()
                            continue

                        if (self.stop_command and not self.adapter.cmd_sending) or (self.emergency_evacuation_cmd and not self.emergency_evacuation_stop and self.AgvLastState !='Evacuation'): #8.21N-6:
                            self.adapter.vehicle_stop() #blocking
                            
                            #self.stop_command=False
                            self.no_begin=True
                            
                            if self.emergency_evacuation_cmd:
                                self.emergency_evacuation_stop=True
                                self.AgvState='Parked'
                                continue
                            else:
                                raise alarms.BaseReplaceJobWarning(self.id, local_tr_cmd.get('uuid', ''), target) #20211001 chocp fix

                        #if self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.current_route and not self.adapter.is_moving): #????  need cancel it
                        if self.adapter.move['obstacles']: #chi 22/05/04 check obstacles when Enroute
                            now_time=time.time()
                            if now_time - self.adapter.move['into_obstacles'] > self.warningBlockTime and not self.adapter.cmd_sending: #3min
                                self.adapter.move['obstacles']=False
                                alarms.MoveRouteObstaclesWarning(self.id, local_tr_cmd.get('uuid', ''))

                                if self.autoReroute == 'yes': # Mike: 2022/08/20
                                    self.reroute()

                        #dangeous, will have a bug
                        if (self.adapter.move['arrival'] == 'EndArrival' or (not self.adapter.planner.occupied_route and not self.adapter.planner.current_route and not self.adapter.planner.is_moving))\
                            and self.adapter.move['status'] == 'Idle': #chocp 8/30

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'
                            self.at_station=target
                            
                            self.alarm_edge=[]
                            self.alarm_node=[]

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
                                        'CommandID':local_tr_cmd.get('uuid', ''),
                                        'VehicleState':self.AgvState,
                                        'Message':self.message,
                                        'ForceCharge':self.force_charge,
                                        'TransferPort':target,
                                        'ResultCode':0}) #chocp fix

                            print('>>> check ', self.adapter.last_point, PortsTable.reverse_mapping[self.adapter.last_point])
                            for target in PortsTable.reverse_mapping[self.adapter.last_point]:
                                if target in self.secsgem_e88_h.Ports.Data:
                                    port=self.secsgem_e88_h.Ports.Data[target]
                                    idx=PortsTable.mapping[target][6]-1
                                    if port.PortBook and self.adapter.carriers[idx]['port'] == 'ReadyToLoad':
                                        EqMgr.getInstance().trigger(target, 'ready_to_load_evt', {})

                                    if self.adapter.carriers[idx]['port'] == 'ReadyToUnload':
                                        EqMgr.getInstance().trigger(target, 'ready_to_unload_evt', {})
                                        
                            if self.emergency_evacuation_cmd and self.at_station in self.standby_station:
                                raise alarms.EmergencyEvacuationWarning(self.id)

                    elif self.AgvState == 'TrUnLoadReq': # ReadyToUnload
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        #need check position
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        command_id=local_tr_cmd.get('uuid', '') #chocp 2022/4/14
                        carrierID=local_tr_cmd.get('carrierID', '') #chocp 2022/4/14
                        port=PortsTable.mapping[target]
                        idx=port[6]-1

                        for port in PortsTable.reverse_mapping[self.adapter.last_point]:
                            idx=PortsTable.mapping[port][6]-1
                            if self.adapter.carriers[idx]['port'] == 'TransferBlocked':
                                self.action_in_run['target']=port

                                EqMgr.getInstance().trigger(port, 'transfer_block_evt', {})

                                self.enter_acquiring_state()
                                continue

                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrUnLoadReqTimeout', 0)

                        if self.TrUnLoadReqTime and (time.time()-self.TrUnLoadReqTime > pending_timeout):
                            self.goTrUnLoadReq=0
                            self.ControlPhase='GoUnassigned'

                            time.sleep(1) #???
                            print('To GoUnassigned:')

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

                            E88.report_event(self.secsgem_e88_h,
                                        E88.CraneIdle,{
                                        'StockerCraneID':self.id,
                                        'CommandIDList':self.CommandIDList,
                                        'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})

                            print('Unassigned',self.CommandIDList)
                            self.CommandIDList=[]
                            self.action_in_run={}
                            #self.tr_cmds=[] #double check # bug check??????
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Unassigned'
                            self.wq=None #8.21H-4
                            self.last_action_is_for_workstation=False #8.21H-4
                            self.AgvSubState='InWaitCmdStatus'
                            self.enter_unassigned_state_time=time.time()


                    elif self.AgvState == 'Acquiring': # Unloading
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        port=PortsTable.mapping[target]
                        idx=port[6]-1

                        if self.adapter.carriers[idx]['port'] == 'ReadyToLoad':
                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass

                            if target in self.secsgem_e88_h.Ports.Data:
                                self.secsgem_e88_h.Ports.Data[target].PortBook=False

                            self.AgvLastState=self.AgvState
                            self.AgvState='Parked'

                            EqMgr.getInstance().trigger(target, 'ready_to_load_evt', {})

                            output('VehicleAcquireCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], 
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':command_id,
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target,
                                    'CarrierID':local_tr_cmd['carrierID'], #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':self.action_in_run['loc'],
                                    'ResultCode':0}) #chocp fix

                            self.LastAcquireTarget=target

                            # EqMgr.getInstance().trigger(target, 'acquire_complete_evt', {'vehicleID':self.id, 'carrierID':local_tr_cmd['carrierID']})

                    elif self.AgvState == 'TrLoadReq': # ReadyToLoad
                        #need check position
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        command_id=local_tr_cmd.get('uuid', '') #chocp 2022/4/14
                        carrierID=local_tr_cmd.get('carrierID', '') #chocp 2022/4/14
                        port=PortsTable.mapping[target]
                        idx=port[6]-1

                        for port in PortsTable.reverse_mapping[self.adapter.last_point]:
                            idx=PortsTable.mapping[port][6]-1
                            if self.adapter.carriers[idx]['port'] == 'TransferBlocked':
                                self.action_in_run['target']=port

                                EqMgr.getInstance().trigger(port, 'transfer_block_evt', {})

                                self.enter_depositing_state()
                                continue

                        pending_timeout=local_tr_cmd.get('TransferInfo', {}).get('ExecuteTime', 0)
                        if not pending_timeout:
                            pending_timeout=global_variables.TSCSettings.get('Safety',{}).get('TrLoadReqTimeout', 0)

                        if self.TrLoadReqTime and (time.time()-self.TrLoadReqTime > pending_timeout):
                            for port in PortsTable.reverse_mapping[self.adapter.last_point]:
                                if port in self.secsgem_e88_h.Ports.Data:
                                    self.secsgem_e88_h.Ports.Data[port].PortBook=False

                            self.ControlPhase='GoUnassigned'

                            time.sleep(1) #???
                            print('To GoUnassigned:')

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

                            E88.report_event(self.secsgem_e88_h,
                                        E88.CraneIdle,{
                                        'StockerCraneID':self.id,
                                        'CommandIDList':self.CommandIDList,
                                        'CommandID':self.CommandIDList[0] if self.CommandIDList else ''})

                            print('Unassigned',self.CommandIDList)
                            self.CommandIDList=[]
                            self.action_in_run={}
                            #self.tr_cmds=[] #double check # bug check??????
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Unassigned'
                            self.wq=None #8.21H-4
                            self.last_action_is_for_workstation=False #8.21H-4
                            self.AgvSubState='InWaitCmdStatus'
                            self.enter_unassigned_state_time=time.time()

                    elif self.AgvState == 'Depositing': # Loading
                        if self.emergency_evacuation_cmd and self.emergency_situation == 'EarthQuake': # FireDisaster  EarthQuake
                            raise alarms.EmergencyEvacuationWarning(self.id)

                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        port=PortsTable.mapping[target]
                        idx=port[6]-1

                        if self.adapter.carriers[idx]['port'] == 'ReadyToUnload':
                            # elif self.adapter.robot['finished'] == 'Finished' and self.adapter.robot['status'] == 'Idle':
                            try: #chocp:2021/6/22
                                if self.action_in_run == self.actions[0]: #if same obj do pop to avoid pop other valid action #chocp 2022/7/11
                                    self.actions.popleft()
                            except:
                                pass

                            if target in self.secsgem_e88_h.Ports.Data:
                                self.secsgem_e88_h.Ports.Data[target].PortBook=False

                            self.AgvLastState=self.AgvState
                            self.AgvState='Parked'

                            '''port=self.secsgem_e88_h.Ports.Data[target]
                            port.PortBook=False
                            port.transfer_block()
                            print(">>> transfer_block", target)'''
                            EqMgr.getInstance().trigger(target, 'transfer_block_evt', {})

                            output('VehicleDepositCompleted', {
                                    'Battery':self.adapter.battery['percentage'],
                                    'Charge':self.adapter.battery['charge'], #chocp 2022/5/20
                                    'Connected':self.adapter.online['connected'],
                                    'Health':self.adapter.battery['SOH'],
                                    'MoveStatus':self.adapter.move['status'],
                                    'RobotStatus':self.adapter.robot['status'],
                                    'RobotAtHome':self.adapter.robot['at_home'],
                                    'VehicleID':self.id,
                                    'CommandID':local_tr_cmd.get('uuid', ''),
                                    'VehicleState':self.AgvState,
                                    'Message':self.message,
                                    'TransferPort':target,
                                    'CarrierID':self.bufs_status[idx]['stockID'], #chocp fix for tfme 2021/10/23
                                    'CarrierLoc':'{}BUF{:02d}'.format(self.id, idx+1),
                                    'ResultCode':0})

                    elif self.AgvState == 'Charging':
                        if self.emergency_evacuation_cmd:
                            self.AgvState='Evacuation'
                            continue
                        local_tr_cmd=self.action_in_run.get('local_tr_cmd', {})
                        target=self.action_in_run.get('target', '') #chocp add for assist close door 2022/10/27
                        end_charge=False
                        #chocp fix end_charge=True from pause

                        if self.ChargeSafetyCheck == 'yes': #chi 2023/02/09
                            if time.time() - self.charge_start_time > self.ChargeTimeMax:
                                raise alarms.ChargeCommandTimeTooLongWarning(self.id, local_tr_cmd.get('uuid', ''), self.at_station)

                        if self.adapter.battery['charge']: #chocp fix 2022/6/1
                            start_charge=True
                        elif start_charge and not self.adapter.battery['charge']: #chocp fix 2022/6/1
                            start_charge=False
                            end_charge=True
                            #trigger a warning
                            alarms.ChargeCommandBreakOffWarning(self.id, local_tr_cmd.get('uuid', ''), self.at_station) #chocp 2022/6/29
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

                            '''E82.report_event(self.secsgem_e88_h,
                                                E82.VehicleChargeCompleted, {
                                                'VehicleID':self.id}) #chocp 9/28 for tfme'''

                            E88.report_event(self.secsgem_e88_h,
                                                E88.CraneInService,{
                                                'StockerCraneID':self.id})

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
                                    'CommandID':local_tr_cmd.get('uuid', ''),
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

                        elif end_charge:
                            if self.adapter.battery['percentage'] > self.ChargeBelowPower: # Mike: 2022/12/07
                                self.force_charge=False
                            end_charge=False

                            '''E82.report_event(self.secsgem_e88_h,
                                                E82.VehicleExchangeCompleted, {
                                                'VehicleID':self.id}) #chocp 9/28 for tfme'''

                            E88.report_event(self.secsgem_e88_h,
                                                E88.CraneInService,{
                                                'StockerCraneID':self.id})

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
                                    'CommandID':local_tr_cmd.get('uuid', ''),
                                    'TransferPort':target,
                                    'ResultCode':0})
                            #bug
                            #self.tr_cmds=[] #double check #bug................
                            self.tr_cmd_assign_timeout=0 #chocp 8/21

                            self.actions.clear() #double check
                            self.action_in_run={} #double check

                            self.AgvLastState=self.AgvState  #fix 8/20
                            self.AgvState='Parked'
    
            except alarms.MyException as alarm_instance:
                traceback.print_exc()

                self.alarm_handler(alarm_instance) #test
                time.sleep(1)
            
            except:
                traceback.print_exc()
                sub_code=traceback.format_exc()
                alarm_instance=alarms.VehicleInternalWarning(self.id, sub_code) #chocp fix 2021/11/26
                #self.alarm_handler('Removed')
                self.alarm_handler(alarm_instance)
                time.sleep(1)
        else:
            #self.adapter.stop=True #chocp:2021/3/9
            self.AgvState='Removed'
            # ActiveVehicles[self.id]["VehicleInfo"]["VehicleState"]=1
            # E82.update_variables(self.secsgem_e88_h, {'ActiveVehicles': ActiveVehicles})
            for carrier in self.adapter.carriers:
                self.secsgem_e88_h.carrier_kill(carrier['status'])
            datasets={}
            datasets['ZoneSize']=0
            datasets['ZoneCapacity']=0
            self.secsgem_e88_h.Zones.Data[self.id].zone_capacity_change(datasets['ZoneCapacity'])
            self.secsgem_e88_h.Zones.delete(self.id)
            self.adapter.logger.info('{} {}'.format('[{}] '.format(self.id), 'end vehicle thread'))
