# -*- coding: utf-8 -*-
import time
import global_variables
import traceback
import threading

def length(a, b):
    try:
        if global_variables.TSCSettings.get('Other', {}).get('StationOrderEnable') == 'yes':
            check = 1 if (a['order'] > b['order']) else 0
        else:
            check = 0
            
        return global_variables.dist[a['point']][b['point']] + 1 * (a['point'] != b['point']), 1 * check
    except:
        traceback.print_exc()
        return -1, -1

# Python 2.7 相容的快取實作
length_cache = {}
find_route_cache = {}

def get_thread_cache():
    """獲取當前線程的快取"""
    current_thread = threading.current_thread().ident
    if current_thread not in find_route_cache:
        find_route_cache[current_thread] = {}
    return find_route_cache[current_thread]

def generate_cache_key(sequences):
    """生成快取鍵，針對 Python 2.7 優化"""
    key_parts = []
    for seq_idx, seq in enumerate(sequences):
        for item_idx, item in enumerate(seq):
            # 只使用關鍵欄位來生成更短的快取鍵
            key_parts.extend([
                item.get('order', 0),
                item.get('point', ''),
                item.get('target', ''),
                item.get('type', '')
            ])
            # 限制記錄數量以避免快取鍵過長
            records = item.get('records', [])
            for record_idx, record in enumerate(records[:3]):  # 只取前3個記錄
                key_parts.extend([
                    record.get('uuid', '')[:8],  # 只取 UUID 前8位
                    record.get('source', ''),
                    record.get('dest', '')
                ])
    return tuple(key_parts)

def find_route_iterative(now, sequences):
    """使用迭代方式替代遞迴，避免 Python 2.7 的遞迴限制"""
    if not sequences:
        return -1, [], 0
    
    # 基本情況處理
    if len(sequences) == 1 and len(sequences[0]) == 1:
        target = sequences[0][0]
        length_key = (now['order'], now['point'], target['order'], target['point'])
        
        if length_key in length_cache:
            l, ot = length_cache[length_key]
        else:
            l, ot = length(now, target)
            length_cache[length_key] = (l, ot)
        
        return l, [now] + sequences[0], ot
    
    thread_cache = get_thread_cache()
    
    # 使用堆疊模擬遞迴
    stack = [(now, sequences, [])]  # (current_node, remaining_sequences, path)
    best_cost = float('inf')
    best_route = []
    best_out_time = float('inf')
    
    # 限制迭代次數以避免無窮迴圈（Python 2.7 保護機制）
    max_iterations = 1000
    iteration_count = 0
    
    while stack and iteration_count < max_iterations:
        iteration_count += 1
        current_node, current_sequences, current_path = stack.pop()
        
        if not current_sequences:
            # 到達終點，計算總成本
            total_cost = 0
            total_out_time = 0
            valid_path = True
            
            for i in range(len(current_path) - 1):
                length_key = (current_path[i]['order'], current_path[i]['point'], 
                            current_path[i+1]['order'], current_path[i+1]['point'])
                if length_key in length_cache:
                    step_cost, step_out_time = length_cache[length_key]
                else:
                    step_cost, step_out_time = length(current_path[i], current_path[i+1])
                    length_cache[length_key] = (step_cost, step_out_time)
                
                if step_cost == -1:
                    valid_path = False
                    break
                    
                total_cost += step_cost
                total_out_time += step_out_time
            
            if valid_path and (total_cost < best_cost or 
                              (total_cost == best_cost and total_out_time < best_out_time)):
                best_cost = total_cost
                best_route = current_path[:]
                best_out_time = total_out_time
            continue
        
        # 生成下一層節點（限制分支數量）
        branch_count = 0
        max_branches = 10  # 限制分支數量以控制複雜度
        
        # 按啟發式排序序列
        sequence_priorities = []
        for i, seq in enumerate(current_sequences):
            if seq:
                first_item = seq[0]
                heuristic = global_variables.dist.get(current_node['point'], {}).get(
                    first_item['point'], float('inf'))
                sequence_priorities.append((heuristic, i))
        
        sequence_priorities.sort()
        
        for heuristic, i in sequence_priorities:
            if branch_count >= max_branches:
                break
            branch_count += 1
            
            # 剪枝：如果啟發式成本已經超過當前最佳解，跳過
            if best_cost != float('inf') and heuristic > best_cost:
                continue
                
            seq_copy = [list(s) for s in current_sequences]
            next_item = seq_copy[i][0]
            seq_copy[i] = seq_copy[i][1:]
            
            if not seq_copy[i]:
                del seq_copy[i]
            
            new_path = current_path + [next_item]
            stack.append((next_item, seq_copy, new_path))
    
    if iteration_count >= max_iterations:
        print("警告：到達最大迭代次數，可能存在性能問題")
    
    return (best_cost if best_cost != float('inf') else -1, 
            best_route, 
            best_out_time if best_out_time != float('inf') else 0)

def find_route_greedy(now, sequences):
    """貪婪演算法版本，適用於大型序列"""
    if not sequences:
        return -1, [], 0
        
    route = [now]
    total_cost = 0
    total_out_time = 0
    current_node = now
    remaining_sequences = [list(seq) for seq in sequences]
    
    while any(remaining_sequences):
        best_next = None
        best_cost = float('inf')
        best_out_time = 0
        best_seq_idx = -1
        
        # 找到最近的下一個節點
        for i, seq in enumerate(remaining_sequences):
            if seq:
                next_item = seq[0]
                length_key = (current_node['order'], current_node['point'], 
                            next_item['order'], next_item['point'])
                
                if length_key in length_cache:
                    step_cost, step_out_time = length_cache[length_key]
                else:
                    step_cost, step_out_time = length(current_node, next_item)
                    length_cache[length_key] = (step_cost, step_out_time)
                
                if step_cost != -1 and step_cost < best_cost:
                    best_cost = step_cost
                    best_out_time = step_out_time
                    best_next = next_item
                    best_seq_idx = i
        
        if best_next is None:
            break
            
        # 移動到下一個節點
        route.append(best_next)
        total_cost += best_cost
        total_out_time += best_out_time
        current_node = best_next
        
        # 從序列中移除已處理的項目
        remaining_sequences[best_seq_idx] = remaining_sequences[best_seq_idx][1:]
        if not remaining_sequences[best_seq_idx]:
            del remaining_sequences[best_seq_idx]
    
    return total_cost, route, total_out_time

def find_route(now, sequences):
    """主要路徑搜尋函數，根據問題大小選擇演算法"""
    if not sequences:
        return -1, [], 0
        
    # 計算問題複雜度
    total_items = sum(len(seq) for seq in sequences)
    complexity = len(sequences) * total_items
    
    # 根據複雜度選擇演算法
    if complexity > 100:  # 大型問題使用貪婪演算法
        # print("使用貪婪演算法處理大型問題...")
        return find_route_greedy(now, sequences)
    elif complexity > 50:  # 中型問題使用迭代演算法
        # print("使用迭代演算法處理中型問題...")
        return find_route_iterative(now, sequences)
    else:  # 小型問題使用原有遞迴演算法
        return find_route_recursive(now, sequences)

def find_route_recursive(now, sequences):
    """原有的遞迴演算法，用於小型問題"""
    if not sequences:
        return -1, [], 0
        
    if len(sequences) == 1 and len(sequences[0]) == 1:
        length_key = (now['order'], now['point'], sequences[0][0]['order'], sequences[0][0]['point'])
        if length_key in length_cache:
            l, ot = length_cache[length_key]
        else:
            l, ot = length(now, sequences[0][0])
            length_cache[length_key] = (l, ot)
        return l, [now] + sequences[0], ot
    
    thread_cache = get_thread_cache()
    cache_key = generate_cache_key(sequences)
    full_cache_key = (now['order'], now['point'], now.get('target', ''), now.get('type', '')) + cache_key
    
    if full_cache_key in thread_cache:
        return thread_cache[full_cache_key]
    
    min_out_time = -1
    min_cost = -1
    min_route = []
    
    for i in range(min(len(sequences), 5)):  # 限制分支數量
        s = [list(seq) for seq in sequences]
        n = s[i][0]
        s[i] = s[i][1:]
        if not s[i]:
            del s[i]
        
        c, r, o = find_route(n, s)
        
        length_key = (now['order'], now['point'], r[0]['order'], r[0]['point']) if r else None
        if length_key:
            if length_key in length_cache:
                l, ot = length_cache[length_key]
            else:
                l, ot = length(now, r[0])
                length_cache[length_key] = (l, ot)
        else:
            l, ot = -1, -1
        
        if l != -1 and c != -1:
            if (min_out_time < 0 and o > -1 and ot > -1) or (o > -1 and ot > -1 and o + ot < min_out_time):
                min_cost = c + l
                min_route = [now] + r
                min_out_time = o + ot
            elif (min_cost < 0 and c > -1 and l > -1) or (c > -1 and l > -1 and c + l < min_cost):
                min_cost = c + l
                min_route = [now] + r
                min_out_time = o + ot
    
    result = (min_cost, min_route, min_out_time)
    thread_cache[full_cache_key] = result
    return result

def cal(now, sequences):
    """優化的計算函數"""
    thread_cache = get_thread_cache()
    
    # 定期清理快取以避免記憶體洩漏
    if len(thread_cache) > 5000:
        # 保留最近的 1000 個項目
        items = list(thread_cache.items())
        thread_cache.clear()
        for key, value in items[-1000:]:
            thread_cache[key] = value
    
    tic = time.time()
    c, s, o = find_route(now, sequences)
    toc = time.time()
    
    return toc - tic, c, s, o

def clear_cache():
    """清理所有快取"""
    global length_cache
    length_cache.clear()
    current_thread = threading.current_thread().ident
    if current_thread in find_route_cache:
        find_route_cache[current_thread].clear()

def batch_cal(requests):
    """批次處理函數"""
    results = []
    for now, sequences in requests:
        result = cal(now, sequences)
        results.append(result)
    return results 