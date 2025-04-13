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

TOTAL_DISTANCE=10000 #chocp fix 10/11

def query_mile_by_point(point):
    try:
        pose=PoseTable.mapping[point]
        print('pose', pose)
        return int(pose['priority'])
    except:
        traceback.print_exc()
        print('query_mile:{} fail'.format(point))
        return 0


def get_new_mile(first_mile, second_mile):

    for new_mile in [second_mile, TOTAL_DISTANCE-second_mile, TOTAL_DISTANCE+second_mile, 2*TOTAL_DISTANCE-second_mile, 2*TOTAL_DISTANCE+second_mile, 3*TOTAL_DISTANCE-second_mile]: #if only support twpreplace
        if new_mile > first_mile: 
            return new_mile
    else:
        return 10*TOTAL_DISTANCE

def task_generate(transfers, query_empty_buf_id, init_point=''):
    fail_tr_cmds_id=[]
    d={}

    init_mile=query_mile_by_point(init_point)

    print('=>init_mile', init_point, init_mile)

    #step1
    last_dest_port='' #chocp add 2021/11/12
    last_dest_point=''
    last_dest_mile=0
    
    #sequence 1
    print('=>schedule transfers:', transfers)
    for transfer in transfers[::-1]: #magic and must

        print(init_point, init_mile, last_dest_port, last_dest_point, last_dest_mile)

        uuid=transfer['uuid']
        carrierID=transfer['carrierID']
        source_port=transfer['source']
        dest_port=transfer['dest']
        print('=>step1:', uuid, carrierID, source_port, dest_port)

        #step 1, source MRxxx, BUF01~04
        if 'BUF' in transfer['source']: #if source is BUF in vehicle, then skip unload action, chocp:2021/3/27  
            assign_buf_id=re.findall(r'BUF\d+', source_port)[0]
            source_mile=init_mile
        else:    
            res, assign_buf_id=query_empty_buf_id()
            if not res:
                fail_tr_cmds_id.append(uuid)
                print('=>No empty buffer found for CommandID:{}'.format(fail_tr_cmds_id))
                continue

            source_point=tools.find_point(source_port)
            source_mile=query_mile_by_point(source_point)
            print('=>step2:', source_point, source_mile)

            if source_point == last_dest_point or last_dest_port.rstrip('AB') == source_port.rstrip('AB'): #for asecl dummyloadport_AB do replace

                source_mile=last_dest_mile
            else:
                source_mile=get_new_mile(init_mile, source_mile)

            print('=>step3:', source_point, last_dest_point, source_mile)

            unload={
                'type':'ACQUIRE_STANDBY' if transfer.get('host_tr_cmd', {}).get('stage', 0) else 'ACQUIRE',
                'carrierID':carrierID,
                'target':source_port,
                'mile':source_mile,
                'loc':assign_buf_id,
                'local_tr_cmd':transfer
                }

            element=d.get(source_mile)
            if element:
                d[source_mile].append(unload)
            else: #none, then new
                d[source_mile]=[unload]
           
        #step 2
        dest_point=tools.find_point(dest_port)
        dest_mile=query_mile_by_point(dest_point)
        print('=>step4:', dest_point, dest_mile) 

        dest_mile=get_new_mile(source_mile, dest_mile)

        print('=>step5:', source_mile, dest_point, dest_mile) 

        load={
            'type':'DEPOSIT',
            'carrierID':carrierID,
            'target':dest_port,
            'mile':dest_mile,
            'loc':assign_buf_id,
            'local_tr_cmd':transfer
            }

        element=d.get(dest_mile)
        if element:
            d[dest_mile].append(load)
        else: #none, then new
            d[dest_mile]=[load]

        last_dest_port=dest_port
        last_dest_point=dest_point
        last_dest_mile=dest_mile

    #sequence 2
    task_mile_dict=collections.OrderedDict(sorted(d.items(), key=lambda t: t[0]))

    tasks=[]
    for mile, actions in task_mile_dict.items():
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

    
