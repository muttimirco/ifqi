import numpy as np
import gym
from builtins import range
import time


class Environment(gym.Env):
    def __init__(self):
        self.gamma = 1
        self.horizon = None

    def _eval_and_render(self, policy, nbEpisodes=1, metric='discounted', render=True):
        """
        This function evaluate a policy on the specified metric by executing
        multiple episode and visualize its performance
        Params:
            policy (object): a policy object (method drawAction is expected)
            nbEpisodes (int): the number of episodes to execute
            metric (string): the evaluation metric ['discounted', 'average']
        Return:
            metric (float): the selected evaluation metric
            confidence (float): 95% confidence level for the provided metric
        """
        fps = self.metadata.get('video.frames_per_second') or 100
        values = np.zeros(nbEpisodes)
        gamma = self.gamma
        if metric == 'average':
            gamma = 1
        for e in range(nbEpisodes):
            epPerformance = 0.0
            df = 1
            t = 0
            done = False
            if render:
                self.render(mode='human')
            state = self.reset()
            while (t < self.horizon) and (not done):
                action = policy.drawAction(state)
                state, r, done, _ = self.step(action)
                epPerformance += df * r
                df *= gamma
                t += 1

                if render:
                    self.render()
                    time.sleep(1.0 / fps)
            if gamma == 1:
                epPerformance /= t
            values[e] = epPerformance
        return values.mean(), 2 * values.std() / np.sqrt(nbEpisodes)

    def _parallel_eval(self, policy, nbEpisodes, metric):
        #TODO using joblib
        return self._eval_and_render(policy, nbEpisodes, metric, False)

    def evaluate(self, policy, nbEpisodes=1, metric='discounted', render=False):
        """
        This function evaluate a policy on the specified metric by executing
        multiple episode.
        Params:
            policy (object): a policy object (method drawAction is expected)
            nbEpisodes (int): the number of episodes to execute
            metric (string): the evaluation metric ['discounted', 'average']
            render (bool): flag indicating whether to visualize the behavior of
                            the policy
        Return:
            metric (float): the selected evaluation metric
            confidence (float): 95% confidence level for the provided metric
        """
        assert metric in ['discounted', 'average'], "unsupported metric for evaluation"
        if render:
            return self._eval_and_render(policy, nbEpisodes, metric, True)
        else:
            return self._parallel_eval(policy, nbEpisodes, metric)

# class Environment(object):
#     """
#     Environment abstract class.
#
#     """
#     __metaclass__ = ABCMeta
#
#     @abstractmethod
#     def __init__(self):
#         """
#         Constructor.
#
#         """
#         # Properties
#         self.stateDim = None
#         self.actionDim = None
#         self.discreteStates = None
#         self.discreteActions = None
#         self.horizon = None
#         # End episode
#         self._isEpisodic = False
#         self._atGoal = None
#         self._absorbing = None
#         # Discount factor
#         self.gamma = None
#
#     @abstractmethod
#     def evaluate(self, fqi, expReplay=False, render=False):
#         """
#         This function evaluates the regressor in the provided object parameter.
#         Params:
#             fqi (object): an object containing the trained regressor
#             expReplay (bool): flag indicating whether to do experience replay
#             render (bool): flag indicating whether to render visualize behavior
#                            of the agent
#         Returns:
#             J
#
#         """
#         pass
#
#     def collect(self, policy=None):
#         """
#         This function can be used to collect a dataset from the environment
#         using a given policy.
#
#         Params:
#             policy (object): an object that can be evaluated in order to get
#                              an action
#
#         Returns:
#             - a dataset composed of:
#                 - a flag indicating the beginning of an episode
#                 - state
#                 - action
#                 - reward
#                 - next state
#                 - a flag indicating wheter the reached state is absorbing
#         """
#         self._reset()
#         t = 0
#         data = list()
#         action = None
#         while (t < self.horizon) and (not self._isAbsorbing()):
#             state = self._getState()
#             if policy:
#                 action = policy.predict(state)
#                 if isinstance(action, tuple):
#                     action = action[0]
#             else:
#                 action = np.random.choice(np.arange(self.nActions))
#             reward = self._step(action)
#             nextState = self._getState()
#             t += 1
#
#             if not self._isAbsorbing():
#                 if t < self.horizon:
#                     newEl = [0] + state + [action, reward] + nextState + [0]
#                 else:
#                     newEl = [1] + state + [action, reward] + nextState + [0]
#             else:
#                 newEl = [1] + state + [action, reward] + nextState + [1]
#
#             data.append(newEl)
#
#         return np.array(data)
#
#     def runEpisode(self, fqi, expReplay, render=False):
#         """
#         This function runs an episode using the regressor in the provided
#         object parameter.
#         Args:
#             fqi (object): an object containing the trained regressor
#             expReplay (bool): flag indicating whether to do experience replay
#             render (bool): flag indicating whether to render visualize behavior
#                            of the agent
#         Returns:
#             - J
#             - number of steps
#             - a flag indicating if the goal state has been reached
#             - augmented training set (if using experience replay)
#             - augmented target set (if using experience replay)
#
#         """
#         J = 0
#         t = 0
#         testSuccessful = 0
#
#         # reset the environment (draw a random initial state)
#         self._reset()
#         if expReplay:
#             stateList = list()
#             actionList = list()
#             rewardList = list()
#             df = 1.0
#             while (t < self.horizon) and (not self._isAbsorbing()):
#                 state = self._getState()
#                 stateList.append(state)
#                 action, _ = fqi.predict(np.array(state))
#                 actionList.append(action)
#                 r = self._step(int(action[0]), render=render)
#                 rewardList.append(r)
#                 J += df * r
#                 t += 1
#                 df *= self.gamma
#
#             if self._isAtGoal():
#                 testSuccessful = 1
#                 print("Goal reached")
#             else:
#                 print("Failure")
#
#             state = self._getState()
#             stateList.append(state)
#
#             s = np.array(stateList)
#             a = np.array(actionList)
#             s1 = s[1:]
#             s = s[:-1]
#             t = np.array([[0] * (s.shape[0] - 1) + [1]]).T
#             r = np.array(rewardList)
#             sast = np.concatenate((s, a, s1, t), axis=1)
#
#             return J, t, testSuccessful, sast, r
#         else:
#             df = 1.0
#             while (t < self.horizon) and (not self._isAbsorbing()):
#                 state = self._getState()
#                 action, _ = fqi.predict(np.array(state))
#                 r = self._step(action, render=render)
#                 J += df * r
#                 t += 1
#                 df *= self.gamma
#
#             if self._isAtGoal():
#                 testSuccessful = 1
#                 print("Goal reached")
#             else:
#                 print("Failure")
#
#             return J, t, testSuccessful
#
#     @abstractmethod
#     def _step(self, u, render=False):
#         """
#         This function performs the step function of the environment.
#         Args:
#             u (int): the id of the action to be performed.
#         Returns:
#             the new state and the obtained reward
#
#         """
#         pass
#
#     @abstractmethod
#     def _reset(self, state=None):
#         """
#         This function set the current state to the initial state
#         and reset flags.
#         Args:
#             state (np.array): the initial state
#
#         """
#         pass
#
#     @abstractmethod
#     def _getState(self):
#         """
#         Returns:
#             a tuple containing the current state.
#
#         """
#         pass
#
#     def _isAbsorbing(self):
#         """
#         Returns:
#             True if the state is absorbing, False otherwise.
#
#         """
#         return self._absorbing
#
#     def _isAtGoal(self):
#         """
#         Returns:
#             True if the state is a goal state, False otherwise.
#
#         """
#         return self._atGoal
#
#     def _isEpisodic(self):
#         """
#         Returns:
#             True if it is an episodic problem, false otherwise
#
#         """
#         return self._isEpisodic
#
#     def _discreteAction(self):
#         """
#         Returns:
#              None if the problem is a continuous problem
#         """
#
#     def getDiscreteActions(self):
#         return range(self.nActions)