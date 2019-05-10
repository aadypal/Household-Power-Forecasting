import numpy as np
import pandas as pd
import keras
from math import sqrt
from numpy import array
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Flatten
from keras.layers.convolutional import Conv1D
from keras.layers.convolutional import MaxPooling1D
 
#fill missing values with a value at the same time one day ago
def fill_missing_data(values):
	one_day = 60 * 24
	for row in range(values.shape[0]):
		for col in range(values.shape[1]):
			if np.isnan(values[row, col]):
				values[row, col] = values[row - one_day, col]
 
#load raw data
dataset = pd.read_csv('household_power_consumption.txt', sep=';', header=0, low_memory=False, infer_datetime_format=True, parse_dates=             
                     {'datetime':[0,1]}, index_col=['datetime'])
#mark all missing values
dataset.replace('?', np.nan, inplace=True)
dataset = dataset.astype('float32')
#fill missing
fill_missing_data(dataset.values)
#add a column for for the remainder of sub metering
values = dataset.values
dataset['sub_metering_4'] = (values[:,0] * 1000 / 60) - (values[:,4] + values[:,5] + values[:,6])
#save updated dataset
dataset.to_csv('household_power_consumption.csv')

#load saved file
dataset = pd.read_csv('household_power_consumption.csv', header=0, infer_datetime_format=True, parse_dates=['datetime'], index_col=['datetime'])
#grouping to daily data
daily_groups_data = dataset.resample('D')
daily_data = daily_groups_data.sum()
print(daily_data.shape)
daily_data.to_csv('household_power_consumption_days.csv')

#plot dataset
dataset = pd.read_csv('household_power_consumption_days.csv', header=0, index_col=0)
values = dataset.values
groups = [0, 1, 2, 3, 5, 6, 7]
i = 1
plt.figure()
for group in groups:
	plt.subplot(len(groups), 1, i)
	plt.plot(values[:, group])
	plt.title(dataset.columns[group], y=0.5, loc='right')
	i += 1
plt.show()

# multichannel multi-step cnn
def split_dataset(data):
	train, test = data[1:-328], data[-328:-6]
	train = np.array(np.split(train, len(train)/7))
	test = np.array(np.split(test, len(test)/7))
	return train, test
 
def evaluate_forecasts(actual, predicted):
	scores = list()
	#RMSE score for each day
	for i in range(actual.shape[1]):
		mse = mean_squared_error(actual[:, i], predicted[:, i])
		rmse = sqrt(mse)
		scores.append(rmse)
	#overall RMSE
	s = 0
	for row in range(actual.shape[0]):
		for col in range(actual.shape[1]):
			s += (actual[row, col] - predicted[row, col])**2
	score = sqrt(s / (actual.shape[0] * actual.shape[1]))
	return score, scores
 
def summarize_scores(name, score, scores):
	s_scores = ', '.join(['%.1f' % s for s in scores])
	print('%s: [%.3f] %s' % (name, score, s_scores))
 
def to_supervised(train, n_input, n_out=7):
	data = train.reshape((train.shape[0]*train.shape[1], train.shape[2]))
	X, y = list(), list()
	in_start = 0
	for _ in range(len(data)):
		in_end = in_start + n_input
		out_end = in_end + n_out
		if out_end < len(data):
			X.append(data[in_start:in_end, :])
			y.append(data[in_end:out_end, 0])
		#move along one time step
		in_start += 1
	return np.array(X), np.array(y)
 
def build_model(train, n_input):
	train_x, train_y = to_supervised(train, n_input)
	verbose, epochs, batch_size = 1, 90, 16
	n_timesteps, n_features, n_outputs = train_x.shape[1], train_x.shape[2], train_y.shape[1]
	model = Sequential()
	model.add(Conv1D(filters=32, kernel_size=3, activation='relu', input_shape=(n_timesteps,n_features)))
	model.add(Conv1D(filters=32, kernel_size=3, activation='relu'))
	model.add(MaxPooling1D(pool_size=2))
	model.add(Conv1D(filters=16, kernel_size=3, activation='relu'))
	model.add(MaxPooling1D(pool_size=2))
	model.add(Flatten())
	model.add(Dense(100, activation='relu'))
	model.add(Dense(n_outputs))
	model.compile(loss='mse', optimizer='adam')
	model.fit(train_x, train_y, epochs=epochs, batch_size=batch_size, verbose=verbose)
	return model
 
#make a forecast
def forecast(model, history, n_input):
	data = np.array(history)
	data = data.reshape((data.shape[0]*data.shape[1], data.shape[2]))
	input_x = data[-n_input:, :]
	input_x = input_x.reshape((1, input_x.shape[0], input_x.shape[1]))
	# forecast the next week
	yhat = model.predict(input_x, verbose=0)
	yhat = yhat[0]
	return yhat
 
def evaluate_model(train, test, n_input):
	model = build_model(train, n_input)
	history = [x for x in train]
	#walk-forward validation over each week
	predictions = list()
	for i in range(len(test)+1):
		#predict the week
		yhat_sequence = forecast(model, history, n_input)
		predictions.append(yhat_sequence)
		while i<len(test):
			history.append(test[i, :])
	forecast_sequence = array(predictions)
	score, scores = evaluate_forecasts(test[:, :, 0], predictions)
	return score, scores, forecast_sequence
 #define input to the model
dataset = pd.read_csv('household_power_consumption_days.csv', header=0, infer_datetime_format=True, parse_dates=['datetime'], index_col=['datetime'])
train, test = split_dataset(dataset.values)
n_input = 14
score, scores, forecast_sequence = evaluate_model(train, test, n_input)
summarize_scores('cnn', score, scores)
#plot scores
days = ['sun', 'mon', 'tue', 'wed', 'thr', 'fri', 'sat']
plt.xlabel('Day')
plt.ylabel('Loss in KiloWatt for whole day')
plt.title('Loss for prior one week')
plt.plot(days, scores, marker='o', label='cnn')
plt.show()
#plot prediction
forecast_sequence=forecast_sequence[46:]
forecast_sequence = np.squeeze(np.asarray(forecast_sequence))
plt.xlabel('Day')
plt.ylabel('Power conjumption for whole day in KiloWatt')
plt.title('Forecast for next week')
plt.plot(days, forecast_sequence, marker='o', label='power conjuption for next week')
plt.show()
print(forecast_sequence)
