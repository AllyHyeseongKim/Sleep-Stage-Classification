import os

import pandas as pd

import tensorflow as tf
import tensorflow_io as tfio


TRAIN_RATIO = 0.8
VALIDATION_RATIO = 0.1
TEST_RATIO = 0.1


@tf.function
def load_wav_16k_mono(wav_path: str):
    """ Load a WAV file, convert it to a float tensor, resample to 16 kHz single-channel audio. """
    file_contents = tf.io.read_file(wav_path)
    wav, sample_rate = tf.audio.decode_wav(
        file_contents,
        desired_channels=1
    )
    wav = tf.squeeze(wav, axis=-1)
    sample_rate = tf.cast(sample_rate, dtype=tf.int64)
    wav = tfio.audio.resample(wav, rate_in=sample_rate, rate_out=16000)
    return wav

def load_wav_for_map(filename: str, label, split):
    return (load_wav_16k_mono(filename), label, split)

def load(path: str, dataset: str = 'sleep_scoring'):
    if dataset == 'sleep_scoring':
        classes = ['NONE', 'SLEEP-REM', 'SLEEP-S0', 'SLEEP-S1', 'SLEEP-S2', 'SLEEP-S3']
        map_class_to_id = {'NONE': 0, 'SLEEP-REM': 3, 'SLEEP-S0': 0, 'SLEEP-S1': 1, 'SLEEP-S2': 2, 'SLEEP-S3': 2}
        new_classes = ['wake', 'light', 'deep', 'REM']

        print(f'Sleep Scoring Classes: {new_classes}')
    else:
        classes = ['NONE', 'SLEEP-REM', 'SLEEP-S0', 'SLEEP-S1', 'SLEEP-S2', 'SLEEP-S3']
        map_class_to_id = {'NONE': 0, 'SLEEP-REM': 3, 'SLEEP-S0': 0, 'SLEEP-S1': 1, 'SLEEP-S2': 2, 'SLEEP-S3': 2}
        new_classes = ['wake', 'light', 'deep', 'REM']

        print(f'data.load else')

    #map_split_to_id = {'train': 0, 'validation': 1, 'eval': 2}

    metadata = pd.DataFrame(columns=['filename', 'class', 'split'])
    for class_name in classes:
        tempdata = pd.DataFrame(columns=['filename', 'class', 'split'])
        tempdata['filename'] = [path + class_name + '/' + dirs for dirs in os.listdir(path + class_name)]
        tempdata['class'] = class_name
        class_id = tempdata['class'].apply(lambda name: map_class_to_id[name])
        tempdata = tempdata.assign(target=class_id)
        num_train = int(len(tempdata) * TRAIN_RATIO)
        num_validation = (len(tempdata) - num_train) // 2
        tempdata['split'].loc[:num_train] = 'train'
        tempdata['split'].loc[num_train:num_train + num_validation] = 'validation'
        tempdata['split'].loc[num_train + num_validation:] = 'eval'
        metadata = metadata.append(tempdata, ignore_index=True)

    dataset = tf.data.Dataset.from_tensor_slices((metadata['filename'], tf.keras.utils.to_categorical(metadata['target'], len(new_classes)), metadata['split']))
    #print(dataset)
    dataset = dataset.map(load_wav_for_map)

    splited_dataset = {}
    train = dataset.filter(lambda wav, target, split: split == 'train')
    validation = dataset.filter(lambda wav, target, split: split == 'validation')
    eval = dataset.filter(lambda wav, target, split: split == 'eval')
    splited_dataset['train'] = train.map(lambda wav, target, split: {'audio': wav, 'label': target})
    splited_dataset['validation'] = validation.map(lambda wav, target, split: {'audio': wav, 'label': target})
    splited_dataset['eval'] = eval.map(lambda wav, target, split: {'audio': wav, 'label': target})

    return splited_dataset, new_classes

def load_certificate(path):

    classes = ['NONE', 'SLEEP-REM', 'SLEEP-S0', 'SLEEP-S1', 'SLEEP-S2', 'SLEEP-S3']
    map_class_to_id = {'NONE': 0, 'SLEEP-REM': 3, 'SLEEP-S0': 0, 'SLEEP-S1': 1, 'SLEEP-S2': 2, 'SLEEP-S3': 2}
    new_classes = ['wake', 'light', 'deep', 'REM']

    print(f'Sleep Scoring Classes: {new_classes}')

    metadata = pd.DataFrame(columns=['filename', 'class'])
    for class_name in classes:
        tempdata = pd.DataFrame(columns=['filename', 'class'])
        tempdata['filename'] = [path + class_name + '/' + dirs for dirs in os.listdir(path + class_name)]
        tempdata['class'] = class_name
        class_id = tempdata['class'].apply(lambda name: map_class_to_id[name])
        tempdata = tempdata.assign(target=class_id)
        metadata = metadata.append(tempdata, ignore_index=True)

    return metadata, new_classes