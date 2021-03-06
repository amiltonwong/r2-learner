import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelBinarizer
from sklearn.base import BaseEstimator, clone
from scipy import linalg as la

def _elm_vectorized_rbf(X, W, B):
    WS = np.array([np.sum(np.multiply(W,W), axis=0)])
    XS = np.array([np.sum(np.multiply(X,X), axis=1)]).T[0,:]
    return np.exp(-np.multiply(B, -2*X.dot(W) + WS + XS))


def _elm_sigmoid(X, W, B):
    return 1.0/(1.0  + np.exp(-(X.dot(W) + B)))


class ELM(BaseEstimator):

    def __init__(self, h=60, activation='linear', random_state=None, C=100):
        self.name = 'elm'
        self.h = h
        self.activation = activation
        self.random_state = random_state
        self.C = C

        assert self.activation in ['rbf', 'sigmoid', 'linear']

    def fit(self, X, y):

        if self.random_state is None:
            self.random_state = np.random.RandomState(np.random.randint(0, np.iinfo(np.int32).max))
        elif type(self.random_state) == int:
            self.random_state = np.random.RandomState(self.random_state)

        self.lb = LabelBinarizer()
        self.W = self.random_state.normal(size=(X.shape[1], self.h))
        self.B = self.random_state.normal(size=self.h)

        if self.activation == 'rbf':
            H = _elm_vectorized_rbf(X, self.W, self.B)
        elif self.activation == 'sigmoid':
            H = _elm_sigmoid(X, self.W, self.B)
        else :
            H = X.dot(self.W)

        self.lb.fit(y)

        lam = np.eye(H.shape[1]) * (1./self.C)
        H_inv = np.linalg.inv(H.T.dot(H) + lam)
        self.beta = H_inv.dot(H.T.dot(self.lb.transform(y)))

        return self


    def decision_function(self, X):
        if self.activation == 'rbf':
            return _elm_vectorized_rbf(X, self.W, self.B).dot(self.beta)
        elif self.activation == 'sigmoid':
            return _elm_sigmoid(X, self.W, self.B).dot(self.beta)
        else :
            return X.dot(self.W).dot(self.beta)


    def predict(self, X):
        return self.lb.inverse_transform(self.decision_function(X))
