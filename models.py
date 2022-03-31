import pandas as pd

import tensorflow as tf
import tensorflow_hub as hub


def import_model(vggish):
    if vggish == 'yamnet':
        yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')
        class_map_path = yamnet_model.class_map_path().numpy().decode('utf-8')
        class_names = list(pd.read_csv(class_map_path)['display_name'])
        return yamnet_model, class_names

def model(classes):
    return tf.keras.Sequential([
        tf.keras.layers.Input(shape=1024, dtype=tf.float32, name='input_embedding'),
        tf.keras.layers.Dense(512, activation='relu'),
        tf.keras.layers.Dense(len(classes))
    ], name='model')

class ReduceMeanLayer(tf.keras.layers.Layer):
    def __init__(self, axis=0, **kwargs):
        super(ReduceMeanLayer, self).__init__(**kwargs)
        self.axis = axis

    def call(self, input):
        return tf.math.reduce_mean(input, axis=self.axis)