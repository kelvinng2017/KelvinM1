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


def query_order_by_point(point, order_type='loadOrder'):
    try:
        pose=PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except:
        traceback.print_exc()
        print('query_order:{} fail'.format(point))
        return 0

def task_generate(transfers, buf_available, init_point='', model=''):
    print('**********************************')
    print("TASK_GENERATE BY 'LOWEST' COST ALGO")
    print('**********************************')

    fail_tr_cmds_id=[]
    actions=[]
    
    #print('=>schedule transfers:', transfers)
    last_tasks=[]
    sequences=[]
    deposit_sequences=[]
    print('=>schedule transfers:', transfers)
    for transfer in transfers[::-1]: #magic and must
        tasks=[]
        last_task={}
        uuid=transfer['uuid']
        source_port=transfer['source']
        dest_port=transfer['dest']
        back_port= transfer['host_tr_cmd'].get('back')
        source_type= transfer['source_type']
        replace= transfer['host_tr_cmd'].get('replace')

        #for shift transfer, not through buf in vehicle, and shift command source_point should equal to dest_point: #chocp 2024/8/21 for shift
        
        if transfer.get('transferType') == 'SHIFT':
            # if source_type == 'other':
            point = tools.find_point(source_port)
            order = query_order_by_point(point)
            tasks.append({
            'type': 'SHIFT',
            'target': source_port,
            'target2': dest_port,
            'point': point,
            'order': order,
            'loc': '',
            'local_tr_cmd': transfer,
            'records': [transfer]
            })
            
            if transfer['host_tr_cmd'].get('destType') not in ['workstation']:
                deposit_sequences.append(tasks)
            else:
                sequences.append(tasks)
            last_tasks = tasks
            continue
            # point=tools.find_point(source_port) #chocp 2024/8/21 for shift
            # order=query_order_by_point(point)
            # tasks.append({
            #     'type':'SHIFT',
            #     'target':source_port,
            #     'target2':dest_port,
            #     'point':point, 
            #     'order':order,
            #     'loc':'',
            #     'local_tr_cmd':transfer,
            #     'records':[transfer]
            #     })
            
            # # sequences.append(tasks)
            # if transfer['host_tr_cmd'].get('destType') not in ['workstation']:
            #     deposit_sequences.append(tasks)
            # else:
            #     sequences.append(tasks)
            # last_tasks=tasks 
            # continue

        if 'BUF' in source_port: #if source is BUF in vehicle, then skip unload action, chocp:2021/3/27  
            buf_id=re.findall(r'BUF\d+', source_port)[0]
            #skip Acquire
            point=tools.find_point(dest_port)
            order=query_order_by_point(point)
            tasks.append({
                'type':'DEPOSIT',
                'target':dest_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #GF Buf Specified
                'local_tr_cmd':transfer,
                'records':[transfer]
                })
            
            # sequences.append(tasks)
            if transfer['host_tr_cmd'].get('destType') not in ['workstation']:
                deposit_sequences.append(tasks)
            else:
                sequences.append(tasks)
            last_tasks=tasks
            continue

        try:
            last_task=last_tasks[-1]
        except:
            pass

        if last_task.get('target', '').rstrip('AB') == source_port.rstrip('AB') and last_task.get('type', '') != 'NULL': #for dummyport_ab, and all
            last_task['type']='SWAP'
            last_task['records'].append(transfer)
            if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #for StockOut, ErackOut, for preTransfer
                try:
                    source_point=tools.find_point(source_port) 
                except:
                    source_point=init_point #chocp 2024/8/21 for shift
                last_tasks.append({
                    'type':'NULL',
                    'target':source_port,
                    'point':source_point, #chocp 2024/8/21 for shift
                    #'point':point,
                    'order':0, #order
                    'loc':'',
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    })
            else:   
                point=tools.find_point(dest_port)
                order=query_order_by_point(point)
                last_tasks.append({
                    'type':'DEPOSIT',
                    'target':dest_port,
                    'point':point,
                    'order':order,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    })            
        else:
            point=tools.find_point(source_port)
            order=query_order_by_point(point)
            tasks.append({
                'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                'target':source_port,
                'point':point,
                'order':order,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer,
                'records':[transfer]
                })

            if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #for StockOut, ErackOut, for preTransfer
                try:
                    source_point=tools.find_point(source_port) #DestPort MRXXXBUF00 #chocp 2024/8/21 for shift
                    #point=tools.find_point(source_port) #DestPort MRXXXBUF00
                except:
                    source_point=init_point #chocp 2024/8/21 for shift
                    #point=init_point

                tasks.append({
                    'type':'NULL',
                    'target':source_port,
                    'point':source_point, #chocp 2024/8/21 for shift
                    #'point':point,
                    'order':0, #order
                    'loc':'',
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    })
            else:
                point=tools.find_point(dest_port)
                order=query_order_by_point(point)
                
                tasks.append({
                    'type':'DEPOSIT',
                    'target':dest_port,
                    'point':point,
                    'order':order,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    })

            if transfer['host_tr_cmd'].get('destType') not in ['workstation']:
                deposit_sequences.append(tasks)
            else:
                sequences.append(tasks)

            last_tasks=tasks
 
    elapsed_time, cost, point_order, extra_cost=schedule.cal({'target':'', 'point':init_point, 'order':1}, sequences[::-1]+deposit_sequences[::-1])

    #print('=>elapsed_time', 'res', elapsed_time, cost)
    for task in point_order[1:]:#skip init_point
        if task['type']!='SWAP': #chocp 2024/8/21 for shift
            print(task['type'], task['target'])
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
                    'local_tr_cmd':task['records'][1] #.....
                    }
                actions.append(acquire)

                deposit={
                    'type':'DEPOSIT',
                    'target':task['records'][0]['dest'], #for dummyport_ab, and all
                    'loc':task['records'][0].get('buf_loc', '') if task['records'][0].get('buf_loc') else '', #Buf Constrain
                    'local_tr_cmd':task['records'][0]
                    }
                actions.append(deposit)
                print(task['type'], task['target'])


    #need deal carrier in buffer
    return fail_tr_cmds_id, actions



    
