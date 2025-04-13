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

def query_order(port_id, order_type):
    try:
        point=tools.find_point(port_id)
        pose=PoseTable.mapping[point]
        return int(pose.get(order_type, 0))
    except:
        traceback.print_exc()
        print('query_order:{} fail'.format(port_id))
        return 0

def task_generate(transfers, buf_available, init_point=''):
    print('**********************************')
    print("TASK_GENERATE BY 'Piority'")
    print('**********************************')
    fail_tr_cmds_id=[]
    d={}
    buf_available_num, buf_available_list=buf_available()
    last_tasks={}
    last_task={}

    #step1
    transfers = transfers[::-1]
    for i, transfer in enumerate(transfers):
        source_port=transfer['source']
        dest_port=transfer['dest']

        res1=True
        seq1=0
        
        if last_task.get('target', '').rstrip('AB') == source_port.rstrip('AB') and last_task.get('type', '') != 'NULL': #for dummyport_ab, and all
            last_task['type']='SWAP'
            last_task['records'].append(transfer)
            if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #for StockOut, ErackOut, for preTransfer
                try:
                    source_point=tools.find_point(source_port) 
                except:
                    source_point=init_point #chocp 2024/8/21 for shift
                seq3=300-transfer['priority']*3+2
                load={
                    'type':'NULL',
                    'target':source_port,
                    'point':source_point, #chocp 2024/8/21 for shift
                    #'point':point,
                    'order':seq3, #order
                    'loc':'',
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    }
                element=d.get(seq3)
                #print('seq1', element)
                if element:
                    d[seq3].append(load)
                else: #none, then new
                    d[seq3]=[load]
            else:   
                point=tools.find_point(dest_port)
                seq3=300-transfer['priority']*3+2
                load={
                    'type':'DEPOSIT',
                    'target':dest_port,
                    'point':point,
                    'order':seq3,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    }
                element=d.get(seq3)
                #print('seq1', element)
                if element:
                    d[seq3].append(load)
                else: #none, then new
                    d[seq3]=[load]
            last_task=load
        else:
            #step 1, source MRxxx, BUF01~04 ......................................................................
            if 'BUF' in transfer['source']: #if source is BUF in vehicle, then skip unload action, chocp:2021/3/27  
                assign_buf_id=re.findall(r'BUF\d+', transfer['source'])[0]
            else:    
                seq1=300-transfer['priority']*3
                #print(transfer['source'], res1, seq1)
                unload={
                    'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                    'carrierID':transfer['carrierID'],
                    'target':transfer['source'],
                    'order':seq1,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    }
                
                element=d.get(seq1)
                #print('seq1', element)
                if element:
                    d[seq1].append(unload)
                else: #none, then new
                    d[seq1]=[unload]
                last_task=unload
            '''if 'BUF' not in transfer['dest']: 
                seq2=query_order(transfer['dest'], 'loadOrder')
                if seq1 >= seq2: #chocp fix
                    seq2+=10000
                load={
                    'type':'DEPOSIT',
                    'carrierID':transfer['carrierID'],
                    'target':transfer['dest'],
                    'order':seq2,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer
                    }
            else:
                seq2=seq1
                load={
                    'type':'NULL',
                    'carrierID':transfer['carrierID'],
                    'target':transfer['source'], # for StouckOut
                    'order':seq2,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer
                    }'''
            if 'BUF' in transfer['dest'] or transfer['dest'] == '*' or transfer['dest'] == '' or transfer['dest'] == 'E0P0': #for StockOut, ErackOut, for preTransfer
                seq2=seq1
                load={
                    'type':'NULL',
                    'carrierID':transfer['carrierID'],
                    'target':transfer['source'], # for StouckOut
                    'order':seq2,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    }
                
            else:
                seq2=300-transfer['priority']*3+1
                '''if seq1 >= seq2: #chocp fix
                    seq2+=10000'''
                load={
                    'type':'DEPOSIT',
                    'carrierID':transfer['carrierID'],
                    'target':transfer['dest'],
                    'order':seq2,
                    'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                    'local_tr_cmd':transfer,
                    'records':[transfer]
                    }
                
            element=d.get(seq2)
            #print('seq2', element)
            if element:
                d[seq2].append(load)
            else: #none, then new
                d[seq2]=[load]
                
            last_task=load

    #step2
    task_order_dict=collections.OrderedDict(sorted(d.items(), key=lambda t: t[0]))

    tasks=[]
    for order, actions in task_order_dict.items():
        # actions=actions[::-1]
        for action in actions:
            if action['type']!='SWAP':
                tasks.append(action)
            else:
                acquire={
                    'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                    'target':action['records'][1]['source'], #for dummyport_ab, and all
                    'loc':action['records'][1].get('buf_loc', '') if action['records'][1].get('buf_loc') else '', #Buf Constrain
                    'local_tr_cmd':action['records'][1] #.....
                    }
                tasks.append(acquire)

                deposit={
                    'type':'DEPOSIT',
                    'target':action['records'][0]['dest'], #for dummyport_ab, and all
                    'loc':action['records'][0].get('buf_loc', '') if action['records'][0].get('buf_loc') else '', #Buf Constrain
                    'local_tr_cmd':action['records'][0]
                    }
                tasks.append(deposit)
    for action in tasks:
        print(action['type'], action['target'])

    return fail_tr_cmds_id, tasks


if __name__ == '__main__':
    
    transfers=[]

    job={'carrierID':'GY001', 'source':'E1P1', 'dest':'S2P1'}
    transfers.append(job)

    job={'carrierID':'GY003', 'source':'S1P1', 'dest':'E2P1'}
    transfers.append(job)

    job={'carrierID':'GY002', 'source':'E1P12', 'dest':'S1P1'}
    transfers.append(job)

    
    tasks=task_generate(transfers)

    print(pformat(tasks))

    
