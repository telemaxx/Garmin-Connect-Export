from datetime import timedelta
import os


####################################################################################################################
# Updates:
# rsjrny    13 May 2019 New file for universal functions
####################################################################################################################


def vprintmsg(verbose, message):
    if verbose:
        print(message)


def removefiles(dir):
    for filename in os.listdir(dir):
        if (filename.endswith('.json')) or (filename.endswith('csv')):
            # print("debug filename: ", filename)
            os.remove(dir + "\\" + filename)


def kmh_from_mps(mps):
    """Helper function that converts meters per second (mps) to km/h."""
    return str(mps * 3.6)


def hhmmss_from_seconds(sec):
    """Helper function that converts seconds to HH:MM:SS time format."""
    if isinstance(sec, float):
        formatted_time = str(timedelta(seconds=int(sec))).zfill(8)
    else:
        formatted_time = "0.000"
    return formatted_time


def decoding_decider(format, data):
    """Helper function that decides if a decoding should happen or not."""
    if format == "original":
        # An original file (ZIP file) is binary and not UTF-8 encoded
        data = data
    elif data:
        # GPX and TCX are textfiles and UTF-8 encoded
        data = data.decode()

    return data


def write_to_file(filename, content, mode):
    """Helper function that persists content to file."""
    write_file = open(filename, mode)
    write_file.write(content)
    write_file.close()
