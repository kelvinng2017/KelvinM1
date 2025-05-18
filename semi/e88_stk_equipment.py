#####################################################################
# gem_equipment.py
#
# (c) Copyright 2016, Benjamin Parzella. All rights reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#####################################################################

import logging
import code

import secsgem

import collections

import traceback
from time import strftime
from time import localtime
from time import sleep
from datetime import datetime
#from communication_log_file_handler import CommunicationLogFileHandler

from . import E88_dataitems as DI

from global_variables import remotecmd_queue
from secsgem.common.fysom import Fysom

from datetime import datetime

import threading

#from global_variables import eRacks

#from vehicle import VehicleMgr 
#chocp 2021/1/6


#chocp add
lock=threading.Lock()
def report_event(secsgem_h, ceid, dataset={}):
    print('>> report', secsgem_h, ceid, dataset)
    lock.acquire()
    try:
        for key, value in dataset.items():
            #print(key, value)
            setattr(secsgem_h, key, value)
            
        secsgem_h.trigger_collection_events([ceid])
        #print('report_vehicle_event, ceid=%d'%ceid)
    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** report event error ***')
        getattr(secsgem_h, "communicationLogger").warn('CEID:{}, DATASET:{}'.format(ceid, dataset))
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass
        
    lock.release()
    return

def alarm_set(secsgem_h, alid, alarm_set, dataset={}):
    lock.acquire()
    try:
        for key, value in dataset.items():
            #print(key, value)
            setattr(secsgem_h, key, value)
            
        if alarm_set:
            secsgem_h.set_alarm(alid)
        else:
            secsgem_h.clear_alarm(alid)
        #print('alarm_set, alid=%d'%alid)
        sleep(0.05) #chocp 2021/11/24
    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** report event error ***')
        getattr(secsgem_h, "communicationLogger").warn('ALID:{}, SET:{}, DATASET:{}'.format(alid, alarm_set, dataset))
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass
        
    lock.release()
    return

# Mike: 2020/07/29
def get_variables(secsgem_h, key):
    lock.acquire()
    try:

        value=''
        value=getattr(secsgem_h, key)
            
    except Exception as e:
        getattr(secsgem_h, "communicationLogger").warn('*** get variables error ***')
        getattr(secsgem_h, "communicationLogger").warn(e)
        traceback.print_exc()
        pass
        
    lock.release()
    return value

# Mike: 2020/07/29
def update_variables(secsgem_h, dataset={}):
    lock.acquire()
    try:

        for key, value in dataset.items():
            #print(key, value)
            setattr(secsgem_h, key, value)
            
    except Exception as e:
        getattr(secsgem_h, "logger").warn('*** update variables error ***')
        getattr(secsgem_h, "logger").warn(e)
        traceback.print_exc()
        pass
        
    lock.release()
    return



CarrierNum=5
CommandNum=5
PortNum=5
VehicleNum=5
TransNum=5

########################
#       SVID
########################
''' basic '''
#GEM_ALARMID=1
#GEM_ESTABLISH_COMMUNICATIONS_TIMEOUT=2
GEM_ALARMS_ENABLED=3
GEM_ALARMS_SET=4
GEM_CLOCK=5
GEM_CONTROL_STATE=6
GEM_EVENTS_ENABLED=7
GEM_LINK_STATE=8
GEM_MDLN=9
GEM_SOFTREV=10

GEM_SPOOL_COUNT_ACTUAL=23
GEM_SPOOL_COUNT_TOTAL=24
GEM_SPOOL_FULL_TIME=25
GEM_SPOOL_START_TIME=27
GEM_SPOOL_STATE=28
GEM_SPOOL_UNLOAD_SUPSTATE=29


''' SV '''
SV_SCState=79 # U2: init=1, paused=2, auto=3, pausing=4
SV_EqpName=62 # A
SV_ActiveCarriers=51 # CarrierInfo*n
SV_ActiveTransfers=52 # TransferCommand*n
SV_ActiveZones=53 # ZoneData*n
SV_EnhancedCarriers=300003 # EnhancedCarrierInfo*n
SV_EnhancedTransfers=302 # EnhancedTranferCommand*n
SV_EnhancedActiveZones=303 # EnhancedZoneData*n
SV_EnhancedPortData=30001 # ZoneData*n

''' tmp sv, for events, not available '''
SV_CarrierID=54 # A
SV_CarrierInfo=55 # CarrierID, CarrierLoc
SV_CarrierLoc=56 # A
SV_CarrierType=656 # A
SV_CarrierState=604 # U2: wait_in=1, transfer=2, wait_out=3, completed=4, alternate=5
SV_CarrierZoneName=605 # A
#SV_CurrentPortStates=81 # PortID, PortTransferState 2=Normal, 1=Abnormal
SV_CommandID=58 # A
SV_CommandInfo=59 # CommandID, Priority
#SV_CommandName=57 # A
SV_CommandType=608 # A
SV_Dest=60 # A
SV_EmptyCarrier=61 # U2: empty=0, not empty=1
SV_EnhancedCarrierInfo=611 # CarrierID, CarrierLoc, CarrierZoneName, InstallTime, CarrierState
SV_EnhancedTransferCommand=612 # TransferState, CommandInfo, TransferInfo
SV_EnhancedZoneData=613 # ZoneName, ZoneCapacity, ZoneSize, ZoneType
SV_ErrorID=63 # A
SV_HandoffType=64 # U2: man=1, auto=2
SV_IDReadStatus=65 # U2: succ=0, fail=1, duplicate=2, mismatch=3
SV_InstallTime=617 # A: TIME
SV_PortID=80 # A
SV_PortType=66 # A: OP=output, BP=buffer, LP=loading
SV_Priority=67 # U2
SV_RecoveryOptions=68 # A: blank, RETRY, ABORT
SV_ResultCode=69 # U2: succ=0, cancel=1, abort=2
SV_Source=70 # A
SV_StockerCraneID=623 # A
SV_StockerUnitID=71 # A
SV_StockerUnitInfo=72 # StockerUnitID, StockerUnitState
SV_StockerUnitState=73 # U2: unknown=0, empty=1, occupied=2, error=3, manual=4
SV_TransferCommand=74 # CommandInfo, TransferInfo
SV_TransferInfo=75 # CarrierID, CarrierLoc, Dest
SV_TransferState=629 # U2: queued=1, transfering=2, paused=3, canceling=4, aborting=5
SV_ZoneCapacity=76 # U2
SV_ZoneData=77 # ZoneName, ZoneCapacity
SV_ZoneName=78 # A
SV_ZoneSize=633 # U2
SV_ZoneType=634 # U2: shelf=1, port=2, other=3
SV_ZoneState=635 # U2: UP=1, DOWN=2, other=0
SV_DeviceID=640
SV_PortIOType=641 # A

SV_ALTX=651
SV_ALSV=652
SV_UnitType=653
SV_UnitID=654
SV_Level=655
SV_SubCode=657

########################
#       CEID
########################
''' Control State '''
GEM_EQP_OFFLINE=1
GEM_CONTROL_STATE_LOCAL=2
GEM_CONTROL_STATE_REMOTE=3
GEM_CONTROL_STATE_ALARM_SET=5
GEM_CONTROL_STATE_ALARM_CLEARED=6
GEM_CONTROL_STATE_OP_EQP_CONST_CHANGE=7
GEM_CONTROL_STATE_TERMINAL_DISPLAY_CHECK=10

''' SC state transition events '''
SCAutoCompleted=12000
SCAutoInitiated=12001
SCPauseCompleted=12002
SCPaused=12003
SCPauseInitiated=12004

''' transfer command state transition events '''
TransferAbortCompleted=13000
TransferAbortFailed=13001
TransferAbortInitiated=13002
TransferCancelCompleted=13003
TransferCancelFailed=13004
TransferCancelInitiated=13005
TransferCompleted=13006
TransferInitiated=13007
TransferPaused=13008
TransferResumed=13009

''' stocker carrier state transition events '''
CarrierInstallCompleted=14000
CarrierRemoveCompleted=14001
CarrierRemoved=14002
CarrierResumed=14003
CarrierStored=14004
CarrierStoredAlt=14005
CarrierTransferring=14006
CarrierWaitOut=14007
CarrierWaitIn=14008

''' stocker crane state transition events '''
CraneActive=15000
CraneIdle=15001
CraneOutOfService=15002
CraneInService=15003

''' port transfer state transition events'''
PortInService=1500
PortOutOfService=1501
PortTransferBlocked=1502
PortReadyToLoad=1503
PortReadyToUnload=1504
PortTypeChange=1510

''' non-transition events '''
CarrierIDRead=14009
CarrierInstallFailed=14010
CarrierLocateCompleted=14011
CarrierRemoveFailed=14012
IDReadError=14013
OperatorInitiatedAction=14014
ZoneCapacityChange=14015
ShelfStatusChanged=16000

secsgem.gem.equipmenthandler.GEM_MDLN=GEM_MDLN
secsgem.gem.equipmenthandler.GEM_SOFTREV=GEM_SOFTREV
secsgem.gem.equipmenthandler.GEM_CLOCK=GEM_CLOCK
secsgem.gem.equipmenthandler.GEM_ALARMS_ENABLED=GEM_ALARMS_ENABLED
secsgem.gem.equipmenthandler.GEM_ALARMS_SET=GEM_ALARMS_SET
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE=GEM_CONTROL_STATE
secsgem.gem.equipmenthandler.GEM_LINK_STATE=GEM_LINK_STATE
secsgem.gem.equipmenthandler.GEM_EVENTS_ENABLED=GEM_EVENTS_ENABLED
secsgem.gem.equipmenthandler.GEM_EQP_OFFLINE=GEM_EQP_OFFLINE
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_LOCAL=GEM_CONTROL_STATE_LOCAL
secsgem.gem.equipmenthandler.GEM_CONTROL_STATE_REMOTE=GEM_CONTROL_STATE_REMOTE
secsgem.gem.equipmenthandler.GEM_SPOOL_COUNT_ACTUAL=GEM_SPOOL_COUNT_ACTUAL
secsgem.gem.equipmenthandler.GEM_SPOOL_COUNT_TOTAL=GEM_SPOOL_COUNT_TOTAL
secsgem.gem.equipmenthandler.GEM_SPOOL_FULL_TIME=GEM_SPOOL_FULL_TIME
secsgem.gem.equipmenthandler.GEM_SPOOL_START_TIME=GEM_SPOOL_START_TIME
secsgem.gem.equipmenthandler.GEM_SPOOL_STATE=GEM_SPOOL_STATE
secsgem.gem.equipmenthandler.GEM_SPOOL_UNLOAD_SUPSTATE=GEM_SPOOL_UNLOAD_SUPSTATE


class Carrier():
    def __init__(self, secsgem_h, CARRIERID):
        self.h=secsgem_h
        self.CarrierID=CARRIERID
        self.CarrierIDRead=''
        self.CarrierLoc=''
        self.CarrierState=0 # U2: wait_in=1, transfer=2, wait_out=3, completed=4, alternate=5
        self.CarrierZoneName=''
        self.CarrierDeviceName=''
        self.CommandID=''
        self.StockerCraneID=''
        self.Dest=''
        self.HandoffType=1 # U2: man=1, auto=2
        self.IDReadStatus=0 # U2: succ=0, fail=1, duplicate=2, mismatch=3
        self.InstallTime=''
        self.PortType='' # A: OP=output, BP=buffer, LP=loading

        #####################################
        #   control state 
        #####################################
        ''' CarrierState '''
        self.State=Fysom({
            'initial': "none",
            'events': [
                {'name': 'wait_in', 'src': ['none', 'WAIT_OUT', 'WAIT_OUT_2'], 'dst': 'WAIT_IN'},  # 1, 13
                {'name': 'transfer', 'src': ['WAIT_IN', 'COMPLETED'], 'dst': 'TRANSFERING'},  # 2, 4
                {'name': 'store', 'src': 'TRANSFERING', 'dst': 'COMPLETED'},  # 3
                {'name': 'wait_out', 'src': ['none', 'TRANSFERING', 'WAIT_OUT_2'], 'dst': 'WAIT_OUT'},  # 5, 6, 14
                {'name': 'wait_out', 'src': 'WAIT_OUT', 'dst': 'WAIT_OUT_2'},  # 6
                {'name': 'remove', 'src': ['WAIT_OUT', 'WAIT_OUT_2'], 'dst': 'none'},  # 7
                {'name': 'alternated', 'src': 'TRANSFERING', 'dst': 'ALTERNATE'},  # 8
                {'name': 'resume', 'src': 'ALTERNATE', 'dst': 'TRANSFERING'},  # 9
                {'name': 'add_carrier', 'src': 'none', 'dst': 'COMPLETED'},  # 10
                {'name': 'mod_carrier', 'src': 'COMPLETED', 'dst': 'COMPLETED'},  #
                {'name': 'kill_carrier', 'src': ['WAIT_IN', 'TRANSFERING', 'WAIT_OUT', 'WAIT_OUT_2', 'COMPLETED', 'ALTERNATE'], 'dst': 'none'},  # 11
            ],
            'callbacks': {
                'onWAIT_IN': self._on_carrier_state_WAIT_IN,  # 
                'onTRANSFERING': self._on_carrier_state_TRANSFERING,  # 
                'onWAIT_OUT': self._on_carrier_state_WAIT_OUT,  # 
                'onWAIT_OUT_2': self._on_carrier_state_WAIT_OUT,  # 
                'onCOMPLETED': self._on_carrier_state_COMPLETED,  # 
                'onALTERNATE': self._on_carrier_state_ALTERNATE,  # 
                'onbeforewait_in': self._on_carrier_state_wait_in,  # 1, send collection event (CarrierWaitIn)
                'onbeforetransfer': self._on_carrier_state_transfer,  # 2, 4, send collection event (CarrierTransferring)
                'onbeforestore': self._on_carrier_state_store,  # 3, send collection event (CarrierStored)
                'onbeforewait_out': self._on_carrier_state_wait_out,  # 5, 6, send collection event (CarrierWaitOut)
                'onbeforeremove': self._on_carrier_state_remove,  # 7, send collection event (CarrierRemoved)
                'onbeforealternated': self._on_carrier_state_alternated,  # 8, send collection event (CarrierStoredAlt)
                'onbeforeresume': self._on_carrier_state_resume,  # 9, send collection event (CarrierResumed)
                'onbeforeadd_carrier': self._on_carrier_state_add_carrier,  # 10, send collection event (CarrierInstallCompleted)
                'onbeforemod_carrier': self._on_carrier_state_mod_carrier,  # send collection event (CarrierInstallCompleted)
                'onbeforekill_carrier': self._on_carrier_state_kill_carrier,  # 11, send collection event (CarrierRemoveCompleted)
            },
            'autoforward': [
                # {'src': '', 'dst': ''},  # 
            ]
        })

    #####################################
    #       State Machine Callback
    #####################################
    def _on_carrier_state_WAIT_IN(self, _):  # 
        self.CarrierState=1

    def _on_carrier_state_TRANSFERING(self, _):  # 
        self.CarrierState=2

    def _on_carrier_state_WAIT_OUT(self, _):  # 
        self.CarrierState=3

    def _on_carrier_state_COMPLETED(self, _):  # 
        self.CarrierState=4

    def _on_carrier_state_ALTERNATE(self, _):  # 
        self.CarrierState=5

    def _on_carrier_state_wait_in(self, _):  # 1, send collection event (CarrierWaitIn)
        dataset={}
        dataset['CarrierID']=self.CarrierIDRead
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, CarrierWaitIn, dataset)

    def _on_carrier_state_transfer(self, _):  # 2, 4, send collection event (CarrierTransferring)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['StockerCraneID']=self.StockerCraneID
        dataset['CommandID']=self.CommandID
        report_event(self.h, CarrierTransferring, dataset)

    def _on_carrier_state_store(self, _):  # 3, send collection event (CarrierStored)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['HandoffType']=self.HandoffType
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierStored, dataset)

    def _on_carrier_state_wait_out(self, _):  # 5, 6, send collection event (CarrierWaitOut)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierWaitOut, dataset)
        if self.IDReadStatus != 0:
            dataset={}
            dataset['CarrierID']=self.CarrierID
            dataset['CarrierLoc']=self.CarrierLoc
            dataset['IDReadStatus']=self.IDReadStatus
            report_event(self.h, IDReadError, dataset)

    def _on_carrier_state_remove(self, _):  # 7, send collection event (CarrierRemoved)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['HandoffType']=self.HandoffType
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierRemoved, dataset)

    def _on_carrier_state_alternated(self, _):  # 8, send collection event (CarrierStoredAlt)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['Dest']=self.Dest
        report_event(self.h, CarrierStoredAlt, dataset)

    def _on_carrier_state_resume(self, _):  # 9, send collection event (CarrierResumed)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['Dest']=self.Dest
        report_event(self.h, CarrierResumed, dataset)

    def _on_carrier_state_add_carrier(self, _):  # 10, send collection event (CarrierInstallCompleted)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['HandoffType']=self.HandoffType
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierInstallCompleted, dataset)

    def _on_carrier_state_mod_carrier(self, _):  # send collection event (CarrierInstallCompleted)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['HandoffType']=self.HandoffType
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierInstallCompleted, dataset)

    def _on_carrier_state_kill_carrier(self, _):  # 11, send collection event (CarrierRemoveCompleted)
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['HandoffType']=self.HandoffType
        dataset['PortType']=self.PortType
        report_event(self.h, CarrierRemoveCompleted, dataset)

    #####################################
    #       Normal Function Define
    #####################################

    def locate(self):
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, CarrierLocateCompleted, dataset)
    
    def id_read(self, CARRIERID, IDREADSTATUS=0):
        self.CarrierID=CARRIERID
        dataset={}
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['IDReadStatus']=IDREADSTATUS
        report_event(self.h, CarrierIDRead, dataset)

class TransferCommand():
    def __init__(self, secsgem_h, COMMANDID):
        self.h=secsgem_h
        self.CommandID=COMMANDID
        self.CarrierID=''
        self.CarrierLoc=''
        self.CarrierZoneName=''
        self.Priority=''
        self.ResultCode=0 # U2: succ=0, cancel=1, abort=2
        self.Dest=''
        self.TransferState=0 # U2: queued=1, transfering=2, paused=3, canceling=4, aborting=5
        self.StockerCraneID=''

        #####################################
        #   control state 
        #####################################
        ''' TransferState '''
        self.State=Fysom({
            'initial': "none",
            'events': [
                {'name': 'queue', 'src': 'none', 'dst': 'QUEUED'},  # 0
                {'name': 'transfer', 'src': ['QUEUED', 'CANCELLING'], 'dst': 'TRANSFERING'},  # 1, 10
                {'name': 'cancel', 'src': 'QUEUED', 'dst': 'CANCELLING'},  # 2
                {'name': 'cancel_completed', 'src': 'CANCELLING', 'dst': 'COMPLETED'},  # 3
                {'name': 'pause', 'src': 'TRANSFERING', 'dst': 'PAUSED'},  # 4
                {'name': 'resume', 'src': 'PAUSED', 'dst': 'TRANSFERING'},  # 5
                {'name': 'complete', 'src': ['COMPLETED', 'TRANSFERING', 'PAUSED'], 'dst': 'none'},  # 6
                {'name': 'abort', 'src': ['TRANSFERING', 'PAUSED'], 'dst': 'ABORTING'},  # 7
                {'name': 'abort_completed', 'src': 'ABORTING', 'dst': 'COMPLETED'},  # 8
                {'name': 'abort_failed', 'src': 'ABORTING', 'dst': 'ACTIVE'},  # 9
                {'name': 'cancel_failed', 'src': 'CANCELLING', 'dst': 'QUEUED'},  # 11
                {'name': 'history_tranfering', 'src': 'ACTIVE', 'dst': 'TRANSFERING'},  # 9-1
                {'name': 'history_paused', 'src': 'ACTIVE', 'dst': 'PAUSED'},  # 9-2
            ],
            'callbacks': {
                'onQUEUED': self._on_transfer_state_QUEUED,  # 
                'onTRANSFERING': self._on_transfer_state_TRANSFERING,  # 
                'onPAUSED': self._on_transfer_state_PAUSED,  # 
                'onCANCELLING': self._on_transfer_state_CANCELLING,  # 
                'onABORTING': self._on_transfer_state_ABORTING,  # 
                'onACTIVE': self._on_transfer_state_ACTIVE,  # 
                'onCOMPLETED': self._on_transfer_state_COMPLETED,  # 
                'onbeforetransfer': self._on_transfer_state_transfer,  # 1, 10, send collection event (TransferInitiated)
                'onbeforecancel': self._on_transfer_state_cancel,  # 2, send collection event (TransferCancelInitiated)
                'onbeforecancel_completed': self._on_transfer_state_cancel_completed,  # 3, send collection event (TransferCancelCompleted)
                'onbeforepause': self._on_transfer_state_pause,  # 4, send collection event (TransferPaused)
                'onbeforeresume': self._on_transfer_state_resume,  # 5, send collection event (TransferResumed)
                'onbeforecomplete': self._on_transfer_state_complete,  # 6, send collection event (TransferCompleted)
                'onbeforeabort': self._on_transfer_state_abort,  # 7, send collection event (TransferAbortInitiated)
                'onbeforeabort_completed': self._on_transfer_state_abort_completed,  # 8, send collection event (TransferAbortCompleted)
                'onbeforeabort_failed': self._on_transfer_state_abort_failed,  # 9, send collection event (TransferAbortFailed)
                'onbeforecancel_failed': self._on_transfer_state_cancel_failed,  # 11, send collection event (TransferCancelFailed)
            },
            'autoforward': [
            ]
        })

    #####################################
    #       State Machine Callback
    #####################################
    def _on_transfer_state_QUEUED(self, _):  # 
        self.TransferState=1

    def _on_transfer_state_TRANSFERING(self, _):  # 
        self.TransferState=2

    def _on_transfer_state_PAUSED(self, _):  # 
        self.TransferState=3

    def _on_transfer_state_CANCELLING(self, _):  # 
        self.TransferState=4

    def _on_transfer_state_ABORTING(self, _):  # 
        self.TransferState=5

    def _on_transfer_state_ACTIVE(self, _):  # 
        if self.history == 'TRANSFER':
            self.State.history_tranfering()
        else:
            self.State.history_paused()

    def _on_transfer_state_COMPLETED(self, _):  # 
        self.State.complete()

    def _on_transfer_state_transfer(self, _):  # 1, 10, send collection event (TransferInitiated)
        self.history='TRANSFER'
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        dataset['Dest']=self.Dest
        report_event(self.h, TransferInitiated, dataset)

    def _on_transfer_state_cancel(self, _):  # 2, send collection event (TransferCancelInitiated)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferCancelInitiated, dataset)

    def _on_transfer_state_cancel_completed(self, _):  # 3, send collection event (TransferCancelCompleted)
        self.ResultCode=1
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferCancelCompleted, dataset)

    def _on_transfer_state_pause(self, _):  # 4, send collection event (TransferPaused)
        self.history='PAUSED'
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferPaused, dataset)

    def _on_transfer_state_resume(self, _):  # 5, send collection event (TransferResumed)
        self.history='TRANSFER'
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferResumed, dataset)

    def _on_transfer_state_complete(self, _):  # 6, send collection event (TransferCompleted)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.Dest
        dataset['ResultCode']=self.ResultCode
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferCompleted, dataset)

    def _on_transfer_state_abort(self, _):   # 7, send collection event (TransferAbortInitiated)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferAbortInitiated, dataset)

    def _on_transfer_state_abort_completed(self, _):  # 8, send collection event (TransferAbortCompleted)
        self.ResultCode=2
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferAbortCompleted, dataset)

    def _on_transfer_state_abort_failed(self, _):  # 9, send collection event (TransferAbortFailed)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferAbortFailed, dataset)

    def _on_transfer_state_cancel_failed(self, _):  # 11, send collection event (TransferCancelFailed)
        dataset={}
        dataset['CommandID']=self.CommandID
        dataset['CarrierID']=self.CarrierID
        dataset['CarrierLoc']=self.CarrierLoc
        dataset['CarrierZoneName']=self.CarrierZoneName
        report_event(self.h, TransferCancelFailed, dataset)

class Zone():
    def __init__(self, secsgem_h, ZONENAME):
        self.h=secsgem_h
        self.ZoneName=ZONENAME
        self.ZoneSize=0
        self.ZoneCapacity=0
        self.ZoneType=0 # U2: shelf=1, port=2, transporter=3
        self.ZoneState=0 # U2: UP=1, DOWN=2, OTHER=0
        self.WaterLevel='unknown'
        self.ZoneUnitState={}
        self.StockerUnit={}
        self.lock=threading.Lock()

    def capacity_decrease(self):
        self.lock.acquire()
        self.ZoneCapacity -= 1
        dataset={}
        dataset['ZoneData']={'ZoneName':self.ZoneName, 'ZoneCapacity':self.ZoneCapacity}
        report_event(self.h, ZoneCapacityChange, dataset)
        self.lock.release()

    def capacity_increase(self):
        self.lock.acquire()
        self.ZoneCapacity += 1
        dataset={}
        dataset['ZoneData']={'ZoneName':self.ZoneName, 'ZoneCapacity':self.ZoneCapacity}
        report_event(self.h, ZoneCapacityChange, dataset)
        self.lock.release()

    def zone_capacity_change(self, CAPACITY):
        self.lock.acquire()
        self.ZoneCapacity=CAPACITY
        dataset={}
        dataset['ZoneData']={'ZoneName':self.ZoneName, 'ZoneCapacity':self.ZoneCapacity}
        report_event(self.h, ZoneCapacityChange, dataset)
        self.lock.release()

    def zone_alarm_set(self, alid, is_set, dataset={}): # Mike: 2021/07/12
        dataset['ZoneName']=self.ZoneName
        alarm_set(self.h, alid, is_set, dataset)

class Port():
    def __init__(self, secsgem_h, PORTID):
        self.h=secsgem_h
        self.PortID=PORTID
        self.PortState=0 # U2: unknown=0, transferBlocking=3, readyToLoad=4, readyToUnload=5
        self.PortServiceState=1 # U2: outOfService=1, inService=2
        self.TransferState=0 # U2: unknown=0, outOfService=1, inService=2, transferBlocking=3, readyToLoad=4, readyToUnload=5
        self.PortIOType=3 # U1: loader=1, unloader=2, mixed=3
        self.PortBook=False
        self.StockerCraneID=''

    def in_service(self):
        self.PortServiceState=2
        self.TransferState=2
        dataset={}
        dataset['PortID']=self.PortID
        print('>>> PortInService', PortInService, dataset)
        report_event(self.h, PortInService, dataset)

    def out_of_service(self):
        self.PortServiceState=1
        self.TransferState=1
        dataset={}
        dataset['PortID']=self.PortID
        print('>>> PortOutOfService', PortOutOfService, dataset)
        report_event(self.h, PortOutOfService, dataset)

    def transfer_block(self):
        self.PortState=3
        self.PortServiceState=2
        self.TransferState=3
        dataset={}
        dataset['PortID']=self.PortID
        print('>>> PortTransferBlocked', PortTransferBlocked, dataset)
        report_event(self.h, PortTransferBlocked, dataset)

    def ready_to_load(self):
        self.PortState=4
        self.PortServiceState=2
        self.TransferState=4
        dataset={}
        dataset['PortID']=self.PortID
        print('>>> PortReadyToLoad', PortReadyToLoad, dataset)
        report_event(self.h, PortReadyToLoad, dataset)

    def ready_to_unload(self):
        self.PortState=5
        self.PortServiceState=2
        self.TransferState=5
        dataset={}
        dataset['PortID']=self.PortID
        print('>>> PortReadyToUnload', PortReadyToUnload, dataset)
        report_event(self.h, PortReadyToUnload, dataset)


class Carriers():
    def __init__(self, secsgem_h):
        self.Data={}
        self.h=secsgem_h

    def add(self, CARRIERID):
        if CARRIERID not in self.Data:
            self.Data[CARRIERID]=Carrier(self.h, CARRIERID)
            self.Data[CARRIERID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
            return True
        return False

    def set(self, CARRIERID, datasets):
        for key, value in datasets.items():
            setattr(self.Data[CARRIERID], key, value)

    def mod(self, CARRIERID, NEWCARRIERID):
        if CARRIERID in self.Data and NEWCARRIERID not in self.Data:
            self.Data[NEWCARRIERID]=self.Data[CARRIERID]
            del self.Data[CARRIERID]
            return True
        return False

    def delete(self, CARRIERID):
        if CARRIERID in self.Data:
            del self.Data[CARRIERID]
            return True
        return False

class Transfers():
    def __init__(self,secsgem_h):
        self.Data={}
        self.h=secsgem_h

    def add(self, COMMANDID):
        if COMMANDID not in self.Data:
            self.Data[COMMANDID]=TransferCommand(self.h, COMMANDID)
            return True
        return False

    def mod(self, COMMANDID, NEWCOMMANDID):
        for cmd_id, cmd_obj in self.Data.items():
            print('mod commandid:', cmd_id, 'obj:', cmd_obj)
        if COMMANDID in self.Data and NEWCOMMANDID not in self.Data:
            self.Data[NEWCOMMANDID]=self.Data[COMMANDID]
            print('>>> mod', NEWCOMMANDID)
            del self.Data[COMMANDID]
            return True
        elif COMMANDID not in self.Data: # Stage cmd not in Data
            # self.Data[NEWCOMMANDID]=self.Data[COMMANDID]
            self.Data[NEWCOMMANDID].CommandID=NEWCOMMANDID
            for cmd_id, cmd_obj in self.Data.items():
                print('mod2 commandid:', cmd_id, 'obj:', cmd_obj.CommandID)
            return True
        return False

    def set(self, COMMANDID, datasets):
        for key, value in datasets.items():
            setattr(self.Data[COMMANDID], key, value)

    def delete(self, COMMANDID):
        if COMMANDID in self.Data:
            del self.Data[COMMANDID]
            return True
        return False

class Zones():
    def __init__(self, secsgem_h):
        self.Data={}
        self.ZoneMap={}
        self.h=secsgem_h

    def add(self, ZONENAME):
        if ZONENAME not in self.Data:
            self.Data[ZONENAME]=Zone(self.h, ZONENAME)
            return True
        return False

    def set(self, ZONENAME, datasets):
        for key, value in datasets.items():
            setattr(self.Data[ZONENAME], key, value)

    def mod(self, ZONENAME, NEWZONENAME):
        if ZONENAME in self.Data and NEWZONENAME not in self.Data:
            self.Data[NEWZONENAME]=self.Data[ZONENAME]
            del self.Data[ZONENAME]
            return True
        return False

    def delete(self, ZONENAME):
        if ZONENAME in self.Data:
            del self.Data[ZONENAME]
            return True
        return False

class Ports():
    def __init__(self, secsgem_h):
        self.Data={}
        self.h=secsgem_h

    def add(self, PORTID):
        if PORTID not in self.Data:
            self.Data[PORTID]=Port(self.h, PORTID)
            return True
        return False

    def set(self, PORTID, datasets):
        for key, value in datasets.items():
            setattr(self.Data[PORTID], key, value)

    def mod(self, PORTID, NEWPORTID):
        if PORTID in self.Data and NEWPORTID not in self.Data:
            self.Data[NEWPORTID]=self.Data[PORTID]
            del self.Data[PORTID]
            return True
        return False

    def delete(self, PORTID):
        if PORTID in self.Data:
            del self.Data[PORTID]
            return True
        return False


GenIndex=0
GenLock=threading.Lock()
def FailureIDGEN(fail_loc, dup_carrier=None): # zhangpeng 2025-02-25 Adjust the format for failure ID
    global GenIndex, GenLock
    GenLock.acquire()
    ret = ''
    if fail_loc and dup_carrier: # Duplicate
        ret='UNKNOWNDUP-{}-{}-{:04d}'.format(dup_carrier, fail_loc, GenIndex) # e.g. UNKNOWNDUP-CARRIER456-E1P1-0000
    elif fail_loc: # ReadFail
        ret='UNKNOWN-{}-{:04d}'.format(fail_loc, GenIndex) # e.g. UNKNOWN-E1P1-0000
    else:
        ret='FAILURE{:04d}'.format(GenIndex)
    GenIndex=(GenIndex+1) % 10000
    GenLock.release()
    return ret


'''AlarmTable={
    20001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode],'text':'SC internal error, code exception'},
    20002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'Base read rfid error'},
    20003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'E84 error'},
    20004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName],'text':'Off line, retry communication with rack timeout'},
    20005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'Port in manual mode'},

    20051: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack off line'},
    20052: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level high'},
    20053: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level full'},
    20054: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level low'},
    20055: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level empty'},

    30001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack Rack connect fail'},
    30002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'receive null string from socket'},
    30003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'linking timeout'},
    30004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'receive format error from socket'},
    30005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack syntax error'},
}'''

AlarmTable={
    # ALID: {'report_id':[], 'report':[], 'text':ALTX},
    10000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode], 'text':'TSC internal error or code exception'}, #chocp 2021/11/26
    10001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID], 'text':'Vehicle internal error or code exception'}, #chocp 2021/11/26
    10002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID], 'text':'Vehicle generate action fail or no buffer left'}, #chocp 2021/11/26
    10003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'Robot status error'},
    10004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'MR move status error'},
    10005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_Source, SV_Dest], 'text':'MR route error error'},
    10006: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID], 'text':'MR offline'},
    10007: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'interlock error'},
    10008: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID], 'text':'MR not in auto mode'},
    10009: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'MR with other alarm'},
    10010: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID], 'text':'TSC in manual test'},
    10011: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_ZoneName], 'text':'Fault rack full or allocate fail'},
    10012: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_ZoneName], 'text':'Select rack full or allocate fail'},
    10013: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_PortID], 'text':'Port not found or syntax error'},
    10014: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack syntax error'},
    10015: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'Safety check fail, port not reach'},
    10016: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'Safety check fail, eq port check fail'},
    10017: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'Safety check fail, erack check fail'},
    10018: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'Safety check fail, buffer check fail'},
    10019: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'CarrierID read fail'},
    10020: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID, SV_CarrierID], 'text':'CarrierID already exists'},
    10021: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'Robot status check error'},
    10022: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'MR move status check error'},
    10023: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'Transfer command timeout'}, #chocp fix 2021/10/10
    10024: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_Source, SV_Dest], 'text':'MR try or select to standby station fail'},
    10025: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'MR execute charge command timeout'},
    10026: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'CarrierType None or Check Error for Acquire/Deposit'},
    10027: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID], 'text':'MR move with route obstacles'},
    10028: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_Source, SV_Dest], 'text': 'MR try or select to charge station fail'},
    10029: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_PortID], 'text': 'Stop MR command to replace new job'},
    10030: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_PortID], 'text': 'No available carrier.'},
    10031: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID], 'text': 'MR Stop wit host command'},
    10032: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_StockerCraneID, SV_CommandID, SV_PortID], 'text':'MR with other warning'},

    20001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode],'text':'SC internal error, code exception'},
    20002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'Base read rfid error'},
    20003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'E84 error'},
    20004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName],'text':'Off line, retry communication with rack timeout'},
    20005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName, SV_CarrierLoc],'text':'Port in manual mode'},

    20051: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack off line'},
    20052: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level high'},
    20053: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level full'},
    20054: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level low'},
    20055: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack water level empty'},

    30001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack Rack connect fail'},
    30002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'receive null string from socket'},
    30003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'linking timeout'},
    30004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'receive format error from socket'},
    30005: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_ZoneName], 'text':'Erack syntax error'},
    40000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level ,SV_SubCode], 'text':'Host transfer cmd parse get exception'},

    40001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Cancel by host'},
    40002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Abort by host'},

    
    40007: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host transfer cmd, commandID duplicated in active transfers'},
    40008: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Dest], 'text':'Host change cmd, go to new dest port due to TrLoad request NG'},
    40009: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_CarrierType], 'text':'Host transfer cmd, CarrierType None or Error'},
    40010: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID not in white list'},
    40011: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Source], 'text':'Host transfer cmd, source port not found in map'},
    40012: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Dest], 'text':'Host transfer cmd, dest port not found in map'},
    40013: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID duplicated in waiting queue'},
    40014: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, carrierID duplicated in executing queue'},
    40015: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Source], 'text':'Host transfer cmd, source port null'},
    40016: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host transfer cmd, can not locate carrierID'},
    40017: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Dest], 'text':'Host transfer cmd, dest port auto assign fail'},
    40018: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Source, SV_CarrierID], 'text':'Host transfer cmd, source port conflict with specified carrier'},
    40019: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Dest], 'text':'Host transfer cmd, dest port duplicate with other cmd'},
    40020: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_Source], 'text':'Host transfer cmd, source port duplicate with other cmd'},

    50061: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Elevator with alarmst'},
    50062: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Elevator linking timeout'},
    50063: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Elevator Connect fail'},

    60000: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID], 'text':'Host order rtd cmd, workID duplicate in worklist'},
    60001: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier duplicate in worklist'},
    60002: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, can not locate carrier'},
    60003: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID], 'text':'Host order rtd cmd, carrier ID can not null'},
    60004: {'report':[SV_ALTX, SV_ALSV, SV_UnitType, SV_UnitID, SV_Level, SV_SubCode, SV_CommandID, SV_CarrierID, SV_Dest], 'text':'Host order rtd cmd, dest port dispatch fail'},

}


class E88Equipment(secsgem.GemEquipmentHandler):
    def __init__(self, address, port, active, session_id, name='Gyro Agvc', log_name="E88_hsms_communication", mdln='STKC_v1.1', T3=45, T5=10, T6=5, T7=10, T8=5, custom_connection_handler=None, initial_control_state="ONLINE", initial_online_control_state="REMOTE"):

        SOFTREV='' # Mike: 2021/11/12
        try:
            f=open('version.txt','r')
            SOFTREV=f.readline()
            f.close()
        except:
            pass

        secsgem.GemEquipmentHandler.__init__(self, address, port, active, session_id, name, custom_connection_handler, initial_control_state, initial_online_control_state)

        self.connection.T3=T3
        self.connection.T5=T5
        self.connection.T6=T6
        self.connection.T7=T7
        self.connection.T8=T8

        self.MDLN=mdln
        self.SOFTREV=SOFTREV
        self.EqpName=name
        self.communicationLogger=logging.getLogger(log_name)
        self.communicationLogger.setLevel(logging.DEBUG)
        self.logger=self.communicationLogger
        self.connection.logger=self.communicationLogger

        self._spool_enable=0

        self.rcmd_auto_reply=False

        self.ERROR_MSG=''

        self.active_alarms=[] # Mike: 2021/05/17

        self.failure_map={}

        self.remote_commands_callback=None

        ### example: ActiveCarriers={
        ###              "123456": {"CarrierID": "123456", "CarrierLoc": "aaaa"},
        ###              "654321": {"CarrierID": "654321", "CarrierLoc": "bbbb"}
        ###          }
        self.ActiveCarriers={} # CarrierInfo*n

        ### example: self.ActiveTransfers={
        ###              "cmd1": {
        ###                  "CommandInfo": {"CommandID":"cmd1", "Priority":1},
        ###                  "TransferInfo": {"CarrierID": "123456", "CarrierLoc": "aaaa", "Dest": "LP1"},
        ###              "cmd2": {
        ###                  "CommandInfo": {"CommandID":"cmd2", "Priority":2},
        ###                  "TransferInfo": {"CarrierID": "111111", "CarrierLoc": "cccc", "Dest": "STORAGE"}}
        ###          }
        self.ActiveTransfers={} # TransferCommand*n

        ### example: ActiveZones={
        ###              "STORAGE": {"ZoneName": "STORAGE", "ZoneCapacity": 30},
        ###              "STORAGE2": {"ZoneName": "STORAGE2", "ZoneCapacity": 50}
        ###          }
        self.ActiveZones={} # ZoneData*n

        ### example: EnhancedCarriers={
        ###              "123456": {"CarrierID": "123456", "CarrierLoc": "aaaa", "CarrierZoneName": "STORAGE", "InstallTime": "2021042210132233", "CarrierState": 1},
        ###              "654321": {"CarrierID": "654321", "CarrierLoc": "bbbb", "CarrierZoneName": "STORAGE", "InstallTime": "2021042210151842", "CarrierState": 2}
        ###          }
        self.EnhancedCarriers={} # EnhancedCarrierInfo*n

        ### example: EnhancedTransfers={
        ###              "cmd1": {
        ###                  "TransferState": ,
        ###                  "CommandInfo": {"CommandID":"cmd1", "Priority":1},
        ###                  "TransferInfo": {"CarrierID": "123456", "CarrierLoc": "aaaa", "Dest": "LP1"}},
        ###              "cmd2": {
        ###                  "TransferState": ,
        ###                  "CommandInfo": {"CommandID":"cmd2", "Priority":2},
        ###                  "TransferInfo": {"CarrierID": "111111", "CarrierLoc": "cccc", "Dest": "STORAGE"}}
        ###          }
        self.EnhancedTransfers={} # EnhancedTranferCommand*n

        ### example: EnhancedActiveZones={
        ###              "STORAGE": {"ZoneName": "STORAGE", "ZoneCapacity": 30, "ZoneSize": 80, "ZoneType": 1},
        ###              "STORAGE2": {"ZoneName": "STORAGE2", "ZoneCapacity": 50, "ZoneSize": 80, "ZoneType": 2}
        ###          }
        self.EnhancedActiveZones={} # EnhancedZoneData*n

        self.Carriers=Carriers(self)
        self.Transfers=Transfers(self)
        self.Zones=Zones(self)
        self.Ports=Ports(self)

        ''' tmp sv, for events, not available '''
        self.CarrierID='' # A
        self.CarrierLoc='' # A
        self.CarrierState=0 # U2: wait_in=1, transfer=2, wait_out=3, completed=4, alternate=5
        self.CarrierZoneName='' # A
        self.CommandName='' # A
        self.CommandID='' # A
        self.CommandType='' # A
        self.Dest='' # A
        self.EmptyCarrier=0 # U2: empty=0, not empty=1
        self.ErrorID='' # A
        self.HandoffType=0 # U2: man=1, auto=2
        self.IDReadStatus=0 # U2: succ=0, fail=1, duplicate=2, mismatch=3
        self.InstallTime='' # A: TIME
        self.PortType='' # A: OP=output, BP=buffer, LP=loading
        self.Priority=0 # U2
        self.RecoveryOptions='' # A: blank, RETRY, ABORT
        self.ResultCode=0 # U2: succ=0, cancel=1, abort=2
        self.Source='' # A
        self.SCState=1 # U2: SC_init=1, paused=2, auto=3, pausing=4
        self.StockerCraneID='' # A
        self.StockerUnitID='' # A
        self.StockerUnitState=0 # U2
        self.TransferState=0 # U2: queued=1, transfering=2, paused=3, canceling=4, aborting=5
        self.ZoneCapacity=0 # U2
        self.ZoneName='' # A
        self.ZoneSize=0 # U2
        self.ZoneType=0 # U2: shelf=1, port=2, other=3
        self.DeviceID=''
        self.PortID=''
        self.PortTransferState=0 # U2: OutOfService=1, InService=2, TransferBlocked=3, ReadyToLoad=4, ReadyToUnload=5
        self.PortIOType=3 # U1: loader=1, unloader=2, mixed=3

        self.ALTX=''
        self.ALSV=''
        self.UnitType='Rack'
        self.UnitID=''
        self.Level=''
        self.SubCode=''

        self.CarrierInfo={'CarrierID':'', 'CarrierLoc':''} # CarrierID, CarrierLoc
        self.CommandInfo={'CommandID':'', 'Priority':0} # CommandID, Priority
        self.StockerUnitInfo={'StockerUnitID':self.StockerUnitID, 'StockerUnitState':self.StockerUnitState} # StockerUnitID, StockerUnitState
        self.TransferInfo={'CarrierID':self.CarrierID, 'CarrierLoc':self.CarrierLoc, 'Dest':self.Dest} # CarrierID, CarrierLoc, Dest
        self.ZoneData={'ZoneName':self.ZoneName, 'ZoneCapacity':self.ZoneCapacity} # ZoneName, ZoneCapacity
        self.TransferCommand={'CommandInfo':self.CommandInfo, 'TransferInfo':self.TransferInfo} # CommandInfo, TransferInfo
        self.EnhancedCarrierInfo={'CarrierID':self.CarrierID, 'CarrierLoc':self.CarrierLoc, 'CarrierZoneName':self.CarrierZoneName, 'InstallTime':self.InstallTime, 'CarrierState':self.CarrierState} # CarrierID, CarrierLoc, CarrierZoneName, InstallTime, CarrierState
        self.EnhancedTransferCommand={'TransferState':self.TransferState, 'CommandInfo':self.CommandInfo, 'TransferInfo':self.TransferInfo} # TransferState, CommandInfo, TransferInfo
        self.EnhancedZoneData={'ZoneName':self.ZoneName, 'ZoneCapacity':self.ZoneCapacity, 'ZoneSize':self.ZoneSize, 'ZoneType':self.ZoneType} # ZoneName, ZoneCapacity, ZoneSize, ZoneType
        self.EnhancedPortData={'PortID':self.PortID, 'PortTransferState':self.PortTransferState, 'PortIOType':self.PortIOType} # PortID, PortStatus, PortIOType


        #####################################
        #     Status Variable Declaration
        #####################################
        ''' SV initial '''
        self.status_variables.update({
            GEM_MDLN: secsgem.StatusVariable(GEM_MDLN, "GEM_MDLN", "", secsgem.SecsVarString, False),
            GEM_SOFTREV: secsgem.StatusVariable(GEM_SOFTREV, "GEM_SOFTREV", "", secsgem.SecsVarString, False),
            SV_EqpName: secsgem.StatusVariable(SV_EqpName, "SV_EqpName", "", secsgem.SecsVarString, True),
            SV_SCState: secsgem.StatusVariable(SV_SCState, "SV_SCState", "", secsgem.SecsVarU2, True),
            SV_ActiveCarriers: secsgem.StatusVariable(SV_ActiveCarriers, "SV_ActiveCarriers", "", secsgem.SecsVarArray, True),
            SV_ActiveTransfers: secsgem.StatusVariable(SV_ActiveTransfers, "SV_ActiveTransfers", "", secsgem.SecsVarArray, True),
            SV_ActiveZones: secsgem.StatusVariable(SV_ActiveZones, "SV_ActiveZones", "", secsgem.SecsVarArray, True),
            SV_EnhancedCarriers: secsgem.StatusVariable(SV_EnhancedCarriers, "SV_EnhancedCarriers", "", secsgem.SecsVarArray, True),
            SV_EnhancedTransfers: secsgem.StatusVariable(SV_EnhancedTransfers, "SV_EnhancedTransfers", "", secsgem.SecsVarArray, True),
            SV_EnhancedActiveZones: secsgem.StatusVariable(SV_EnhancedActiveZones, "SV_EnhancedActiveZones", "", secsgem.SecsVarArray, True),
            SV_EnhancedPortData: secsgem.StatusVariable(SV_EnhancedPortData, "SV_EnhancedPortData", "", secsgem.SecsVarArray, True),
            SV_CarrierID: secsgem.StatusVariable(SV_CarrierID, "SV_CarrierID", "", secsgem.SecsVarString, True),
            SV_CarrierInfo: secsgem.StatusVariable(SV_CarrierInfo, "SV_CarrierInfo", "", secsgem.SecsVarList, True),
            SV_CarrierLoc: secsgem.StatusVariable(SV_CarrierLoc, "SV_CarrierLoc", "", secsgem.SecsVarString, True),
            SV_CarrierType: secsgem.StatusVariable(SV_CarrierType, "SV_CarrierType", "", secsgem.SecsVarString, True), # chocp 2022/1/2
            SV_CarrierZoneName: secsgem.StatusVariable(SV_CarrierZoneName, "SV_CarrierZoneName", "", secsgem.SecsVarString, True),
            # SV_CommandName: secsgem.StatusVariable(SV_CommandName, "SV_CommandName", "", secsgem.SecsVarString, True),
            SV_CommandID: secsgem.StatusVariable(SV_CommandID, "SV_CommandID", "", secsgem.SecsVarString, True),
            SV_CommandInfo: secsgem.StatusVariable(SV_CommandInfo, "SV_CommandInfo", "", secsgem.SecsVarList, True),
            SV_CommandType: secsgem.StatusVariable(SV_CommandType, "SV_CommandType", "", secsgem.SecsVarString, True),
            SV_Dest: secsgem.StatusVariable(SV_Dest, "SV_Dest", "", secsgem.SecsVarString, True),
            SV_EmptyCarrier: secsgem.StatusVariable(SV_EmptyCarrier, "SV_EmptyCarrier", "", secsgem.SecsVarU2, True),
            SV_EnhancedCarrierInfo: secsgem.StatusVariable(SV_EnhancedCarrierInfo, "SV_EnhancedCarrierInfo", "", secsgem.SecsVarList, True),
            SV_EnhancedTransferCommand: secsgem.StatusVariable(SV_EnhancedTransferCommand, "SV_EnhancedTransferCommand", "", secsgem.SecsVarList, True),
            SV_EnhancedZoneData: secsgem.StatusVariable(SV_EnhancedZoneData, "SV_EnhancedZoneData", "", secsgem.SecsVarList, True),
            SV_ErrorID: secsgem.StatusVariable(SV_ErrorID, "SV_ErrorID", "", secsgem.SecsVarString, True),
            SV_HandoffType: secsgem.StatusVariable(SV_HandoffType, "SV_HandoffType", "", secsgem.SecsVarU2, True),
            SV_IDReadStatus: secsgem.StatusVariable(SV_IDReadStatus, "SV_IDReadStatus", "", secsgem.SecsVarU2, True),
            SV_InstallTime: secsgem.StatusVariable(SV_InstallTime, "SV_InstallTime", "", secsgem.SecsVarString, True),
            SV_PortType: secsgem.StatusVariable(SV_PortType, "SV_PortType", "", secsgem.SecsVarString, True),
            SV_Priority: secsgem.StatusVariable(SV_Priority, "SV_Priority", "", secsgem.SecsVarU2, True),
            SV_RecoveryOptions: secsgem.StatusVariable(SV_RecoveryOptions, "SV_RecoveryOptions", "", secsgem.SecsVarString, True),
            SV_ResultCode: secsgem.StatusVariable(SV_ResultCode, "SV_ResultCode", "", secsgem.SecsVarU2, True),
            SV_Source: secsgem.StatusVariable(SV_Source, "SV_Source", "", secsgem.SecsVarString, True),
            SV_StockerCraneID: secsgem.StatusVariable(SV_StockerCraneID, "SV_StockerCraneID", "", secsgem.SecsVarString, True),
            SV_StockerUnitID: secsgem.StatusVariable(SV_StockerUnitID, "SV_StockerUnitID", "", secsgem.SecsVarString, True),
            SV_StockerUnitInfo: secsgem.StatusVariable(SV_StockerUnitInfo, "SV_StockerUnitInfo", "", secsgem.SecsVarList, True),
            SV_StockerUnitState: secsgem.StatusVariable(SV_StockerUnitState, "SV_StockerUnitState", "", secsgem.SecsVarU2, True),
            SV_TransferCommand: secsgem.StatusVariable(SV_TransferCommand, "SV_TransferCommand", "", secsgem.SecsVarList, True),
            SV_TransferInfo: secsgem.StatusVariable(SV_TransferInfo, "SV_TransferInfo", "", secsgem.SecsVarList, True),
            SV_TransferState: secsgem.StatusVariable(SV_TransferState, "SV_TransferState", "", secsgem.SecsVarU2, True),
            SV_PortID: secsgem.StatusVariable(SV_PortID, "SV_PortID", "", secsgem.SecsVarString, True),
            SV_PortIOType: secsgem.StatusVariable(SV_PortIOType, "SV_PortIOType", "", secsgem.SecsVarU1, True),
            SV_ZoneCapacity: secsgem.StatusVariable(SV_ZoneCapacity, "SV_ZoneCapacity", "", secsgem.SecsVarU2, True),
            SV_ZoneData: secsgem.StatusVariable(SV_ZoneData, "SV_ZoneData", "", secsgem.SecsVarList, True),
            SV_ZoneName: secsgem.StatusVariable(SV_ZoneName, "SV_ZoneName", "", secsgem.SecsVarString, True),
            SV_ZoneSize: secsgem.StatusVariable(SV_ZoneSize, "SV_ZoneSize", "", secsgem.SecsVarU2, True),
            SV_ZoneType: secsgem.StatusVariable(SV_ZoneType, "SV_ZoneType", "", secsgem.SecsVarU2, True),
            SV_DeviceID: secsgem.StatusVariable(SV_DeviceID, "SV_DeviceID", "", secsgem.SecsVarString, True),
            SV_ALTX: secsgem.StatusVariable(SV_ALTX, "SV_ALTX", "", secsgem.SecsVarString, True), # Mike: 2021/11/08
            SV_ALSV: secsgem.StatusVariable(SV_ALSV, "SV_ALSV", "", secsgem.SecsVarString, True), # Mike: 2021/11/08
            SV_UnitType: secsgem.StatusVariable(SV_UnitType, "SV_UnitType", "", secsgem.SecsVarString, True), # Mike: 2021/11/29
            SV_UnitID: secsgem.StatusVariable(SV_UnitID, "SV_UnitID", "", secsgem.SecsVarString, True), # Mike: 2021/11/29
            SV_Level: secsgem.StatusVariable(SV_Level, "SV_Level", "", secsgem.SecsVarString, True), # Mike: 2021/12/01
            SV_SubCode: secsgem.StatusVariable(SV_SubCode, "SV_SubCode", "", secsgem.SecsVarString, True), #Chi 2022/06/17
        })
        self.status_variables[GEM_MDLN].value=self.MDLN
        self.status_variables[GEM_SOFTREV].value=self.SOFTREV

        #####################################
        #  Equipment Constants Declaration
        #####################################
        ''' EC initial '''
        '''self.equipment_constants.update({
            ECID: secsgem.EquipmentConstant(ECID, "EC", EC_max, EC_min, EC_default, "EC_unit", secsgem.SecsVarU4, False),
        })'''

        #####################################
        #       Report Declaration
        #####################################
        ''' Report initial '''
        for ALID, DATA in AlarmTable.items():
            if DATA['report']:
                self.registered_reports.update({
                    ALID+500000: secsgem.CollectionEventReport(ALID+500000, DATA['report']),
                })

        self.registered_reports.update({
            # SC STATE TRANSITION EVENTS
            #SCAutoCompleted: secsgem.CollectionEventReport(SCAutoCompleted, []),
            #SCAutoInitiated: secsgem.CollectionEventReport(SCAutoInitiated, []),
            #SCPauseCompleted: secsgem.CollectionEventReport(SCPauseCompleted, []),
            #SCPaused: secsgem.CollectionEventReport(SCPaused, []),
            #SCPauseInitiated: secsgem.CollectionEventReport(SCPauseInitiated, []),
            # TRANSFER COMMAND STATE TRANSITION EVENTS
            TransferAbortCompleted: secsgem.CollectionEventReport(TransferAbortCompleted, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferAbortFailed: secsgem.CollectionEventReport(TransferAbortFailed, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferAbortInitiated: secsgem.CollectionEventReport(TransferAbortInitiated, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferCancelCompleted: secsgem.CollectionEventReport(TransferCancelCompleted, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferCancelFailed: secsgem.CollectionEventReport(TransferCancelFailed, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferCancelInitiated: secsgem.CollectionEventReport(TransferCancelInitiated, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferCompleted: secsgem.CollectionEventReport(TransferCompleted, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_ResultCode, SV_CarrierZoneName]),
            TransferInitiated: secsgem.CollectionEventReport(TransferInitiated, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName, SV_Dest]),
            TransferPaused: secsgem.CollectionEventReport(TransferPaused, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            TransferResumed: secsgem.CollectionEventReport(TransferResumed, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            # STOCKER CARRIER STATE TRANSITION EVENTS
            CarrierInstallCompleted: secsgem.CollectionEventReport(CarrierInstallCompleted, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            CarrierRemoveCompleted: secsgem.CollectionEventReport(CarrierRemoveCompleted, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            CarrierRemoved: secsgem.CollectionEventReport(CarrierRemoved, [SV_CarrierID, SV_HandoffType]),
            CarrierResumed: secsgem.CollectionEventReport(CarrierResumed, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName, SV_Dest, SV_StockerCraneID]),
            CarrierStored: secsgem.CollectionEventReport(CarrierStored, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            CarrierStoredAlt: secsgem.CollectionEventReport(CarrierStoredAlt, [SV_CommandID, SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName, SV_Dest]),
            CarrierTransferring: secsgem.CollectionEventReport(CarrierTransferring, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName, SV_StockerCraneID, SV_CommandID]),
            CarrierWaitIn: secsgem.CollectionEventReport(CarrierWaitIn, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            CarrierWaitOut: secsgem.CollectionEventReport(CarrierWaitOut, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName, SV_PortType]),
            ZoneCapacityChange: secsgem.CollectionEventReport(ZoneCapacityChange, [SV_ZoneData]),
            # STOCKER CRANE STATE TRANSITION EVENTS
            CraneActive: secsgem.CollectionEventReport(CraneActive, [SV_CommandID, SV_StockerCraneID]),
            CraneIdle: secsgem.CollectionEventReport(CraneIdle, [SV_CommandID, SV_StockerCraneID]),
            CraneOutOfService: secsgem.CollectionEventReport(CraneOutOfService, [SV_StockerCraneID]),
            CraneInService: secsgem.CollectionEventReport(CraneInService, [SV_StockerCraneID]),
            #port transfer state transition events
            PortInService: secsgem.CollectionEventReport(PortInService, [SV_PortID]),
            PortOutOfService: secsgem.CollectionEventReport(PortOutOfService, [SV_PortID]),
            PortTransferBlocked: secsgem.CollectionEventReport(PortTransferBlocked, [SV_PortID]),
            PortReadyToLoad: secsgem.CollectionEventReport(PortReadyToLoad, [SV_PortID]),
            PortReadyToUnload: secsgem.CollectionEventReport(PortReadyToUnload, [SV_PortID]),
            PortTypeChange: secsgem.CollectionEventReport(PortTypeChange, [SV_PortID, SV_PortIOType]),
            # NON-TRANSITION EVENTS
            CarrierIDRead: secsgem.CollectionEventReport(CarrierIDRead, [SV_CarrierID, SV_CarrierLoc, SV_IDReadStatus]),
            CarrierLocateCompleted: secsgem.CollectionEventReport(CarrierLocateCompleted, [SV_CarrierID, SV_CarrierLoc, SV_CarrierZoneName]),
            IDReadError: secsgem.CollectionEventReport(IDReadError, [SV_CarrierID, SV_CarrierLoc, SV_IDReadStatus]),
            OperatorInitiatedAction: secsgem.CollectionEventReport(OperatorInitiatedAction, [SV_CommandID, SV_CommandType, SV_CarrierID, SV_Source, SV_Dest, SV_Priority]),
        })


        #####################################
        #       Event Declaration/Link
        #####################################
        ''' Report link initial'''
        for ALID, DATA in AlarmTable.items():
            if DATA['report']:
                self.registered_collection_events.update({
                    ALID+100000: secsgem.CollectionEventLink(ALID+100000, [ALID+500000]),
                    ALID+200000: secsgem.CollectionEventLink(ALID+200000, [ALID+500000]),
                })
                self.registered_collection_events[ALID+100000].enabled=True
                self.registered_collection_events[ALID+200000].enabled=True
            else:
                self.registered_collection_events.update({
                    ALID+100000: secsgem.CollectionEventLink(ALID+100000, [ALID+500000]),
                    ALID+200000: secsgem.CollectionEventLink(ALID+200000, [ALID+500000]),
                })
                self.registered_collection_events[ALID+100000].enabled=True
                self.registered_collection_events[ALID+200000].enabled=True

        self.registered_collection_events.update({
            # SC STATE TRANSITION EVENTS
            SCAutoCompleted: secsgem.CollectionEventLink(SCAutoCompleted, []),
            SCAutoInitiated: secsgem.CollectionEventLink(SCAutoInitiated, []),
            SCPauseCompleted: secsgem.CollectionEventLink(SCPauseCompleted, []),
            SCPaused: secsgem.CollectionEventLink(SCPaused, []),
            SCPauseInitiated: secsgem.CollectionEventLink(SCPauseInitiated, []),

            # TRANSFER COMMAND STATE TRANSITION EVENTS
            TransferAbortCompleted: secsgem.CollectionEventLink(TransferAbortCompleted, [TransferAbortCompleted]),
            TransferAbortFailed: secsgem.CollectionEventLink(TransferAbortFailed, [TransferAbortFailed]),
            TransferAbortInitiated: secsgem.CollectionEventLink(TransferAbortInitiated, [TransferAbortInitiated]),
            TransferCancelCompleted: secsgem.CollectionEventLink(TransferCancelCompleted, [TransferCancelCompleted]),
            TransferCancelFailed: secsgem.CollectionEventLink(TransferCancelFailed, [TransferCancelFailed]),
            TransferCancelInitiated: secsgem.CollectionEventLink(TransferCancelInitiated, [TransferCancelInitiated]),
            TransferCompleted: secsgem.CollectionEventLink(TransferCompleted, [TransferCompleted]),
            TransferInitiated: secsgem.CollectionEventLink(TransferInitiated, [TransferInitiated]),
            TransferPaused: secsgem.CollectionEventLink(TransferPaused, [TransferPaused]),
            TransferResumed: secsgem.CollectionEventLink(TransferResumed, [TransferResumed]),

            # STOCKER CARRIER STATE TRANSITION EVENTS
            CarrierInstallCompleted: secsgem.CollectionEventLink(CarrierInstallCompleted, [CarrierInstallCompleted]),
            CarrierRemoveCompleted: secsgem.CollectionEventLink(CarrierRemoveCompleted, [CarrierRemoveCompleted]),
            CarrierRemoved: secsgem.CollectionEventLink(CarrierRemoved, [CarrierRemoved]),
            CarrierResumed: secsgem.CollectionEventLink(CarrierResumed, [CarrierResumed]),
            CarrierStored: secsgem.CollectionEventLink(CarrierStored, [CarrierStored]),
            CarrierStoredAlt: secsgem.CollectionEventLink(CarrierStoredAlt, [CarrierStoredAlt]),
            CarrierTransferring: secsgem.CollectionEventLink(CarrierTransferring, [CarrierTransferring]),
            CarrierWaitIn: secsgem.CollectionEventLink(CarrierWaitIn, [CarrierWaitIn]),
            CarrierWaitOut: secsgem.CollectionEventLink(CarrierWaitOut, [CarrierWaitOut]),
            ZoneCapacityChange: secsgem.CollectionEventLink(ZoneCapacityChange, [ZoneCapacityChange]),

            # STOCKER CRANE STATE TRANSITION EVENTS
            CraneActive: secsgem.CollectionEventLink(CraneActive, [CraneActive]),
            CraneIdle: secsgem.CollectionEventLink(CraneIdle, [CraneIdle]),
            CraneOutOfService: secsgem.CollectionEventLink(CraneOutOfService, [CraneOutOfService]),
            CraneInService: secsgem.CollectionEventLink(CraneInService, [CraneInService]),

            PortInService: secsgem.CollectionEventLink(PortInService, [PortInService]),
            PortOutOfService: secsgem.CollectionEventLink(PortOutOfService, [PortOutOfService]),
            PortTransferBlocked: secsgem.CollectionEventLink(PortTransferBlocked, [PortTransferBlocked]),
            PortReadyToLoad: secsgem.CollectionEventLink(PortReadyToLoad, [PortReadyToLoad]),
            PortReadyToUnload: secsgem.CollectionEventLink(PortReadyToUnload, [PortReadyToUnload]),
            PortTypeChange: secsgem.CollectionEventLink(PortTypeChange, [PortTypeChange]),

            # NON-TRANSITION EVENTS
            CarrierIDRead: secsgem.CollectionEventLink(CarrierIDRead, [CarrierIDRead]),
            CarrierLocateCompleted: secsgem.CollectionEventLink(CarrierLocateCompleted, [CarrierLocateCompleted]),
            IDReadError: secsgem.CollectionEventLink(IDReadError, [IDReadError]),
            OperatorInitiatedAction: secsgem.CollectionEventLink(OperatorInitiatedAction, [OperatorInitiatedAction]),
        })

        self.registered_collection_events[SCAutoCompleted].enabled=True
        self.registered_collection_events[SCAutoInitiated].enabled=True
        self.registered_collection_events[SCPauseCompleted].enabled=True
        self.registered_collection_events[SCPaused].enabled=True
        self.registered_collection_events[SCPauseInitiated].enabled=True
        
        self.registered_collection_events[TransferAbortCompleted].enabled=True
        self.registered_collection_events[TransferAbortFailed].enabled=True
        self.registered_collection_events[TransferAbortInitiated].enabled=True
        self.registered_collection_events[TransferCancelCompleted].enabled=True
        self.registered_collection_events[TransferCancelFailed].enabled=True
        self.registered_collection_events[TransferCancelInitiated].enabled=True
        self.registered_collection_events[TransferCompleted].enabled=True
        self.registered_collection_events[TransferInitiated].enabled=True
        self.registered_collection_events[TransferPaused].enabled=True
        self.registered_collection_events[TransferResumed].enabled=True

        self.registered_collection_events[CarrierInstallCompleted].enabled=True
        self.registered_collection_events[CarrierRemoveCompleted].enabled=True
        self.registered_collection_events[CarrierRemoved].enabled=True
        self.registered_collection_events[CarrierResumed].enabled=True
        self.registered_collection_events[CarrierStored].enabled=True
        self.registered_collection_events[CarrierStoredAlt].enabled=True
        self.registered_collection_events[CarrierTransferring].enabled=True
        self.registered_collection_events[CarrierWaitIn].enabled=True
        self.registered_collection_events[CarrierWaitOut].enabled=True
        self.registered_collection_events[ZoneCapacityChange].enabled=True

        self.registered_collection_events[PortInService].enabled=True
        self.registered_collection_events[PortOutOfService].enabled=True
        self.registered_collection_events[PortTransferBlocked].enabled=True
        self.registered_collection_events[PortReadyToLoad].enabled=True
        self.registered_collection_events[PortReadyToUnload].enabled=True

        self.registered_collection_events[CraneActive].enabled=True
        self.registered_collection_events[CraneIdle].enabled=True

        self.registered_collection_events[CarrierIDRead].enabled=True
        self.registered_collection_events[CarrierLocateCompleted].enabled=True
        self.registered_collection_events[IDReadError].enabled=True
        self.registered_collection_events[OperatorInitiatedAction].enabled=True


        #####################################
        #         Alarm Declaration
        #####################################
        ''' Alarm initial '''
        for ALID, DATA in AlarmTable.items():
            self.alarms.update({
                #alid: secsgem.Alarm((alid), "name", "text", secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, set_ce, clear_ce),
                ALID: secsgem.Alarm((ALID), DATA['text'], DATA['text'], secsgem.ALCD.PERSONAL_SAFETY | secsgem.ALCD.EQUIPMENT_SAFETY, ALID+100000, ALID+200000),
            })
            self.alarms[ALID].enabled=True


        #####################################
        #     Remote Command Declaration
        #####################################
        ''' Remote command '''
        self.remote_commands.clear()

        self.remote_commands.update({
            "ABORT": secsgem.RemoteCommand("ABORT", "abort command", ["COMMANDID"], None),
            "BOOK": secsgem.RemoteCommand("BOOK", "cancel command", ["PORTID"], None),
            "CANCEL": secsgem.RemoteCommand("CANCEL", "cancel command", ["COMMANDID"], None),
            "INSTALL": secsgem.RemoteCommand("INSTALL", "install command", ["CARRIERID", "CARRIERLOC"], None),
            "INFOUPDATE": secsgem.RemoteCommand("INFOUPDATE", "in foup date command", ["CARRIERID"], None, ["*"]), # Mike: 2021/08/11
            "LOCATE": secsgem.RemoteCommand("LOCATE", "locate command", ["CARRIERID"], None),
            "PAUSE": secsgem.RemoteCommand("PAUSE", "pause command", [], None),
            "REMOVE": secsgem.RemoteCommand("REMOVE", "remove command", ["CARRIERID"], None),
            "RENAME": secsgem.RemoteCommand("RENAME", "rename carrier command", ["CARRIERID", "CARRIERLOC"], None),
            "RESUME": secsgem.RemoteCommand("RESUME", "resume command", [], None),
            "RETRY": secsgem.RemoteCommand("RETRY", "retry command", ["ERRORID"], None),
            "STAGEDELETE": secsgem.RemoteCommand("STAGEDELETE", "stage delete command", [], None, ["STAGEID"]),
        })


        #####################################
        # Enhanced Remote Command Declaration
        #####################################
        ''' Enhance Remote command '''
        self.enhance_remote_commands.clear()

        self.enhance_remote_commands.update({
            "STAGE": secsgem.RemoteCommand("STAGE", "stage command", {"STAGEINFO":["STAGEID", "PRIORITY", "REPLACE", "EXPECTEDDURATION", "NOBLOCKINGTIME", "WAITTIMEOUT"], "TRANSFERINFO":["CARRIERID", "SOURCEPORT", "DESTPORT"]}, None, {"TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY"], "VEHICLEID":None}), # Mike: 2021/07/12
            "TRANSFER": secsgem.RemoteCommand("TRANSFER", "transfer command", {"COMMANDINFO":["COMMANDID", "PRIORITY"], "TRANSFERINFO":["CARRIERID", "SOURCE", "DEST"]}, None, {"TRANSFERINFO_CST":["LOT_ID","CARRIER_TYPE"] ,"STAGEIDLIST":None, "TRANSFERINFO":["CARRIERTYPE", "LOTID", "LOTTYPE", "CUSTID", "PRODUCT", "QUANTITY", "QTIME"], "EXECUTETIME":None, "CARRIERTYPE":None, "VEHICLEID":None}),
        })

        #####################################
        #          Control State 
        #####################################
        ''' SCState '''
        self.State=Fysom({
            'initial': "none",
            'events': [
                {'name': 'initial_done', 'src': 'SC_INIT', 'dst': 'PAUSED'},  # 2
                {'name': 'resume', 'src': ['PAUSED', 'PAUSING'], 'dst': 'AUTO'},  # 3, 6
                {'name': 'pause', 'src': 'AUTO', 'dst': 'PAUSING'},  # 4
                {'name': 'pause_completed', 'src': 'PAUSING', 'dst': 'PAUSED'},  # 5
            ],
            'callbacks': {
                'onSC_INIT': self._on_SC_state_SC_INIT,  # 
                'onPAUSED': self._on_SC_state_PAUSED,  # 
                'onAUTO': self._on_SC_state_AUTO,  # 
                'onPAUSING': self._on_SC_state_PAUSING,  # 
                'onbeforeinitial_done': self._on_SC_state_initial_done,  # 2, send collection event (SCPaused)
                'onbeforeresume': self._on_SC_state_resume,  # 3, 6, send collection event (SCAutoCompleted)
                'onbeforepause': self._on_SC_state_pause,  # 4, send collection event (SCPauseInitiated)
                'onbeforepause_completed': self._on_SC_state_pause_completed,  # 5, send collection event (SCPauseCompleted)
            },
            'autoforward': [
                {'src': 'none', 'dst': 'SC_INIT'},  # 1
            ]
        })


    #####################################
    #       Variable Callback
    #####################################
    def on_sv_value_request(self, svid, sv):
        if sv.svid == SV_SCState:
            value=self.SCState
            return sv.value_type(value)
        elif sv.svid == SV_EqpName:
            value=self.EqpName
            return sv.value_type(value)
        elif sv.svid == SV_EnhancedCarriers:
            L_EnhancedCarriers=[]
            for key, EnhancedCarrier in self.Carriers.Data.items():
                EnhancedCarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.CARRIERZONENAME, DI.INSTALLTIME, DI.CARRIERSTATE], [EnhancedCarrier.CarrierID, EnhancedCarrier.CarrierLoc, EnhancedCarrier.CarrierZoneName, EnhancedCarrier.InstallTime, EnhancedCarrier.CarrierState])
                L_EnhancedCarriers.append(EnhancedCarrierInfo_n)
            ret=secsgem.SecsVarArray(DI.ENHANCEDCARRIERSUNIT, L_EnhancedCarriers)
            return ret
        elif sv.svid == SV_EnhancedTransfers:
            L_EnhancedTransfers=[]
            for key, EnhancedTransfer in self.Transfers.Data.items():
                CommandInfo=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY], [EnhancedTransfer.CommandID, EnhancedTransfer.Priority])
                TransferInfo=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.DEST], [EnhancedTransfer.CarrierID, EnhancedTransfer.CarrierLoc, EnhancedTransfer.Dest])
                EnhancedTransferCommand_n=secsgem.SecsVarList([DI.TRANSFERSTATE, DI.COMMANDINFO, DI.TRANSFERINFO], [EnhancedTransfer.TransferState, CommandInfo, TransferInfo])
                L_EnhancedTransfers.append(EnhancedTransferCommand_n)
            ret=secsgem.SecsVarArray(DI.ENHANCEDTRANSFERSUNIT, L_EnhancedTransfers)
            return ret
        elif sv.svid == SV_EnhancedActiveZones:
            L_EnhancedActiveZones=[]
            for key, EnhancedActiveZone in self.Zones.Data.items():
                L_StockerUnitInfo=[]
                for key, StockerUnitInfo in EnhancedActiveZone.StockerUnit.items():
                    StokerUnitInfo_n=secsgem.SecsVarList([DI.STOCKERUNITID, DI.STOCKERUNITSTATE, DI.CARRIERID], [StockerUnitInfo['StockerUnitID'], StockerUnitInfo['StockerUnitState'], StockerUnitInfo['CarrierID']])
                    L_StockerUnitInfo.append(StokerUnitInfo_n)
                A_StockerUnitInfo=secsgem.SecsVarArray(DI.STOCKERUNITINFO, L_StockerUnitInfo)
                EnhancedZoneData_n=secsgem.SecsVarList([DI.ZONENAME, DI.ZONECAPACITY, DI.ZONESIZE, DI.ZONETYPE, DI.ZONESTATE, DI.STOCKERUNIT], [EnhancedActiveZone.ZoneName, EnhancedActiveZone.ZoneCapacity, EnhancedActiveZone.ZoneSize, EnhancedActiveZone.ZoneType, EnhancedActiveZone.ZoneState, A_StockerUnitInfo])
                L_EnhancedActiveZones.append(EnhancedZoneData_n)
            ret=secsgem.SecsVarArray(DI.ENHANCEDACTIVEZONESUNIT, L_EnhancedActiveZones)
            return ret
        elif sv.svid == SV_EnhancedPortData:
            L_EnhancedPorts=[]
            for key, EnhancedPort in self.Ports.Data.items():
                EnhancedPortInfo_n=secsgem.SecsVarList([DI.PORTID, DI.PORTSTATE, DI.PORTIOTYPE], [EnhancedPort.PortID, EnhancedPort.TransferState, EnhancedPort.PortIOType])
                L_EnhancedPorts.append(EnhancedPortInfo_n)
            ret=secsgem.SecsVarArray(DI.ENHANCEDPORTSUNIT, L_EnhancedPorts)
            return ret
        elif sv.svid == SV_ActiveCarriers:
            L_ActiveCarriers=[]
            for key, ActiveCarrier in self.Carriers.Data.items():
                CarrierInfo_n=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC], [ActiveCarrier.CarrierID, ActiveCarrier.CarrierLoc])
                L_ActiveCarriers.append(CarrierInfo_n)
            ret=secsgem.SecsVarArray(DI.ACTIVECARRIERSUNIT, L_ActiveCarriers)
            return ret
        elif sv.svid == SV_ActiveTransfers:
            L_ActiveTransfers=[]
            for key, ActiveTransfer in self.Transfers.Data.items():
                CommandInfo=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY], [ActiveTransfer.CommandID, ActiveTransfer.Priority])
                TransferInfo=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.DEST], [ActiveTransfer.CarrierID, ActiveTransfer.CarrierLoc, ActiveTransfer.Dest])
                TransferCommand_n=secsgem.SecsVarList([DI.COMMANDINFO, DI.TRANSFERINFO], [CommandInfo, TransferInfo])
                L_ActiveTransfers.append(TransferCommand_n)
            ret=secsgem.SecsVarArray(DI.ACTIVETRANSFERSUNIT, L_ActiveTransfers)
            return ret
        elif sv.svid == SV_ActiveZones:
            L_ActiveZones=[]
            for key, ActiveZone in self.Zones.Data.items():
                ZoneData_n=secsgem.SecsVarList([DI.ZONENAME, DI.ZONECAPACITY], [ActiveZone.ZoneName, ActiveZone.ZoneCapacity])
                L_ActiveZones.append(ZoneData_n)
            ret=secsgem.SecsVarArray(DI.ACTIVEZONESUNIT, L_ActiveZones)
            return ret
        # For inner use
        elif sv.svid == SV_EnhancedCarrierInfo:
            ret=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.CARRIERZONENAME, DI.INSTALLTIME, DI.CARRIERSTATE], [self.EnhancedCarrierInfo['CarrierID'], self.EnhancedCarrierInfo['CarrierLoc'], self.EnhancedCarrierInfo['CarrierZoneName'], self.EnhancedCarrierInfo['InstallTime'], self.EnhancedCarrierInfo['CarrierState']])
            return ret
        elif sv.svid == SV_EnhancedTransferCommand:
            CommandInfo=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY], [self.EnhancedTransferCommand['CommandInfo']['CommandID'], self.EnhancedTransferCommand['CommandInfo']['Priority']])
            TransferInfo=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.DEST], [self.EnhancedTransferCommand['TransferInfo']['CarrierID'], self.EnhancedTransferCommand['TransferInfo']['CarrierLoc'], self.EnhancedTransferCommand['TransferInfo']['Dest']])
            ret=secsgem.SecsVarList([DI.TRANSFERSTATE, DI.COMMANDINFO, DI.TRANSFERINFO], [self.EnhancedTransferCommand['TransferState'], CommandInfo, TransferInfo])
            return ret
        elif sv.svid == SV_EnhancedZoneData:
            ret=secsgem.SecsVarList([DI.ZONENAME, DI.ZONECAPACITY, DI.ZONESIZE, DI.ZONETYPE], [self.EnhancedZoneData['ZoneName'], self.EnhancedZoneData['ZoneCapacity'], self.EnhancedZoneData['ZoneSize'], self.EnhancedZoneData['ZoneType']])
            return ret
        elif sv.svid == SV_TransferCommand:
            CommandInfo=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY], [self.TransferCommand['CommandInfo']['CommandID'], self.TransferCommand['CommandInfo']['Priority']])
            TransferInfo=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.DEST], [self.TransferCommand['TransferInfo']['CarrierID'], self.TransferCommand['TransferInfo']['CarrierLoc'], self.TransferCommand['TransferInfo']['Dest']])
            ret=secsgem.SecsVarList([DI.COMMANDINFO, DI.TRANSFERINFO], [CommandInfo, TransferInfo])
            return ret
        elif sv.svid == SV_CarrierInfo:
            ret=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC], [self.CarrierInfo['CarrierID'], self.CarrierInfo['CarrierLoc']])
            return ret
        elif sv.svid == SV_CommandInfo:
            ret=secsgem.SecsVarList([DI.COMMANDID, DI.PRIORITY], [self.CommandInfo['CommandID'], self.CommandInfo['Priority']])
            return ret
        elif sv.svid == SV_StockerUnitInfo:
            ret=secsgem.SecsVarList([DI.STOCKERUNITID, DI.STOCKERUNITSTATE], [self.StockerUnitInfo['StockerUnitID'], self.StockerUnitInfo['StockerUnitState']])
            return ret
        elif sv.svid == SV_TransferInfo:
            ret=secsgem.SecsVarList([DI.CARRIERID, DI.CARRIERLOC, DI.DEST], [self.TransferInfo['CarrierID'], self.TransferInfo['CarrierLoc'], self.TransferInfo['Dest']])
            return ret
        elif sv.svid == SV_ZoneData:
            ret=secsgem.SecsVarList([DI.ZONENAME, DI.ZONECAPACITY], [self.ZoneData['ZoneName'], self.ZoneData['ZoneCapacity']])
            return ret
        elif sv.svid == SV_CarrierID:
            value=self.CarrierID
            return sv.value_type(value)
        elif sv.svid == SV_CarrierLoc:
            value=self.CarrierLoc
            return sv.value_type(value)
        elif sv.svid == SV_CarrierType: # chocp: 2022/1/2
            value=self.CarrierType
            return sv.value_type(value)
        elif sv.svid == SV_CarrierState:
            value=self.CarrierState
            return sv.value_type(value)
        elif sv.svid == SV_CarrierZoneName:
            value=self.CarrierZoneName
            return sv.value_type(value)
        elif sv.svid == SV_CommandID:
            value=self.CommandID
            return sv.value_type(value)
        elif sv.svid == SV_CommandType:
            value=self.CommandType
            return sv.value_type(value)
        elif sv.svid == SV_Dest:
            value=self.Dest
            return sv.value_type(value)
        elif sv.svid == SV_EmptyCarrier:
            value=self.EmptyCarrier
            return sv.value_type(value)
        elif sv.svid == SV_DeviceID:
            value=self.DeviceID
            return sv.value_type(value)
        elif sv.svid == SV_ErrorID:
            value=self.ErrorID
            return sv.value_type(value)
        elif sv.svid == SV_HandoffType:
            value=self.HandoffType
            return sv.value_type(value)
        elif sv.svid == SV_IDReadStatus:
            value=self.IDReadStatus
            return sv.value_type(value)
        elif sv.svid == SV_InstallTime:
            value=self.InstallTime
            return sv.value_type(value)
        elif sv.svid == SV_PortType:
            value=self.PortType
            return sv.value_type(value)
        elif sv.svid == SV_Priority:
            value=self.Priority
            return sv.value_type(value)
        elif sv.svid == SV_RecoveryOptions:
            value=self.RecoveryOptions
            return sv.value_type(value)
        elif sv.svid == SV_ResultCode: # U2
            value=self.ResultCode
            return sv.value_type(value)
        elif sv.svid == SV_Source:
            value=self.Source
            return sv.value_type(value)
        elif sv.svid == SV_StockerCraneID:
            value=self.StockerCraneID
            return sv.value_type(value)
        elif sv.svid == SV_StockerUnitID:
            value=self.StockerUnitID
            return sv.value_type(value)
        elif sv.svid == SV_StockerUnitState:
            value=self.StockerUnitState
            return sv.value_type(value)
        elif sv.svid == SV_TransferState:
            value=self.TransferState
            return sv.value_type(value)
        elif sv.svid == SV_PortID:
            value=self.PortID
            return sv.value_type(value)
        elif sv.svid == SV_PortIOType:
            value=self.PortIOType
            return sv.value_type(value)
        elif sv.svid == SV_ZoneCapacity:
            value=self.ZoneCapacity
            return sv.value_type(value)
        elif sv.svid == SV_ZoneName:
            value=self.ZoneName
            return sv.value_type(value)
        elif sv.svid == SV_ZoneSize:
            value=self.ZoneSize
            return sv.value_type(value)
        elif sv.svid == SV_ZoneType:
            value=self.ZoneType
            return sv.value_type(value)
        elif sv.svid == SV_ALTX: # Mike: 2021/11/08
            value=self.ALTX
            return sv.value_type(value)
        elif sv.svid == SV_ALSV: # Mike: 2021/11/08
            value=self.ALSV
            return sv.value_type(value)
        elif sv.svid == SV_UnitType: # Mike: 2021/11/29
            value=self.UnitType
            return sv.value_type(value)
        elif sv.svid == SV_UnitID: # Mike: 2021/11/29
            value=self.UnitID
            return sv.value_type(value)
        elif sv.svid == SV_Level: # Mike: 2021/12/01
            value=self.Level
            return sv.value_type(value)
        elif sv.svid == SV_SubCode: # Chi: 2022/06/17
            value=self.SubCode
            return sv.value_type(value)


        '''
        def on_dv_value_request(self, dvid, dv):
        if dv.dvid=1:
            dv_list=secsgem.SecsVarList([
                secsgem.AAA,
            ])
            dv_list.AAA=AAA
            return dv_list
        '''

    #####################################
    #      Stream Function Callback
    #####################################
    def _on_s02f15(self, handler, packet):
        return self.stream_function(9, 5)() # Function Disable (New EC)

    def _on_s06f23(self, handler, packet):
        return self.stream_function(6, 0)() # Function Disable (spool)

    def _on_s02f17(self, handler, packet):
        """Callback handler for Stream 2, Function 17, Request online

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        if self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"]:
            return self.stream_function(2, 0)()

        del handler, packet  # unused parameters

        TIME=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]

        return self.stream_function(2, 18)(TIME)

    def _on_s02f31(self, handler, packet):
        """Callback handler for Stream 2, Function 31, Request online

        :param handler: handler the message was received on
        :type handler: :class:`self.secsgem_e82_hsms.handler.HsmsHandler`
        :param packet: complete message received
        :type packet: :class:`self.secsgem_e82_hsms.packets.HsmsPacket`
        """
        if self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"]:
            return self.stream_function(2, 0)()

        del handler  # unused parameters

        message=self.secs_decode(packet)
        TIME=message.get() # TIME='YYYYmmddHHMMSSXX'

        # set system date
        if len(TIME) not in [14, 16]:
            return self.stream_function(2, 32)(secsgem.TIACK.ERROR)

        YY=TIME[0:4]
        mm=TIME[4:6]
        dd=TIME[6:8]
        HH=TIME[8:10]
        MM=TIME[10:12]
        SS=TIME[12:14]
        XX=TIME[14:16] if len(TIME) == 16 else '00'

        TIME="{}{}{} {}:{}:{}.{}".format(YY,mm,dd,HH,MM,SS,XX)

        print ("set time: {}".format(TIME))
        return self.stream_function(2, 32)(secsgem.TIACK.OK)

        commands.getoutput("sudo timedatectl set-ntp off")
        msg=commands.getoutput('sudo date -s "'+TIME+'"')

        if "cst" not in msg:
            commands.getoutput("sudo timedatectl set-ntp on")
            return self.stream_function(2, 32)(secsgem.TIACK.ERROR)

        return self.stream_function(2, 32)(secsgem.TIACK.OK)

    def set_alarm(self, alid, alarmlevel =''): # Mike: 2021/11/26
        """The list of the alarms

        :param alid: Alarm id
        :type alid: str/int
        """
        if alid not in self.alarms:
            raise ValueError("Unknown alarm id {}".format(alid))

        '''if not self.alarms[alid].set:
            return'''

        if self.alarms[alid].enabled:
            if not self._spool_enable and (self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"] or not self.communicationState.isstate("COMMUNICATING")):
                pass
            else:
                try:
                    self.send_prime_message(self.stream_function(5, 1)({"ALCD": self.alarms[alid].code | secsgem.ALCD.ALARM_SET , \
                        "ALID": alid, "ALTX": self.alarms[alid].text}))
                except Exception as err:
                    self.send_stream_function(self.stream_function(9, 9)())
                    raise Exception(err)
        
        self.alarms[alid].set=True

        self.trigger_collection_events([self.alarms[alid].ce_on])

    def clear_alarm(self, alid, alarmlevel =''): # Mike: 2021/11/26
        """The list of the alarms

        :param alid: Alarm id
        :type alid: str/int
        """
        if alid not in self.alarms:
            raise ValueError("Unknown alarm id {}".format(alid))

        '''if not self.alarms[alid].set:
            return'''

        if self.alarms[alid].enabled:
            if not self._spool_enable and (self.controlState.current not in ["ONLINE", "ONLINE_LOCAL", "ONLINE_REMOTE"] or not self.communicationState.isstate("COMMUNICATING")):
                pass
            else:
                try:
                    self.send_prime_message(self.stream_function(5, 1)({"ALCD": self.alarms[alid].code , "ALID": alid, "ALTX": self.alarms[alid].text}))
                except Exception as err:
                    self.send_stream_function(self.stream_function(9, 9)())
                    raise Exception(err)

        self.alarms[alid].set=False

        self.trigger_collection_events([self.alarms[alid].ce_off])

    #####################################
    #      Remote Command Callback
    #####################################
    def _on_rcmd_ABORT(self, COMMANDID, system, ack_params):
        print("\nget abort cmd, param:{}".format([COMMANDID]))
        print("get abort cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if COMMANDID not in self.Transfers.Data:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4] and self.Transfers.Data[COMMANDID].TransferState in [3, 2] and self.Carriers.Data[self.Transfers.Data[COMMANDID].CarrierID].CarrierState in [5, 2, 1, 3]:
            obj={}
            obj['remote_cmd']='abort'
            obj['CommandID']=COMMANDID
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            self.COMMANDID=COMMANDID
            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.ResultCode=2
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.transfer_abort(COMMANDID)
        else:
            print("\nabort cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_AUTO(self, ZONENAME, system, ack_params):
        print("\nget auto cmd, param:{}".format([]))
        print("get auto cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if self.SCState in [3, 2, 4]:
            obj={}
            obj['remote_cmd']='auto'
            obj['ZoneName']=ZONENAME
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

        else:
            print("\nauto cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_BOOK(self, PORTID, system, ack_params):
        print("\nget book cmd, param:{}".format([PORTID]))
        print("get book cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if PORTID not in self.Ports.Data:
            ack_params.append(['PORTID', 2])
            print("\PORTID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4]:
            # self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            obj={}
            obj['remote_cmd']='book'
            obj['PortID']=PORTID
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            remotecmd_queue.append(obj)

        else:
            print("\nbook cmd can not perform now. ({})\n".format(self.SCState))
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_CANCEL(self, COMMANDID, system, ack_params):
        print("\nget cancel cmd, param:{}".format([COMMANDID]))
        print("get cancel cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if COMMANDID not in self.Transfers.Data:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4] and self.Transfers.Data[COMMANDID].TransferState in [1]:
            obj={}
            obj['remote_cmd']='cancel'
            obj['CommandID']=COMMANDID
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.transfer_cancel(COMMANDID)
        else:
            print("\ncancel cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_INSTALL(self, CARRIERID, CARRIERLOC, system, ack_params):
        print("\nget install cmd, param:{}".format([CARRIERID, CARRIERLOC]))
        print("get install cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if CARRIERID not in self.Carriers.Data:
            ack_params.append(['CARRIERID', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4]:
            obj={}
            obj['remote_cmd']='install'
            obj['CarrierID']=CARRIERID
            obj['CarrierLoc']=CARRIERLOC
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.carrier_add(CARRIERID, CARRIERLOC, self.Zones.ZoneMap.get(CARRIERLOC, ''))
        else:
            print("\ninstall cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_INFOUPDATE(self, CARRIERID, system, ack_params, **kwargs): # Mike: 2021/08/11
        print("\nget infoupedate cmd, param:{}".format([CARRIERID, kwargs]))
        print("get infoupedate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        if CARRIERID not in self.Carriers.Data:
            ack_params.append(['CARRIERID', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4]:
            obj={}
            obj['remote_cmd']='infoupdate'
            obj['CarrierID']=CARRIERID
            obj['Data']={}
            for key, value in kwargs.items():
                obj['Data'][key]=value
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0]), system)
        else:
            print("\nlocate cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_LOCATE(self, CARRIERID, system, ack_params): # Mike: 2020/08/18
        print("\nget locate cmd, param:{}".format([CARRIERID]))
        print("get locate cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if CARRIERID and CARRIERID not in self.Carriers.Data:
            ack_params.append(['CARRIER', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4]:
            obj={}
            obj['remote_cmd']='locate'
            obj['CarrierID']=CARRIERID
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            if CARRIERID:
                self.carrier_locate(CARRIERID)
                for key, value in self.failure_map:
                    if value == CARRIERID:
                        self.carrier_locate(key)
            else:
                for carrier in self.Carriers.Data:
                    self.carrier_locate(carrier)
        else:
            print("\nlocate cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_MANUAL(self, ZONENAME, system, ack_params):
        print("\nget manual cmd, param:{}".format([]))
        print("get manual cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if self.SCState in [3, 2, 4]:
            obj={}
            obj['remote_cmd']='manual'
            obj['ZoneName']=ZONENAME
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

        else:
            print("\nmanual cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_PAUSE(self, system, ack_params):
        print("\nget pause cmd, param:{}".format([]))
        print("get pause cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if self.SCState in [3]:
            obj={}
            obj['remote_cmd']='sc_pause' #2022/08/09 Chi 
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.pause()
        else:
            print("\npause cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_REMOVE(self, CARRIERID, system, ack_params):
        print("\nget remove cmd, param:{}".format([]))
        print("get remove cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if CARRIERID not in self.Carriers.Data:
            ack_params.append(['CARRIERID', 2])
            print("\nCarrierID not found.\n")
            self.send_response(self.stream_function(2,42)([3, ack_params]), system)
        elif self.SCState in [3, 2, 4] and self.Carriers.Data[CARRIERID].CarrierState in [5, 4, 1, 3]:
            obj={}
            obj['remote_cmd']='remove'
            obj['CarrierID']=CARRIERID
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.carrier_kill(CARRIERID)
        else:
            print("\nremove cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_RENAME(self, CARRIERID, CARRIERLOC, system, ack_params):
        #print("get rename cmd\n")
        #print("get rename cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))
        obj={}
        obj['remote_cmd']='rename'
        obj['CarrierID']=CARRIERID
        obj['CarrierLoc']=CARRIERLOC
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([0]), system)
        remotecmd_queue.append(obj)

    def _on_rcmd_RESUME(self, system, ack_params):
        print("\nget resume cmd, param:{}".format([]))
        print("get resume cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if self.SCState in [2, 4]:
            obj={}
            obj['remote_cmd']='sc_resume'  #2022/08/09 Chi 
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)

            self.resume()
        else:
            print("\nresume cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_RETRY(self, ERRORID, system, ack_params):
        print("\nget retry cmd, param:{}".format([ERRORID]))
        print("get retry cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        if False and self.active_alarms and self.SCState in [3, 2, 4] and self.Transfers.Data[self.active_alarms[ERRORID]['CommandID']].TransferState in [3]:
            obj={}
            obj['remote_cmd']='retry'
            obj['ErrorID']=ERRORID
            obj['system']=system
            obj['ack_params']=ack_params

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2,42)([0, ack_params]), system)
        else:
            print("\nretry cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_rcmd_STAGEDELETE(self, system, ack_params, STAGEID=''): # Mike: 2020/08/18
        #print("get stage delete cmd, param:{}\n", STAGEID)
        #print("get stage delete cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        obj={}
        obj['remote_cmd']='stagedelete'
        obj['StageID']=STAGEID
        obj['system']=system
        obj['ack_params']=ack_params
        obj['handle']=self
        # self.send_response(self.stream_function(2,42)([4]), system)
        remotecmd_queue.append(obj)

    def _on_ercmd_STAGE(self, STAGEINFO, TRANSFERINFO, system, ack_params, **kwargs): # Mike: 2020/08/18
        print("get stage cmd, param:{}, {}\n", STAGEINFO, TRANSFERINFO)
        #print("get stage cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        StageID=STAGEINFO[0][0][1]
        Priority=STAGEINFO[0][1][1]
        CarrierID=TRANSFERINFO[0][0][1]
        Source=TRANSFERINFO[0][1][1]
        Dest=TRANSFERINFO[0][2][1]

        if StageID in self.Transfers.Data:
            ack_params.append(['STAGEID', 2])
            print("\nStageID already exists.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        elif not StageID:
            ack_params.append(['STAGEID', 2])
            print("\nStageID can not be empty.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        # elif CarrierID not in self.Carriers.Data:
        #     ack_params.append(['CARRIERID', 2])
        #     print("\CARRIERID not found.\n")
        #     self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        elif Priority > 101:
            ack_params.append(['PRIORITY', 2])
            print("\PRIORITY error.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        # elif self.SCState in [3, 2, 4] and StageID not in self.Transfers.Data and self.Carriers.Data[CarrierID].CarrierState in [1, 4]:
        elif self.SCState in [3, 2, 4] and StageID not in self.Transfers.Data :

            obj={}
            obj['remote_cmd']='transfer'
            obj['stageinfo']={'StageID':StageID, 'Priority':Priority}
            obj['transferinfo']={'CarrierID':CarrierID, 'Source':Source, 'Dest':Dest}
            obj['stageIDlist']=kwargs.get("STAGEIDLIST", [[]])[0]
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            obj['CARRIERTYPE']=kwargs.get('CARRIERTYPE', [])
            obj['EXECUTETIME']=kwargs.get('EXECUTETIME', [''])
            obj['VEHICLEID']=kwargs.get('VEHICLEID', [''])

            #D_TransferInfo={} #chocp fix
            self.StageInfo={}
            self.StageInfo["StageID"]=STAGEINFO[0][0][1]
            self.StageInfo["Priority"]=STAGEINFO[0][1][1]
            self.StageInfo["ExpectedDuration"]=STAGEINFO[0][3][1]
            self.StageInfo["NoBlockingTime"]=STAGEINFO[0][4][1]
            self.StageInfo["WaitTimeout"]=STAGEINFO[0][5][1]

            #D_TransferInfo={} #chocp fix
            self.TransferInfo={}
            self.TransferInfo["CarrierID"]=TRANSFERINFO[0][0][1]
            self.TransferInfo["SourcePort"]=TRANSFERINFO[0][1][1]
            self.TransferInfo["DestPort"]=TRANSFERINFO[0][2][1]

            self.TransferInfoList=[] # Mike: 2021/07/27
            for Trans in TRANSFERINFO:
                Transfer={}
                Transfer["CarrierID"]=Trans[0][1]
                Transfer["SourcePort"]=Trans[1][1]
                Transfer["DestPort"]=Trans[2][1]
                for t in Trans[3:]:
                    if t[0] == "CARRIERTYPE":
                        Transfer["CarrierType"]=t[1]
                    elif t[0] == "LOTID":
                        Transfer["LotID"]=t[1]
                    elif t[0] == "LOTTYPE":
                        Transfer["LotType"]=t[1]
                    elif t[0] == "CUSTID":
                        Transfer["CustID"]=t[1]
                    elif t[0] == "PRODUCT":
                        Transfer["Product"]=t[1]
                    elif t[0] == "QUANTITY":
                        Transfer["Quantity"]=t[1]
                    else:
                        pass
                self.TransferInfoList.append(Transfer)

            obj={}
            obj['remote_cmd']='stage'
            obj['stageinfo']=self.StageInfo
            # obj['transferinfo']=self.TransferInfo # Mike: 2021/07/27
            obj['transferinfolist']=self.TransferInfoList # Mike: 2021/07/27
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            obj['VEHICLEID']=kwargs.get('VEHICLEID', [''])
            # self.send_response(self.stream_function(2,50)([4]), system)
            # remotecmd_queue.append(obj)

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            # if self.rcmd_auto_reply:
            #     self.send_response(self.stream_function(2, 50)([0, ack_params]), system)

            # self.transfer_cmd(StageID, Priority, CarrierID, Source, Dest)
        else:
            print("\nstage cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    def _on_ercmd_TRANSFER(self, COMMANDINFO, TRANSFERINFO, system, ack_params, **kwargs):
        print("\nget transfer cmd, param:{}".format([COMMANDINFO, TRANSFERINFO]))
        print("get transfer cmd, system:{}, ack_parmas:{}\n".format(system, ack_params))

        CommandID=COMMANDINFO[0][0][1]
        Priority=COMMANDINFO[0][1][1]
        CarrierID=TRANSFERINFO[0][0][1]
        Source=TRANSFERINFO[0][1][1]
        Dest=TRANSFERINFO[0][2][1]

        if CommandID in self.Transfers.Data:
            ack_params.append(['COMMANDID', 2])
            print("\nCommandID already exists.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        elif CarrierID not in self.Carriers.Data:
            ack_params.append(['CARRIERID', 2])
            print("\CARRIERID not found.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
        elif Priority > 100:
            ack_params.append(['PRIORITY', 2])
            print("\PRIORITY error.\n")
            self.send_response(self.stream_function(2,50)([3, ack_params]), system)
            return
        elif self.SCState in [3, 2, 4] and CommandID not in self.Transfers.Data and self.Carriers.Data[CarrierID].CarrierState in [1, 4]:

            obj={}
            obj['remote_cmd']='transfer'
            obj['commandinfo']={'CommandID':CommandID, 'Priority':Priority}
            obj['transferinfo']={'CarrierID':CarrierID, 'Source':Source, 'Dest':Dest}
            obj['transferinfolist']=[{'CarrierID':CarrierID, 'SourcePort':Source, 'DestPort':Dest}]
            obj['stageIDlist']=kwargs.get("STAGEIDLIST", [[]])[0]
            obj['system']=system
            obj['ack_params']=ack_params
            obj['handle']=self
            obj['CARRIERTYPE']=kwargs.get('CARRIERTYPE', [])
            obj['EXECUTETIME']=kwargs.get('EXECUTETIME', [''])
            obj['VEHICLEID']=kwargs.get('VEHICLEID', [''])

            if self.remote_commands_callback:
                th=threading.Thread(target=self.remote_commands_callback, args=(obj,))
                th.setDaemon(True)
                th.start()
            else:
                remotecmd_queue.append(obj)

            '''if self.rcmd_auto_reply:
                self.send_response(self.stream_function(2, 50)([0, ack_params]), system)'''

            # self.transfer_cmd(CommandID, Priority, CarrierID, Source, Dest)
        else:
            print("\ntransfer cmd can not perform now.\n")
            self.send_response(self.stream_function(2,42)([2, ack_params]), system)

    #####################################
    #       State Machine Callback
    #####################################
    ''' SCState '''

    def _on_SC_state_SC_INIT(self, _):  # 
        self.SCState=1

    def _on_SC_state_PAUSED(self, _):  # 
        self.SCState=2

    def _on_SC_state_AUTO(self, _):  # 
        self.SCState=3

    def _on_SC_state_PAUSING(self, _):  # 
        self.SCState=4

    def _on_SC_state_initial(self, _):  # 1, send collection event (SCAutoInitiated)
        self.trigger_collection_events([SCAutoInitiated])

    def _on_SC_state_initial_done(self, _):  # 2, send collection event (SCPaused)
        self.trigger_collection_events([SCPaused])

    def _on_SC_state_resume(self, _):  # 3, 6, send collection event (SCAutoCompleted)
        self.trigger_collection_events([SCAutoCompleted])

    def _on_SC_state_pause(self, _):  # 4, send collection event (SCPauseInitiated)
        self.trigger_collection_events([SCPauseInitiated])

    def _on_SC_state_pause_completed(self, _):  # 5, send collection event (SCPauseCompleted)
        self.trigger_collection_events([SCPauseCompleted])

    #####################################
    #       Normal Function Define
    #####################################
    def initial(self):
        self.State.initial_done()

    def pause(self):
        self.State.pause()
        th=threading.Thread(target=self.pausing,)
        th.setDaemon(True)
        th.start()
    
    def pausing(self):
        check=True
        while check:
            if self.SCState != 4:
                break
            check=False
            for key, TransferCommand in self.Transfers.Data.items():
                if TransferCommand.TransferState not in [0, 1]:
                    check=True
            sleep(0.5)
        else:
            self.State.pause_completed()

    def resume(self):
        self.State.resume()

    def carrier_wait_in(self, CARRIERID, CARRIERLOC, CARRIERZONENAME, NoIDRead=False):
        if CARRIERID not in self.Carriers.Data:
            self.Carriers.Data[CARRIERID]=Carrier(self, CARRIERID)
            self.Carriers.Data[CARRIERID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
        if not NoIDRead:
            self.Carriers.Data[CARRIERID].CarrierIDRead=CARRIERID
        last_zone=self.Carriers.Data[CARRIERID].CarrierZoneName
        self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
        self.Carriers.Data[CARRIERID].CarrierZoneName=CARRIERZONENAME
        self.Carriers.Data[CARRIERID].State.wait_in()
        if last_zone != CARRIERZONENAME:
            if last_zone:
                self.Zones.Data[last_zone].capacity_increase()
            self.Zones.Data[CARRIERZONENAME].capacity_decrease()

    def carrier_transfer(self, CARRIERID, DEST, CRANEID, COMMANDID):
        if CARRIERID in self.Carriers.Data:
            self.Carriers.Data[CARRIERID].Dest=DEST
            self.Carriers.Data[CARRIERID].StockerCraneID=CRANEID
            self.Carriers.Data[CARRIERID].CommandID=COMMANDID
            if self.Carriers.Data[CARRIERID].State.current == 'ALTERNATE':
                self.Carriers.Data[CARRIERID].State.alternated_transfer()
            else:
                self.Carriers.Data[CARRIERID].State.transfer()
            self.Zones.Data[self.Carriers.Data[CARRIERID].CarrierZoneName].capacity_increase()
            return True
        return False

    def carrier_store(self, CARRIERID, CARRIERLOC, CARRIERZONENAME):
        if CARRIERID in self.Carriers.Data:
            self.Carriers.Data[CARRIERID].Dest=''
            self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
            self.Carriers.Data[CARRIERID].CarrierZoneName=CARRIERZONENAME
            self.Carriers.Data[CARRIERID].State.store()
            self.Zones.Data[CARRIERZONENAME].capacity_decrease()
            return True
        return False

    def carrier_wait_out(self, CARRIERID, CARRIERLOC, CARRIERZONENAME, PORTTYPE):
        if CARRIERID not in self.Carriers.Data:
            self.Carriers.Data[CARRIERID]=Carrier(self, CARRIERID)
            self.Carriers.Data[CARRIERID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
        if self.Carriers.Data[CARRIERID].State.current not in ['none', 'TRANSFERING', 'WAIT_OUT', 'WAIT_OUT_2']:
            return False
        last_state=self.Carriers.Data[CARRIERID].State.current
        last_zone=self.Carriers.Data[CARRIERID].CarrierZoneName
        self.Carriers.Data[CARRIERID].Dest=''
        self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
        self.Carriers.Data[CARRIERID].CarrierZoneName=CARRIERZONENAME
        self.Carriers.Data[CARRIERID].PortType=PORTTYPE
        self.Carriers.Data[CARRIERID].State.wait_out()
        if last_zone != CARRIERZONENAME:
            if last_zone:
                self.Zones.Data[last_zone].capacity_increase()
            self.Zones.Data[CARRIERZONENAME].capacity_decrease()
        return True

    def carrier_remove(self, CARRIERID, HANDOFFTYPE):
        if CARRIERID in self.Carriers.Data:
            self.Carriers.Data[CARRIERID].HandoffType=HANDOFFTYPE
            self.Carriers.Data[CARRIERID].State.remove()
            self.Zones.Data[self.Carriers.Data[CARRIERID].CarrierZoneName].capacity_increase()
            while self.Carriers.Data[CARRIERID].State.current != 'none':
                sleep(0.5)
            del self.Carriers.Data[CARRIERID]
            return True
        return False

    def carrier_alternated(self, CARRIERID, COMMANDID, CARRIERLOC, CARRIERZONENAME, DEST):
        if CARRIERID in self.Carriers.Data:
            self.Carriers.Data[CARRIERID].CommandID=COMMANDID
            self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
            self.Carriers.Data[CARRIERID].CarrierZoneName=CARRIERZONENAME
            self.Carriers.Data[CARRIERID].Dest=DEST
            self.Carriers.Data[CARRIERID].State.alternated()
            self.Zones.Data[CARRIERZONENAME].capacity_decrease()
            return True
        return False

    def carrier_resume(self, CARRIERID):
        if CARRIERID in self.Carriers.Data:
            self.Carriers.Data[CARRIERID].State.resume()
            self.Zones.Data[self.Carriers.Data[CARRIERID].CarrierZoneName].capacity_increase()
            return True
        return False

    def carrier_add(self, CARRIERID, CARRIERLOC, CARRIERZONENAME):
        Zone=CARRIERZONENAME
        if not Zone:
            Zone=self.Zones.ZoneMap.get(CARRIERLOC, '')
        if CARRIERID not in self.Carriers.Data:
            self.Carriers.Data[CARRIERID]=Carrier(self, CARRIERID)
            self.Carriers.Data[CARRIERID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
            self.Carriers.Data[CARRIERID].CarrierID=CARRIERID
            self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
            self.Carriers.Data[CARRIERID].CarrierZoneName=Zone
            self.Carriers.Data[CARRIERID].State.add_carrier()
            if Zone:
                self.Zones.Data[Zone].capacity_decrease()
            return True
        else:
            last_zone=self.Carriers.Data[CARRIERID].CarrierZoneName
            self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
            if Zone:
                self.Carriers.Data[CARRIERID].CarrierZoneName=Zone
            self.Carriers.Data[CARRIERID].State.mod_carrier()
            if Zone:
                if last_zone != Zone:
                    self.Zones.Data[last_zone].capacity_increase()
                    self.Zones.Data[Zone].capacity_decrease()

    def carrier_kill(self, CARRIERID):
        if CARRIERID in self.Carriers.Data:
            self.Zones.Data[self.Carriers.Data[CARRIERID].CarrierZoneName].capacity_increase()
            self.Carriers.Data[CARRIERID].State.kill_carrier()
            while self.Carriers.Data[CARRIERID].State.current != 'none':
                sleep(0.5)
            del self.Carriers.Data[CARRIERID]
            return True
        return False
    
    def carrier_locate(self, CARRIERID):
        if CARRIERID:
            if CARRIERID in self.Carriers.Data:
                self.Carriers.Data[CARRIERID].locate()
                return True
            return False
        else:
            for CarrierID in self.Carriers.Data:
                self.Carriers.Data[CARRIERID].locate()
            return True
    
    def carrier_id_read(self, CARRIERID, CARRIERLOC, IDREADSTATUS):
        if CARRIERID and CARRIERID not in self.Carriers.Data:
            self.Carriers.Data[CARRIERID]=Carrier(self, CARRIERID)
            self.Carriers.Data[CARRIERID].CarrierID=CARRIERID
            self.Carriers.Data[CARRIERID].CarrierLoc=CARRIERLOC
            self.Carriers.Data[CARRIERID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
            self.Carriers.Data[CARRIERID].id_read(CARRIERID, IDREADSTATUS)
            return ''
        else:
            ID=FailureIDGEN(CARRIERLOC, CARRIERID)
            self.Carriers.Data[ID]=Carrier(self, ID)
            self.Carriers.Data[ID].CarrierID=ID
            self.Carriers.Data[ID].InstallTime=datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]
            self.Carriers.Data[ID].id_read(ID, 2)
            return ID
    
    def carrier_rename(self, CARRIERID, NEWCARRIERID):
        return self.Carriers.mod(CARRIERID, NEWCARRIERID)
    
    def zone_capacity_change(self, ZONENAME, CAPACITY):
        self.Zones.Data[ZONENAME].zone_capacity_change(CAPACITY)

    def transfer_cmd(self, COMMANDID, PRIORITY, CARRIERID, CARRIERLOC, DEST):
        if COMMANDID not in self.Transfers.Data:
            self.Transfers.Data[COMMANDID]=TransferCommand(self, COMMANDID)
            self.Transfers.Data[COMMANDID].CarrierID=CARRIERID
            self.Transfers.Data[COMMANDID].CarrierLoc=CARRIERLOC
            if CARRIERID in self.Carriers.Data:
                self.Transfers.Data[COMMANDID].CarrierLoc=self.Carriers.Data[CARRIERID].CarrierLoc
                self.Transfers.Data[COMMANDID].CarrierZoneName=self.Carriers.Data[CARRIERID].CarrierZoneName
            self.Transfers.Data[COMMANDID].Dest=DEST
            self.Transfers.Data[COMMANDID].Priority=PRIORITY
            self.Transfers.Data[COMMANDID].State.queue()

    def transfer_queue(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.queue()

    def transfer_start(self, COMMANDID, STOCKERCRANEID):
        self.Transfers.Data[COMMANDID].StockerCraneID=STOCKERCRANEID
        self.Transfers.Data[COMMANDID].State.transfer()
        self.carrier_transfer(self.Transfers.Data[COMMANDID].CarrierID, self.Transfers.Data[COMMANDID].Dest, STOCKERCRANEID, COMMANDID)

    def transfer_pause(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.pause()

    def transfer_resume(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.resume()

    def transfer_complete(self, COMMANDID, DEST='', RESULTCODE=0):
        if DEST:
            self.Transfers.Data[COMMANDID].Dest=DEST
        if RESULTCODE:
            self.Transfers.Data[COMMANDID].ResultCode=RESULTCODE
        self.Transfers.Data[COMMANDID].State.complete()
        while self.Transfers.Data[COMMANDID].State.current != 'none':
            sleep(0.5)
        del self.Transfers.Data[COMMANDID]

    def transfer_cancel(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.cancel()

    def transfer_cancel_succ(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.cancel_completed()
        while self.Transfers.Data[COMMANDID].State.current != 'none':
            sleep(0.5)
        del self.Transfers.Data[COMMANDID]

    def transfer_cancel_failed(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.cancel_failed()

    def transfer_abort(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.abort()

    def transfer_abort_succ(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.abort_completed()
        while self.Transfers.Data[COMMANDID].State.current != 'none':
            sleep(0.5)
        del self.Transfers.Data[COMMANDID]

    def transfer_abort_failed(self, COMMANDID):
        self.Transfers.Data[COMMANDID].State.abort_failed()

    def check_transfer_cmd_duplicate(self, CommandID):
        if CommandID not in ['', '0'] and CommandID in self.Transfers.Data:
            return True
        return False

    def enable_event(self, CEID_list):
        for CEID in CEID_list:
            if CEID in self.registered_collection_events:
                self.registered_collection_events[CEID].enabled=True

    def disable_event(self, CEID_list):
        for CEID in CEID_list:
            if CEID in self.registered_collection_events:
                self.registered_collection_events[CEID].enabled=False

