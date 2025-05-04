# algorithm/route_count_caches.py
# -*- coding: utf-8 -*-
import time
import global_variables
import traceback
import threading
import cProfile # 引入 cProfile
import pstats   # 引入 pstats
from web_service_log import *

def length(a, b, station_order_enable_flag): # 新增參數
    try:
        # 直接使用傳入的標誌，避免重複讀取全域變數
        if station_order_enable_flag:
            check=(a['order'] > b['order'])
        else:
            check=0

        # global_variables.dist 查找應該很快
        dist_val = global_variables.dist[a['point']][b['point']]
        return dist_val + 1*(a['point'] != b['point']), 1*check
    except:
        traceback.print_exc()
        return -1, -1

length_cache={}
find_route_cache={}

def find_route(now, sequences, station_order_enable_flag): # 新增參數
    current_thread = threading.current_thread().ident # 將 thread id 獲取移到函數開頭
    if not find_route_cache.get(current_thread): # 確保線程的 cache dict 存在
        find_route_cache[current_thread] = {}

    if sequences:
        if len(sequences) == 1 and len(sequences[0]) == 1:
            target_node = sequences[0][0]
            length_cache_key = (now['order'], now['point'], target_node['order'], target_node['point'])
            l=-1
            ot=-1
            if length_cache_key in length_cache:
                l, ot = length_cache[length_cache_key]
            else:
                # 傳遞 station_order_enable_flag
                l, ot = length(now, target_node, station_order_enable_flag)
                length_cache[length_cache_key] = l, ot
            return l, [now] + sequences[0], ot
        else:
            min_out_time=-1
            min_cost=-1
            min_route=[]
            # 使用 xrange 替代 range (Python 2.7)
            for i in xrange(len(sequences)):
                s = list(sequences) # 創建副本
                n = s[i][0]
                s[i] = s[i][1:]
                if not s[i]:
                    del s[i]

                # 優化快取鍵生成：只包含必要的狀態信息，移除 records
                cache_key_list = [n['order'], n['point'], n['target'], n['type']]
                # 使用 xrange 替代 range (Python 2.7)
                for j in xrange(len(s)):
                    # 使用 xrange 替代 range (Python 2.7)
                    for k in xrange(len(s[j])):
                        item = s[j][k]
                        cache_key_list.append(item.get('order', ''))
                        cache_key_list.append(item.get('point', ''))
                        cache_key_list.append(item.get('target', ''))
                        cache_key_list.append(item.get('type', ''))
                        # --- 移除了對 records 的遍歷 ---
                        # for m in xrange(len(s[j][k]['records'])):
                        #     record = s[j][k]['records'][m]
                        #     cache_key_list.append(record.get('carrierID', ''))
                        #     cache_key_list.append(record.get('dest', ''))
                        #     cache_key_list.append(record.get('source', ''))
                        #     cache_key_list.append(record.get('uuid', ''))
                find_route_cache_key = tuple(cache_key_list)

                c = -1
                r = []
                o = 0
                thread_cache = find_route_cache[current_thread] # 獲取當前線程的 cache
                if find_route_cache_key in thread_cache:
                    c, r, o = thread_cache[find_route_cache_key]
                else:
                    # 遞迴呼叫時傳遞 station_order_enable_flag
                    c, r, o = find_route(n, s, station_order_enable_flag)
                    thread_cache[find_route_cache_key] = c, r, o # 存入快取

                l = -1
                ot = -1
                # 確保 r 不是空的才進行下一步
                if r:
                    first_node_in_r = r[0]
                    length_cache_key = (now['order'], now['point'], first_node_in_r['order'], first_node_in_r['point'])
                    if length_cache_key in length_cache:
                        l, ot = length_cache[length_cache_key]
                    else:
                        # 傳遞 station_order_enable_flag
                        l, ot = length(now, first_node_in_r, station_order_enable_flag)
                        length_cache[length_cache_key] = l, ot

                    # 優化比較邏輯的可讀性
                    current_total_cost = c + l if c > -1 and l > -1 else -1
                    current_total_out_time = o + ot if o > -1 and ot > -1 else -1

                    is_better = False
                    if current_total_out_time > -1:
                        if min_out_time < 0 or current_total_out_time < min_out_time:
                            is_better = True
                        elif current_total_out_time == min_out_time:
                            if current_total_cost > -1 and (min_cost < 0 or current_total_cost < min_cost):
                                is_better = True
                    elif min_out_time < 0: # 如果還沒有有效的 out_time 解，則比較 cost
                         if current_total_cost > -1 and (min_cost < 0 or current_total_cost < min_cost):
                             is_better = True

                    if is_better:
                        min_cost = current_total_cost
                        min_route = [now] + r
                        min_out_time = current_total_out_time
                # else: r is empty, cannot calculate length or update minimums

            return min_cost, min_route, min_out_time
    return -1, [], 0 # Base case or no sequences left

def cal(now, sequences):
    current_thread = threading.current_thread().ident
    find_route_cache[current_thread] = {} # 初始化當前線程的 cache
    length_cache.clear() # 清空 length cache (如果跨 cal 呼叫不需要保留)

    # 在 cal 開始時讀取一次設定
    station_order_enable_setting = global_variables.TSCSettings.get('Other', {}).get('StationOrderEnable', 'no') # 提供預設值
    station_order_enable_flag = (station_order_enable_setting == 'yes')

    # --- 使用 cProfile ---
    profiler = cProfile.Profile()
    tic = time.time()
    # 在 profiler 下執行 find_route
    profiler.enable()
    # 傳遞 station_order_enable_flag
    c, s, o = find_route(now, sequences, station_order_enable_flag)
    profiler.disable()
    toc = time.time()

    # --- 打印性能分析結果 ---
    stats = pstats.Stats(profiler).sort_stats('cumulative') # 按累積時間排序
    stats.print_stats(20) # 打印前 20 個耗時最多的函數
    # tr_wq_lib_logger.warning(stats.print_stats(20))

    return toc - tic, c, s, o