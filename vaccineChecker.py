#!/usr/bin/python3

# TODO
# input argument for credentials.json
# input / output dirs
# look for other sites
# more testing. script?

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

    This program is meant to be a daemon to run in background for querying 
    vaccine provider websites, looking for confirmation or lack of phrases
    indicating availabiltiy, and outputting a 'status.json' file, which is
    used as an input to 'status.php'
    
    This program expects a valid 'credentials.json' file in the same
    directory with contents similar to:
       {
       "email" : "foo@gmail.com",
       "password" : "bar",
       "recipient" : "foobar@tmomail.net",
       "smtp_host" : "smtp.myserver.com",
       "smtp_port" : 465
       }

    EXAMPLE USE (Command Line):

        TODO 

    REQUIREMENTS:

        This script requires Python TODO and packages TODO.

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

    MAX_ATTEMPTS = 10000 # maximum runs of main while loop
    TIMEOUT = 10 # website access timeout (seconds)
    QUERY_TIME = 16 # how often to ask (minimum 15)

    m_attempts = 0
    m_outputDir = "" # where status.json and it's archive friends end up

    # name, website, phrases to look for, etc..
    m_websites = [
        {
            "name": "UT Health San Antonio",
            "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
            "neg_phrase": "are full",
            "pos_phrase": "you confirm your understanding",
            "status": "probably not",
            "update_time": "",
        },
        {
            "name": "University Health",
            "website": "https://www.universityhealthsystem.com/coronavirus-covid19/vaccine/vaccine-appointments",
            "neg_phrase": "currently no vaccine",
            "pos_phrase": "A small number of",
            "status": "probably not",
            "update_time": "",
        },
        {
            "name": "San Antonio Metro Health",
            "website": "https://covid19.sanantonio.gov/Services/Vaccination-for-COVID-19?lang_update=63752022779168615",
            "neg_phrase": "Please check back",
            "pos_phrase": "",
            "status": "probably not",
            "update_time": "",
        },
        # for debugging
        {
            "name": "Test Site",
            "website": "https://amasmiller.com/savaccine/test.php",
            "neg_phrase": "this is a bad phrase",
            "pos_phrase": "this is a good phrase",
            "status": "probably not",
            "update_time": "",
        },
    ]

    '''
    Setup.
    '''
    def __init__(self, outputDir):

        self.m_outputDir = outputDir

        # for confirmation things are going ok, send a text/email
        schedule.every(30).minutes.do(self.heartbeat)

        # load credentials
        filename = "credentials.json"
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
            c = json.load(f)
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

        self.send_message("INFO: Starting Up!")

    '''
    Given a string, logs it and sends an email to RECIPIENT ,
    using the credentials in EMAIL and PASSWORD.
    '''
    def send_message(self, msg):
        DEBUG(msg)

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
        self.send_message("INFO: I'm alive! (%d)" % (attempts))

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
                    html = re.sub("(<!--.*?-->)", "", r.text, flags=re.DOTALL) # remove HTML comments

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

            # populate the file we use for communication with PHP
            if (not os.path.exists(self.m_outputDir)):
                os.makedirs(self.m_outputDir)
            STATUS_JSON_FILENAME = self.m_outputDir + "/status.json" 
            content = json.dumps(self.m_websites, indent=4)
            f = open(STATUS_JSON_FILENAME, "w")
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
                    
            sleeptime = random.randint(self.QUERY_TIME-15, self.QUERY_TIME+15)
            DEBUG("checking again in %d seconds..." % (sleeptime))
            time.sleep(sleeptime)

            schedule.run_pending()
            self.m_attempts += 1

if __name__ == "__main__":

    signal.signal(signal.SIGINT, SignalHandler)

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=RawTextHelpFormatter)

    parser.add_argument(
            '--output-dir',
            action="store",
            dest="outputDir",
            help="The directory where 'status.json' and the archives of it will be written to",
            required=False,
            metavar='[X]',
            default=".")

    args = parser.parse_args()

    vc = vaccineChecker(args.outputDir)
    vc.run()
