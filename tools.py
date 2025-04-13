import re
import alarms
import datetime
import time

import global_variables
from global_variables import PortsTable
from global_variables import PoseTable

from workstation.eq_mgr import EqMgr

from global_variables import Erack
from global_variables import Equipment

from global_variables import Vehicle #for StockOut
#from vehicle import VehicleMgr
#import route_count #for K25
import algorithm.route_count_caches as schedule #for K25
from tr_wq_lib import TransferWaitQueue
from web_service_log import * 


from global_variables import output

import traceback

def calculate_distance(source, dest):
    try: #chocp 2022/5/4
        distance=global_variables.dist[find_point(source)][find_point(dest)]
    except:
        #traceback.print_exc()
        distance=float('inf')
        pass

    return distance

def find_point(target): #input: simple station or point, output: point

    try:
        #print(PortsTable.mapping)
        point=PortsTable.mapping[target][0]
    except:
        raise alarms.PortNotFoundWarning(target)

    return point

def find_port(point):#Yuri 2024/10/30
    try:
        #print(PortsTable.mapping)
        check=True if PortsTable.reverse_mapping.get(point,"") else False
    except:
        pass
       # raise alarms.PortNotFoundWarning(point)
    return check


def get_pose(point):
    return PoseTable.mapping[point]

def round_a_point(p):

    near=sorted(PoseTable.mapping.items(), key=lambda t: (t[1]['x'] - p[0])**2 + (t[1]['y'] - p[1])**2)
    #near=[ [point, {}], ]
    return near[0][0]

def check_a_point(p, target, max_dist=100): # Mike: 2022/04/15
    return (((PortsTable.mapping[target]['x'] - p[0])**2 + (PortsTable.mapping[target]['y'] - p[1])**2) < max_dist**2) and (PortsTable.mapping[target]['z'] == p[2])

def round_a_point_new(p, check_head=True, max_dist=100, find_nearest=True): # Mike: 2021/03/02 # Mike: 2021/10/06

    near=list(filter((lambda t: t[1]['z'] == p[2]), sorted(PoseTable.mapping.items(), key=lambda t: (t[1]['x'] - p[0])**2 + (t[1]['y'] - p[1])**2))) #chocp 2023/7/21

    ret=['']
    for P in near:
        #P=[point, {}]
        if max_dist > 0:
            if ((PoseTable.mapping[P[0]]['x'] - p[0])**2 + (PoseTable.mapping[P[0]]['y'] - p[1])**2) > max_dist**2:
                break
        if not check_head:
            ret=P
            break
        else: # Mike: 2021/11/12
            if (abs(PoseTable.mapping[P[0]]['w'] - p[3]) < 15):
                ret=P
                break
            elif (abs(PoseTable.mapping[P[0]]['w'] - p[3] - 360) < 15):
                ret=P
                break
            elif (abs(PoseTable.mapping[P[0]]['w'] - p[3] + 360) < 15):
                ret=P
                break
            else:
                pass
    if not ret[0] and find_nearest: # Mike: 2021/11/12
        ret=near[0]

    return ret


def indicate_slot(target, dest, vehicle_id=''):
    res, rack_id, port_no=rackport_format_parse(target)  #fix2
    if res:
        for indicate_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            if rack_id == indicate_rack_id:
                h_eRack.set_machine_info(port_no, dest, vehicle_id)
                break

# def reset_indicate_slot(target):
#     res, rack_id, port_no=rackport_format_parse(target)  #fix2
#     if res:
#         for indicate_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
#             if rack_id == indicate_rack_id:
#                 h_eRack.set_machine_info(port_no, '')
#                 break
            
def reset_indicate_slot(target,carrierID=''):
    res, rack_id, port_no=rackport_format_parse(target)  #fix2
    if res:#kelvinng 20240406
        if carrierID:
            for indicate_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                if rack_id == indicate_rack_id:
                    h_eRack.set_machine_info(port_no, '',carrierID)
                    break
        else:
            for indicate_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
                if rack_id == indicate_rack_id:
                    h_eRack.set_machine_info(port_no, '')
                    break


def book_slot(target, vehicle_id='', source=''):
    res, rack_id, port_no=rackport_format_parse(target)  #fix2
    if res:
        for booked_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            if rack_id == booked_rack_id:
                h_eRack.set_booked_flag(port_no, True, vehicle_id, source)
                break

def reset_book_slot(target):
    res, rack_id, port_no=rackport_format_parse(target)  #fix2
    if res:
        for booked_rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            if rack_id == booked_rack_id:
                h_eRack.set_booked_flag(port_no, False)
                break

#9/21
def re_assign_source_port(carrierID):
        ##chocp:2021/3/27  return ExPx, MRxBUFx
        #for vehicle_id, h_vehicle in VehicleMgr.getInstance().vehicles.items():
        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
            for i in range(h_vehicle.bufNum):
                buf=h_vehicle.adapter.carriers[i]
                if buf['status'] == carrierID:
                    target='%s%s'%(h_vehicle.id, h_vehicle.vehicle_bufID[i])
                    print('re_assign_source_port:', target)
                    return True, target

        # 9/19
        for rack_id, h_eRack in Erack.h.eRacks.items(): #fix2
            for port_no in range(1, h_eRack.slot_num+1, 1):
                carrier=h_eRack.carriers[port_no-1]
                if carrier['carrierID'] == carrierID and carrier['status'] == 'up':
                    res, target=print_rackport_format(rack_id, port_no, h_eRack.rows, h_eRack.columns)
                    if res:
                        if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                            target=target+'O'
                        return True, target

        return False, '*'

def preserved_dest_port_in_racks(combo_dest_racks, carrierType): #select port by most empty columns, 2023/12/26
    final_rack=''
    for dest_racks in combo_dest_racks.split(','):
        for rackID in dest_racks.strip().split('|'): #for xxx|xxx|xxx
            if Erack.h.port_areas.get(rackID):
                return True, rackID
            res, rack_id, port_no=rackport_format_parse(rackID)
            if res:
                return True, rackID #direct return not check, if DestPort is Rack Port
            h_eRack=Erack.h.eRacks.get(rackID)
            if h_eRack: #rack_id
                final_rack=rackID
                if h_eRack.available:
                    eRack_columns=h_eRack.columns
                    eRack_rows=h_eRack.rows
                    for i in range(0, eRack_columns, 1):  #select port by columns
                        for j in range(1, eRack_columns*eRack_rows, eRack_columns):
                            port_no=i + j
                            carrier=h_eRack.carriers[port_no-1]
                            lot=h_eRack.lots[port_no-1]
                            if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                                if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                                    continue
                                res, target=print_rackport_format(rackID, 0, h_eRack.rows, h_eRack.columns)
                                if res:
                                    return True, target
    res=False
    if final_rack:
        res, target=print_rackport_format(final_rack, 0, h_eRack.rows, h_eRack.columns)
    if res:
        return True, target
    else:
        return False, ''

def book_dest_port_in_racks(h_eRacks, average, carrierType): #select port by most empty columns, 2023/12/26
    h_eRacks_sorted=h_eRacks
    eRack_available=[]
    eRack_books=[]
    if average:
        h_eRacks_sorted=sorted(h_eRacks, key=lambda h: h.available, reverse=True)
    if global_variables.RackNaming in  [25, 17]:
        for h_eRack in h_eRacks_sorted:
            if h_eRack.available:
                eRack_columns=h_eRack.columns
                eRack_rows=h_eRack.rows
                for i in range(0, eRack_columns*eRack_rows, 1):
                    carrier=h_eRack.carriers[i]
                    lot=h_eRack.lots[i]
                    if lot['booked']:
                        eRack_books.append(i)
                    if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                        if carrierType and not i in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                            continue
                        eRack_available.append(i) #???
                if not len(eRack_available):#Yuri 20225/2/25
                    continue
                for c in range(len(eRack_available),-1,-1):
                    port_no=eRack_available[c-1] + 1
                    carrier= h_eRack.carriers[eRack_available[c-1]]
                    lot= h_eRack.lots[eRack_available[c-1]]
                    if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                        if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                            continue
                        res, target=print_rackport_format(h_eRack.device_id, port_no, h_eRack.rows, h_eRack.columns)
                        if res:
                            if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                                target=target+'I'
                            return True, target
    else:    
        for h_eRack in h_eRacks_sorted:
            if h_eRack.model == 'CDAErack': #Sean for CDA Erack Comm
                if global_variables.RackNaming == 53: #Kumamoto TPB
                    API_check, port_no=h_eRack.check_and_query_wafer_slot()
                    result, erack_port=print_rackport_format(h_eRack.device_id, port_no, h_eRack.rows, h_eRack.columns)
                    print("Rackport", erack_port)
                    return API_check, erack_port if API_check else '*'
            if h_eRack.available:
                eRack_columns=h_eRack.columns
                eRack_rows=h_eRack.rows
                for i in range(0, eRack_columns, 1):  #select port by columns
                    eRack_available.append([])
                    for j in range(1, eRack_columns*eRack_rows, eRack_columns):
                        port_no=i + j
                        carrier=h_eRack.carriers[port_no-1]
                        lot=h_eRack.lots[port_no-1]
                        if lot['booked']:
                            eRack_books.append(port_no)
                        if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                            if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                                continue
                            eRack_available[i].append(port_no) #???

                if eRack_books:
                    for c in range(len(eRack_books)):
                        for d in range(1,eRack_rows):
                            port_no=eRack_books[c] + eRack_columns*d
                            if port_no > eRack_columns*eRack_rows:
                                continue
                            carrier= h_eRack.carriers[port_no-1]
                            lot= h_eRack.lots[port_no-1]
                            if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                                if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                                    continue
                                res, target=print_rackport_format(h_eRack.device_id, port_no, h_eRack.rows, h_eRack.columns)
                                if res:
                                    if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                                        target=target+'I'
                                    return True, target

                eRack_sorted=sorted(eRack_available, key=lambda h: len(h),reverse=True)
                for a in range(len(eRack_sorted)):
                    for b in range(len(eRack_sorted[a])):
                        port_no=eRack_sorted[a][b]
                        carrier= h_eRack.carriers[port_no-1]
                        lot= h_eRack.lots[port_no-1]
                        if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                            if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                                continue
                            res, target=print_rackport_format(h_eRack.device_id, port_no, h_eRack.rows, h_eRack.columns)     
                            if res:
                                if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                                    target=target+'I'
                                return True, target


    return False, '*'

def book_dest_port_by_area_id(dest_port_area, carrierType):
    if not dest_port_area:
        return False, '*'

    port_areas=Erack.h.port_areas
    #print(port_areas)
    ports=port_areas.get(dest_port_area, []) #chocp fix 2021/12/7
    #print(ports)
    for port in ports:
        h_eRack=port.get('h', 0)
        rack_id=port.get('rack_id', '')
        slot_no=port.get('slot_no', 0)

        #print('port in port_areas:', h_eRack, rack_id, slot_no)

        if h_eRack and rack_id and slot_no: #chocp fix 2021/12/7
            carrier=h_eRack.carriers[slot_no-1] #need add last idx, to avoid collision
            lot=h_eRack.lots[slot_no-1]
            if not lot['booked'] and carrier['carrierID'] == '' and carrier['status'] == 'up':
                if carrierType and not slot_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                    continue
                res, target=print_rackport_format(rack_id, slot_no, h_eRack.rows, h_eRack.columns)
                if res:
                    if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                        target=target+'I'
                    return True, target

    return False, '*'

def select_any_carrier_by_area(dest_port_area, carrierType):
    if not dest_port_area:
        return False, '*', ''

    port_areas=Erack.h.port_areas
    #print(port_areas)
    ports=port_areas.get(dest_port_area, []) #chocp fix 2021/12/7

    if not ports: # Mike: 2022/12/05
        return False, '*', ''
    #print(ports)
    for port in ports:
        h_eRack=port.get('h', 0)
        rack_id=port.get('rack_id', '')
        slot_no=port.get('slot_no', 0)

        if h_eRack and rack_id and slot_no: #chocp fix 2021/12/7
            carrier=h_eRack.carriers[slot_no-1] #need add last idx, to avoid collision
            lot=h_eRack.lots[slot_no-1]
            if not lot['machine'] and not lot['booked'] and carrier['carrierID']!='' and carrier['status'] == 'up':
                if carrierType and not slot_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                    continue
                res, target=print_rackport_format(rack_id, slot_no, h_eRack.rows, h_eRack.columns)
                if res:
                    if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                        target=target+'O'
                    return True, target, carrier['carrierID']

    return False, dest_port_area, '' # Mike: 2022/12/05

def select_any_empty_carrier_in_racks(h_eRacks, carrierType): #for UTAC usg1 MOUNT stage
    for h_eRack in h_eRacks:
        for port_no in range(1, h_eRack.slot_num+1, 1):
            carrier=h_eRack.carriers[port_no-1] #need add last idx, to avoid collision
            lot=h_eRack.lots[port_no-1]
            if not lot['machine'] and not lot['booked'] and not lot['lotID'] and carrier['carrierID']!='' and carrier['status'] == 'up':
                if carrierType and not port_no in h_eRack.validSlotType.get(carrierType, []): #2023/12/26 chocp
                    continue
                res, target=print_rackport_format(h_eRack.device_id, port_no, h_eRack.rows, h_eRack.columns)
                if res:
                    if h_eRack.model == 'TurnTable': #for qualcomm, for turntable
                        target=target+'O'
                    return True, target, carrier['carrierID']

    return False, '*', ''

def auto_assign_return_to_port(combo_dest_racks, carrierType): #workstations return to setting
    for dest_racks in combo_dest_racks.split(','):
        h_eRacks=[]
        for rackID in dest_racks.strip().split('|'): #for xxx|xxx|xxx
            h_eRack=Erack.h.eRacks.get(rackID)
            if h_eRack: #rack_id
                h_eRacks.append(h_eRack)

        if h_eRacks:
            res, new_dest_port=book_dest_port_in_racks(h_eRacks, True, carrierType)
            # res, new_dest_port=find_dest_port_in_racks(h_eRacks, True, carrierType)
            if res:
                return res, new_dest_port

    return False, ''

def erack_slot_type_verify(h_eRack, port_no, carrierType):
    slot_list=h_eRack.validSlotType.get(carrierType)
    if slot_list and port_no in slot_list:
        return True
    return False

def new_auto_assign_dest_port(DestPort, carrierType): #area, zone, group, rack, port
    average=True if global_variables.TSCSettings.get('CommandCheck', {}).get('AverageErackCapacityEnable') == 'yes' else False
    backward_search_allow=True if global_variables.TSCSettings.get('CommandCheck', {}).get('AllowBackwardSearchEnable') == 'yes' else False
    searchlimits=global_variables.TSCSettings.get('CommandCheck', {}).get('SearchLimits','Zones')

    print('=>do new_auto_assign_dest_port: DestPort={}, carrierType={}'.format(DestPort, carrierType))
    print('=>average={}, backward_search_allow={}, searchlimits={}'.format(average, backward_search_allow, searchlimits))

    h_workstation=EqMgr.getInstance().workstations.get(DestPort)
    if h_workstation:
        if global_variables.RackNaming in [1,21]:#Hshuo 20240611 for M11
            if "_C" in DestPort or 'Erack' in h_workstation.workstation_type or not h_workstation.enable:    #for ASECL M11 if destport is _C or plasma 
                return False, DestPort
            else:            
                return True, DestPort
        else:            
            return True, DestPort #direct return not check, if DestPort is workstation

    for target in DestPort.split('|'): #for xxx|xxx|xxx
        res, rack_id, port_no=rackport_format_parse(target) 
        if res:
            return True, target #direct return not check, if DestPort is Rack Port

        if Erack.h.port_areas.get(target): #target is areaID
            res, new_dest_port=book_dest_port_by_area_id(target, carrierType)
            if res: #DestPort is Area
                return res, new_dest_port #end
        else:
            h_eRack=Erack.h.eRacks.get(target) #test in rack search
            if h_eRack: #Target is rackID
                if global_variables.RackNaming == 4 and average: #special for spil bumping require
                    target=h_eRack.groupID
                else:
                    res, new_dest_port=book_dest_port_in_racks([h_eRack], average, carrierType)
                    if res:
                        return res, new_dest_port #end

                    elif backward_search_allow: 
                        target=h_eRack.groupID #do backward search

                    else:
                        continue

            h_eRacks=Erack.h.erack_groups.get(target) #test in group search
            if h_eRacks: #DestPort is Group
                res, new_dest_port=book_dest_port_in_racks(h_eRacks, average, carrierType)
                if res:
                    return res, new_dest_port #end

                elif backward_search_allow and searchlimits == 'Zones': #do backward search
                    target=h_eRacks[0].zone

                else:
                    continue

            h_eRacks=Erack.h.map_zones.get(target) #test in zone search
            if h_eRacks: #DestPort is Zone
                res, new_dest_port=book_dest_port_in_racks(h_eRacks, average, carrierType)
                if res:
                    return res, new_dest_port #end

    return False, DestPort #change, need add worksation mask

def print_rackport_format(rack_id, port_no, rows=3, columns=4):
    res=False
    portID=''

    if global_variables.RackNaming == 2: #GRA
        if rack_id[-1] == 'C':
            port_no=port_no+24

        elif rack_id[-1] == 'B':
            port_no=port_no+12

        res=True
        rack_id=rack_id.rstrip('ABC')
        portID=global_variables.Format_RackPort_Print%(rack_id, port_no)
        
    elif global_variables.RackNaming in [1, 16 ,23, 34, 54]: #ASECL
        r=re.match(global_variables.Format_Rack_Parse, rack_id) #E001, E1P1
        if r:
            res=True
            rack_no=int(r.group(1))
            portID=global_variables.Format_RackPort_Print%(rack_no, port_no)
        else:
            print('<<<Erack Naming Rule Error>>>:', rack_id, global_variables.Format_Rack_Parse)

    elif global_variables.RackNaming in [24, 27]: #SKYWORKS SG, JP
        L=(port_no-1)//columns+1
        C=(port_no-1)%columns+1
        port_position='L{}C{}R1'.format(L, C)
        if port_no == 0:
            port_position='L0C0R1'
        res=True
        portID=global_variables.Format_RackPort_Print%(rack_id, port_position)

    elif global_variables.RackNaming == 29: #8.27.10
        if port_no != 0:
            port_no=(port_no-1)%columns+1+int((port_no-1)/columns+1)*10
        res=True
        portID=global_variables.Format_RackPort_Print%(rack_id, port_no)

    elif global_variables.RackNaming == 30: #BOE
        res=True
        a=rows-(port_no//columns)
        b=port_no%columns
        if b == 0:
            b=columns
            a=a+1
        port_position=int(str(a)+str(b))
        portID=global_variables.Format_RackPort_Print%(rack_id, port_position)
        
    elif global_variables.RackNaming == 52: #240822 Hshuo KYEC FT
        if port_no != 0:
            port_map={
                10: 'A',
                11: 'B',
                12: 'C'
            }
            port_str=port_map.get(port_no, '{}'.format(port_no))

        portID=global_variables.Format_RackPort_Print % (rack_id, port_str)
        res=True
            
    elif global_variables.RackNaming == 53:  # 240822 Hshuo Kumamoto TPB
        L=(port_no - 1) // columns + 1
        C=(port_no - 1) % columns + 1
        port_position='0{}-0{}'.format(L, C)
        
        res=True
        portID=global_variables.Format_RackPort_Print % (rack_id, port_position)   
        
    elif global_variables.RackNaming in [46,47]: #TI Baguio
        row=(port_no-1)//columns+1
        col=(port_no-1)%columns+1
        # port_position='-{}-{}'.format(row, col)
        if port_no == 0:
            # port_position='-0-0'
            row=0
            col=0
        res=True
        portID=global_variables.Format_RackPort_Print%(rack_id, row,col)
        
    elif global_variables.RackNaming == 51:
        row = (port_no - 1) // columns
        col = (port_no - 1) % columns
        port_position = (row + 1) * 10  + (columns - col)
        res=True
        portID=global_variables.Format_RackPort_Print%(rack_id, port_position)

    else:
        res=True
        portID=global_variables.Format_RackPort_Print%(rack_id, port_no)
    #print('res:', res, portID)
    #print('**************************')
    return res, portID

def rackport_format_parse(target): #2023/12/26
    res=False
    rack_id=''
    port_no=0
    #print('**************************')
    #print('rackport_format_parse:', target)
    r=re.match(global_variables.Format_RackPort_Parse, target)
    if r:
        if global_variables.RackNaming == 2: #GRA11-001~024
            rack_id=r.group(1)
            port_no=int(r.group(2))
            if port_no>24:
                rack_id=rack_id+'C'
                port_no=port_no-24
            elif port_no>12:
                rack_id=rack_id+'B'
                port_no=port_no-12
            else:
                rack_id=rack_id+'A'
            if port_no < 0:
                port_no=0
            res=True

        elif global_variables.RackNaming in [1, 16 ,23, 34, 54]: #8.21M-2
            port_no=int(r.group(2))
            rack_no=int(r.group(1))
            rack_id=global_variables.Format_Rack_Print%(rack_no)
            res=True

        elif global_variables.RackNaming in [25,32,26]:  #8.25.15-1 CDTI
            port_no=int(r.groups()[-1])
            rack_id=r.group(1)
            res=True

        elif global_variables.RackNaming == 29: #8.27.10
            rack_id=r.group(1)
            tmp=int(r.group(2))
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                port_no=int(tmp/10-1)*h_eRack.columns+tmp%10
                if port_no < 0:
                    port_no=0
                res=True

        elif global_variables.RackNaming in [24, 27]: #SKYWORKS SG, JP
            rack_id=r.group(1)
            a=int(r.group(2))
            b=int(r.group(3))
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                port_no=int(a-1)*h_eRack.columns+b
                if port_no < 0:
                    port_no=0
                res=True

        elif global_variables.RackNaming == 30: #BOE
            rack_id=r.group(1)
            port_position=int(r.group(2))
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                res=True
                num=str(port_position)
                a=int(num[0])
                b=int(num[1])
                port_no=(h_eRack.rows-a)*h_eRack.columns+b
                if port_no < 0:
                    port_no=0
                    
        elif global_variables.RackNaming == 52:# 240822 Hshuo KYEC FT
            rack_id=r.group(1)
            port_str=r.group(2)
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                if port_str.isdigit():
                    port_no=int(port_str) - 1   
                else:
                    port_no=ord(port_str) - ord('A') + 10
                res=True

        elif global_variables.RackNaming == 53:  # 240822 Hshuo Kumamoto TPB
            rack_id=r.group(1)
            a=int(r.group(2))
            b=int(r.group(3))
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                port_no=(a - 1) * h_eRack.columns + b
                if port_no < 0:
                    port_no=0
                res=True
                
        elif global_variables.RackNaming in [46,47]: #TI Baguio
            rack_id=r.group(1)
            a=int(r.group(2))
            b=int(r.group(3))
            
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                port_no=int(a-1)*h_eRack.columns+b
                if port_no < 0:
                    port_no=0
                res=True
                
        elif global_variables.RackNaming == 51: #TI Miho
            rack_id=r.group(1)
            tmp = int(r.group(2))
            
            h_eRack=Erack.h.eRacks.get(rack_id)
            if h_eRack:
                port_no = (((tmp // 10)) - 1) * h_eRack.columns + (h_eRack.columns - (tmp % 10) + 1)
                if port_no < 0:
                    port_no=0
                res=True
                
        else:
            res=True
            port_no=int(r.group(2))
            rack_id=r.group(1)

    #else:
        #print('<<<Erack Naming Rule Parse Error>>>:', target, global_variables.Format_Rack_Parse)

    #print('Format_Rack_Parse res:{}, rack_id:{}, port_no:{}'.format(res, rack_id, port_no))

    return res, rack_id, port_no


def check_transfer_waiting_queue(check_queueID_name):
    for queueID_name, zone_wq_check in TransferWaitQueue.getAllInstance().items():
        tool_logger.debug("queueID_name:{}".format(queueID_name))
        if "zone_1F_AMR_MGZ" in check_queueID_name:
            tool_logger.debug("in zone_1F_AMR_MGZ")
            for host_tr_cmd_check in zone_wq_check.queue:#equipmentID
                tool_logger.debug(host_tr_cmd_check.get("source"))
                tool_logger.debug(host_tr_cmd_check.get("dest"))
                tool_logger.debug("source:{},dest:{},equipmentID:{}".format(host_tr_cmd_check.get("source"),host_tr_cmd_check.get("dest"),""))



def buf_allocate_test(h_vehicle, host_tr_cmd, buf_available_list_sorted, buf_reserved, schedule_algo='by_fix_order'): #new for Buf Constain
    # tool_logger.info("host_tr_cmd:{}".format(host_tr_cmd))
    # tool_logger.info("buf_available_list_sorted:{}".format(buf_available_list_sorted))
    # tool_logger.info("buf_reserved:{}".format(buf_reserved))
    # tool_logger.info("schedule_algo:{}".format(schedule_algo))
    primary_cmd_count=0
    single_cmd_count=0
    #About combine cmd
    #Unload first, and load after
    #Unload cmd is primary, and link to unload cmd
    #load is not primary, and no link
    buf_constrain=[]
    unload_buf_constrain=[]

    try:
        if global_variables.RackNaming in [33, 58] and buf_available_list_sorted:
            priorityBuf=host_tr_cmd.get('priorityBuf', '')
            if priorityBuf and priorityBuf != 'All':
                front_order = [3, 4, 5, 0, 1, 2, 9, 10, 11, 6, 7, 8]
                rear_order = [9, 10, 11, 6, 7, 8, 3, 4, 5, 0, 1, 2]
                if priorityBuf == "Front":
                    sort_order = front_order
                elif priorityBuf == "Rear":
                    sort_order = rear_order
                buf_to_index = {}
                for i in range(12):
                    buf_to_index["BUF" + str(i + 1).zfill(2)] = i
                buf_available_list_sorted.sort(key=lambda buf: sort_order[buf_to_index[buf]])

        r_dest=re.match(r'(.+)(BUF\d+)', host_tr_cmd['dest'])
        carriertype=host_tr_cmd['TransferInfoList'][0].get('CarrierType', '')
        if r_dest and r_dest.group(1) in Vehicle.h.vehicles:
            bufID=r_dest.group(2)
            if bufID!='BUF00':
                if h_vehicle.check_carrier_type =='yes':
                    if carriertype and carriertype in h_vehicle.carriertypedict[bufID] or 'All' in h_vehicle.carriertypedict[bufID]:
                        buf_constrain.append(bufID)
                        return True, 1, 1, False, buf_constrain, unload_buf_constrain
                    else:
                        return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
                else:
                    buf_constrain.append(bufID)
                    return True, 1, 1, False, buf_constrain, unload_buf_constrain
                           
        r_source=re.match(r'(.+)(BUF\d+)', host_tr_cmd['source'])
        if r_source and r_source.group(1) in Vehicle.h.vehicles:
            bufID=r_source.group(2)
            if bufID!='BUF00':
                buf_constrain.append(bufID)
                return True, 1, 1, False, buf_constrain, unload_buf_constrain
            
        if h_vehicle.check_carrier_type =='yes':
            valid_buf=[]
            unload_valid_buf=[]
            link_valid_buf=[]
            carriertype=host_tr_cmd['TransferInfoList'][0].get('CarrierType', '')
            unload_carriertype=host_tr_cmd['TransferInfoList'][1].get('CarrierType', '') if len(host_tr_cmd['TransferInfoList']) == 2 else ''
            link_carriertype=host_tr_cmd['link']['TransferInfoList'][0].get('CarrierType', '') if host_tr_cmd['link'] else ''

            for i in buf_available_list_sorted:
                if global_variables.RackNaming == 42:
                    if i == 'BUF01': # BUF01 only for cover tray not production
                        continue
                    if carriertype in h_vehicle.dynamicBufferMapping[i]  or 'All' in h_vehicle.dynamicBufferMapping[i]:
                        valid_buf.append(i)
                    if unload_carriertype in h_vehicle.dynamicBufferMapping[i] or 'All' in h_vehicle.dynamicBufferMapping[i]:
                        unload_valid_buf.append(i)
                    if link_carriertype in h_vehicle.dynamicBufferMapping[i] or 'All' in h_vehicle.dynamicBufferMapping[i]:
                        link_valid_buf.append(i)
                else:
                    if carriertype in h_vehicle.carriertypedict[i] or 'All' in h_vehicle.carriertypedict[i]:
                        valid_buf.append(i)
                    if unload_carriertype in h_vehicle.carriertypedict[i] or 'All' in h_vehicle.carriertypedict[i]:
                        unload_valid_buf.append(i)
                    if link_carriertype in h_vehicle.carriertypedict[i] or 'All' in h_vehicle.carriertypedict[i]:
                        link_valid_buf.append(i) 

            BufConstrain =[]
            unload_BufConstrain =[]
            if host_tr_cmd.get('BufConstrain'):
                bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections','')
                if bufferAllowedDirections and bufferAllowedDirections != 'All':
                    if valid_buf:
                        for i in range(len(valid_buf)):
                            if valid_buf[i] in h_vehicle.bufferDirection[bufferAllowedDirections]:
                                BufConstrain.append(valid_buf[i])
                        valid_buf=BufConstrain
                    if unload_valid_buf:
                        for i in range(len(unload_valid_buf)):
                            if unload_valid_buf[i] in h_vehicle.bufferDirection[bufferAllowedDirections]:
                                unload_BufConstrain.append(unload_valid_buf[i])
                        unload_valid_buf=unload_BufConstrain
                else:
                    if valid_buf:
                        for i in range(len(valid_buf)):
                            if valid_buf[i] in h_vehicle.vehicle_onTopBufs:
                                BufConstrain.append(valid_buf[i])
                        valid_buf=BufConstrain
                    if unload_valid_buf:
                        for i in range(len(unload_valid_buf)):
                            if unload_valid_buf[i] in h_vehicle.vehicle_onTopBufs:
                                unload_BufConstrain.append(unload_valid_buf[i])
                        unload_valid_buf=unload_BufConstrain
           
            if host_tr_cmd['replace']>0:
                if valid_buf and unload_valid_buf:
                    for i,load_bufID in enumerate(valid_buf):
                        for j,unload_bufID in enumerate(unload_valid_buf):
                            print(load_bufID,unload_bufID)
                            if load_bufID != unload_bufID:
                                unload_bufID=unload_valid_buf.pop(j)
                                buf_available_list_sorted.remove(unload_bufID)
                                unload_buf_constrain.append(unload_bufID)
                                load_bufID=valid_buf.pop(i)
                                buf_constrain.append(load_bufID)
                                buf_available_list_sorted.remove(load_bufID)
                                primary_cmd_count+=1
                                single_cmd_count+=2 #add for future load cmd not primary cmd test
                                if global_variables.RackNaming == 42:
                                    h_vehicle.update_dynamic_buffer_mapping(h_vehicle.vehicle_bufID.index(load_bufID),carriertype)
                                    h_vehicle.update_dynamic_buffer_mapping(h_vehicle.vehicle_bufID.index(unload_bufID),unload_carriertype)
                                return True, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
                            
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
                else:
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
            elif host_tr_cmd['link']:
                r1=re.match(r'(.+)(BUF\d+)', host_tr_cmd['link']['source'])
                if valid_buf and r1:
                    if r1.group(1) in Vehicle.h.vehicles:
                        bufID=r1.group(2)
                        if bufID!='BUF00':
                            load_bufID=valid_buf.pop()
                            buf_constrain.append(load_bufID)
                            buf_available_list_sorted.remove(load_bufID)
                            primary_cmd_count+=1
                            single_cmd_count+=1 #add for future load cmd not primary cmd test
                            return True, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain  
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain 
                elif valid_buf and link_valid_buf:
                    # if global_variables.RackNaming == 42:
                    #     valid_buf=valid_buf[::-1]
                    #     link_valid_buf=link_valid_buf[::-1]
                    for i,load_bufID in enumerate(valid_buf):
                        for j,link_bufID in enumerate(link_valid_buf):
                            print(load_bufID,link_bufID)
                            if load_bufID != link_bufID:
                                load_bufID=valid_buf.pop(i)
                                buf_constrain.append(load_bufID)
                                buf_available_list_sorted.remove(load_bufID)
                                primary_cmd_count+=1
                                single_cmd_count+=1 #add for future load cmd not primary cmd test
                                if global_variables.RackNaming == 42:
                                    h_vehicle.update_dynamic_buffer_mapping(h_vehicle.vehicle_bufID.index(load_bufID),carriertype)
                                return True, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain      
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain 
                else:
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain  
                
            else:
                if valid_buf: 
                    bufID=valid_buf.pop(-1) if global_variables.RackNaming != 42 else valid_buf.pop(0) #reserverd for link cmd from last not important buf
                    buf_constrain.append(bufID)
                    buf_available_list_sorted.remove(bufID)
                    single_cmd_count+=1 #add for future load cmd not primary cmd test
                    primary_cmd_count+=1
                    if global_variables.RackNaming == 42:
                        h_vehicle.update_dynamic_buffer_mapping(h_vehicle.vehicle_bufID.index(bufID),carriertype)
                else:
                    return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain

        else:
            # r=re.match(r'(.+MR.+)(BUF\d+)', host_tr_cmd['dest'])                
            if host_tr_cmd.get('BufConstrain') or schedule_algo == 'by_fix_order' or schedule_algo == 'by_auto_order': #load, unload or Replace Buf Constain cmd
                bufferAllowedDirections=host_tr_cmd.get('bufferAllowedDirections', '')
                
                if bufferAllowedDirections and bufferAllowedDirections != 'All' and host_tr_cmd.get('BufConstrain', ''):
                    matched_buf = [buf for buf in buf_available_list_sorted if buf in h_vehicle.bufferDirection[bufferAllowedDirections]]
                    if matched_buf:
                        bufID = matched_buf[0]
                        buf_available_list_sorted.pop(buf_available_list_sorted.index(bufID))
                        buf_constrain.append(bufID)
                        single_cmd_count+=1
                    else:
                        return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
                    if host_tr_cmd['replace']>0:
                        matched_buf = [buf for buf in buf_available_list_sorted if buf in h_vehicle.bufferDirection[bufferAllowedDirections]]
                        if matched_buf:
                            bufID = matched_buf[0]
                            buf_available_list_sorted.pop(buf_available_list_sorted.index(bufID))
                            buf_constrain.append(bufID)
                            single_cmd_count+=1
                        else:
                            return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain
                else:
                    bufID=buf_available_list_sorted.pop(0)
                    #if host_tr_cmd.get('BufConstrain') and (bufID not in ['BUF01', 'BUF03']): #contrain buf to top level
                    if host_tr_cmd.get('BufConstrain') and (bufID not in h_vehicle.vehicle_onTopBufs): #contrain buf to top level #8.21K
                        return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain

                    buf_constrain.append(bufID)
                    single_cmd_count+=1

                    if host_tr_cmd['replace']>0:
                        bufID=buf_available_list_sorted.pop(0)
                        if host_tr_cmd.get('BufConstrain') and (bufID not in h_vehicle.vehicle_onTopBufs): #contrain to top level
                            return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain

                        buf_constrain.append(bufID)
                        single_cmd_count+=1

            elif host_tr_cmd['primary']:#unload or load primary single cmd or replace primary cmd
                #if host_tr_cmd['link'] or host_tr_cmd['replace']>0:
                if host_tr_cmd['link'] or host_tr_cmd['replace']>0 or host_tr_cmd.get('preTransfer') or h_vehicle.one_buf_for_swap: #v8.24F for reserved one buffer when preTransfer 
                    if not buf_reserved:
                        bufID=buf_available_list_sorted.pop(-1) #reserverd for link cmd from last not important buf
                        buf_reserved=True
                    single_cmd_count+=1 #add for future load cmd not primary cmd test

                bufID=buf_available_list_sorted.pop(-1) #reserverd for this cmd
                primary_cmd_count+=1
                single_cmd_count+=1
                #if host_tr_cmd['Dest'] == '*....
                #   return True, primary_cmd_count, single_cmd_count, buf_reserved, [bufID]
                #

    except:
        traceback.print_exc()
        return False, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain

    return True, primary_cmd_count, single_cmd_count, buf_reserved, buf_constrain, unload_buf_constrain




day_night=False
eqset=set()
last_date_time=datetime.datetime.min

def in_timezone(dt):   #Jwo: 2023/02/24 for SPIL LG SampleDestSector
    timezone=(dt.time() >= datetime.time(7, 0) and dt.time() < datetime.time(19, 0))
    return timezone


def sampling_time_check(eqp):  #Jwo: 2023/02/24 for SPIL LG SampleDestSector
    global day_night, last_date_time
    current_time=datetime.datetime.now()
    print("current_time", current_time)

    current_zone=in_timezone(current_time)
    day_night=in_timezone(last_date_time)

    if not current_zone:
        day_night=not day_night

    else:
        pass

    if not day_night or (current_time - last_date_time).total_seconds() > 12*60*60:
        day_night=True
        eqp=set()
        print("change zone")
    last_date_time=current_time
    return eqp




def input_action_gen(target):
    TransferInfo={'CarrierID':'', 'SourcePort':'', 'DestPort':'', 'CarrierType': ''}
    CommandInfo={'CommandID':'', 'Replace':0, 'Priority':0, 'TransferState':1}

    host_tr_cmd={
        'primary':1,
        'uuid':'',
        'carrierID':'',
        'source':'',
        'dest':'',
        'zoneID':'other', #9/14
        'priority':0,
        'replace':0,
        'CommandInfo':CommandInfo,
        'TransferCompleteInfo':[],
        'OriginalTransferCompleteInfo':[],
        'TransferInfoList':[TransferInfo],
        'OriginalTransferInfoList':[TransferInfo],
        'link':None,
        'sourceType':''
    }
    
    local_tr_cmd={
        'uuid':'',
        'carrierID':'',
        'carrierLoc':'',
        'source':'',
        'dest':'',
        'priority':0,
        'first':True, #chocp 2022/5/11
        'last':True,
        'TransferInfo':TransferInfo,
        'OriginalTransferInfo':TransferInfo,
        'host_tr_cmd':host_tr_cmd
    }

    input_action={
        'type':'INPUT',
        'target':target,
        'point':find_point(target),
        'loc':'',
        'order':0,
        'local_tr_cmd':local_tr_cmd,
        }

    return input_action

#for append transfer and 3 load cmds, 3 unload cmds
def reschedule_to_eq_actions(action_list, initial_point, initial_station, logger=None): 
    initial_actions_in_order=[]
    seqs=[]
    in_order=True
    for action in action_list:
        if logger: logger.debug("QQ_tools.find_point(action.get('target')):{}".format(find_point(action.get('target'))))
        if logger: logger.debug("tools.find_point(initial_station):{}".format(find_point(initial_station)))
        if find_point(action.get('target')) == find_point(initial_station) and in_order:
            if logger: logger.debug("in_order:{}".format(in_order))
            initial_actions_in_order.append(action)
        else:
            in_order=False
            if logger: logger.debug("in_order:{}".format(in_order))
            seqs.append([action])

    elapsed_time, cost, action_in_order, extra_cost=schedule.cal({'target':'', 'point':initial_point, 'order':1}, seqs)

    for action in action_in_order[1:]:
        if logger: logger.debug("re-order actions=>")
        if logger: logger.debug("action['type']:{}".format(action['type']))
        if logger: logger.debug("action['target']:{}".format(action['target']))
        if logger: logger.debug("action['point']:{}".format(action['point']))
        if logger: logger.debug("elapsed_time:{}".format(elapsed_time))
        print('re-order actions=>', action['type'], action['target'], action['point'], elapsed_time)

    action_list.clear()
    action_list.extend(initial_actions_in_order)
    action_list.extend(action_in_order[1:])


def reschedule_to_stocker_actions(action_list, initial_point, initial_station, logger=None): 
    seqs=[]
    test_commands={}
    end_actions=[]
    for action in action_list[::-1]:
        h_workstation=EqMgr.getInstance().workstations.get(action['target'])
        if not h_workstation or 'ErackPort' in h_workstation.workstation_type or 'Stock' in h_workstation.workstation_type:
            if action['type'] == 'DEPOSIT':
                end_actions.append(action)
                continue

        command_id=action.get('local_tr_cmd', {}).get('uuid')
        if test_commands.get(command_id):
            if action['type'] == 'ACQUIRE':
                test_commands[command_id].appendleft(action) 
            else:
                test_commands[command_id].append(action)  
        else:
            test_commands[command_id]=[action]

    seqs=list(test_commands.values())
    elapsed_time, cost, action_in_order, extra_cost=schedule.cal({'target':'', 'point':initial_point, 'order':1}, seqs)
    return action_in_order[1:].extend(end_actions)

def find_other_charge_vehicle_for_BOE(vehicle):
    for vehicle_id,h_vehicle in Vehicle.h.vehicles.items():
        if vehicle != h_vehicle:
            if h_vehicle.force_charge:
                return True,h_vehicle
            else:
                return False,False

def find_other_vehicle_status(vehicleID):#kelvinng 20250317
    for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
        if vehicle_id == vehicleID:
            return {
                'AlarmCode': h_vehicle.error_code,
                'ForceCharge': h_vehicle.force_charge,
                'Point': h_vehicle.adapter.last_point,
                'Station': h_vehicle.at_station,
                'Battery': h_vehicle.adapter.battery['percentage'],
                'Charge': h_vehicle.adapter.battery['charge'],
                'Connected': h_vehicle.adapter.online['connected'],
        }
    return {}
            
def Timed_charging(timelist):
    current_time=datetime.datetime.now().time()
    try:
        for t in timelist:
            start=datetime.datetime.strptime(t.split("-")[0]+":00", "%H:%M:%S").time()
            end=datetime.datetime.strptime(t.split("-")[1]+":00", "%H:%M:%S").time()
            
            if start <= current_time <= end:
                return True
        return False
    except:
        return False
    
def find_command_detail_by_commandID(commandID):
    default_cmd={'CommandInfo':'','TransferCompleteInfo':''}
    if global_variables.RackNaming != 43:  #only Mirle MCS need query this detail
        return default_cmd
    for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
        for host_tr_cmd in zone_wq.queue:
            if commandID == host_tr_cmd['uuid']:
                default_cmd['CommandInfo']=host_tr_cmd['CommandInfo']
                default_cmd['TransferCompleteInfo']=host_tr_cmd['TransferCompleteInfo']
                return default_cmd
    else:
        for vehicle_id, h_vehicle in Vehicle.h.vehicles.items():
            for local_tr_cmd in h_vehicle.tr_cmds:
                if commandID == local_tr_cmd['uuid']:
                    default_cmd['CommandInfo']=local_tr_cmd['host_tr_cmd']['CommandInfo']
                    default_cmd['TransferCompleteInfo']=local_tr_cmd['host_tr_cmd']['TransferCompleteInfo']
                    return default_cmd
    return default_cmd

def find_command_zone_by_commandID(commandID):
    for queueID, zone_wq in TransferWaitQueue.getAllInstance().items():
        for host_tr_cmd in zone_wq.queue:
            if commandID == host_tr_cmd['uuid']:
                return queueID, host_tr_cmd
    return None, None

def appendTransferJudgment(actions, last_point):# Yuri 2024/11/27
    allowed_append=False
    if actions:
        target=actions[0].get('target', '')
        h_workstation=EqMgr.getInstance().workstations.get(target)
        if actions[0].get('type') == 'DEPOSIT' and (not h_workstation or 'Stock' in h_workstation.workstation_type):
            if find_point(target) != last_point and not any(action.get('type') == 'ACQUIRE' for action in actions):
                allowed_append=True
    return allowed_append

def acquire_lock_with_timeout(lock, timeout): #Yuri 2024/12/11
    acquired=lock.acquire(False)
    end_time=time.time() + timeout
    while not acquired and time.time() < end_time:
        time.sleep(0.1)  
        acquired=lock.acquire(False)
    return acquired

def allocate_buffer(buffer_list,transfer,check_carrier_type="no",vehicle_onTopBufs=[],carriertypedict={},bufferDirection={}):#Yuri 2024/12/13
    BufConstrain=transfer.get("BufConstrain",False)
    carriertype=transfer['TransferInfoList'][0].get('CarrierType', '')
    buffertype=transfer.get("bufferAllowedDirections","All")
    buffID=""
    if check_carrier_type=="yes":
        buffer_type_list={i:carriertypedict[i] for i in buffer_list}
        for k,v in buffer_type_list.items():
            if carriertype in v or "All" in v \
            and ((BufConstrain and buffertype != "All" and k in bufferDirection[buffertype])\
                or (BufConstrain and buffertype == "All" and k not in vehicle_onTopBufs ) \
                or (not BufConstrain)):
                buffID=k
    elif BufConstrain:
        for buff in buffer_list:
            if (BufConstrain and buffertype != "All" and buff in bufferDirection[buffertype] )\
                or (BufConstrain and buffertype == "All" and buff not in vehicle_onTopBufs ):
                buffID=buff
    else:
        buffID=buffer_list[0]
        
    return buffID

def update_lot_list(lot_list, lot_id, command_id, quantity):
    if lot_id in lot_list:
        lot_list[lot_id]["CommandID"].append(command_id)
    else:
        lot_list[lot_id] = {"CommandID": [command_id], "QUANTITY": quantity, "dispatch": False}
    
    if len(lot_list[lot_id]["CommandID"]) == lot_list[lot_id]["QUANTITY"]:
        lot_list[lot_id]["dispatch"] = True
    
    return lot_list