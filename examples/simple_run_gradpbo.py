import numpy as np

from ifqi import envs
from ifqi.evaluation import evaluation
from ifqi.evaluation.utils import check_dataset, split_dataset, split_data_for_fqi
from ifqi.models.regressor import Regressor
from ifqi.algorithms.pbo.gradpbo import GradPBO

from keras.models import Sequential
from keras.layers import Dense
from matplotlib import pyplot as plt

"""
Simple script to quickly run pbo. It solves the LQG environment.

"""

np.random.seed(6652)

mdp = envs.LQG1D()
mdp.seed(2897270658018522815)
state_dim, action_dim, reward_dim = envs.get_space_info(mdp)
reward_idx = state_dim + action_dim
discrete_actions = np.linspace(-8, 8, 20)
dataset = evaluation.collect_episodes(mdp, n_episodes=100)
check_dataset(dataset, state_dim, action_dim, reward_dim)

INCREMENTAL = False
ACTIVATION = 'sigmoid'


# sast, r = split_data_for_fqi(dataset, state_dim, action_dim, reward_dim)

### Q REGRESSOR ##########################
class LQG_Q(object):
    def model(self, s, a, omega):
        b = omega[:, 0]
        k = omega[:, 1]
        q = - b * b * s * a - 0.5 * k * a * a - 0.4 * k * s * s
        return q.ravel()

    def n_params(self):
        return 2

    def get_k(self, omega):
        b = omega[:, 0]
        k = omega[:, 1]
        return - b * b / k

    def name(self):
        return "R1"


q_regressor = LQG_Q()
##########################################

### F_RHO REGRESSOR ######################
n_q_regressors_weights = q_regressor.n_params()
Sequential.n_inputs = lambda self: n_q_regressors_weights

rho_regressor = Sequential()
rho_regressor.add(Dense(20, input_dim=n_q_regressors_weights, init='uniform', activation=ACTIVATION))
rho_regressor.add(Dense(n_q_regressors_weights, init='uniform', activation='linear'))
rho_regressor.compile(loss='mse', optimizer='rmsprop', metrics=['accuracy'])
# rho_regressor.fit(None, None)
##########################################

### PBO ##################################
pbo = GradPBO(bellman_model=rho_regressor,
              q_model=q_regressor,
              discrete_actions=discrete_actions,
              gamma=mdp.gamma,
              optimizer="adam",
              state_dim=state_dim,
              action_dim=action_dim, incremental=INCREMENTAL)
state, actions, reward, next_states = split_dataset(dataset,
                                                    state_dim=state_dim,
                                                    action_dim=action_dim,
                                                    reward_dim=reward_dim)
theta0 = np.array([6., 0.001], dtype='float32').reshape(1, -1)
history = pbo.fit(state, actions, next_states, reward, theta0,
                  batch_size=10, nb_epoch=2,
                  theta_metrics={'k': lambda theta: q_regressor.get_k(theta)})
##########################################
# Evaluate the final solution
initial_states = np.array([[1, 2, 5, 7, 10]]).T
values = evaluation.evaluate_policy(mdp, pbo, initial_states=initial_states)
print(values)

##########################################
# Some plot
ks = np.array(history.hist['k']).squeeze()
weights = np.array(history.hist['theta']).squeeze()

plt.figure()
plt.title('[train] evaluated weights')
plt.scatter(weights[:, 0], weights[:, 1], s=50, c=np.arange(weights.shape[0]),
            cmap='viridis', linewidth='0')
plt.xlabel('b')
plt.ylabel('k')
plt.colorbar()
plt.savefig(
    'LQG_MLP_{}_evaluated_weights_incremental_{}_activation_{}.png'.format(q_regressor.name(), INCREMENTAL, ACTIVATION),
    bbox_inches='tight')

plt.figure()
plt.plot(ks[30:-1])
plt.xlabel('iteration')
plt.ylabel('coefficient of max action (opt ~0.6)')
plt.savefig(
    'LQG_MLP_{}_max_coeff_{}_activation_{}.png'.format(q_regressor.name(), INCREMENTAL, ACTIVATION),
    bbox_inches='tight')


theta = theta0.copy()
L = [np.array(theta)]
for i in range(4000):
    theta = pbo.apply_bop(theta)
    L.append(np.array(theta))

L = np.array(L).squeeze()
print(L.shape)

print(theta)
print('K: {}'.format(q_regressor.get_k(theta)))

plt.figure()
plt.scatter(L[:, 0], L[:, 1])
plt.title('Application of Bellman operator')
plt.xlabel('b')
plt.ylabel('k')
plt.savefig(
    'LQG_MLP_{}_bpo_application_incremental_{}_activation_{}.png'.format(q_regressor.name(), INCREMENTAL, ACTIVATION),
    bbox_inches='tight')
#plt.show()


# best_rhos = pbo._rho_values[-1]
# q_w = np.array([4, 8])
# L = [q_w]
# for _ in range(10):
#     q_w = pbo._f2(best_rhos, q_w)
#     print(-q_w[1] ** 2 / q_w[0])
#     L.append(q_w)
# L = np.array(L)
# plt.figure()
# plt.scatter(L[:, 0], L[:, 1], s=50, c=np.arange(L.shape[0]), cmap='inferno')
#
# B_i, K_i = np.meshgrid(np.linspace(-10, 11, 20), np.linspace(-10, 11, 20))
# B_f = np.zeros(B_i.shape)
# K_f = np.zeros(K_i.shape)
# for i in range(B_i.shape[0]):
#     for j in range(K_i.shape[0]):
#         B_f[i, j], K_f[i, j] = pbo._f2(best_rhos, np.array([B_i[i, j], K_i[i, j]]))
#
# fig = plt.figure(figsize=(15, 10))
# Q = plt.quiver(B_i, K_i, B_f - B_i, K_f - K_i, angles='xy')
# plt.axis([-10, 10, -10, 10])
# plt.xlabel('b')
# plt.ylabel('k')
# plt.title('Theta vector field')
#
# plt.show()