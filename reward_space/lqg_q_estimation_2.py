from __future__ import print_function
from ifqi.envs import LQG1D
from ifqi.evaluation import evaluation
import numpy as np
from numpy import linalg as LA
import ifqi.envs as envs

from policy import GaussianPolicy1D
from utils import add_discount, chebvalNd, MinMaxScaler
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


class ContinuousEnvSampleEstimator(object):
    tol = 1e-24  # to avoid divisions by zero

    def __init__(self, dataset, gamma):

        '''
        Works only for discrete mdps.
        :param dataset: numpy array (n_samples,7) of the form
            dataset[:,0] = current state
            dataset[:,1] = current action
            dataset[:,2] = reward
            dataset[:,3] = next state
            dataset[:,4] = discount
            dataset[:,5] = a flag indicating whether the reached state is absorbing
            dataset[:,6] = a flag indicating whether the episode is finished (absorbing state
                           is reached or the time horizon is met)
        :param gamma: discount factor
        '''
        self.dataset = dataset
        self.gamma = gamma
        self.n_samples = dataset.shape[0]
        self._estimate()

    def _estimate(self):
        states = self.dataset[:, 0]
        actions = self.dataset[:, 1]
        next_states = self.dataset[:, 3]
        discounts = self.dataset[:, 4]

        n_episodes = 0

        d_sa_mu = np.zeros(self.n_samples)
        d_sasa = np.zeros((self.n_samples,self.n_samples))
        d_sasa_mu = np.zeros((self.n_samples,self.n_samples))

        i = 0
        while i < self.n_samples:
            j = i

            d_sa_mu[i] += discounts[i]

            if i == 0 or self.dataset[i - 1, -1] == 1:
                n_episodes += 1

            while j < self.n_samples and self.dataset[j, -1] == 0:
                d_sasa[i,j] += discounts[j] / discounts[i]
                d_sasa_mu[i,j] += discounts[j]
                j += 1

            if j < self.n_samples:
                d_sasa[i,j] += discounts[j] / discounts[i]
                d_sasa_mu[i,j] += discounts[j]

            i += 1

        d_sa_mu /= n_episodes
        d_sasa_mu /= n_episodes

        self.d_sa_mu = d_sa_mu
        self.d_sasa = d_sasa
        self.d_sasa_mu = d_sasa_mu

        self.J = 1.0 / n_episodes * np.sum(self.dataset[:, 2] * self.dataset[:, 4])


def compute_feature_matrix(n_samples, n_features, states, actions, features):
    '''
    Computes the feature matrix X starting from the sampled data and
    the feature functions

    :param n_samples: number of samples
    :param n_features: number of features
    :param states: the states encountered in the run
    :param actions: the actions performed in the run
    :param features: a list of functions, each one is a feature
    :return: X the feature matrix n_samples x n_features
    '''
    X = np.zeros(shape=(n_samples,n_features))
    for i in range(n_samples):
        for j in range(n_features):
            X[i,j] = features[j]([states[i], actions[i]])
    return X

def remove_projections(X, C, W):
    '''
    Makes the columns of matrix X orthogonal to the columns of
    matrix C, based on the weighted inner product with weights W
    '''
    P_cx = LA.multi_dot([C.T, W, X])
    P_cc = LA.multi_dot([C.T, W, C])
    C_norms2 = np.diag(np.diag(P_cc)) 
    P_cx_n = (np.power(C_norms2,-1)).dot(P_cx)
    X_ort = X - C.dot(P_cx_n) 
    return X_ort

def find_basis(X, w):
    '''
    Finds an orthonormal basis for the space of the columns of matrix X
    based on the weighted inner product with weights w
    '''

    W = np.diag(w)
    W_inv = np.diag(np.power(w,-1))
    
    X_tilda_ort = np.sqrt(W).dot(X)
    U_ort, s_ort, V_ort = LA.svd(X_tilda_ort)
    tol = s_ort.max() * max(X_ort.shape) * np.finfo(s_ort.dtype).eps    #as done in numpy
    U_tilda_ort_ort = U_ort[:,:s_ort.shape[0]][:,s_ort > tol] 
    U_ort_ort = np.sqrt(W_inv).dot(U_tilda_ort_ort)
    return U_ort_ort

'''
def compute_k_opt(mdp, n_episodes, discount_factor, k_min, k_max, k_step):
    _range = np.arange(k_min, k_max, k_step)
    grad_J_vec = np.zeros(len(_range))
    print('Finding the best parameter')
    for i,k in enumerate(_range):
        policy = GaussianPolicy1D(k, sigma)
        mdp.reset()
        dataset = evaluation.collect_episodes(mdp, policy, n_episodes)
        dataset = add_discount(dataset, 5, discount_factor)
        states_actions = dataset[:, :2]
        states = dataset[:, 0]
        actions = dataset[:, 1]
        discounts = dataset[:, -1]
        rewards = dataset[:, 2]
        n_samples = 100 * n_episodes

        complement = [lambda x: policy.gradient_log_pdf(x[0], x[1])]
        n_complement = 1
        n_samples = dataset.shape[0]
        C = compute_feature_matrix(n_samples, n_complement, states, actions, complement)
        Q_true = np.array(map(lambda s, a: mdp.computeQFunction(s, a, K, np.power(sigma, 2)), states, actions))

        W = np.diag(discounts)

        grad_J_true = 1.0 / n_episodes * LA.multi_dot([C.T, W, Q_true])
        grad_J_vec[i] = grad_J_true
        J_hat = 1.0 / n_episodes * np.sum(rewards * discounts)

        print('mu = %f grad_J = %f, J=%f' % (k, grad_J_true, J_hat))
    best = _range[np.argmin(np.abs(grad_J_vec))]
    print('The best parameter is %f' % best)
    return best
'''

def estimate_Q(X, Q_true):
    '''
    Performs LS estimation of the Q function starting from the orthonormal
    basis X and the target Q_true
    '''
    w, residuals, rank, _ =  LA.lstsq(X, Q_true)
    rmse = np.sqrt(residuals/X.shape[0])
    Q_hat = X.dot(w)
    return Q_hat, w, rmse

mdp = LQG1D()

#MDP parameters
discount_factor = mdp.gamma
horizon = mdp.horizon
max_action = mdp.max_action
max_pos = mdp.max_pos
state_dim, action_dim, reward_dim = envs.get_space_info(mdp)

#Policy parameters
K = mdp.computeOptimalK()
sigma = 0.01

policy = GaussianPolicy1D(K,sigma)

#Collect samples
n_episodes = 20
dataset = evaluation.collect_episodes(mdp, policy, n_episodes)
dataset = dataset[(np.arange(500,1000) + np.arange(0,20000,1000)[:,np.newaxis]).ravel()]

estimator = ContinuousEnvSampleEstimator(dataset, mdp.gamma)

states_actions = dataset[:,:2]
states = dataset[:,0]
actions = dataset[:,1]
discounts = dataset[:,4]
rewards = dataset[:,2]

print('Dataset (sigma %f) has %d samples' % (sigma, dataset.shape[0]))

#Scale data
bounds = [[-max_pos, max_pos], [-max_action ,max_action]]
scaler = MinMaxScaler(ndim=2, input_ranges=bounds)
scaled_states_actions = scaler.scale(states_actions)
scaled_states = scaled_states_actions[:,0]
scaled_actions = scaled_states_actions[:,1]

#Compute feature matrix    
complement = [lambda x : policy.gradient_log_pdf(x[0],x[1])]
max_degree = 5
degrees = [[ds,da] for ds in range(max_degree+1) for da in range(max_degree+1)]
cheb_basis = map(lambda d: lambda x: chebvalNd(x, d), degrees)

n_samples = dataset.shape[0]
n_features = len(cheb_basis)
n_complement = 1

X = compute_feature_matrix(n_samples, n_features, scaled_states, scaled_actions, cheb_basis)
C = compute_feature_matrix(n_samples, n_complement, states, actions, complement)

W = estimator.d_sasa_mu
X_ort = remove_projections(X, C, W)
#X_ort = remove_projections(X, C, np.diag(discounts)) 
#Non mi interessa che sia ortonormale!!!
#X_ort_ort = find_basis(X_ort, np.diag(discounts))
#print('Rank of feature matrix X %s/%s' % (X_ort_ort.shape[1], X.shape[1]))

rewards_hat, w, rmse = estimate_Q(X_ort, rewards)
error = np.abs(rewards - rewards_hat)
mae = np.mean(error)
error_rel = np.abs((rewards - rewards_hat)/rewards)
mare = np.mean(error_rel)


grad_J_true = 1.0/n_episodes * LA.multi_dot([C.T, W, rewards])
grad_J_hat = 1.0/n_episodes * LA.multi_dot([C.T, W, rewards])
J_hat = 1.0/n_episodes * np.sum(rewards * discounts)
print('Results of LS rmse = %s mae = %s mare = %s' % (rmse, mae, mare))
print('True policy gradient %s' % grad_J_true)
print('Estimated policy gradient %s' % grad_J_hat)
print('Estimated expected return %s' % J_hat)

'''

#---------------------------Q-function evaluation-----------------------------
Q_true = np.array(map(lambda s,a: mdp.computeQFunction(s, a, K, np.power(sigma,2)), states, actions))
Q_hat, w, rmse = estimate_Q(X_ort_ort, Q_true)
error = np.abs(Q_true - Q_hat)
mae = np.mean(error)
error_rel = np.abs((Q_true - Q_hat)/Q_true)
mare = np.mean(error_rel)

W = np.diag(discounts)

grad_J_true = 1.0/n_episodes * LA.multi_dot([C.T, W, Q_true])
grad_J_hat = 1.0/n_episodes * LA.multi_dot([C.T, W, Q_hat])
J_hat = 1.0/n_episodes * np.sum(rewards * discounts)
print('Results of LS rmse = %s mae = %s mare = %s' % (rmse, mae, mare))
print('True policy gradient %s' % grad_J_true)
print('Estimated policy gradient %s' % grad_J_hat)
print('Estimated expected return %s' % J_hat)

#-------------------------Plot------------------------------------------------
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(states, actions, Q_true, c='r', marker='o')
ax.scatter(states, actions, Q_hat, c='b', marker='^')
ax.set_xlabel('s')
ax.set_ylabel('a')
ax.set_zlabel('Q(s,a)')

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(states, actions, error, c='g', marker='*')
ax.set_xlabel('s')
ax.set_ylabel('a')
ax.set_zlabel('error(s,a)')

fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(states, error, c='g', marker='*')
ax.set_xlabel('s')
ax.set_ylabel('|Q_true(s,*) - Q_hat(s,*)|')

fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(states, error_rel, c='g', marker='*')
ax.set_xlabel('s')
ax.set_ylabel('|Q_true(s,*) - Q_hat(s,*)|/|Q_true(s,*)|')

fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(states[:n_episodes], Q_true[:n_episodes], c='r', marker='o')
ax.scatter(states[:n_episodes], Q_hat[:n_episodes], c='b', marker='^')
ax.set_xlabel('s')
ax.set_ylabel('Q(s,*)')

fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(actions[:n_episodes], Q_true[:n_episodes], c='r', marker='o')
ax.scatter(actions[:n_episodes], Q_hat[:n_episodes], c='b', marker='^')
ax.set_xlabel('a')
ax.set_ylabel('Q(*,a)')

fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(states[:n_episodes], error_rel[:n_episodes], c='g', marker='*')
ax.set_xlabel('s')
ax.set_ylabel('|Q_true(s,*) - Q_hat(s,*)|/|Q_true(s,*)|')

plt.show()
'''