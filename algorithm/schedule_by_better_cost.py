import collections
import traceback
import global_variables
from global_variables import PortsTable
from global_variables import PoseTable
#from global_variables import tsc_map
import re
import tools
from pprint import pformat
from global_variables import output

#import algorithm.route_count as schedule
import algorithm.route_count_caches as schedule
#import algorithm.route_count_caches_new as schedule

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

def process_station_actions(station,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action):# kelvinng 20240927 TI Baguio WB
    actions_in_order=[]
    
    #unload -> null -> shift -> load

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
def task_generate(transfers, buf_available, init_point='', model=''):
    print('**********************************')
    print("TASK_GENERATE BY 'BETTER' COST ALGO")
    print('**********************************')


    fail_tr_cmds_id=[]
    actions=[]
    #print('=>schedule transfers:', transfers)
    from_seq_list=[]
    middle_seq_list=[]
    end_seq_list=[]
    
    eq_has_null_action={}# kelvinng 20240927 TI Baguio WB

    last_middle_seq=[]

    eq_already_add_action=[]#TIPI WB

    eq_has_acquire_action = {}#TIPI WB
    eq_has_desposit_action = {}#TIPI WB
    eq_has_shift_action = {}#TIPI WB
    has_erack_acquire_acton=False#TIPI WB
    tmp_erack_action=[]#TIPI WB
    tmp_init_action=[]#TIPI WB
    only_shift=True
    IAR_init_point=init_point
    shif_seq_list=[]
    
    for transfer in transfers[::-1]: #magic and must

        wait_link=False #chocp 2022/10/11

        uuid=transfer['uuid']
        source_port=transfer['source']
        dest_port=transfer['dest']

        #for shift transfer, not through buf in vehicle, and shift command source_point should equal to dest_point: #chocp 2024/8/21 for shift
        if transfer.get('transferType') == 'SHIFT':
            point=tools.find_point(source_port) #chocp 2024/8/21 for shift
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
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    eq_has_shift_action[h_workstation.equipmentID]=action

            if global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_shift_action,h_workstation.equipmentID,action)
                    

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

        last_middle_action={}
        try:
            last_middle_action=last_middle_seq[-1]
        except:
            pass

        if 'BUF' not in source_port: #not from MR buff
            point=tools.find_point(source_port)
            order=query_order_by_point(point)
            only_shift=False
            
            action={
                'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                'target':source_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer,
                'records':[transfer]
                }

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
            if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type: #from Erack for K25
                from_seq_list.append([action])

            elif last_middle_action and (last_middle_action.get('target', '').rstrip('AB') == source_port.rstrip('AB')) and global_variables.RackNaming != 36:
                action_logger.debug("SWAP")
                last_middle_action['type']='SWAP'
                last_middle_action['records'].append(transfer)
                wait_link=True
            else:
                middle_seq_list.append([action])
                last_middle_seq=middle_seq_list[-1]
                wait_link=True
                print('Source last_middle_seq:', last_middle_seq) #new...
                
        #if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #for StockOut, ErackOut, for preTransfer
        if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #............................
            try:
                point=tools.find_point(source_port) #DestPort MRXXXBUF00
            except:
                point=init_point
            only_shift=False
            action={
                'type':'NULL',
                'target':source_port,
                'point':point,
                'order':0, #order
                'loc':'',
                'local_tr_cmd':transfer,
                'records':[transfer]
                }
            #from_seq_list.append([action])
            # end_seq_list.append([action])
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation:
                    eq_has_null_action[h_workstation.equipmentID]=action
            if global_variables.RackNaming in [36]:
                action_logger.debug("actio11s")
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_null_action,h_workstation.equipmentID,action)
            else:
                end_seq_list.append([action])

        else:
            point=tools.find_point(dest_port)
            order=query_order_by_point(point)
            only_shift=False
            action={
                'type':'DEPOSIT',
                'target':dest_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer,
                'records':[transfer]
                }

            h_workstation=EqMgr.getInstance().workstations.get(dest_port)
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    eq_has_desposit_action[h_workstation.equipmentID]=action
            if global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation and  h_workstation.workstation_type != "ErackPort":
                    add_to_list_dict(eq_has_desposit_action,h_workstation.equipmentID,action)
            if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type:
                end_seq_list.append([action])
            #elif last_middle_action and (last_middle_action.get('target', '').rstrip('AB') == source_port.rstrip('AB')): #do swap
            #    last_middle_seq.append(action)
            elif wait_link:
                last_middle_seq.append(action)

            else:
                middle_seq_list.append([action])
                last_middle_seq=middle_seq_list[-1]
                print('Dest last_middle_seq:', last_middle_seq)
            


    point_order=[]

    #print('from_seq_list:', from_seq_list)
    #elapsed_time, cost, from_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, from_seq_list)
    elapsed_time, cost, from_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, from_seq_list[::-1]) #chocp fix for GB by seq swap
    print('=>from sequences elapsed_time', elapsed_time, cost)
    
    if cost>=0:
        point_order=point_order+from_point_order[1:] #skip init_point
        print('last point', from_point_order[-1].get('point', ''))
        init_point=from_point_order[-1].get('point', '')

    print('middle_seq_list:')
    for seq in middle_seq_list:
        print('new seq:')
        for s in seq:
            print('s', s['type'], s['point'])

    elapsed_time, cost, shift_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, shif_seq_list[::-1]) #chocp 2024/8/21 for shift
    print('=>shift sequences elapsed_time', elapsed_time, cost)
    if cost>=0:
        point_order=point_order+shift_point_order[1:] #skip init_point
        print('last point', shift_point_order[-1].get('point', ''))

    #elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list)
    if global_variables.RackNaming == 15:
        elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list[::-1]) #chocp fix for GB by seq swap
    else:
        #elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list) #
        elapsed_time, cost, middle_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, middle_seq_list[::-1]) #chocp 2024/8/21 for shift

    print('=>middle sequences elapsed_time', elapsed_time, cost)
    
    if cost>=0:
        point_order=point_order+middle_point_order[1:] #skip init_point 
        print('last point', middle_point_order[-1].get('point', ''))
        init_point=middle_point_order[-1].get('point', '')
    #print('end_seq_list:', end_seq_list)
    
    #elapsed_time, cost, end_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, end_seq_list)
    elapsed_time, cost, end_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, end_seq_list[::-1]) #chocp fix for GB by seq swap
    print('=>end sequences elapsed_time', elapsed_time, cost)
    
    if cost>=0:
        point_order=point_order+end_point_order[1:] #skip init_point
        print('last point', end_point_order[-1].get('point', ''))

    for task in point_order: 
        if task['type']!='SWAP':
            print(task['type'], task['target'])
            if global_variables.RackNaming in [46]:            
                h_workstation=EqMgr.getInstance().workstations.get(task['target'])
                target_point=tools.find_point(task['target'])
                
                if h_workstation and  h_workstation.workstation_type != "ErackPort":#h_workstation.equipmentID 
                    action_logger.debug("hhha")
                    
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
                    if task['type']=='DEPOSIT':
                        desposit_source=task.get("local_tr_cmd").get("source")
                       
                        if "BUF" in desposit_source:
                            if len(actions) >=1:
                                if has_erack_acquire_acton:
                                    # actions.append(task)
                                    actions.insert(0,task)
                                else:
                                    
                                    original_frist_action_target=actions[0].get('target')
                                    original_frist_action_point=tools.find_point(actions[0].get('target'))
                                    new_action_target=task['target']
                                    new_action_point=tools.find_point(task['target'])
                                    
                                    original_frist_action_target_and_mr_distance=tools.calculate_distance(IAR_init_point,tools.find_point(actions[0].get('target')))
                                    new_action_targe_tand_mr_distance=tools.calculate_distance(IAR_init_point,task['target'])
                                    
                                    original_frist_action_h_workstation=EqMgr.getInstance().workstations.get(actions[0].get('target'))
                                    if original_frist_action_h_workstation:#0<=41849
                                        if original_frist_action_h_workstation.workstation_type != "ErackPort":
                                            if original_frist_action_target_and_mr_distance <= new_action_targe_tand_mr_distance:#39738 661
                                                
                                                actions.append(task)
                                            else:
                                                
                                                actions.insert(0,task)
                                        else:
                                            actions.insert(0,task)
                                    else:
                                        actions.insert(0,task)
                            else:
                                actions.insert(0,task)
                                
                        else:
                            actions.append(task)

                            
                    else:
                        actions.append(task)
                    
                    # tmp_erack_action.append(task)

            # action_logger.debug(eq_has_acquire_action)
            # action_logger.debug(eq_has_shift_action)
            # action_logger.debug(eq_has_desposit_action)
            elif global_variables.RackNaming in [36]:
                h_workstation=EqMgr.getInstance().workstations.get(task['target'])

                action_logger.info("task target:{}".format(task['target']))
                action_logger.info("h_workstation.equipmentID:{}".format(h_workstation.equipmentID))
                if h_workstation.workstation_type != "ErackPort":
                    if h_workstation.equipmentID not in ["EQ_5078_P019"]:
                        if h_workstation.equipmentID not in eq_already_add_action:
                            action_logger.info("in extend")
                            
                            
                            actions.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                            eq_already_add_action.append(h_workstation.equipmentID)
                    else:
                        action_logger.info("in append")
                        actions.append(task)
                    
                else:
                    action_logger.info("in append")
                    actions.append(task)
                                    
            else:
                actions.append(task)
        else:
            if model == 'Type_J':
                swap={
                    'type':'SWAP',
                    'target':task['records'][1]['source'], #for dummyport_ab, and all
                    'loc':task['records'][1].get('buf_loc', '') if task['records'][1].get('buf_loc') else '', #Buf Constrain
                    'local_tr_cmd':task['records'][1]
                    }
                print(swap['type'], task['target'])
                actions.append(swap)
            else:
                acquire={
                    'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                    'target':task['records'][1]['source'], #for dummyport_ab, and all
                    'loc':task['records'][1].get('buf_loc', '') if task['records'][1].get('buf_loc') else '', #Buf Constrain
                    'local_tr_cmd':task['records'][1]
                    }
                print(acquire['type'], task['target'])
                actions.append(acquire)

            deposit={
                'type':'DEPOSIT',
                'target':task['records'][0]['dest'], #for dummyport_ab, and all
                'loc':task['records'][0].get('buf_loc', '') if task['records'][0].get('buf_loc') else '', #Buf Constrain
                'local_tr_cmd':task['records'][0]
                }
            print(deposit['type'], task['target'])
            actions.append(deposit)
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

        # Dynamic EWB custom sorting: Process in order of first appearance of EWBxxx.
        eq_candidates = []
        for act in actions:
            if act['type'] in ('DEPOSIT','ACQUIRE') and act['target'].startswith('EWB'):
                eq_name = act['target'].split('-', 1)[0]
                if eq_name not in eq_candidates:
                    eq_candidates.append(eq_name)
        grouped = []
        for eq in eq_candidates:
            # Check if both DEPOSIT and ACQUIRE are present.
            has_dep = any(act['type']=='DEPOSIT' and act['target'].startswith(eq) for act in actions)
            has_acq = any(act['type']=='ACQUIRE' and act['target'].startswith(eq) for act in actions)
            if has_dep and has_acq:
                # First handle the DEPOSIT.
                for act in actions[:]:
                    if act['type']=='DEPOSIT' and act['target'].startswith(eq):
                        grouped.append(act)
                        actions.remove(act)
                # Reprocess ACQUIRE
                for act in actions[:]:
                    if act['type']=='ACQUIRE' and act['target'].startswith(eq):
                        grouped.append(act)
                        actions.remove(act)
        actions = grouped + actions

    for action_list in actions:
        action_logger.debug("**type:{},target:{}".format(action_list['type'],action_list['target']))
        # print("**type:{},target:{}".format(action_list['type'],action_list['target']))
    #need deal carrier in buffer
    return fail_tr_cmds_id, actions



    
