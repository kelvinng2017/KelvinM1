from semi.SecsHostMgr import E88_Host

import global_variables

from erack.ICWiserErackAdapter_e88 import ICWiserErackAdapter

import traceback
import time

if __name__ == '__main__':

    global_variables.RackNaming=30
    global_variables.Format_RackPort_Parse=r'(.+E\d+)-(\d\d)'
    global_variables.Format_RackPort_Print='%s-%.2d'
    global_variables.Format_Rack_Parse=r'(.+E\d+)'
    global_variables.Format_Rack_Print='%s'

    E88_Host('', 5001, name='Main', mdln='STKC_v1.1')
    secsgem_e88_h=E88_Host.getInstance()

    secsgem_e88_h.initial()
    secsgem_e88_h.enable()
    setting={'ip':'192.168.0.198', 'port':10001}

    setting['idx']=1
    setting['eRackID']='E001-01'
    setting['mac']=''
    setting['groupID']=''
    setting['zone']=''
    setting['link']=''
    setting['func']=''

    setting['location']=''
    setting['type']='3x4'
    setting['zonesize']=12
    setting['validCarrierType']=''


    h=ICWiserErackAdapter(secsgem_e88_h, setting, secsgem_e88_h.Transfers, secsgem_e88_h.Carriers, secsgem_e88_h.Zones)

    h.setDaemon(True)
    h.start()
    try:
        while True:
            time.sleep(0.005)
            try:
                res=raw_input('\ninput cmd and exit\n') #go,215,300,180
            except EOFError:
                time.sleep(5)
                continue
            
            cmds=res.split(',')
            #print('\n\n')
            if cmds[0] == 'r': #man
                h.shelf_h.get_cst_id()
    except:
        traceback.print_exc()
        pass
