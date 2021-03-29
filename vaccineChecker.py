#!/usr/bin/python3

# standard libraries
import traceback
import requests
import signal
import argparse
import os
import time
import smtplib
import sys
import random
import urllib3
import syslog
import json
import re
import selenium
import urllib3
from datetime import datetime
from email.mime.text import MIMEText

# non-standard libraries
import schedule 
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

PROGRAM_DESCRIPTION="""
    
    OVERVIEW:

    This program is a daemon for inspecting vaccine provider websites, 
    looking for confirmation of lack of phrases indicating availability.
    The result is written to a 'status.json' file in the directory 
    specified by --output-dir.  Archives of the 'status.json' and the HTML
    content of the website changes are archived to the '[output-dir]/archive'
    directory.
    
    If the argument --alert-rate is passed, this program expects a 
    valid 'credentials.json' file in the directory
    specified by --input-dir.  This file should contain the authentication
    credentials for an SMTP server and login and email recipients
    for status messages to be sent to.  Example 'credentials.json' file:
       {
       "email" : "foo@gmail.com",
       "password" : "bar",
       "recipients" : "foobar@tmomail.net, myname@yahoo.com",
       "smtp_host" : "smtp.myserver.com",
       "smtp_port" : 465
       }
    
    This program always expects a valid 'websites.json' file in the directory
    specified by --input-dir.  This file defines the websites to query, along with 
    the positive/negative phrases to search for.  Example 'websites.json' file:

        "UT Health San Antonio" : {
            "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
            "neg_phrase": "are full",
            "pos_phrase": "you confirm your understanding"
        },
        "Test Site" : {
            "website": "http://mytestsite.com/mydirectory",
            "neg_phrase": "no",
            "pos_phrase": "yes",
        }

        TODO include walgreens, CVS, others supported


    EXAMPLE USE (Command Line):

        # run the daemon with a request rate of 5 minutes (300 seconds), outputting
        # status to the 'status' directory
        ./vaccineChecker.py --input-dir input --output-dir status --request-rate 300

        # run the daemon with a request rate of 30 seconds, output status to
        # the 'out' directory, and send an email heartbeat and erros to the 'recipients'
        # in 'credentials.json' every 60 minutes.
        ./vaccineChecker.py --input-dir input --output-dir out --request-rate 30 --alert-rate 60

    REQUIREMENTS:

        This script was developed with Python 3.4.3 and the packages as specified
        by the import directives.

        TODO urllib3, selenium version?

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
    RECIPIENTS =  []
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
    m_alertRate = 0 # how often, in minutes, we should send a emailed alert with script status

    # see input/websites.json
    m_websites = {}

    # for accessing sites that require special navigation
    m_sd = object()


    '''
    Setup.
    '''
    def __init__(self, inputDir, outputDir, requestRate, alertRate):

        DEBUG("INFO: Initializing....")

        self.m_inputDir = inputDir
        self.m_outputDir = outputDir
        self.m_requestRate = requestRate
        self.m_alertRate = alertRate

        urllib3.disable_warnings() # for ignoring InsecureRequestWarning for https

        # if configured, for confirmation things are going ok, send a text/email
        if (0 != self.m_alertRate):
            self.read_credentials()
            DEBUG("INFO: --alert-rate passed, configuring to send heartbeat message every %d minutes" % (self.m_alertRate))
            schedule.every(self.m_alertRate).minutes.do(self.heartbeat)
        else:
            DEBUG("INFO: --alert-rate not passed, no alerts will be sent.")

        self.send_message("INFO: Initalization complete!")
        
        self.read_websites()

        if "Walgreens" in self.m_websites or "CVS" in self.m_websites:
            DEBUG("INFO: Setting up selenium for queries requiring user navigation...")
            options = webdriver.firefox.options.Options()
            options.headless = True
            DEBUG("INFO: Creating selenium object...")
            self.m_sd = webdriver.Firefox(options=options)
            DEBUG("INFO: Done setting up selenium.")

   
    '''
    Read in credentials.json.
    '''
    def read_credentials(self):

        filename = self.m_inputDir + "/credentials.json"
        example = ''' 
{
"email" : "foo@gmail.com",
"password" : "bar",
"recipients" : "foobar@tmomail.net,myname@yahoo.com",
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
            self.RECIPIENTS = c['recipients']
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
            for name, info in self.m_websites.items():
                site = self.m_websites[name]
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
    Given a string, logs it.  If alerts are enabled, it sends an email to RECIPIENTS,
    using the credentials in EMAIL and PASSWORD.
    '''
    def send_message(self, s):

        DEBUG(s)
        if (self.m_alertRate == 0):
            return

        msg = "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s)
        msg = MIMEText(msg)
        msg['Subject'] = 'Vaccine Checker Script'
        msg['From'] = self.EMAIL
        msg['To'] = self.RECIPIENTS

        DEBUG("INFO: Attempting to send email with '%s'..." % (s))
        server = smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT)
        server.login(self.EMAIL, self.PASSWORD)
        server.sendmail(self.EMAIL, self.RECIPIENTS, str(msg))
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
    def handle_status(self, status, name, html):

        site = self.m_websites[name]
        if status != site['status']:
            self.send_message("INFO: %s changed to %s" % (name, status))

            # save off HTML that we make
            archive_dir = self.m_outputDir + "/archive"
            if (not os.path.exists(archive_dir)):
                os.makedirs(archive_dir)
            filename = archive_dir + "/" + name + ".html." + (datetime.now().strftime("%Y-%m-%d_%H%M%S"))
            f = open(filename, "w")
            f.write(html)
            f.close()
            DEBUG("INFO: Wrote %s" % (filename))
        else:
            DEBUG("INFO: still %s" % (status))

        site['status'] = status

    '''
    For querying the Walgreens page for availability.
    '''
    def query_walgreens(self):

        DEBUG("INFO: Requesting main page from Walgreens...")
        self.m_sd.get("https://www.walgreens.com/findcare/vaccination/covid-19")
        btn = self.m_sd.find_element_by_css_selector('span.btn.btn__blue')
        btn.click()
        DEBUG("INFO: Requesting next page from Walgreens...")
        self.m_sd.get("https://www.walgreens.com/findcare/vaccination/covid-19/location-screening")
        element = self.m_sd.find_element_by_id("inputLocation")
        element.clear()

        q = self.m_websites['Walgreens']['query']
        DEBUG("INFO: Asking Walgreens about the location '%s'" % (q))
        element.send_keys(q)
        button = self.m_sd.find_element_by_css_selector("button.btn")
        button.click()
        time.sleep(0.75)

        timeout = time.time() + 30 # 30 sec timeout
        DEBUG("INFO: Waiting for Walgreens result...")
        response = object()
        while True:
            if (time.time() > timeout):
                DEBUG("WARNING: Timeout waiting for Walgreens result, continuing")
            try:
                response = self.m_sd.find_element_by_css_selector("p.fs16")
                break
            except NoSuchElementException:
                time.sleep(0.5)

        DEBUG("INFO: Found Walgreens result '%s'" % (response.text))
        site = self.m_websites['Walgreens']
        if "Appointments unavailable" == response.text:
            DEBUG("INFO: Walgreens appointments are NOT available!")
            site['status'] = "probably not"
        elif "Please enter a valid city and state or ZIP" == response.text:
            DEBUG("WARNING: Walgreens rejected '%s' query as invalid" % (self.m_walgreensQuery))
            site['status'] = "probably not"
        else:
            DEBUG("INFO: Walgreens appointments are MAYBE available.")
            site['status'] = "maybe"

    '''
    For querying the CVS page for availability.
    '''
    def query_cvs(self):

        DEBUG("INFO: Requesting main page from CVS...")
        self.m_sd.get("https://www.cvs.com/immunizations/covid-19-vaccine")
#        btn = self.m_sd.find_element_by_css_selector('span.btn.btn__blue')
#        btn.click()
#        DEBUG("INFO: Requesting next page from Walgreens...")
#        self.m_sd.get("https://www.walgreens.com/findcare/vaccination/covid-19/location-screening")
#        element = self.m_sd.find_element_by_id("inputLocation")
#        element.clear()
#
#        q = self.m_websites['Walgreens']['query']
#        DEBUG("INFO: Asking Walgreens about the location '%s'" % (q))
#        element.send_keys(q)
#        button = self.m_sd.find_element_by_css_selector("button.btn")
#        button.click()
#        time.sleep(0.75)
#
#        timeout = time.time() + 30 # 30 sec timeout
#        DEBUG("INFO: Waiting for Walgreens result...")
#        response = object()
#        while True:
#            if (time.time() > timeout):
#                DEBUG("WARNING: Timeout waiting for Walgreens result, continuing")
#            try:
#                response = self.m_sd.find_element_by_css_selector("p.fs16")
#                break
#            except NoSuchElementException:
#                time.sleep(0.5)
#
#        DEBUG("INFO: Found Walgreens result '%s'" % (response.text))
#        site = self.m_websites['Walgreens']
#        if "Appointments unavailable" == response.text:
#            DEBUG("INFO: Walgreens appointments are NOT available!")
#            site['status'] = "probably not"
#        elif "Please enter a valid city and state or ZIP" == response.text:
#            DEBUG("WARNING: Walgreens rejected '%s' query as invalid" % (self.m_walgreensQuery))
#            site['status'] = "probably not"
#        else:
#            DEBUG("INFO: Walgreens appointments are MAYBE available.")
#            site['status'] = "maybe"
#

    '''
    primary loop.  query the self.m_websites and keep track of status.
    '''
    def run(self):

        # primary loop
        while self.m_attempts < self.MAX_ATTEMPTS:

            # query the entries that have a 'website'/'pos_phrase'/'neg_phrase'
            for name, info in self.m_websites.items():
                try:
                    site = self.m_websites[name]

                    # catch the special cases
                    if 'website' not in site:

                        # special cases that require website navigation
                        if ("Walgreens" == name):
                            self.query_walgreens()
                        elif ("CVS" == name):
                            self.query_cvs()
                        else:
                            DEBUG("WARNING: The site '%s' does not have a 'website' and is not a special case." % (name))
                    else:
                        # TODO move to function?
                        DEBUG("INFO: asking %s at %s ..." % (name, info['website']))
                        r = requests.get(site['website'], timeout=self.TIMEOUT, verify=False)
                        html = re.sub("(<!--.*?-->)", "", r.text, flags=re.DOTALL) # remove HTML comments, outdated information sometimes lives here

                        if site['pos_phrase'] != "" and site['pos_phrase'] in html:
                            self.handle_status("probably", name, html)
                        elif site['neg_phrase'] in html:
                            self.handle_status("probably not", name, html)
                        else:
                            self.handle_status("maybe", name, html)

                    site['update_time'] = time.strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception as e:
                    if isinstance(e, requests.exceptions.Timeout):
                        DEBUG("WARNING: Timeout: " + str(e) + "...continuing")
                        continue
                    else:
                        DEBUG(traceback.format_exc())
                        self.send_message("Other Error of type %s : %s ... need assistance!" % (type(e).__name__, str(e)))
                        continue
    
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
                archive_dir = self.m_outputDir + "/archive"
                if (not os.path.exists(archive_dir)):
                    os.makedirs(archive_dir)
                filename = archive_dir + "/" + STATUS_JSON_FILENAME + "." + (datetime.now().strftime("%Y-%m-%d_%H%M%S"))
                f = open(filename, "w")
                f.write(content)
                f.close()
                DEBUG("INFO: Wrote %s" % (filename))
                
                # give the good servers some time to rest
                VARIANCE = 10 # seconds
                sleeptime = random.randint(max(self.MIN_REQUEST_RATE, self.m_requestRate - VARIANCE), max(self.MIN_REQUEST_RATE, self.m_requestRate + VARIANCE))
                DEBUG("INFO: checking again in %d seconds..." % (sleeptime))
                time.sleep(sleeptime)

                schedule.run_pending()
                self.m_attempts += 1

            except Exception as e:
                DEBUG(traceback.format_exc())
                self.send_message("Error during processing of type %s : %s ... exiting." % (type(e).__name__, str(e)))
                sys.exit(-1)

if __name__ == "__main__":

    signal.signal(signal.SIGINT, SignalHandler)

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
            '--alert-rate',
            action="store",
            dest="alertRate",
            help="If passed, defines how often, in minutes, the program will email the 'recipients' field in 'credentials.json' to send a periodic update of status and/or errors.  If not passed, 'credentials.json' is not required.",
            required=False,
            metavar='[X]',
            default="")

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
    
    if (args.alertRate != ""):
        try:
            args.alertRate = int(args.alertRate)
        except Exception as e:
            DEBUG("ERROR: --alert-rate must be a number")
            sys.exit(-1)
    else:
        args.alertRate = 0

    vc = vaccineChecker(args.inputDir, args.outputDir, args.requestRate, args.alertRate)
    vc.run()
