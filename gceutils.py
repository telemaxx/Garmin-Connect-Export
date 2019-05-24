import logging
import os
from datetime import timedelta
from zipfile import ZipFile

####################################################################################################################
# Updates:
# rsjrny    13 May 2019 New file for universal functions
####################################################################################################################
log = logging.getLogger(__name__)


# Zip the files from given directory that matches the filter
def zipfilesindir(dirname, zipfilename, filterlist):
    log.debug("we are in gceutils.py zipfile")
    # create a ZipFile object
    with ZipFile(dirname + zipfilename, 'w') as zipObj:
        abs_src = os.path.abspath(dirname)
        # Iterate over all the files in directory
        for filename in os.listdir(dirname):
            # build arcname to remove path from archive
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            # extract the file extension from the filename. tfn is name part of the split
            tfn, fileext = os.path.splitext(filename)
            # print if verbose
            log.debug("tfn = " + tfn + "  fileext = " + fileext)
            if fileext in filterlist:
                # create complete filepath of file in directory
                filepath = os.path.join(dirname, filename)
                # Add file to zip
                zipObj.write(filepath, arcname)
                log.debug("adding: " + str(filepath) + " to " + absname)
        # close the Zip File
        zipObj.close()
        log.info("Archive created: " + dirname + zipfilename)


def removefiles(dirname):
    for filename in os.listdir(dirname):
        if (filename.endswith('.json')) or (filename.endswith('csv')):
            # print("debug filename: ", filename)
            os.remove(dirname + "\\" + filename)


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


def decoding_decider(formattype, data):
    """Helper function that decides if a decoding should happen or not."""
    if formattype == "original":
        # An original file (ZIP file) is binary and not UTF-8 encoded
        data = data
    elif data:
        # GPX and TCX are textfiles and UTF-8 encoded
        data = data.decode()

    return data


def write_to_file(filename, content, mode):
    """Helper function that persists content to file."""
    if content == '':
        content = 'empty file, no data existed in the downloaded file'
    write_file = open(filename, mode)
    write_file.write(content)
    write_file.close()
