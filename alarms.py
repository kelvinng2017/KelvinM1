import traceback
import time
import alarms
from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E82_Host
from semi.SecsHostMgr import E88_STK_Host
from global_variables import output
import collections
import json
import os

class MyException(Exception):
    def __init__(self, level, code, sub_code, txt):
        self.level=level
        self.code=code
        self.sub_code=sub_code
        self.txt=txt
        self.alsv=''

        #self.extend_code='' #for UI
        self.more_txt='' #for UI
        self.command_id=''
        

    def notify(self, arg, args={}, handler=None):
        alsv_str=''
        param=[]
        params=[]
        new_sub_code=self.sub_code

        if not handler:
            handler=E82_Host.getInstance()
            print('Not set secsgem handler in alarm exception, use default')
         
        if not self.sub_code or self.sub_code == '0':
            new_sub_code=str(self.code)
            
        key_list=[]     
        for key, value in args.items():
            try:
                key_list.append(key)
                if handler.MDLN =='v3_MIRLE':
                    VehicleInfo={"VehicleID": '', "VehicleState": 0}
                    setattr(handler,'VehicleInfo', VehicleInfo)
                    setattr(handler,'CommandID', '')
                    setattr(handler,'CarrierID', '')
                    setattr(handler,'CarrierLoc', '')
                    #if key == 'VehicleID' and str(list(arg.value())[0]) != 'Vehicle':
                    if key == 'VehicleID':
                        VehicleInfo={"VehicleID": value, "VehicleState": 4}
                        setattr(handler,'VehicleInfo', VehicleInfo)
                    if key == 'CommandID':
                        setattr(handler,'CommandID', value)
                        self.command_id=value
                    if key == 'CarrierID':
                        setattr(handler,'CarrierID', value)
                    if key == 'CarrierLoc':
                        setattr(handler,'CarrierLoc', value)
                else:
                    if key == 'CommandID':
                        self.command_id=value
                    setattr(handler, key, value)
                    param.append(str(key) +':'+ str(value))
                    if key!='CommandID':
                        params.append(str(key) +': '+ str(value))
            except:
                traceback.print_exc()
                pass

        if self.code in [10001, 40000]: #Chi 2022/06/29
            detail=self.sub_code
            self.sub_code='TSC000'
            new_sub_code=self.sub_code
            setattr(handler, 'SubCode', self.sub_code)
            param.append('SubCode:'+ self.sub_code)
        elif not self.sub_code or self.sub_code == '0':
            detail=self.txt
            setattr(handler, 'SubCode', new_sub_code)
            param.append('SubCode:'+ new_sub_code)
        else:
            detail=get_sub_error_msg(self.sub_code)  #Chi 2022/06/24
            setattr(handler, 'SubCode', self.sub_code)
            param.append('SubCode:'+ self.sub_code)
        
        unit_type='' #for py 3.8
        unit_id='' #for py 3.8
        
        
        try:
            unit_type, unit_id=list(arg.items())[0]
            #self.extend_code=unit_id
            param.append('UnitType:'+str(unit_type))
            param.append('UnitID:'+str(unit_id))
            param.append('Level:'+str(self.level))
            setattr(handler, 'UnitType', unit_type)
            setattr(handler, 'UnitID', unit_id)
            setattr(handler, 'Level', self.level)
        except:
            pass

        alsv_str=', '.join(param)
        cause_str=', '.join(params)

        #setattr(handler, 'ALTX', self.txt+','+self.sub_code+','+get_sub_error_msg(self.sub_code))
        setattr(handler, 'ALTX', self.txt+','+ get_sub_error_msg(self.sub_code))
        setattr(handler, 'ALSV', alsv_str)
        setattr(handler, 'ALID', self.code)
        self.alsv=key_list


        if self.level!='Info': #chocp add 2022/10/17
            handler.set_alarm(self.code, self.level)

        if self.level == 'Warning':
            time.sleep(0.1)
            handler.clear_alarm(self.code, self.level)

        self.more_txt='[CommandID]: {} . [Cause]: {} . [Detail]: {} . [Params]: {}'.format(self.command_id, self.txt, detail, cause_str) #Chi 2022/06/24
        output('AlarmSet', {'UnitType':unit_type, 'UnitID':unit_id, 'Level':self.level, 'Code':self.code, 'SubCode':new_sub_code, 'CommandID':self.command_id, 'Cause':self.txt, 'Detail':detail, 'Params': cause_str, 'Description':self.more_txt}) 
        

class TSCInternalWarning(MyException):
    def __init__(self, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10000, sub_code, 'TSC internal error or code exception')  #chocp 2021/11/26
        self.notify({'Tsc':'Tsc'}, handler=handler)

class VehicleInternalWarning(MyException):
    def __init__(self, vehicleID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10001, sub_code, 'Vehicle internal error or code exception') #2021/11/26
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID}), handler=handler)
    
class TscActionGenWarning(MyException):
    def __init__(self, vehicleID, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10002, sub_code, 'Vehicle generate action fail or no buffer left') #2021/11/26
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class BaseRobotWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10003, sub_code, 'Robot status error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseMoveWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10004, sub_code, 'MR move status error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseRouteWarning(MyException):
    def __init__(self, vehicleID, commandID, from_point, to_point, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10005, sub_code, 'MR route error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'SourcePort':from_point, 'DestPort':to_point}), handler=handler)

class BaseOffLineWarning(MyException):
    def __init__(self, vehicleID, commandID, sub_code='0', handler=None): #test
        MyException.__init__(self, 'Error', 10006, sub_code, 'MR offline') #test
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class BaseOffLineNotifyWarning(MyException):
    def __init__(self, vehicleID, commandID, sub_code='TSC001', handler=None): #test
        MyException.__init__(self, 'Warning', 10006, sub_code, 'MR offline') #test
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class BaseRobotInterlockWarning(MyException):#2023/01/13 for FST
    def __init__(self, vehicleID, commandID, portID, alarmlevel, sub_code='0', handler=None):
        MyException.__init__(self, alarmlevel, 10007, sub_code, 'interlock error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)
class BaseSourceInterlockWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC029', handler=None):
        MyException.__init__(self, 'Error', 10007, sub_code, 'interlock error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseDestInterlockWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC030', handler=None):
        MyException.__init__(self, 'Error', 10007, sub_code, 'interlock error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseShiftInterlockWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC032', handler=None):
        MyException.__init__(self, 'Error', 10007, sub_code, 'interlock error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

# class BaseRobotInterlockWarning(MyException):
#     def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
#         MyException.__init__(self, 'Error', 10007, sub_code, 'interlock error')
#         self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseNotAutoModeWarning(MyException):#need add commandID
    def __init__(self, vehicleID, commandID, alarmlevel, sub_code='0', handler=None):
        MyException.__init__(self, alarmlevel, 10008, sub_code, 'MR not in auto mode')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class BaseOtherAlertWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10009, sub_code, 'MR with other alert')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class GetRouteTimeoutWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='900001', handler=None):
        MyException.__init__(self, 'Error', 10009, sub_code, 'MR with other alert')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class OperateManualTestWarning(MyException): #chocp, 2021/11/29
    def __init__(self, vehicleID, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10010, sub_code, 'TSC in manual test')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class FaultRackFullWarning(MyException):
    def __init__(self, vehicleID, commandID, eRackID, sub_code='0', handler=None):
        #MyException.__init__(self, 'Error', 10011, sub_code, 'Fault Rack full or allocate fail')
        MyException.__init__(self, 'Serious', 10011, sub_code, 'Fault Rack full or allocate fail') #chocp 2022/8/30
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'RackID':eRackID}), handler=handler)

class SelectRackWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10012, sub_code, 'Select rack or allocate fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler) #need fix secs spec


class PortNotFoundWarning(MyException):
    def __init__(self, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10013, sub_code, 'Port to point not found')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'PortID':portID}), handler=handler)

class PointNotInMapWarning(MyException):
    def __init__(self, pointID, sub_code='TSC024', handler=None):
        MyException.__init__(self, 'Serious', 10013, sub_code, 'Port to point not found')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'PortID':pointID}), handler=handler)



class ErackSyntaxWarning(MyException): #fix 6
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10014, sub_code, 'Erack syntax error')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'RackID':eRackID}), handler=handler)


class PortNotReachWarning(MyException): 
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10015, sub_code, 'Safety check, MR not reach to port')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler) #need fix secs spec

class EqUnLoadCheckFailWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC002', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)

class EqLoadCheckFailWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC027', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)

class EqBackCheckFailWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC028', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)
class EqShiftCheckFailWarning(MyException):# kelvinng 2024/11/04 TrShiftCheck    
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC035', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)

class EqShiftCheckTimeoutWarning(MyException):# kelvinng 2024/11/04 TrShiftCheck    
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC036', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)
class EqCheckTimeoutWarning(MyException):    
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC003', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)

class EqDoorReqFailWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC031', handler=None):
        MyException.__init__(self, 'Error', 10016, sub_code, 'Safety check, Eq port check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID}), handler=handler)

class RackAcquireCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, carrierID, sub_code='TSC004', handler=None):
        MyException.__init__(self, 'Error', 10017, sub_code, 'Safety check fail, erack check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID, 'CarrierID':carrierID}), handler=handler)


class RackEmptyCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID,  carrierID, sub_code='TSC005', handler=None):
        MyException.__init__(self, 'Warning', 10017, sub_code, 'Safety check fail, erack check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID, 'CarrierID':carrierID}), handler=handler)

class RackDepositCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, carrierID, sub_code='TSC006', handler=None):
        MyException.__init__(self, 'Serious', 10017, sub_code, 'Safety check fail, erack check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID, 'CarrierID':carrierID}), handler=handler)

class TurnTableCheckWarning(MyException): #8.22H
    def __init__(self, vehicleID, commandID, portID, carrierID, sub_code='TSC020', handler=None):
        MyException.__init__(self, 'Serious', 10017, sub_code, 'Safety check fail, erack check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID, 'CarrierID':carrierID}), handler=handler)

class RackAcquireCheckCarrierIDWarning(MyException): #8.28.7
    def __init__(self, vehicleID, commandID, portID, carrierID, sub_code='TSC022', handler=None):
        MyException.__init__(self, 'Error', 10017, sub_code, 'Safety check fail, erack check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':portID, 'CarrierID':carrierID}), handler=handler)

class BufferAcquireCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC007', handler=None):
        MyException.__init__(self, 'Error', 10018, sub_code, 'Safety check fail, buffer check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BufferDepositCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC008', handler=None):
        MyException.__init__(self, 'Error', 10018, sub_code, 'Safety check fail, buffer check fail')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BaseCarrPosErrWarning(MyException):
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC009', handler=None):
        MyException.__init__(self, 'Serious', 10018, sub_code, 'Safety check fail, buffer check fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)
class SwapCarrierIDErrWarning(MyException):
    def __init__(self, vehicleID, carrierID, sub_code='TSC033', handler=None):
        MyException.__init__(self, 'Serious', 10018, sub_code, 'Safety check fail, buffer check fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CarrierID':carrierID}), handler=handler)
class BaseCovertrayWarning(MyException):
    def __init__(self, vehicleID, commandID, carrierID, sub_code='TSC034', handler=None):
        MyException.__init__(self, 'Warning', 10018, sub_code, 'Safety check fail, buffer check fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID , 'CarrierID':carrierID}), handler=handler)
class BaseCarrRfidFailWarning(MyException): #chocp 2022
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 10019, sub_code, 'Buffer carrier ID read fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BaseCarrRfidConflictWarning(MyException): #8.22-1
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC021', handler=None):
        MyException.__init__(self, 'Serious', 10019, sub_code, 'Buffer carrier ID read fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BaseCarrRfiddifferentWarning(MyException): #8.22-1
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC018', handler=None):
        MyException.__init__(self, 'Error', 10019, sub_code, 'Buffer carrier ID read fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BaseCarrRfidEmptyOrNoneWarning(MyException): #richard 250430 For trigger rfid is None or different 
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='TSC037', handler=None):
        MyException.__init__(self, 'Error', 10019, sub_code, 'Buffer carrier ID read None')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)
        
class BaseCarrDupWarning(MyException):
    def __init__(self, vehicleID, commandID, buffer, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10020, sub_code, 'Buffer carrier duplicate error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID ,'PortID':buffer, 'CarrierID':carrierID}), handler=handler)

class BaseRobotCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10021, sub_code, 'Robot status check Error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class BaseMoveCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10022, sub_code, 'Move status check error')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class TransferTimeoutWarning(MyException): # need compile error code in secsgem
    def __init__(self, vehicleID, commandID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10023, sub_code, 'Transfer command timeout')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class RobotTimeoutCheckWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC010', handler=None):
        MyException.__init__(self, 'Error', 10023, sub_code, 'Transfer command timeout')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class RobotGetRightCheckWarning(MyException): # Mike: 2022/05/23
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC011', handler=None):
        MyException.__init__(self, 'Error', 10023, sub_code, 'Transfer command timeout')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)


class BaseTryStandbyFailWarning(MyException):
    def __init__(self, vehicleID, commandID, from_point, to_point, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10024, sub_code, 'MR try or select to standby station fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'SourcePort':from_point, 'DestPort':to_point}), handler=handler)

class ChargeCommandTimeoutWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC014', handler=None):
        MyException.__init__(self, 'Warning', 10025, sub_code, 'MR charge fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class ChargeCommandBreakOffWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC013', handler=None):
        MyException.__init__(self, 'Warning', 10025, sub_code, 'MR charge fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class DischargeCommandFailedWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC012', handler=None):
        MyException.__init__(self, 'Serious', 10025, sub_code, 'MR charge fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class ChargeCommandTimeTooLongWarning(MyException): #chi 2023/02/09
    def __init__(self, vehicleID, commandID, portID, sub_code='TSC017', handler=None):
        MyException.__init__(self, 'Serious', 10025, sub_code, 'MR charge fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class CarrierTypeCheckWarning(MyException): #chocp 2021/12/26
    def __init__(self, vehicleID, commandID, carrierID, carrierType, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10026, sub_code, 'CarrierType None or Check Error for Acquire/Deposit')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'CarrierID':carrierID, 'CarrierType':carrierType}), handler=handler)

class MoveRouteObstaclesWarning(MyException): #chi 2022/04/26
    def __init__(self, vehicleID, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 10027, sub_code, 'MR move with route obstacles')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID }), handler=handler)

class BaseTryChargeFailWarning(MyException):
    def __init__(self, vehicleID, commandID, from_point, to_point, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10028, sub_code,  'MR try or select to charge station fail')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'SourcePort':from_point, 'DestPort':to_point}), handler=handler)


class BaseReplaceJobWarning(MyException): #2022/10/17
    def __init__(self, vehicleID, commandID,  portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Info', 10029, sub_code,  'Stop MR command to replace new job')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class NoAvailableCarrierWarning(MyException): # Mike: 2022/12/05
    def __init__(self, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 10030, sub_code, 'No available carrier.')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'PortID':portID}), handler=handler)

class HostStopMRWarning(MyException): # Chi: 2023/03/15
    def __init__(self, vehicleID, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10031, sub_code, 'MR Stop with host command')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID}), handler=handler)

class BaseOtherWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code, handler=None):
        MyException.__init__(self, 'Warning', 10032, sub_code, 'MR with other warning')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)

class EmergencyEvacuationWarning(MyException):
    def __init__(self, vehicleID, sub_code='0', handler=None):
        MyException.__init__(self, 'Serious', 10033, sub_code, 'MR with emergency evacuation')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID}), handler=handler)

class ActionNotSupportWarning(MyException):
    def __init__(self, vehicleID, commandID, portID, sub_code='', handler=None):
        MyException.__init__(self, 'Error', 10034, sub_code, 'Action not support')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID, 'CommandID':commandID, 'PortID':portID}), handler=handler)
class FaultCarrierWarning(MyException):
    def __init__(self,vehicleID, commandID, portID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 10035, sub_code, 'Fault carrier on MR')
        self.notify({'Vehicle':vehicleID}, collections.OrderedDict({'VehicleID':vehicleID,'CommandID':commandID,'CarrierLoc':portID, 'CarrierID':carrierID}), handler=handler)

class SCInternalWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20001, sub_code, 'SC internal error or code exception')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class BaseSCCarrRfidFailWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20002, sub_code, 'Base read rfid error')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID, 'CarrierLoc':portID}), handler=handler)

class BaseE84ErrorWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20003, sub_code, 'E84 error')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID, 'CarrierLoc':portID}), handler=handler)

class BaseSCOffLineWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20004, sub_code, 'Erack offline')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class BasePortNotAutoModeWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, portID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20005, sub_code, 'Erack Port in manual mode')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID, 'CarrierLoc':portID}), handler=handler)


class ErackOffLineWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 20051, sub_code, 'Erack offline')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'RackID':eRackID}), handler=handler)

class ErackLevelHighWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 20052, sub_code, 'Erack water level high')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class ErackLevelFullWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 20053, sub_code, 'Erack water level full')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class ErackLevelLowWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 20054, sub_code, 'Erack water level low')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class ErackLevelEmptyWarning(MyException): #need fix secsgem
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 20055, sub_code, 'Erack water level empty')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class ErackLevelNormalWarning(MyException): #need fix secsgem ...
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 20056, sub_code, 'Erack water level normal')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)


class ConnectWarning(MyException):
    def __init__(self, eRackID, ip, port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 30001, sub_code, '{}, Rack connect:{}, port:{} fail'.format(eRackID, ip, port))
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class SocketNullStringWarning(MyException):
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 30002, sub_code, 'receive null string from socket')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class LinkLostWarning(MyException):
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 30003, sub_code, 'linking timeout')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class SocketFormatWarning(MyException):
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 30004, sub_code, 'receive format error from socket')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'ZoneName':eRackID}), handler=handler)

class SCSyntaxWarning(MyException):
    def __init__(self, eRackID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 30005, sub_code, 'Erack syntax error')
        self.notify({'Rack':eRackID}, collections.OrderedDict({'RackID':eRackID}), handler=handler)


class CommandExceptionWarning(MyException): #need fix secsgem
    def __init__(self, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40000, sub_code, 'Host transfer cmd parse get exception')
        self.notify({'Command': 'Unknown'}, handler=handler)

#warning ....
class CommandCanceledWarning(MyException):
    def __init__(self, trigger, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40001, sub_code, 'Transfer command in waiting queue be canceled')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'CommandID':commandID, 'Trigger': trigger}), handler=handler)

class CommandAbortWarning(MyException):
    def __init__(self, trigger, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40002, sub_code, 'Transfer command in exectuing queue be aborted')
        self.notify({'Tsc':'Tsc'}, collections.OrderedDict({'CommandID':commandID, 'Trigger': trigger}), handler=handler)

        
#end warning
class CommandIDDuplicatedWarning(MyException): #need fix secsgem
    def __init__(self, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40007, sub_code, 'Host transfer cmd, commandID duplicated in active transfers')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID}), handler=handler)

class CommandDestPortChangedWarning(MyException): #need fix secsgem
    def __init__(self, commandID, dest_port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40008, sub_code, 'Host change cmd, go to new dest port due to TrLoad request NG')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'DestPort':dest_port}), handler=handler)

class CommandCarrierTypeNoneWarning(MyException): #chocp 2021/12/26
    def __init__(self, commandID, carrierID, carrierType, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40009, sub_code, 'Host transfer cmd, CarrierType None or Error')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID, 'CarrierType':carrierType}), handler=handler)

class CommandSourceErackCarrierTypefailWarning(MyException): #8.22-1
    def __init__(self, commandID, carrierID, carrierType, source_port, validSlotType, sub_code='TSC019', handler=None):
        MyException.__init__(self, 'Warning', 40009, sub_code, 'Host transfer cmd, CarrierType None or Error') #2023/12/29 chocp
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID, 'CarrierType':carrierType, 'SourcePort':source_port, 'ValidSlotType':validSlotType}), handler=handler)

class CommandDestErackCarrierTypefailWarning(MyException): #8.22-1
    def __init__(self, commandID, carrierID, carrierType, dest_port, validSlotType, sub_code='TSC023', handler=None):
        MyException.__init__(self, 'Warning', 40009, sub_code, 'Host transfer cmd, CarrierType None or Error') #2023/12/29 chocp
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID, 'CarrierType':carrierType, 'DestPort':dest_port, 'ValidSlotType':validSlotType}), handler=handler)

class CommandCarrierNotInWhiteListWarning(MyException): #chocp 2021/12/26
    def __init__(self, commandID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40010, sub_code, 'Host transfer cmd, CarrierID not in white list')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID}), handler=handler)

class CommandSourcePortNotFoundWarning(MyException): #need fix secsgem
    def __init__(self, commandID, source_port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40011, sub_code, 'Host transfer cmd, source port not found in map')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port}), handler=handler)

class CommandDestPortNotFoundWarning(MyException): #need fix secsgem
    def __init__(self, commandID, dest_port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40012, sub_code, 'Host transfer cmd, dest port not found in map')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'DestPort':dest_port}), handler=handler)

class CommandCarrierDuplicatedInWaitingQueueWarning(MyException): #need fix secsgem
    def __init__(self, commandID, carrierID, duplicatedcommand, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40013, sub_code, 'Host transfer cmd, carrierID duplicated in waiting queue')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID, 'DuplicatedCommand':duplicatedcommand}), handler=handler)

class CommandCarrierDuplicatedInExecutingQueueWarning(MyException): #need fix secsgem
    def __init__(self, commandID, carrierID, duplicatedcommand, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40014, sub_code, 'Host transfer cmd, carrierID duplicated in executing queue')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID, 'DuplicatedCommand':duplicatedcommand}), handler=handler)

class CommandSourcePortNullWarning(MyException):
    def __init__(self, commandID, source_port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40015, sub_code, 'Host transfer cmd, source port null')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port}), handler=handler)

class CommandCarrierLocateWarning(MyException):
    def __init__(self, commandID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40016, sub_code, 'Host transfer cmd, can not locate carrierID')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'CarrierID':carrierID}), handler=handler)

class CommandDestPortAssignFailWarning(MyException):
    def __init__(self, commandID, dest_port, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40017, sub_code, 'Host transfer cmd, dest port auto assign fail')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'DestPort':dest_port}), handler=handler)

class CommandSourcePortConflictWarning(MyException):
    def __init__(self, commandID, source_port, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40018, sub_code, 'Host transfer cmd, source port conflict with specified carrier')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port, 'CarrierID':carrierID}), handler=handler)

class CommandDestPortDuplicatedWarning(MyException):
    def __init__(self, commandID, dest_port, duplicatedcommand, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40019, sub_code, 'Host transfer cmd, dest port duplicated with other cmd')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'DestPort':dest_port, 'DuplicatedCommand':duplicatedcommand}), handler=handler)

class CommandSourcetPortDuplicatedWarning(MyException): #chi 2023/02/16
    def __init__(self, commandID, source_port, duplicatedcommand, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40020, sub_code, 'Host transfer cmd, source port duplicated with other cmd')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port, 'DuplicatedCommand':duplicatedcommand}), handler=handler)

class CommandSpecifyWarning(MyException): #chi 2024/04/09
    def __init__(self, commandID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40021, sub_code, 'Host transfer cmd, can not specify MR')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID}), handler=handler)

class CommandSourcePortDisable(MyException): #Hshuo 20240611
    def __init__(self, commandID, source_port, sub_code='TSC025', handler=None):
        MyException.__init__(self, 'Warning', 40022, sub_code, 'Host transfer cmd, loadport disabled')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port}), handler=handler)
 
class CommandDestPortDisable(MyException): #Hshuo 240802
    def __init__(self, commandID, dest_port, sub_code='TSC026', handler=None):
        MyException.__init__(self, 'Warning', 40022, sub_code, 'Host transfer cmd, loadport disabled')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'DestPort':dest_port}), handler=handler)

class CommandZoneDisable(MyException): #Hshuo 20240611 
    def __init__(self, commandID, zoneid, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40023, sub_code, 'Host transfer cmd, service zone disabled')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'ZoneID':zoneid}), handler=handler)
class CommandSourceLocationMismatchWarning(MyException):
    def __init__(self, commandID, source_port, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 40024, sub_code, 'Host transfer cmd, carrier source port mismatch')
        self.notify({'Command': commandID}, collections.OrderedDict({'CommandID':commandID, 'SourcePort':source_port, 'CarrierID':carrierID}), handler=handler)


class ABCSWithAlarmWarning(MyException):
    def __init__(self, ABCSID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50051, sub_code, 'ABCS with alarms')
        self.notify({'Iot':ABCSID}, collections.OrderedDict({'DeviceID':ABCSID}), handler=handler)

class ABCSLinkLostWarning(MyException):
    def __init__(self, ABCSID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50052, sub_code, 'ABCS linking timeout')
        self.notify({'Iot':ABCSID}, collections.OrderedDict({'DeviceID':ABCSID}), handler=handler)

class ABCSConnectFailWarning(MyException):
    def __init__(self, ABCSID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50053, sub_code, 'ABCS Connect fail')
        self.notify({'Iot':ABCSID}, collections.OrderedDict({'DeviceID':ABCSID}), handler=handler)

class ELVWithAlarmWarning(MyException):
    def __init__(self, ELVID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50061, sub_code, 'Elevator with alarms')
        self.notify({'Iot':ELVID}, collections.OrderedDict({'DeviceID':ELVID}), handler=handler)

class ELVLinkLostWarning(MyException):
    def __init__(self, ELVID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50062, sub_code, 'Elevator linking timeout')
        self.notify({'Iot':ELVID}, collections.OrderedDict({'DeviceID':ELVID}), handler=handler)

class ELVConnectFailWarning(MyException):
    def __init__(self, ELVID, sub_code='0', handler=None):
        MyException.__init__(self, 'Error', 50063, sub_code, 'Elevator Connect fail')
        self.notify({'Iot':ELVID}, collections.OrderedDict({'DeviceID':ELVID}), handler=handler)


#for temp
class RtdOrderIdDuplicatedInList(MyException): #need fix secsgem
    def __init__(self, workID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 60000, sub_code, 'Host order rtd cmd, workID duplicate in worklist')
        self.notify({'Command': workID}, collections.OrderedDict({'CommandID':workID}), handler=handler)

class RtdOrderCarrierDuplicatedInList(MyException): #need fix secsgem
    def __init__(self, workID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 60001, sub_code, 'Host order rtd cmd, carrier duplicate in worklist')
        self.notify({'Command': workID}, collections.OrderedDict({'CommandID':workID, 'CarrierID':carrierID}), handler=handler)

class RtdOrderCarrierLocateWarning(MyException):
    def __init__(self, workID, carrierID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 60002, sub_code, 'Host order rtd cmd, can not locate carrier')
        self.notify({'Command': workID}, collections.OrderedDict({'CommandID':workID, 'CarrierID':carrierID}), handler=handler)

class RtdOrderCarrierNull(MyException): #need fix secsgem
    def __init__(self, workID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 60003, sub_code, 'Host order rtd cmd, carrier ID can not null')
        self.notify({'Command': workID}, collections.OrderedDict({'CommandID':workID}), handler=handler)

class RtdOrderDispatchFailWarning(MyException): #need fix secsgem
    def __init__(self, workID, carrierID, machineID, sub_code='0', handler=None):
        MyException.__init__(self, 'Warning', 60004, sub_code, 'Host order rtd cmd, dest port dispatch fail')
        self.notify({'Command': workID}, collections.OrderedDict({'CommandID':workID, 'CarrierID':carrierID, 'DestPort':machineID}), handler=handler)


sub_error_code_msg_map={
    "0":'',
}

for root, dirs, files in os.walk('alarm_code/'):
    for file in files:
        with open(os.path.join(root, file),'r') as f:
            data = json.load(f)
            sub_error_code_msg_map.update(data)

def get_sub_error_msg(sub_code): #chocp fix ti hex code
    try:
        return sub_error_code_msg_map[sub_code]
    except:
        #return '{}'.format(sub_code)
        return '{}'.format('Can not decode the SubCode, '+ sub_code) #Chi 2022/06/24



if __name__ == '__main__':

    print( get_sub_error_msg(200090) )
    print( get_sub_error_msg(0) )
    print( get_sub_error_msg(14) )
