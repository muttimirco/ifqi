from keras.models import Sequential, Model
from keras.layers import Dense, merge
import numpy as np

class SumRegressor:
    """Sum regressor - i-th model not parametrizable
    """
    def __init__(self, n_input=2,
                    n_output=1,
                    hidden_neurons=[15] * 10,
                    n_h_layer_beginning=1,
                    act_function=["sigmoid","sigmoid"] + ["relu"]*8,
                    reLearn=False,
                    optimizer=None,
                    regularizer=None,
                    use_trained_weights=False):
        self.n_input = n_input
        self.n_output = n_output
        self.optimizer = optimizer
        self.hidden_neurons = hidden_neurons
        self.reLearn = reLearn
        self.n_h_layer_beginning = n_h_layer_beginning
        self.activation = act_function
        self.regularizer = regularizer
        self.dense_id = 0
        self.use_trained_weights = use_trained_weights
        self.model = self.initModel()
    
    def fit(self, X, y, **kwargs):
        #learn delta
        delta = y-self.predictLast(X)
        return self.model[-1].fit(X, delta, **kwargs)
      
    def predict(self, x, **kwargs):
        #Sum of all predictive model found till now
        len_ = x.shape[0]
        sum_ = np.zeros((len_,1))
        for model in self.model[:]:
            sum_ = sum_ + model.predict(x, **kwargs)
            #print("predict shape", model.predict(x, **kwargs).shape)
        return sum_
        
    def predictLast(self, x, **kwargs):
        #Sum of all predictive model found till now
        len_ = x.shape[0]
        sum_ = np.zeros((len_,))
        for model in self.model[:-1]:
            sum_ = sum_ + model.predict(x, **kwargs).ravel()
            #print("predict shape", model.predict(x, **kwargs).shape)
        return sum_  
        
    def adapt(self, iteration=1):
        self.addModel()
    
    def addModel(self,iteration=1):
        self.model.append(self.generateModel(iteration))
        
    def initModel(self):
        model = self.generateModel(0)
        return [model]
    
    def generateModel(self,iteration):
        model = Sequential()
        model.add(Dense(self.hidden_neurons[iteration],
                        input_shape=(self.n_input,),
                        activation=self.activation[iteration],
                        W_regularizer = self.regularizer,
                        b_regularizer = self.regularizer,
                        name='dense_0-' + str(self.dense_id)))
        for i in range(1, self.n_h_layer_beginning):
            model.add(Dense(self.hidden_neurons[iteration],
                        activation=self.activation[iteration],
                        W_regularizer = self.regularizer,
                        b_regularizer = self.regularizer,
                        name='dense_' + str(i) + '-' + str(self.dense_id)))
        model.add(Dense(self.n_output,
                        activation='linear',
                        W_regularizer = self.regularizer,
                        b_regularizer = self.regularizer,
                        name='dense_' + str(self.n_h_layer_beginning) + '-' + str(self.dense_id)))
        self.dense_id += 1

        model.compile(loss='mse', optimizer=self.optimizer)
        return model
