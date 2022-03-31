import functools
import tensorflow_hub

from data import load
from models import import_model, model, ReduceMeanLayer

from typing import Dict, Mapping
import tensorflow as tf

from tflite_coverter import export_tflite


AUTOTUNE = tf.data.experimental.AUTOTUNE


def preprocess(inputs: Mapping[str, tf.Tensor]):
  """Sequentially applies the transformations to the waveform."""
  _, audio, _ = yamnet_model(inputs['audio'])
  num_embeddings = tf.shape(audio)[0]
  label = inputs['label']
  return (audio, tf.repeat([label], repeats=[num_embeddings], axis=0))

def extract_embedding(datasets: Dict[str, tf.data.Dataset]) -> Dict[str, tf.data.Dataset]:
    """ Run YAMNet to extract embedding"""
    result = {}
    for split in ['train', 'validation', 'eval']:
        ds = datasets[split]
        ds = ds.map(functools.partial(preprocess), num_parallel_calls=AUTOTUNE)
        result[split] = ds.prefetch(AUTOTUNE)
    return result

def split_data(dataset):
    cache = dataset.cache()
    train = cache.filter(lambda embedding, label, fold: fold < 4)
    validation = cache.filter(lambda embedding, label, fold: fold == 4)
    test = cache.filter(lambda embedding, label, fold: fold == 5)

    column = lambda embedding, label, fold: (embedding, label)

    train = train.map(column).cache().shuffle(1000).batch(32).prefetch(tf.data.AUTOTUNE)
    validation = validation.map(column).batch(32).prefetch(tf.data.AUTOTUNE)
    test = test.map(column).batch(32).prefetch(tf.data.AUTOTUNE)
    return train, validation, test


if __name__ == "__main__":
    learning_rate = 1e-3
    metric = 'sparse_categorical_accuracy'
    num_epochs = 300

    yamnet_model, class_names = import_model('yamnet')
    print(f'Number of classes: {len(class_names)}')
    print(f'Main Classes: {class_names}')

    sleep_scoring_path = 'D:/database/SMC PSG dataset/result/on-device/2/sleep scoring/'
    dataset, classes = load(path=sleep_scoring_path)
    print(dataset)
    dataset = extract_embedding(dataset)
    # dataset = dataset.map(extract_embedding)
    print("After embedding: ")
    print(dataset)

    model = model(classes)
    print(model.summary())
    model.compile(
        loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),
        optimizer="adam",
        metrics=['accuracy']
    )
    ckpt_path = './temp/checkpoint'
    callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=ckpt_path,
        save_weights_only=True,
        monitor=f'val_{metric}',
        mode='max',
        save_best_only=True
    )
    history = model.fit(
        dataset['train'],
        validation_data=dataset['validation'],
        epochs=num_epochs,
        callbacks=callback
    )
    loss, accuracy = model.evaluate(dataset['eval'])
    print(f'Loss: {loss}')
    print(f'Accuracy: {accuracy}')

    saved_model_path = './results/sleep_sound_model/class 4/sample'

    input_segment = tf.keras.layers.Input(shape=(), dtype=tf.float32, name='audio')
    embedding_extraction_layer = tensorflow_hub.KerasLayer(
        'https://tfhub.dev/google/yamnet/1',
        trainable=False,
        name='YAMNet'
    )
    _, embedding_output, _ = embedding_extraction_layer(input_segment)
    serving_outputs = model(embedding_output)
    serving_outputs = ReduceMeanLayer(axis=0, name='classifier')(serving_outputs)
    serving_model = tf.keras.Model(input_segment, serving_outputs)
    serving_model.save(saved_model_path, include_optimizer=False)

    print(serving_model.summary())

    export_tflite(saved_model_path)
