import multiprocessing as mp
import time

import numpy as np
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn import preprocessing 

from accuracy import test_acc_svm
from bssa import BSSA
from myplot import plot_cost_accuracy
from pickable_us import UPDATE_STRATEGIES as us

import matplotlib.pyplot as plt
import main
import logging

from dataset import load_dataset, replace_none_with_zero
from dataset import load_mice, load_hepatitis, load_epileptic

import pickle
#parameters
iterations = 20
sync_iter = 5
pop_size = 20
ub = 1
lb = 0

logger = logging.getLogger("main.mp__main")

#Load dataset
#breast cancer dataset
dataset = datasets.load_breast_cancer()
dataset.data = preprocessing.scale(dataset.data)
x_train, x_test, y_train, y_test = train_test_split(dataset.data, dataset.target, test_size = 0.2, random_state=42)

#hepatit
data_x, data_y = load_hepatitis()
data_x = replace_none_with_zero(data_x)
data_x = preprocessing.scale(data_x)
x_train, x_test, y_train, y_test = train_test_split(data_x, data_y, test_size = 0.2, random_state=42)

#Diabetes
dataset = datasets.load_diabetes()
dataset.data = preprocessing.scale(dataset.data)
x_train, x_test, y_train, y_test = train_test_split(dataset.data, dataset.target, test_size = 0.2, random_state=42)

#mice
x, y = load_mice()
x = preprocessing.scale(x)
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.2, random_state=42)

#epileptic
x, y = load_epileptic()
x = preprocessing.scale(x)
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.2, random_state=42)

#Set and define parameter
problem_dim = len(x_train[0])

def tf(x):
    return 1/(1+np.exp(-x))
strategies = ["TCSSA2", "TCSSA2", "TCSSA2", "TCSSA2"]
sub_chains = ["S1", "S2", "S3", "S4"]

#Define bssa object
bssa_list = []
for st, su in zip(strategies, sub_chains):
    bssa_list.append(BSSA(pop_size, problem_dim, tf, ub, lb, us[st][su]))
    
def train_bssa(in_object_q, out_object_q, iter_num):
    bssa = pickle.loads(in_object_q.get())
    bssa.train(iter_num, x_train, y_train, x_test, y_test)
    out_object_q.put(pickle.dumps(bssa))


#Train
t = time.time()
for i in range(iterations//sync_iter):
    p_l = []
    #Create q for send and recv object to process
    send_q_l = []
    recv_q_l = []
    for bssa in bssa_list:
        send_q_l.append(mp.Queue())
        recv_q_l.append(mp.Queue())
    #Create process
    for bssa, s, r in zip(bssa_list, send_q_l, recv_q_l):
        s.put(pickle.dumps(bssa))
        p = mp.Process(target = train_bssa, args=(s, r, sync_iter, ))
        p.start()
        p_l.append(p)
    #Wait for reading
    bssa_list = []
    for r in recv_q_l:
        bssa_list.append(pickle.loads(r.get()))
    
    bssa_list = sorted(bssa_list, key= lambda x: x.get_best_cost())
    for bssa in bssa_list[1:]:
        bssa.replace_with_worst_salp(bssa_list[0].get_best_salp())
    logger.info("The best salp of each bssa replaced with worst one")

logger.info("Time = {}".format(time.time() - t))

for bssa, i in zip(bssa_list, range(len(bssa_list))):
    plot_cost_accuracy(bssa, problem_dim)
sf = bssa_list[0].get_best_salp().get_position()
print("Test accuracy = {}".format(test_acc_svm(list(sf), x_test, y_test, x_train, y_train)))
plt.show()
