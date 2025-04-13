import subprocess
#import commands
import threading
import os
import time
path='./auto_setting_file/'
if not os.path.isdir(path):#check file being
    os.makedirs(path, mode=0o777)#create file

def cmdrun(cmd):
    try:
        #print(cmd)
        subprocess.getoutput(cmd)
        #commands.getoutput(cmd)
    except:    
        print("["+cmd+"] ERROR")     

f=open('/home/mcsadmin/tsc/simulator/auto_config.txt', 'r')
mode=0
cmds=[]
for line in f.readlines():
    port=0    
    name=""
    if "MR" in line.upper():
        mode=1
    elif "ERACK" in line.upper():
        mode=2
    if line[0]!='#' and line[0]!='/':
        if "," in line:
            port=str(int(line[0:line.find(",")]))
            name=str(line[line.find(",")+1:])
            if mode == 1:
                cmd="python2 /home/mcsadmin/tsc/simulator/tcp_bridge_simulate.py -p {} -i {} > ./auto_setting_file/MR_{}.txt".format(port.strip(),name.strip(),name.strip())
            elif mode == 2:
                cmd="python3 /home/mcsadmin/tsc/simulator/GuiErackSimulator.py {} {} > ./auto_setting_file/ER_{}.txt".format(port.strip(),name.strip(),name.strip())
            if cmd:
                cmds.append(cmd)
                cmd=""
f.close()
for i in range(len(cmds)):
    print(cmds[i])
    time.sleep(4)
    threading.Thread(target=cmdrun, args=(cmds[i].strip(),)).start()     
while 1:
    input()
    pass
