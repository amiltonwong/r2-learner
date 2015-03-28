#!/usr/bin/env python

import sys, os
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data_api import fetch_uci_datasets
from sklearn.grid_search import ParameterGrid
from multiprocessing import Pool

from fit_models import k_fold
from r2 import R2ELMLearner, R2SVMLearner, R2LRLearner
import time
from data_api import *


# assert len(sys.argv) > 1
#
# names = sys.argv[1:]
# print names
# datasets = fetch_uci_datasets(names)

datasets = fetch_uci_datasets(['diabetes'])

n_jobs = 16

lmao_r2svm_params = {'beta': [0.1, 0.5, 1.0, 1.5, 2.0],
                     'depth': [i for i in xrange(1,11)],
                     'fit_c': ['random'],
                     'scale': [True, False],
                     'recurrent': [True, False],
                     'use_prev': [True, False],
                     'seed': [666],
                     'fixed_prediction': [1]}

random_r2svm_params = {'beta': [0.1, 0.5, 1.0, 1.5, 2.0],
                       'depth': [i for i in xrange(1,11)],
                       'fit_c': ['random_cls'],
                       'scale': [True, False],
                       'recurrent': [True, False],
                       'use_prev': [True, False],
                       'seed': [666]}

centered_random_r2svm_params = {'beta': [0.1, 0.5, 1.0, 1.5, 2.0],
                                'depth': [i for i in xrange(1,11)],
                                'fit_c': ['random_cls_centered'],
                                'scale': [True, False],
                                'recurrent': [True, False],
                                'use_prev': [True, False],
                                'seed': [666]}

switched_r2elm_params = {'h': [i for i in xrange(20,101,20)],
                         'beta': [0.1, 0.5, 1.0, 1.5, 2.0],
                         'depth': [i for i in xrange(1,11)],
                         'activation': ['01_rbf'],
                         'fit_c': ['random'],
                         'scale': [True, False],
                         'recurrent': [True, False],
                         'use_prev': [True, False],
                         'seed': [666],
                         'switched': [True]}

exp_params = [{'model': R2SVMLearner(), 'params': lmao_r2svm_params, 'exp_name': 'lmao', 'model_name': 'r2svm'},
              {'model': R2SVMLearner(), 'params': random_r2svm_params, 'exp_name': 'random', 'model_name': 'r2svm'},
              {'model': R2SVMLearner(), 'params': centered_random_r2svm_params, 'exp_name': 'center_random', 'model_name': 'r2svm'},
              {'model': R2ELMLearner(), 'params': switched_r2elm_params, 'exp_name': 'switched', 'model_name': 'r2elm'}]


def gen_params():
    for data in datasets:
        for r in exp_params:
            param_list = ParameterGrid(r['params'])
            for param in param_list:
                yield {'model': r['model'], 'params': param, 'data': data,
                       'name': r['exp_name'], 'model_name': r['model_name']}

params = list(gen_params())

def run(p):
    try:
        k_fold(base_model=p['model'], params=p['params'], data=p['data'], exp_name=p['name'],
           model_name=p['model_name'], all_layers=False)
    except:
        print p['model']
        print traceback.format_exc()


# for i, p in enumerate(params):
#     run(p)
#     print "done %i/%i with %s" % (i, len(params), p['model_name'])

pool = Pool(n_jobs)
rs = pool.map_async(run, params, 1)

while True:
    if rs.ready():
        break
    remaining = rs._number_left
    print "Waiting for", remaining, "tasks to complete"
    time.sleep(3)
