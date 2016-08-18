import re
import socket
import networkx as nx
import subprocess
import random
import json
import numpy as np
from poprouting import ComputeTheoreticalValues
from graph_generator import Gen
import matplotlib.pyplot as plt


class PrinceTestOONF:
    '''
    Generate a topology in netjson format and send it to a client
    type: type of topology generated: 0 CN, 1 PLAW, 2 MESH
    cs: clientsocket object
    N: nubmer of nodes of the topology
    '''
    def genG(self, type, cs, N):
        T = int(N * 1.2)
        E = N * 1.8
        ge = Gen()
        if type == 0:
            ge.genCNGraph(N)
        if type == 1:
            ge.genGraph("PLAW", N)
        if type == 2:
            ge.genMeshGraph(N, 23)
        self.graph = ge.graph
        self.netjson = ge.composeNetJson(self.graph)
        self.json_netjson = json.dumps(self.netjson)
        self.h_py, self.tc_py = self.calculateTimers()
        print ("sending graph")
        print cs.send(self.json_netjson)
        cs.close()

    '''
    Calculate timers using the poprouting function CalculateTheoreticalValues
    and choose the one that matches our "router_id"
    '''
    def calculateTimers(self):
        # compute the timers values using the poprouting python lib
        ctv = ComputeTheoreticalValues(graph=self.graph)
        hello_py = tc_py = 0
        # search for the timer we are calculating (the 'router_id' one)
        for node in ctv.node_list:
            if node == self.netjson['router_id']:
                hello_py = ctv.Hi[node]
                tc_py = ctv.TCi[node]
        return hello_py, tc_py
    '''
    Run a test without heuristic
    type: see below
    N: number of nodes
    iter: number of batch tests
    '''
    def test_noh(self, type, N, iter):
        ''' type = 0    CN
            type = 1    PLAW
            type = 2    MESH
        '''

        ''' listen to the port 2010 to emulate a oonf's daemon.
            when prince connect it reply with the netjson and then wait for the
            optimized timers
        '''
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('localhost', 2010))
        serversocket.listen(5)
        # regular expression to catch the timers' values
        p = re.compile(r"\d*\.\d+")
        tc_cpp = 0
        executions = []
        hs = []
        tcs = []
        # run the test 'iter' times
        while iter:
            # accept connections and receive the request
            (cs, address) = serversocket.accept()
            data = cs.recv(1024).decode("utf-8")
            # simulate the oonf's netjson command to get the topology
            if data.strip() == "/netjsoninfo filter graph ipv6_0/quit":
                # generate the graph, calculate timers(python) and push topology to prince
                self.genG(type, cs, N)

            else:
                # search for the timers' values using the regex
                if data:
                    toks = p.findall(data)  # match the regex
                    if toks:
                        tc_cpp = float(toks[0])
                        hello_cpp = float(toks[1])
                        exec_time = float(toks[2])
                        ''' calculate the percentage difference between the
                        expected and the reference values, then append this values in a list
                        '''
                        p_tc = abs(tc_cpp - self.tc_py) / ((tc_cpp + self.tc_py) / 2) * 100
                        p_h = abs(hello_cpp - self.h_py) / ((hello_cpp + self.h_py) / 2) * 100
                        hs.append(p_h)
                        tcs.append(p_tc)
                        executions.append(exec_time)
                        print "node: " + str(self.netjson['router_id'])
                        print "       " + "C++  " + "Python" + "              " + "Percent"
                        print "tc:    " + repr(tc_cpp) + "   " + repr(self.tc_py) + " " + str(p_tc)
                        print "hello: " + repr(hello_cpp) + "   " + repr(self.h_py) + " " + str(p_h)
                        cs.close()
                        iter = iter - 1
        measures = {}
        measures['exec_mean'] = np.mean(executions)
        measures['exec_var'] = np.std(executions)
        measures['h_mean'] = np.mean(hs)
        measures['tc_mean'] = np.mean(tcs)
        measures['h_var'] = np.std(hs)
        measures['tc_var'] = np.std(tcs)
        print "Average execution time with " + str(N) + " nodes is " + str(measures['exec_mean']) + "s   variance: " + str(measures['exec_var'])
        print "Average tc difference is " + str(measures['tc_mean']) + " variance: " + str(measures['tc_var'])
        print "Average h difference is " + str(measures['h_mean']) + " variance: " + str(measures['h_var'])
        return measures
    '''
    Run a test with the heuristic
    type: see below
    N: number of nodes
    iter: number of batch tests
    '''
    def test(self, type, N, iter):
        ''' type = 0    CN
            type = 1    PLAW
            type = 2    MESH
        '''
        ''' listen to the port 2009 to emulate a oonf's daemon.
            when prince connect it reply with the netjson and then wait for the optimized timers
        '''
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('localhost', 2009))
        serversocket.listen(5)
        # regular expression to catch the timers' values
        p = re.compile(r"\d*\.\d+")
        tc_cpp = 0
        executions = []
        hs = []
        tcs = []
        while iter:
            # accept connections
            (cs, address) = serversocket.accept()
            data = cs.recv(1024).decode("utf-8")
            # simulate the oonf's netjson command to get the topology
            if data.strip() == "/netjsoninfo filter graph ipv6_0/quit":
                # generate the graph, calculate timers(python) and push topology to prince
                self.genG(type, cs, N)

            else:
                # search for the timers' values using the regex
                if data:
                    toks = p.findall(data)
                    if toks:
                        tc_cpp = float(toks[0])
                        hello_cpp = float(toks[1])
                        exec_time = float(toks[2])
                        p_tc = abs(tc_cpp - self.tc_py) / ((tc_cpp + self.tc_py) / 2) * 100
                        p_h = abs(hello_cpp - self.h_py) / ((hello_cpp + self.h_py) / 2) * 100
                        hs.append(p_h)
                        tcs.append(p_tc)
                        print "node: " + str(self.netjson['router_id'])
                        print "       " + "C++  " + "Python" + "              " + "Percent"
                        print "tc:    " + repr(tc_cpp) + "   " + repr(self.tc_py) + " " + str(p_tc)
                        print "hello: " + repr(hello_cpp) + "   " + repr(self.h_py) + " " + str(p_h)
                        executions.append(exec_time)
                        cs.close()
                        iter = iter - 1
        measures = {}
        measures['exec_mean'] = np.mean(executions)
        measures['exec_var'] = np.std(executions)
        measures['h_mean'] = np.mean(hs)
        measures['tc_mean'] = np.mean(tcs)
        measures['h_var'] = np.std(hs)
        measures['tc_var'] = np.std(tcs)
        print "Average execution time with " + str(N) + " nodes is " + str(measures['exec_mean']) + "s   variance: " + str(measures['exec_var'])
        print "Average tc difference is " + str(measures['tc_mean']) + " variance: " + str(measures['tc_var'])
        print "Average h difference is " + str(measures['h_mean']) + " variance: " + str(measures['h_var'])
        return measures


p = PrinceTestOONF()
# initialize the lists
measures_plaw_noh = []
measures_plaw = []
measures_plaw_noh_var = []
measures_plaw_var = []
x = []
sample = 20
max = 500
# run prince w & w/o heuristic
proc_noh = subprocess.Popen("exec ../../build/prince ../../input/test_noh.ini", shell=True)
proc = subprocess.Popen("exec ../../build/prince ../../input/test.ini", shell=True)

# cycle till the max values
for i in range(1, (max / sample) + 1):
    size = sample * i
    # run tests with and w/o heuristic
    t = p.test(1, size, 5)
    tnoh = p.test_noh(1, size, 5)
    # append the values in lists to plot them
    measures_plaw_noh.append(tnoh['exec_mean'])
    measures_plaw_noh_var.append(tnoh['exec_var'])
    measures_plaw.append(t['exec_mean'])
    measures_plaw_var.append(t['exec_var'])
    x.append(size)

# plot the values and the error bars with pyplot
plt.errorbar(x, measures_plaw_noh, yerr=measures_plaw_noh_var)
plt.errorbar(x, measures_plaw, yerr=measures_plaw_var)
plt.xlabel('size of graph (nodes)')
plt.ylabel('execution time (s)')
plt.show()