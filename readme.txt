8.37.3(2025/05/07) 
add:
mod:
1.modify racknamin [1,21,22] TrloadRq & Trunloadrq recive Result = ["FAIL"]
2.modify requirements.txt mark setproctitle
fix:

8.37.2(2025/05/05) by richard
add:
1.add TrloadRq & Trunloadrq recive Result = ["FAIL"] to trigger Alarm EqUnLoadCheckFailWarning and EqLoadCheckFailWarning
2.add alarm 10019 subcode:307 To distinguish whether the rfid is none or empty
mod:
fix:
1.fix bug:OvenAdapter and OvenHandlerAdapter can run in py2 and py3

8.37.1(2025/05/02)
add:
1.add the ability to configure the sequence in which the MR places carriers onto the buffer for each port
mod:
1.update amr alarm code
fix:
1.fix skip trreq bug (for Renesas)

8.36.19(2025/04/24) 
add:
mod:
1. now will re-assign location when loc is BUF00
2. do faulty recovery will now check the dest of local command instead of check pretransfer flag
fix:
1. fix bug that when back is * cannot do shift+replace
8.36.18(2025/04/23) 
add:
1.add more cpu logger
2.add functionality to detect polygons.
mod:
1.modify vehicle adapter wait MR respond timeout to 20s
fix:
1.fix wrong erack adapter racknaming
2.fix vehicle adapter send_cmd_wait_ack no wait bug 
3.fix vehicle sync bug

8.36.17(2025/04/22) by kelvinng
add:
1. add new alarm 
mod:
fix:

8.36.16(2025/04/21)
add:
1. preDispatch_tr_cmd_to_vehicle can now support replace cmd
mod:
fix:
1. fix is_junction_avoid not work issue
2. fix cancel/abort predispatch cmd cannot go to charge bug
3. fix predispatch will assign more than available buffer bug
4. fix cmd in vehicle queue with different zone cannot be assign bug
5. fix bug that when change replace command's priority will break the order
6. add initial value for tcp_bridge_simulator's state so that when reconnected tsc will not raise status error

8.36.15(2025/04/17)
add:
mod:
fix:
1.fix the error of TrBackReq using "at_station" as the TransferPort

8.36.14(2025/04/16)
add:
1. add field_id for UTAC, USG1ASSY, USG1SORT
2. add ELV_simulator, ELV_adapter for multi floor transfer
mod:
1. change dummyportUTAC dispatch logic
2. mod orderMgr send_transfer, cancel_transfer format
3. mod erackMgr work_add logic
fix:
1. fix orderMgr add_work_list/update_work_status to ensure compatibility for all customers

8.36.13(2025/04/16)
add:
mod:
1.modify P19 cmd
fix:

8.36.12(2025/04/15)
add:
mod:
1.modify Renease vehicle stop cmd and replace new job no need use auto recover function
fix:
1.fix same point robot control bug

8.36.11(2025/04/14)
add:
1.add check buffer01 status before execute cmd only for FCBGA
mod:
1.modify vehicle robot control log
2.modify priority 101 to all custom can use
3.modify Renesas BJ lot dispatch logic
fix:

8.36.10(2025/04/11)
add:
1. add log of key and value when secsgem report_envent has exception
mod:
fix:
1. fix bug that the safety check for clean location group might not work
2. fix clean_right timing when stop routing
3. fix that when erack offline and online will send different ALID
4. fix bug that when MR alarm does not clean the wait_error_code counter

8.36.9(2025/04/11) UI version(250411)
add:
1. add by_mix_lowest_cost_priority algo
mod:
fix:
1. fix by_priority algo issue

8.36.8 (2025/04/08)
add:
mod:
fix:
1.fix vehicle actions misspelling
2.fix renesas skip trreq bug  

8.36.7 (2025/04/08)
add:
mod:
1. mod P512 to fit real MR's action
2. change assign NextBuffer time and call action_loc_assign time
3. enable MR communication log
fix:
1. fix bug in MR sync step and add to log
2. remove protection code in schedule_by_priority

8.36.6 (2025/04/02)
add:
mod:
1. change tsc communication spec with MR to 5.5
fix:
1. fix bug that direct command use wrong system id in vehicleAdapter

8.36.5(2025/04/01)
add:
mod:
1.Update the api params used to request the automatic door opening and closing of the SJ EQ.
fix:

8.36.4(2025/04/01)
add:
mod:
fix:
1.fix skip ask trload/unload req bug

8.36.3(2025/04/01) by sunny
add:
1.add skip ask trload/unload req when doing retry action for Renesas JP
mod:
fix:

8.36.2(2025/04/01)
add:
mod:
1.modify cancel/abort command id is string type
fix:
1.fix FCBGA use buf01 but not cover tray bug

8.36.1 (2025/03/31)
add:
1.Add name the threads launched via the IoT Vehicle ERack workstation Mgr.
2.Add 'LOT' and 'LOTNUM' to the E82 transferInfoList.
3.Add the Vehicle Max Capacity parameter in the zone to limit the number of MRs that can execute commands in that zone at once. 
4.Add a record of thread information when the TSC CPU usage exceeds 90%.
5.Add merge_max_lots to the zone settings to limit the maximum number of lots that can be executed.(only for Renesas BJ)
6.Add TSCSettings SortingCondition and SortingMethod to determine the command sorting based on lotID or equipment
7.Add crossZoneLink to allow manual input of source, destination, and transport type to indicate which zone the command belongs to
    example:
        "zone1":
                "crossZoneLink": [
                {
                    "From": "zone3",
                    "To": "zone1",
                    "handlingType": "Undefined"
                },
                {
                    "From": "zone5",
                    "To": "zone2",
                    "handlingType": "Undefined"
                }
            ],

mod:
1.Modify so that when the workstation type belongs to erack port, the DivideMethodByMachinePior can be applied when determining which zone a command belongs to.
2.Modify commandID from secs is string type
fix:
1.Fix the bug where the simulator does not support more than 10 slots for MR
2.Fix the issue where the correct carrierID, lotID, and lotNum are not retrieved from the UI upon TSC restart.
3.Fix the bug when SJ changes the transfer priority.
4.Fix the bug when sorting by the same equipmentID.

8.35.5(2025/03/28) by Sunny
add:
mod:
fix:
1. fix replace and mr buffer and shift transfer combination issue
2. fix tcp_bridge_simulator bug with shift command

8.35.4(2025/03/28)
add:
1. add naming thread patch for thead naming
2. add route no response msg for manual route
3. add P00 heartbeats
4. add route fail log
5. add recv string combination for vehicle
6. add log for vehicle stop thread
7. add step in sync data to make sure the date is correct
8. add raw_data log for vehicle and erack(not active yet)
mod:
1. change default get a route timeout from 600s to 30s
2. do not clean memory_group before calling clean_right function
3. add soft_ver for all TSCUpdate event
4. change all_status_query and version_query to blocking mode
fix:
1. fix bug that avoid action does not correctly occupied the right
2. fix move command nak can not end enroute state issue
3. fix bug that does not check current location when clean memory_group in update_location
4. fix missing ',' in global_variables
5. fix missing systemid for tcp_bridge_simulator
6. fix link_tr_cmd might not have original_priority issue

8.35.3(2025/03/20)
add:
1. report state to UI when AgvState Pause and  man_mode
mod:
1. update door_action flow for SJ
2. update alarm msg 'Safty' to 'Safety'
fix:
1. fix recovery_transfer miss carrierType

8.35.2(2025/03/10) by yuri
add:
1. add Hitch to support BufConstrain
mod:
1. smooth docking point to get S82 message
fix:
1. fix eracknameing is 25 27 instruction carrierType for the shelf does not support times error

8.35.1(2025/03/06)
add:
1. add swap action (only for better_cost and lowest_cost)
2. add type_J vehicle support swap action
3. add new secs event for swap action
4. add new append_transfer_allowed for renesas
5. add log for CPU and memory usage
mod:
fix:
1.fix carrier already in MR buf and get new transfer cmd will update carrier local_tr_cmd bug

8.34.10(2025/03/03)
add:
1. add operator id parameter for transfer cmd
mod:
fix:
1. fix bug that in stage and preDispatch mode, cmd cannot be dispatch when there is only eq cmd

8.34.9(2025/03/03)
add:
mod:
1. load sub alarm code from files
fix:
1. fix shifting state missing interlock error process bug
2. fix "/" doesnot return int in python3 bug

8.34.8(2025/03/03)
add:
mod:
fix:
1.fix can't use secs cmd abort Replace cmd

8.34.7(2025/02/07) by Richard
add:
1.add OvenHandlerAdapter for ASECL Oven 
2.add OvenAdapter for ASECL Oven 
3.add OvenHandlerAdapter PLC　transfer　function in vehicle.py
4.add OvenAdapter in iot_module
5.add OvenHandlerAdapter in  iot_module
6.add marco_list in vehicleRouterPlanner
7.add DeviceParameter in controller 
mod:
fix:

8.34.6(2025/02/27) by cyun
add:
mod:
fix:
1.fix erack down but erack port status is up bug

8.34.5(2025/02/27)
add:
1. add .gitignore to ignore files that do not need to be pushed 
mod:
1. adjust the format of the failure ID
fix:
1. fix creating duplicate threads for the same ID
2. fix the latest dest port is not be reset book after the dest is changed
3. fix transfer will be appended to the execution queue when there is a task with priority 101 in the execution queue(for SJ)

8.34.4(2025/02/20)
add:
1. let non-storage port wait for storage zone 
mod:
1. let initial value on buffer of tcp_bridge simulator be blank
fix:
1. fix bug for PreProcess cmd check of last segment
2. fix bug for getting post process
3. fix bug of secsgem library happend in python3 when disconnect

8.34.3(2025/02/14)
add:
mod:
fix:
1.fix dynamicBufferMapping bug

8.34.2(2025/02/10)
add:
1.add rackNaming 58 for Renesas 
mod:
fix:
1.fix force close thread function bug

8.34.1(2025/02/04)  UI version(250210)
add:
1.add workstations limitBuf param for bufconstrain
2.add vehicle bufferDirection param for bufconstrain
mod:
1.modify bufconstrain function can choose [front, rear, top, bottom, left, right]
2.modify choose buf sequence for Renesas
fix:
1.fix GATE adapter bug
2.fix buf_allocate_test carriertype bug

8.33.1(2025/01/17)
add:
1. add next buffer info for robot command
mod:
1. in from to only mode, add last junction point to the route
fix:
1. fix bug in executeTime and HostSpecifyMR with replace cmd
1. do not turn off charge flag after disconnecting

8.32.3(2025/01/17)
fix:
1.fix bug in vehicle_stop cmd have race condition issue

8.32.2(2025/01/14) by Au
fix:
1.fix sender.py controller id and receive none bug

8.32.1(2025/01/14) by Kenny
add:
1. add PreProcess and PostProcess function for iot Gate
2. add force close thread function
3. add SSL vehicle connect method for rackNaming == 55

8.31.32(2025/01/10)
add:
mod:
1.modify TI Miho racknamin rules
fix:
1.fix transfer cmd source is MR buf but choice wrong buf bug

8.31.31(2025/01/09)
add:
1.add racknaming 57 for Malta
mod:
fix:
1.fix transfer_format_check missing parameter bug
2.fix add_transfer_cmd can't specify buf bug

8.31.30(2025/01/06)
add:
mod:
1. call vehicle stop when receive nak
2. move cmd will be sent after the ack of last cmd received
3. let A* algo in c++ code be executed by thread so that it can end when algo no response
fix:
1. fix preprocess and postproces of edge cannot set continuously problem
2. fix when go is at last point cannot trigger waiting action end problem
3. fix tcp simulator cannot clean stop flag when no route is executed

8.31.29(2025/01/02)
add:
1.add racknaming 55 56 for intel
mod:
1.modify TrloadReq & TrUnLoadReq event interval time to 30s (only for Renesas FCBGA)
2.filter readfail alarm for Renesas FCBGA
fix:

8.31.28(2025/01/02) by Yuri
fix:
1. appendTransferMoving performs multiple computations at the same point
2. If actions is empty, the output is abnormal
3.If the current_route and current_go_list are empty, the thread stops because global_occupied_lock does not release
4. appendTransferMoving S52 returns less than 50s
add:
1. Add carrierTypeCheck to appendTransferMoving and appendTransferMovePath

8.31.27(2025/01/02)
add:
mod:
1. change EqDoorReqFailWarning alarm subcode TSC031.
fix:

8.31.26(2025/01/02)
add:
mod:
1. add TrLoadReq before door_action(request the api for opening and closing the port door).
fix:

8.31.25(2024/12/19)
add:
1. let buffer num of the vehicle simulator be a paramter
mod:
fix:
1. fix bug that when AMR missing rfid for two buffers, the carrier will be rename to same ID

8.31.24(2024/12/18) by peter
add:
1.add can receive link cmd in append_transfer_allowed(K11)
mod:
2.remove showmcs(K11)
fix:

8.31.23(2024/12/18)
add:
mod:
fix:
1.fix appendTransferMovePath no action bug
2.fix return_standby_cmd can't generated the route but still create cmd bug

8.31.22(2024/12/16)
add:
1.add message to UI when vehicle have obstacle
2.add filter carrierID "%L" from MR P25(only for Renesas JP)
mod:
fix:

8.31.21(2024/12/12) by Yuri
add:
mod:
1.tools added support for the timeout method from threading.Lock in python2
fix:
1.Repair vehicle_stop to obtain the route_right_lock and cause a jam

8.31.20(2024/12/12) by zhenghao zhou
add:
1. add new fucntion for request a a thrid party opendoor in SJ
mod:
fix:

8.31.19(2024/12/10)
add:
1.add send event when host update priority
mod:
1.modify the syntax to be compatible with both Python 2 and Python 3.
2.modify "==" to " == " and " = " to "="
fix:
1.fix return to standby bug

8.31.18(2024/12/04)
add:
mod:
fix:
1. fix preprocess and postprocess of edge not work for two point route
2. fix postprocess of point not work bug
3. fix cannot go charge after abort predispatch bug

8.31.17(2024/12/04)
add:
1. add P97 function
mod:
1. rewrite buffer initial to parameter format
fix:
1. fix bug when preDispatch abort, eq zone can not be dispatch issue

8.31.16(2024/12/04)
add:
1.add new protocol v3_tipi_tiem
2.add new type vehicle (Type_G:16 buf Type_H:10 buf Type_I:1 buf)
3.add update_dynamic_buffer_mapping for Renesas FCBGA
4.add vehicleadapter query battery ID 
mod:
fix:
1.fix doPreDispatchCmd bug(still have some issues need check)

8.31.15(2024/12/02)
add:
1.add E88&E82 device id to controller parser
mod:
fix:

8.31.14(2024/11/29)
add:
1. add PreProcess and PostProcess for edge
2. add Floor in point properties for elevator
3. add ProcessParam
mod:
1. mod elevator to edge process form
2. mod go point judgement for fromToOnly
3. rewrite stage check for replace transfer
4. when stage enable, it will enable most of preDispatch function
5. do not clean doPreDispatch flag when abort action
fix:
1. fix problem that do not book additional point for fromToOnly
2. fix bug that when in junction avoid do not check process
3. fix compile file not delete git file
4. fix problem that stage cannot read addition info for transferinfo
5. fix bug that not check if cmd is replace when search pairng cmd for cmd in waiting queue
6. fix bug in delay vehicle flag count in tsc
7. fix typo in map msg_decode

8.31.13(2024/11/28) by Yuri
add
1.appendTransferMovePathAllowed and appendTransferMovingAllowed
2.FOUP stays timeout on the AMR BUFFER
3.QTime parameter is added in instruction initialization
4.Add buffer to eq replace transfer
5.instruction initialization to increase the point and instruction relationship table
6.Add pre_transfer type command judgment

8.31.12(2024/11/21)
add:
mod:
fix:
1.fix tools.py book_dest_port_in_racks CDAErack model bug

8.31.11(2024/11/13)
add:
1.add new vid_v2_asecl_oven
mod:
1.modify alarm text from "Base E84 interlock error" to "interlock error"
fix:

8.31.10(2024/11/11)
add: (by sean)
1. New Erack Adapter CDAErackAdapter_e88.py
2. CDAErack check/open/close door cmds
3. CDAErack rackport select for API 
mod:
fix:

8.31.9(2024/11/08)
add:
mod:
fix:
1.fix preDispatch cmd priority type bug

8.31.8(2024/11/07)
add:
1.add Transfer class mod function in e88_eqipment
mod:
fix:
1.fix stage cmd bug

8.31.7(2024/11/06)
add:
mod:
fix:
1. fix call command will stuck in waiting bug

8.31.6(2024/11/06)
fix:
1.fix new version output block bug(by Alan)
mod:
1.modify lowest cost schedule can support swap cmd but dest is MR buf(by kelvinng)

8.31.5(2024/11/05)
add:
1. add stage delete command
mod:
1. change stage id keyword in stage delete command
fix:
1. fix from to only do not book junction point(by peter, Mike rewrite)
2. set stage enable default to NO
3. fix a possible bug in preDispatch that might cause the loop not end

8.31.4(2024/11/04)
add:
1. add ip argument for e82 and e88 to bind on specific ip
2. add stage command
3. add change transfer priority in waiting queue
4. add 5.0 robot command
mod:
1. combine socket msg for erack adapter
2. modify call command, now will ack like stage cmd(use action structure)
3. add some log for MR reply msg
fix:
1. fix bug in call command
2. fix cancel by link doesn't show by link
3. fix current cmd control get wrong dest port
4. do not executing withdraw job when vehicle not stop
5. request route_right_lock when executing vehicle stop
6. fix exchange status assign bug

8.31.3(2024/10/30)
fix
1.fix bug when use appendTransferAllowed but not valid buffer

8.31.2(2024/10/28)by Alan
mod:
1.modify new output function

8.31.1(2024/10/28)by chocp
mod:
1.modify new socketio to UI output

8.30.6(2024/10/28)
add:
1.add new E82 cmd PRIORITYUPDATE for host want update waitingqueue command priority
mod:
1.modify S2F31 use new thread to do(in real server will take too long to change time)
2.modify E82 abort/cancel cmd return HCACK from 0 to 4(only for mirle)
3.modify return abort fail when host send ABORT cmd but MR robot is moving state((only for mirle)
fix:
1.fix bug alarms.py missing alarm subcode

8.30.5(2024/10/22)
fix:
1.fix bug When a task does not require support, but a command is still assigned to a support MR.

8.30.4(2024/10/21)
add:
1.add new add_transfer_into_queue function for SJ (only dispatch priority 101 cmd if queue have)
mod:
1.modify E82 transfer cmd can assert priority 101
fix:
1.fix bug with execute acquire action and carrier is empty bug

8.30.3(2024/10/16)
add:
1.add new alarm when vehicle dispatch but carrier source port mismatch actual location(SourceLocationMismatchCheck)
fix:
1.fix bug When the source port is the same, place multiple command to MR buff
2.fix bug BaseDestInterlockWarning alarm misspelled

8.30.2(2024/10/14) by Hshuo
add:
1.add vid_v2_asecl_cp
mod:
1.dummyport_for_asecl if erack no checked that ordermanagement status still waiting

8.30.1(2024/10/14)
add:
mod:
1.modify output event 'VehicleAssigned' to sync_output
2.modify append_transfer_allowed can assert vehicle different carrier type(Carrier Type Check)
3.modify vehicle subcode to new version
4.modify when tsc code exception don't put detail to subcode field
5.modify when DestPortDuplicatedCheck ==yes but destPort is stock type will skip check
fix:
1.fix bug when point set RobotRouteLock but map didn't have this point
2.fix bug when preDispatch UI show command zone is stock but actually is MR zone

8.29.29(2024/10/9)
add:
1. add VehicleOnline and VehicleOffline event for JCAP
mod:
fix:
1. fix bug that did not send carrier id in P37 when command finished
2. fix bug that .adapter appear in VehicleAdapter.py

8.29.28(2024/10/4)
mod:
1.modify schedule_by_better_cost by kelvinng
2.mark GuiErackSimulator Unused package
3.modify racknaming rule for [47 50 51]
fix:
1.fix bug with disabled zone and host send S2F49 transfer cmd can't respond S2F50

8.29.27(2024/10/4)
add:
1. add VehicleLocationReport event for JCAP
2. add reject stage cmd if no stage id
3. link connection logger to main logger for secsgem equipment
4. add P63 and other msg return for tcp_bridge_simulator
5. add more detail for recv_ack:timeout log
mod:
fix:

8.29.26(2024/09/26)
modify:
1.modify transfer priority only for racknaming 21
fix:
1.fix bug with transfer queue insert wrong place 

8.29.25(2024/09/23) by peter
add:
1.add pass door secsgem event for K11
2.add TrLoadReq/TrUnLoadReq with carrierType for K11
3.add TrLoadReq NG with NGPORT for K11
4.add show MCS message in UI alarm page for K11

8.29.24(2024/09/20) by yuri
add
1. vehicle status e82 message add BatteryValue
2, add erack allocate storage from the bottom layer (only applicable to RackNaming 25)
3. Empty buff before adding vehicle to ChargeBelowPower (only applicable to RackNaming 25)
4, Add-api add v3_TICD (only applicable to TICD)
modify
1. Change whether the filter DestPort or source contains the MR Field

8.29.23(2024/09/20) UI version(240923)
add:
1.add "WAIT" to E82 ASSERT CMD for Renesas
2.add new E82 CMD
    2-1 SUSPENDCANCEL for Renesas
    2-2 VEHICLERETRYACTION for Host want retry MR action when MR alarm
3.add retry cmd to tcp_bridge_simulate
4.add new vehicle state(Suspend) for Renesas
5.add new PS protocal P19 for MR retry action
mod:
1.modify vehicle parameter name "TimeChargeingWhen" to "EnableScheduleCharging" and "TimeChargeing" to "ScheduleChargingTime"
2.modify when MR execute acquire action but carrier already on MR buf will pop action and continue other action
3.modify when choice DefaultErack for do_fault_recovery use sector be the dest (only for qualcomm)
4.modify racknamin 48 53 rules

8.29.22(2024/09/20)
add:
1. add python3 compile, now can compile python3 pyc when using python3 to run compile
2. add PreProcessParam and PostProcessParam in pose for future use
mod:
fix:
1. fix bug that will cause multiple command add to waiting queue when sorting priority

8.29.21(2024/09/13)
add:
1. add e82 event VehicleTrafficBlocking, VehicleTrafficRelease, VehicleObstacleBlocking, VehicleObstacleRelease, VehicleStateChange
2. add enable and disable event function for secsgem
3. add P39 for tcp_bridge_simulator
4. add P39 function to report current command
5. add some log for direct command of vehicle
mod:
1. change manual and disconnect state to substate of pause
2. clean route when move cmd nak, vehicle will resend route if MR is not at right place
fix:
1. add join in main loop of route planner to make sure that get_right thread is end before clean route

8.29.20(2024/09/06)
add:
1.add choose buf rules for racknaming 42 Renesas FCBGA
    -buf01 only for CoverTray
2.add commandinfo and transfercompleted to E82 cancel and abort event (only for Mirle MCS)
mod:
1.modify VehicleAssigned trigger time (Mirle MCS can't accept commmandIDlist need send VehicleAssigned every cmd)
2.modify when link cmd priority change will send originalpriority to UI 
fix:
1.fix bug when e88 set alarm missing parameters

8.29.19(2024/09/03)
add:
1.add new vehicle type 'Type_F for 3 buffer
2.add allow_shift to all dummpyport for shift cmd
mod:
1.modify duplicated alarm add duplicated cmdID
2.modify Baguio BUMP racknaming rule
3.modify can assert replace cmd when source is MRBuff
fix:
1.fix shift command bug when MR not support this command

8.29.18(2024/08/30)
add:
1. vehicle will go to park if next action is not here and there is a vehicle waiting with higher priority
mod:
1. add junction into route in fromToOnly mode so that mr need to get junction's right to passby
2. send DeviceOnline and DeviceOffline when erack enable/disable
3. filt erack to erack in book later mode
4. call command will now choose a nearest vehicle if destport doesn't have service zone
fix:
1. add check to prevent from exception in vehicleRoutePlanner
2. filt in route plan if the macro name of preprocess or postprocess is not in macro_list
3. return destport error if destport not in map for call command

8.29.17(2024/08/30)
add:
1.add rack name start with B for SJ J2B (by peng)
2.add equipmentID when sourceport is MR buffer for ASECL Oven(by Hshuo)

8.29.16(2024/08/29)
add:
1.add new SV for Mirle MCS
2.add event_id to E82 Alarm report can Define ReportID
3.add alarmlevel to E82 set_alarm and clear_alarm for Mirle trigger alarm or unitalarm

mod:
1.rename E82 cmd AGVVALIDPERMISSION to VALIDPERMISSION
2.modify whne recevie Host ASSERT cmd have HEIGHT then send to MR
3.modify P45 kwargs will be json format
4.modify  deposite_control and acquire_control need choose DisablePort2AddrTable then use new protocol

8.29.15(2024/08/26)by Hshuo
add:
1.ASECL PortStatusUpdate add RackGroup
2.add RackNaming 52&53

8.29.14(2024/08/26)
fix:
1.fix add_transfer_cmd shift bug
2.fix query SV bug for Mirle MCS

8.29.13(2024/08/23)
add:
1. add action not support error for shift cmd
mod:
fix:
1. fix bug in route_count
2. fix bug if source or dest is MR port in add_transfer_cmd
3. fix bug in enter_shifting_state action

8.29.12(2024/08/22)
add:
1.add E82 CurrentPortStates SV can query PortState 1:OutOfService 2:InService
2.add E82 AGVVALIDPERMISSION cmd and is equal with ASSERT cmd but not [REQUEST&DESTPORT] parameter(only for Mirle)
3.add new alarm to different source and dest interlock error (for Mirle MCS)
4.add new alarm to different source and dest from receive Host "NG" 
mod:
1.modify v3_mirle SVID
2.modify E82 ASSERT cmd add "HEIGHT" parameter(only for Renesas)
3.modify E82 PortInService&PortOutOfService events be effective
4.modify E82 transfercompleted result_code for Mirle(racknamin=43)
fix:
1.fix battery exchange bug

8.29.11(2024/8/21)
1.add zero mq server support -add_db_logger='Y' option for external db requirement
2.support shift transfer cmd from UI
a.add 'SHIFT' action type
b.add 'SHIFT' action type schedule in schedule_by_lowest_cost.py and schedule_by_better_cost.py
c.add vehicle 'Shifting' state
d.add 'shiftTransfer' flag in host_tr_cmd
e.add 'transferType' flag in local_tr_cmd
d.add 'shiftTransfer' type and dispatch_shift_tr_cmd_to_vehicle()
e.fix vehicle simulator
f.fix UI

8.29.10(2024/08/21)
add:
1. add vehicle priority check for junction avoid and get route timeout
2. add rename command for e82 and e88_stk (vehicle only now)
3. erack simulator now can set row and column size
4. tcp_bridge simulator now can suppert shift command
5. unload and load cmd with differnt priority can be linked now
mod:
1. modify status of MR alarm and warning to take off the unicode
2. modify some warning code of MR
3. rewrite manual api in controller
4. rename carrier for MR will send carrierRevoved then carrierInstalled now
fix:
1. fix manual robot command bug
2. fix typo of acquire_control

8.29.9(2024/08/09)
1.add auto cancel cmd when carrier removed from erack (only for ASECL and SRTD)
2.add alarm code 40022 40023 for reject transfer cmd by disable loadport and zone
3.add disable workstaion and zone function
by Hshuo
4.mark controller.py exception code 
5.re-add sleep to global_variables sync_output

8.29.8(2024/08/09)
1. add license
2. fix bug in wait port state
3. add clean folder param in compile
4. modify pyzmq to >=15.4.0 for python3.8+

8.29.7(2024/08/07)
1.add SV&CE for mirle MCS
2.modify MR and erack simulate
--GUI erack can entry row and column
--MR can support python3
3.modify alarm code [50052 50053 50062 50063] level from Warning to Error
4.add racknaming 46-51

8.29.6(2024/08/05)
1. add preprocess & postprocess
2. add move out completed and close door in postprocess for elevator
3. fix bug that tsc will hang when no node in map
4. add heart beat for all units and threads
5. add location to elevator command
6. add protect code in set function of e88_equipment models
7. add LifterPort for tsc
8. modify stop flag for vehicles
9. modify P45 corresponding for shift control
10. fix python3 compatibility
11. fix keep_angle problem
12. add setup for replace secsgem module
    sh setup.sh -> default 2.7
    sh setup.sh 3.8 -> specific version
13. add log for setting from UI

8.29.5(2024/07/30)
1.fix pretransfer bug
2.fix alarm.py detail missing bug

8.29.4(2024/07/26)
1.fix keep_angle when no recevie UI data or get error type then use default 20.0
2.add when receive cancel and abort cmd from UI send E82 OperatorInitiatedAction event
3.modify 'transfer type' OperatorInitiatedAction trigger time

8.29.3(2024/07/25)
1.add e82 SV "IDReadStatus" "BatteryValue" "VehicleLastPosition" "ALID"
2.add e82 CE "CarrierIDRead" "AlarmCleared" "AlarmSet" "UnitAlarmSet" "UnitAlarmCleared"
3.add e82 VehicleRemoved event when stop vehicle thread
4.add e82 OperatorInitiatedAction event when received transfer cmd from UI
5.add CarrierIDRead event when acquiring complete (only for mirle)
--for mirle new version E82 spec
6.update alarms sub_code
7.add racknaming 43-45

8.29.2(2024/07/25)(by yuri)
1.Add car charging for a specified period of time under Unassigned status
2.update Naming rules for Chengdu TI erack(BUMP)

8.29.1(2024/07/10)
1.modify e82 S2F31 function
2.modify when TSCpaused all movement activities will be halted except for emergency evacuation and traffic management for urgent situations
3.add evacuate_station to UI if no setting us standby_station
4.fix disable edge bug
5.add racknaming 39-42
6.add vehicleAlgo to zone setting
--by_lowest_distance: Select the AMR that is closest to the command(Default)
--by_battery: Select the MR with the most battery power.

8.28.58(2024/07/05)
1. fix get_right_th bug
2. add waitout to waitin path in e88
3. add originaltransfer for correcting the report of transfercompleted/transferabortcompleted/transfercancelcompleted location info
4. fix command link problem for predispatch command
5. fix load cmd and unload cmd not in same batch if cmd is too much
6. fix mr queue delay bug for normal zone
7. fix the problem that will clean route right which is not occupied by itself (HH problem)
8. fix clean_right and new_route race condition in reroute function(HH problem)
9. add P37 function
10. switch to manual when disconnected(KYEC problem)

8.28.57(2024/06/26)
1.add change_state to erack_mgr.py for racknaming =7 and don't infoupdate
2.modify GpmErackAdapter_e88
3.add protocol_list 'v3_MIRLE' and 'v3_CHIPMOS'
4.add E82 SV_EnhancedCarriers(add InstallTime and CarrierState) to all v3 protocal
5.modify E82 Evacuation cmd distinguish between different situations(FireDisaster or EarthQuake)
FireDisaster
-- wait arm finished then go to safety point
EarthQuake
-- immediately stop arm and raise alarm
6.add racknaming 36:K9 37:K11 38:K8
7.add use vehicle battery["percentage"] to decide which MR tp dispatch(only for racknaming=7)

8.28.56(2024/06/20)
1. junction avoid will now send the rest route after MR is arrived to prevent from backward route
2. add filter for backward route
3. add send cmd info to vehicle function
4. fix bug that abort cmd when robot is acquiring carrier but not put on to vehicle yet will let the carriertype missing
5. filt workstation type for recovery cmd

8.28.55(2024/06/13)
1.add racknaming 35 for UTAC USG3

8.28.54(2024/06/12)
1. add keep_angle function
2. add try except to prevent from not release lock
3. let all the area can establish the stockport model for lifter.

8.28.53(2024/06/06)
1.add max_size(100k) of socket queue
--If the upper limit is exceeded, the first one will be discarded.

8.28.52(2024/06/05)
1.modify controller check socket connect time loop (from 5 to 2 sec)
2.modify make sure socketio connect then send events
3.fix bug when the replace cmd but carrier already on vehicle

8.28.51(2024/06/04)
1. fix bug that to erack command cannot generate in booklater mode.
2. add vehicle info and eq info for booklater when booking erack.
3. fix bug when vehicle queue is done and eq zone is done, predispatch zone might not be execute.

8.28.50(2024/05/31)
1.add racknaming 34 for SJ 3F

8.28.49(2024/05/30)
1.add new alarm code 10033 for Host S2F41 Evacuation cmd
2.add nwe S2F41 secs  EVACUATION cmd
3.modify S2F41 secs STOPVEHICLE  cmd can support stop all MR
4.change trigger ABCS put_batt() time
5.add when AMR depositcomplete will take CoverTray back to buf(Do not into faulty recover) only for Renesas JP FT
6.add new rack nameing 33 for Renesas JP FT

8.28.48(2024/05/23)
1. prevent predispatch transfer cmd from book later function.
2. fix merge bug corresponding to unload_buf_assigned.
3. fix bug in zone dispatch check corresponding to predispatch.
4. fix bug in eq_mgr.

8.28.47(2024/05/17)
1. add book later function for spil, it will keep zone name or P0 of erack until dispatch
2. zone queue can assign only when preDispatch queue is expired.
3. add logger for dummyport jcet

8.28.46(2024/05/10)
1.fix bug for pre dispatch cmd get wrong zone
2.fix bug in chck source for pre dispatch cmd in waiting state

8.28.45(2024/05/10)
1.modify vehicle waiting state
2.modify stock out cmd zone(only for FST) 

8.28.44(2024/05/08)
1.fix schedule_by_lowest_cost bug

8.28.43(2024/05/07)
1. fix get wrong state in wait port state
2. add connection state to erack info
3. add skyworksSG protocol
4. add dispatch delay for mr zone
5. modify reroute algorithm, now will try all the route and wait at the latest choice

8.28.42(2024/05/07)
1.modify schedule_by_lowest_cost 

8.28.41(2024/05/03)
1.add new param('color') to E88 infoupdate for SJ show erack background_color (Options)
2.add vehicle carrier type check for AMR buf have different type
--if have plural type use "|" 
--if buf is Universal use 'All"
ex:
buf01 12S
buf02 8S
buf03 12S|8S
buf04 All

3.modify reroute function
4.add new vehicle state(Waiting)
5.modify E82 call cmd 
--add waiting param
--if have waiting AMR will waiting on the target(port)
--and change state to waiting
--if in waiting state only can do target cmd

8.28.40(2024/04/18)
1.add erack_date_ti.py to send msg to erack
2.add new E88 secs cmd (infoupdatebyrack) for SJ update carrierinfo by erack

8.28.39(2024/04/12)
1.add ImmediatelyAssignedReq(UI) to control VehicleAssignReq
2.add auto_group function(Options)
-use args to start controller.py (-auto_group vehicle_length,vehicle_width)
-vehicle_length and vehicle_width must be int and unit is mm

8.28.38(2024/04/12)
1. do unloading last while keeping the lowest cost
2. add log when block group or block node change
3. add VehicleAssignReq event for MCS to acknowledge the order of return cassette
4. add ASSIGNABLE rcmd to let MCS to inform AMR to go immediately
5. fix L and C reversed problem for skyworks SG/JP
6. add DestType=WorkStion for do unloading last
7. send VehicleAssignReq after preDispatch is done
8. add filter for replace command to send only one transferring
9. fix bug in dummyport_jcet

8.28.37(2023/4/8)
1.add 'VEHICLEID' to SECS S2F49 transfer cmd(Optional) for host Specify MR
2.add new alarm code 40021 for host Specify MR error
3.fix controller manual control bug(Pause --> Manual)

8.28.36
1.redirect TrLoadReq/TrUnLoadReq for Stocker workstation

8.28.35(2023/03/27)
1.fix bufs_status_check item when acquire completed, exclude unknown
2.fix bufs_status_check item when buf select in deposit, exclude unknown
3.downgrade manual mode code
carrierID unknown need rewrite

8.28.34(2023/03/26)
2.enhance UMC SRTD

8.28.33(2023/03/25)
1.update dummyport_for_umc.py and dummyport_for_umc_stocker.py

8.28.32(2024/03/25)
1. auto send manual when alarm set in tcp_bridge_simulator
2. fix tr_wq_lib format check for blank or * in destport
3. add replace total count in wq for dispatch
4. fix replace command counting bug
5. add StockIn&StockOut type for preDispatch
6. add call cmd for asking nearest MR
7. fix can_run_flag condition
8. fix bug in transporter update carrier state
9. always report None when not get CarrierID except buffer is readyToUnload
10. add buffer update when MR is alarm
11. add manual state and disconnected state (with UI version: 6.5.240325+)
12. fix carrier type check bug in do_fault_recovery

8.28.31(2024/03/08)
1. add LoadBackOrder event in E82 for MCS to check the order when AMR load back cassette to box on stk
2. fix MR naming check in buf_allocate_test
3. add StockIn&StockOut type for both in and out stk port

8.29.30(2024/03/08)
1.modify break vehicle state(TrUnLoadReq/TrLoadReq) when command abort
2.modify make sure MapUpdateCompleted then run vehicle thread
3.add 'ControllerID' to all socket event

8.28.29(2024/03/05)
1.modify acquiring buffer_list to [1,3,0,2] for BOE
2.add try except to vehicle task_generate
3.add new charge rule (only for BOE and 2 vehicle situation)
4.add new racknaming for ASECL FRG

8.28.28(2024/03/05)
1. modify flow of elevator control
2. fix junction avoid and find new route problem
3. add debug info to elevator control
4. modify socket initial for multiple controller
5. add missing info for erack alarm
6. fix report wrong sf for enhanced remote command in e88_eqipment
7. fix bug for racknaming decoding
8. change MR name check from just 'MR' to real MRID for destport check in format check
9. add transfer info to active transfer for user cmd and recovery cmd
10. fix some parameter update bug in transporter and vehicle
11. modify change cmd sending time from the first GO point after meet change point to the very last GO point
12. add stockport type for lift AMR

8.28.27(2024/2/19)
1.modify (source and dest port)DuplicatedCheck for all type(erack and EQ) except 'Stock' type

8.28.26(2024/2/7)
1.add new subcode(TS1317-TS1321)
2.fix vehicleRoutePlanner (before mapping PoseTable make sure last_point inside)
3.add new alarm for PointNotInMap
4.fix vehicle.message None bug
5.add try except to vehicle_mgr when except only affect one vehicle
6.modify use same flag to stop vehicle and vehicleadapter thread

8.28.25(2024/2/1)
1.add log for (erack vehicle iot eq)mgr and controller when except

8.28.24 (2024/1/24)
1. add mount_socketio_func() to mount namespace with controller_id 
2. also init E88_ErackMgr() with secsgem_e88_h=None for compatible

8.28.23 (2024/1/23)
1.fix a bug change,
namespace='/tsc' => namespace='/{}'.format(global_variables.controller_id)

8.28.22 (2024/01/19)
1. add alarms for elevator
2. fix bug that EqMgr does not call getInstance() in schedule_by_better_cost
3. modify pre-process for elevator(need to test with real elevator)
4. clean route if moveappend command is rejected
5. resend the moveappend command if moveappend command is not sent according to the internet issue
6. update ElvAdapter
7. add carrierID in assert (by chi)
8. add fromToOnly function
9. add filter for Unknown buffer status in do_fault_recovery
10. set move arrival status to Fail when charge/exchagne failed
11. abort command when AMR disable (by chi)
12. fix slot digit bug if buffer num is 2 digits (by chi)
13. fix carrierloc report problem (buf -> AMR+buf)

8.28.22(2024/01/12)
1. add threading lock to prevent the conflict between release right and book new route's right
2. add TSCUpdate when socket connect to let the webpage shows the version of tsc
3. fix erack name parse format for skyworks JP/SG
4. add put battery function in ABCS
5. add send command function in ABCS
6. add fromToOnly function for new AMR
7. add wait stop return in vehicle_stop
8. add log in version check(for debug)

8.28.21
1.fix old pretransfer bug(when cancel MR to EQ will try abort erack to MR)

8.28.20
1.redefine lanuch tsc parameter(if not specified will use default)
ex:
python2 ./controller.py -id tsc1 -url 127.0.0.1 -port 3000 -e82_port 5000 -api v3 -e88_port 5001 -loadport Gyro

8.28.19(2024/1/5)
1.fix AllVehiclePoseUpdate output
2.add logger for EqView, EqMgr, OrderMgr, Workstation
3.add more in config

8.28.18(2024/1/4)(chocp)
1.add AllVehiclePoseUpdate event output
2.change OrderMgr objet from global object to EqMgr
3.for umc test Sean
- (eq_mgr.py) add dummyport_for_umc.py
- (tsc.py) TSCSettings RTDCarrierLocateCheck (default:yes) : Create Order when carrier not on erack
- (GyroErackAdapter_e88.py) Update Order's Location When put carrier on erack (testing)

8.28.18(2024/01/04)
1. fix mr buffer info parse error for 10+ buffer (mr spec 3.0+)

8.28.17(2024/1/2)
1.fix bug: do ErackCassetteType check...
2.fix bug: add import OrderMgr in erack_mgr
3.add select flag in OrderMgr before add in waiting queue
4.fix E88_dataitems for MF Erack

8.28.16(2023/12/28)
1.renew OrderMgr dispatch func
2.rewrite EqMgr
3.rewrite OrderMgr
4.enchance ErackCassetteType check

8.28.15(2023/12/28)
1.add log to vehicleadapter and vehicleRoutePlanner
2.add -filter to control.py for filter erackstatusupdate event
3.modify hsot_call cmd

8.28.14(2023/12/28)
1.carrierType not support 'NA', 'None'
2.fix carrierType check in book algo
3.remove binding code
4.remove rtd for HH code

8.28.13(2023/12/27)
1.add format_parse func for Erack.validSlotType #{'8S':[1,2,3], '12S':[7,8,15]}
2.fix tcp_bridge_simulate.py path to read pose_table.txt file
3.tools.rackport_format_parse for BOE
4.update all h_eRack.status and h_eRack.last_status to h_eRack.erack_status and h_eRack.last_erack_status

8.28.12(2023/12/25)
1.support dumpwaiter control(with mcs, lifterc)
2.support link with ICWiser Erack for BOE
3.change rackport_format_parse func
4.support more size of ICWiser
5.add eap_port_state for UTAC and change 'RejectAndReadyUnload' algo

8.28.11(2023/12/22)
1.add vehicleid to erack set_machine_info()
2.fix ctrl+C can not kill process bug

8.28.10 (2023/12/22)
1. add E88 stk for dumbwaiter(transporter)
2. add elevator relative process (connectionpoint)
3. modify tcp_bridge_simulation for different floor
4. rewrite source port if carrier is on MR
5. add book command for dumbwaiter
6. modify the judgement if zone is MR
7. fix the change route function
8. fix some preprocess problem

8.28.9(2023/12/21)
1.fix find_charge_station bug
2.add log to return_standby_cmd
3.fix P87 send point to MR bug

8.28.8 (2023/12/21)
1. update alarm code list of AMR
2. fix key word not right for JCET erack infoupdate
3. correct the naming rule for skyworks SG and JP
4. sperate vehicle_mgr to vehicle_mgr and vehicle
5. change folder name from vehicle to vehicles to avoid the conflict of module nameing
6. modify the host call command
7. fix elevator bug

8.28.7
1.modify when MR battery > BatteryHighLevel then end_charge
2.add new alarm for BOE

8.28.6
1. update graph2_with_process_Cdata_dijkstra.py
2. update route_count_caches.py to fix bug: commandID not match real in real event

8.28.5(2023/12/7)
1.add subcode
2.modify controller.py start E82 HOST param for ASECL
3.modify E82 CALL cmd
4.fix add_transfer_into_queue() double link issue

8.28.4
update mp_lib.so mp_lib2.so
remove auto_worker code for HH

8.28.3(2023/11/28)
1.fix order_mgr import time
2.modify vehicle_mgr return_standby_cmd() park when standby not selecting current point by Sean
3.fix controller start E82 Host param(for v2.7) and updata protocol_list

8.28.2 (2023/11/27)
1. seperate vehicle command part(vehicleAdapter.py) and vehicle routing part(vehicleRoutePlanner)
2. adjust the architecture

8.28.1
rewrite in work handling method eq_mgr to OrderMgr class
rewrite EqMgr class

8.28
1.normal support each host for each zone
2.use route_count_caches.py replace route_count.py
3.use schedule_by_lowest_cost for all type vehicle(no matter how manay buffers), not use schedule_by_better_cost for time improve
4.use thread call process, then call C code to find_nearest path

8.27.14
1.add vehicle.py find_buf_idx_by_carrierID() for vehicle appendTransferAllowed
2.modify append_transfer_allowed code from vehicle 'park' state to func
3.remove dummpyport callback code
4.modify vehicle return_standby_cmd() when other vehicle in the standby point skip that
5.fix erackAdapter_e88 update_groups_zones_areas bug
6.remove some tr_wq_lib logger

8.27.13.1
1.fix dummyport_for_asecl bug not add 'next_dest' algo
2.for erack for UTAC LotIn check bug
3.fix tr_wq_lib.py line 100 remove_waiting_transfer_by_commandID usage
4.enhance cancel or abort transfer when workstation be reset
5.fix cancel link command bug in transfer_cancel()

8.27.13
modify call command and pretransfer command to e82
add racknaming 29 for TPW
fix all dummyport loss update_params and import random

8.27.10.4
add BOE RackNaming and parsing method *E*-?? only support 3x4 now

8.27.10.3
fix dummyload port for ASECL

8.27.10.2
fix EqStatus changed view update for UTAC

8.27.10.1
fix e82 event report bug for multi hosts

8.27.10
support multi hosts

8.27.9.2
fix param input bug when create eRackAdapter for e82+
add workstation enable mask in special feild when h_workstation not alive

8.27.9.1
fix self.secegem_e82_h bug in controller.py, fix update_params in dummpyport, fix some bug in dummpyport_for_utac

8.27.9
add schedule by priority
rewrite call SecsGemE82.h, SecsGemE88.h to local var secsgem_e82_h, secsgem_e88_h

8.27.8
fix 'FromVehicle' swap bug
modify ouput VehiclePauseset to sync_output

8.27.7
support SJ 'FromVehicle' load cmd and relative unload cmd go first and rewrite some code about add waiting queue

8.27.6
fix enable and disable workstation recreate all dummyloadport thread
support new workstation state 'Tracking' for UTAC state change latency

8.27.5
1. fix bug that if execute bufconstrain port and normal port at the same time, the normal port will put to wrong port.

8.27.4
1. fix carrier to MR bug (add pretransfer flag)

8.27.3
version merge

8.27.2
1. supprt Crossing Transfer racknaming:28, not dispatch transfer when station static or dynamic blocking
2. replace dest from  '*' to 'return to' when dest is '' in SRTD dispatch func

8.27.1
1. rewrite secsgem.h or hh call dict or func method
2. fix workstation exchange display
3. add filter from running to unloaded for UATC

8.26.2
1. add NoBlockingTime and WaitTimeout to call command
NoBlockingTime: Timeout for calling a vehicle
WaitTimeout: Wait time when vehicle arrival

8.26.1
1. add call command and pretransfer command to e82

8.26.0

support UTAC couples dispatch 
support Skyworks racknaming
support TI racknaming
fix bug: if transfer cmd rejected, then trigger Order fail if SRTD enable
support disable workstation on dashboard
support Erack func option for LotIn, ECOut, LotOut, ECIn, Fault for special stage 
support workstation type for LotOut&LotIn, LotIn&ECOut, LotOut&ECIn, CarrierIn, CarrierOut, StockIn, StockOut, ErackPort
only -LOAD cmd will trigger Order status change Fail
fix carrierType code


support source to MRxxxBUF0x cmd
fix MRxxxBUF0x to Dest, carrierID check fail 
support SRTD auto issue cancel transfer cmd when relative transfer cmd fail


1.reorganize transfer cmd params:
A.Transfer cmd
carrierID from xxx to yyy

B.(preTransfer cmd) or (acquire action)
carrierID from ''/xxx  to * (mean vehicle assigned by TSC)
carrierID from ''/xxx  to yMRyyyBUF00 (mean vehicle specified by host, buffer allocated by TSC)
carrierID from ''/xxx  to yMRyyyBUF0x (mean vehicle buffer specified by host)
carrierID from ''/xxx  to yMRyyy(valid param)

C.(Deposit action)
yMRyyyBUF0x to zzz 

2.TransferWaitQueue setting priority
specified setting=>other setting=>default_setting

3.
(Call vehicle cmd)
stage cmd

8.25.18
1. add rstrip() to  vehicleAdapter P25(Cassette Status Report)
2. add log to vehicleadapter
3. add clean current_route in get_right() when vehicle in man_mode or alarm


8.25.17
1.fix appendTransferAllowed bug
2.add racknaming 26 for TI BUMP

8.25.16
1. change loadport state mapping of 0 from disable to PortOutOfService to prevent from not being able to enable by remote
2. do not let occupied route list have repeated station in vehicleAdapter
3. raise alarm if no carrier detected after acquiring

8.25.15
1.add racknaming 25 for TI FAB

8.25.14
1.add tmpPark to points Attributes
2.fix add_manual_route algo bug
3.modify vehicleadapter loop time to 0.01

8.25.13
1.add vehicleID to E82.TransferAbortCompleted

8.25.12
1.modify pretransfer cmd for SJ (only take 2 carrier to buf)
2.add e82 host cmd (assginlot)

8.25.11
1.modify TSC send to erack data by custom defined

8.25.10
1.add E82 TransferCompleted event to preTransfer

8.25.9
1.rename TSC setting SkipAbortLoadWhenUnloadAlarm to SkipAbortLoadWhenUnloadAbort
2.add TSC setting SkipCancelLoadWhenUnloadCancel

8.25.8
1. fix bug that sending port instead of point when using new robot command
2. do not re-docking if at the same point

8.25.7
1.fix bug when abort pretransfer load cmd


8.25.6
1.change back TSC send datasets to erack from 1 slot/once to 4 slot/once and by racknaming decide
2. modify cassette status report by buffer_num in tcp_simulator

8.25.5
1.fix: not support preDispatch for preTransfer cmd
2.fix: swap transfer source from vehicle,
received unload cmd first then load cmd after, or replace cmd,
not support received load cmd first then unload cmd after
3.modify schedule_by_better_cost middle_seq_list remove [::-1] if racknaming !=15(GF)

8.25.4
1.fix for Erack link zone
2.add reschedule_to_eq_actions,  reschedule_to_stocker_actions for K25

8.25.3
1.modify TSC send datasets to erack from 4 slot/once to 1 slot/once

8.25.2
1. fix stop cmd bug when MR sync after connected

8.25.1
1. add timestamp for UI output
2. do not release right if MR is disconnected (option)

1.fix E82 TrLoadWithGateReq and TrLoadReq event transferport bug

8.25.0
modify version numbers to MAJOR.MINOR.PATCH

8.24F
1. add link_zone to erack setting for SJ
2. modify decide_service_zone_common

8.24E3
1.add 'alarm' to e88 infoupdate cmd for SJ

8.24E2
1. add other class for MR alarm to prevent exception

8.24E1
1.fix E82 reassign cmd reply from S2F50 to S2F42

8.24E
1. fix waiting alarm code function
2. add alarm code filter

8.24D1
1. modify when doPreDispatchCmd don't go charge

8.24D
1.fix abort_tr_cmds_and_actions send E82 event(TransferCancelCompleted)
2.modify doPreDispatchCmd only force_charge to charge
3.fix tsc dispatch_transfer bug(only dispatch to first MR)

8.24C
1. replace space in carrier type to prevent from the leading space
2. add vehicle ID back to transfer command when tsc restart with executing command
3. split carrier type directly when assign parameter to erack adapter
4. fix rfid report bug of P87 in tcp simulator
5. change carrier type and rename rfid timming, now will do it when bufs status change in agverrcheck
6. fix robot command assign bug

8.24B
1. fix tcp_bridge_simulate P87 bug
2. modify vehicle DisablePort2AddrTable function
3. modify when doPreDispatchCmd don't go charge
4. add VehicleID to E82 event (Transferring TransferCompleted) for vid_v3_biwin

8.24A
1. fix score function bug

8.24
1. set alarm subcode to alarm code if not exist.
2. change REASSIGN cmd format
3. add carrier prefix to global variable carrier list(for new robot command)
4. fix get carrier type logic in transfer command
5. change reassign logic to check either CommandID or CarrierID, CommandID first if conflict with CarrierID
6. add rewrite rfid to MR when rfid read fail
7. change location update range to 1500 when alarm
8. add new robot command
9. fix get speed value bug with new graph
10. add safety lock for trigger move control twice
11. clean local_tr_cmd when task abort
12. add local_tr_cmd_mem for recovery command
13. add type to bufs_status for recovery command
14. update tcp_bridge_simulator to 2.6 ver.


8.23F
1. add SkipAbortLoadWhenUnloadAlarm in TSC setting
2. modify use ABCS first if force_charge else use Normal chargestation first
3. modify vehicle log from Gyro_tsc to Gyro_MR

8.23E
1.fix some for REASSIGN cmd
a.only support single cmd commandID, replace cmd need add '-LOAD' or '-UNLOAD' suffix
b.add search vehicle.CommandIDList
b.fix CommandID add to vehicle.CommandIDList

8.23D
fix: remove branch in clean path func for K25
fix: add clean buf with command note when abort for K25

support preTransfer cmd(carrier to * or source to *), transfer carrier to MR itself, and not clean when exit park state

8.23C
1. combine K25 code to main code
2. add recovery to near stock for K25
3. mask wait_error_code function fix auto send move cmd in man mode when reset
4. add 'socketio_connected_evt' to refesh UI state
5. support py2 or py3 cna run

8.23B.P3
1. add score function to get route algo based on dijkstra map
2. add reassign function to redirect dest port
3. add lstrip for vehicle rfid report
4. change alarm lock distance to 150cm
5. fix enable edge not work bug
6. fix jcet dummyport status decode problem
7. fix property 100 problem
8. sync all format of transfer type cmd in e82

10. add SV_TransferCompleteInfo to TransferCancelCompleted in e82
11. fix bug which not update vehicle bufs_status local_tr_cmd when doing recovery
12. fix bug which get wrong action in vehicle
13. change rfid read failed logic
14. add delay send alarm when robot or MR error
15. remove P513 in vehicleadapter

16.support blocking event, routing fail event, change cmd

8.23A.P3
0.support python3
1.add recipe in e88 infoupdate
2.remove 8.19E lower level erack for spil CY code
3.support multuprocess for get_a_route


8.22J
1.when add transfer cmd but carrier on the vehicle will update bufs_status
2.modify abort_tr_cmds_and_actions

8.22I_K25
1.support 3 drop stocker, TrLoadReq, 3 pick stocker, 3 drop stocker, 3 pick stocker, 6 output EQ
2.at same statio and point, not do forward and backward align
3.support back tarnsfer, reassign to one stocker

8.22I
fix vehicle rfid space problem
fix erack port 13-16 problem
raise alarm if carrierID in command is blank and rfid read failed

8.22H
1.add zonetype=3 for turntable
2.modify tsc get_weight() for FST

8.22G
1.support PreBindCheck for jcet CIS

8.22F
1.
fix XXXMRXXBUF00 'Port not found' bug in TSC cmd dispatch
2.
Carrier check in transfer waiting queue must check else have a bug

8.22E
modify auto_recovery fun to old version


8.22D
slow down the frequency of ABCS status update
do not attach to the nearest station when moving
let alarm code from vehicle be checked first
raise alarm in next loop if vehicle state error
do not raise alarm repeatly when not able to find charge station or standby station
fix old get right thread not close bug
report segment when MR moving for K25
add warning report for MR (spec 2.4+, alarm id=10032)

8.22C
1.
if GY003 not in Erack
GY003 from * or E0P0 or '' or SourcePort not workstation to DestPort =>Reject, carrierID not locate
2.
Add TrAddReq and Assert TrAddReq into proxy, e82_equipment, tsc check for K25
3.fix auto_recovery bug

8.22A
1.modify AllowBackwardSearchEnable add SearchLimits

8.22
1.add new alarm
2.add erack carriertype check on transfer_format_check()
3.modify auto_recovery function
4.add carrierID check before acquire finished

8.21N
1.fix ABCS start bug
2.fix predispatch cancel clean flag bug
3.fix tsc Thread double lock bug
4.modify when vehicle do predispatch don't do Normal charge
5.fix appendTransferAllowed bug
6.fix stop_cmd bug
7.update alarm subcode

8.21M
1.modify dummyport_for_jcet
2.fix rackport_format_parse racknaming==16 for SJ
3.map generate with new lib

8.21L by Sean
vehicle : vehicle charge station pathing optimization

8.21K
1.add AbortAllCommandsWhenErrorAlarm func option
2.fix buf_contrain select method
3.enhance append_transfer include backto stocker

8.21J
modify Append Transfer Allowed function
modify vehicle.vehicle_onTopBufs

8.21I by Sean
Reversed Direction Edge for overtaking (Edge Properties Setting)

8.21H by chocp
1.fix zone change bug when recovery_transfer cmds (due to workstation not ready)
2.add dispatch waiting queue sort by first cmd priority high and receive time 
3.add dispatch waiting queue with neighborhood vehicle
4.add wq_lock for accees wq, and can append_transfer before vehicle back to erack
5.add more rack naming
6.fix CPU loading too high in loop check find_charge_station when vehicle unassigned, by exhange or charge algo in 
7.add 'sourceType':'Normal' in all host_tr_cmd

modify stockoutout cmd for FST
modify trbackreq for SJ
modify host_stop_vehicle cmd 

8.20C
modify E82&E88 secs port to 6000&6001 for qualcomm
fix E88 zone_capacity bug
add when cmd have CarrierID and source port can be sector name (only for qualcomm)


8.20D
updata stock-out cmd and fix bug

8.21
support StockOut replace cmd to do predispatch
support ErackOut cmd(include replace cmd, tow single swap cmd) in Zone waiting queue to do predispatch
copy waiting queue setting with preferVehicle to relative vehicle queue
fix 'NULL' action seq in schedule_by_better_cost.py

8.21A
fix merge_max_cmds bug

8.21B
fix merge max eqp problem
fix route enable problem
add carrier id in EQstate for utac loadport(by yoyo)
add alarm control in vehicleAdapter

8.21C
no begin command after stop charge cmd and execute job
set alarm to vehicle
fix transfer command missing transferState problem
return to faulty erack when RFID not correct
add delay while retry to connect to MR

8.21D
update E84 inter error alarm level for FST
add new alarm for charge time too long
add P89 for e82+
fix merge_max_eqps bug
update VehiclePoseUpdate info to UI
update vehicle find charge station function
add source port duplicate function
add erack online event

8.21E
for SPIL LG sampling re-arrange destport to sector


8.21F
add new alarm for host stop vehicle
add E82 new command(StopVehicle)
add trbackreqforEQ for SJ
fix recover cmd bug

8.21G by sean
vehicle : vehicle standby parking optimization

8.20B
change stop vehicle command from P512 to P513 for spec ver 2.3
fix nest for loop using same symbol in vehicle.py
fix zone compared bug

make a standalone waiting queue with equipmentID for stockout workstation,
host cmd belong a zone, add into a wq(queueID may zoneID or equipmentID)

8.20A
add Merge Max Eqps function
fix stockout cmd  when alarm will cancel the link cmd

8.19I
support racknaming 13, 14 
support Erack CarrierID check enable
rewrite some code in vehicle.py

improve receive Tcp Null String issue in eRackAdapter.py
create UTAC workstation model and renew SRTD code
fix swap task exec sequence with fifo in schedule_by_better_cost.py
fix SRTD for HH 

8.20
fix go work below low level when charge abnormally stop problem
add dynamic enable route/disable route api (need test)

8.19L
add no valid buffer alarm for empty carrier

8.19K
add transferstate to commandinfo (for qualcomm)
completed auto door function
fix trigger eq acquired complete event before update carrier

8.19J
Auto generate work for HH
add work list timer
updata workstations state by equipmentID
fix bug when stockout cmd no carrierID
add e82 infoupdate cmd

8.19H5
update when can't go chargestation and standby only send once alarm
fix e82_equipment ercmd callback error from S2F42 to S2F50
add commandLivingTime in zone setting

8.19H4
update MR alarm code
add KeepCarrierOnTheVehicle when auto recover
add PreDispatchForRack

8.19H3
fix bug for vehicleAdapter (get_right)
fix bug when reroute not begin flag

8.19H2
support open door assist before TrLoadReq or TrUnloadReq

8.19H
getroutetimeout => Error
straight first function
add lower level slot extend function

8.19G
add WithdrawJobOnDemand option in tsc settings

8.19F
add some miss event and alarm to vid_x.py

8.19E
add several parameter to transfer cmd in e82
add several parameter to infoupdate in e88
add use lower level erack for spil CY

8.19D
add stop command in not force charge routing when receive new batch job
add new alarm level 'Info' that is lowest level and not trigger secsgem report
add BaseReplaceJobWarning alarm, level is 'Info'

8.19C
fix schedule by better cost algo for eq to eq transfer
fix TrUnLoadReq for pending, change TransferPort from self.at_station to self.action_in_run['target']
add sub_code "TSC015": "CarrierID duplicate in waiting queue"
add sub_code "TSC016": "CarrierID duplicate in executing queue"
change 'MapUpdateCompleted' output event to async

add host offline warning??

8.19B
update decide_service_zone_comm when one is other use other one to decide service zone
add more charge station function


8.19A
query all info when re-connected and get auto message


8.19
add MapUpdateCompleted event for route generated successfully
fix MoveRouteObstaclesWarning exception when autoreroute trigger

8.18K
update swap cmd when upload cmd be abort will also abort load cmd

8.18J
add battery exchange CEID to E82
fix battery exchange bug

8.18I
fix transferAbortCompleted event trigger moment
modify CARRIERID and COMMANDID max length for secs/gem
update erack dashboard when lotID len=1 ,Do not show (1)

8.18H
fix decouple swap command due to overwrite carrierID duplicate transfer cmd

8.18G
fix some issue about equpdate and portupdate
add '^' to abcs msg

8.18F
modify erack waterlevel warning without booking

8.18E
force digital setting covert to int for TransferWaitQueue, Vehicle, Erack

8.18D
add carriertype for erack setting (for auto_recovery to choose erack with carriertype)

8.18C
fix z-index is not int problem

8.18B
add ResetAllPortState in e82_equipment
change TSCUpdate and STKCUpdate state to mState

8.18A
add dummyport_for_jcet

for loadport select
python2 ./controller.py -url 127.0.0.1 -loadport jcet / hh


add E82 PortStatusReq secs event
add ResetAllPortState secs cmd
add PortState secs cmd
add EqUnloadComplete secs event

8.18
update FaultRackFullWarning alarm level from Error to Serious
fix tsc loop delay from 0.5 to 0.1 sec to speed up command add

fix EQStatusReq, EQState format in e82_equipment.py

fix vehicle.py and vehicleAdapter.py support 12 buffer in MR
add schedule_by_better_cost for MR buffer size > 4

add queue mechanism to ouput view function

8.17
fix idle charge algo, now will restart charge flow if vehicle automatically discharge
add reroute function
add battery exchange function
add map change function (need test)

8.16H
fix CommandDispatch function

8.16G
fix E88 status dashboard bug
fix eRack_e82 alarm set
add racknaming #10 for SPIL ZG

8.16F
change carrier type(global_cassetteType) setting to global_variables.py

8.16E
add E88 status dashboard in erack dashboard
fix idle charge bug when MR in charge state turn man model
add log for dispatch cmd to MR

8.16D1 special
bug free for 8.16D
-add log for dispatch cmd to MR
-add queue mechanism to ouput view function

8.16D
fix charge complete algo

8.16B
fix some secsgem query SV bug
fix when MR disable status should be remove
fix alarmID 40007 alarm text

8.16A
fix booked bug with TrloadReq change cmd
add protocol_list for QUALCOMM

8.16
fix residual book when erack slot error after MR depositing completely
add var:with_buf_contrain_batch to guide buf allocate seq 4321 or 1234
In dispatch_transfer_with_token, dispatch_tr_cmd_to_vehicle of first loop have bug, fix by Jason, 2022/7/13
fix lstrip problem
modify buffer constrain to BUF01 and BUF03

8.15D
detail Online/Offline display to ControlState and CommunicationState
fix bug when abort cmd in executing queue will delete other valid action after acquiring or depositing finished
support 8 and 12 buufers in vehicle
add v2_asecl protocal(no commmandID)
enhance control online and control offline func
to differentiate load or unload fault erack for do_fault_recovery

8.15C
add iot module
add protocol module
add secsgem online/offline to support not trigger MCS when TSC testing
update secsgem lib

8.15B
fix cancel transfer cmd func

8.15A
1. Add BufferPosCheck for PositionError

8.15
1. Set PositionError to warning
2. Auto recover when move and robot in Idle
3. fix alarm code '10001' sub_code exception
4. fix tr_wq_lib line 631 line, get() lost a '' default value
5. fix alarm reset code, fix remove tr_cmd loop for leave a residual
6. add and fix ChargeCommandBreakOff, ChargeCommandTimeout, DischargeCommandFailed


8.14L
1.fix transfer_cancel() to support report 'TransferCancelCompleted' to host not only primary cmd  also auto cancel link cmd
2.auto reset booked to option


8.14J
1.add scheduleAlgo select (by_lowest_cost, by_fix_order, by_auto_order),
  order divide upload order and load order,
  by_order only support one buffer for one cmd, support oven proces
2.add strict check foup of carrierID and commandID for depositng
3.fix charge complete algo

8.14I
rebuild alarms
    1.add SV_SubCode for secs/gem
    2.add TSC001-TSC012 for TSC subcode
    3.Update ('AlarmSet') event params


8.14C
fix BUF Constrain Algo
add source_type(not sourceType) in local_tr_cmd

8.14B
add Load and UnLoad request check in vehicle TrLoadReq/TrUnLoadReq check

8.14A
add erack and zone waterlevel alarm setting

8.14
support StockOut preDispatch
support eable Buf Constrain to Buf01 ad Buf02

replace VehicleMgr.getInstance().vehicles.items() by change global_variables.Vehicle.h

bundle same equipmentID transfer cmd in waiting queue together

8.13J
change keyworrd 'user' to 'channel' in add_transfer_cmd

8.13I
add transferAbortCompleted event for UI
add user(secsgem, webapi, internal) param in add_transfer_cmd
fix white mask func

8.13H
fix no output update event when MR disconnected

8.13G
add Rack Naming:9 # for QUALCOMM, add TurnTable erack function
add 'C12N2' black mask in CarrierID for LG 2022/6/7
remove all about 'STAGE' transfer cmd and 'ACQUIRE_STANDBY' action
add WorkStation 'ReturnTo' can be set by unload_cmd

8.13F
fix bug:  change carrier to identified state event if carrier at Booked state
fix bug:  comment reset_indicate_slot, reset_book_slot at complete transfer success!
          avoid race condition to reselect booked slot if get new command at monent!
fix bug:  fix abort command can not get local_tr_cmd when no action in run problem
          add abort by other cmd type

8.13E
fix machine info bug in eRackAdapter_e82
update secsgem library for more complex transfer command

8.13D
add addition info to alarmset event
add connection state to vehicle state event
change charging state from on/off to true/false
regard end charge failed as move command rejected when sending move
fix bug: adapter.battery['charge']=='On' in vehicle 2274,2275 line

8.13C
DestPort duplication check valid for workstation for Erack operate mistake
fix heartbeat from 5sec to 3sec when vehicle not in moving
fix some code(check h_eRack...), when no erack build in system #2022/5/24
fix into recovery loop if alarm happen #2022/5/27

8.13B
do not check vehicle head when releasing route right
fix robot get right bug
modify transfer init event and transferring event trigger time
add machine info in erack info for erack adapter e82
add robot get right timeout alarm

8.13A
ouput battery charge status 'On' or 'Off' in all vehicle event

8.13
support preDispatch cmd:
1.fix ExecuteTime params in host_tr_cmd
2.add repeat validinput req in TrLoadReq and TrUnLoadReq state, timeout is ExecuteTime if >0
3.fix duetmeupdate remote cmd handler

fix eRackAdapter_e82.py add water level warning

8.12F
Add add_executing_transfer_queue in do_fault_recovery() for reset book slot when recovery alarm
fix  replace for command_id in self.CommandIDList to for local_tr_cmd in self.tr_cmds in reset_alarm_cmd

8.12D
change mr offline alarm level to Error for auto recovery
force to find a standby station if other MR is waiting

8.12C
fix bug 1: recovery h_vehicle.AgvSubState='InWaitCmdStatus' when exception
fix bug 2: auto cancel link cmd when primary cmd be cancled

8.12B
add off line warning log
add vehicle state log


8.12A
add try .. except for get_dist_empty_rack_port()
vehicle not auto major 'other' zoneID

8.12
add stage msg merging method as lot ID
prevent from decoding ps protocol msg error
add msg to vehicle block event
fix vehicle state will exit enroute when finding new route
fix near_pt comparing bug

8.11H
add PS protocol P65 ,add new alarm code 10027 MoveRouteObstaclesWarning

8.11G
add more in do_fault_recovery(), select nearby port from vehicle for fault area(ex:NG_PORT)

8.11F
fix Erack auto dispatch to Erack funxtion

8.11E
add vehicleID in TransferTask output to UI
add merge_max_cmds limit protect in waiting queue dispatch
add protect DestDuplicate attack cmd link in waiting queue dispatch

8.11D
add connect retry time setting

8.11C
fix mr offline retry problem

8.11B
add port type for several event in e88
fix serious alarm auto recover bug when alarm not set from MR
fix bug move command can be sent even if latest move command is still sending

8.11
add port_areas_revert dic for re-select rack area empty port for deposit
add robot_timeout for user define
add call_support_delay
add man charge cmd filter only in AgvState=='Unassigned'
replace action_in_run.get('uuid', '') by local_tr_cmd.get('uuid', '') #because no ''uuid' key in action
fix a bug, when re-deposit erack, book slot can not be reset
add valid input mask in workstation for TrLoadReq or TrUnloadReq
for every transfer_waiting_queue add indepentent BatchRun setting

8.10C
replace TSCSettings.get('Other', {}).get('RTDEnable') by TSCSettings.get('RTDMode', {}).get('Enable')
send alarm msg to UI when MR set alarm
fix delete all vehicle/erack doesn't update bug
reverse position error alarm level
remove position error check before depositing
fix position error continuously sending problem

8.10B
update MR subcode

8.10A
change seq num to (datetime + 4 bit numbers) for web to tell if the event is the same as last one
change position error alarm level to serious
fix last point update problem when in manual mode or alarm occurred
add position error and unknown check before depositing

8.10

fix set front_end_config_complete=True when map config complete, to avoid TSC enter TSCAuto

replace 'ErackStatusCheck' with 'BufferStatusCheck'
add slot book display vehicle + source in desc item
add ReturnTo First function and shortage code about check and assign dest port
add auto dispatch Erack to Erack when waterlevel high

add auto_assign_return_to_port support xxx|yyy,zzz destport

fix BaseCarrRfidFailWarning level from Error to Warning and no raise exception
#fix 'TSCPowerOn' output to not sync

8.9G
modify rfid read fail alarm level.
prevent tsc from keeping sending read fail warning.
add buffer status check function.
force check erack status when load/unload.

8.9F
fix service zone initial bug
modify leave station range from 80cm to 150cm

8.9D
fix no prepare parameter bug

8.9C
add output 'TransferCancelCompleted' event at waiting queue cmd be cancel, so commmads log can query from database
add E82.TransferCancelInitiated and change E82.TransferCancelCompleted seq when overwite transfer cmd with carrier duplicated
add recovery_transfer remote_cmd (no trnasfer format check again) for agvc recovey waitnf queue cmd when tsc restart

8.9B
fix charge and park setting for every vehicle bug

8.9A
fix dynamic_avoid initial value bug
fix manual robot command naming problem
set secsgem parameter in run function instead of initial function
add z parameter to round a point function
fix dispatch problem in tsc, now will sort received time for the commands
update vehicle z-axis with last point

8.9
check charge and park setting for every vehicle if have, or use global tsc setting
add commandID param for BaseNotAutoModeWarning, BaseOffLineWarning, OperateManualTestWarning alarm

find a issue when one MR disable, another can't support it

8.8E
fix alarm problem
add secsgem timeout setting(proxy and equipment)
add robot check function // PS protocal 1.5, P89, need test
fix vehicle carrier id show ReadIdFail problem
fix wrong ZoneState problem
TODO: e88 alarm wrong parameter problem

8.8D
fix carrierType output in add_executing_queue
fix do_faulty_recovery meet without carrierType exception

8.8C
fix bug: alarm notify() def change handler=SecsGem.h => handler=None

8.8B
fix erack adapter zone problem
fix get route timeout message problem

8.8A
enhance duetime format check
enhance AgcErrorCheck detect ReadIdFail or ReadFail
enhance deposit safty check, allow select buffer by cmd if local_tr_cmd['CarrierID']==False only
change  local command_id of MyException of Alarm class used for reject cmd event

8.8
change: accept dest port not in workstation or rack port
add workstation running duetime


8.7E
fix new_auto_assign_dest_port() exception ex: DestPort=='ER-B03|ER-B04' for spil 4
change command reject event,use alarm.command_id instend ComandInfo['Commandid'],
fix regular problem for spil 4
modify carrier loc by naming
fix vehicle location index disappear bug
fix alarm level for Erack check

8.7C
to enchance: select_dest_port_in_racks() func,
             select a slot in most empty slots in column to improve MR working time,
             because next time will next slot in same column

8.7B
fix AgvErrorCheck 'local_tr_cmd' key error exception, because self.action_in_run sometime is {}

8.7A
fix a bug: change sequence in unassigned state from do_recovery, parked, charge, exec transfer,
                                               to   do_recovery, exec transfer, charge, parked,

8.7
a bug

8.6E
add carrierType to output TransferExecuteQueueAdd/TransferWaitQueueAdd
abolish action_in_run['uuid'] to action_in_run['local_tr_cmd']['uuid']
fix tsc pause, pausing method
fix order status change fail when dispatch dest not search

8.6D
add reset from agv function
update agv error list
update vid_v3 error list

8.6C
re-write TransferInfo['DestPort'] if auto change deposit target
make sure VehicleAssign E82 event mutux with VehicleDepart E82 event

fix GpmErackAdapter_e88

modify round point radius to 500mm when vehicle alarm

8.6B
enhance force charge check in end of parked state

8.6A
set default pointID if node group null


8.6
add TransferFormatCheckReject, TransferParamsCheckReject

8.5B
add check cmd id duplicator
eracks in same group will combind into one zone in e88
modify dead lock counting from 1 time to 10 sec in vehicleAdapter
fix repeatedly going to avoid location bug in vehicleAdapter

8.5A
fix a bug

8.5
rework print_rackport_format, rackport_format_parse and special for GRA

8.4E
special for spil 4 average stock with Erack group
fix order direct_dispatch bug, not aligment

8.4D
fix bug: add zone_wq.dispatch_transfer return True or Fail
fix bug: select_dest_port_in_racks

8.4C
fix bug: not import Equipment in tools

8.4B
fix average erack capacity
add new_auto_assign_dest_port() func
add robot check when recovery transfer cmd when move error

8.4A
fix auto assign dest port check

8.4
fix recovery, standby or charge hang by exception in unassigned state
fix group matching namong  from group* -> group

add more port workstationID, workstationID+'A', workstationID+'B' in EqMgr.getInstance().workstations dict
change workstation search method

8.3D
add charge before unassigned if force_charge True
fix bufs_status['local_tr_cmd'] default to {} from None
change dummyloadport_AB2 dispatch callback to True
add reset_book_slot and re_book_slot when change cmd get

8.3C
fix self.workstations to EqMgr.getInstance().workstations in dispatch() of eq_mgr.py

8.3
fix junction avoid bug
modify infoupdate for e82
fix A-B-A group problem(need test)
fix vehicle speed can't modify bug

8.2
add battery event

8.1
change workstations from list to dict
add sync and retry func in import output
fix tsc initiated state to run loop, and start thread in main loop
fix dispatch cmd with token will hange,  when send replace cmd in MR with 1 buffer
support carrierID:'*' or 'None' to ''


8.0
rewrite auto assign dest port algo
add dest_type(workstation)) in local_tr_cmd and report DestType in TransferComplete event

7.10
fix vehicleAdapter auto avoid bug
modify SPIL CP naming rule
add _* as wild card in tr_wq_lib

7.9
support select_any_carrier_by_area
support emptycarriermove func

7.8. fix set 'InWaitCmdStatus' timing, avoid tsc can't set cmds

7.7.


7.6
fix charge cmd race condition problem

7.4
support change cmd dest to workstation, area, rack for any rack naming
auto fill carrierType when replace command only with one carrier
fix CarrierType None or Check Error for Acquire/Deposit Error

7.3
support Disable Vehicle Buffer function
support change cmd at TrLoadReq for spil 4

7.2
fix global_moveout_request[h_vehicle.id] =>get(h_vehicle.id, '')
fix retrun after deposit in TrLoadReq State
disable drive to park function in Parked state

7.1
support sensitive carrierType by carrierID prefix or commandID


7.0
open all config in tsc setting


6.24C
change erack alarm code to 2XXXX
delete carrier loc of erack off line alarm
change erack water level alarm system
fix incorrect carrier loc problem in several alarms of erack
return sector name as CarrierZoneName if sector exists
clean LotID if LotID is empty
fix charging check bug


6.24B
add dynamic_avoid func
mike add start_charge/end_charge flags in vehicle charging

6.24
add carrier white list and alarm 40010
add release alarm for move status Error
support change cmd priority in wq

6.23B
fix direct_dispatch make transfer cmd bug

6.23A
add handoff to several events at E88
add DUETIMEUPDATE at E82

add new erack when project change
fix raise alarms.commanddestdiplicate DestPort with carrierID

6.22A
fix duplicated command id issue

6.22
fix change project problem

6.21F
fix go park bug at parked state
won't go park if MR is doing swapping

6.21E
add robot get right function
raise get route timeout if traffic jam is detected
fix global plan route from current section to all the route

6.21D
add TrUnload check when replace for spil 6

6.21C
add assign_dest_port_by_group if DestPort is Erack-*


6.21B
enable edge disable function
add go standby in parked when other vehicle wait
add area_id display to erack like box_color
add tr_assert more check

6.21
update erack box_color display for sector/area


6.20
update traffic algo
add get route timeout handling method
add CommandDestPortDuplicatedWarning for spil 6 CP

6.19
fix alarms.DischargeCommandFailedWarning/ChargeCommandFailedWarning lose CommandID

6.18A
fix block node calculation(considering with groups)
remove find route cost check if is bigger than old one
fix auto/manual bug (recovery and manual command race condition)

6.18
fix cancel and abort cmd log
fix AlarmCode default to 0

6.17
fix bug .eracks => .eracks.items()
fix port_areas.get by dest_port_area default to []
force TrLoadReq and TrUnLoadReq for spil LG replace cmd
fix dest_port_area parse


6.16
fix bug and enhance in erack group and area parse

6.15A
e82proxy fix
add charge alarm
add plan route check when executing junction avoid
add block node to get_a_route at the beginning (vehicle.py)

6.15
fix default 'AlarmCode':'' to '00000'
change decide_service_zone for spil CY again

6.14
fix default 'battery':'' to 0

6.13
change from, to check workstation first!

6.12
update decide_service_zone for spil CY, see workstation and dest first,
add force_charge display

6.11
re-code enable/disable vehicle
re-code enable/disable eRack_e88
re-code enable/disable eRack_e82

6.10
re-code enable/disable vehicle
re-code enable/disable eRack

socketio need enhance
auto backup ...

6.09
clean all carriers if erack is disabled
vehicle get right based on distance

6.08A
add level(Serious, Error, Warning) to alarm report

6.08
add level(Serious, Error, Warning) to alarm report
fix self.standby_station->standby_station in update params

6.07B
fix standby

6.07
enchance dispatch transfer, avoid can't add into queue
abort all command when 'Serious' alarm reset in auto recovery, or
abort all command when
update eRackAdapter_e82.py

abolish charge_end() in alarm_handler()
fix AgvErrorCheck return value and handle code
add VehicleInternalWarning and fix relative alarm code

6.06
fix go park bug
disable secsgem alarm set/clear limit(need test)


6.05
add force_charge flags for call other vehicle support
fix e88/e82 alarm_set delay from 0.5 ->0.05 sec


6.04
fix route_count bug: same station issue
fix vehicleAdapter bug: manual exception if at_point is killed
fix eRackAdapter_e88 bug: can't clean data if erack reconnected
clean right if vehicle is disabled

6.03
add disptch waiting queue with cmd limit
fix other vehicle support when primary vehicle go to charge(include charge), remove, and pause with Serious Alarm

6.02
add cassette type in secs transfer cmd and associate cmd

6.01
fix some

6.00
support max 6 cmds to MR

5.59A
fix order schedule bug, in graph2 dist[CP][FP]>-1 from 0 alarm_handler dist[FP][TP]>-1 from 0
fix 0.5sec delay in set alarm

5.59
use auto allocate buffer by carrierID commandID

5.58A
change AgvcErrorCheck sequence, put not auto check after robot, move, other alarm, manual, offline ...

add self.charge_end() no condition in move_control

keep 
if self.battery['charge']!='Off': #????? 
            self.charge_end()

5.58
limit order weight only for LG
fix charge complete immediately after charge start

5.57C
...
fix dummyloadport_AB  do TrloadRequest only on RTD mode



5.57B
add NearDistance
move abort cmd from alarm_handler to clear_handler

5.57A
add order in new_schedule2.py and route_count.py

5.57
change action order algo
support OCR dummpyport_ab to call replace trnasfer

5.56C
fix abort cmd cause by host, by man, by replace, by alarm
fix E88 water level alarm code
add delay to unassigned state for mq sequence
fix raise stans exception

5.56B
fix last point after reset alarm
fix vehicleAdapter charge on/charge off wait battery status change
fix E88 alarm code

5.56A
    self.enable_begin_flag
    fix inital erack carriers, last_carriers, lots, read_carriers
    add secs water level hight/low alarm


5.56
fix host dispatch cmd, self recovery cmd, self standby cmd, self charge cmd meet race condition
fix dummyloadport_AB for ASECL OCR
fix alarm code function for tfme
(alarm event add altx, and parms string, warning auto clear, error tsc auto reset, serious ...)
support 8" 2 site AMR, move with begin and wait charge off

5.55
for e82+
python2 ./controller.py -url 127.0.0.1 -api v2.7
for e82+e88
python2 ./controller.py -url 127.0.0.1

5.54
enhance alarm code


5.53
change re-assign dest port by 'rack' to 'group' when load eRack check fail for spil 4
cancel ErackMgr.getInstance() method, replace by Erack.h_eRack
maintain (E82 v2.7) / (E82 v3.0 + E88 1.1) in one project
re-write alarm handling

5.50C
fix P85 (need test with real car)
add begin end function
fix park bug(can detect other car now)
fix auto recover bug(do not auto recover if car is not in auto mode)
support type B car(2 foup)

5.50
add standbypoint list to park
add replace carrierID duplicate cmd in waiting queue
fix alarm message to default

5.49B
use this:
###########
SecsGem.h.add_carrier($CarrierID, {
                     'RackID':$RackID,
                     'SlotID':$SlotID,
                     'CarrierID':$CarrierID})

if $CarrierID in SecsGem.h.ActiveCarriers:
    if SecsGem.h.ActiveCarriers[$CarrierID]['RackID'] == $RackID
        SecsGem.h.rm_carrier($CarrierID)
###########

5.49A
modify junction algorithm
fix junction bug
fix last point bug
fix msg reply check bug

5.49
add erack port naming for Spil LG r'(ER.+)-(.+)'
add eRack port_areas(ER_LG_WaitIn) for Spil LG
fix re_assign_return_port to assign_dest_port
add reset_book_slot
add reset_indicate_slot

5.48
add auto park when block others vehicle

may change erack name
may chnage average foup

5.47

fix systemID_gen() lock

add back func in workstation setting
add trace workstation state when tsc restart


5.46
1. fix wait reply pool bug
2. modify the round_a_point method
3. fix secsgem can't request the real time problem
4. fix system ID gen bug
5. fix wait ack bug
6. update location when error

?
?
?

5.44 or 4.44
1.fix vehicleAdapter last_point update bug, will cause vehicle crazy run when communication data lost  
2.fix bug, add continue after exec charge or standby in unassigned, bug will cause exec transfer when in charge
3.fix robot timeout check execption
4.associate machine, desc, book, lot(N) to eRack
5.indicate stock num/slot num to front end
6.new assign dest port by rack. group, zone 
7.fix SourcePort no CarrierID check when wih CarrierID
8.add book for, and show MR in desc column
9.modify junction algorithm

5.43

1.change add transfer or order check sequence

2.change eRackAdapter, indicate machine, book to erack when add transfer into waiting queue

3.
fix exec transfer cmd race condition witn park or charge cmd

4.
new lot associate cmd

add transfer executing queue update
fix return algo and alarm, cancel transfer

intall db for new 

5.42
controller.py
-add KeyboardInterrupt in controller to stutdown program by ctrl-C
e82_equipment.py
-modify the statement of alarm 10019 in e82
-add alarm 10021 10022 to e82
-add some parameter check to the remote command in e82
e88_equipment.py and eRackAdapter.py
-modify the statement of alarm 10002 in e88
-add stocker unit info to e88
vehicleAdapter.py
-add non_blocking mode flag
-add sending retry flag
-add system ID generator

5.41
fix erack naming, add type 4: ER-A-002--1

5.40

change charge algo
change standby algo
change waiting queue priority
add booking algo
support action output


fix transfercompleteInfo carrier loc not correct!

5.39

add associate more
add more alarm
add robot working timeout
fix vehicleadapter recv ack timeout
fix replace transfer back bug

abuse 'GOTO' action, replace by force_route

change priority stack 0~99, 100 mean immediately
change waiting queue schedule

add booked


new webapi
new agvc statics...

5.38D
enhance secs communication for fcc

5.38
fix SocketFormatWarning exception in eRackAdapter
fix CarrierRemove carrier status
fix transfer complete in abort tr when Error
fix fix define report commandID

5.38G
add carrier duplicator check, source, dest valid and respond ack
add new secs ceid, vid
add stage flag in recovery local cmd

5.37F
change command split from '-' to '-sub'

5.37E
fix erack port E88 report naming bug
add E82 Abort relative event
add E82 Cancel relative event
add CarrierID duplicate check

4.37D


erack exception add subcode
vehicle exception add PortID, eRackID, ..


re-arrange alarm code

4.37C
fix do fault recovery complete, have exception no tr_cmd
fix version check bug
fix long workstation name bug

4.37A
update alarm code, result code, and relative secsgem code
add occupying route right when robot is working(additional property)
add clean route and wait vehicle stopping when manual mode on(need uncommand)


4.36
fix bug add_work_list with priority
a bug
fix operate work with  transferInfo to transferinfolist

4.35
support E82 Stage host command
rewrite cancel and abort transfer cmd code

4.34A
fix start sequencr, tsc config need first
fix eRackadapter exception h_eRack->h

4.34
support custom define erack and port pattern
support port len > 7 chars

4.33

fix secsgem lib for new s02f49 format
add group junction

fix 'go' -> 'g'
fix sweep no buf bug

4.31C
add reset_alarm_cmd=True in alarm handler
fix unload_cmd_evt work an any workstation state


4.31B
trigger alarm when can't dispatch tr_cmds to vehicle
optimal action gen and recovery
optimal agvErrorcheck()

4.31A?
need change dispatch rule 1. by source zone, 2. by workstation zone, but unload/load cmd may divide to two vehicle
need fix auto recovery problem:10003 move base error?
fix power on, off line view program
add abort_order in order dispatch, play will abort relative transfer cmd
add release_order in order fail, play will reset port
rewrite dummyloadport state machine for bypassmode

4.31
add code
fix locate bug

4.29

how to dismiss order when port not found 

robot at home check

add VehicleRoutesPlan event to database
add Oder hold status for carrierID not not checked

fix remove, popleft self.actions exception

4.28
fix bug eq_mgr.y line 333
redefine machineID, workstationID, portID


4.27
acquire erack need verify checked and carrierID ?
fix waiting order bug (when machine NA)
add lock to operate work_list and delete for idx code


4.26
support P87 long name of port and version check
enhace receive erack format not alignment


4.25A
add recovery order list and waiting transfer list, exectuing list will delete and response error
add erack checked fucntion(delay report movein event to host) and support new erack protocal
fix erackAdapter sync data period(need 3 echo) to eRack to avoid too data (>1500 char) erackAdapter
fix new web with go flags problem
fix manual mode route func
new PoseTable format
add new cmd to support long workstaion ID
use vehicleAdapter.last_point replace vehicle.at_point

4.24
sync active racks and active vehicles at e82
move car location when receive unknown arrival

4.23
stop before junction point instead of stop on junction point.
fix the bug caused by not getting the right of the station where the car is.
wait 3 more cycle to find new way if the car is at avoid station.
remove setting 'K' if two stations are close.
add vehicle SOH and send event when SOH change
add erack loc property
acquiring right when going to last 2 station
not keep sending connection failed alarm
add auto charge when vehicle unassigned > idle_time(ex:60sec)

4.22
fix sending cmd bug caused by threading
fix too many threading issue caused by update location
send 'K' instead of 'G' if the station is very close to the previous one (occur at cross roads).
add lock at generate route

4.20
fix auto charge in vehicle unassigned state, and battery < limit
improve traffic control
fix loadport link crack?

4.19
fix add lotID in Order cmd
fix vehicle in unassigned state and wait 60sec timeout, auto go to charge, and will repeat when vehicle battery=100% (because at battery 100% charge will auto off)
fix vehicle need in auto charge setting, then execute above action

4.18_2
fix vehicleAdapter.py - rounting
fix graph2 - cost length
add vehicle avoid solution
add point belong multi group

4.15
add distance check when target not reach to overcome points to close
add transfer cancel or abort or fail to set order fail, and make order fail to retry by man

fix vehicleAdapter NoRFIDCheck function
fix A&B workstation direct_dispatch function

need fix return standby policy

E*, MR* port need reserved

4.14
fit order management to keep fail command
support transfer source from vehicle buffer
fit go charge when vehicle in unassigned state and idle timeout
fix A/B port workstation management

4.13
add new port type(A/B port) and fix something
add EqStatusReq event(904, 5904)
add Idle port state
add clean point lock  in alarm_set
note never input w<0 degree to vehicle

v4.12


fix back_zone->back_erack
add vehicle fault_erack, ex:E001|E002
add erack zone, ex:zone1

fix charge, recovery command uuid
fix vehicleadapter in route waiting pose update bug
if Source Erack to E0P0, will assign vehicle fault erack

fix latency too long when manay node in a route 
add manual route, begin, end flags
fix auto set Go bug

v4.11
fix vehicle state control from remote
add tcp_bridge_simulator with initial point
add more break in if else loop
fix add edge direction
update vehicleAdapter.py(加入參數化各功能-修改小Bug充電中會一直嘗試釋放路權)
add EdgesTable and with group, speed ratio property

add vehicle manual/auto mode, and data sync
add BufferNoRFIDCheck

v4.10
add traffic control

v3.9
replace graph to mike graph with single or two way control
add and fix node group data
change secs port to 5000 from 6000, and change SimulateErack to 5600 from 5000
add vehicle adapter to get pointID when recevie point arrival report
add true vehicle simulator for traffic control

v3.8
support LotID='NA' or '' in order
support vehicle set simulate
add alarm_reset for adapter when Pause release

v3.7
fix erack repeat trigger portstatus update

v3.6
2021/2/8 change mcs.py to eq_mgr.py
2021/2/16 add auto reset alarm in loadport/dummyport, when vehicle alarm reset

v3.4
support rtd mode by dummyport and loadport

v21.8
2021/1/4 add self.at_point to VehiclePauseClear
2021/1/5 add port setting for loadport
2021/1/5 if get SocketNullStringWarning in loadport, then retry!
2021/1/5 add begin flags for every route start

2020/12/11 add binding to spread lotInfo to eRack...
2020/12/14 bug: residual cmd in queue, nano -l vehicle.py, uncomment self.tr_cmds=[]
2020/12/15 cancel dispatch cmd after remove foup
2020/12/16 bug: cmd1, cmd2, cmd3 exceute sequence not correct, so need edit tsc.py 300 line, fix i=>i+1

2.
cd ~
sh ./compile_mcs.sh
cp ./agvc_test/config.py gunicron.com.py .env .flaskenv ./agvc
rm -rf agvc_test

1.update secsgem.zip
cp secsgem.zip ~/.local/lib/python2.7/site-packages
unzip secsgem.zip

