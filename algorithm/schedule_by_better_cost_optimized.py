# -*- coding: utf-8 -*-


import collections
import traceback
import global_variables
from global_variables import PortsTable
from global_variables import PoseTable
import re
import tools
from pprint import pformat
from global_variables import output

# Use the optimized path calculation module
import algorithm.route_count_caches_py27_optimized as schedule

import logging
from global_variables import Equipment
from workstation.eq_mgr import EqMgr
from web_service_log import *

def query_order_by_point(point, order_type='loadOrder'):
    try:
        pose=PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except:
        traceback.print_exc()
        print('query_order:{} fail'.format(point))
        return 0
    
def add_to_list_dict(d, key, value):
    if key not in d:
        d[key] = []
    d[key].append(value)

def process_station_actions(station,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action):
    # Implementation remains the same as the original version
    actions_in_order=[]
    
    if global_variables.RackNaming == 46:
        if station in eq_has_acquire_action:
            actions_in_order.append(eq_has_acquire_action[station])
            if station in eq_has_null_action:
                actions_in_order.append(eq_has_null_action[station])
        if station in eq_has_shift_action:
            actions_in_order.append(eq_has_shift_action[station])
        if station in eq_has_desposit_action:
            actions_in_order.append(eq_has_desposit_action[station])
    elif global_variables.RackNaming == 36:
        if station in eq_has_acquire_action:
            actions_in_order.extend(eq_has_acquire_action[station])
        if station in eq_has_shift_action:
            actions_in_order.extend(eq_has_shift_action[station])
        if station in eq_has_desposit_action:
            actions_in_order.extend(eq_has_desposit_action[station])
    
    return actions_in_order

def preprocess_sequences(sequences):
    """Preprocess sequences by removing empty sequences and duplicates"""
    processed = []
    for seq in sequences:
        if seq:  # Keep only non-empty sequences
            # Add deduplication logic here if needed
            processed.append(seq)
    return processed

def calculate_sequence_priority(sequence, init_point):
    """Calculate sequence priority for sorting"""
    if not sequence:
        return float('inf')
    
    first_item = sequence[0]
    try:
        # Calculate priority based on distance and order
        distance = global_variables.dist.get(init_point, {}).get(first_item.get('point'), float('inf'))
        order_penalty = first_item.get('order', 0) * 0.1  # Order weight
        return distance + order_penalty
    except:
        return float('inf')

def task_generate_optimized(transfers, buf_available, init_point='', model=''):
    """Optimized task generation function"""
    print('**********************************')
    print("TASK_GENERATE BY 'BETTER' COST ALGO (OPTIMIZED)")
    print('**********************************')

    fail_tr_cmds_id=[]
    actions=[]
    
    # Initialize various sequences and dictionaries (same as the original version)
    from_seq_list=[]
    middle_seq_list=[]
    end_seq_list=[]
    eq_has_null_action={}
    last_middle_seq=[]
    eq_already_add_action=[]
    eq_has_acquire_action = {}
    eq_has_desposit_action = {}
    eq_has_shift_action = {}
    has_erack_acquire_acton=False
    tmp_erack_action=[]
    tmp_init_action=[]
    only_shift=True
    IAR_init_point=init_point
    shif_seq_list=[]
    
    # Transfer handling (essentially the same as the original version, but with minor optimizations)
    for transfer in transfers[::-1]:
        wait_link=False
        uuid=transfer['uuid']
        source_port=transfer['source']
        dest_port=transfer['dest']

        # SHIFT transfer processing
        if transfer.get('transferType') == 'SHIFT':
            point=tools.find_point(source_port)
            order=query_order_by_point(point)

            action={
                'type':'SHIFT',
                'target':source_port,
                'target2':dest_port,
                'point':point, 
                'order':order,
                'loc':'',
                'local_tr_cmd':transfer,
                'records':[transfer]
            }
            
            # Handle different Rack Naming
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    eq_has_shift_action[h_workstation.equipmentID]=action

            if global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_shift_action,h_workstation.equipmentID,action)
                    
            # Sort into different sequences.
            if 'workstation' in transfer['host_tr_cmd'].get('sourceType', '') :
                from_seq_list.append([action])
            elif 'workstation' in transfer['host_tr_cmd'].get('destType', '') :
                end_seq_list.append([action])
            else:
                if global_variables.RackNaming != 46:
                    middle_seq_list.append([action])
                    last_middle_seq=middle_seq_list[-1]
                else:
                    shif_seq_list.append([action])
                    last_middle_seq=shif_seq_list[-1]
            continue

        # Handle non-SHIFT transfers (maintaining original logic but simplifying).
        last_middle_action={}
        try:
            last_middle_action=last_middle_seq[-1]
        except:
            pass

        # ACQUIRE 處理
        if 'BUF' not in source_port:
            point=tools.find_point(source_port)
            order=query_order_by_point(point)
            only_shift=False
            
            action={
                'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                'target':source_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',
                'local_tr_cmd':transfer,
                'records':[transfer]
            }

            # 處理工作站
            h_workstation=EqMgr.getInstance().workstations.get(source_port)
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    eq_has_acquire_action[h_workstation.equipmentID]=action
                else:
                    has_erack_acquire_acton=True
                    
            if global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_acquire_action,h_workstation.equipmentID,action)
                    
            # 分類處理
            if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type:
                from_seq_list.append([action])
            elif (last_middle_action and 
                  last_middle_action.get('target', '').rstrip('AB') == source_port.rstrip('AB') and 
                  global_variables.RackNaming != 36):
                action_logger.debug("SWAP")
                last_middle_action['type']='SWAP'
                last_middle_action['records'].append(transfer)
                wait_link=True
            else:
                middle_seq_list.append([action])
                last_middle_seq=middle_seq_list[-1]
                wait_link=True
                
        # NULL 和 DEPOSIT 處理（簡化但保持原邏輯）
        if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0':
            try:
                point=tools.find_point(source_port)
            except:
                point=init_point
            only_shift=False
            
            action={
                'type':'NULL',
                'target':source_port,
                'point':point,
                'order':0,
                'loc':'',
                'local_tr_cmd':transfer,
                'records':[transfer]
            }
            
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation:
                    eq_has_null_action[h_workstation.equipmentID]=action
            elif global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_null_action,h_workstation.equipmentID,action)
            else:
                end_seq_list.append([action])
        else:
            # DEPOSIT 處理
            point=tools.find_point(dest_port)
            order=query_order_by_point(point)
            only_shift=False
            
            action={
                'type':'DEPOSIT',
                'target':dest_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',
                'local_tr_cmd':transfer,
                'records':[transfer]
            }

            h_workstation=EqMgr.getInstance().workstations.get(dest_port)
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    eq_has_desposit_action[h_workstation.equipmentID]=action
            elif global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_desposit_action,h_workstation.equipmentID,action)
                    
            if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type:
                end_seq_list.append([action])
            elif wait_link:
                last_middle_seq.append(action)
            else:
                middle_seq_list.append([action])
                last_middle_seq=middle_seq_list[-1]

    # 優化：預處理和排序序列
    from_seq_list = preprocess_sequences(from_seq_list)
    middle_seq_list = preprocess_sequences(middle_seq_list)
    end_seq_list = preprocess_sequences(end_seq_list)
    shif_seq_list = preprocess_sequences(shif_seq_list)
    
    # 按優先級排序序列以提高效率
    from_seq_list.sort(key=lambda seq: calculate_sequence_priority(seq, init_point))
    middle_seq_list.sort(key=lambda seq: calculate_sequence_priority(seq, init_point))
    end_seq_list.sort(key=lambda seq: calculate_sequence_priority(seq, init_point))
    
    point_order=[]

    # 使用批次處理進行路徑計算（如果序列較多）
    if len(from_seq_list) + len(middle_seq_list) + len(end_seq_list) + len(shif_seq_list) > 50:
        print("使用批次處理模式...")
        
        # 分別處理每個序列，確保 init_point 正確傳遞
        current_init_point = init_point
        
        # 處理 from_seq_list
        if from_seq_list:
            elapsed_time, cost, from_point_order, extra_cost = schedule.cal(
                {'target':'', 'point':current_init_point, 'order':1}, 
                from_seq_list[::-1]
            )
            print('=>from sequences elapsed_time', elapsed_time, cost)
            
            if cost >= 0:
                point_order = point_order + from_point_order[1:]
                current_init_point = from_point_order[-1].get('point', '') if from_point_order else current_init_point
                print('last point', from_point_order[-1].get('point', ''))
        
        # 處理 shif_seq_list
        if shif_seq_list:
            elapsed_time, cost, shift_point_order, extra_cost = schedule.cal(
                {'target':'', 'point':current_init_point, 'order':1}, 
                shif_seq_list[::-1]
            )
            print('=>shift sequences elapsed_time', elapsed_time, cost)
            if cost >= 0:
                point_order = point_order + shift_point_order[1:]
                current_init_point = shift_point_order[-1].get('point', '') if shift_point_order else current_init_point
                print('last point', shift_point_order[-1].get('point', ''))
        
        # 處理 middle_seq_list
        if middle_seq_list:
            elapsed_time, cost, middle_point_order, extra_cost = schedule.cal(
                {'target':'', 'point':current_init_point, 'order':1}, 
                middle_seq_list[::-1]
            )
            print('=>middle sequences elapsed_time', elapsed_time, cost)
            if cost >= 0:
                point_order = point_order + middle_point_order[1:]
                current_init_point = middle_point_order[-1].get('point', '') if middle_point_order else current_init_point
                print('last point', middle_point_order[-1].get('point', ''))
        
        # 處理 end_seq_list
        if end_seq_list:
            action_logger.debug("end_seq_list[::-1]:{}".format(end_seq_list[::-1]))

            elapsed_time, cost, end_point_order, extra_cost = schedule.cal(
                {'target':'', 'point':current_init_point, 'order':1}, 
                end_seq_list[::-1]
            )
            action_logger.debug("end_point_order:{}".format(end_point_order))
            print('=>end sequences elapsed_time', elapsed_time, cost)
            if cost >= 0:
                # 對於 end_seq_list，如果前面已有序列處理，檢查第一個動作是否為重複的起始點
                if point_order and end_point_order and end_point_order[0].get('point') == current_init_point:
                    point_order = point_order + end_point_order[1:]
                else:
                    # 如果是獨立的 end_seq_list 或第一個動作不是重複點，則包含所有動作
                    point_order = point_order + end_point_order
                print('last point', end_point_order[-1].get('point', ''))
    else:
        # 原有的序列處理方式
        elapsed_time, cost, from_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, from_seq_list[::-1])
        print('=>from sequences elapsed_time', elapsed_time, cost)
        
        if cost>=0:
            point_order=point_order+from_point_order[1:]
            print('last point', from_point_order[-1].get('point', ''))
            init_point=from_point_order[-1].get('point', '')

        elapsed_time, cost, shift_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, shif_seq_list[::-1])
        print('=>shift sequences elapsed_time', elapsed_time, cost)
        if cost>=0:
            point_order=point_order+shift_point_order[1:]
            print('last point', shift_point_order[-1].get('point', ''))
            init_point=shift_point_order[-1].get('point', '') if shift_point_order else init_point

        if global_variables.RackNaming == 15:
            elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list[::-1])
        else:
            elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list[::-1])

        print('=>middle sequences elapsed_time', elapsed_time, cost)
        
        if cost>=0:
            point_order=point_order+middle_point_order[1:]
            print('last point', middle_point_order[-1].get('point', ''))
            init_point=middle_point_order[-1].get('point', '')
        action_logger.debug("end_seq_list[::-1]:{}".format(end_seq_list[::-1]))
        elapsed_time, cost, end_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, end_seq_list[::-1])
        print('=>end sequences elapsed_time', elapsed_time, cost)
        
        if cost>=0:
            action_logger.debug("end_point_order:{}".format(end_point_order))
            # 對於 end_seq_list，如果前面已有序列處理，檢查第一個動作是否為重複的起始點
            if point_order and end_point_order and end_point_order[0].get('point') == init_point:
                point_order=point_order+end_point_order[1:]
            else:
                # 如果是獨立的 end_seq_list 或第一個動作不是重複點，則包含所有動作
                point_order=point_order+end_point_order
            print('last point', end_point_order[-1].get('point', ''))

    # 處理動作生成（保持原邏輯不變）
    for task in point_order: 
        if task['type']!='SWAP':
            print(task['type'], task['target'])
            if global_variables.RackNaming in [46]:            
                h_workstation=EqMgr.getInstance().workstations.get(task['target'])
                target_point=tools.find_point(task['target'])
                
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    if target_point != IAR_init_point:
                        if h_workstation.equipmentID not in eq_already_add_action:
                            print("target_point != IAR_init_point")
                            actions.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                            eq_already_add_action.append(h_workstation.equipmentID)
                    else:
                        if h_workstation.equipmentID not in eq_already_add_action:
                            if h_workstation.equipmentID in eq_has_desposit_action.keys():
                                print("target_point == IAR_init_point but has desposit_action")
                                actions.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                                eq_already_add_action.append(h_workstation.equipmentID)
                            else:
                                print("target_point == IAR_init_point ")
                                tmp_init_action.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                                eq_already_add_action.append(h_workstation.equipmentID)
                else:
                    actions.append(task)
            elif global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(task['target'])
                if h_workstation.workstation_type != "ErackPort":
                    if h_workstation.equipmentID not in ["EQ_5078_P019"]:
                        if h_workstation.equipmentID not in eq_already_add_action:
                            actions.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                            eq_already_add_action.append(h_workstation.equipmentID)
                    else:
                        actions.append(task)
                else:
                    actions.append(task)
            else:
                actions.append(task)
        else:
            # SWAP 處理（與原版本相同）
            if model == 'Type_J':
                swap={
                    'type':'SWAP',
                    'target':task['records'][1]['source'],
                    'loc':task['records'][1].get('buf_loc', '') if task['records'][1].get('buf_loc') else '',
                    'local_tr_cmd':task['records'][1]
                }
                print(swap['type'], task['target'])
                actions.append(swap)
            else:
                acquire={
                    'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                    'target':task['records'][1]['source'],
                    'loc':task['records'][1].get('buf_loc', '') if task['records'][1].get('buf_loc') else '',
                    'local_tr_cmd':task['records'][1]
                }
                print(acquire['type'], task['target'])
                actions.append(acquire)

            deposit={
                'type':'DEPOSIT',
                'target':task['records'][0]['dest'],
                'loc':task['records'][0].get('buf_loc', '') if task['records'][0].get('buf_loc') else '',
                'local_tr_cmd':task['records'][0]
            }
            print(deposit['type'], task['target'])
            actions.append(deposit)

    # 後處理動作（與原版本相同）
    if global_variables.RackNaming in [46]:
        for tmp_erack_action_index in tmp_erack_action:
            if tmp_erack_action_index['type']=='ACQUIRE':
                actions.insert(0,tmp_erack_action_index)
            elif tmp_erack_action_index['type']=='DEPOSIT':
                if has_erack_acquire_acton:
                    actions.insert(0,tmp_erack_action_index)
                else:
                    actions.append(tmp_erack_action_index)

        for tmp_init_action_index in tmp_init_action[::-1]:
            actions.insert(0,tmp_init_action_index)

        # EWB 自定義排序
        eq_candidates = []
        for act in actions:
            if act['type'] in ('DEPOSIT','ACQUIRE') and act['target'].startswith('EWB'):
                eq_name = act['target'].split('-', 1)[0]
                if eq_name not in eq_candidates:
                    eq_candidates.append(eq_name)
        grouped = []
        for eq in eq_candidates:
            has_dep = any(act['type']=='DEPOSIT' and act['target'].startswith(eq) for act in actions)
            has_acq = any(act['type']=='ACQUIRE' and act['target'].startswith(eq) for act in actions)
            if has_dep and has_acq:
                for act in actions[:]:
                    if act['type']=='DEPOSIT' and act['target'].startswith(eq):
                        grouped.append(act)
                        actions.remove(act)
                for act in actions[:]:
                    if act['type']=='ACQUIRE' and act['target'].startswith(eq):
                        grouped.append(act)
                        actions.remove(act)
        actions = grouped + actions

    for action_list in actions:
        # action_logger.debug("action_list:{}".format(action_list))
        action_logger.debug("**type:{},target:{},uuid:{},carrierID:{},loc:{}".format(action_list['type'],action_list['target'],action_list['local_tr_cmd']['uuid'],action_list['local_tr_cmd']['carrierID'],action_list["loc"]))
    
    # 按照指定規則對actions進行排序
    def sort_actions_by_target_suffix(actions):
        """
        對actions進行排序，規則如下：
        1. 沒有_I/_O的target保持原本位置不變
        2. 有_I/_O的target按base target分組，每組內部按照以下順序：
           - 所有 ACQUIRE 的 _I
           - 所有 ACQUIRE 的 _O
           - 所有 DEPOSIT 的 _O  
           - 所有 DEPOSIT 的 _I
        """
        import re
        from collections import defaultdict, OrderedDict
        
        # 按base target分組
        base_target_groups = defaultdict(lambda: {
            'acquire_i': [],
            'acquire_o': [],
            'deposit_i': [],
            'deposit_o': []
        })
        no_suffix_actions = []
        
        # 分類所有actions
        for idx, action in enumerate(actions):
            target = action.get('target', '')
            action_type = action.get('type', '')
            
            # 檢查是否有_I或_O模式
            match = re.match(r'^(.+?)_([IO])(\d+).*$', target)
            if match:
                base_target = match.group(1)  # 基本target部分
                suffix_type = match.group(2)  # I 或 O
                
                if action_type == 'ACQUIRE' and suffix_type == 'I':
                    base_target_groups[base_target]['acquire_i'].append((idx, action))
                elif action_type == 'ACQUIRE' and suffix_type == 'O':
                    base_target_groups[base_target]['acquire_o'].append((idx, action))
                elif action_type == 'DEPOSIT' and suffix_type == 'I':
                    base_target_groups[base_target]['deposit_i'].append((idx, action))
                elif action_type == 'DEPOSIT' and suffix_type == 'O':
                    base_target_groups[base_target]['deposit_o'].append((idx, action))
            else:
                # 沒有_I/_O模式的保持原順序
                no_suffix_actions.append((idx, action))
        
        # 按每個base target組內的原始順序排序
        for base_target in base_target_groups:
            base_target_groups[base_target]['acquire_i'].sort(key=lambda x: x[0])
            base_target_groups[base_target]['acquire_o'].sort(key=lambda x: x[0])
            base_target_groups[base_target]['deposit_i'].sort(key=lambda x: x[0])
            base_target_groups[base_target]['deposit_o'].sort(key=lambda x: x[0])
        
        no_suffix_actions.sort(key=lambda x: x[0])
        
        # 按base target的第一次出現順序排序組
        base_target_order = []
        for idx, action in enumerate(actions):
            target = action.get('target', '')
            match = re.match(r'^(.+?)_([IO])(\d+).*$', target)
            if match:
                base_target = match.group(1)
                if base_target not in base_target_order:
                    base_target_order.append(base_target)
        
        # 構建最終結果
        result = []
        suffix_inserted = False
        
        for idx, action in enumerate(actions):
            target = action.get('target', '')
            match = re.match(r'^(.+?)_([IO])(\d+).*$', target)
            is_suffix = match is not None
            
            if is_suffix:
                # 如果是第一次遇到有後綴的項目，插入所有重新排序的有後綴項目
                if not suffix_inserted:
                    # 按base target分組順序添加
                    for base_target in base_target_order:
                        group = base_target_groups[base_target]
                        
                        # 按指定順序添加該組的項目
                        for _, action in group['acquire_i']:
                            result.append(action)
                        for _, action in group['acquire_o']:
                            result.append(action)
                        for _, action in group['deposit_o']:
                            result.append(action)
                        for _, action in group['deposit_i']:
                            result.append(action)
                    
                    suffix_inserted = True
                # 跳過原來的有後綴項目
            else:
                # 保持無後綴項目的原始位置
                result.append(action)
        
        return result
    
    # 應用排序
    actions = sort_actions_by_target_suffix(actions)
    
    print("排序後的actions順序：")
    for i, action in enumerate(actions):
        action_logger.debug("{}. {}-{}".format(i+1, action.get('type', 'UNKNOWN'), action.get('target', 'NO_TARGET')))
        
    return fail_tr_cmds_id, actions

# 保持相容性的包裝函數
def task_generate(transfers, buf_available, init_point='', model=''):
    """為了向後相容性而保留的原函數名稱"""
    return task_generate_optimized(transfers, buf_available, init_point, model) 