from six.moves import configparser
import six

if six.PY2:
  ConfigParser=configparser.SafeConfigParser
else:
  ConfigParser=configparser.ConfigParser
# from configparser import ConfigParser
import traceback
import os
import signal
import psutil
import threading
import socketio
import time
from collections import defaultdict 
import argparse
import algorithm.auto_group as auto_group

import global_variables
#import graph
#import graph2 as graph
import algorithm.graph2_with_process_Cdata_dijkstra as graph #for ver 8.28~
#import algorithm.graph2_with_process as graph #for ver 8.28~

import global_variables
import alarms


from semi.SecsHostMgr import E88_Host
from semi.SecsHostMgr import E88_STK_Host
from semi.SecsHostMgr import E82_Host

import semi.e88_equipment as E88 #for E88+E82
import semi.e82_equipment as E82

import tools
import json

import copy
from tsc import TSC

from workstation.eq_mgr import EqView
from workstation.eq_mgr import EqMgr

from erack.eRackAdapter_e82 import E82_ErackMgr ##
from erack.erack_mgr import E88_ErackMgr
from bridge.bridgeServer import BridgeServer

# import mgr.iot_mgr
from iot.iot_mgr import IotView
from iot.iot_mgr import IotMgr

from global_variables import SocketIO
from global_variables import Route

from global_variables import Vehicle
from global_variables import Equipment
from global_variables import Erack
from global_variables import Iot

from global_variables import remotecmd_queue
from global_variables import PortsTable
from global_variables import PoseTable
from global_variables import EdgesTable

from global_variables import global_junction_neighbor # Mike: 2021/08/09

from pprint import pformat
from vehicles.vehicle_mgr import VehicleMgr

from global_variables import output

import tr_wq_lib
from  tr_wq_lib import TransferWaitQueue

from collections import OrderedDict #2023/11/5

import logging.handlers as log_handler
import logging

import zmq #chocp 2024/8/9

from web_service_log import *
import namedthreads
namedthreads.patch()

def generate_routes():
    print('\ngenerate_routes:')
    elaspe_time=int(time.time())

    Route.h=graph.Graph()
    nodes=global_variables.tsc_map['nodes']
    #print('nodes', nodes)
    edges=global_variables.tsc_map['edges']
    #print('edges', edges)#speedration
    routemaps=global_variables.tsc_map.get('routemaps',"")
    #time.sleep(10)
    #print('routemaps', routemaps)#speedration

    PortsTable.mapping={} #port map to point
    PoseTable.mapping={} #point map to pose
    EdgesTable.mapping={} #edge map to propotery
    global_variables.global_disable_nodes=[] # Mike: 2021/04/15
    global_variables.global_disable_edges=[] # Mike: 2021/04/15
    junction_group=[] # Mike: 2021/10/01
    global_variables.global_junction_neighbor={} # Mike: 2021/10/21
    global_variables.group_to_node={} # Mike: 2021/12/08
    elevator_collections=[] # Mike: 2023/12/02
    global_variables.dist={} # Mike: 2021/12/08

    for routemap in routemaps:
        print(routemap)
        global_variables.global_map_mapping[routemap['file']]=int(routemap['z-index'])
        global_variables.global_map_mapping[int(routemap['z-index'])]=routemap['file']
        for route in routemap['route']:
            global_variables.global_route_mapping[route]=routemap['file']
    print('>>> global_map_mapping', global_variables.global_map_mapping)
    print('>>> global_route_mapping', global_variables.global_route_mapping)

    for node in nodes:
        #print('****************')
        #print('node', node)
        #print('****************')
        Route.h.add_node(node[0])
        '''#make ports table
        class PortsTable():
            mapping={
            "C1":   ["p1",1, True, 2], #pointID, mask, enable, bayNo
            }
        '''
        PortsTable.mapping[node[0]]=[node[0], 0, True, 0, 0, 0, 1] #also add point as port, map itself
        PortsTable.reverse_mapping[node[0]]=[]
        for port in node[1].get('ports', []):
            # print('haha ', port)
            PortsTable.mapping[port.get('id')]=[node[0], port.get('mask', 0), port.get('enable', True), port.get('bay', 0), port.get('e84', 0), port.get('CS', 0), port.get('portNumber', 1)] #add port map to point
            if port.get('enable', True):
                PortsTable.reverse_mapping[node[0]].append(port.get('id'))
        '''if not PortsTable.reverse_mapping[node[0]]:
            PortsTable.reverse_mapping[node[0]]=[node[0]]'''

        #make points table
        '''
        pose=[node[1].get('x', 0),\
            node[1].get('y', 0),\
            node[1].get('z', 0),\
            node[1].get('w', 0),\
            node[1].get('junction', 0),\
            node[1].get('enable', 1),\
            node[1].get('group', node[0]),\
            node[1].get('go', 0),\
            node[1].get('AltPointID', '')]
        '''
        #print(node)
        pose={  'x': node[1].get('x', 0),\
                'y': node[1].get('y', 0),\
                'z': node[1].get('z', 0),\
                'w': node[1].get('w', 0),\
                'junction': node[1].get('junction', 0),\
                'enable': node[1].get('enable', 1),\
                'group': node[1].get('group', node[0]),\
                'go': node[1].get('go', 0),\
                'AltPointID': node[1].get('AltPointID', ''),\
                'RobotRouteLock': node[1].get('RobotRouteLock', ''),\
                'PreProcess': node[1].get('PreProcess', ''),\
                'PostProcess': node[1].get('PostProcess', ''),\
                'loadOrder': node[1].get('loadOrder', 0),\
                'unloadOrder': node[1].get('unloadOrder', 0),\
                'priority': node[1].get('priority', 0),\
                'type': node[1].get('type', ''),\
                'route': node[1].get('route', 'moveappend_route'),\
                'park':node[1].get('park', 0) #8.25.14-1
                #'priority': node[1].get('priority', 0)
            }

        try:
            pose['PreProcessParam']=json.loads(node[1]['PreProcessParam'])
        except:
            pose['PreProcessParam']={}
        try:
            pose['PostProcessParam']=json.loads(node[1]['PostProcessParam'])
        except:
            pose['PostProcessParam']={}
        #0213 richard
        try:
            pose['DeviceParam'] = json.loads(node[1]['DeviceParam'])
        except:
            pose['DeviceParam'] = {}
        #0213

        if node[1].get('Floor'):
            try:
                pose['floor']=int(node[1].get('Floor'))
            except:
                pass

        if pose['type'] == 'connectionpoint': # Mike: 2023/12/02
            elevator_collections.append(node[0])

        if not pose['group']:
            pose['group']=node[0]

        PoseTable.mapping[node[0]]=pose
        if not pose['enable']:
            global_variables.global_disable_nodes.append(node[0])

    #     for group in pose['group'].split('|'): # Mike: 2021/12/08
    #         if group not in global_variables.global_group_to_node:
    #             global_variables.global_group_to_node[group]=[]
    #         global_variables.global_group_to_node[group].append(node[0])
    #         if pose['junction']: # Mike: 2021/08/09
    #             junction_group.append(group)

    # # print('disable nodes:', global_variables.global_disable_nodes)

    # for node in PoseTable.mapping: # Mike: 2021/10/01
    #     for group in PoseTable.mapping[node]['group'].split('|'):
    #         if group in junction_group:
    #             PoseTable.mapping[node]['junction']=1
    #             global_variables.global_junction_neighbor[node]=[]
    #             break

    # #write file
    # try:
    #     with open('pose_table.txt', 'w') as outFile:
    #         json.dump(PoseTable.mapping, outFile)
    # except Exception as e:
    #     print(e)
    #     pass

    for edge in edges:
        '''if not edge[4]['enable']: #chocp 2021/12/20
            continue'''

        if not edge[4]['enable']: #Mike: 2022/12/06
            points=edge[4]['points']
            global_variables.global_disable_edges.append((points[0]['id'], points[1]['id']))
            global_variables.global_disable_edges.append((points[1]['id'], points[0]['id']))
        #print(edge[4])
        length=edge[3]
        edge_details=edge[4] #Sean 23/3/21

        bidirection=False
        points=edge_details['points']
        group=edge_details['group']
        speed_ratio=edge_details.get('speedratio', 100)
        road=edge_details.get('road', '')
        dynamic_avoid=edge_details.get('dynamicAvoidance', 0)
        ReversedOvertakingAllowed=edge_details.get('reverseOvertakingAllowed', False) #Sean 23/3/21

        if points[0]['dir'] == 'in':
            from_node=points[0]['id']
            to_node=points[1]['id']
            #bidirection=True if points[1]['dir'] == 'in' else False
        else:
            from_node=points[1]['id']
            to_node=points[0]['id']  #chocp:2021/3/8
            #bidirection=False if points[1]['dir'] == 'in' else True
        bidirection=(points[0]['dir'] == points[1]['dir']) #Sean 23/3/21
        '''
        if edge[0] == 'e5':
            print('e5', edge[4])
            print('e5', from_node, to_node, length, bidirection)

        if edge[0] == 'e6':
            print('e6', edge[4])
            print('e6', from_node, to_node, length, bidirection)

        if edge[0] == 'e7':
            print('e7', edge[4])
            print('e7', from_node, to_node, length, bidirection)
        '''
        #PortsTable.mapping[port[0]]=[node[0], port[1], port[2], port[3]]

        #Sean: 23/03/24
        if not bidirection:
            Route.h.add_edge(from_node, to_node, length, bidirection, ReversedOvertakingAllowed)
        else:
            Route.h.add_edge(from_node, to_node, length, bidirection)

        payload={
            'name':edge[0],
            'road':road,
            'speed':speed_ratio,
            'group':group,
            'dynamic_avoid':dynamic_avoid,
        }

        pose0=PoseTable.mapping[points[0]['id']]
        pose1=PoseTable.mapping[points[1]['id']]

        forward_payload={}
        if points[0].get('properties', {}).get('PreProcess'):
            forward_payload['PreProcess']=points[0]['properties']['PreProcess']
            try:
                forward_payload['PreProcessParam']=json.loads(points[0]['properties']['PreProcessParam'])
            except:
                forward_payload['PreProcessParam']={}
        if points[1].get('properties', {}).get('PostProcess'):
            forward_payload['PostProcess']=points[1]['properties']['PostProcess']
            try:
                forward_payload['PostProcessParam']=json.loads(points[1]['properties']['PostProcessParam'])
            except:
                forward_payload['PostProcessParam']={}

        backward_payload={}
        if points[1].get('properties', {}).get('PreProcess'):
            backward_payload['PreProcess']=points[1]['properties']['PreProcess']
            try:
                backward_payload['PreProcessParam']=json.loads(points[1]['properties']['PreProcessParam'])
            except:
                backward_payload['PreProcessParam']={}
        if points[0].get('properties', {}).get('PostProcess'):
            backward_payload['PostProcess']=points[0]['properties']['PostProcess']
            try:
                backward_payload['PostProcessParam']=json.loads(points[0]['properties']['PostProcessParam'])
            except:
                backward_payload['PostProcessParam']={}

        forward_payload.update(payload)
        backward_payload.update(payload)

        # auto set for elevator
        if (pose0['type'], pose1['type']) == ('connectionpoint', 'connectionpoint'):
            forward_payload['PreProcess']='go_floor'
            backward_payload['PreProcess']='go_floor'
        elif pose0['type'] == 'connectionpoint':
            forward_payload['PreProcess']='open_elevator'
            forward_payload['PostProcess']='leave_elevator'
            backward_payload['PreProcess']='go_elevator'
            backward_payload['PostProcess']='close_elevator'
        elif pose1['type'] == 'connectionpoint':
            forward_payload['PreProcess']='go_elevator'
            forward_payload['PostProcess']='close_elevator'
            backward_payload['PreProcess']='open_elevator'
            backward_payload['PostProcess']='leave_elevator'
        else:
            pass
        #print(from_node, to_node, forward_payload, backward_payload)

        # Mike: 2021/03/15
        Route.h.add_edge_info(from_node, to_node, **forward_payload)
        if bidirection:
            Route.h.add_edge_info(to_node, from_node, **backward_payload)

        EdgesTable.mapping[edge[0]]=[group, speed_ratio, from_node, to_node, length, bidirection, road, ReversedOvertakingAllowed]
        
    for node in PoseTable.mapping:
        if global_variables.global_auto_group: #use auto group
            node_coordinate=(PoseTable.mapping[node]['x'], PoseTable.mapping[node]['y'], PoseTable.mapping[node]['w'])
            neighbors=Route.h.get_neighbor(node)
            for neighbor in neighbors:
                if node != neighbor:
                    neighbor_coordinate=(PoseTable.mapping[neighbor]['x'], PoseTable.mapping[neighbor]['y'], PoseTable.mapping[neighbor]['w'])
                    if auto_group.check_group(node_coordinate, neighbor_coordinate):
                        node_group='group_' + node + '_' + neighbor
                        PoseTable.mapping[node]['group']=PoseTable.mapping[node]['group'] + '|' + node_group
                        PoseTable.mapping[neighbor]['group']=PoseTable.mapping[neighbor]['group'] + '|' + node_group
                        for next in Route.h.get_neighbor(neighbor):
                            if next not in neighbors:
                                neighbors.append(next)

        for group in PoseTable.mapping[node]['group'].split('|'): # Mike: 2021/12/08
            if group not in global_variables.global_group_to_node:
                global_variables.global_group_to_node[group]=[]
            global_variables.global_group_to_node[group].append(node)
            if PoseTable.mapping[node]['junction']: # Mike: 2021/08/09
                junction_group.append(group)

    for node in PoseTable.mapping: # Mike: 2021/10/01
        for group in PoseTable.mapping[node]['group'].split('|'):
            if group in junction_group:
                PoseTable.mapping[node]['junction']=1
                global_variables.global_junction_neighbor[node]=[]
                break
    #write file
    try:
        with open('pose_table.txt', 'w') as outFile:
            json.dump(PoseTable.mapping, outFile)
    except Exception as e:
        print(e)
        pass

    '''for vertex in global_junction_neighbor: # Mike: 2021/08/13
        t=Route.h.get_neighbor(vertex)
        collect=[]
        while t:
            tmp=t
            for ele in t:
                if PoseTable.mapping[vertex]['group'] == PoseTable.mapping[ele]['group']:
                    ara=Route.h.get_neighbor(ele)
                    for a in ara:
                        if a not in tmp+collect:
                            tmp.append(a)
                if ele not in collect:
                    collect.append(tmp.pop(tmp.index(ele)))
            t=tmp
            time.sleep(1)
        global_junction_neighbor[vertex]=collect'''

    n=list(global_variables.global_junction_neighbor) # Mike: 2021/10/01
    while n:
        n_list=[n.pop()]
        t=Route.h.get_neighbor(n_list[0])
        collect=[]
        while t:
            tmp=[]
            for ele in t:
                if ele not in global_variables.global_junction_neighbor:
                    collect.append(ele)
                else:
                    ara=Route.h.get_neighbor(ele)
                    for a in ara:
                        if a not in tmp+collect+n_list:
                            tmp.append(a)
                    n_list.append(ele)
                    if ele in n:
                        n.remove(ele)
            t=tmp
        for ele in n_list:
            global_variables.global_junction_neighbor[ele]=collect

    for node in PoseTable.mapping: # Mike: 2021/10/21
        if PoseTable.mapping[node]['junction'] != 1:
            n=Route.h.get_neighbor(node)
            for neighbor in n:
                if neighbor in global_variables.global_junction_neighbor:
                    if node not in global_variables.global_junction_neighbor[neighbor]:
                        global_variables.global_junction_neighbor[neighbor].append(node)
                        break

    if nodes:
        global_variables.dist, trace=Route.h.dijkstra_map_generator()

    def score_func(start_vertex, end_vertex):
        """ return the h score with start_vertex and end_vertex """
        return global_variables.dist[start_vertex][end_vertex]
    global_variables.score_func=score_func

    #write file
    try:
        with open('dijkstra_map.txt', 'w') as outFile:
            json.dump(global_variables.dist, outFile)
    except Exception as e:
        print(e)
        pass

    for point in elevator_collections:
        for p in Route.h.get_neighbor(point):
            if PoseTable.mapping[p]['type'] != 'connectionpoint':
                global_variables.global_elevator_entrance.append(p)
    # print('elevator_entrance', global_variables.global_elevator_entrance)

    elaspe_time=int(time.time())-elaspe_time
    print('\nroute generated successfully', elaspe_time)
    output('MapUpdateCompleted', {'ElapseTime':elaspe_time}, True)
    #add event ...



def mount_socketio_func(sio):
    @sio.on('RouteEnable', namespace='/{}'.format(global_variables.controller_id))
    def route_enable(data):
        #print('->get_route_enable: ', data)
        for node in data['nodes']:
            if not node[1]['enable']:
                if node[0] not in global_variables.global_disable_nodes:
                    global_variables.global_disable_nodes.append(node[0])
            else:
                if node[0] in global_variables.global_disable_nodes:
                    global_variables.global_disable_nodes.pop(global_variables.global_disable_nodes.index(node[0]))

        for edge in data['edges']:
            points=edge[4]['points']
            if not edge[4]['enable']: #Mike: 2022/12/06
                if (points[0]['id'], points[1]['id']) not in global_variables.global_disable_edges:
                    global_variables.global_disable_edges.append((points[0]['id'], points[1]['id']))
                if (points[1]['id'], points[0]['id']) not in global_variables.global_disable_edges:
                    global_variables.global_disable_edges.append((points[1]['id'], points[0]['id']))
            else:
                if (points[0]['id'], points[1]['id']) in global_variables.global_disable_edges:
                    global_variables.global_disable_edges.pop(global_variables.global_disable_edges.index((points[0]['id'], points[1]['id'])))
                if (points[1]['id'], points[0]['id']) in global_variables.global_disable_edges:
                    global_variables.global_disable_edges.pop(global_variables.global_disable_edges.index((points[1]['id'], points[0]['id'])))
        sio.emit('RouteEnable', data, namespace='/{}'.format(global_variables.controller_id))


    @sio.on('config', namespace='/{}'.format(global_variables.controller_id)) #multi thread
    def config(data):
        global front_end_config_complete
        #print(type(data))
        #key, value=data.items()
        if data.get('MapSettings'):
            # print("[][][]"*5,(data))
            global_variables.tsc_map=copy.deepcopy(data['MapSettings'])
            print('\nMapSettings:')
            #print(global_variables.tsc_map)

            #write file
            try:
                with open('param/MapSettings.txt', 'w') as outFile:
                    json.dump(global_variables.tsc_map, outFile, indent=4, sort_keys=True)
            except Exception as e:
                print(e)
                pass

            while True: # Mike: 2021/08/14
                if global_variables.global_occupied_lock.acquire(False):
                    try:
                        global_variables.global_generate_routes=True
                        generate_routes()
                        global_variables.global_generate_routes=False
                        global_variables.global_occupied_lock.release()
                        break
                    except:
                        #traceback.print_exc()
                        logger.error('{} {} {}'.format('generate_routes error: ',sio.sid, traceback.format_exc()))
                        global_variables.global_generate_routes=False
                        global_variables.global_occupied_lock.release()
                        break
                time.sleep(0.5)

            print('>map_config_complete')
            print('>all_front_end_config_complete')
            front_end_config_complete=True #chocp fix 2022/3/18


        elif 'VehicleSettings' in data: # Mike: 2022/04/12
            global_variables.VehicleSettings=data['VehicleSettings']
            print('\nVehicleSettings:')
            # print(json.dumps(global_variables.VehicleSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/VehicleSettings.txt', 'w') as outFile:
                    json.dump(global_variables.VehicleSettings, outFile, indent=4, sort_keys=True, default=str)
            except Exception as e:
                print(e)
                pass

            if Vehicle.h:
                Vehicle.h.api_queue.put({'cmd':'restart', 'config':global_variables.VehicleSettings})
            else:
                logger.error('{} {}'.format('get VehicleSettings but not Vehicle.h',sio.sid))

        elif 'eRackSettings' in data: # Mike: 2022/04/12
            global_variables.eRackSettings=data['eRackSettings']
            print('\neRackSettings:')
            # print(json.dumps(global_variables.eRackSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/eRackSettings.txt', 'w') as outFile:
                    json.dump(global_variables.eRackSettings, outFile, indent=4, sort_keys=True, default=str)
            except Exception as e:
                print(e)
                pass

            if Erack.h:
                Erack.h.api_queue.put({'cmd':'restart', 'config':global_variables.eRackSettings})
            else:
                logger.error('{} {}'.format('get eRackSettings but not Erack.h',sio.sid))

        elif 'EqSettings' in data: # Mike: 2022/04/12
            global_variables.EqSettings=data['EqSettings']
                     
            if Equipment.h:
                Equipment.h.api_queue.put({'cmd':'restart', 'config':global_variables.EqSettings})
            else:
                logger.error('{} {}'.format('get EqSettings but not Equipment.h',sio.sid))

            print('\nEqSettings:')
            #print(json.dumps(global_variables.EqSettings, indent=4, sort_keys=True))

            port_transfer_table=[]
            zone_disable=defaultdict(list)

            for eq_setting in global_variables.EqSettings:
                port_transfer_state=2 if eq_setting['enable'] else 1
                port_transfer_table.append({
                    'PortID': eq_setting['portID'],
                    'PortTransferState': port_transfer_state})
                
                if not eq_setting['enable']:
                    zone_disable[eq_setting['zoneID']].append(eq_setting['portID'])

            changes=[]
            current_port_dict={item['PortID']: item['PortTransferState'] for item in port_transfer_table}
            
            if global_variables.global_port_transfer_table_mem:
                previous_port_dict=global_variables.global_port_transfer_table_mem
                for port_id, current_state in current_port_dict.items():
                    if port_id not in previous_port_dict:
                        changes.append({'PortID': port_id, 'ChangeType': 'New', 'PortTransferState': current_state})
                    elif previous_port_dict[port_id] != current_state:
                        changes.append({'PortID': port_id, 'ChangeType': 'Modified', 'PortTransferState': current_state})

                for port_id, previous_state in previous_port_dict.items():
                    if port_id not in current_port_dict:
                        changes.append({'PortID': port_id, 'ChangeType': 'Removed', 'PortTransferState': 1})

            global_variables.global_port_transfer_table_mem=current_port_dict  
            
            try:
                secsgem_e82_h=E82_Host.getInstance()
                port_variable='PortID' if global_variables.RackNaming != 43 else 'TransferPort'
                if changes:
                    for i in changes:
                        if i['PortTransferState'] == 2:
                            E82.report_event(secsgem_e82_h, E82.PortInService, {port_variable:i['PortID']}) 
                        else:
                            E82.report_event(secsgem_e82_h, E82.PortOutOfService, {port_variable:i['PortID']})        
                    
                E82.update_variables(secsgem_e82_h, {'CurrentPortStates': port_transfer_table})
            except:
                pass
            
            for zone_id, port_ids in zone_disable.items():
                h_zone=TransferWaitQueue.getInstance(zone_id)
                remove_commands=[
                            cmd['uuid'] 
                            for cmd in h_zone.queue 
                            if cmd['source'] in port_ids or cmd['dest'] in port_ids]

                for command_uuid in remove_commands:
                    global_variables.tsc.transfer_cancel(command_uuid, cause='by equipment disabled')
            try:
                with open('param/EqSettings.txt', 'w') as outFile:
                    json.dump(global_variables.EqSettings, outFile, indent=4, sort_keys=True, default=str)
            except Exception as e:
                print(e)
                pass

        elif 'WSSettings' in data: # Jwo: 2023/02/24
            global_variables.WSSettings=data['WSSettings']

            print('\nWSSettings:')
            # print(json.dumps(global_variables.WSSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/WSSettings.txt', 'w') as outFile:
                    json.dump(global_variables.WSSettings, outFile, indent=4, sort_keys=True)
            except Exception as e:
                print(e)
                pass

        elif 'IOTSettings' in data: # Mike: 2022/04/12
            global_variables.IotSettings=data['IOTSettings']
            if Iot.h:
                Iot.h.api_queue.put({'cmd':'restart', 'config':global_variables.IotSettings})
            else:
                logger.error('{} {}'.format('get IOTSettings but not Iot.h',sio.sid))

            print('\nIOTSettings:')
            # print(json.dumps(global_variables.IotSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/IOTSettings.txt', 'w') as outFile:
                    json.dump(global_variables.IotSettings, outFile, indent=4, sort_keys=True, default=str)
            except Exception as e:
                print(e)
                pass

        elif data.get('TSCSettings'):
            #front_end_config_complete=True
            global_variables.TSCSettings=data['TSCSettings']

            print('\nTSCSettings:')
            # print(json.dumps(global_variables.TSCSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/TSCSettings.txt', 'w') as outFile:
                    json.dump(global_variables.TSCSettings, outFile, indent=4, sort_keys=True)
            except Exception as e:
                print(e)
                pass

            global_variables.PSProtocol=global_variables.TSCSettings.get('Communication', {}).get('PSProtocol', 1)
            global_variables.HostProtocol=global_variables.TSCSettings.get('Communication', {}).get('HostProtocol', 1)
            global_variables.RackNaming=global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 1)
            carrierTypeList=global_variables.TSCSettings.get('CassetteTypeSensitive', {}).get('CassetteTypePrefix', '')
            if carrierTypeList:
                global_variables.global_cassetteType=carrierTypeList.replace(' ', '').split(',')
            if global_variables.TSCSettings.get('TrafficControl', {}).get('EnableStraightRoadFirst', 'yes').lower() == 'yes':
                global_variables.RouteAlgo='A*WithRoad'
            else:
                global_variables.RouteAlgo='A*'
            try:
                global_variables.Format_RackPort_Parse=global_variables.RackPortFormat[global_variables.RackNaming-1][0]
                global_variables.Format_RackPort_Print=global_variables.RackPortFormat[global_variables.RackNaming-1][1]
                global_variables.Format_Rack_Parse=global_variables.RackPortFormat[global_variables.RackNaming-1][2]
                global_variables.Format_Rack_Print=global_variables.RackPortFormat[global_variables.RackNaming-1][3]
            except:
                logger.error('{} {} {}'.format('RackNaming Format error',sio.sid, traceback.format_exc()))
                pass

            '''print(global_variables.Format_RackPort_Parse,\
                    global_variables.Format_RackPort_Print,\
                    global_variables.Format_Rack_Parse,\
                    global_variables.Format_Rack_Print)'''


        elif data.get('CarriersMask'):
            global_variables.WhiteCarriersMask={}
            try:
                for element in data['CarriersMask']:
                    global_variables.WhiteCarriersMask[element[0]]={'type':element[1], 'size':element[2]}
            except:
                pass

            #write file
            try:
                with open('param/WhiteCarriersMask.txt', 'w') as outFile:
                    json.dump(global_variables.WhiteCarriersMask, outFile, indent=4, sort_keys=True)
            except Exception as e:
                print(e)
                pass

        elif data.get('ZoneSettings'):
            #not used
            '''
            global_variables.map_zones=[]
            for zone_setting in data['ZoneSettings']:
                global_variables.map_zones.append(zone_setting.get('zoneName', 'other'))
            '''
            global_variables.ZoneSettings=data['ZoneSettings']
            global_variables.OtherZoneSetting={} #chocp add 2023/9/26
            print('\nZoneSettings:')
            # print(json.dumps(global_variables.ZoneSettings, indent=4, sort_keys=True))

            #write file
            try:
                with open('param/ZoneSettings.txt', 'w') as outFile:
                    json.dump(global_variables.ZoneSettings, outFile, indent=4, sort_keys=True)
            except Exception as e:
                print(e)
                pass

            for setting in data['ZoneSettings']:
                zoneID=setting.get('zoneName')
                if zoneID:
                    h_zone=TransferWaitQueue.getInstance(zoneID, setting)
                    if zoneID == 'other':
                        global_variables.OtherZoneSetting=setting
                    if setting.get('enable','yes') == 'no': #Hshuo 240805 disable zone will cancel command   
                        cmd_remove=[cmd['uuid'] for cmd in h_zone.queue]
                        for cmdid in cmd_remove:
                            global_variables.tsc.transfer_cancel(cmdid, cause='by zone disabled')
                    if h_zone and setting.get('crossZoneLink',''):
                        global_variables.global_crossZoneLink[zoneID]=setting.get('crossZoneLink')
                        
                        '''example:
                                "zone1":
                                        "crossZoneLink": [
                                        {
                                            "From": "zone3",
                                            "To": "zone1",
                                            "handlingType": "Undefined"
                                        },
                                        {
                                            "From": "zone5",
                                            "To": "zone2",
                                            "handlingType": "Undefined"
                                        }
                                    ],'''

            # print('TransferWaitQueue.getAllInstance:')
            # print(TransferWaitQueue.getAllInstance())


        elif data.get('SectorSettings'): # Mike: 2022/06/14
            global_variables.color_sectors={}
            global_variables.SectorSettings={}
            for setting in data['SectorSettings']:
                if setting.get('sectorName'):
                    global_variables.color_sectors[setting.get('sectorName')]=setting.get('sectorColor')
                    global_variables.SectorSettings[setting.get('sectorName')]=setting
                    water_level_table={}
                    if setting.get('alarmEmptyEnable', False):
                        water_level_table['empty']=alarms.ErackLevelEmptyWarning
                    if setting.get('alarmLowEnable', False):
                        water_level_table['low']=alarms.ErackLevelLowWarning
                    if setting.get('alarmHighEnable', False):
                        water_level_table['high']=alarms.ErackLevelHighWarning
                    if setting.get('alarmFullEnable', False):
                        water_level_table['full']=alarms.ErackLevelFullWarning
                    global_variables.SectorSettings[setting.get('sectorName')]['water_level_table']=water_level_table
                    global_variables.SectorSettings[setting.get('sectorName')]['waterLevelHigh']=int(setting.get('waterLevelHigh', 0))
                    global_variables.SectorSettings[setting.get('sectorName')]['waterLevelLow']=int(setting.get('waterLevelLow', 0))
            print('\nSectorSettings:')
            # print(json.dumps(global_variables.SectorSettings, indent=4, sort_keys=True, default=str))

            #write file
            try:
                with open('param/SectorSettings.txt', 'w') as outFile:
                    json.dump(global_variables.SectorSettings, outFile, indent=4, sort_keys=True, default=str)
            except Exception as e:
                print(e)
                pass

        elif data.get('WorkPlanList') or data.get('TransferQueues'): #bug chocp: 2021/6/6
            print('\nWorkPlanList:')
            residual_orders=data['WorkPlanList']
            for order in residual_orders:
                # print('order:')
                # print(order)
                EqMgr.getInstance().orderMgr.recovery_work_list(order.get('workID', ''),
                                        order.get('carrierID', ''),
                                        order.get('CarrierType', ''),
                                        order.get('lotID', ''),
                                        order.get('location', ''),
                                        order.get('stage', ''),
                                        order.get('machine', ''),
                                        order.get('priority', 0),
                                        order.get('destport', ''),
                                        order.get('replace', 0),
                                        order.get('status', ''),
                                        order.get('cause', ''))

            print('\nTransferQueues:')
            # print(data['TransferQueues'])

            residual_waiting_cmds=data['TransferQueues'].get('Waiting')
            for cmd in residual_waiting_cmds:
                output('TransferWaitQueueRemove', {
                        'CommandID':cmd['CommandID'] }, True)
                #tools.reset_indicate_slot(cmd.get('Source')) #chocp add 2021/10/23
                #tools.reset_book_slot(cmd.get('Dest')) #chocp add 2021/10/23
                #tools.reset_book_slot(cmd.get('Back')) #chocp add 2021/10/23
                LotID=''
                LotNum=''
                if cmd['CarrierID']=='NA':
                    cmd['CarrierID']='' 
                if cmd.get('TransferInfoList'):
                    LotID=cmd['TransferInfoList'][0].get('LotID','')
                    LotNum=cmd['TransferInfoList'][0].get('LotNum','')

                if cmd['Replace']:
                    remotecmd_queue.append({'remote_cmd':'recovery_transfer',\
                        'commandinfo':{'CommandID':cmd['CommandID'], 'Replace':cmd['Replace'], 'Priority':cmd['Priority']},\
                        'transferinfolist':[{'CarrierID':cmd['CarrierID'] , 'SourcePort':cmd['Source'], 'DestPort':cmd['Dest'], 'CarrierType': cmd['CarrierType']}, \
                                            {'CarrierID':'', 'SourcePort':cmd['Dest'], 'DestPort':cmd.get('Back', '*'), 'CarrierType': cmd['CarrierType']}]})
                else:
                    remotecmd_queue.append({'remote_cmd':'recovery_transfer',\
                        'commandinfo':{'CommandID':cmd['CommandID'], 'Replace':cmd['Replace'], 'Priority':cmd['Priority']},\
                        'transferinfolist':[{'CarrierID':cmd['CarrierID'] , 'SourcePort':cmd['Source'], 'DestPort':cmd['Dest'], 'CarrierType': cmd['CarrierType'], 'LotID':LotID, 'LotNum':LotNum}]})



            residual_executing_cmds=data['TransferQueues'].get('Executing')
            for cmd in residual_executing_cmds:
                del_command_id=cmd['CommandID']
                output('TransferExecuteQueueRemove', {'CommandID':del_command_id}, True)
                #tools.reset_indicate_slot(cmd.get('Source')) #chocp 2021/10/25
                #tools.reset_book_slot(cmd['Dest']) #2021/1020
                secsgem_e82_h=E82_Host.getInstance()
                E82.report_event(secsgem_e82_h, E82.TransferCompleted, {
                    'CommandInfo':{'CommandID':del_command_id, 'Replace':cmd.get('Replace', 0), 'Priority':cmd.get('Priority', 0)},
                    'TransferCompleteInfo':[{'TransferInfo':{'CarrierID':cmd.get('CarrierID', '') , 'SourcePort':cmd['Source'], 'DestPort':cmd['Dest']}, 'CarrierLoc':''}],
                    'TransferInfo':{'CarrierID':cmd.get('CarrierID', '') , 'SourcePort':cmd['Source'], 'DestPort':cmd['Dest']},
                    'VehicleID':'',
                    'ResultCode': 10001,
                    'ResultSubCode':'' }) #tsc internal error

                output('TransferCompleted', {
                        'VehicleID':cmd.get('VehicleID', ''),
                        'DestType':'',
                        'CommandID':del_command_id,
                        'TransferCompleteInfo':[{'TransferInfo':{'CarrierID':cmd.get('CarrierID', '') , 'SourcePort':cmd['Source'], 'DestPort':cmd['Dest']}, 'CarrierLoc':''}],
                        'ResultCode': 10001,
                        'Message': 'TSC internal error' }, True)

                if global_variables.TSCSettings.get('Other', {}).get('RTDEnable') == 'yes': #only for RTD mode
                    if '-UNLOAD' not in del_command_id:
                        EqMgr.getInstance().orderMgr.update_work_status(del_command_id, 'FAIL', 'TSC internal error') #chocp change 2021/11/2

        else:
            if data.get('WaterLevel'): #choc 202`1/11/9
                global_variables.WaterLevel=data.get('WaterLevel')
                print('=>WaterLevel', global_variables.WaterLevel)

            # print(data)


    @sio.on('remote_cmd', namespace='/{}'.format(global_variables.controller_id))
    def add_remote_cmd(data):
        print('\n##get front end cmd:\n##{}\n'.format(data))
        remotecmd_queue.append(data)


    @sio.on('ManualOff', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_off(data):
        print('ManualOff', data)
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual of cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            h_vehicle.manual=False
            # Mike: 2021/08/02
            '''h_vehicle.clean_path()
            while h_vehicle.is_moving:
                time.sleep(1)'''
        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('ManualOn', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_on(data):
        print('ManualOn', data)
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual on cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            h_vehicle.manual=True
            # Mike: 2021/08/02
            '''h_vehicle.clean_path()
            while h_vehicle.is_moving:
                time.sleep(1)'''
        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('ManualMove', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_move(data):
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual move cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':MR state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            pose=tools.get_pose(data['dest'])
            h_vehicle.adapter.go(pose['x'], pose['y'], pose['w'], 'G', 0)

        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))



    @sio.on('ManualRoute', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_route(data):
        print(data)
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual route cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            print(data)
            flags_begin=1 if data.get('begin') == 'yes' else 0
            flags_end=1 if data.get('end') == 'yes' else 0

            source=h_vehicle.adapter.last_point
            dest= tools.find_point(data['dest'])


            block_nodes=[]
            for car in global_variables.global_vehicles_location_index: # Mike: 2021/04/06
                if car != h_vehicle.id and global_variables.global_vehicles_location_index[car]: # Mike: 2021/12/08
                    group_list=PoseTable.mapping[global_variables.global_vehicles_location_index[car]]['group'].split("|")
                    for group in group_list:
                        block_nodes += global_variables.global_group_to_node.get(group, [])
            cost, path=Route.h.get_a_route(source, dest, block_nodes=block_nodes+global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func) #8.25.14-2
            print('ManualRoute:', cost, source, dest)
            print('path:', path)
            if cost < 0:
                cost, path=Route.h.get_a_route(source, dest, block_nodes=global_variables.global_disable_nodes, block_edges=global_variables.global_disable_edges, algo=global_variables.RouteAlgo, score_func=global_variables.score_func)
                #print(cost, path)
            if cost >= 0:
                h_vehicle.adapter.move_control(path, flags_begin, flags_end)
            elif cost < -1:
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} route no response'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))
            else:
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} no route to dest'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))
        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('ManualRobot', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_robot(data):
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual robot cmd'}, namespace='/{}'.format(global_variables.controller_id))
        #robot_control(self, from_port, to_port):
        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            from_port=data['from']
            to_port=data['to']

            from_port_info=PortsTable.mapping.get(from_port, [])
            to_port_info=PortsTable.mapping.get(to_port, [])

            if global_variables.TSCSettings.get('Other',{}).get('DisablePort2AddrTable', 'no') == 'yes' and \
                h_vehicle.adapter.version_check(h_vehicle.adapter.mr_spec_ver, '2.5'):
                if from_port_info:
                    from_port=from_port_info[0]
                if to_port_info:
                    to_port= to_port_info[0]

            if 'BUFFER' in from_port and 'BUFFER' not in to_port:
                h_vehicle.adapter.deposite_control(to_port, from_port, '', 
                                                    e84=to_port_info[4], 
                                                    cs=to_port_info[5],
                                                    pn=to_port_info[6],
                                                    ct=data['CarrierType'],
                                                    no_check=True)
            elif 'BUFFER' not in from_port and 'BUFFER' in to_port:
                h_vehicle.adapter.acquire_control(from_port, to_port, '', 
                                                    e84=from_port_info[4], 
                                                    cs=from_port_info[5],
                                                    pn=from_port_info[6],
                                                    ct=data['CarrierType'],
                                                    no_check=True)
            else:
                h_vehicle.adapter.shift_control(from_port, to_port, '', 
                                                    e84=from_port_info[4], 
                                                    cs=from_port_info[5],
                                                    fpn=from_port_info[6],
                                                    tpn=to_port_info[6],
                                                    ct=data['CarrierType'],
                                                    no_check=True)
        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('ManualCharge', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_charge(data):
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual charge relay cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            if data['relayON'] == 'yes':
                h_vehicle.adapter.charge_start()
            else:
                h_vehicle.adapter.charge_end()

        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('BatteryChange', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_battery_exchange(data):
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual battery exchange cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            if not h_vehicle.adapter.exchange_start():
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle failed to start battery exchange'}, namespace='/{}'.format(global_variables.controller_id))

        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    @sio.on('MapChange', namespace='/{}'.format(global_variables.controller_id))
    def add_manual_map_change(data):
        sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':'<-Receive manual map change cmd'}, namespace='/{}'.format(global_variables.controller_id))

        h_vehicle=Vehicle.h.vehicles.get(data['vehicleID'])
        if h_vehicle:
            #need tsc inpause, vehicle in pause
            if h_vehicle.AgvSubState != 'Manual':
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle state not in Manual state'}, namespace='/{}'.format(global_variables.controller_id))
                return

            map_name=data['action']

            if not h_vehicle.adapter.map_change(map_name):
                sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle failed to change map'}, namespace='/{}'.format(global_variables.controller_id))

        else:
            sio.emit('ManualMessage', {'vehicleID':data['vehicleID'], 'message':':Vehicle {} not found'.format(data['vehicleID'])}, namespace='/{}'.format(global_variables.controller_id))

    #for GPM
    @sio.on('CarrierDispatch', namespace='/{}'.format(global_variables.controller_id))
    def get_carrier_booking_cmd(data):

        eRackID=data.get('erackid')
        row=data.get('row', 1)
        col=data.get('col', 0)

        machine=data.get('machine')
        result=data.get('result')

        # 9/19
        for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            if rack_id == eRackID:
                port_no=h_eRack.columns*(row-1)+col
                h_eRack.change_state(h_eRack.carriers[port_no-1], 'user_edit_cmd', {'machine':machine, 'result':result})
                break

        print('->get_carrier_comfirm_cmd: ', eRackID, row, col, data)

    @sio.on('CarrierBooking', namespace='/{}'.format(global_variables.controller_id))
    def get_carrier_booking_cmd(data):

        eRackID=data.get('erackid')
        row=data.get('row', 1)
        col=data.get('col', 0)
        booked=data.get('newBooking')

        # 9/19
        for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            if rack_id == eRackID:
                booked_port_no=h_eRack.columns*(row-1)+col
                h_eRack.set_booked_flag(booked_port_no, booked)
                break

        print('->get_carrier_booking_cmd: ', eRackID, row, col, booked)


    @sio.on('MCSViewCommand', namespace='/{}'.format(global_variables.controller_id))
    def get_mcs_view_cmd(data):
        #print('->get_mcs_view_cmd: ', data)
        if data['remote_cmd'] == 'reset':
            EqMgr.getInstance().trigger(data['portID'], 'alarm_reset')

        elif data['remote_cmd'] == 'enable':
            EqMgr.getInstance().trigger(data['portID'], 'enable')

        elif data['remote_cmd'] == 'disable':
            EqMgr.getInstance().trigger(data['portID'], 'disable')

        elif data['remote_cmd'] == 'port_state_set':
            EqMgr.getInstance().trigger(data['portID'], 'manual_port_state_set', data)



    @sio.on('connect', namespace='/{}'.format(global_variables.controller_id))
    def on_connect():
        SocketIO.connected=True
        logger.info('{} {} '.format('{} socket io connected to UI'.format(global_variables.controller_id),sio.sid))

        output('TSCUpdate', {'TSCState':global_variables.tsc.mTscState, 'ControlState':global_variables.tsc.mControlState, 'CommunicationState':global_variables.tsc.mCommunicationState, 'LastCommunicationState':global_variables.tsc.mLastCommunicationState, 'TSCVersion':global_variables.soft_ver}, True) #easy timeout, and will re-enter

        remotecmd_queue.append({'remote_cmd':'socketio_connected_evt'})


    @sio.on('disconnect', namespace='/{}'.format(global_variables.controller_id))
    def on_disconnect():
        SocketIO.connected=False
        sio.disconnect()
        logger.info('{} {} '.format('{} socket io disconnected to UI'.format(global_variables.controller_id),sio.sid))

def cpu_monitor(interval_A=30, process_check_interval=30):

    last_process_check = 0  

    cpulogger.debug("tsc pid is now {}!".format(os.getpid()))
    while True:
        try:
            cpu_per_core_usage = psutil.cpu_percent(interval=1, percpu=True)
            ram_usage = psutil.virtual_memory().percent
            ram_used = psutil.virtual_memory().used

            cpulogger.debug("CPU usage: {}%, RAM usage: {:.2f}%, RAM used: {:08x}".format(
                    cpu_per_core_usage, ram_usage, ram_used))


            now = time.time()
            if now - last_process_check >= process_check_interval:
                last_process_check = now
                #cpulogger.info("Checking high CPU usage processes...")
                for p in psutil.process_iter():
                    try:
                        #pid=p.pid
                        #p.cpu_percent(interval=0.1)  
                        if p.cpu_percent() >= 90:
                            cpulogger.warning("High CPU usage - PID:{} CPU:{}% Command:{}".format(
                                p.pid, p.cpu_percent(interval=0.1), p.cmdline()))
                            #process = psutil.Process(p)
                            if 'controller.py' in p.cmdline():
                                threads = p.threads()  
                                thread_info=[]
                                for thread in threads:
                                    tid = thread.id
                                    process = psutil.Process(tid)
                                    #print(process.cpu_percent(interval=0.5),process.name)
                                    thread_detail=process.name
                                    user_time = thread.user_time
                                    thread_info.append((tid, user_time, thread_detail))
                                sorted_threads = sorted(thread_info, key=lambda x: x[1], reverse=True)[:5]
                                for idx, (tid, user_time, thread_detail) in enumerate(sorted_threads, 1):
                                    cpulogger.info("Top {}, Thread Detail: {}, User Time: {:.2f}".format(idx, thread_detail, user_time))
                    except Exception as e:
                        cpulogger.warning("Error reading process info: {}".format(str(e)))

        except Exception as e:
            cpulogger.error("Exception found: {}".format(str(e)))

        time.sleep(interval_A)


if __name__ == '__main__':
    logger=logging.getLogger("tsc")
    logger.setLevel(logging.DEBUG)
    # For log file. Mike: 2021/03/29
    fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_tsc.log"), when='midnight', interval=1, backupCount=30)
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s"))
    logger.addHandler(fileHandler)
    # For console. Mike: 2021/03/29
    streamHandler=logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    streamHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s", "%H:%M:%S"))
    logger.addHandler(streamHandler)

    cpulogger=logging.getLogger("cpu")
    cpulogger.setLevel(logging.DEBUG)
    # For log file. Mike: 2021/03/29
    fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_cpu.log"), when='midnight', interval=1, backupCount=30)
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s"))
    cpulogger.addHandler(fileHandler)
    # For console. Mike: 2021/03/29
    streamHandler=logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    streamHandler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s] [%(levelname)s]: %(message)s", "%H:%M:%S"))
    cpulogger.addHandler(streamHandler)

    parser=argparse.ArgumentParser()
    parser.add_argument('-id',  default='tsc', help='controller id')
    parser.add_argument('-url',  default='127.0.0.1', help='fron end remote ip')
    parser.add_argument('-port',  default=3000, help='fron end remote port')

    parser.add_argument('-api', default='v3.0',  help='specify the secs api spec, v2 for e82+ or v3 for e82&e88')

    parser.add_argument('-e82_ip',  default='', help='specify local ip for e82')
    parser.add_argument('-e82_port',  default=0, help='specify local port for e82')
    parser.add_argument('-e82_device_id',  default=0, help='device id for e82')
    parser.add_argument('-e88_ip',  default='', help='specify local ip for e88')
    parser.add_argument('-e88_port',  default=0, help='specify local port for e88')
    parser.add_argument('-e88_device_id',  default=0, help='device id for e88')
    parser.add_argument('-field', default='',  help='specify which field') #for USG3 2023/12/15

    parser.add_argument('-erack',  default='v1', help='use old or new eRackAdapter')
    parser.add_argument('-loadport', default='',  help='specify the secs api spec')
    parser.add_argument('-multi_olps', default='',  help='specify multi hosts from file')

    parser.add_argument('-filter', default='',  help='filter event to UI') #for SJ 2023/12/26
    parser.add_argument('-auto_group', default='',  help='auto group point') #2024/04/12

    parser.add_argument('-add_db_logger', default='N',  help='add Spil DB logger') #2024/08/12

    args=parser.parse_args()

    global_variables.Display.getInstance() #chocp 2024/8/12

    print('\n*********************************')
    logger.info('{} {} '.format('{} '.format(global_variables.controller_id),'controller start processing'))

    print('arguments:')

    global_variables.soft_ver='v0.0'
    try:
        f=open('version.txt','r')
        global_variables.soft_ver=f.readline()
        f.close()
    except:
        pass

    logger.info('TSC version {}'.format(global_variables.soft_ver))
    global_variables.controller_id=args.id
    print('-id', args.id)

    global_variables.url_ip=args.url
    print('-url', args.url)

    global_variables.url_port=args.port
    print('-port', args.port)

    global_variables.api_spec=args.api
    print('-api', args.api)

    global_variables.e82_ip=args.e82_ip
    print('-e82_ip', args.e82_ip)

    global_variables.e82_port=int(args.e82_port)
    print('-e82_port', args.e82_port)
    
    global_variables.e82_device_id=int(args.e82_device_id)
    print('-e82_device_id', args.e82_device_id)

    global_variables.e88_ip=args.e88_ip
    print('-e88_ip', args.e88_ip)

    global_variables.e88_port=int(args.e88_port)
    print('-e88_port', args.e88_port)
    
    global_variables.e88_device_id=int(args.e88_device_id)
    print('-e88_device_id', args.e88_device_id)

    global_variables.erack_version=args.erack
    print('-erack', args.erack)

    global_variables.loadport_version=args.loadport.upper()
    print('-loadport', args.loadport)

    global_variables.field_id=args.field.upper()  #for USG3 2023/12/15
    print('-field', args.field)  #for USG3 2023/12/15

    global_variables.filter=args.filter  #for SJ 2023/12/26
    print('-filter', args.filter)  #for SJ 2023/12/26

    file=args.multi_olps
    print('-multi_olps', file)
    
    auto_group_args=args.auto_group
    print('-auto_group', auto_group_args)

    add_db_logger=args.add_db_logger
    print('-add_db_logger', add_db_logger)


    logger.info('{} {} '.format('{}'.format(global_variables.controller_id),args))

    if not os.path.exists("param"):
        os.mkdir('param')
        os.chmod('param', 0o777)
        # os.mkdir("param", mode=0o777)

    hosts_dict={}
    clients_dict={}
    if file:
        try:
            #multi_hosts.ini
            cfg=ConfigParser()
            cfg.read(file)
            data=cfg.items('api')
            api=dict(data).get('api')
            if api:
                global_variables.api_spec=api

            hosts_dict=OrderedDict(cfg.items('hosts')) #2023/11/5
            print('multi hosts:', hosts_dict)
            clients_dict=OrderedDict(cfg.items('clients')) #2023/11/5
            print('multi clients:', clients_dict)
            loadport_type=dict(cfg.items('loadport')).get('type')
            if loadport_type:
                global_variables.loadport_version=loadport_type.upper()
                print('set loadport version:', global_variables.loadport_version)
        except:
            logger.error('{} {} '.format('multi error', traceback.format_exc()))
            pass
        
    if auto_group_args:
        try:
            auto_group_args=args.auto_group.split(',')
            if len(auto_group_args) == 2:
                global_variables.vehicle_length =int(auto_group_args[0])
                global_variables.vehicle_width =int(auto_group_args[1])
                global_variables.global_auto_group=True    

        except:
            logger.error('{} {}'.format('auto group error', traceback.format_exc()))
    print('*********************************\n')

    print('Init SocketIO......')
    SocketIO.h=socketio.Client()
    #SocketIO.h=socketio.Client(logger=False, engineio_logger=True)
    mount_socketio_func(SocketIO.h)
    print('Init SocketIO Done!')


    h_view=EqView()
    #python2 ./controlller.py -api v3 or v2.7 or ASECL
    if 'v3' in global_variables.api_spec: #E82&E88
        if not global_variables.e82_port:
            global_variables.e82_port=6000 if global_variables.api_spec == 'v3_QUALCOMM' else 5000
        E82_Host(global_variables.e82_ip, global_variables.e82_port, name='Main', mdln=global_variables.api_spec, deciveid=global_variables.e82_device_id)

        if not global_variables.e88_port:
            global_variables.e88_port=6001 if global_variables.api_spec == 'v3_QUALCOMM' else 5001
        E88_Host(global_variables.e88_ip, global_variables.e88_port, name='Main', mdln='STKC_v1.1', deciveid=global_variables.e88_device_id)

        Vehicle.h=VehicleMgr() #then wait setting cmd msg
        Vehicle.h.setDaemon(True)
        Erack.h=E88_ErackMgr(E88_Host.getInstance()) #then wait setting cmd msg
        Erack.h.setDaemon(True)
        if Vehicle.h and Erack.h:
            logger.info('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v3 '))
        else:
            logger.error('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v3 error'))

    elif 'v4' in global_variables.api_spec: #for dumpwaiter
        if not global_variables.e82_port:
            global_variables.e82_port=5100
        E82_Host(global_variables.e82_ip, global_variables.e82_port, name='Main', mdln=global_variables.api_spec, deciveid=global_variables.e82_device_id)

        if not global_variables.e88_port:
            global_variables.e88_port=5003

        E88_STK_Host(global_variables.e88_ip, global_variables.e88_port, name='Main', mdln='STKC_v2.0')
        Vehicle.h=VehicleMgr() #then wait setting cmd msg
        Vehicle.h.setDaemon(True)
        Erack.h=E88_ErackMgr()
        Erack.h.setDaemon(True)
        if Vehicle.h and Erack.h:
            logger.info('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v4 '))
        else:
            logger.error('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v4 error'))

    else: #'v2' for e82+
        if hosts_dict.items():
            for host, port in hosts_dict.items():
                E82_Host('', int(port), name=host, mdln='v2_ASECL', deciveid=global_variables.e82_device_id) #5000   #8.28.3-3
        else:
            if not global_variables.e82_port:
                global_variables.e82_port=5000
            E82_Host(global_variables.e82_ip, global_variables.e82_port, name='Main', mdln=global_variables.api_spec, deciveid=global_variables.e82_device_id) #5000

        for client, host in clients_dict.items():
            E82_Host.mapping(client, host)

        Vehicle.h=VehicleMgr() #then wait setting cmd msg
        Vehicle.h.setDaemon(True)
        Erack.h=E82_ErackMgr() #then wait setting cmd msg
        Erack.h.setDaemon(True)
        if Vehicle.h and Erack.h:
            logger.info('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v2 '))
        else:
            logger.error('{} {} '.format('{}'.format(global_variables.controller_id),'Start Vehicle and Erack by v2 error'))

    Equipment.h=EqMgr() #need create fisrt
    Equipment.h.setDaemon(True)

    Iot.h=IotMgr()
    Iot.h.setDaemon(True)

    front_end_config_complete=False

    SocketIO.connected=False
    #generate_routes()
    time.sleep(2)

    global_variables.tsc=TSC(E82_Host.getInstance(), E88_Host.getInstance(), E88_STK_Host.getInstance())
    global_variables.tsc.setDaemon(True)

    global_variables.bridge_h=None
    
    if global_variables.field_id == 'USG3':  #for USG# 2023/12/15
        global_variables.bridge_h=BridgeServer(4001)
        # print('<<bridge_h>>:', global_variables.bridge_h)
        global_variables.bridge_h.setDaemon(True)
        global_variables.bridge_h.start()

    time.sleep(2)

    obj={}
    obj['remote_cmd']='resume'
    remotecmd_queue.append(obj)

    obj1={}
    obj1['remote_cmd']='sc_resume'
    remotecmd_queue.append(obj1)


    remote_enable=False

    if 'Y' in add_db_logger.upper():
        global_variables.zmq_h=zmq.Context().socket(zmq.PUB) #chocp 2024/8/9
        global_variables.zmq_h.bind("tcp://*:5050") #chocp 2024/8/9

    while global_variables.url_ip:
        try:
            if global_variables.tsc.heart_beat > 0 and time.time() - global_variables.tsc.heart_beat > 60:
                global_variables.tsc.heart_beat=0
                global_variables.tsc.tsclogger.info('{}'.format("<<<  TSC is dead. >>>"))

            if not SocketIO.connected:
                print('connect front-end server before {}:{}'.format(global_variables.url_ip, global_variables.url_port))
                print('<<SocketIO.connected before>>:', SocketIO.connected)
                #SocketIO.h.connect('http://192.168.0.59:3000', namespaces=['/tsc'])
                SocketIO.h.connect('http://{}:{}'.format(global_variables.url_ip, global_variables.url_port), namespaces=['/{}'.format(global_variables.controller_id)]) #need create socketIO connect first, then setting, then create object
                #print('Connect to namespace: /{}'.format(global_variables.controller_id))
                #print('<<SocketIO.connected 1>>:', SocketIO.connected)
                #SocketIO.connected=True
                #print('<<SocketIO.connected 2>>:', SocketIO.connected)
                # This data can be of type str, bytes, dict, list or tuple
                print('connected to front-end server after{}:{}'.format(global_variables.url_ip, global_variables.url_port))
                if not front_end_config_complete:
                    print('http://{}:{}'.format(global_variables.url_ip, global_variables.url_port), "namespaces=['/{}']".format(global_variables.controller_id))
                    print("SocketIO.h.sid: ", SocketIO.h.sid)
                    output('TSCUpdate', {'TSCState':'TSCPowerOn', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING', 'LastCommunicationState':'NOT_COMMUNICATING', 'TSCVersion':global_variables.soft_ver}, True) #easy timeout, and will re-enter
                    #output('TSCUpdate', {'TSCState':'TSCPowerOn', 'RemoteStatus':'Host OffLine', 'TSCVersion':soft_ver}, False)
                    print('front-end connected')
            #time.sleep(5)
            if not remote_enable and front_end_config_complete:
                remote_enable=True
                print('<<remote_enable>>')

                for secsgem_e82_h in E82_Host.getAllInstance():
                    if global_variables.TSCSettings.get('Communication', {}).get('RackNaming', 0) != 3: # for JCAP
                        secsgem_e82_h.disable_event([E82.VehicleTrafficBlocking, E82.VehicleTrafficRelease, E82.VehicleObstacleBlocking, E82.VehicleObstacleRelease, E82.VehicleStateChange])
                    secsgem_e82_h.enable()

                if 'v3' in global_variables.api_spec:
                    output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING', 'LastCommunicationState':'NOT_COMMUNICATING'}) #new for qualcomm
                    #output('STKCUpdate', {'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING'}, True) #new for qualcomm
                    E88_Host.getInstance().enable()

                if 'v4' in global_variables.api_spec:
                    output('STKCUpdate', {'STKCStatus':True, 'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING', 'LastCommunicationState':'NOT_COMMUNICATING'}) #new for qualcomm
                    #output('STKCUpdate', {'STKCState':'SCAutoInitiated', 'ControlState':'OFFLINE', 'CommunicationState':'NOT_COMMUNICATING'}, True) #new for qualcomm
                    E88_STK_Host.getInstance().enable()
                    print('<<E88_STK_Host.enable()>>')

                if Equipment.h:
                    Equipment.h.start() #8.21H-1
                if Erack.h:
                    Erack.h.start() #8.21H-1
                if Vehicle.h:
                    Vehicle.h.start() #8.21H-1
                if Iot.h:
                    Iot.h.start() #8.21N-1
                    
                cpu_thread = threading.Thread(target=cpu_monitor, args=(30, 30), name='tsc_cpu_monitor')
                cpu_thread.setDaemon(True)
                cpu_thread.start()  

                time.sleep(5)
                global_variables.tsc.start() #call secsgem e82  20 times/1 sec, e88 2 times/1sec

            time.sleep(5)

        except KeyboardInterrupt:
            print('***************************')
            print('Get Keyboard Interrupt')

            '''pid=os.getpid()
            print('controller', pid)
            parent=psutil.Process(pid)
            children=parent.children(recursive=True)
            for p in children:
                print('children', p)
                p.send_signal(signal.SIGTERM)
            gone, alive=psutil.wait_procs(children)'''
            print('Exit Tsc Program')
            print('***************************')
            break
        # except ValueError as e:
        #     if 'not in a disconnected state' in str(e):
        #         SocketIO.connected=True
        #     else:
        #         raise
        except:
            traceback.print_exc()
            SocketIO.connected=False
            time.sleep(2)

if global_variables.bridge_h:
    global_variables.bridge_h.disable()

for h in E82_Host.h_list:
    h.disable()

for h in E88_Host.h_list:
   h.disable()

for h in E88_STK_Host.h_list:
    h.disable()

if global_variables.zmq_h:
    global_variables.zmq_h.close()

