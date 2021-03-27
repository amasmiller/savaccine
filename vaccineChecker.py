#!/usr/bin/python3

# TODO
# 
# cleanup documentation and TODOs
#
# possibly add other sites
# - https://www.walgreens.com/findcare/vaccination/covid-19/location-screening#!
# - https://www.cvs.com/immunizations/covid-19-vaccine
#
# test on different size devices
#
#

import traceback
import requests
import signal
import argparse
import os
import time
import smtplib
import sys
import smtplib
import random
import schedule
import syslog
import json
import re

from argparse import RawTextHelpFormatter
from datetime import datetime
from email.mime.text import MIMEText

PROGRAM_DESCRIPTION="""
    
    OVERVIEW:

    This program is a daemon for inspecting vaccine provider websites, 
    looking for confirmation of lack of phrases indicating availability.
    The result is written to a 'status.json' file in the directory 
    specified by --output-dir.
    
    This program expects a valid 'credentials.json' file in the directory
    specified by --input-dir.  This file should contain the authentication
    credentials for an SMTP server and login and an email recipient
    for status messages to be sent to.  Example 'credentials.json' file:
       {
       "email" : "foo@gmail.com",
       "password" : "bar",
       "recipient" : "foobar@tmomail.net",
       "smtp_host" : "smtp.myserver.com",
       "smtp_port" : 465
       }
    
    This program also expects a valid 'websites.json' file in the directory
    specified by --input dir.  This file defines the websites to query, along with 
    the positive/negative phrases to search for.  Example 'websites.json' file:
        [
            {
                "name": "UT Health San Antonio",
                "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
                "neg_phrase": "are full",
                "pos_phrase": "you confirm your understanding"
            }
        ]


    EXAMPLE USE (Command Line):

        # run the daemon with a request rate of 5 minutes (300 seconds), outputting
        # status to the 'status' directory
        ./vaccineChecker.py --input-dir input --output-dir status --request-rate 300

        # run the daemon with a request rate of 30 seconds, output status to
        # the 'out' directory
        ./vaccineChecker.py --input-dir input --output-dir out --request-rate 30

    REQUIREMENTS:

        This script was developed with Python 3.4.3 and the packages as specified
        by the import directives.

    """


'''
Utility function for logging.  Send to standard out and syslog.
'''
def DEBUG(x):
    logLine = "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x)
    sys.stdout.write(logLine)
    syslog.syslog(logLine)

'''
Handle Ctrl+C
'''
def SignalHandler(sig, frame):
    DEBUG("INFO: Program interrupted via Ctrl-C.  Exiting")
    sys.exit(0)

class vaccineChecker(object):

    ##############################################
    # to be populated by read of credentials.json
    EMAIL = ""
    PASSWORD = ""
    RECIPIENT = ""
    SMTP_HOST = ""
    SMTP_PORT = 0
    ##############################################

    MIN_REQUEST_RATE = 5 # seconds
    MAX_ATTEMPTS = 10000 # maximum runs of main while loop
    TIMEOUT = 10 # website access timeout (seconds)

    m_attempts = 0
    m_inputDir = "" # location of credentials.json, websites.json, FAQ.md
    m_outputDir = "" # the directory were status.json gets written to
    m_requestRate = 0 # how often, in seconds, we should ask for website status

    # see input/websites.json
    m_websites = []

    '''
    Setup.
    '''
    def __init__(self, inputDir, outputDir, requestRate):

        self.m_inputDir = inputDir
        self.m_outputDir = outputDir
        self.m_requestRate = requestRate

        # for confirmation things are going ok, send a text/email
        schedule.every(30).minutes.do(self.heartbeat)

        self.read_credentials()
        self.read_websites()

        self.send_message("INFO: Starting Up!")

   
    '''
    Read in credentials.json.
    '''
    def read_credentials(self):

        filename = self.m_inputDir + "/credentials.json"
        example = ''' 
{
"email" : "foo@gmail.com",
"password" : "bar",
"recipient" : "foobar@tmomail.net",
"smtp_host" : "smtp.myserver.com",
"smtp_port" : 465
}
        '''
        if (not os.path.exists(filename)):
            DEBUG("ERROR: " + filename + ' file not found, exiting. example file contents: ' + example)
            sys.exit(-1)

        try:
            f = open(filename)
            c = json.loads(f.read())
            f.close()
            self.EMAIL = c['email']
            self.PASSWORD = c['password']
            self.RECIPIENT = c['recipient']
            self.SMTP_HOST = c['smtp_host']
            self.SMTP_PORT = c['smtp_port']
            DEBUG("INFO: Successfully read credentials file.")
        except Exception as e:
            DEBUG("ERROR: Problem reading file " + filename + '. valid example content: ' + example)
            DEBUG(traceback.format_exc())
            sys.exit(-1)

    '''
    Read in websites.json.
    '''
    def read_websites(self):
        filename = self.m_inputDir + "/websites.json"
        example = ''' 
{
    "name": "UT Health San Antonio",
    "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
    "neg_phrase": "are full",
    "pos_phrase": "you confirm your understanding",
}
        '''
        if (not os.path.exists(filename)):
            DEBUG("ERROR: " + filename + ' file not found, exiting. example file contents: ' + example)
            sys.exit(-1)

        try:
            f = open(filename)
            self.m_websites = json.loads(f.read())

            # initialize things the user doesn't supply
            for site in self.m_websites:
                if "status" not in site:
                    site["status"] =  "probably not"
                if "update_time" not in site:
                    site["update_time"] = ""

            f.close()
        except Exception as e:
            DEBUG("ERROR: Problem reading file " + filename + '. valid example content: ' + example)
            DEBUG(traceback.format_exc())
            sys.exit(-1)

    '''
    Given a string, logs it and sends an email to RECIPIENT ,
    using the credentials in EMAIL and PASSWORD.
    '''
    def send_message(self, msg):
        DEBUG(msg)

        msg = "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
        msg = MIMEText(msg)
        msg['Subject'] = 'Vaccine Checker Script'
        msg['From'] = self.EMAIL
        msg['To'] = self.RECIPIENT

        DEBUG("INFO: Attempting to send email...")
        server = smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT)
        server.login(self.EMAIL, self.PASSWORD)
        server.sendmail(self.EMAIL, self.RECIPIENT, str(msg))
        server.quit()
        DEBUG("INFO: Successfully sent email!")


    '''
    Utility function to let someone know the script is running a-ok.
    '''
    def heartbeat(self):
        self.send_message("INFO: I'm alive! (%d)" % (self.m_attempts))

    '''
    Handle when a website status changes (i.e. from "probably not" to "maybe")
    '''
    def handle_status(self, s, i):
        if s != self.m_websites[i]['status']:
            self.send_message("INFO: %s changed to %s" % (self.m_websites[i]['website'], s))
        else:
            DEBUG("INFO: still %s, not sending message" % (s))
        self.m_websites[i]['status'] = s


    '''
    primary loop.  query the self.m_websites and keep track of status.
    '''
    def run(self):

        # primary loop
        while self.m_attempts < self.MAX_ATTEMPTS:

            for i in range(0, len(self.m_websites)):
                try:
                    DEBUG("asking %s at %s ..." % (self.m_websites[i]['name'], self.m_websites[i]['website']))
                    r = requests.get(self.m_websites[i]['website'], timeout=self.TIMEOUT, verify=False)
                    html = re.sub("(<!--.*?-->)", "", r.text, flags=re.DOTALL) # remove HTML comments, outdated information sometimes lives here

                    if self.m_websites[i]['pos_phrase'] != "" and self.m_websites[i]['pos_phrase'] in html:
                        self.handle_status("probably", i)
                    elif self.m_websites[i]['neg_phrase'] in html:
                        self.handle_status("probably not", i)
                    else:
                        self.handle_status("maybe", i)

                    self.m_websites[i]['update_time'] = time.strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception as e:
                    if isinstance(e, requests.exceptions.Timeout):
                        DEBUG("Timeout: " + str(e) + "...continuing")
                        continue
                    else:
                        DEBUG(traceback.format_exc())
                        self.send_message("Other Error of type %s : %s ... exiting." % (type(e).__name__, str(e)))
                        sys.exit(-1)
    
            try:
                # populate the file we use for communication with PHP
                if (not os.path.exists(self.m_outputDir)):
                    os.makedirs(self.m_outputDir)
                STATUS_JSON_FILENAME = "status.json" 
                content = json.dumps(self.m_websites, indent=4)
                f = open(self.m_outputDir + "/" + STATUS_JSON_FILENAME, "w")
                f.write(content)
                f.close()

                # save off all that we make
                ARCHIVE_DIR = self.m_outputDir + "/archive"
                if (not os.path.exists(ARCHIVE_DIR)):
                    os.makedirs(ARCHIVE_DIR)
                filename = ARCHIVE_DIR + "/" + STATUS_JSON_FILENAME + "." + (datetime.now().strftime("%Y-%m-%d_%H%M%S"))
                f = open(filename, "w")
                f.write(content)
                f.close()
                DEBUG("Wrote %s" % (filename))
                
                # give the good server some time to rest
                VARIANCE = 10 # seconds
                sleeptime = random.randint(max(self.MIN_REQUEST_RATE, self.m_requestRate - VARIANCE), max(self.MIN_REQUEST_RATE, self.m_requestRate + VARIANCE))
                DEBUG("checking again in %d seconds..." % (sleeptime))
                time.sleep(sleeptime)

                schedule.run_pending()
                self.m_attempts += 1

            except Exception as e:
                DEBUG(traceback.format_exc())
                self.send_message("Error during processing of type %s : %s ... exiting." % (type(e).__name__, str(e)))
                sys.exit(-1)

if __name__ == "__main__":

    signal.signal(signal.SIGINT, SignalHandler)

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=RawTextHelpFormatter)

    parser.add_argument(
            '--input-dir',
            action="store",
            dest="inputDir",
            help="The directory where 'credentials.json' and 'websites.json' will be read from.  Default directory is 'input'.",
            required=False,
            metavar='[X]',
            default="input")

    parser.add_argument(
            '--output-dir',
            action="store",
            dest="outputDir",
            help="The directory where 'status.json' and the archives of it will be written to.  Default directory is 'status'.",
            required=False,
            metavar='[X]',
            default="status")

    parser.add_argument(
            '--request-rate',
            action="store",
            dest="requestRate",
            help="How often, in seconds, the status will be requested from the sites in 'websites.json'.",
            required=False,
            metavar='[X]',
            default=5*60)

    args = parser.parse_args()

    try:
        args.requestRate = int(args.requestRate)
    except Exception as e:
        DEBUG("ERROR: --request-rate must be a number")
        sys.exit(-1)

    vc = vaccineChecker(args.inputDir, args.outputDir, args.requestRate)
    vc.run()
