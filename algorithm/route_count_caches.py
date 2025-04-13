import time
import global_variables
import traceback
import threading
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

length_cache={}
find_route_cache={}

def find_route(now, sequences):
    if sequences:
        if len(sequences) == 1 and len(sequences[0]) == 1:
            length_cache_key=(now['order'], now['point'], sequences[0][0]['order'], sequences[0][0]['point'])
            l=-1
            ot=-1
            if length_cache_key in length_cache:
                l, ot=length_cache[length_cache_key]
            else:
                l, ot=length(now, sequences[0][0])
                length_cache[length_cache_key]=l, ot
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
                cache=[n['order'], n['point'], n['target'], n['type']]
                for j in range(len(s)):
                    for k in range(len(s[j])):
                        cache.append(s[j][k].get('order', ''))
                        cache.append(s[j][k].get('point', ''))
                        cache.append(s[j][k].get('target', ''))
                        cache.append(s[j][k].get('type', ''))
                        for m in range(len(s[j][k]['records'])):
                            cache.append(s[j][k]['records'][m].get('carrierID', ''))
                            cache.append(s[j][k]['records'][m].get('dest', ''))
                            cache.append(s[j][k]['records'][m].get('source', ''))
                            cache.append(s[j][k]['records'][m].get('uuid', ''))
                find_route_cache_key=tuple(cache)

                c=-1
                r=[]
                o=0
                current_thread=threading.current_thread().ident
                if find_route_cache_key in find_route_cache.get(current_thread, {}):
                    c, r, o=find_route_cache[current_thread][find_route_cache_key]
                else:
                    c, r, o=find_route(n, s)
                    find_route_cache[current_thread][find_route_cache_key]=c, r, o
                l=-1
                ot=-1
                length_cache_key=(now['order'], now['point'], r[0]['order'], r[0]['point'])
                if length_cache_key in length_cache:
                    l, ot=length_cache[length_cache_key]
                else:
                    l, ot=length(now, r[0])
                    length_cache[length_cache_key]=l, ot
                if (min_out_time < 0 and o > -1 and ot > -1) or (o > -1 and ot > -1 and o + ot < min_out_time):
                    min_cost=c + l
                    min_route=[now] + r
                    min_out_time=o + ot
                elif (min_cost < 0 and c > -1 and l > -1) or (c > -1 and l > -1 and c + l < min_cost):
                    min_cost=c + l
                    min_route=[now] + r
                    min_out_time=o + ot
                else:
                    pass
            return min_cost, min_route, min_out_time
    return -1, [], 0

def cal(now, sequences):
    current_thread=threading.current_thread().ident
    find_route_cache[current_thread]={}
    tic=time.time()
    c, s, o=find_route(now, sequences)
    toc=time.time()
    return toc-tic, c, s, o

