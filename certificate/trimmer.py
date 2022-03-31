# use package ffmpeg-python, not ffmpeg
# make sure ffmpeg is installed on OS or venv
import ffmpeg

import sys
import os
import librosa
import csv
import shutil
from datetime import datetime
from datetime import timedelta
import asyncio
import time
import psutil


# keep format of batch.tsv - full path of audio for column 1, full path of csv for column 2, use \ for path
BATCH_FILE = "batch.tsv"


# move file to location
def move(source_path, target_path):
    shutil.move(source_path, target_path)


# convert two datetimes to create timestamp - under 24 hours
def datetime_to_timestamp(title_time, target_datetime):
    start_datetime = datetime.strptime(title_time, "%Y%m%d %H%M%S")
    diff = target_datetime - start_datetime
    return abs(diff.seconds)

# slice source_path from start_timestamp to finish_timestamp and save to target_path
def trim_wav(source_path, start_timestamp, finish_timestamp, target_path):
    # check if target file already exists -> doesn't exist
    if not os.path.isfile(target_path):
        # check ffmpeg process count
        while True:
            ffmpeg_counter = 0
            for proc in psutil.process_iter():
                try:
                    processName = proc.name()
                    if processName == "ffmpeg.exe":
                        ffmpeg_counter += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            # maximum of 8 ffmpegs may run simultaneously
            if ffmpeg_counter > 7:
                time.sleep(1)
            else:
                break

        # audio slice
        in_file = ffmpeg.input(source_path)
        audio_cut = in_file.audio.filter('atrim', start=start_timestamp, end=finish_timestamp)
        audio_output = ffmpeg.output(audio_cut, target_path)
        # waiting 0.2~0.5 seconds has positive impact on ffmpeg_async performance
        time.sleep(0.1)
        ffmpeg.run_async(audio_output, cmd=["ffmpeg", "-loglevel", "quiet", "-y"])

        # return log
        return str(target_path + " : " + str(start_timestamp) + " ~ " + str(finish_timestamp) + "\n")
    # check if target file already exists -> exists
    else:
        # return log
        return str("skipping " + str(start_timestamp) + " ~ " + str(finish_timestamp) + " because file exists" + "\n")


# uses source_audio_path, source_csv_path, line (of csv), counter (of events) to create an output path
# event is overridden as none if force_none is True
def path_calculator(source_audio_path, source_csv_path, line, counter, force_none=False):
    # determine event
    if force_none:
        event = "NONE"
    else:
        event = line[4]

    # calculate target directory and create parent directory
    target_path = source_audio_path.split("\\")
    csv_path = source_csv_path.split("\\")
    target_path = source_audio_path.replace(target_path[len(target_path) - 1], "") + "result\\" + target_path[
        len(target_path) - 1] + "-" + csv_path[len(csv_path) - 1]
    target_path = target_path + "\\" + event
    os.makedirs(target_path, exist_ok=True)

    # audio format - uncomment following 4 lines to use original audio format
    out_format = "wav"
    # if source_audio_path.endswith("wav"):
    #     out_format = "wav"
    # elif source_audio_path.endswith("mp3"):
    #     out_format = "mp3"

    # calculate target name
    target_name = line[0] + "_" + line[1] + "(" + str(counter[event]) + ")." + out_format

    # manipulate counter of event
    counter[event] = counter[event] + 1

    # finally calculate target path and return
    target_audio_path = target_path + "\\" + target_name
    return target_audio_path

# export log
def write_log(text, source_audio_path, source_csv_path):
    target_path = source_audio_path.split("\\")
    csv_path = source_csv_path.split("\\")
    target_path = source_audio_path.replace(target_path[len(target_path) - 1], "") + "result\\" + target_path[
        len(target_path) - 1] + "-" + csv_path[len(csv_path) - 1] + "\\log.txt"

    f = open(target_path, "w")
    f.write(text)
    f.close()

def trim_file(source_audio_path, source_csv_path):
    # Fetch csv content
    result = []
    try:
        file = open(source_csv_path, "r", encoding="utf-8")
        tr = csv.reader(file, delimiter=',')
        for row in tr:
            if row != "":
                result += [row]
    # If failed, use default cp949
    except:
        file = open(source_csv_path, "r")
        tr = csv.reader(file, delimiter=',')
        for row in tr:
            if row != "":
                result += [row]

    # manipulate audio path to get time of audio start as text
    source_audio_time = source_audio_path.replace(".wav", "")
    source_audio_time = source_audio_time.replace(".mp3", "")
    source_audio_time = source_audio_time.split("_")
    source_audio_time = source_audio_time[len(source_audio_time) - 2] + " " + source_audio_time[
        len(source_audio_time) - 1]

    # create/reset counter for each line of batch
    counter = {
        "NONE": 0,
        "APNEA-CENTRAL": 0,
        "APNEA-MIXED": 0,
        "APNEA-OBSTRUCTIVE": 0,
        "HYPOPNEA": 0,
        "AROUSAL-RERA": 0,
        "AROUSAL-RESP": 0,
        "POSITION-SUPINE": 0,
        "SNORE": 0,
        "SLEEP-S0": 0,
        "SLEEP-S1": 0,
        "SLEEP-S2": 0,
        "SLEEP-S3": 0,
        "SLEEP-REM": 0,
        "N/A": 0,
    }

    # exit if csv has only one line(title row)
    if len(result) < 2:
        return

    # fetch audio duration
    file_duration = librosa.get_duration(filename=source_audio_path)

    # init
    task_list = []
    log_compilation = ""

    # First none
    line = result[1]
    finish_datetime = datetime.strptime(line[3], "%Y-%m-%d %H:%M:%S")
    finish_timestamp = datetime_to_timestamp(source_audio_time, finish_datetime)
    if finish_timestamp > 0:
        target_audio_path = path_calculator(source_audio_path, source_csv_path, line, counter, force_none=True)
        log_line = trim_wav(source_audio_path, 0, finish_timestamp, target_audio_path)
        print(log_line, end = '')
        log_compilation += log_line


    # For each line of csv
    for i in range(1, len(result)):
        line = result[i]
        # Extract
        start_datetime = datetime.strptime(line[3], "%Y-%m-%d %H:%M:%S")
        duration = int(line[6])
        finish_datetime = start_datetime + timedelta(seconds=duration)

        # Rename/move to appropriate directory
        target_audio_path = path_calculator(source_audio_path, source_csv_path, line, counter)

        # Datetime to timestamp
        start_timestamp = datetime_to_timestamp(source_audio_time, start_datetime)
        finish_timestamp = datetime_to_timestamp(source_audio_time, finish_datetime)
        if finish_timestamp > file_duration:
            finish_timestamp = file_duration

        # Trim
        if start_timestamp < finish_timestamp:
            log_line = trim_wav(source_audio_path, start_timestamp, finish_timestamp, target_audio_path)
            print(log_line, end = '')
            log_compilation += log_line
        else:
            log_line = "skipping " + str(start_timestamp) + " ~ " + str(finish_timestamp) + " because start_timestamp is later than finish_timestamp or file_duration\n"
            print(log_line, end = '')
            log_compilation += log_line

    # Last none
    line = result[len(result) - 1]
    start_duration = int(line[6])
    if start_duration < 0:
        start_duration = 0
    start_datetime = datetime.strptime(line[3], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=start_duration)
    start_timestamp = datetime_to_timestamp(source_audio_time, start_datetime)
    if file_duration > start_timestamp:
        finish_datetime = datetime.strptime(result[1][3], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=file_duration)
        finish_timestamp = datetime_to_timestamp(source_audio_time, finish_datetime)
        target_audio_path = path_calculator(source_audio_path, source_csv_path, line, counter, force_none=True)
        log_line = trim_wav(source_audio_path, start_timestamp, finish_timestamp, target_audio_path)
        print(log_line, end = '')
        log_compilation += log_line


    write_log(log_compilation, source_audio_path, source_csv_path)


if __name__ == '__main__':
    # Check
    if len(sys.argv) == 3:
        manual = False
        wav_file = sys.argv[1]
        csv_file = sys.argv[2]
    else:
        manual = True
        wav_file = input("wav path? : ")
        csv_file = input("csv path? : ")

    print(trim_file(wav_file, csv_file))

