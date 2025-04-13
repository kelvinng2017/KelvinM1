import threading
import queue
import logging
import traceback
import time
from semi.SecsHostMgr import E88_STK_Host
from semi.SecsHostMgr import E82_Host

from vehicles.vehicle import Vehicle
from vehicles.transporter import Transporter
from global_variables import output
import ctypes


class VehicleMgr(threading.Thread):
    __instance=None

    @staticmethod
    def getInstance():

        if VehicleMgr.__instance == None:
            VehicleMgr()

        return VehicleMgr.__instance

    def __init__(self):

        VehicleMgr.__instance=self
        self.vehicles={}
        self.api_queue=queue.Queue()
        self.tsclogger=logging.getLogger("tsc")

        threading.Thread.__init__(self)
    def force_shutdown_thread(self, thread, timeout):
        if not thread:
            self.tsclogger.info("Force shutdown thread failed: thread is None")
            return None
        if not thread.ident:
            self.tsclogger.info("Force shutdown thread failed: {} is not started yet.".format(thread.name))
            return thread
        if not thread.is_alive():
            self.tsclogger.info("Force shutdown thread failed: {} is stopped.".format(thread.name))
        try:
            thread_id = ctypes.c_long(thread.ident)
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))

            if res == 0:
                self.tsclogger.info("Cannot find thread {}'s ID: {}".format(thread.name, thread.ident))
            elif res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
                self.tsclogger.error("[Error] Multiple threads affected, reset")
                return thread
            else:
                self.tsclogger.info("[Success] Thread {} has been forcibly terminated.".format(thread.name))
                thread.join(timeout=timeout)
                if thread.is_alive():
                    self.tsclogger.error("[Error] The thread did not terminate properly; manual inspection is recommended.")
                    return thread
        except Exception as e:
            self.tsclogger.error('{} {} '.format('force_shutdown_thread error', traceback.format_exc()))
            return thread
        
        self.tsclogger.info("[Completed] Thread object set to None.")
        return None

    #for thread
    def run(self):
        
        while(True):
            try:
                obj=None
                try:
                    obj=self.api_queue.get(timeout=1) #if none, will hold
                except:
                    vehicle_pose_status_dict={}
                    vehicle_pose_status_list=[]
                    for vehicle_id, h_vehicle in self.vehicles.items():
                        vehicle_pose_status_list.append({
                            'VehicleID': h_vehicle.id,
                            'VehicleState': h_vehicle.AgvState,
                            'Message': h_vehicle.message,
                            'AlarmCode': h_vehicle.error_code,
                            'ForceCharge': h_vehicle.force_charge,
                            'Point': h_vehicle.adapter.last_point,
                            'Station': h_vehicle.at_station,
                            'Pose': [
                                h_vehicle.adapter.move['pose']['x'],
                                h_vehicle.adapter.move['pose']['y'],
                                h_vehicle.adapter.move['pose']['h'],
                                h_vehicle.adapter.move['pose']['z']
                            ],
                            'Speed':h_vehicle.adapter.move['velocity']['speed'],#K11 Speed 20241122 kelvinng
                            'Battery': h_vehicle.adapter.battery['percentage'],
                            'Charge': h_vehicle.adapter.battery['charge'],
                            'Connected': h_vehicle.adapter.online['connected'],  # Mike: 2022/05/31
                            'Health': h_vehicle.adapter.battery['SOH'],
                            'MoveStatus': h_vehicle.adapter.move['status'],
                            'RobotStatus': h_vehicle.adapter.robot['status'],
                            'RobotAtHome': h_vehicle.adapter.robot['at_home'],
                            'Voltage': h_vehicle.adapter.battery['voltage'],
                            'Temperature': h_vehicle.adapter.battery['temperature'],
                            'Current': h_vehicle.adapter.battery['current'],
                            'RealTime': (h_vehicle.adapter.online['status'] == 'Ready'),
                            'BatteryID':h_vehicle.adapter.battery['id']
                        })
                        if h_vehicle.heart_beat > 0 and time.time() - h_vehicle.heart_beat > 60:
                            h_vehicle.heart_beat=0
                            self.tsclogger.info('{}'.format("<<<  Vehicle {} is dead. >>>".format(vehicle_id)))

                    vehicle_pose_status_dict['VehicleList']=vehicle_pose_status_list
                        
                    if vehicle_pose_status_dict:
                        output('AllVehiclePoseUpdate', vehicle_pose_status_dict)
                        continue
                
                tmp={}
                if obj and (obj['cmd'] == 'start' or obj['cmd'] == 'restart'):
                    self.tsclogger.info('{} '.format('<<< get VehicleSettings >>>'))
                    for idx, setting in enumerate(obj['config']):
                        vehicle_id=setting['vehicleID']
                        try:
                            h_vehicle=self.vehicles.pop(vehicle_id)
                        except:
                            h_vehicle=0
                        
                        if vehicle_id in tmp: # zhangpeng 2025-02-13 # Prevent duplicate creation of threads with the same vehicle id
                            continue

                        try:
                            if h_vehicle:
                                if h_vehicle.ip == setting['ip'] and h_vehicle.port == setting['port']:
                                    if setting['enable'] == 'yes':
                                        if not h_vehicle.is_alive():
                                            h_vehicle.start()
                                        self.tsclogger.info('{}'.format("<<< continue1: {} >>>".format(vehicle_id)))
                                        h_vehicle.update_params(setting)
                                        tmp[vehicle_id]=h_vehicle #end
                                        continue
                                    else:
                                        if not h_vehicle.is_alive():
                                            self.tsclogger.info('{}'.format("<<< continue2: {} >>>".format(vehicle_id)))
                                            h_vehicle.update_params(setting)
                                            tmp[vehicle_id]=h_vehicle #end
                                            continue
                                        self.tsclogger.info('{}'.format("<<< stop1: {} >>>".format(vehicle_id)))
                                        h_vehicle.thread_stop=True
                                        h_vehicle.join(5)
                                        if h_vehicle.is_alive():
                                            self.tsclogger.info('{}'.format("<<< shutdown1: {} >>>".format(vehicle_id)))
                                            self.force_shutdown_thread(h_vehicle,30)
                                        #time.sleep(5) #can't change vehicleID
                                else:
                                    self.tsclogger.info('{}'.format("<<< stop2: {} >>>".format(vehicle_id)))
                                    h_vehicle.thread_stop=True
                                    h_vehicle.join(5)
                                    if h_vehicle.is_alive():
                                        self.tsclogger.info('{}'.format("<<< shutdown2: {} >>>".format(vehicle_id)))
                                        self.force_shutdown_thread(h_vehicle,30)

                            if setting['model'] in ['Type_T']: # Mike: 2023/12/02
                                self.tsclogger.info('{}'.format("<<<  e88 transporter: {} >>>".format(vehicle_id)))
                                #dynamic assign secsgem_e88_h before create vehicle
                                secsgem_e88_h=E88_STK_Host.getInstance(vehicle_id)
                                #no obj or no thread alive
                                h_vehicle=Transporter(self, secsgem_e88_h, setting)
                            else:
                                self.tsclogger.info('{}'.format("<<< e82 vehicle: {} >>>".format(vehicle_id)))
                                #dynamic assign secsgem_e82_h before create vehicle
                                secsgem_e82_h=E82_Host.getInstance(vehicle_id)
                                #no obj or no thread alive
                                h_vehicle=Vehicle(self, secsgem_e82_h, setting)

                            if setting['enable'] == 'yes':
                                print("<<< new: {} >>>".format(vehicle_id))
                                self.tsclogger.info('{}'.format("<<< new: {} >>>".format(vehicle_id)))
                                # h_vehicle=Vehicle(setting) #avoid adapter not enable, with erack different
                                h_vehicle.name=str(vehicle_id)
                                h_vehicle.setDaemon(True)
                                h_vehicle.start()

                            tmp[vehicle_id]=h_vehicle #end
                        except:
                            self.tsclogger.error('{} {} {} '.format(vehicle_id, 'start vehicle thread error', traceback.format_exc()))
                    #residual thread need clear ....
                    for vehicle_id, h_vehicle in self.vehicles.items():
                        self.tsclogger.info('{}'.format("<<< stop3: {} >>>".format(vehicle_id)))
                        if hasattr(h_vehicle, 'thread_stop'):
                            h_vehicle.thread_stop=True
                            if h_vehicle.is_alive():
                                h_vehicle.join(5)
                                if h_vehicle.is_alive():
                                    self.tsclogger.info('{}'.format("<<< shutdown3: {} >>>".format(vehicle_id)))
                                    self.force_shutdown_thread(h_vehicle,30)
                        
                    self.vehicles=tmp
                    output('AllVehicleSettingUpdate', {'Completed': True})
            except:
                self.tsclogger.error('{} {} '.format('Vehicle mgr error', traceback.format_exc()))





            


