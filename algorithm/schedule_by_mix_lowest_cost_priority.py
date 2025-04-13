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

import logging
from global_variables import Equipment
from workstation.eq_mgr import EqMgr

def query_order_by_point(point, order_type='loadOrder'):
    try:
        pose=PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except:
        traceback.print_exc()
        print('query_order:{} fail'.format(point))
        return 0

def process_station_actions(station,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action):# kelvinng 20240927 TI Baguio WB
    actions_in_order=[]
    
    #unload -> null -> shift -> load

    if station in eq_has_acquire_action:
        actions_in_order.append(eq_has_acquire_action[station])
        
        if station in eq_has_null_action:
            actions_in_order.append(eq_has_null_action[station])

    if station in eq_has_shift_action:
        actions_in_order.append(eq_has_shift_action[station])
    if station in eq_has_desposit_action:
        actions_in_order.append(eq_has_desposit_action[station])
    
    return actions_in_order
def task_generate(transfers, buf_available, init_point='', model=''):
    print('**********************************')
    print("TASK_GENERATE BY 'mix Lowest and Priority' COST ALGO")
    print('**********************************')


    fail_tr_cmds_id=[]
    actions=[]
    #print('=>schedule transfers:', transfers)
    from_seq_list=[]
    middle_seq_list=[]
    end_seq_list=[]
    eq_has_desposit_action_list=[]# kelvinng 20240927 TI Baguio WB
    eq_has_null_action={}# kelvinng 20240927 TI Baguio WB

    last_middle_seq=[]
    
    eq_already_add_action=[]# kelvinng 20240927 TI Baguio WB
    eq_has_acquire_action={}# kelvinng 20240927 TI Baguio WB
    eq_has_desposit_action={}# kelvinng 20240927 TI Baguio WB
    eq_has_shift_action={}# kelvinng 20240927 TI Baguio WB
    
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
                if h_workstation:
                    eq_has_shift_action[h_workstation.equipmentID]=action

            if 'workstation' in transfer['host_tr_cmd'].get('sourceType', '') :
                from_seq_list.append([action])

            elif 'workstation' in transfer['host_tr_cmd'].get('destType', '') :
                end_seq_list.append([action])

            else:
                middle_seq_list.append([action])
                last_middle_seq=middle_seq_list[-1]

            continue

        last_middle_action={}
        try:
            last_middle_action=last_middle_seq[-1]
        except:
            pass

        if 'BUF' not in source_port: #not from MR buff
            point=tools.find_point(source_port)
            order=query_order_by_point(point)
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
                if h_workstation:
                    eq_has_acquire_action[h_workstation.equipmentID]=action
            if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type: #from Erack for K25
                from_seq_list.append([action])

            elif last_middle_action and (last_middle_action.get('target', '').rstrip('AB') == source_port.rstrip('AB')): #do swap
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
            end_seq_list.append([action])
            if global_variables.RackNaming in [46]:
                h_workstation=EqMgr.getInstance().workstations.get(action['target'])
                if h_workstation:
                    eq_has_null_action[h_workstation.equipmentID]=action
        else:
            point=tools.find_point(dest_port)
            order=query_order_by_point(point)
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
                if h_workstation:
                    eq_has_desposit_action[h_workstation.equipmentID]=action
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
            if h_workstation:
                eq_has_desposit_action_list.append(h_workstation.equipmentID)



    point_order=[]

    #print('from_seq_list:', from_seq_list)
    #elapsed_time, cost, from_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, from_seq_list)
    elapsed_time, cost, from_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, from_seq_list[::-1]) #chocp fix for GB by seq swap
    print('=>from sequences elapsed_time', elapsed_time, cost)
    
    if cost>=0:
        point_order=point_order+from_point_order[1:] #skip init_point
        print('last point', from_point_order[-1].get('point', ''))
        init_point=from_point_order[-1].get('point', '')
    

    middle_merged_list = []
    for seq in middle_seq_list:
        middle_merged_list.extend(seq)
    
    sorted_middle_seq_list = sorted(middle_merged_list, key=lambda s: s['local_tr_cmd']['host_tr_cmd']['priority'], reverse=True)
    
    for s in sorted_middle_seq_list:
        priority = s['local_tr_cmd']['host_tr_cmd']['priority']
        print('new seq:')
        print('s', s['type'], s['point'], priority)
    
    
    point_order=point_order+sorted_middle_seq_list #skip init_point 
    print('last point', sorted_middle_seq_list[-1].get('point', ''))
    init_point=sorted_middle_seq_list[-1].get('point', '')

    
    #elapsed_time, cost, end_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, end_seq_list)
    elapsed_time, cost, end_point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, end_seq_list[::-1]) #chocp fix for GB by seq swap
    
    
    if cost>=0:
        point_order=point_order+end_point_order[1:] #skip init_point
        print('last point', end_point_order[-1].get('point', ''))
   

    for task in point_order: 
        print(task['type'], task['target'])
        if task['type']!='SWAP':
            if global_variables.RackNaming in [46]:            
                h_workstation=EqMgr.getInstance().workstations.get(task['target'])
                if h_workstation:
                    if h_workstation.equipmentID not in eq_already_add_action:
                        actions.extend(process_station_actions(h_workstation.equipmentID,eq_has_acquire_action,eq_has_shift_action,eq_has_desposit_action,eq_has_null_action))
                        eq_already_add_action.append(h_workstation.equipmentID)
                else:
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

    for action_list in actions:
        print("**type:{},target:{}".format(action_list['type'],action_list['target']))
    #need deal carrier in buffer
    return fail_tr_cmds_id, actions



    
