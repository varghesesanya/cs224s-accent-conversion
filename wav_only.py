import os
import numpy as np
import scipy.io.wavfile as wav
from python_speech_features import mfcc
from sklearn.naive_bayes import MultinomialNB
#from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import wave


def classify():
	data = []
	labels = []
	test_data = []
	test_labels = []
	test_names = ['arctic_b0529.wav','arctic_b0530.wav','arctic_b0531.wav','arctic_b0532.wav','arctic_b0533.wav','arctic_b0534.wav','arctic_b0535.wav','arctic_b0535.wav', 'arctic_b0536.wav', 'arctic_b0537.wav', 'arctic_b0538.wav', 'arctic_b0539.wav']

	print 'CANADIAN'
	for fname in os.listdir('data/cmu_arctic/canadian-english-male-jmk/wav/'):
		w = wave.open('data/cmu_arctic/canadian-english-male-jmk/wav/'+fname)
		for i in range(w.getnframes()):
			frame = w.readframes(1)
			if fname in test_names:
				for j in range(len(frame)):
					test_data.append(frame[j])
					test_labels.append(0) # 0 = canadian
			else:
				for j in range(len(frame)):
					data.append(frame[j])
					labels.append(0) # 0 = canadian
		w.close()


	print 'AMERICAN 1'
	for fname in os.listdir('data/cmu_arctic/us-english-male-bdl/wav/'):
		w = wave.open('data/cmu_arctic/us-english-male-bdl/wav/'+fname)
		for i in range(w.getnframes()):
			frame = w.readframes(1)
			if fname in test_names:
				for j in range(len(frame)):
					test_data.append(frame[j])
					test_labels.append(1) # 1 = american
			else:
				for j in range(len(frame)):
					data.append(frame[j])
					labels.append(1) # 1 = american
		w.close()


	print 'AMERICAN 2'
	for fname in os.listdir('data/cmu_arctic/us-english-male-rms/wav/'):
		w = wave.open('data/cmu_arctic/us-english-male-rms/wav/'+fname)
		for i in range(w.getnframes()):
			frame = w.readframes(1)
			if fname in test_names:
				for j in range(len(frame)):
					test_data.append(frame[j])
					test_labels.append(1) # 1 = american
			else:
				for j in range(len(frame)):
					data.append(frame[j])
					labels.append(1) # 1 = american
		w.close()


	print 'SCOTTISH'
	for fname in os.listdir('data/cmu_arctic/scottish-english-male-awb/wav/'):
		w = wave.open('data/cmu_arctic/scottish-english-male-awb/wav/'+fname)
		for i in range(w.getnframes()):
			frame = w.readframes(1)
			if fname in test_names:
				for j in range(len(frame)):
					test_data.append(frame[j])
					test_labels.append(2) # 2 = scottish
			else:
				for j in range(len(frame)):
					data.append(frame[j])
					labels.append(2) # 2 = scottish
		w.close()


	print 'INDIAN'
	for fname in os.listdir('data/cmu_arctic/indian-english-male-ksp/wav/'):
		w = wave.open('data/cmu_arctic/indian-english-male-ksp/wav/'+fname)
		for i in range(w.getnframes()):
			frame = w.readframes(1)
			if fname in test_names:
				for j in range(len(frame)):
					test_data.append(frame[j])
					test_labels.append(3) # 3 = indian
			else:
				for j in range(len(frame)):
					data.append(frame[j])
					labels.append(3) # 3 = indian
		w.close()

	model = MultinomialNB()
	model.fit(data, labels)
	print 'model fit'
	pred = model.predict(test_data)
	print(classification_report(pred, test_labels))
	print(accuracy_score(pred, test_labels))

	for i, class_label in enumerate([0, 1, 2, 3]):
		top10 = np.argsort(model.coef_[i])[-10:]
		print("%s: %s" % (class_label, " ".join(str(j) for j in top10)))

classify()