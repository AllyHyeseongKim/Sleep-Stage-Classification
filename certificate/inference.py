from data import load_certificate, load_wav_16k_mono

import tensorflow as tf


def inference():
    true = 0
    false = 0
    flag = true
    result_csv_path = "./result.csv"
    new = open(result_csv_path, "a")
    new.write("filename,ground truth,predicted,result\n")

    sleep_scoring_path = 'C:/Users/AllyHyeseongKim/PycharmProjects/Sleep-Stage-Classification/certificate/dataset/audio/'
    dataset, map_classes = load_certificate(path=sleep_scoring_path)
    print(dataset)

    saved_model_path = '../results/sleep_sound_model/class 4/sample'
    saved_model = tf.saved_model.load(saved_model_path)

    for test_data in dataset.to_numpy():
        filename = test_data[0]
        label = int(test_data[2])
        wav = load_wav_16k_mono(filename)
        model_result = saved_model(wav)
        pred = tf.argmax(model_result).numpy()

        if label == pred:
            true += 1
            flag = "true"
        else:
            false += 1
            flag = "false"

        filename = "/".join(filename.split("/")[-2:])
        new.write(filename + "," + map_classes[label] + "," + map_classes[pred] + "," + flag + "\n")

    accuracy = true/(true+false)*100
    print(f"Test Accuracy: {accuracy}%")
    new.write("\n")
    new.write("\n")
    new.write("result," + str(accuracy) + "%\n")

    new.close()
