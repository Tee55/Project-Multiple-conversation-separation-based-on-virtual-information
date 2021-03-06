#%%
import numpy as np
from sklearn.decomposition import FastICA
import speech_recognition as sr
import math
import os
import cv2
from PIL import Image
import time
import matplotlib.pyplot as plt
import librosa
import librosa.display
from moviepy.editor import VideoFileClip, clips_array, concatenate_videoclips, CompositeVideoClip
from skimage.filters import threshold_yen
import pandas
from skimage import io
import urllib
import re
import tensorflow as tf
from progress.bar import Bar
from sklearn.cluster import KMeans
from sklearn import preprocessing
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
from scipy.io import wavfile
import scipy.signal as signal
from jiwer import wer

from keras.models import Sequential
from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D, ZeroPadding2D, Activation, Dropout, Flatten, Dense, BatchNormalization, GlobalAveragePooling2D, LSTM, RepeatVector, TimeDistributed, Reshape
from keras.models import Model
from keras.datasets import mnist
from keras.utils.np_utils import to_categorical
from keras.utils import plot_model
from keras import optimizers, regularizers

from keras.backend.tensorflow_backend import set_session
from keras.backend.tensorflow_backend import clear_session
from keras.backend.tensorflow_backend import get_session

import torch
import torch.nn as nn

video_file_path_train = './data/train/video/'
audio_file_path_train = './data/train/audio/'
spec_file_path_train = './data/train/spec/'

video_file_path_test = './data/test/video/'
audio_file_path_test = './data/test/audio/'
spec_file_path_test = './data/test/spec/'

IMG_HEIGHT_MFCC = 20
IMG_HEIGHT_MEL = 128
IMG_WIDTH = 44

duration = 1
'''
main_speaker = ['SirKenRobinson', 'AlGore', 'DavidPogue', 'MajoraCarter', 'HansRosling', 'TonyRobbins', 'JuliaSweeney', 'JoshuaPrinceRamus', 'DanDennett', 'RickWarren']
year = ['2006', '2006','2006', '2006', '2006', '2006', '2006','2006', '2006', '2006']
'''
main_speaker = ['AlGore', 'DavidPogue', 'MajoraCarter', 'HansRosling', 'TonyRobbins']
year = ['2006','2006', '2006', '2006', '2006']

class VoiceSplit:

    def reset_keras(self):

        torch.cuda.empty_cache()

        sess = get_session()
        clear_session()
        sess.close()
        sess = get_session()

        try:
            del classifier
        except:
            pass

        config = tf.ConfigProto()
        config.gpu_options.per_process_gpu_memory_fraction = 1.0
        config.gpu_options.visible_device_list = "0"
        set_session(tf.Session(config=config))

    def speech_recognition(self, ref_speaker_path):

        speech_recog_pred = []
        speech_recog_ref = []

        r = sr.Recognizer()
        audio_file_ref = sr.AudioFile(ref_speaker_path)
        audio_file = sr.AudioFile(audio_file_path_test + 'output.wav')

        with audio_file_ref as source_ref: 
            r.adjust_for_ambient_noise(source_ref)
            audio_ref = r.record(source_ref, duration=60.0)

        with audio_file as source: 
            r.adjust_for_ambient_noise(source)
            audio = r.record(source, duration=60.0)

        result_ref = r.recognize_ibm(audio_ref, username="apikey", password="fRj5hZlwxCNRulhCrZDESzxeUvc5T6EQUx0st_ztwbbe", language='en-US')
        result_pred = r.recognize_ibm(audio, username="apikey", password="fRj5hZlwxCNRulhCrZDESzxeUvc5T6EQUx0st_ztwbbe", language='en-US')

        #print(result_pred)
        #print(result_ref)

        speech_recog_pred.append(result_pred)
        speech_recog_ref.append(result_ref)

        ground_truth = speech_recog_pred
        hypothesis = speech_recog_ref

        error = wer(ground_truth, hypothesis)

        return error

    def wav2sig(self, file_path, offset):
        x, fs = librosa.load(file_path, offset=offset, duration=duration)
        x = librosa.util.normalize(x)

        return x

    def wav2mel(self, file_path, offset):
        x, fs = librosa.load(file_path, offset=offset, duration=duration)
        mel = librosa.feature.melspectrogram(x, sr=fs, n_mels=IMG_HEIGHT_MEL)

        return mel
        
    def preprocess(self, data_type):

        data_mel = []
        data_sig = []

        bar = Bar('Preprocess')

        if data_type == 'train':

            each_main_speaker_target = 'SirKenRobinson'
            each_year_target = '2006'

            for each_main_speaker_mixed in main_speaker:

                ref_speaker_path = audio_file_path_train + 'raw/' + each_main_speaker_target + '_' + each_year_target + '.wav'

                wav_path = ref_speaker_path

                x, fs = librosa.load(wav_path)

                aud_length = librosa.get_duration(x)

                for offset in range(0, int(math.ceil(aud_length))-duration, duration):

                    mel = self.wav2mel(file_path=wav_path, offset=offset)
                    sig = self.wav2sig(file_path=wav_path, offset=offset)

                    data_mel.append(mel)
                    data_sig.append(sig)

                    bar.next()

            data_mel = np.array(data_mel)
            data_sig = np.array(data_sig)

            bar.finish()

            return data_mel, data_sig, fs

        elif data_type == 'test':

            main_speaker_target = 'SirKenRobinson'
            year_target = '2006'
            main_speaker_mixed = 'DanDennett'
            year_mixed = '2006'

            mixed_wav_path = audio_file_path_test + 'mixed/' + 'mixed' + '_' + main_speaker_target + '_' + year_target + '_' +  main_speaker_mixed + '_' + year_mixed + '.wav'

            wav_path = mixed_wav_path

            x, fs = librosa.load(wav_path)
            aud_length = librosa.get_duration(x)

            for offset in range(0, int(math.ceil(aud_length))-duration, duration):

                mel = self.wav2mel(file_path=wav_path, offset=offset)
                sig = self.wav2sig(file_path=wav_path, offset=offset)

                data_mel.append(mel)
                data_sig.append(sig)

                bar.next()

            data_mel = np.array(data_mel)
            data_sig = np.array(data_sig)

            bar.finish()

            return data_mel, data_sig, fs

        elif data_type == 'mixed':

            each_main_speaker_target = 'SirKenRobinson'
            each_year_target = '2006'

            for each_main_speaker_mixed, each_year_mixed in zip(main_speaker, year):

                mixed_wav_path = audio_file_path_test + 'mixed/' + 'mixed' + '_' + each_main_speaker_target + '_' + each_year_target + '_' +  each_main_speaker_mixed + '_' + each_year_mixed + '.wav'

                wav_path = mixed_wav_path

                x, fs = librosa.load(wav_path)
                aud_length = librosa.get_duration(x)

                for offset in range(0, int(math.ceil(aud_length))-duration, duration):

                    mel = self.wav2mel(file_path=wav_path, offset=offset)
                    sig = self.wav2sig(file_path=wav_path, offset=offset)

                    data_mel.append(mel)
                    data_sig.append(sig)

                    bar.next()

            data_mel = np.array(data_mel)
            data_sig = np.array(data_sig)

            bar.finish()

            return data_mel, data_sig, fs

    def CNN_model(self, input_shape=(IMG_HEIGHT_MEL, IMG_WIDTH, 1), classes=1):
        # c.f. https://github.com/alexgkendall/SegNet-Tutorial/blob/master/Example_Models/bayesian_segnet_camvid.prototxt
        img_input = Input(shape=input_shape)
        x = img_input
        # Encoder
        x = Conv2D(64, 3, 3, border_mode="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)
        x = MaxPooling2D(pool_size=(2, 2))(x)

        x = Conv2D(128, 3, 3, border_mode="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)
        x = MaxPooling2D(pool_size=(2, 2))(x)

        # Decoder
        x = UpSampling2D(size=(2, 2))(x)
        x = Conv2D(128, 3, 3, border_mode="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)

        x = UpSampling2D(size=(2, 2))(x)
        x = Conv2D(64, 3, 3, border_mode="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)

        x = Conv2D(classes, 1, 1, border_mode="valid")(x)
        x = Activation("sigmoid")(x)
        model = Model(img_input, x)

        model.compile(loss="mse", optimizer='adadelta', metrics=["accuracy"])

        return model

    def LSTM_model(self, input_shape=(128, 44)):

        seq_input = Input(shape=input_shape)
        x = seq_input

        x = LSTM(units=500, return_sequences=True)(x)
        x = LSTM(units=500)(x)

        x = Dense(units=22050)(x)

        model = Model(seq_input, x)

        adam = optimizers.Adam(learning_rate=0.001)

        model.compile(optimizer=adam, loss='mse', metrics=['accuracy'])

        model.summary()

        #plot_model(model, to_file='LSTM_model.png')

        return model

    def autoencoder(self, data_mel):
        
        encoder_model = self.CNN_model()

        train_X = np.reshape(data_mel, (data_mel.shape[0], IMG_HEIGHT_MEL, IMG_WIDTH, 1))

        data_mel_mask = encoder_model.predict(train_X)

        data_mel_mask = np.reshape(data_mel_mask, (data_mel_mask.shape[0], IMG_HEIGHT_MEL, IMG_WIDTH))

        data_mel_encoded = []
        for mel, mask in zip(data_mel, data_mel_mask):

            soft_pred = np.multiply(mel, mask)
            data_mel_encoded.append(soft_pred)

        data_mel_encoded = np.array(data_mel_encoded)

        return data_mel_encoded

    def train(self):

        self.data_mel_train, self.data_sig_train, self.fs = self.preprocess(data_type='train')
        self.data_mel_mixed, self.data_sig_mixed, self.fs = self.preprocess(data_type='mixed')

        self.data_mel_mixed_encoded = self.autoencoder(data_mel=self.data_mel_mixed)
        
        train_X = self.data_mel_mixed_encoded
        train_y = np.reshape(self.data_sig_train, (self.data_sig_train.shape[0], 22050))

        model = self.LSTM_model()
        model.fit(train_X, train_y, batch_size=10, epochs=200)
        model.save_weights('LSTM_weight.h5')

    def predict(self):

        self.data_mel_test, self.data_sig_test, self.fs = self.preprocess(data_type='test')

        self.data_mel_test_encoded = self.autoencoder(data_mel=self.data_mel_test)

        model = self.LSTM_model()
        model.load_weights('LSTM_weight.h5')

        # Prediction
        test_X = self.data_mel_test_encoded
        pred = model.predict(test_X)

        combine = []
        bar = Bar('Generate audio')
        for sig in pred:

            combine.extend(sig)
            bar.next()

        combine = np.array(combine)
        bar.finish()

        y = (np.iinfo(np.int32).max * (combine/np.abs(combine).max())).astype(np.int32)
        wavfile.write(audio_file_path_test + 'output.wav', self.fs, y)

    def WER_eval():

        wer = self.speech_recognition(ref_speaker_path)

        print('WER Target ' + each_main_speaker_train_target + 'mixed ' + each_main_speaker_train_mixed + ': ', wer)

        f = open("result.txt", "a")
        f.write('WER Target ' + each_main_speaker_train_target + ' mixed ' + each_main_speaker_train_mixed + ': ' + str(wer) + '\n')
        f.close()

    def main(self):

        self.reset_keras()

        #self.train()
        self.predict()

if __name__ == "__main__":

    voicesplit = VoiceSplit()

    voicesplit.main()




# %%
