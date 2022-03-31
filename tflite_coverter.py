import os

import tensorflow as tf


def export_tflite(saved_model_dir):
  converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
  tflite_model = converter.convert()

  converted_model_path = os.path.join(saved_model_dir, 'converted_model.tflite')
  open(converted_model_path, "wb").write(tflite_model)