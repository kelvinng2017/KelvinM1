from collections import deque
import traceback
import global_variables
import tools  # Introduce custom tool modules to use PortsTable and PoseTable.
from web_service_log import by_point_logger
import time
import datetime
import random

import re
from itertools import groupby



def query_order_by_point(point, order_type='loadOrder'):
    try:
        pose=tools.PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except Exception:
        traceback.print_exc()
        print('query_order:{} fail'.format(point))
        return 0
    
def find_point(target): #input: simple station or point, output: point

    try:
        return tools.PortsTable.mapping[target][0]
    except KeyError:
        raise ValueError("no port: {}".format(target))
    
def sort_key_by_port(port, acquire_type=False):
    match=re.match(r"([A-z0-9]+)(_I|_O)", port)
    if match:
        suffix=match.group(2)  
        type_flag=1 if 'I' in suffix else 2  
        if acquire_type:
            return -type_flag
        else:  
            return type_flag

def extra_check_sort(s0_sorted):
    if global_variables.RackNaming == 36:
        hot_point_acquire_items=[
            item for item in s0_sorted
            if item['point'] in ['carrier_hot_eq','4160_P01','4160_P02','4305_P01A','4305_P01B','4110_P01A','4110_P01B'] and item['type'] == 'ACQUIRE'
        ]
        hot_point_acquire_items_sorted=sorted(
            hot_point_acquire_items,
            key=lambda x: sort_key_by_port(x['local_tr_cmd']['TransferInfo']['SourcePort'], acquire_type=True)
        )

        hot_point_deposit_items=[
            item for item in s0_sorted
            if item['point'] in ['carrier_hot_eq','4160_P01','4160_P02','4305_P01A','4305_P01B','4110_P01A','4110_P01B'] and item['type'] == 'DEPOSIT'
        ]
        hot_point_deposit_items_sorted=sorted(
            hot_point_deposit_items,
            key=lambda x: sort_key_by_port(x['local_tr_cmd']['TransferInfo']['DestPort'])
        )
        index_a=0
        index_d=0
        for i, item in enumerate(s0_sorted):
            if item['point'] in ['carrier_hot_eq','4160_P01','4160_P02','4305_P01A','4305_P01B','4110_P01A','4110_P01B']:
                if item['type'] == 'ACQUIRE':
                    s0_sorted[i]=hot_point_acquire_items_sorted[index_a]
                    index_a += 1
                elif item['type'] == 'DEPOSIT':
                    s0_sorted[i]=hot_point_deposit_items_sorted[index_d]
                    index_d += 1
            else:
                s0_sorted[i]=item
    return s0_sorted

def record_sx_sequential(point, sx, uuid_order, uuid_priority_map):
    """
    At the specified point, record the actions in the order of ACQUIRE -> SHIFT -> DEPOSIT.
    """
    action_taken = False

    # ACQUIRE
    if point in sx["ACQUIRE"]:
        sorted_acquire = sorted(
            sx["ACQUIRE"][point],
            key=lambda x: uuid_order.get(x, float('inf'))
        )
        sx["ASSIGNLIST"].extend(sorted_acquire)
        sx["INCAR"].update(sorted_acquire)
        del sx["ACQUIRE"][point]
        action_taken = True
        by_point_logger.debug("Recorded ACQUIRE at {}: {}".format(point,sorted_acquire))

    # SHIFT
    if point in sx["SHIFT"]:
        sorted_shift = sorted(
            sx["SHIFT"][point],
            key=lambda x: uuid_order.get(x, float('inf'))
        )
        sx["ASSIGNLIST"].extend(sorted_shift)
        del sx["SHIFT"][point]
        action_taken = True
        by_point_logger.debug("Recorded SHIFT at {}: {}".format(point,sorted_shift))

    # DEPOSIT
    if point in sx["DEPOSIT"]:
        assign_uuids = list(sx["INCAR"].intersection(sx["DEPOSIT"][point]))
        if assign_uuids:
            sorted_assign = sorted(
                assign_uuids,
                key=lambda x: uuid_order.get(x, float('inf'))
            )
            sx["ASSIGNLIST"].extend(sorted_assign)
            sx["INCAR"].difference_update(sorted_assign) # from INCAR delete
            sx["DEPOSIT"][point] = [
                u for u in sx["DEPOSIT"][point] if u not in sorted_assign
            ]
            if not sx["DEPOSIT"][point]:
                del sx["DEPOSIT"][point]
            action_taken = True
            by_point_logger.debug("Recorded DEPOSIT at {}: {}".format(point,sorted_assign))

    return sx, action_taken

def check_received_time(transfers):
    """
    Sort the task list by the time the task was received.

    Args:
        transfers (list): A list containing dictionaries for transfer tasks. Each dictionary should include ['host_tr_cmd']['received_time'].

    Returns:
        list: A list of tuples, each containing (receipt time, original transmission task), sorted in ascending order by receipt time.
    """
    received_time_array=[]
    for transfer in transfers:
        received_time_array.append(transfer['host_tr_cmd']['received_time'])
    sorted_transfers=sorted(zip(received_time_array, transfers), key=lambda x: x[0])
    by_point_logger.warning("sorted_transfers:{}".format(sorted_transfers))
    return sorted_transfers

def div_action_by_priority(sorted_transfers):
    sorted_transfers=[transfer for _, transfer in sorted_transfers] # Unpacking the (time, transmission) tuple.

    by_point_logger.debug("sorted_transfers (by time):{}".format(sorted_transfers))

    # *** Correction: Sort by priority before grouping. ***
    sorted_by_priority = sorted(sorted_transfers, key=lambda x: x.get('priority', 0)) # Use .get to provide a default value just in case.
    by_point_logger.debug("sorted_transfers (by priority):{}".format(sorted_by_priority))

    # It can now be safely grouped by priority.

    ss2h=[list(group) for _, group in groupby(sorted_by_priority, key=lambda x: x.get('priority', 0))]

    # Sort groups in descending order by priority (higher values first).

    ss2h.reverse()
    by_point_logger.debug("ss2h (grouped and reversed):{}".format(ss2h))
    return ss2h

def gen_s0_action(ss):
    by_point_logger.info("ss:{}".format(ss))
    s0 = []
    uuid_array = []
    uuid_priority_map = {} # New: Used to store mapping of UUID and priority.
    for transfer in ss:
        uuid = transfer['uuid']
        priority = transfer['priority'] # Get priority
        uuid_array.append(uuid)
        uuid_priority_map[uuid] = priority 

        source_port = transfer['source']
        dest_port = transfer['dest']
        carrierID=transfer['carrierID']
        point=find_point(source_port)
        order=query_order_by_point(point)
        if transfer.get('transferType') == 'SHIFT':
            action={
                'type': 'SHIFT',
                'target': source_port,
                'target2': dest_port,
                'point': point,
                'order': order,
                'carrierid': carrierID,
                'loc': '',
                'local_tr_cmd': transfer,
            }
            s0.append(action)
        else:
            action={
                'type': 'ACQUIRE',
                'target': source_port,
                'point': point,
                'order': order,
                'carrierid': carrierID,
                'loc': transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',
                'local_tr_cmd': transfer,
            }
            s0.append(action)
            point=tools.find_point(dest_port)
            order=query_order_by_point(point)
            action={
                'type': 'DEPOSIT',
                'target': dest_port,
                'point': point,
                'order': order,
                'carrierid': carrierID,
                'loc': transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',
                'local_tr_cmd': transfer,
            }
            s0.append(action)
    uuid_order = {uuid: index for index, uuid in enumerate(uuid_array)}
    by_point_logger.debug("s0:{}".format(s0))
    by_point_logger.warning("uuid_order:{}".format(uuid_order))
    by_point_logger.warning("uuid_priority_map:{}".format(uuid_priority_map)) # Log a priority map
    return s0, uuid_order, uuid_priority_map # back uuid_priority_map

def resort_s0_with_sx(s0, sx):
    """
   Rearrange the atomic action list s0 according to the execution order calculated from gen_sx (sx['ASSIGNLIST']).

    Args:
        s0 (list): A list of primitive atomic actions generated by gen_s0_action.
        sx (dict): A state dictionary generated by gen_sx, where sx['ASSIGNLIST'] contains the scheduled task UUID order.

    Returns:
        tuple:
            - list: Reordered list of atomic actions (s0_sorted) based on sx['ASSIGNLIST'].
            - Final location of the transport vehicle at the end of the schedule (init_point).
    """
    init_point=sx['POINT'][-1]
    s0_sorted=[]
    for uuid in sx['ASSIGNLIST']:
        
        for cmd in s0:
            if cmd["local_tr_cmd"]['uuid'] == uuid:
                s0_sorted.append(cmd)
                s0.remove(cmd)
                break
    return s0_sorted,init_point

def check_by_dist(sx, uuid_order, uuid_priority_map):
    """
    Find the nearest location containing the highest priority executable task and perform all actions at that location.
    """
    last_point = sx["POINT"][-1]
    distances = global_variables.dist.get(last_point, {})

    # 1.Identify all executable tasks and their highest priority.

    max_priority = -1
    pending_tasks_exist = False
    all_pending_tasks_info = [] # (priority, point, uuid)

    for point, uuids in sx.get("ACQUIRE", {}).items():
        for uuid in uuids:
            priority = uuid_priority_map.get(uuid, -1)
            all_pending_tasks_info.append((priority, point, uuid))
            max_priority = max(max_priority, priority)
            pending_tasks_exist = True
    for point, uuids in sx.get("SHIFT", {}).items():
         for uuid in uuids:
            priority = uuid_priority_map.get(uuid, -1)
            all_pending_tasks_info.append((priority, point, uuid))
            max_priority = max(max_priority, priority)
            pending_tasks_exist = True
    for point, uuids in sx.get("DEPOSIT", {}).items():
        runnable_deposit_uuids = sx.get("INCAR", set()).intersection(uuids)
        for uuid in runnable_deposit_uuids:
            priority = uuid_priority_map.get(uuid, -1)
            all_pending_tasks_info.append((priority, point, uuid))
            max_priority = max(max_priority, priority)
            pending_tasks_exist = True

    if not pending_tasks_exist:
        by_point_logger.info("No pending tasks left.")
        return sx, False # no tarnsfer

    # 2. Identify the locations of the highest priority tasks and their distances.
    high_priority_points_dist = {}
    for priority, point, uuid in all_pending_tasks_info:
        if priority == max_priority:
             if point in distances: # Check if the checkpoint is reachable.
                 if point not in high_priority_points_dist: # Record distance once
                    high_priority_points_dist[point] = distances[point]
             elif point == last_point: # If it's the current point
                  if point not in high_priority_points_dist:
                    high_priority_points_dist[point] = 0
             else:
                 by_point_logger.warning("Point {} with high priority task {} (priority {}) not found in distances from {}. Skipping.".format(point,uuid,priority,last_point))

    # 3. Select the nearest high-priority point.
    if not high_priority_points_dist:
         # Fallback: If there is no reachable highest priority point, choose the nearest reachable point.
         # Maintain current behavior to avoid deadlock, but high-priority tasks will be delayed.
         by_point_logger.warning("No reachable points found with the current highest priority {} from {}. Falling back to nearest point with *any* task.".format(max_priority,last_point))
         eligible_points = {}
         for point, distance in distances.items():
             can_acquire = point in sx.get("ACQUIRE", {})
             can_shift = point in sx.get("SHIFT", {})
             can_deposit = point in sx.get("DEPOSIT", {}) and sx.get("INCAR", set()).intersection(sx["DEPOSIT"][point])
             if can_acquire or can_shift or can_deposit:
                 eligible_points[point] = distance

         # Check current point as well for eligibility
         point = last_point
         can_acquire = point in sx.get("ACQUIRE", {})
         can_shift = point in sx.get("SHIFT", {})
         can_deposit = point in sx.get("DEPOSIT", {}) and sx.get("INCAR", set()).intersection(sx["DEPOSIT"].get(point, []))
         if (can_acquire or can_shift or can_deposit) and point not in eligible_points:
              eligible_points[point] = 0

         if not eligible_points:
              by_point_logger.error("Fallback failed: No reachable points with any actionable tasks from {}.".format(last_point))
              return sx, False # I'm really stuck.
         sorted_points = sorted(eligible_points.items(), key=lambda item: item[1])
         closest_point, _ = sorted_points[0]
         current_priority_target = "Fallback (Any)"
    else:
         # Select the nearest point of highest priority.
         sorted_high_priority_points = sorted(high_priority_points_dist.items(), key=lambda item: item[1])
         closest_point, _ = sorted_high_priority_points[0]
         current_priority_target = "Highest ({})".format(max_priority)


    # 4. Move to the location (if needed) and perform the action.
    moved = False
    if closest_point != last_point:
        by_point_logger.info("Moving to point: {} (Targeting Priority: {}) from {}, Distance: {}".format(closest_point,current_priority_target,last_point,distances.get(closest_point, 0)))
        sx["POINT"].append(closest_point)
        moved = True
    else:
         by_point_logger.info("Staying at point: {} (Targeting Priority: {}) to execute tasks.".format(closest_point,current_priority_target))

    # 5. Execute actions in order at designated points (ACQUIRE -> SHIFT -> DEPOSIT), prioritizing high priority tasks.
    sx, action_taken_at_point = record_sx_sequential(closest_point, sx, uuid_order, uuid_priority_map)

    # Return sx and a boolean indicating if there was progress (moved or performed an action).
    return sx, moved or action_taken_at_point

def gen_sx(init_point, s0, uuid_order, uuid_priority_map): # recevid uid_priority_map
    """
    Based on the initial position, the list of atomic actions, and the UUID order, simulate the scheduling process and generate the state dictionary sx.
    This version will prioritize tasks with higher priority.
    Args:
        init_point (str): Initial position of the vehicle.
        s0 (list): A list of atomic actions generated by gen_s0_action.
        uuid_order (dict): A dictionary that maps task UUIDs to their order in the original priority group.
        uuid_priority_map (dict): A dictionary that maps task UUIDs to their priorities.

    Returns:
        dict: dict status sx
    """
    sx = {
        "ACQUIRE": {},
        "DEPOSIT": {},
        "SHIFT": {},
        "INCAR": set(),
        "POINT": [init_point],
        "ASSIGNLIST": deque()
    }
    for item in s0:
        by_point_logger.debug("item:{}".format(item))
        t=item["type"]
        p=item["point"]
        u=item["local_tr_cmd"]["uuid"]
        if t in ["ACQUIRE", "DEPOSIT", "SHIFT"]:
            by_point_logger.error("t:{}".format(t))
            by_point_logger.warning("sx[{}]:{}".format(t,sx[t]))
            if p not in sx[t]:#If p is not in sx[t]
                # by_point_logger.debug("1sx[t][p]:{}".format(sx[t][p]))
                sx[t][p]=[]#Add to the list.
                by_point_logger.debug("2sx[t][p]:{}".format(sx[t][p]))
            # by_point_logger.debug("3sx[t][p]:{}".format(sx[t][p]))
            sx[t][p].append(u)
            by_point_logger.debug("4sx[t][p]:{}".format(sx[t][p]))
    # pass_check_swap=False # No longer needed
    by_point_logger.info("sx initial state:{}".format(sx))

    loop_count = 0
    max_loops = len(s0) * 2 + 5 # Increase the loop limit slightly just in case.

    while sx.get("ACQUIRE") or sx.get("DEPOSIT") or sx.get("SHIFT"): # Use .get to avoid key errors.
        loop_count += 1
        if loop_count > max_loops:
             by_point_logger.error("Exceeded max loop count ({}) in gen_sx. Breaking loop. State: {}".format(max_loops,sx))
             break

        by_point_logger.info("--- Loop {} ---".format(loop_count))
        by_point_logger.debug("Current state before check_by_dist: {}".format(sx))

        # Pass uuid_priority_map
        sx, progress_made = check_by_dist(sx, uuid_order, uuid_priority_map)

        by_point_logger.debug("Current state after check_by_dist: {}".format(sx))
        by_point_logger.info("Progress made in loop {}: {}".format(loop_count,progress_made))

        if not progress_made:
            # If check_by_dist hasn't moved or taken action, it means it's stuck.
            by_point_logger.warning("No progress made in this loop. Breaking loop to prevent infinite execution.")
            break
        # Add a delay for easier log observation (optional)
        # time.sleep(0.1)


    by_point_logger.info("sx final state:{}".format(sx))
    return sx

def task_generate(transfers, buf_available, init_point=''):
    # for transfer in transfers:
        # action_logger.debug("transfer:{}".format(transfer))
    sorted_transfers = check_received_time(transfers)
    ss2h = div_action_by_priority(sorted_transfers) # It has already been grouped by priority, but gen_sx will be reconsidered.
    s0_sorted2 = []
    last_point = init_point # Record the last point when the previous priority group ended.

    for ss in ss2h: # Iterate through each priority group.

        if not ss: continue # continie empty
        current_priority = ss[0]['priority'] # Get the current group's priority.
        by_point_logger.warning("--- Processing Priority Group: {} ---".format(current_priority))

        # Generate s0, uuid_order, and uuid_priority_map for the current priority group.
        s0, uuid_order, uuid_priority_map = gen_s0_action(ss)

        # Use the endpoint of the previous group as the starting point of the current group.
        # and pass uuid_priority_map
        sx = gen_sx(last_point, s0, uuid_order, uuid_priority_map)

        # Arrange s0 according to sx.
        s0_sorted, last_point = resort_s0_with_sx(s0, sx) # Update last_point.
        s0_sorted = extra_check_sort(s0_sorted) # Apply special sorting rules.
        # by_point_logger.debug(type(s0_sorted))
        by_point_logger.debug("Sorted actions for priority {}: {}".format(current_priority,s0_sorted))
        s0_sorted2.extend(s0_sorted)

    # Final output log
    by_point_logger.info("--- Final Generated Task Sequence ---")
    for i, action in enumerate(s0_sorted2):
        print("{}. type:{}, target:{}, point:{}, carrierid:{}, priority:{}, uuid:{}".format(
            i+1,
            action.get('type'),
            action.get('target'),
            action.get('point'),
            action.get('carrierid'),
            action.get('local_tr_cmd', {}).get('priority'),
            action.get('local_tr_cmd', {}).get('uuid')
        ))

        # More detailed logging if needed
        # by_point_logger.debug(f"Action Details: {action}")

    # Return the sorted list and the final point (although the example doesn't use the final point).
    return [], s0_sorted2


# if __name__ == "__main__":
    
#     from from_erack_to_erack_3910_shift import transfers
    
#     by_point_logger.info("transfers:{}".format(transfers))
#     buf_available=[]
#     init_point='C002'
    _, scheduled_tasks = task_generate(transfers, buf_available, init_point)
    # print("\nFinal Scheduled Tasks:")
    # for task in scheduled_tasks:
    #     print(task)