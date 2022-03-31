import csv
from datetime import datetime
from datetime import timedelta
import re
import sys

# Known events and corresponding integer codes
EVENT_CODE = {
    "NONE": 0,

    "APNEA-CENTRAL": 1,
    "APNEA-MIXED": 2,
    "APNEA-OBSTRUCTIVE": 3,
    "HYPOPNEA": 4,
    "AROUSAL-RERA": 5,
    "AROUSAL-RESP": 6,
    "POSITION-SUPINE": 7,

    # SNORE_SINGLE == SNORE
    "SNORE": 8,
    "SNORE-SINGLE": 8,

    "SLEEP-S0": 10,
    "SLEEP-S1": 11,
    "SLEEP-S2": 12,
    "SLEEP-S3": 13,
    "SLEEP-REM": 14,
    "N/A": 15,
}

DEVICE_REGEX = "go[0-9]{3}"
FIRST_LINE = "Device,Trial,Sleep Stage,Time,Event,Event ID,Duration"


# Read TSV file from storage
def import_tsv_content(file_name):
    return_value = []

    # Try with utf-8 first
    try:
        file = open(file_name, "r", encoding="utf-8")
        tr = csv.reader(file, delimiter='\t')
        for row in tr:
            if row != "":
                return_value += [row]

    # If failed, use default cp949
    except:
        file = open(file_name, "r")
        tr = csv.reader(file, delimiter='\t')
        for row in tr:
            if row != "":
                return_value += [row]

    return return_value


# Trim unneeded content from imported TSV list
def trim_imported_tsv_content(tsv_content_array):
    # Trim header information
    trim_anchor_head = ['Sleep Stage', 'Position', 'Time [hh:mm:ss]', 'Event', 'Duration[s]']
    trim_anchor_head_index = tsv_content_array.index(trim_anchor_head)
    temp = []
    for line in tsv_content_array:
        temp.append([line[0]]+line[2:])
    tsv_content_array = temp

    # Trim hanging line breaks
    trim_anchor_tail = len(tsv_content_array)
    while True:
        if not tsv_content_array[trim_anchor_tail - 1]:
            trim_anchor_tail -= 1
        else:
            break

    # Return
    return tsv_content_array[trim_anchor_head_index + 1:trim_anchor_tail]


# Format Korean time into integer list
def convert_time(date_string, time_string):
    # Extract date from string
    date = date_string.split("-")
    year = int(date[0])
    month = int(date[1])
    day = int(date[2])

    # Hour conversion :
    # 오전 12시 -> 0
    # 오후 1시 -> 13
    time = time_string.split(":")
    if time[0].startswith("오전"):
        hour = time[0].replace("오전 ", "")
        if hour == "12":
            hour = 0
        hour = int(hour)
    elif time[0].startswith("오후"):
        hour = time[0].replace("오후 ", "")
        if hour != "12":
            hour = int(hour) + 12
        hour = int(hour)
    else:
        hour = int(time[0])

    # Minute/second parse
    minute = int(time[1])
    second = int(time[2])

    # Return
    return_value = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=0)
    return return_value


# Check date validity by splitting and casting to integer
def check_date_valid(string):
    tmp = string.split("-")
    if len(tmp) == 3:
        try:
            int(tmp[0])
            int(tmp[1])
            int(tmp[2])
            return True
        except:
            return False
    else:
        return False


# Use device name regular expression to check device name validity
def check_device_valid(string):
    regex = re.compile(DEVICE_REGEX)
    if regex.search(string):
        return True
    return False


# Each row's info of the tsv file is stored using Iter
# get_row returns a string in csv row format
class Iter:
    def __init__(self, device, trial, sleep_stage, full_time, event, duration):
        self.device = device
        self.trial = int(trial)
        self.sleep_stage = EVENT_CODE[sleep_stage]
        self.time = full_time
        self.event_id = EVENT_CODE[event]
        if event == "SNORE-SINGLE":
            event = "SNORE"
        self.event = event
        self.duration = int(duration)

    def get_row(self):
        return str(self.device) + "," + str(self.trial) + "," + str(self.sleep_stage) + "," + str(self.time) + "," + \
               str(self.event) + "," + str(self.event_id) + "," + str(self.duration)


#
def import_file(device, trial, date, init_date, file_name):
    # Select file
    imported_content = import_tsv_content(file_name)

    # Init
    trimmed_content = trim_imported_tsv_content(imported_content)
    container = []

    # Next day calculation
    offset = 0
    if len(trimmed_content) == 0:
        return []
    if convert_time(date, trimmed_content[0][1]) < init_date:
        offset = 1

    # Content iteration
    for i in range(0, len(trimmed_content)):
        item = trimmed_content[i]

        # Next day calculation
        if 0 < i:
            if trimmed_content[i - 1][1] > trimmed_content[i][1]:
                offset += 1

        iteration = Iter(device=device, trial=trial, sleep_stage=item[0],
                         full_time=convert_time(date, item[1]) + timedelta(days=offset),
                         event=item[2], duration=item[3])
        container.append(iteration)
    return container


def fetch_initial_data(tsv_name, wav_name):
    # Parsing
    device = tsv_name[0:5]
    trial = int(tsv_name[6:7])
    year = int(wav_name[0:4])
    month = int(wav_name[4:6])
    day = int(wav_name[6:8])
    # todo : muted - no global start of recording across recorded files
    # hour = int(wav_name[9:11])
    # minute = int(wav_name[11:13])
    # second = int(wav_name[13:15])

    return {
        "device": device,
        "trial": trial,
        "year": year,
        "month": month,
        "day": day,
        # todo : muted - no global start of recording across recorded files
        # "hour": hour,
        # "minute": minute,
        # "second": second,
        "date": str(year) + "-" + str(month) + "-" + str(day),

        "full_time": datetime(year=year, month=month, day=day, hour=0, minute=0, second=0,
                              microsecond=0),
        # todo : replaced - no global start of recording across recorded files
        # "full_time": datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second,
        #                       microsecond=0),
    }


def diff_datetime(first, second):
    if second > first:
        diff = second - first
    else:
        diff = first - second
    return diff


def none_fill(array, global_info):
    base_list = sorted(array, key=lambda iter: iter.time)
    none_list = []

    # Fill with none only if array is not empty:
    if len(array) != 0:
        # Add head none
        # todo : muted - no global start of recording across recorded files
        # if global_info["full_time"] < base_list[0].time:
        #     none_list.append(Iter(device=global_info["device"], trial=global_info["trial"],sleep_stage="NONE",
        #                           full_time=global_info["full_time"], event="NONE",
        #                           duration=diff_datetime(base_list[0].time, global_info["full_time"]).seconds))

        # Add consecutive nones
        for i in range(0, len(base_list) - 1):
            end_of_i = base_list[i].time + timedelta(seconds=base_list[i].duration)
            if end_of_i < base_list[i + 1].time:
                none_list.append(Iter(device=global_info["device"], trial=global_info["trial"],
                                      sleep_stage="NONE", full_time=end_of_i,
                                      event="NONE", duration=diff_datetime(base_list[i + 1].time, end_of_i).seconds))

        # Add tail none
        end_of_last_base = base_list[len(base_list) - 1].time + timedelta(
            seconds=base_list[len(base_list) - 1].duration)
        none_list.append(Iter(device=global_info["device"], trial=global_info["trial"], sleep_stage="NONE",
                              full_time=end_of_last_base, event="NONE", duration=-1))

    # Return
    return_list = base_list
    for iter in none_list:
        return_list.append(iter)
    return_list = sorted(return_list, key=lambda iter: iter.time)
    return return_list


def overlap_analysis(array):
    return_value = ""

    i = 0
    while True:
        if len(array) - 1 < i + 1:
            break
        else:
            start_time_1 = array[i].time
            end_time_1 = start_time_1 + timedelta(seconds=array[i].duration)
            start_time_2 = array[i + 1].time
            if end_time_1 > start_time_2:
                return_value += array[i].get_row() + "\n"
                return_value += array[i + 1].get_row() + "\n"
                j = 2
                while True:
                    if len(array) - 1 < i + j + 1:
                        break
                    start_time_loop = array[i + j].time
                    if end_time_1 > start_time_loop:
                        return_value += array[i + j].get_row() + "\n"
                        j += 1
                    else:
                        i = i + j
                        break

            i += 1

    return return_value


# Good night, world!
def convert(file_name, start_time):
    # CSV init
    export_value = FIRST_LINE + "\n"

    filename_split = file_name.split("\\")
    short_filename = filename_split[len(filename_split) - 1]

    # Input global information
    # Actual time not specified "Recording Date" of tsv - manual input required
    global_info = fetch_initial_data(short_filename, start_time)

    # Scan each file
    compilation = []
    compilation += import_file(device=global_info["device"], trial=global_info["trial"], date=global_info["date"],
                               init_date=global_info["full_time"], file_name=file_name)

    # Check for overlaps - BEFORE NONES ARE FILLED
    overlaps = overlap_analysis(compilation)

    # Fill gaps with event NONE
    none_filled = none_fill(array=compilation, global_info=global_info)
    for item in none_filled:
        export_value += item.get_row() + "\n"

    # Export file
    f = open("/certificate/dataset/go020_1_sleep scoring.csv", 'w')
    f.write(export_value)
    f.close()

    # Export overlaps if not empty
    if len(overlaps) != 0:
        f = open("./certificate/dataset/output_overlap.csv", 'w')
        f.write(FIRST_LINE + "\n" + overlaps)
        f.close()

    # Exit
    return True


# Standalone mode
if __name__ == '__main__':
    # Check

    if len(sys.argv) == 3:
        manual = False
        file_name = sys.argv[1]
        start_time = sys.argv[2]
    else:
        manual = True
        file_name = input("file path? : ")
        start_time = input("when did recording start? (as yyyyMMdd) : ")
        # todo : replaced - no global start of recording across recorded files
        # start_time = input("when did recording start? (as yyyyMMdd_HHmmss) : ")

    convert(file_name, start_time)
    print("converted as go020_1_sleep scoring.csv")

