from reportlab.graphics.widgetbase import Face

from numpy.matlib import rand

import psutil
import threading
from time import sleep
import json
import numpy as np
from ctypes import cdll,c_double,py_object
from graph_generator import Gen
import datetime as dt
import networkx as nx
import random
from heapq import heappush, heappop
from itertools import count
import networkx as nx
import random


class CPUThread(threading.Thread):
    def __init__(self):
        super(CPUThread, self).__init__()
        self.usage=[]
        self.active=True
    def run(self):
        while self.active:
            self.usage.append(psutil.cpu_percent(interval=1))
            sleep(1)


def run_fun(f,n,h,w):
    t=CPUThread()
    t.start()
    elapsed_time=fun(n,h,w)
    t.active=False;
    t.join()
    print("data",np.mean(t.usage),elapsed_time)


#@profile
def compute(lib):
    lib.compute();

def fun(node_num,h,w):
        ge = Gen()
        ge.genGraph("PLAW", node_num)
        g=ge.graph

        s=json.dumps(ge.composeNetJson(g))
        lib_n='./libtest_cpp.so'
        if h==1:
            lib_n='./libtest_c.so'
        lib = cdll.LoadLibrary(lib_n)
        lib.get_res.restype=py_object
        lib.init(w);
        lib.parse(s);
        n1=dt.datetime.now()
        compute(lib)
        elapsed_time = (dt.datetime.now()-n1).microseconds
        elapsed_time=elapsed_time
        res=lib.get_res()

        print(dict(map(lambda (k,v): (k, round(v,8)), nx.betweenness_centrality(g,endpoints=True).iteritems()))==dict(map(lambda (k,v): (k, round(v,8)), res.iteritems())))
        print(nx.betweenness_centrality(g,endpoints=True))
        print(res)
        lib.destroy();
        return elapsed_time


import sys
args=sys.argv[1:]
#nodenum=int(args[0])
#is_c=int(args[1])
#heu=int(args[2])
#run_fun(fun,nodenum,is_c,heu)

#run_fun(fun,nodenum,1,0)
#run_fun(fun,nodenum,1,1)


#new

nodenum=7



def betweenness_centrality(G, k=None, normalized=True, weight=None,
                           endpoints=False,
                           seed=None):

    betweenness = dict.fromkeys(G, 0.0)  # b[v]=0 for v in G
    if k is None:
        nodes = G
    else:
        random.seed(seed)
        nodes = random.sample(G.nodes(), k)
    for s in nodes:
        # single source shortest paths
        S, P, sigma = _single_source_dijkstra_path_basic(G, s, weight)
        # accumulation
        betweenness = _accumulate_endpoints(betweenness, S, P, sigma, s)
    betweenness = _rescale(betweenness, len(G),normalized=normalized,directed=G.is_directed(),k=k)
    return betweenness


def _single_source_dijkstra_path_basic(G, s, weight='weight'):
    # modified from Eppstein
    S = []
    P = {}
    for v in G:
        P[v] = []
    sigma = dict.fromkeys(G, 0.0)    # sigma[v]=0 for v in G
    D = {}
    sigma[s] = 1.0
    push = heappush
    pop = heappop
    seen = {s: 0}
    c = count()
    Q = []   # use Q as heap with (distance,node id) tuples
    push(Q, (0, next(c), s, s))
    while Q:
        (dist, _, pred, v) = pop(Q)
        if v in D:
            continue  # already searched this node.
        sigma[v] += sigma[pred]  # count paths
        S.append(v)
        D[v] = dist
        for w, edgedata in G[v].items():
            vw_dist = dist + edgedata.get(weight, 1)
            if w not in D and (w not in seen or vw_dist < seen[w]):
                seen[w] = vw_dist
                push(Q, (vw_dist, next(c), v, w))
                sigma[w] = 0.0
                P[w] = [v]
            elif vw_dist == seen[w]:  # handle equal paths
                sigma[w] += sigma[v]
                P[w].append(v)
    return S, P, sigma


def _accumulate_endpoints(betweenness, S, P, sigma, s):
    betweenness[s] += len(S) - 1
    #print(s,' len ', len(S),(S))
    delta = dict.fromkeys(S, 0)
    while S:
        w = S.pop()
        coeff = (1.0 + delta[w]) / sigma[w]
        #print("======================")
        #print ('coeff for'+str(s)+":"+str(coeff))
        for v in P[w]:
            delta[v] += sigma[v] * coeff
        if w != s:
            #print ('@> ret_val'+str(w)+":"+str(delta[w]))
            betweenness[w] += delta[w] + 1
    #print(s,betweenness[s])
    return betweenness


def _rescale(betweenness, n, normalized, directed=False, k=None):
    if normalized is True:
        if n <= 2:
            scale = None  # no normalization b=0 for all nodes
        else:
            scale = 1.0 / ((n - 1) * (n - 2))
    else:  # rescale by 2 for undirected graphs
        if not directed:
            scale = 1.0 / 2.0
        else:
            scale = None
    if scale is not None:
        if k is not None:
            scale = scale * n / k
        for v in betweenness:
            betweenness[v] *= scale
    return betweenness


b=True
i=0
r=random.Random(1555)
while b and i <50:
    i+=1
    ge = Gen()
    ge.genGraph("PLAW", nodenum)
    g=ge.graph
    g2=nx.Graph()
    for e in g.edges():
        g2.add_edge(e[0],e[1],weight=r.uniform(0,10))
    g=g2
    #el=[(0, 17), (0, 12), (0, 13), (1, 3), (1, 11), (1, 15), (2, 17), (3, 18), (3, 11), (3, 12), (3, 10), (4, 6), (5, 17), (7, 18), (7, 10), (8, 17), (9, 15), (11, 18), (11, 17), (12, 17), (12, 18), (14, 17), (15, 17), (16, 17), (17, 18), (18, 19)]
    #g=nx.from_edgelist(el)
    #g=nx.Graph()
    #for i,e in enumerate(el):
    #    g.add_edge(e[0],e[1],weight=r.uniform(0,10))


    s=json.dumps(ge.composeNetJson(g))

    lib_n='./libtest_c.so'
    lib = cdll.LoadLibrary(lib_n)
    lib.get_res.restype=py_object
    lib.init(0);
    lib.parse(s);
    n1=dt.datetime.now()
    compute(lib)
    res=lib.get_res()
    lib.destroy()
    b=b and (dict(map(lambda (k,v): (k, round(v,8)), betweenness_centrality(g,endpoints=True, weight="weight").iteritems()))==dict(map(lambda (k,v): (k, round(v,8)), res.iteritems())))
    #print(betweenness_centrality(g,endpoints=True, weight="weight"))
    #print("b",res)
    lib = cdll.LoadLibrary(lib_n)
    lib.get_res.restype=py_object
    lib.init(1);
    lib.parse(s);
    n1=dt.datetime.now()
    compute(lib)
    res=lib.get_res()
    lib.destroy()
    b=b and (dict(map(lambda (k,v): (k, round(v,8)), betweenness_centrality(g,endpoints=True, weight="weight").iteritems()))==dict(map(lambda (k,v): (k, round(v,8)), res.iteritems())))
    if not b:
        print( betweenness_centrality(g,endpoints=True, weight="weight"))
        print(res)
        for e in g.edges(data='weight'):
            print('add_edge_graph(&g1,"'+str(e[0])+'","'+str(e[1])+'",'+str(e[2])+',0);')
        for e in g.edges(data='weight'):
            print('{"source": "'+str(e[0])+'","target": "'+str(e[1])+'","cost": '+str(e[2])+'},')
        sys.exit(-1)