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
    fail_tr_cmds_id=[]
    d={}
    buf_available_num, buf_available_list=buf_available()
    #step1
    for i, transfer in enumerate(transfers):
        if i>=buf_available_num: #for protectd
            break

        res1=True
        seq1=0
        #step 1, source MRxxx, BUF01~04 ......................................................................
        if 'BUF' in transfer['source']: #if source is BUF in vehicle, then skip unload action, chocp:2021/3/27  
            assign_buf_id=re.findall(r'BUF\d+', transfer['source'])[0]
        else:    
            seq1=query_order(transfer['source'], 'unloadOrder')
            #print(transfer['source'], res1, seq1)
            unload={
                'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                'carrierID':transfer['carrierID'],
                'target':transfer['source'],
                'order':seq1,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer
                }

            element=d.get(seq1)
            #print('seq1', element)
            if element:
                d[seq1].append(unload)
            else: #none, then new
                d[seq1]=[unload]

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

        #if 'BUF' in dest_port or dest_port == '*' or dest_port == '' or dest_port == 'E0P0': #for StockOut, ErackOut, for preTransfer
        if 'BUF' in transfer['dest'] or transfer['dest'] == '*' or transfer['dest'] == '' or transfer['dest'] == 'E0P0': #for StockOut, ErackOut, for preTransfer
            seq2=seq1
            load={
                'type':'NULL',
                'carrierID':transfer['carrierID'],
                'target':transfer['source'], # for StouckOut
                'order':seq2,
                'loc':transfer.get('buf_loc', '') if transfer.get('buf_loc') else '',  #Buf Constrain
                'local_tr_cmd':transfer
                }
        else:
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



        element=d.get(seq2)
        #print('seq2', element)
        if element:
            d[seq2].append(load)
        else: #none, then new
            d[seq2]=[load]

    #step2
    task_order_dict=collections.OrderedDict(sorted(d.items(), key=lambda t: t[0]))

    tasks=[]
    for order, actions in task_order_dict.items():
        lst2=sorted(actions, key=lambda t: 0 if t['type'] in ['ACQUIRE', 'ACQUIRE_STANDBY'] else 1)
        tasks.extend(lst2)

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

    
