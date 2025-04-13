from collections import deque
import traceback
import global_variables
from global_variables import PoseTable
import tools
from web_service_log import action_logger
import re
from itertools import groupby

def query_order_by_point(point, order_type='loadOrder'):
    try:
        pose=PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except:
        traceback.print_exc()
        print('query_order:{} fail'.format(point))
        return 0
    
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

def find_T_and_point(sorted_points,sx,pass_check_swap):
    T=None
    closest_point=None
    for point, distance in sorted_points:
        if not T:
            if point in sx["ACQUIRE"] and (distance == 0 or (point not in sx["DEPOSIT"]) or pass_check_swap or\
                (point in sx["DEPOSIT"] and all(item in sx["INCAR"] for item in sx["DEPOSIT"][point]))):
                T="ACQUIRE"
            elif point in sx["SHIFT"]:
                T="SHIFT"
            elif point in sx["DEPOSIT"] and ((any(item in sx["INCAR"] for item in sx["DEPOSIT"][point]) and\
                distance == 0) or all(item in sx["INCAR"] for item in sx["DEPOSIT"][point])):
                T="DEPOSIT"
            if T:closest_point=point
    return T,closest_point

def record_sx(T,closest_point,sx,uuid_order):
    if T == "ACQUIRE":
        sorted_acquire=sorted(
            sx[T][closest_point],
            key=lambda x: uuid_order.get(x, float('inf'))
        )
        sx["INCAR"].update(sorted_acquire)
        sx["ASSIGNLIST"].extend(sorted_acquire)
        del sx[T][closest_point]
    elif T == "SHIFT":
        sorted_shift=sorted(
            sx[T][closest_point],
            key=lambda x: uuid_order.get(x, float('inf'))
        )
        sx["ASSIGNLIST"].extend(sorted_shift)
        del sx[T][closest_point]
    elif T == "DEPOSIT":
        assign_uuids=list(sx["INCAR"].intersection(sx["DEPOSIT"][closest_point]))
        sorted_assign=sorted(
            assign_uuids,
            key=lambda x: uuid_order.get(x, float('inf'))
        )
        sx["ASSIGNLIST"].extend(sorted_assign)
        sx["DEPOSIT"][closest_point]=[
            u for u in sx["DEPOSIT"][closest_point] if u not in sorted_assign
        ]
        if not sx["DEPOSIT"][closest_point]:
            del sx["DEPOSIT"][closest_point]
    sx["POINT"].append(closest_point)
    return sx

def check_received_time(transfers):
    received_time_array=[]
    for transfer in transfers:
        received_time_array.append(transfer['host_tr_cmd']['received_time'])
    sorted_transfers=sorted(zip(received_time_array, transfers), key=lambda x: x[0])
    return sorted_transfers

def div_action_by_priority(sorted_transfers):
    sorted_transfers=[transfer for _, transfer in sorted_transfers]
    ss2h=[list(group) for _, group in groupby(sorted_transfers, key=lambda x: x['priority'])]
    ss2h.reverse()
    return ss2h

def gen_s0_action(ss):
    s0=[]
    uuid_array=[]
    for transfer in ss:
        uuid_array.append(transfer['uuid'])
        source_port=transfer['source']
        dest_port=transfer['dest']
        carrierID=transfer['carrierID']
        point=tools.find_point(source_port)
        order=query_order_by_point(point)
        if transfer.get('transferType') == 'SHIFT':
            action={
                'type': 'SHIFT',
                'target': source_port,
                'target2': dest_port,
                'point': point,
                'order': order,
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
    uuid_order={uuid: index for index, uuid in enumerate(uuid_array)}
    return s0,uuid_order

def resort_s0_with_sx(s0,sx):
    init_point=sx['POINT'][-1]
    s0_sorted=[]
    for uuid in sx['ASSIGNLIST']:
        for cmd in s0:
            if cmd["local_tr_cmd"]['uuid'] == uuid:
                s0_sorted.append(cmd)
                s0.remove(cmd)
                break
    return s0_sorted,init_point

def check_by_dist(sx,pass_check_swap,uuid_order):
    last_point=sx["POINT"][-1]
    distances=global_variables.dist.get(last_point, {})
    filtered_distances={
        point: distance for point, distance in distances.items()
        if point in sx["ACQUIRE"] or point in sx["DEPOSIT"] or point in sx["SHIFT"]
    }
    sorted_points=sorted(filtered_distances.items(), key=lambda x: x[1])
    T, closest_point=find_T_and_point(sorted_points, sx, pass_check_swap)
    if pass_check_swap:
        print("pass_check_swap!")
        pass_check_swap=False
    if T and closest_point:
        sx=record_sx(T, closest_point, sx, uuid_order)
        # action_logger.info("sx:{}, T:{}, closest_point:{}".format(sx, T, closest_point))
    else:
        pass_check_swap=True
    return sx,pass_check_swap

def gen_sx(init_point,s0,uuid_order):
    sx={
        "ACQUIRE": {},
        "DEPOSIT": {},
        "SHIFT": {},
        "INCAR": set(),
        "POINT": [init_point],
        "ASSIGNLIST": deque()
    }
    for item in s0:
        t=item["type"]
        p=item["point"]
        u=item["local_tr_cmd"]["uuid"]
        if t in ["ACQUIRE", "DEPOSIT", "SHIFT"]:
            if p not in sx[t]:
                sx[t][p]=[]
            sx[t][p].append(u)
    pass_check_swap=False
    for i in range(len(s0)*2):
        # action_logger.info("gen_sx:{}".format(i))
        if sx["ACQUIRE"] or sx["DEPOSIT"] or sx["SHIFT"]:
            sx,pass_check_swap=check_by_dist(sx,pass_check_swap,uuid_order)
        else:
            break
    return sx

def task_generate(transfers, buf_available, init_point=''):
    # for transfer in transfers:
        # action_logger.debug("transfer:{}".format(transfer))
    sorted_transfers=check_received_time(transfers)
    ss2h=div_action_by_priority(sorted_transfers)
    s0_sorted2=[]
    for ss in ss2h:
        s0,uuid_order=gen_s0_action(ss)
        sx=gen_sx(init_point,s0,uuid_order)
        s0_sorted,init_point=resort_s0_with_sx(s0,sx)
        s0_sorted=extra_check_sort(s0_sorted)
        s0_sorted2.extend(s0_sorted)
    for s0_sorted2_index in s0_sorted2:
        action_logger.debug("type*c:{},target:{},point:{},received_time:{},carrierid:{}".format(s0_sorted2_index.get("type"),s0_sorted2_index.get("target"),s0_sorted2_index.get("point"),s0_sorted2_index.get("local_tr_cmd").get("host_tr_cmd").get("received_time"),s0_sorted2_index.get("carrierid")))
    return [], s0_sorted2