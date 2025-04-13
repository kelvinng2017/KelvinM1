import time
import global_variables
import traceback

'''class Task():
    def __init__(self, uuid, port):
        self.uuid=uuid
        self.point=tools.find_point(port)
        self.port=port
        self.point=port
        self.port=port
    def __repr__(self):
        return self.point'''

def length(a, b):
    try:
        if global_variables.TSCSettings.get('Other', {}).get('StationOrderEnable') == 'yes': # chocp fix for other item
            check=(a['order'] > b['order'])
        else:
            check=0
            
        return global_variables.dist[a['point']][b['point']]+1*(a['point']!=b['point']), 1*check
    except:
        traceback.print_exc()
        return -1, -1

def find_route(now, sequences):
    if sequences:
        if len(sequences) == 1 and len(sequences[0]) == 1:
            #print(now, sequences)
            l, ot=length(now, sequences[0][0])
            return l, [now] + sequences[0], ot
        else:
            min_out_time=-1
            min_cost=-1
            min_route=[]
            for i in range(len(sequences)):
                s=list(sequences)
                n=s[i][0]
                s[i]=s[i][1:]
                if not s[i]:
                    del s[i]
                c, r, o=find_route(n, s)
                l, ot=length(now, r[0])
                #print(now, sequences, s, n, c, r, o, l, ot)
                if (min_out_time < 0 and o > -1 and ot > -1) or (o > -1 and ot > -1 and o + ot < min_out_time):
                    min_cost=c + l
                    min_route=[now] + r
                    min_out_time=o + ot
                elif (o > -1 and ot > -1 and o + ot == min_out_time):
                    if (min_cost < 0 and c > -1 and l > -1) or (c > -1 and l > -1 and c + l < min_cost):
                        min_cost=c + l
                        min_route=[now] + r
                        min_out_time=o + ot
                    else:
                        pass
                else:
                    pass
            return min_cost, min_route, min_out_time
    return -1, [], 0

def cal(now, sequences):
    tic=time.time()
    c, s, o=find_route(now, sequences)
    toc=time.time()
    return toc-tic, c, s, o
