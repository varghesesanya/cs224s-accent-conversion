import time

import numpy as np
import tensorflow as tf

import os
import scipy.io.wavfile as wav
from python_speech_features import mfcc

from tensorflow.python.ops.nn import dynamic_rnn

from utils.general_utils import get_minibatches


class Config(object):
		"""Holds model hyperparams and data information.

		The config class is used to store various hyperparameters and dataset
		information parameters. Model objects are passed a Config() object at
		instantiation.
		"""
		batch_size = 32 
		n_epochs = 50
		lr = 1e-4
		max_num_frames = 582 
		n_mfcc_features = 13		


class RNNModel(object):
		"""Implements an LSTM machine translation-esque baseline model with a regression loss."""

		def add_placeholders(self):
				"""Generates placeholder variables to represent the input tensors.

				These placeholders are used as inputs by the rest of the model building
				and will be fed data during training.

				Adds following nodes to the computational graph

				input_placeholder: Input placeholder tensor of shape
													 (batch_size, max_num_frames, n_mfcc_features), type tf.float32
				labels_placeholder: Labels placeholder tensor of shape
														(batch_size, max_num_frames, n_mfcc_features), type tf.float32
				input_masks_placeholder: Input masks placeholder tensor of shape
                   			         (batch_size, max_num_frames), type tf.bool
        labels_masks_placeholder: Labels masks placeholder tensor of shape
                         			    (batch_size, max_num_frames), type tf.bool

				Add these placeholders to self as the instance variables
						self.input_placeholder
						self.labels_placeholder
						self.input_masks_placeholder
						self.label_masks_placeholder
				"""
				self.input_placeholder = tf.placeholder(tf.float32, (None, self.config.max_num_frames, self.config.n_mfcc_features))
				self.labels_placeholder = tf.placeholder(tf.int32, (None, self.config.max_num_frames, self.config.n_mfcc_features))
				self.input_masks_placeholder = tf.placeholder(tf.bool, (None, self.config.max_num_frames))
				self.label_masks_placeholder = tf.placeholder(tf.bool, (None, self.config.max_num_frames)) 


		def create_feed_dict(self, inputs_batch, input_masks_batch, labels_batch=None, label_masks_batch=None):
				"""Creates the feed_dict for training the given step.

				A feed_dict takes the form of:
				feed_dict = {
								<placeholder>: <tensor of values to be passed for placeholder>,
								....
				}
				
				Args:
						inputs_batch: A batch of input data.
						input_masks_batch: A batch of input masks.
						labels_batch: (Optional) a batch of label data.
						labels_mask_batch: (Optional) a batch of label masks.
				Returns:
						feed_dict: The feed dictionary mapping from placeholders to values.
				"""
				feed_dict = {
					self.input_placeholder: inputs_batch,
					self.labels_placeholder: labels_batch,
					self.input_masks_placeholder: input_masks_batch,
					self.label_masks_placeholder: label_masks_batch
				}
				return feed_dict

		def add_prediction_op(self):
				"""Adds the core transformation for this model which transforms a batch of input
				data into a batch of predictions. In this case, the transformation is a linear layer plus a
				softmax transformation:

				y = softmax(Wx + b)

				Hint: Make sure to create tf.Variables as needed.
				Hint: For this simple use-case, it's sufficient to initialize both weights W
										and biases b with zeros.

				Args:
						input_data: A tensor of shape (batch_size, n_features).
				Returns:
						pred: A tensor of shape (batch_size, n_classes)
				"""
				b = tf.Variable(tf.zeros((self.config.batch_size,)))
				W = tf.Variable(tf.zeros((self.config.n_features, self.config.n_classes)))
				xW = tf.matmul(self.input_placeholder, W)
				pred = softmax(tf.transpose(tf.transpose(xW) + b))
				return pred

		def add_loss_op(self, pred):
				"""Adds cross_entropy_loss ops to the computational graph.

				Hint: Use the cross_entropy_loss function we defined. This should be a very
										short function.
				Args:
						pred: A tensor of shape (batch_size, n_classes)
				Returns:
						loss: A 0-d tensor (scalar)
				"""
				loss = cross_entropy_loss(self.labels_placeholder, pred)
				return loss

		def add_training_op(self, loss):
				"""Sets up the training Ops.

				Creates an optimizer and applies the gradients to all trainable variables.
				The Op returned by this function is what must be passed to the
				`sess.run()` call to cause the model to train. See

				https://www.tensorflow.org/versions/r0.7/api_docs/python/train.html#Optimizer

				for more information.

				Hint: Use tf.train.GradientDescentOptimizer to get an optimizer object.
										Calling optimizer.minimize() will return a train_op object.

				Args:
						loss: Loss tensor, from cross_entropy_loss.
				Returns:
						train_op: The Op for training.
				"""
				train_op = tf.train.GradientDescentOptimizer(self.config.lr).minimize(loss)
				return train_op


		def train_on_batch(self, sess, inputs_batch, labels_batch):
				"""Perform one step of gradient descent on the provided batch of data.

				Args:
						sess: tf.Session()
						input_batch: np.ndarray of shape (n_samples, n_features)
						labels_batch: np.ndarray of shape (n_samples, n_classes)
				Returns:
						loss: loss over the batch (a scalar)
				"""
				feed = self.create_feed_dict(inputs_batch, labels_batch=labels_batch)
				_, loss = sess.run([self.train_op, self.loss], feed_dict=feed)
				return loss


		def run_epoch(self, sess, inputs, labels, input_masks, label_masks):
				"""Runs an epoch of training.

				Args:
						sess: tf.Session() object
						inputs: np.ndarray of shape (n_samples, n_features)
						labels: np.ndarray of shape (n_samples, n_classes)
						input_masks: boolean np.ndarray of shape (max_num_frames,)
						label_masks: boolean np.ndarray of shape (max_num_frames,)
				Returns:
						average_loss: scalar. Average minibatch loss of model on epoch.
				"""
				n_minibatches, total_loss = 0, 0
				for input_batch, labels_batch, input_masks_batch, label_masks_batch in \
										get_minibatches([inputs, labels, input_masks, label_masks], self.config.batch_size):
						n_minibatches += 1
						total_loss += self.train_on_batch(sess, input_batch, labels_batch)
				return total_loss / n_minibatches


		def optimize(self, sess, inputs, labels, input_masks, label_masks):
				"""Fit model on provided data.

				Args:
						sess: tf.Session()
						inputs: np.ndarray of shape (max_num_frames, n_mfcc_features)
						labels: np.ndarray of shape (max_num_frames, n_mfcc_features)
						input_masks: boolean np.ndarray of shape (max_num_frames,)
						label_masks: boolean np.ndarray of shape (max_num_frames,)
				Returns:
						losses: list of loss per epoch
				"""
				losses = []
				for epoch in range(self.config.n_epochs):
						start_time = time.time()
						average_loss = self.run_epoch(sess, inputs, labels, input_masks, label_masks)
						duration = time.time() - start_time
						print 'Epoch {:}: loss = {:.2f} ({:.3f} sec)'.format(epoch, average_loss, duration)
						losses.append(average_los)
				return losses


		def __init__(self, config):
				"""Initializes the model.

				Args:
						config: A model configuration object of type Config
				"""
				self.config = config
				self.build()


		def build(self):
				self.add_placeholders()
				self.pred = self.add_prediction_op()
				self.loss = self.add_loss_op(self.pred)
				self.train_op = self.add_training_op(self.loss)


def preprocess_data(config):
	"""Processes the training data and returns MFCC vectors for all of them.
	Args:
		config: the Config object with various parameters specified
	Returns:
		train_data:	A list of tuples, one for each training example: (accent 1 padded MFCC frames, accent 1 mask)
		train_labels: A list of tuples, one for each training example: (accent 2 padded MFCC frames, accent 2 mask)
	"""
	inputs = [] 
	labels = []	
	input_masks = []
	label_masks = []
	
	# American English male bdl
	SOURCE_DIR = '../data/cmu_arctic/us-english-male-bdl/wav/'
	TARGET_DIR = '../data/cmu_arctic/scottish-english-male-awb/wav/'
	for source_fname, target_fname in zip(os.listdir(SOURCE_DIR), os.listdir(TARGET_DIR)):
		(source_sample_rate, source_wav_data) = wav.read(SOURCE_DIR + source_fname) 
		(target_sample_rate, target_wav_data) = wav.read(TARGET_DIR + target_fname)
		source_mfcc_features = mfcc(source_wav_data, source_sample_rate)	 # Returns a numpy array of num_frames x num_cepstrals
		target_mfcc_features = mfcc(target_wav_data, target_sample_rate) 
	
		source_padded_frames, source_mask = pad_sequence(source_mfcc_features, config.max_num_frames)
		target_padded_frames, target_mask = pad_sequence(target_mfcc_features, config.max_num_frames)

		inputs.append(source_padded_frames) 
		labels.append(target_padded_frames) 
		input_masks.append(source_mask)
		label_masks.append(target_mask)	

	print "Train data len: ", len(inputs)
	print "Train labels len: ", len(labels)	

	return inputs, labels, input_masks, label_masks 


def pad_sequence(mfcc_frames, max_num_frames):
	"""
	Args:
		mfcc_frames: A numpy array of shape (num_frames, n_mfcc_features)
		max_length: Tee maximum length to which the array should be truncated or zero-padded 
	"""
	padded_mfcc_frames = np.zeros((max_num_frames, mfcc_frames.shape[1]))
	mask = []

	# Truncate (or fill exactly
	if mfcc_frames.shape[0] >= max_num_frames:	
		padded_mfcc_frames = mfcc_frames[0:max_num_frames,:]
		mask = [True] * max_num_frames 

	# Append 0 MFCC vectors
	elif mfcc_frames.shape[0] < max_num_frames:		
		delta = max_num_frames - mfcc_frames.shape[0]	
		zeros = np.zeros((delta, mfcc_frames.shape[1]))
		padded_mfcc_frames = np.concatenate((mfcc_frames, zeros), axis=0)
		mask = ([True] * mfcc_frames.shape[0]) + ([False] * delta)

	return (padded_mfcc_frames, mask)


def main():
		"""Main entry method for this file."""
		config = Config()

		print "Preprocessing data"
		inputs, labels, input_masks, label_masks = preprocess_data(config)

		# Tell TensorFlow that the model will be built into the default Graph.
		# (not required but good practice)
		with tf.Graph().as_default():
				# Build the model and add the variable initializer Op
				model = RNNModel(config)
				init = tf.global_variables_initializer()

				# Create a session for running Ops in the Graph
				with tf.Session() as sess:
						# Run the Op to initialize the variables.
						sess.run(init)
						# Fit the model
						losses = model.optimize(sess, inputs, labels, input_masks, label_masks)


if __name__ == "__main__":
		main()

