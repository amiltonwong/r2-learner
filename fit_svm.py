from models import R2SVMLearner
from misc.experiment_utils import get_exp_logger

from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import KFold
from sklearn.metrics import accuracy_score, confusion_matrix

import time
import numpy as np

# TODO: do something with those 2 different config types
# TODO: figure out how to get rid of the deprecation warnigngs

def fit_grid(data, config, logger=None):
    """
    Fits a GridSearchCV class from scikit-learn
    :param data: dict-like with fields: name, data, target
    :param config: dictionary with parameters specific for a grid search
    :param logger: logger class
    :return: dictionary Experiment with gird results
    """
    assert hasattr(data, 'name')
    assert hasattr(data, 'data')
    assert hasattr(data, 'target')
    assert ['experiment_type', 'param_grid','scoring', 'fit_c', 'cv', 'refit', 'store_clf'] <= config.keys()
    assert config['experiment_type'] == 'grid'
    ### Prepare result holders ###
    results = {}
    monitors = {}

    E = {"config": config, "results": results, "monitors": monitors}

    model = R2SVMLearner()
    cv_grid = GridSearchCV(model, param_grid=config['param_grid'], scoring=config['scoring'], n_jobs=-1, \
                           fit_params={'fit_c': config['fit_c']}, cv=config['cv'])

    start_time = time.time()
    X = data.data
    Y = data.target
    cv_grid.fit(X, Y)

    monitors['grid_time'] = time.time() - start_time

    results['best_params'] = cv_grid.best_params_
    results['best_score'] = cv_grid.best_score_
    if config['refit'] :
        results['best_cls'] = R2SVMLearner(**cv_grid.best_params_).fit(X,Y)
    else :
        results['best_cls'] = cv_grid.best_estimator_

    monitors['mean_fold_scores'] = [s[1] for s in cv_grid.grid_scores_]
    monitors['std_fold_scores'] = [np.std(s[2]) for s in cv_grid.grid_scores_]
    monitors['best_std'] = [ np.std(s[2]) for s in cv_grid.grid_scores_ if s[1] == cv_grid.best_score_ ]

    if config['store_clf'] :
        monitors['clf'] = cv_grid

    if logger is not None :
        logger.info(results)
        logger.info(monitors)

    return E

def fit_r2svm(data, config, logger=None) :
    """
    Fits R2SVMLearner class on
    :param data: dict-like with fields: name, data, target
    :param config: dictionary with parameters specific for a k-fold fitting
    :param logger: logger class
    :return: dictionary Experiment with cross validation results results
    """
    assert hasattr(data, 'name')
    assert hasattr(data, 'data')
    assert hasattr(data, 'target')
    assert ['experiment_type', 'n_folds', 'fold_seed', 'params', 'store_clf', 'fit_c'] <= config.keys()
    assert config['experiment_type'] == 'k-fold'

    ### Prepare result holders ###b
    results = {}
    monitors = {}
    E = {"config": config, "results": results, "monitors": monitors}

    monitors["acc_fold"] = []
    monitors["train_time"] = []
    monitors["test_time"] = []
    monitors["cm"] = [] # confusion matrix
    monitors["clf"] = []

    X, Y = data.data, data.target
    folds = KFold(n=X.shape[0], n_folds=config['n_folds'], shuffle=True, random_state=config['fold_seed'])
    for train_index, test_index in folds :
        X_train, X_test, Y_train, Y_test = X[train_index], X[test_index], Y[train_index], Y[test_index]

        model = R2SVMLearner(**config['params'])
        train_start = time.time()
        model.fit(X_train, Y_train, fit_c=config['fit_c'])
        monitors['train_time'].append(time.time() - train_start)

        if config['store_clf'] :
            monitors['clf'].append(model)

        test_start = time.time()
        Y_predicted = model.predict(X_test)
        monitors['test_time'] = time.time() - test_start

        monitors['acc_fold'].append(accuracy_score(Y_test, Y_predicted))
        monitors['cm'].append(confusion_matrix(Y_test, Y_predicted))

    monitors["acc_fold"] = np.array(monitors["acc_fold"])
    monitors['std'] = monitors['acc_fold'].std()
    monitors['n_dim'] = data.n_dim
    monitors['n_class'] = data.n_class
    monitors['data_name'] = data.name

    results["mean_acc"] = monitors["acc_fold"].mean()

    if logger is not None :
        logger.info(results)
        logger.info(monitors)

    return E


def fit_grid_default(data):
    """Fits a exhausting grid search with default parameters on a data set, return dictionary with results"""

    config = {'experiment_type': 'grid',
                  'param_grid': default_grid_parameters(),
                  'n_fold': 3,
                  'scoring': 'accuracy',
                  'store_clf': False,
                  'seed': None,
                  'experiment_name': 'default grid experiment on ' + data.name}

    assert hasattr(data, 'name')
    assert hasattr(data, 'data')
    assert hasattr(data, 'target')

    return  fit_grid(config, data.data, data.target)

def fit_on_dataset(data, param_grid_in=None, grid_config_in=None, fold_config_in=None, to_file=False):

    param_grid = default_grid_parameters()
    if param_grid_in is not None :
        param_grid.update(param_grid_in)

    grid_config = {'experiment_name': 'grid_search_on_' + data.name,
                   'experiment_type': 'grid',
                   'refit': True,
                   'scoring': 'accuracy',
                   'fit_c': False, # this can be a list, ex. [True, False], also, True makes this experiment way longer
                   'cv': KFold(n=data.data.shape[0], n_folds=5),
                   'store_clf': False,
                   'param_grid': param_grid}

    if grid_config_in is not None :
        grid_config.update(grid_config_in)

    logger = get_exp_logger(grid_config, to_file=to_file)

    E_grid = fit_grid(data, grid_config, logger)
    params = E_grid['results']['best_params']

    fold_config = {'experiment_name': 'k-fold_testing_on_' + data.name,
                   'experiment_type': 'k-fold',
                   'n_folds': 5,
                   'fit_c': E_grid['config']['fit_c'],
                   'fold_seed': None,
                   'store_clf': True,
                   'params': params}

    if fold_config_in is not None :
        fold_config.update(fold_config_in)

    logger.name = fold_config['experiment_name']

    return E_grid, fit_r2svm(data, fold_config, logger)

def default_grid_parameters() :
    return { 'C': [10**i for i in xrange(-2,6)],
             'beta': [0.02 * i for i in xrange(0,11)],
             'depth': [5],
             'scale': [True],
             'recurrent': [True],
             'use_prev': [True],
             'seed': [None]}