import json

from gym import spaces
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.tree import DecisionTreeRegressor
from models.mlp import MLP
from sklearn.linear_model import LinearRegression
from models.ensemble import Ensemble
from models.actionregressor import ActionRegressor
from models.regressor import Regressor
from envs.carOnHill import CarOnHill
from envs.invertedPendulum import InvPendulum
from envs.acrobot import Acrobot
from envs.bicycle import Bicycle
from envs.swingPendulum import SwingPendulum
from envs.swingUpPendulum import SwingUpPendulum
from envs.cartPole import CartPole
from envs.lqg1d import LQG1D
from envs.lunarLander import LunarLander
import ifqi.envs as envs
import envs.utils as spaceInfo
from ifqi.fqi.FQI import FQI
import warnings

import numpy as np


class Experiment(object):
    """
    This class has the purpose to load the configuration
    file of the experiment and return the required model
    and mdp.

    """
    def __init__(self, configFile=None):
        """
        Constructor.
        Args:
            config_file (str): the name of the configuration file.

        """
        if configFile is not None:
            with open(configFile) as f:
                self.config = json.load(f)

            self.mdp = self.getMDP()
        else:
            self.config = dict()

    def getModelName(self, nRegressor):
        modelConfig = self.config['regressors'][nRegressor]
        return modelConfig['modelName']

    def getFitParams(self,nRegressor):
        return self.config['regressors'][nRegressor]["supervisedAlgorithm"]

    def getActions(self):
        return self.config['mdp']['discreteActions']

    def getMDP(self, seed=None):
        if not hasattr(self, "mdp"):
            """
            This function loads the mdp required in the configuration file.
            Returns:
                the required mdp.
            """
            if self.config['mdp']['mdpName'] == 'CarOnHill':
                self.mdp = CarOnHill()
            elif self.config['mdp']['mdpName'] == 'SwingUpPendulum':
                self.mdp = SwingUpPendulum()
            elif self.config['mdp']['mdpName'] == 'Acrobot':
                self.mdp = Acrobot()
            elif self.config["mdp"]["mdpName"] == "BicycleBalancing":
                self.mdp = Bicycle(navigate=False)
            elif self.config["mdp"]["mdpName"] == "BicycleNavigate":
                self.mdp = Bicycle(navigate=True)
            elif self.config["mdp"]["mdpName"] == "SwingPendulum":
                self.mdp = SwingPendulum()
            elif self.config["mdp"]["mdpName"] == "CartPole":
                self.mdp = CartPole()
            elif self.config["mdp"]["mdpName"] == "CartPoleDisc":
                self.mdp = CartPole(discreteRew=True)
            elif self.config["mdp"]["mdpName"] == "LQG1D":
                self.mdp = LQG1D()
            elif self.config["mdp"]["mdpName"] == "LQG1DDisc":
                self.mdp = LQG1D()
                self.mdp.discreteReward = True
            elif self.config["mdp"]["mdpName"] == "LunarLander":
                self.mdp = LunarLander()
            else:
                raise ValueError('Unknown mdp type.')

        return self.mdp

    def _getModel(self, index):
        """
        This function loads the model required in the configuration file.
        Returns:
            the required model.

        """

        stateDim, actionDim = envs.get_space_info(self.mdp)
        modelConfig = self.config['regressors'][index]

        fitActions = False
        if 'fitActions' in modelConfig:
            fitActions = modelConfig['fitActions']

        if modelConfig['modelName'] == 'ExtraTree':
            model = Regressor#ExtraTreesRegressor
            params = {'regressor_class':ExtraTreesRegressor, 'n_estimators': modelConfig['nEstimators'],
                      'criterion': self.config["regressors"][index]['supervisedAlgorithm']
                                              ['criterion'],
                      'min_samples_split': modelConfig['minSamplesSplit'],
                      'min_samples_leaf': modelConfig['minSamplesLeaf']}
        elif modelConfig['modelName'] == 'DecisionTree':
            model = Ensemble
            params = {'ens_regressor_class': Regressor, 'regressor_class': DecisionTreeRegressor,
                      #'criterion': self.config["regressors"][index]['supervisedAlgorithm']
                      #['criterion'],
                      #'min_samples_split': modelConfig['minSamplesSplit'],
                      #'min_samples_leaf': modelConfig['minSamplesLeaf']}
                      }
        elif modelConfig['modelName'] == 'ExtraTreeEnsemble':
            model = Ensemble
            params = {'ens_regressor_class':Regressor,'regressor_class':ExtraTreesRegressor, 'n_estimators': modelConfig['nEstimators'],
                      'criterion': self.config["regressors"][index]['supervisedAlgorithm']
                                              ['criterion'],
                      'min_samples_split': modelConfig['minSamplesSplit'],
                      'min_samples_leaf': modelConfig['minSamplesLeaf']}
        elif modelConfig['modelName'] == 'MLP':
            model = Regressor
            params = {'regressor_class':MLP, 'n_input': stateDim,
                      'n_output': 1,
                      'hidden_neurons': modelConfig['hidden_neurons'],
                      'optimizer': modelConfig['optimizer'],
                      'activation': modelConfig['activation']}
            if fitActions:
                params["n_input"] = stateDim + actionDim
        elif modelConfig['modelName'] == 'MLPEnsemble':
            model = Ensemble
            params = {'ens_regressor_class':Regressor,'regressor_class':MLP, 'n_input': stateDim,
                      'n_output': 1,
                      'hidden_neurons': modelConfig['hidden_neurons'],
                      'optimizer': modelConfig['optimizer'],
                      'activation': modelConfig['activation']}
            if fitActions:
                params["n_input"] = stateDim + actionDim
        elif modelConfig['modelName'] == 'Linear':
            model = LinearRegression
            params = {}
        elif modelConfig['modelName'] == 'LinearEnsemble':
            #model = LinearEnsemble
            params = {}
        else:
            raise ValueError('Unknown estimator type.')

        if modelConfig['modelName'] in ["ExtraTree", "ExtraTreeEnsemble", "DecisionTree"]:
            if "max_depth" in modelConfig: params["max_depth"] = modelConfig["max_depth"]
            if "min_weight_fraction_leaf" in modelConfig: params["min_weight_fraction_leaf"] = modelConfig["min_weight_fraction_leaf"]
        if modelConfig['modelName'] in ["MLP", "MLPEnsemble"]:
            if "early_stopping" in modelConfig: params["early_stopping"] = modelConfig["early_stopping"]
            if "delta_min" in modelConfig: params["delta_min"] = modelConfig["delta_min"]
            if "patience" in modelConfig: params["patience"] = modelConfig["patience"]


        if "input_scaled" in modelConfig:
            params["input_scaled"] = modelConfig["input_scaled"]
        if "output_scaled" in modelConfig:
            params["output_scaled"] = modelConfig["output_scaled"]

        if fitActions:
            return model(**params)
        else:
            if isinstance(self.mdp.action_space, spaces.Box):
                warnings.warn("Action Regressor cannot be used for continuous "
                              "action environment. Single regressor will be "
                              "used.")
                return model(**params)
            return ActionRegressor(model,
                                   self.mdp.action_space.values, decimals=5,
                                   **params)

    def getFQI(self, regressorIndex):
        regressor = self._getModel(regressorIndex)

        gamma = self.mdp.gamma
        if "gamma" in self.config['rlAlgorithm']:
            gamma = self.config['rlAlgorithm']['gamma']

        horizon = self.config['rlAlgorithm']['horizon']
        verbose = self.config['rlAlgorithm']['verbosity']

        optimized=False
        if "optimized" in self.config["rlAlgorithm"]:
            optimized = self.config['rlAlgorithm']['optimized']

        features = None
        if 'features' in self.config['regressors'][regressorIndex]:
            features = self.config['regressors'][regressorIndex]['features']

        reset=False
        if "reset" in self.config["rlAlgorithm"]:
            reset = self.config["rlAlgorithm"]["reset"]

        state_dim = self.mdp.observation_space.shape[0]

        if(isinstance(self.mdp.action_space, spaces.Box)):
            discreteActions = self.getActions()
        else:
            discreteActions = self.mdp.action_space.values

        fqi = FQI(estimator=regressor,
          state_dim=state_dim,
          #TODO: Fix action dimension
          action_dim=1,
          discrete_actions=discreteActions,
          gamma=gamma,
          horizon=horizon,
          verbose=verbose,
          features=features,
            reset_regressor=reset)
          
        return fqi 