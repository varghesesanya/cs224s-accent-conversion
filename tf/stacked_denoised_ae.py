from time import time, gmtime, strftime
import numpy as np
import os
import random
import matlab.engine

import scipy.io.wavfile as wav
from python_speech_features import mfcc

import tensorflow as tf
from tensorflow.python.ops.nn import dynamic_rnn

from utils.general_utils import get_minibatches, batch_multiply_by_matrix
from utils.fast_dtw import get_dtw_series 
from utils.corrupt_data import corrupt_input
from utils.pad_sequence import pad_sequence


class Config(object):
		"""Holds model hyperparams and data information.

		The config class is used to store various hyperparameters and dataset
		information parameters. Model objects are passed a Config() object at
		instantiation.
		"""
		batch_size = 32 
		n_epochs = 50
		lr = 1e-5
		max_num_frames = 706  # This is the maximum length of any warped time series in the dataset 
		num_mfcc_coeffs = 13
		sample_rate = 16000.0
		num_features = max_num_frames * num_mfcc_coeffs 
		state_size_1 = 50
		state_size_2 = 50
		state_size_3 = 75
		dropout_keep_prob = 1.0 # 0.8
		logs_path = "tensorboard/" + strftime("%Y_%m_%d_%H_%M_%S", gmtime())
		corr_type = "masking"  # 'masking', 'salt_and_pepper', or 'none' 
		corr_frac = 0.5  # Fraction of features to corrupt  


class StackedDenoisedAutoEncoder(object):
		"""Implements a stacked, denoising autoencoder with a MSE loss."""

		def add_placeholders(self):
				"""Generates placeholder variables to represent the input tensors.

				These placeholders are used as inputs by the rest of the model building
				and will be fed data during training.

				Adds following nodes to the computational graph

				input_placeholder: Input placeholder tensor of shape
													 (batch_size, max_num_frames, num_mfcc_coeffs), type tf.float32
				input_placeholder: Corrupted innput placeholder tensor of shape
                           (batch_size, max_num_frames, num_mfcc_coeffs), type tf.float32
				labels_placeholder: Labels placeholder tensor of shape
														(batch_size, max_num_frames, num_mfcc_coeffs), type tf.float32
				input_masks_placeholder: Input masks placeholder tensor of shape
																 (batch_size, max_num_frames), type tf.bool
				labels_masks_placeholder: Labels masks placeholder tensor of shape
																	(batch_size, max_num_frames), type tf.bool

				Add these placeholders to self as the instance variables
						self.input_placeholder
						self.input_corrupted_placeholder
						self.labels_placeholder
						self.input_masks_placeholder
						self.label_masks_placeholder
				"""
				self.input_placeholder = tf.placeholder(tf.float32, (None, self.config.max_num_frames, self.config.num_mfcc_coeffs))
				self.input_corrupted_placeholder = tf.placeholder(tf.float32, (None, self.config.max_num_frames, self.config.num_mfcc_coeffs))
				self.labels_placeholder = tf.placeholder(tf.float32, (None, self.config.max_num_frames, self.config.num_mfcc_coeffs))
				self.input_masks_placeholder = tf.placeholder(tf.bool, (None, self.config.max_num_frames))
				self.label_masks_placeholder = tf.placeholder(tf.bool, (None, self.config.max_num_frames)) 


		def create_feed_dict(self, inputs_batch, inputs_corrupted_batch, input_masks_batch, labels_batch=None, label_masks_batch=None):
				"""Creates the feed_dict for training the given step.

				A feed_dict takes the form of:
				feed_dict = {
								<placeholder>: <tensor of values to be passed for placeholder>,
								....
				}
				
				Args:
						inputs_batch: A batch of input data.
						inputs_corrupted_batch: A batch of noised input data
						input_masks_batch: A batch of input masks.
						labels_batch: (Optional) a batch of label data.
						labels_mask_batch: (Optional) a batch of label masks.
				Returns:
						feed_dict: The feed dictionary mapping from placeholders to values.
				"""
				feed_dict = {
					self.input_placeholder: inputs_batch,
					self.input_corrupted_placeholder = inputs_corrupted_batch, 
					self.labels_placeholder: labels_batch,
					self.input_masks_placeholder: input_masks_batch,
					self.label_masks_placeholder: label_masks_batch
				}
				return feed_dict


		def add_prediction_op(self): 
				"""Adds the core transformation for this model which transforms a batch of input
				data into a batch of predictions. In this case, the transformation is a linear layer plus a
				softmax transformation:
			
				Implements a stacked, denoising autoencoder. 
				Autoencoder learns two mappings: (1) Encoder: input ==> hidden layer, and (2) Decoder: hidden layer ==> output layer
				

				Returns:
						pred: A tensor of shape (batch_size, n_classes)
				"""

				xavier = tf.contrib.layers.xavier_initializer()
				W1 = tf.get_variable("W1", shape=(self.config.num_features, self.config.state_size_1), initializer=xavier) 
				b1 = tf.get_variable("b1", shape=(1, self.config.state_size_1))
				W2 = tf.get_variable("W2", shape=(self.config.state_size_1, self.config.state_size_2), initializer=xavier) 
				b2 = tf.get_variable("b2", shape=(1, self.config.state_size_2))
				W3 = tf.get_variable("W3", shape=(self.config.state_size_2, self.config.state_size_3), initializer=xavier) 
				b3 = tf.get_variable("b3", shape=(1, self.config.state_size_3))
				W4 = tf.get_variable("W4", shape=(self.config.state_size_3, self.config.num_features), initializer=xavier) 
				b4 = tf.get_variable("b4", shape=(1, self.config.num_features))

				# [batch, num_features] x [num_features, state_size] = [batch, state_size]
				h1 = tf.nn.relu(tf.matmul(self.input_placeholder, W1) + b1)
				# [batch, state_size] x [state_size, num_features] = [batch, num_features]
				h2 = tf.nn.relu(tf.matmul(mfcc_preds, W2) + b2)
				# [batch, num_features] x [num_features, state_size] = [batch, state_size]
				h3 = tf.nn.relu(tf.matmul(mfcc_preds, W3) + b3)
				# [batch, state_size] x [state_size, num_features] = [batch, num_features]
				h4 = tf.nn.relu(tf.matmul(mfcc_preds, W4) + b4)

				#masked_preds = tf.boolean_mask(mfcc_preds, self.input_masks_placeholder)
	
				self.mfcc = mfcc_preds
				return mfcc_preds 


		def create_encode_layer(self):
			with tf.variable_scope("encoder"):
				ha = tf.nn.relu( tf.add( tf.matmul(self.input_placeholder, W), bh) )
				return ha

		def create_decode_layer(self):
			with tf.variable_scope("decoder"):
				hd = tf.add( tf.matmul(self.encode, W), bv) 
				return hd

 
		def add_loss_op(self, pred):
				"""Adds mean squared error ops to the computational graph.

				Args:
						pred: A tensor of shape (batch_size, max_num_frames, n_mfcc_features)
				Returns:
						loss: A 0-d tensor (scalar)
				"""
				loss = tf.reduce_mean(tf.squared_difference(pred, self.labels_placeholder))
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


		def train_on_batch(self, sess, inputs_batch, inputs_corrupted_batch, input_masks_batch, labels_batch, label_masks_batch):
				"""Perform one step of gradient descent on the provided batch of data.

				Args:
						sess: tf.Session()
						input_batch: np.ndarray of shape (batch_size, max_num_frames, num_mfcc_coeffs)
						inputs_corrupted_batch: np.ndarray of shape (batch_size, max_num_frames, num_mfcc_coeffs)
						input_masks_batch: np.ndarray of shape (batch_size, max_num_frames)
						labels_batch: np.ndarray of shape (batch_size, max_num_frames, num_mfcc_coeffs)
						label_masks_batch: np.ndarray of shape (batch_size, max_num_frames)
				Returns:
						loss: loss over the batch (a scalar)
				"""
				feed = self.create_feed_dict(inputs_batch, inputs_corrupted_batch, input_masks_batch, 
																		 labels_batch=labels_batch, label_masks_batch=label_masks_batch)
				_, loss, summary = sess.run([self.train_op, self.loss, self.merged_summary_op], feed_dict=feed)
				return loss, summary, feed


		def run_epoch(self, sess, inputs, inputs_corrupted, input_masks, labels, label_masks, train_writer, step_i):
				"""Runs an epoch of training.

				Args:
						sess: tf.Session() object
						inputs: np.ndarray of shape (num_examples, max_num_frames, num_mfcc_coeffs) 
						inputs_corrupted: np.ndarray of shape (num_examples, max_num_frames, num_mfcc_coeffs) 
						input_masks: boolean np.ndarray of shape (num_examples, max_num_frames)
						labels: np.ndarray of shape (num_examples, max_num_frames, num_mfcc_coeffs)
						label_masks: boolean np.ndarray of shape (num_examples, max_num_frames)
						train_writer: a tf.summary.FileWriter object
						step_i: The global number of steps taken so far (i.e., batches we've done a full forward
										and backward pass on) 
				Returns:
						average_loss: scalar. Average minibatch loss of model on epoch.
				"""
				n_minibatches, total_loss = 0, 0
				for input_batch, inputs_corrupted_batch, input_masks_batch, labels_batch, label_masks_batch in \
										get_minibatches([inputs, inputs_corrupted, input_masks, labels, label_masks], self.config.batch_size):
						n_minibatches += 1

						batch_loss, summary, feed = self.train_on_batch(sess, input_batch, inputs_corrupted_batch, input_masks_batch, 
																														labels_batch, label_masks_batch)
						total_loss += batch_loss

						train_writer.add_summary(summary, step_i)
						step_i += 1

				return total_loss / n_minibatches, step_i, feed


		def optimize(self, sess, inputs, inputs_corrupted, input_masks, labels, label_masks):
				"""Fit model on provided data.

				Args:
						sess: tf.Session()
						inputs: np.ndarray of shape (num_examples, max_num_frames, num_mfcc_coeffs) 
						inputs_corrupted: np.ndarray of shape (num_examples, max_num_frames, n_mfcc_features)
            input_masks: boolean np.ndarray of shape (num_examples, max_num_frames)
						labels: np.ndarray of shape (num_examples, max_num_frames, n_mfcc_features)
						label_masks: boolean np.ndarray of shape (num_examples, max_num_frames)
				Returns:
						losses: list of loss per epoch
				"""
				train_writer = tf.summary.FileWriter(self.config.logs_path + '/train', sess.graph)
				step_i = 0

				losses = []
				for epoch in range(self.config.n_epochs):
						start_time = time()
						average_loss, step_i, feed = self.run_epoch(sess, inputs, inputs_corrupted, input_masks, labels, label_masks, train_writer, step_i)
						duration = time() - start_time
						print 'Epoch {:}: loss = {:.2f} ({:.3f} sec)'.format(epoch, average_loss, duration)
						losses.append(average_loss)

						predicted_mfccs_batch = self.mfcc.eval(session=sess, feed_dict=feed)
						for i in range(predicted_mfccs_batch.shape[0]):
							predicted_mfccs = predicted_mfccs_batch[i,:]

							inverted_wav_data = self.eng.invmelfcc(matlab.double(predicted_mfccs.tolist()), 
																										 self.config.sample_rate, 
																										 self.config.num_mfcc_coeffs)

							self.eng.soundsc(inverted_wav_data, self.config.sample_rate, nargout=0)
							inverted_wav_data = np.squeeze(np.array(inverted_wav_data))

							# Scales the waveform to be between -1 and 1
							maxVec = np.max(inverted_wav_data)
							minVec = np.min(inverted_wav_data)
							inverted_wav_data = ((inverted_wav_data - minVec) / (maxVec - minVec) - 0.5) * 2
	 
							wav.write('learned_wav' + str(i) + '.wav', self.config.sample_rate, inverted_wav_data)

				return losses

		
		def setup_matlab_engine(self):
				print "Starting matlab ... type in your password if prompted"
				eng = matlab.engine.start_matlab()
				eng.addpath('../invMFCCs_new')
				print "Done starting matlab"
				return eng				


		def add_summary_op(self):
				return tf.summary.merge_all()
	

		def __init__(self, config):
				"""Initializes the model.

				Args:
						config: A model configuration object of type Config
				"""
				self.config = config
				self.build()


		def build(self):
				self.eng = self.setup_matlab_engine()
				self.mfcc = None	# Add a handle to this so we can set it later
				self.add_placeholders()
				self.encode = self.create_encode_layer()
				self.pred = self.create_decode_layer()
				self.loss = self.add_loss_op(self.pred)
				tf.summary.scalar("loss", self.loss)
				self.train_op = self.add_training_op(self.loss)
				self.merged_summary_op = self.add_summary_op()


		def preprocess_data(self, config):
				"""Processes the training data and returns MFCC vectors for all of them.
				Args:
					config: the Config object with various parameters specified
				Returns:
					train_data:	A list of tuples, one for each training example: (accent 1 padded MFCC frames, accent 1 mask)
					train_labels: A list of tuples, one for each training example: (accent 2 padded MFCC frames, accent 2 mask)
				"""
				inputs = [] 
				inputs_corrupted = []
				labels = []	
				input_masks = []
				label_masks = []
				
				SOURCE_DIR = '../data/cmu_arctic/us-english-male-bdl/wav/'
				TARGET_DIR = '../data/cmu_arctic/scottish-english-male-awb/wav/'
				for source_fname, target_fname in zip(os.listdir(SOURCE_DIR), os.listdir(TARGET_DIR)):
					(source_sample_rate, source_wav_data) = wav.read(SOURCE_DIR + source_fname) 
					(target_sample_rate, target_wav_data) = wav.read(TARGET_DIR + target_fname)

					source_mfcc_features = np.array(mfcc(source_wav_data, samplerate=source_sample_rate, numcep=self.config.num_mfcc_coeffs))
					target_mfcc_features = np.array(mfcc(target_wav_data, samplerate=target_sample_rate, numcep=self.config.num_mfcc_coeffs))

					# Aligns the MFCC features matrices using FastDTW.
					source_mfcc_features, target_mfcc_features = get_dtw_series(source_mfcc_features, target_mfcc_features)

					# Corrupt the input (source) MFCC features
					source_mfcc_features_corrupted = corrupt_input(source_mfcc_features, corr_frac=self.config.corr_frac,
																												 corr_type=self.config.corr_type) 

					# Pads the MFCC feature matrices (rows) to length config.max_num_frames
					source_padded_frames, source_mask = pad_sequence(source_mfcc_features, config.max_num_frames)
					source_padded_frames_corrupted, _ = pad_sequence(source_mfcc_features_corrupted, config.max_num_frames)
					target_padded_frames, target_mask = pad_sequence(target_mfcc_features, config.max_num_frames)

					inputs.append(source_padded_frames) 
					inputs_corrupted.append(source_padded_frames_corrupted)
          input_masks.append(source_mask)
					labels.append(target_padded_frames) 
					label_masks.append(target_mask)	

				randomized_indices = range(0, len(inputs)) 
				random.shuffle(randomized_indices)
				inputs = [inputs[i] for i in randomized_indices]
				inputs_corrupted = [inputs_corrupted[i] for i in randomized_indices]
        input_masks = [input_masks[i] for i in randomized_indices]
				labels = [labels[i] for i in randomized_indices]
				label_masks = [label_masks[i] for i in randomized_indices] 

				return inputs, inputs_corrupted, input_masks, labels, label_masks


def main():
	"""Main entry method for this file."""
	config = Config()

	# Tell TensorFlow that the model will be built into the default Graph.
	# (not required but good practice)
	logs_path = "tensorboard/" + strftime("%Y_%m_%d_%H_%M_%S", gmtime())

	with tf.Graph().as_default():
			# Build the model and add the variable initializer Op
			model = StackedDenoisedAutoEncoder(config)
			init = tf.global_variables_initializer()

			print "Preprocessing data ..."
			inputs, inputs_corrupted, input_masks, labels, label_masks = model.preprocess_data(config)
			print "Finished preprocessing data"

			# Create a session for running Ops in the Graph
			with tf.Session() as sess:
					# Run the Op to initialize the variables 
					sess.run(init)
					# Fit the model
					losses = model.optimize(sess, inputs, inputs_corrupted, input_masks, labels, label_masks)


if __name__ == "__main__":
		main()

