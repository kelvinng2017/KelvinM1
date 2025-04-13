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

def task_generate(transfers, buf_available, init_point=''):
    print('**********************************')
    print("TASK_GENERATE BY 'BETTER' COST ALGO")
    print('**********************************')


    fail_tr_cmds_id=[]
    actions=[]
    #print('=>schedule transfers:', transfers)
    from_seq_list=[]
    middle_seq_list=[]
    end_seq_list=[]

    last_middle_seq=[]
    
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
                'type':'ACQUIRE',
                'target':source_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer,
                'records':[transfer]
                }

            h_workstation=EqMgr.getInstance().workstations.get(source_port)
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
            actions.append(task)
        else:
            acquire={
                'type':'ACQUIRE',
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


    #need deal carrier in buffer
    return fail_tr_cmds_id, actions



    
