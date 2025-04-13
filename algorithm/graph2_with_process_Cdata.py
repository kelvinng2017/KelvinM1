from ctypes import *
import multiprocessing as mp
from threading import Thread
import threading
import time
import random

class c_edge(Structure):
    _fields_=[('dist', c_int*10000)]

class BaseGraph(object):
    def __init__(self, graph_dict=None):
        """ initializes a graph object 
            If no dictionary or None is given, an empty dictionary will be used
        """
        self.iGraph_dict={}
        if graph_dict == None:
            graph_dict={}
        for vertex in graph_dict:
            self.iGraph_dict[vertex]={} #work on py3
            if type(graph_dict[vertex]) is list:
                for edge in graph_dict[vertex]:
                    self.iGraph_dict[vertex][edge]={'length':1, 'name':'', 'road':''}
            elif type(graph_dict[vertex]) is dict:
                for edge in list(graph_dict[vertex].keys()):
                    self.iGraph_dict[vertex][edge]=graph_dict[vertex][edge]
        self.debug=False

    def vertices(self):
        """ returns the vertices of a graph """
        return list(self.iGraph_dict.keys())

    def edges(self, bidirection=False, loop=True):
        """ returns the edges of a graph 
            bidirection=True if the edge is non directional, 
            loop=True if loop is allowed. 
            If edge is non directional, the pair of edges is a set, 
            otherwise, the pair of edges is a tuple. """
        return self.__generate_edges(bidirection, loop)

    def add_vertex(self, vertex):
        """ If the vertex "vertex" is not in 
            self.iGraph_dict, a key "vertex" with an empty 
            dict as a value is added to the dictionary. 
            Otherwise nothing has to be done. 
        """
        if vertex not in self.iGraph_dict:
            self.iGraph_dict[vertex]={}
            return True
        return False

    def del_vertex(self, vertex):
        """ If the vertex "vertex" is in 
            self.iGraph_dict, the dict with the key "vertex" 
            is removed from the dictionary. 
            Besides, all edge with the key "vertex" 
            is removed at the same time. 
            Otherwise nothing has to be done. 
        """ 
        if vertex in self.iGraph_dict:
            self.iGraph_dict.pop(vertex)
            for start_vertex in self.iGraph_dict:
                if vertex in self.iGraph_dict[start_vertex]:
                    self.iGraph_dict[start_vertex].pop(vertex)
            return True
        return False

    def add_edge(self, start_vertex, end_vertex, length=1, bidirection=False, name='', road=''):
        """ add edge to self.iGraph_dict """
        if start_vertex in self.iGraph_dict.keys():
            if end_vertex in self.iGraph_dict.keys():
                self.iGraph_dict[start_vertex][end_vertex]={'length':length, 'name':name, 'road':road}
                if bidirection:
                    self.iGraph_dict[end_vertex][start_vertex]={'length':length, 'name':name, 'road':road}
                return True
        return False

    def del_edge(self, start_vertex, end_vertex, bidirection=False):
        """ remove edge from self.iGraph_dict """
        if start_vertex in self.iGraph_dict:
            if end_vertex in self.iGraph_dict[start_vertex]:
                self.iGraph_dict[start_vertex].pop(end_vertex)
                if not bidirection:
                    return True
        if bidirection:
            if end_vertex in self.iGraph_dict:
                if start_vertex in self.iGraph_dict[end_vertex]:
                    self.iGraph_dict[end_vertex].pop(start_vertex)
                    return True
        return False

    def get_neighbor(self, vertex): # Mike: 2021/08/09
        ret=[]
        try:
            # for neighbor in self.iGraph_dict[vertex]:
            for neighbor in self.iGraph_dict[vertex].keys():
                ret.append(neighbor)
        except KeyError:
            pass
        return ret

    def add_edge_info(self, start_vertex, end_vertex, **kwargs): # Mike: 2021/03/15
        if start_vertex in self.iGraph_dict:
            if end_vertex in self.iGraph_dict[start_vertex]:
                for key, value in kwargs.items():
                    self.iGraph_dict[start_vertex][end_vertex][key]=value
                return True
        return False

    def get_edge_detail(self, start_vertex, end_vertex):
        ret=None
        try:
            ret=self.iGraph_dict[start_vertex][end_vertex]
        except KeyError:
            pass
        return ret

    def __generate_edges(self, bidirection=True, loop=True):
        """ A private method generating the edges of the 
            graph "graph". Edges are represented as sets 
            with one (a loop back to the vertex) or two 
            vertices if edges are non directional, otherwise, 
            they will represented as tuples with 
            two vertices. 
        """
        edges=[]
        # for vertex in self.iGraph_dict:
        for vertex in self.iGraph_dict.keys():
            # for neighbour in self.iGraph_dict[vertex]:
            for neighbour in self.iGraph_dict[vertex].keys():
                if bidirection and loop:
                    edges.append((vertex, neighbour))
                elif bidirection and not loop:
                    if vertex != neighbour:
                        edges.append((vertex, neighbour))
                elif not bidirection and loop:
                    if {neighbour, vertex} not in edges:
                        edges.append({vertex, neighbour})
                else:
                    if vertex != neighbour:
                        if {neighbour, vertex} not in edges:
                            edges.append({vertex, neighbour})
        return edges

    def __str__(self):
        res="vertices: "
        for k in self.iGraph_dict:
            res += str(k) + " "
        res += "\nedges: "
        for edge in self.__generate_edges():
            res += str(edge) + " "
        return res

    def dijkstra_map_generator_original(self): # Mike: 2021/10/22
        """ returns a list of isolated vertices. """
        graph=self.iGraph_dict
        update={}
        dist={}
        trace={}
        nodes=list(graph.keys())
        for FP in nodes:
            update[FP]=True
            dist[FP]={}
            trace[FP]={}
            for TP in nodes:
                try:
                    # dist[FP][TP]=graph[FP][TP].length
                    dist[FP][TP]=graph[FP][TP]['length']
                    trace[FP][TP]=FP
                except KeyError:
                    if FP == TP:
                        dist[FP][TP]=0
                        trace[FP][TP]=FP
                    else:
                        dist[FP][TP]=-1
                        trace[FP][TP]=''
        while nodes:
            for CP in nodes:
                update[CP]=False
                if True not in update.values():
                    return dist, trace
                for FP in nodes:
                    if dist[CP][FP]>-1 and update[FP]:#from 0 => -1 mike
                        for TP in nodes:
                            if TP == CP:
                                continue
                            if dist[FP][TP]>-1: #from 0 => -1 mike
                                if dist[CP][TP] == -1 or dist[CP][TP]>dist[CP][FP]+dist[FP][TP]:
                                    dist[CP][TP]=dist[CP][FP]+dist[FP][TP]
                                    trace[CP][TP]=trace[FP][TP]
                                    update[CP]=True

        return dist, trace

    def dijkstra_map_generator(self): # Mike: 2023/03/30
        """ returns a list of isolated vertices. """
        t0=time.time()
        #print('enter dijkstra_map_generator:', t0)

        graph=self.iGraph_dict
        dist_c=[]
        trace_c=[]
        dist={}
        trace={}
        mapping={}
        reverse_mapping={}
        nodes=list(graph.keys())

        # for i, FP in enumerate(nodes):
        #     dist[FP]={}
        #     trace[FP]={}
        #     mapping[i]=FP
        #     reverse_mapping[FP]=i
        #     dist_c.append([])
        #     trace_c.append([])
        #     for j, TP in enumerate(nodes):
        #         try:
        #             # dist_c[i].append(graph[FP][TP].length)
        #             dist_c[i].append(graph[FP][TP]['length'])
        #             trace_c[i].append(i)
        #         except KeyError:
        #             if FP == TP:
        #                 dist_c[i].append(0)
        #                 trace_c[i].append(i)
        #             else:
        #                 dist_c[i].append(-1)
        #                 trace_c[i].append(-1)

        # dist_list=[]
        # trace_list=[]

        # for i in range(len(dist_c)):
        #     d=c_edge()
        #     t=c_edge()
        #     for j in range(len(dist_c)):
        #         d.dist[j]=dist_c[i][j]
        #         t.dist[j]=trace_c[i][j]
        #     dist_list.append(d)
        #     trace_list.append(t)
        
        dist_list=[]
        trace_list=[]
        for i, FP in enumerate(nodes):
            dist[FP]={}
            trace[FP]={}
            mapping[i]=FP
            reverse_mapping[FP]=i
            d=c_edge()
            t=c_edge()
            for j, TP in enumerate(nodes):
                if FP != TP:
                    temp_dist=graph[FP].get(TP, {}).get('length', -1)
                    d.dist[j]=temp_dist
                    if temp_dist != -1:
                        t.dist[j]=i
                    else:
                        t.dist[j]=-1
                else:
                    d.dist[j]=0
                    t.dist[j]=i
            dist_list.append(d)
            trace_list.append(t)

        dist_array=(c_edge * len(dist_list))(*dist_list)
        trace_array=(c_edge * len(trace_list))(*trace_list)

        t1=time.time()
        #print('initialied data:', t1)

        libc=CDLL("./algorithm/lib/dijkstra_lib.so")
        libc.test.argtypes=POINTER(c_edge), POINTER(c_edge), c_int
        libc.test.restype=None
        libc.test(dist_array, trace_array, len(dist_list))

        t2=time.time()
        #print('external C finish:', t2)

        for i in range(len(dist_list)):
            for j in range(len(dist_list)):
                dist[mapping[i]][mapping[j]]=dist_array[i].dist[j]
                trace[mapping[i]][mapping[j]]=trace_array[i].dist[j]

        t3=time.time()
        #print('finish map:', t2)

        print('do dijkstra_map_generator elapsed time:')
        print("initial:{:.3f}, external C:{:.3f}, create map:{:.3f}".format(t1-t0, t2-t1, t3-t2))

        return dist, trace

    def find_isolated_vertices(self):
        """ returns a list of isolated vertices. """
        graph=self.iGraph_dict
        isolated=[]
        for vertex in graph:
            if not graph[vertex]:
                isolated += [vertex]
        return isolated

    def find_path(self, start_vertex, end_vertex, path=[], length=0):
        """ find a path from start_vertex to end_vertex 
            in graph """
        graph=self.iGraph_dict
        path=path + [start_vertex]
        if start_vertex not in graph or end_vertex not in graph:
            return None, -1
        if start_vertex == end_vertex:
            return path, length
        for vertex in graph[start_vertex].keys():
            if vertex not in path:
                extended_path, extended_length=self.find_path(vertex, 
                                                                end_vertex, 
                                                                path,
                                                                # length+graph[start_vertex][vertex])
                                                                length+graph[start_vertex][vertex]['length'])
                if extended_path:
                    return extended_path, extended_length
        return None, -1

    def find_all_paths(self, start_vertex, end_vertex, path=[], length=0):
        """ find all paths from start_vertex to 
            end_vertex in graph """
        graph=self.iGraph_dict 
        path=path + [start_vertex]
        if start_vertex == end_vertex:
            return [(path, length)]
        if start_vertex not in graph:
            return []
        paths=[]
        for vertex in graph[start_vertex].keys():
            if vertex not in path:
                extended_paths=self.find_all_paths(vertex, 
                                                     end_vertex, 
                                                     path,
                                                    #  length+graph[start_vertex][vertex])
                                                    length+graph[start_vertex][vertex]['length'])
                for (p, l) in extended_paths:
                    paths.append((p, l))
        return paths

    def find_shortest_path(self, start_vertex, end_vertex, block_vertices=[], block_edges=[]):
        """ find the shortest path from start_vertex to end_vertex 
            in graph with dijkstra algorithm """
        graph=self.iGraph_dict
        vertex_list=list(graph.keys())
        path=[]
        length=-1
        visited=[]
        dist={}
        near={}
        # for vertex in graph:
        for vertex in graph.keys():
            if vertex == start_vertex:
                dist[vertex]=0
                near[vertex]=start_vertex
            else:
                dist[vertex]=-1
                near[vertex]=''

        # dijkstra algorithm
        while end_vertex not in visited:
            if self.debug:
                print(dist)
                print(near)
                print(visited)
                print("")

            # find nearest vertex
            min_dist=-1
            min_vertex=''
            for vertex in vertex_list:
                if (vertex not in visited) and (dist[vertex] != -1):
                    if (dist[vertex] < min_dist) or (min_dist == -1):
                        min_dist=dist[vertex]
                        min_vertex=vertex
            if min_dist == -1:
                break

            # update corresponding branch length
            # for vertex in graph[min_vertex]:
            for vertex in graph[min_vertex].keys():
                if vertex not in visited:
                    if vertex not in block_vertices and (min_vertex, vertex) not in block_edges: # check if vertex or edge is blocked
                        # if (graph[min_vertex][vertex].length + dist[min_vertex] < dist[vertex]) or (dist[vertex] == -1):
                        if (graph[min_vertex][vertex]['length'] + dist[min_vertex] < dist[vertex]) or (dist[vertex] == -1):
                            # dist[vertex]=graph[min_vertex][vertex].length + dist[min_vertex]
                            dist[vertex]=graph[min_vertex][vertex]['length'] + dist[min_vertex]
                            near[vertex]=min_vertex

            # add to visited list
            visited.append(min_vertex)

        # generating shortest path if exists
        if end_vertex in visited:
            length=dist[end_vertex]
            visited_vertex=end_vertex
            while True:
                path=[visited_vertex] + path
                if visited_vertex == start_vertex:
                    break
                visited_vertex=near[visited_vertex]

        return path, length

    def find_shortest_path_with_road(self, start_vertex, end_vertex, block_vertices=[], block_edges=[]):
        # find the shortest path from start_vertex to end_vertex 
        #    in graph with dijkstra algorithm 
        graph=self.iGraph_dict
        vertex_list=list(graph.keys())
        path=[]
        length=-1
        visited=[]
        dist={}
        turn={}
        near={}
        road={}
        # for vertex in graph:
        for vertex in graph.keys():
            if vertex == start_vertex:
                dist[vertex]=0
                turn[vertex]=[0]
                near[vertex]=[start_vertex]
                road[vertex]=['']
            else:
                dist[vertex]=-1
                turn[vertex]=[]
                near[vertex]=[]
                road[vertex]=[]

        # dijkstra algorithm
        while end_vertex not in visited:
            if self.debug:
                print(dist)
                print(turn)
                print(near)
                print(road)
                print(visited)
                print("")

            # find nearest vertex
            min_dist=-1
            min_vertex=''
            for vertex in vertex_list:
                if (vertex not in visited) and (dist[vertex] != -1):
                    if (dist[vertex] <= min_dist) or (min_dist == -1):
                        min_dist=dist[vertex]
                        min_vertex=vertex
            if min_dist == -1:
                break

            # update corresponding branch length
            min_road_index=0
            # for vertex in graph[min_vertex]:
            for vertex in graph[min_vertex].keys():
                if vertex not in visited:
                    if vertex not in block_vertices and (min_vertex, vertex) not in block_edges: # check if vertex or edge is blocked
                        for i in range(len(road[min_vertex])):
                            gp=road[min_vertex][i]
                            # if (graph[min_vertex][vertex].length + dist[min_vertex] + 1*(gp!=graph[min_vertex][vertex].road) < dist[vertex]) or (dist[vertex] == -1):
                            if (graph[min_vertex][vertex]['length'] + dist[min_vertex] + 1*(gp!=graph[min_vertex][vertex]['road']) < dist[vertex]) or (dist[vertex] == -1):
                                dist[vertex]=graph[min_vertex][vertex]['length'] + dist[min_vertex] + 1*(gp!=graph[min_vertex][vertex]['road'])
                                turn[vertex]=[turn[min_vertex][i] + 1*(gp!=graph[min_vertex][vertex]['road'])]
                                near[vertex]=[min_vertex]
                                road[vertex]=[graph[min_vertex][vertex]['road']]
                                min_road_index=i
                            elif (graph[min_vertex][vertex]['length'] + dist[min_vertex] + 1*(gp!=graph[min_vertex][vertex]['road']) == dist[vertex]):
                                turn[vertex].append(turn[min_vertex][i] + 1*(gp!=graph[min_vertex][vertex]['road']))
                                near[vertex].append(min_vertex)
                                road[vertex].append(graph[min_vertex][vertex]['road'])

            # add to visited list
            visited.append(min_vertex)

        # generating shortest path if exists
        if end_vertex in visited:
            length=dist[end_vertex]
            visited_vertex=end_vertex
            visited_road_index=turn[end_vertex].index(min(turn[end_vertex]))
            visited_road=road[end_vertex][visited_road_index]
            while True:
                path=[visited_vertex] + path
                if visited_vertex == start_vertex:
                    break
                visited_road_index=0
                for i in range(len(road[visited_vertex])):
                    if road[visited_vertex][i] == visited_road:
                        visited_road_index=i
                visited_road=road[visited_vertex][visited_road_index]
                visited_vertex=near[visited_vertex][visited_road_index]
            length -= turn[end_vertex][0]
        return path, length

    def score(self, start_vertex, end_vertex):
        """ return the h score with start_vertex and end_vertex """
        return 0

    def find_shortest_path_A_star(self, start_vertex, end_vertex, block_vertices=[], block_edges=[], score_func=None):
        """ find the shortest path from start_vertex to end_vertex 
            in graph with A* algorithm """

        # if score_func is None:
        #     score_func=self.score
        q=mp.Queue()
        # p=mp.Process(target=mp_func, args=(q, start_vertex, end_vertex, block_vertices, block_edges, self.iGraph_dict, score_func))
        p=mp.Process(target=mp_func_with_C, args=(q, start_vertex, end_vertex, block_vertices, block_edges, self.iGraph_dict))
        
        p.start()
        p.join()

        result_path=q.get()
        result_length=q.get()

        threading.current_thread().result=result_path, result_length
        return result_path, result_length

        

    def find_shortest_path_A_star_with_road(self, start_vertex, end_vertex, block_vertices=[], block_edges=[], score_func=None, weight=1):
        """ find the shortest path from start_vertex to end_vertex 
            in graph with A* algorithm """
        # if score_func is None:
        #     score_func=self.score
        # graph=self.iGraph_dict

        begin_tick=time.time()

        q=mp.Queue()
        # p=mp.Process(target=mp_func2, args=(q, start_vertex, end_vertex, block_vertices, block_edges, weight, self.iGraph_dict, score_func))
        p=mp.Process(target=mp_func2_with_C, args=(q, start_vertex, end_vertex, block_vertices, block_edges, weight, self.iGraph_dict))

        p.start()
        p.join()
        

        result_path=q.get()
        result_length=q.get()

        end_tick=time.time()
        elapsed_time='%.3f sec'%(end_tick-begin_tick)
        print('=>find_shortest_path_A_star_with_road:',start_vertex, end_vertex, elapsed_time, result_length)
        threading.current_thread().result=result_path, result_length
        return result_path, result_length

    def get_path_cost(self, path):
        length=0
        graph=self.iGraph_dict
        try:
            for i in range(len(path)-1):
                # length += graph[path[i]][path[i+1]].length
                length += graph[path[i]][path[i+1]]['length']
        except KeyError:
            length=-1
        return length

    def is_connected(self, 
                     vertices_encountered=None, 
                     start_vertex=None):
        """ determines if the graph is connected """
        if vertices_encountered is None:
            vertices_encountered=set()
        gdict=self.iGraph_dict        
        vertices=list(gdict.keys()) # "list" necessary in Python 3 
        if not start_vertex:
            # chosse a vertex from graph as a starting point
            start_vertex=vertices[0]
        vertices_encountered.add(start_vertex)
        if len(vertices_encountered) != len(vertices):
            for vertex in gdict[start_vertex].keys():
                if vertex not in vertices_encountered:
                    if self.is_connected(vertices_encountered, vertex):
                        return True
        else:
            return True
        return False

    def vertex_degree(self, vertex):
        """ The degree of a vertex is the number of edges connecting
            it, i.e. the number of adjacent vertices. Loops are counted 
            double, i.e. every occurence of vertex in the list 
            of adjacent vertices. """ 
        adj_vertices= list(self.iGraph_dict[vertex].keys())
        degree=len(adj_vertices) + adj_vertices.count(vertex)
        return degree

    def degree_sequence(self):
        """ calculates the degree sequence """
        seq=[]
        for vertex in self.iGraph_dict:
            seq.append(self.vertex_degree(vertex))
        seq.sort(reverse=True)
        return tuple(seq)

    @staticmethod
    def is_degree_sequence(sequence):
        """ Method returns True, if the sequence "sequence" is a 
            degree sequence, i.e. a non-increasing sequence. 
            Otherwise False is returned.
        """
        # check if the sequence sequence is non-increasing:
        return all( x>=y for x, y in zip(sequence, sequence[1:]))
  

    def delta(self):
        """ the minimum degree of the vertices """
        min=100000000
        for vertex in self.iGraph_dict:
            vertex_degree=self.vertex_degree(vertex)
            if vertex_degree < min:
                min=vertex_degree
        return min
        
    def Delta(self):
        """ the maximum degree of the vertices """
        max=0
        for vertex in self.iGraph_dict:
            vertex_degree=self.vertex_degree(vertex)
            if vertex_degree > max:
                max=vertex_degree
        return max

    def density(self):
        """ method to calculate the density of a graph """
        g=self.iGraph_dict
        V=len(g.keys())
        E=len(self.edges(loop=False))
        return E / (V *(V - 1))

    def diameter(self):
        """ calculates the diameter of the graph """
        
        v=self.vertices() 
        pairs=[ (v[i],v[j]) for i in range(len(v)) for j in range(len(v)) if i != j]
        diameter=-1
        for (s,e) in pairs:
            path, length=self.find_shortest_path_A_star(s,e)
            if length > diameter:
                diameter=length

        # longest path is at the end of list, 
        # i.e. diameter corresponds to the length of this path
        return diameter

    @staticmethod
    def erdoes_gallai(dsequence):
        """ Checks if the condition of the Erdoes-Gallai inequality 
            is fullfilled 
        """
        if sum(dsequence) % 2:
            # sum of sequence is odd
            return False
        if Graph.is_degree_sequence(dsequence):
            for k in range(1,len(dsequence) + 1):
                left=sum(dsequence[:k])
                right= k * (k-1) + sum([min(x,k) for x in dsequence[k:]])
                if left > right:
                    return False
        else:
            # sequence is increasing
            return False
        return True

class Graph(BaseGraph):
    def __init__(self, graph_dict=None):
        super(Graph, self).__init__(graph_dict)
        pass

    def add_node(self, node):
        self.add_vertex(node)


    def add_edge(self, from_node, to_node, length, bidirection=True, Reversed=False): #Sean: 23/03/23
        super(Graph, self).add_edge(from_node, to_node, length, bidirection)
        if Reversed: #Sean: 23/03/23
            super(Graph, self).add_edge(to_node, from_node, int(length*1.2), bidirection=False)

    def get_a_route(self, source, dest, block_nodes=[], block_edges=[], score_func=None, algo='', weight=1000, timeout=30): #p1,p2
        '''block_nodes_convert=[]
        for node in block_nodes:
            block_nodes_convert.append(tools.convert(node))
        block_edges_convert=[]
        for edge in block_edges:
            block_edges_convert.append((tools.convert(edge[0]), tools.convert(edge[1])))'''

        #print('get_a_route', from_point, dest)
        if source == dest:
            #return False, []
            return 0, [source, dest]

        if algo == 'A*WithRoad':
            # path, cost=self.find_shortest_path_A_star_with_road(source, dest, block_vertices=block_nodes, block_edges=block_edges, score_func=score_func, weight=weight)
            th=Thread(target=self.find_shortest_path_A_star_with_road, args=(source, dest,), kwargs={'block_vertices':block_nodes, 'block_edges':block_edges, 'score_func':score_func, 'weight':weight,})
        else:
            # path, cost=self.find_shortest_path_A_star(source, dest, block_vertices=block_nodes, block_edges=block_edges, score_func=score_func)
            th=Thread(target=self.find_shortest_path_A_star, args=(source, dest,), kwargs={'block_vertices':block_nodes, 'block_edges':block_edges, 'score_func':score_func,})
        th.setDaemon(True)
        th.start()
        for i in range(timeout):
            time.sleep(1)
            if not th.is_alive():
                path, cost = th.result
                break
        else:
            path, cost = [], -2
            pass # raise exception
        return cost, path

def mp_func(q, start_vertex, end_vertex, block_vertices, block_edges, graph, score_func):
    # def score_func(start_v, end_v):
    #     return 0
    vertex_list=list(graph.keys())
    path=[]
    length=-1
    visited=[]
    dist={}
    near={}
    h_score={}
    h_score[start_vertex]=score_func(start_vertex, end_vertex)
    # h_score[start_vertex]=0
    for vertex in graph.keys():
        if vertex == start_vertex:
            dist[vertex]=0
            near[vertex]=start_vertex
        else:
            dist[vertex]=-1
            near[vertex]=''
    # A star algorithm
    while end_vertex not in visited:
        # if self.debug:
            # print(dist)
            # print(near)
            # print(h_score)
            # print(visited)
            # print("")

        # find lowest f score of vertex
        min_dist=-1
        min_h_score=0
        min_vertex=''
        for vertex in vertex_list:
            if (vertex not in visited) and (dist[vertex] != -1):
                if vertex not in h_score:
                    h_score[vertex]=score_func(vertex, end_vertex)
                    # h_score[vertex]=0
                if ((dist[vertex] + h_score[vertex] < min_dist + min_h_score) or (min_dist == -1)):
                    min_dist=dist[vertex]
                    min_vertex=vertex
                    min_h_score=h_score[vertex]
        if min_dist == -1:
            break

        # update corresponding branch length
        for vertex in graph[min_vertex].keys():
            if vertex not in visited:
                if vertex not in block_vertices and (min_vertex, vertex) not in block_edges: # check if vertex or edge is blocked
                    if (graph[min_vertex][vertex]['length'] + dist[min_vertex] < dist[vertex]) or (dist[vertex] == -1):
                        dist[vertex]=graph[min_vertex][vertex]['length'] + dist[min_vertex]
                        near[vertex]=min_vertex

        # add to visited list
        visited.append(min_vertex)

    # generating shortest path if exists
    if end_vertex in visited:
        length=dist[end_vertex]
        visited_vertex=end_vertex
        while True:
            path=[visited_vertex] + path
            if visited_vertex == start_vertex:
                break
            visited_vertex=near[visited_vertex]
    q.put(path)
    q.put(length)

def mp_func_with_C(q, start_vertex, end_vertex, block_vertices, block_edges, graph):
    start_t=time.time()
    mapping={}
    reverse_mapping={}
    path=[]
    length=-1

    nodes=list(graph.keys())
    if start_vertex not in nodes or end_vertex not in nodes:
        q.put([])
        q.put(-1)
        return

    dist_list=[]
    for i, FP in enumerate(nodes):
        mapping[i]=FP
        reverse_mapping[FP]=i
        d=c_edge()
        for j, TP in enumerate(nodes):
            if FP != TP:
                dist=graph[FP].get(TP, {}).get('length', -1)
                d.dist[j]=dist
            else:
                d.dist[j]=0
        dist_list.append(d)
    
    dist_array=(c_edge * len(dist_list))(*dist_list)

    block_vertices_list=c_edge()
    for i in range(len(block_vertices)):
        if block_vertices[i] in nodes:
            block_vertices_list.dist[i]=reverse_mapping[block_vertices[i]]

    block_edges_list=[]
    for i in range(len(block_edges)):
        temp=c_edge()
        for j in range(len(block_edges[i])):
            if block_edges[i][j] in nodes:
                temp.dist[j]=reverse_mapping[block_edges[i][j]]
        block_edges_list.append(temp)
    block_edges_array=(c_edge * len(block_edges_list))(*block_edges_list)
    end_t=time.time()
    print('data prepare done: %.3f sec'%(end_t - start_t))

    s_t=time.time()
    libc=CDLL("./algorithm/lib/lib/mp_lib.so")
    libc.test.argtypes=POINTER(c_edge), POINTER(c_edge), POINTER(c_edge), c_int, c_int, c_int, c_int, c_int
    libc.test.restype=c_int
    length=libc.test(dist_array, block_vertices_list, block_edges_array, len(dist_list), len(block_vertices), len(block_edges), reverse_mapping[start_vertex], reverse_mapping[end_vertex])
    if block_vertices_list.dist[0] == -1:
        q.put([])
        q.put(-1)

    else:
        for i in range(block_vertices_list.dist[0]):
            path=[mapping[block_vertices_list.dist[i + 1]]] + path
        q.put(path)
        q.put(length)
    e_t=time.time()
    print('calculate done: %.3f sec'%(e_t - s_t))

def mp_func2(q, start_vertex, end_vertex, block_vertices, block_edges, weight, graph, score_func):
    # def score_func(start_v, end_v):
    #     return 0
    vertex_list=list(graph.keys())
    path=[]
    length=-1
    visited=[]
    dist={}
    turn={}
    near={}
    road={}
    h_score={}
    h_score[start_vertex]=score_func(start_vertex, end_vertex)
    # for vertex in graph:
    for vertex in graph.keys():
        if vertex == start_vertex:
            dist[vertex]=0
            turn[vertex]=[0]
            near[vertex]=[start_vertex]
            road[vertex]=['']
        else:
            dist[vertex]=-1
            turn[vertex]=[]
            near[vertex]=[]
            road[vertex]=[]

    # A star algorithm
    while end_vertex not in visited:
        # if self.debug:
        #     print(dist)
        #     print(turn)
        #     print(near)
        #     print(road)
        #     print(h_score)
        #     print(visited)
         #     print("")

        # find lowest f score of vertex
        min_dist=-1
        min_h_score=0
        min_vertex=''
        for vertex in vertex_list:
            if (vertex not in visited) and (dist[vertex] != -1):
                if vertex not in h_score:
                    h_score[vertex]=score_func(vertex, end_vertex)
                if ((dist[vertex] + h_score[vertex] < min_dist + min_h_score) or (min_dist == -1)):
                    min_dist=dist[vertex]
                    min_vertex=vertex
                    min_h_score=h_score[vertex]
        if min_dist == -1:
            break

        # update corresponding branch length
        min_road_index=0
        # for vertex in graph[min_vertex]:
        for vertex in graph[min_vertex].keys():
            if vertex not in visited:
                if vertex not in block_vertices and (min_vertex, vertex) not in block_edges: # check if vertex or edge is blocked
                    for i in range(len(road[min_vertex])):
                        gp=road[min_vertex][i]
                        if (graph[min_vertex][vertex]['length'] + dist[min_vertex] + weight*(gp!=graph[min_vertex][vertex]['road']) < dist[vertex]) or (dist[vertex] == -1):
                            dist[vertex]=graph[min_vertex][vertex]['length'] + dist[min_vertex] + weight*(gp!=graph[min_vertex][vertex]['road'])
                            turn[vertex]=[turn[min_vertex][i] + 1*(gp!=graph[min_vertex][vertex]['road'])]
                            near[vertex]=[min_vertex]
                            road[vertex]=[graph[min_vertex][vertex]['road']]
                            min_road_index=i
                        elif (graph[min_vertex][vertex]['length'] + dist[min_vertex] + weight*(gp!=graph[min_vertex][vertex]['road']) == dist[vertex]):
                            turn[vertex].append(turn[min_vertex][i] + 1*(gp!=graph[min_vertex][vertex]['road']))
                            near[vertex].append(min_vertex)
                            road[vertex].append(graph[min_vertex][vertex]['road'])

        # add to visited list
        visited.append(min_vertex)

    # generating shortest path if exists
    if end_vertex in visited:
        length=dist[end_vertex]
        visited_vertex=end_vertex
        visited_road_index=turn[end_vertex].index(min(turn[end_vertex]))
        visited_road=road[end_vertex][visited_road_index]
        while True:
            path=[visited_vertex] + path
            if visited_vertex == start_vertex:
                break
            visited_road_index=0
            for i in range(len(road[visited_vertex])):
                if road[visited_vertex][i] == visited_road:
                    visited_road_index=i
            visited_road=road[visited_vertex][visited_road_index]
            visited_vertex=near[visited_vertex][visited_road_index]
        length -= turn[end_vertex][0]
    q.put(path)
    q.put(length)

def mp_func2_with_C(q, start_vertex, end_vertex, block_vertices, block_edges, weight, graph):
    mapping={}
    reverse_mapping={}
    path=[]
    length=-1

    road_map=[]
    road_map.append('')

    nodes=list(graph.keys())
    if start_vertex not in nodes or end_vertex not in nodes:
        q.put([])
        q.put(-1)
        return

    dist_list=[]
    road_list=[]
    for i, FP in enumerate(nodes):
        mapping[i]=FP
        reverse_mapping[FP]=i
        d=c_edge()
        r=c_edge()
        for j, TP in enumerate(nodes):
            if FP != TP:
                dist=graph[FP].get(TP, {}).get('length', -1)
                d.dist[j]=dist

                if dist == -1:
                    r.dist[j]=-1
                else:
                    if graph[FP][TP]['road'] not in road_map:
                        road_map.append(graph[FP][TP]['road'])
                    r.dist[j]=road_map.index(graph[FP][TP]['road'])
            else:
                d.dist[j]=0
                r.dist[j]=0
        dist_list.append(d)
        road_list.append(r)

    dist_array=(c_edge * len(dist_list))(*dist_list)
    road_array=(c_edge * len(road_list))(*road_list)

    block_vertices_list=c_edge()
    for i in range(len(block_vertices)):
        if block_vertices[i] in nodes:
            block_vertices_list.dist[i]=reverse_mapping[block_vertices[i]]

    block_edges_list=[]
    for i in range(len(block_edges)):
        temp=c_edge()
        for j in range(len(block_edges[i])):
            if block_edges[i][j] in nodes:
                temp.dist[j]=reverse_mapping[block_edges[i][j]]
        block_edges_list.append(temp)
    block_edges_array=(c_edge * len(block_edges_list))(*block_edges_list)

    libc=CDLL("./algorithm/lib/mp_lib2.so")
    libc.test.argtypes=POINTER(c_edge), POINTER(c_edge), POINTER(c_edge), c_int, c_int, c_int, c_int, c_int, POINTER(c_edge), c_int
    libc.test.restype=c_int
    length=libc.test(dist_array, block_vertices_list, block_edges_array, len(dist_list), len(block_vertices), len(block_edges), reverse_mapping[start_vertex], reverse_mapping[end_vertex], road_array, weight)
    if block_vertices_list.dist[0] == -1:
        q.put([])
        q.put(-1)

    else:
        for i in range(block_vertices_list.dist[0]):
            path=[mapping[block_vertices_list.dist[i + 1]]] + path
        q.put(path)
        q.put(length)

if __name__ == '__main__':
    graph=Graph()

    for node in ['A', 'B', 'C', 'D', 'E']:
        graph.add_node(node)

    graph.add_edge('A', 'B', 1)
    graph.add_edge('B', 'C', 1)
    graph.add_edge('C', 'D', 1)
    graph.add_edge('D', 'B', 3)
    graph.add_edge('E', 'D', 1)
    graph.add_edge('A', 'E', 3)
    graph.add_edge('A', 'D', 6)
    # print(graph.__str__())
    print(graph.get_a_route('A', 'D')) # output: (3, ['A', 'B', 'C', 'D'])