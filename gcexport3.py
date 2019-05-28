#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
File: gcexport.py
Original author: Kyle Krafka (https://github.com/kjkjava/)
Date: April 28, 2015
Fork author: Michael P (https://github.com/moderation/)
Date: August 25, 2018
Updates: Russ Lilley
Date: May 12, 2019
Description:    Use this script to export your fitness data from Garmin Connect.
                See README.md for more information.



"""

####################################################################################################################
# Updates:
# rsjrny    22 May 2019 Replaced verbose print with logging
# rsjrny    13 May 2019 Added --verbose
# rsjrny    13 may 2019 Added -JSON [y , n] to keep or delete the JSON and CSV files
# rsjrny    13 May 2019 Added a delay between files to eliminated http timeouts and file in use conditions
# rsjrny    13 May 2019 Fixed the fit_filename so the skip already downloaded would work
# rsjrny    13 May 2019 Moved various functions to the gceutils.py file
####################################################################################################################


import argparse
import json
import logging
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from getpass import getpass
from os import mkdir, remove, stat
from os.path import isdir, isfile
from subprocess import call
from sys import argv
from xml.dom.minidom import parseString

import gceaccess
import gceargs
import gceutils

"""
def main():
    # put main stuff here
    print("in Main")
"""

# main()
log = logging.getLogger()
logging.basicConfig()
SCRIPT_VERSION = "1.0.0"
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
ACTIVITIES_DIRECTORY = "./" + CURRENT_DATE + "_garmin_connect_export"

# define the ARGs
PARSER = argparse.ArgumentParser()
gceargs.addargs(PARSER, ACTIVITIES_DIRECTORY)
ARGS = PARSER.parse_args()

if ARGS.verbose or ARGS.debug:
    log.setLevel(logging.DEBUG)

if ARGS.version:
    print(argv[0] + ", version " + SCRIPT_VERSION)
    exit(0)

print("Welcome to Garmin Connect Exporter!")

# Create directory for data files.
if isdir(ARGS.directory):
    print(
        "Warning: Output directory already exists. Will skip already-downloaded files and \
append to the CSV file."
    )

USERNAME = ARGS.username if ARGS.username else input("Username: ")
PASSWORD = ARGS.password if ARGS.password else getpass()

# Maximum number of activities you can request at once.  Set and enforced by Garmin.
LIMIT_MAXIMUM = 1000

try:
    gceaccess.gclogin(USERNAME, PASSWORD)
except Exception as error:
    print(error)
    exit(8)

# create the activities directory if it is not there
if not isdir(ARGS.directory):
    mkdir(ARGS.directory)

CSV_FILENAME = ARGS.directory + "/activities.csv"
CSV_EXISTED = isfile(CSV_FILENAME)
CSV_FILE = open(CSV_FILENAME, "a")
if not CSV_EXISTED:
    CSV_FILE.write(gceaccess.csvheader())

DOWNLOAD_ALL = False

if ARGS.count == "all":
    # If the user wants to download all activities, query the userstats
    # on the profile page to know how many are available
    user_stats = gceaccess.query_garmin_stats()

    # Persist JSON
    gceutils.write_to_file(ARGS.directory + "/userstats.json", user_stats.decode(), "a")

    # Modify total_to_download based on how many activities the server reports.
    JSON_USER = json.loads(user_stats)
    TOTAL_TO_DOWNLOAD = int(JSON_USER["userMetrics"][0]["totalActivities"])
else:
    TOTAL_TO_DOWNLOAD = int(ARGS.count)

TOTAL_DOWNLOADED = 0
TOTAL_SKIPPED = 0
TOTAL_RETRIEVED = 0
print("Total to download: " + str(TOTAL_TO_DOWNLOAD))

# This while loop will download data from the server in multiple chunks, if necessary.
while TOTAL_DOWNLOADED < TOTAL_TO_DOWNLOAD:
    # Maximum chunk size 'limit_maximum' ... 400 return status if over maximum.  So download
    # maximum or whatever remains if less than maximum.
    # As of 2018-03-06 I get return status 500 if over maximum
    if TOTAL_TO_DOWNLOAD - TOTAL_DOWNLOADED > LIMIT_MAXIMUM:
        NUM_TO_DOWNLOAD = LIMIT_MAXIMUM
    else:
        NUM_TO_DOWNLOAD = TOTAL_TO_DOWNLOAD - TOTAL_DOWNLOADED

    log.debug("Number left to download = " + str(NUM_TO_DOWNLOAD))

    SEARCH_PARAMS = {"start": TOTAL_DOWNLOADED, "limit": NUM_TO_DOWNLOAD}
    log.debug("Search parms" + str(SEARCH_PARAMS))

    # Query Garmin Connect
    log.debug("Activity list URL: " + gceaccess.URL_GC_LIST + urllib.parse.urlencode(SEARCH_PARAMS))
    ACTIVITY_LIST = gceaccess.http_req(gceaccess.URL_GC_LIST + urllib.parse.urlencode(SEARCH_PARAMS))
    gceutils.write_to_file(ARGS.directory + "/activity_list.json", ACTIVITY_LIST.decode(), "a")
    LIST = json.loads(ACTIVITY_LIST)

    # Process each activity.
    for a in LIST:
        # Display which entry we're working on.
        print("Garmin Connect activity: [" + str(a["activityId"]) + "]  " + a["activityName"])
        # print("\t" + a["uploadDate"]["display"] + ",", end=" ")
        data_filename = ""
        fit_filename = ""
        tcx_filename = ""
        gpx_filename = ""
        if ARGS.format == "gpx":
            data_filename = (ARGS.directory + "/" + str(a["activityId"]) + "_activity.gpx")
            download_url = gceaccess.URL_GC_GPX_ACTIVITY + str(a["activityId"]) + "?full=true"
            log.debug(download_url)
            file_mode = "w"
        elif ARGS.format == "tcx":
            data_filename = (ARGS.directory + "/" + str(a["activityId"]) + "_activity.tcx")
            download_url = gceaccess.URL_GC_TCX_ACTIVITY + str(a["activityId"]) + "?full=true"
            log.debug(download_url)
            file_mode = "w"
        elif ARGS.format == "original":
            data_filename = (ARGS.directory + "/" + str(a["activityId"]) + "_activity.zip")
            fit_filename = (ARGS.directory + "/" + str(a["activityId"]) + ".fit")
            tcx_filename = (ARGS.directory + "/" + str(a["activityId"]) + ".tcx")
            gpx_filename = (ARGS.directory + "/" + str(a["activityId"]) + ".gpx")
            download_url = gceaccess.URL_GC_ORIGINAL_ACTIVITY + str(a["activityId"])
            log.debug(download_url)
            file_mode = "wb"
        else:
            raise Exception("Unrecognized format.")

        if ARGS.format != "original" and isfile(data_filename):
            print("\tData file already exists; skipping...")
            TOTAL_SKIPPED += 1
            continue
        # Regardless of unzip setting, don't redownload if the ZIP or FIT file exists.
        # some original files only contain tcx or gpx - check for all types before downloading
        if ARGS.format == "original" \
                and (isfile(data_filename)
                     or isfile(fit_filename)
                     or isfile(tcx_filename)
                     or isfile(gpx_filename)):
            print("\tFIT data file already exists; skipping...")
            TOTAL_SKIPPED += 1
            continue

        data = gceaccess.download_data(download_url, ARGS.format)

        # Persist file
        TOTAL_RETRIEVED += 1
        # gceutils.write_to_file(data_filename, data, file_mode)
        gceutils.write_to_file(data_filename, gceutils.decoding_decider(ARGS.format, data), file_mode)

        log.debug("Activity summary URL: " + gceaccess.URL_GC_ACTIVITY + str(a["activityId"]))
        try:
            ACTIVITY_SUMMARY = gceaccess.http_req(gceaccess.URL_GC_ACTIVITY + str(a["activityId"]))
        except Exception as error:
            print("unable to get activity" + str(error))
            continue

        gceutils.write_to_file(ARGS.directory + "/" + str(a["activityId"]) + "_activity_summary.json",
                               ACTIVITY_SUMMARY.decode(), "a", )
        JSON_SUMMARY = json.loads(ACTIVITY_SUMMARY)
        log.debug(JSON_SUMMARY)

        log.debug("Device detail URL: " + gceaccess.URL_DEVICE_DETAIL
                  + str(JSON_SUMMARY["metadataDTO"]["deviceApplicationInstallationId"]))
        DEVICE_DETAIL = gceaccess.http_req(
            gceaccess.URL_DEVICE_DETAIL
            + str(JSON_SUMMARY["metadataDTO"]["deviceApplicationInstallationId"])
        )
        if DEVICE_DETAIL:
            gceutils.write_to_file(
                ARGS.directory + "/" + str(a["activityId"]) + "_app_info.json",
                DEVICE_DETAIL.decode(),
                "a",
            )
            JSON_DEVICE = json.loads(DEVICE_DETAIL)
            log.debug(JSON_DEVICE)
        else:
            log.debug("Retrieving Device Details failed.")
            JSON_DEVICE = None

        log.debug("Activity details URL: " + gceaccess.URL_GC_ACTIVITY + str(a["activityId"]) + "/details")
        try:
            ACTIVITY_DETAIL = gceaccess.http_req(
                gceaccess.URL_GC_ACTIVITY + str(a["activityId"]) + "/details"
            )
            gceutils.write_to_file(
                ARGS.directory + "/" + str(a["activityId"]) + "_activity_detail.json",
                ACTIVITY_DETAIL.decode(),
                "a",
            )
            JSON_DETAIL = json.loads(ACTIVITY_DETAIL)
            log.debug(JSON_DETAIL)
        except Exception as error:
            print("Retrieving Activity Details failed. Reason: " + str(error))
            JSON_DETAIL = None

        log.debug("Gear details URL: " + gceaccess.URL_GEAR_DETAIL + "activityId=" + str(a["activityId"]))
        GEAR_DETAIL = gceaccess.http_req(gceaccess.URL_GEAR_DETAIL + "activityId=" + str(a["activityId"]))
        try:
            gceutils.write_to_file(ARGS.directory + "/" + str(a["activityId"]) + "_gear_detail.json",
                                   GEAR_DETAIL.decode(),
                                   "a", )
            JSON_GEAR = json.loads(GEAR_DETAIL)
            log.debug(JSON_GEAR)
        except Exception as error:
            print("Retrieving Gear Details failed. Error: " + str(error))
            JSON_GEAR = None

        # CSV_FILE.write(csv_record)
        CSV_FILE.write(gceaccess.buildcsvrecord(a, JSON_SUMMARY, JSON_GEAR, JSON_DEVICE, JSON_DETAIL))

        if ARGS.format == "gpx" and data:
            # Validate GPX data. If we have an activity without GPS data (e.g., running on a
            # treadmill), Garmin Connect still kicks out a GPX (sometimes), but there is only
            # activity information, no GPS data. N.B. You can omit the XML parse (and the
            # associated log messages) to speed things up.
            gpx = parseString(data)
            if gpx.getElementsByTagName("trkpt"):
                log.debug("Done. GPX data saved.")
            else:
                log.debug("Done. No track points found.")
        elif ARGS.format == "original":
            # Even manual upload of a GPX file is zipped, but we'll validate the extension.
            if ARGS.unzip and data_filename[-3:].lower() == "zip":
                log.debug("Unzipping and removing original files...")
                try:
                    log.debug("Filesize is: " + str(stat(data_filename).st_size))
                except Exception as error:
                    print("Unable to determine file stats for " + data_filename + "Error: " + str(error))
                    continue
                if stat(data_filename).st_size > 0:
                    zip_file = open(data_filename, "rb")
                    z = zipfile.ZipFile(zip_file)
                    for name in z.namelist():
                        z.extract(name, ARGS.directory)
                    zip_file.close()
                else:
                    log.debug("Skipping 0Kb zip file.")
                remove(data_filename)
            log.debug("Done, getting next file")
            time.sleep(3)
        else:
            # TODO: Consider validating other formats.
            log.debug("Done, getting next file.")
    TOTAL_DOWNLOADED += NUM_TO_DOWNLOAD
# End while loop for multiple chunks.

CSV_FILE.close()


# delete the json and csv files before archiving. If requested
log.debug("--delete arg = " + str(ARGS.delete))
if ARGS.delete is not None:
    gceutils.removefiles(ARGS.directory, ARGS.delete)

# archive the downloaded files
if ARGS.archive:
    gceutils.zipfilesindir(ARGS.archive, ARGS.directory)

# print the final counts
print("Total Requested...." + str(TOTAL_TO_DOWNLOAD))
print("Total Downloaded..." + str(TOTAL_RETRIEVED))
print("Total Skipped......" + str(TOTAL_SKIPPED))

# open the csv file in an external program if requested
if len(ARGS.external):
    log.debug("Open CSV output: " + CSV_FILENAME)
    # open CSV file. Comment this line out if you don't want this behavior
    call([ARGS.external, "--" + ARGS.args, CSV_FILENAME])

print("Done!")
