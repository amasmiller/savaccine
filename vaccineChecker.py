#!/usr/bin/python3

# standard libraries
import enum
import traceback
import requests
import signal
import argparse
import inspect
import os
import time
import smtplib
import sys
import random
import urllib3
import syslog
import json
import re
import urllib3
from datetime import datetime
from email.mime.text import MIMEText

# non-standard libraries
import schedule 

PROGRAM_DESCRIPTION="""
    
    README:

    This program is a daemon for inspecting vaccine provider websites and outputting
    their availability status to an output `status.json` file.

    This program always expects a valid 'websites.json' file passed as the 
    --websites argument. This file defines the websites to query.

    An example file `input/websites.json` is provided in this source tree.  
    The sites in `websites.json` can be one of four `type` values:

    * `phrase` : Looks for the presence or absence of phrases specified by `pos_phrase` or `neg_phrase`.
    * `cvs`: Queries the `cvs.com` website with with the `state` and `city` parameters supplied.
    * `heb`: Queries the `heb.com` website with with the `query` parameter supplied.
    * `walgreens`: Queries the `walgreens.com` website with with the `query` parameter supplied.

    If the argument --notification-rate is passed, this program expects a 
    valid 'credentials.json' file specified by the --credentials argument.
    This file should contain the authentication credentials for an SMTP server 
    and login and email recipients for status messages to be sent to.  Example 
    'credentials.json' file:
    
    {
      "email" : "foo@gmail.com",
      "password" : "bar",
      "recipients" : "foobar@tmomail.net, myname@yahoo.com",
      "smtp_host" : "smtp.myserver.com",
      "smtp_port" : 465
     }
    

    EXAMPLE USE (Command Line):

        See 'vaccineChecker.py --help' for full argument set.

        # run the daemon with a request rate of 5 minutes (300 seconds), outputting
        # status to the default 'status' directory
        ./vaccineChecker.py --websites input/websites.json --request-rate 300

        # run the daemon with a request rate of 10 minutes (600 seconds), outputting
        # status to the 'output' directory, sending a periodic update of status to 
        # the email supplied in 'credentials.json'
        ./vaccineChecker.py --websites input/websites.json --request-rate 500 --output-dir output --credentials input/credentials.json

    REQUIREMENTS:

        This script was developed with Python 3.4.3 and the packages as specified
        by the import directives.

    """


'''
Handle Ctrl+C
'''
def SignalHandler(sig, frame):
    print("INFO: Program interrupted via Ctrl-C.  Exiting")
    sys.exit(0)

'''
Enum class for provider status.
'''
class Availability(enum.Enum):
    PROBABLY_NOT = "probably not"
    MAYBE = "maybe"
    PROBABLY = "probably"

'''
Primary class. 
'''
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
    MAX_ATTEMPTS = 0 # maximum runs of main while loop. 0 = run forever.
    TIMEOUT = 10 # website access timeout (seconds)

    m_attempts = 0 # total runs of main while loop

    # command line arguments
    m_websitesFile = "" # location of 'websites.json'
    m_outputDir = "" # the directory were status.json gets written to
    m_credentialsFile = "" # location of 'credentials.json'
    m_notificationRate = 0 # how often, in minutes, we should send a emailed notification with script status
    m_enableArchive = False # whether or not files should be written as archives in m_outputDir
    m_requestRate = 0 # how often, in seconds, we should ask for website status
    m_verbose = False # if set to true, prints out function name and process ID when logging

    # initially populated with 'websites.json', but then updated continuously
    m_websites = {}

    # selenium object for accessing sites that require special navigation
    m_sd = object()

    '''
    Setup.
    '''
    def __init__(self, websitesFile, outputDir, credentialsFile, notificationRate, enableArchive, requestRate, verbose):

        self.DEBUG("INFO: Initializing....")

        self.m_websitesFile = websitesFile
        self.m_outputDir = outputDir
        self.m_credentialsFile = credentialsFile
        self.m_notificationRate = notificationRate
        self.m_enableArchive = enableArchive
        self.m_requestRate = requestRate
        self.m_verbose = verbose

        urllib3.disable_warnings() # for ignoring InsecureRequestWarning for https

        # if configured, for confirmation things are going ok, send a text/email
        if (0 != self.m_notificationRate):
            self.read_credentials()
            self.DEBUG("INFO: --notification-rate passed, configuring to send heartbeat message every %d minutes" % (self.m_notificationRate))
            schedule.every(self.m_notificationRate).minutes.do(self.heartbeat)
        else:
            self.DEBUG("INFO: --notification-rate not passed, no notifications will be sent.")

        self.send_message("INFO: Startup. m_attempts = %d." % (self.m_attempts))
        
        self.read_websites()

        # check for selenium
        for name, info in self.m_websites.items():
            site = self.m_websites[name]
            
            # currently only Walgreens requires 
            if "walgreens" == site['type'].lower():
                self.DEBUG("INFO: Setting up Python package 'selenium' for queries requiring user navigation (i.e  Walgreens)...")

                from selenium import webdriver
                options = webdriver.firefox.options.Options()
                options.headless = True
                self.DEBUG("INFO: Creating selenium object...")

                # assumes 'geckodriver' binary is in path
                self.m_sd = webdriver.Firefox(options=options)
                self.m_sd.set_page_load_timeout(30)
                self.DEBUG("INFO: Done setting up selenium.")


    '''
    Utility function for logging.  Send to standard out and syslog.
    '''
    def DEBUG(self, x):
        if (self.m_verbose):
            frame,filename,line_number,function_name,lines,index = inspect.stack()[1] 
            logLine = "[%s][%s|%s|%s|%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), os.getpid(), filename, function_name, line_number, x)
        else:
            logLine = "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x)

        sys.stdout.write(logLine)
        syslog.syslog(logLine)
   
    '''
    Read in credentials.json.
    '''
    def read_credentials(self):

        filename = self.m_credentialsFile
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
            self.DEBUG("ERROR: " + filename + ' file not found, exiting. example file contents: ' + example)
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
            self.DEBUG("INFO: Successfully read credentials file.")
        except Exception as e:
            self.DEBUG("ERROR: Problem reading file " + filename + '. valid example content: ' + example)
            self.DEBUG(traceback.format_exc())
            sys.exit(-1)

    '''
    Read in websites.json.
    '''
    def read_websites(self):

        filename = self.m_websitesFile
        example = ''' 
{
    "name": "UT Health San Antonio",
    "type" : "phrase",
    "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
    "neg_phrase": "are full",
    "pos_phrase": "you confirm your understanding",
}
        '''
        if (not os.path.exists(filename)):
            self.DEBUG("ERROR: " + filename + ' file not found, exiting. example file contents: ' + example)
            sys.exit(-1)

        try:
            f = open(filename)
            self.m_websites = json.loads(f.read())

            # initialize things the user doesn't supply
            for name, info in self.m_websites.items():
                site = self.m_websites[name]
                if "type" not in site:
                    self.DEBUG("ERROR: Each site in 'websites.json' must have a 'type'.  See README.md")
                    sys.exit(-1)
                if "status" not in site:
                    site["status"] =  Availability.PROBABLY_NOT.value
                if "update_time" not in site:
                    site["update_time"] = ""

            f.close()
        except Exception as e:
            self.DEBUG("ERROR: Problem reading file " + filename + '. valid example content: ' + example)
            self.DEBUG(traceback.format_exc())
            sys.exit(-1)

    '''
    Given a string, logs it.  If notifications are enabled, it sends an email to RECIPIENTS,
    using the credentials in EMAIL and PASSWORD.
    '''
    def send_message(self, s):

        self.DEBUG(s)

        if (self.m_notificationRate == 0):
            return

        if (self.m_verbose):
            frame,filename,line_number,function_name,lines,index = inspect.stack()[1] 
            m = "[%s][%s|%s|%s|%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), os.getpid(), filename, function_name, line_number, s)
        else:
            m = "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s)

        msg = MIMEText(m)
        msg['Subject'] = os.path.basename(__file__)
        msg['From'] = self.EMAIL
        msg['To'] = (', ').join(self.RECIPIENTS.split(','))

        self.DEBUG("INFO: Attempting to send email with '%s'..." % (s))
        server = smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT)
        server.login(self.EMAIL, self.PASSWORD)
        server.sendmail(self.EMAIL, self.RECIPIENTS.split(','), str(msg))
        server.quit()
        self.DEBUG("INFO: Successfully sent email to '%s'!" % self.RECIPIENTS)


    '''
    Utility function to let someone know the script is running a-ok.
    '''
    def heartbeat(self):
        self.send_message("INFO: Heartbeat. m_attempts = '%d'." % (self.m_attempts))

    '''
    Handle when a website status changes (i.e. from Availability.PROBABLY_NOT to Availability.MAYBE)
    '''
    def handle_status(self, status, name, html):

        site = self.m_websites[name]
        if status.value != site['status']:
            self.send_message("INFO: %s changed to %s" % (site['website'], status))

            # save off HTML if passed 
            if "" != html and self.m_enableArchive:
                archive_dir = self.m_outputDir + "/archive"
                if (not os.path.exists(archive_dir)):
                    os.makedirs(archive_dir)
                filename = archive_dir + "/" + name + ".html." + (datetime.now().strftime("%Y-%m-%d_%H%M%S"))
                f = open(filename, "w")
                f.write(html)
                f.close()
                self.DEBUG("INFO: Archiving file '%s'" % (filename))
        else:
            self.DEBUG("INFO: still %s for %s" % (status, name))

        site['status'] = status.value

    '''
    For querying the Walgreens page for availability.  Requires 'selenium' to be installed.
    '''
    def query_walgreens(self, name):
        from selenium.common.exceptions import NoSuchElementException

        site = self.m_websites[name]

        s = "https://www.walgreens.com/findcare/vaccination/covid-19"
        self.DEBUG("INFO: Requesting site '%s'" % (s))
        self.m_sd.get(s)
        btn = self.m_sd.find_element_by_css_selector('span.btn.btn__blue')
        btn.click()
        s = "https://www.walgreens.com/findcare/vaccination/covid-19/location-screening"
        self.DEBUG("INFO: Requesting site '%s'" % (s))
        self.m_sd.get(s)
        element = self.m_sd.find_element_by_id("inputLocation")
        element.clear()

        q = site['query']
        self.DEBUG("INFO: Asking Walgreens about the location '%s'" % (q))
        element.send_keys(q)
        button = self.m_sd.find_element_by_css_selector("button.btn")
        button.click()
        time.sleep(0.75)

        timeout = time.time() + 30 # 30 sec timeout
        self.DEBUG("INFO: Waiting for Walgreens result...")
        response = object()
        while True:
            if (time.time() > timeout):
                self.DEBUG("WARNING: Timeout waiting for Walgreens result, continuing")
            try:
                response = self.m_sd.find_element_by_css_selector("p.fs16")
                break
            except NoSuchElementException:
                time.sleep(0.5)

        self.DEBUG("INFO: Found Walgreens result '%s'" % (response.text))
        if "Appointments unavailable" == response.text:
            self.handle_status(Availability.PROBABLY_NOT, name, "")
        elif "Please enter a valid city and state or ZIP" == response.text:
            self.handle_status(Availability.PROBABLY_NOT, name, "")
        else:
            self.handle_status(Availability.MAYBE, name, "")

    '''
    For querying the CVS page for availability.
    '''
    def query_cvs(self, name):

        self.DEBUG("INFO: Requesting information from CVS...")
        site = self.m_websites[name]

        state = site['state']
        city = site['city']
        response = requests.get("https://www.cvs.com/immunizations/covid-19-vaccine.vaccine-status.{}.json?vaccineinfo".format(state.lower()), headers={"Referer":"https://www.cvs.com/immunizations/covid-19-vaccine"})
        payload = response.json()

        self.DEBUG("INFO: Received response, parsing information from CVS...")
        mappings = {}
        try:
            for item in payload["responsePayloadData"]["data"][state]:
                mappings[item.get('city')] = item.get('status')

            response = mappings[city.upper()]

            if ("Fully Booked" == response):
                self.handle_status(Availability.PROBABLY_NOT, name, "")
                self.DEBUG("INFO: Found 'fully booked'")
            else:
                self.handle_status(Availability.MAYBE, name, "")

        except KeyError as e:
            self.handle_status(Availability.PROBABLY_NOT, name, "")
            self.DEBUG("WARNING: Could not find state '%s' or city '%s' in CVS response" % (state, city))

    '''
    For querying the HEB page for availability.
    '''
    def query_heb(self, name):

        self.DEBUG("INFO: Requesting information from HEB...")
        site = self.m_websites[name]

        d = requests.get("http://heb-ecom-covid-vaccine.hebdigital-prd.com/vaccine_locations.json").json()

        self.DEBUG("INFO: Received response, parsing information from HEB...")
        city = site['city'].upper()
        self.handle_status(Availability.PROBABLY_NOT, name, "")
        try:
            for location in d['locations']:
                if location["city"].upper() == city and location["openTimeslots"] != 0:
                    self.DEBUG("INFO: Found a match at HEB for '%s'! Zip code: '%s'. Open timeslots: %d" % (city, location['zip'], location['openTimeslots']))
                    self.handle_status(Availability.MAYBE, name, "")

        except KeyError as e:
            self.handle_status(Availability.PROBABLY_NOT, name, "")
            self.DEBUG("WARNING: Could not find city '%s' in HEB response" % (city))


    '''
    primary loop.  query the self.m_websites and keep track of status.
    '''
    def run(self):

        # primary loop
        while self.m_attempts < self.MAX_ATTEMPTS or self.MAX_ATTEMPTS == 0:

            for name, info in self.m_websites.items():
                try:
                    site = self.m_websites[name]

                    # special cases that require website navigation
                    if ("walgreens" == site['type'].lower()):
                        self.query_walgreens(name)
                    elif ("cvs" == site['type'].lower()):
                        self.query_cvs(name)
                    elif ("heb"  == site['type'].lower()):
                        self.query_heb(name)
                    # regular case of looking at a confirmation/absence of phrase in HTML via use
                    # of 'pos_phrase' / 'neg_phrase'
                    elif ("phrase" == site['type'].lower()):
                        self.DEBUG("INFO: asking %s at %s ..." % (name, info['website']))
                        r = requests.get(site['website'], timeout=self.TIMEOUT, verify=False)
                        html = re.sub("(<!--.*?-->)", "", r.text, flags=re.DOTALL) # remove HTML comments, outdated information sometimes lives here

                        if site['pos_phrase'] != "" and site['pos_phrase'] in html:
                            self.handle_status(Availability.PROBABLY, name, html)
                        elif site['neg_phrase'] in html:
                            self.handle_status(Availability.PROBABLY_NOT, name, html)
                        else:
                            self.handle_status(Availability.MAYBE, name, html)
                    else:
                        self.DEBUG("WARNING: Type '%s' for website '%s' not found, skipping..." % (site['type'], site['website']))
                        continue

                    site['update_time'] = time.strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception as e:
                    if isinstance(e, requests.exceptions.Timeout):
                        self.DEBUG("WARNING: Timeout: " + str(e) + "...continuing")
                        continue
                    else:
                        self.DEBUG(traceback.format_exc())
                        self.DEBUG(("ERROR: Error when querying '%s'. Error type %s : %s" % (name, type(e).__name__, str(e))))
                        continue

                    self.handle_status(Availability.PROBABLY_NOT, name, "")
    
            try:

                # populate the file we use for communication with PHP
                if (not os.path.exists(self.m_outputDir)):
                    os.makedirs(self.m_outputDir)
                STATUS_JSON_FILENAME = "status.json" 
                filename = self.m_outputDir + "/" + STATUS_JSON_FILENAME
                content = json.dumps(self.m_websites, indent=4)
                f = open(filename, "w")
                f.write(content)
                f.close()
                self.DEBUG("INFO: Wrote '%s'" % (filename))

                # save off all that we make
                if self.m_enableArchive:
                    archive_dir = self.m_outputDir + "/archive"
                    if (not os.path.exists(archive_dir)):
                        os.makedirs(archive_dir)
                    filename = archive_dir + "/" + STATUS_JSON_FILENAME + "." + (datetime.now().strftime("%Y-%m-%d_%H%M%S"))
                    f = open(filename, "w")
                    f.write(content)
                    f.close()
                    self.DEBUG("INFO: Archiving file %s" % (filename))
                
                # give the good servers some time to rest
                VARIANCE = 10 # seconds
                sleeptime = random.randint(max(self.MIN_REQUEST_RATE, self.m_requestRate - VARIANCE), self.m_requestRate + VARIANCE)
                self.DEBUG("INFO: checking again in %d seconds..." % (sleeptime))
                time.sleep(sleeptime)

                schedule.run_pending()
                self.m_attempts += 1

            except Exception as e:
                self.DEBUG(traceback.format_exc())
                self.send_message("Error during processing of type %s : %s ... exiting." % (type(e).__name__, str(e)))
                sys.exit(-1)
        
        self.DEBUG("INFO: All done.  Bye!")


if __name__ == "__main__":

    signal.signal(signal.SIGINT, SignalHandler)

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
            '--websites',
            action="store",
            dest="websitesFile",
            help="The location of 'websites.json`.  See README at the top of vaccineChecker.py for format.",
            required=True,
            metavar="[x]",
            default="input/websites.json")

    parser.add_argument(
            '--output-dir',
            action="store",
            dest="outputDir",
            help="The directory where 'status.json', which is read by 'index.php', will be written to. If --archive is passed, archives of of status will be written in an 'archive' subdirectory.  Default directory is 'status'.",
            required=False,
            metavar="[x]",
            default="status")

    parser.add_argument(
            '--credentials',
            action="store",
            dest="credentialsFile",
            help="The location of 'credentials.json`.  See README at the top of vaccineChecker.py for format.",
            required=False,
            metavar="[x]",
            default="")

    parser.add_argument(
            '--notification-rate',
            action="store",
            dest="notificationRate",
            help="If passed, defines how often, in minutes, the program will email the 'recipients' field in 'credentials.json' to send a periodic update of status and/or errors.",
            required=False,
            metavar="[x]",
            default="")

    parser.add_argument(
            '--archive',
            action="store_true",
            dest="enableArchive",
            help="If enabled, will write archives of 'status.json' and changed website HTML content to the directory specified in --output-dir",
            required=False,
            default=False)

    parser.add_argument(
            '--request-rate',
            action="store",
            dest="requestRate",
            help="How often, in seconds, the status will be requested from the sites in 'websites.json'.  Default is 300 seconds (5 minutes).  Up to a 10 second jitter is intentionally added every request.",
            required=False,
            metavar="[x]",
            default=5*60)

    parser.add_argument(
            '--verbose',
            action="store_true",
            dest="verbose",
            help="If passed, prints out function name and process ID when logging.",
            required=False,
            default=False)
    
    args = parser.parse_args()

    try:
        args.requestRate = int(args.requestRate)
    except Exception as e:
        print("ERROR: --request-rate must be a number")
        sys.exit(-1)

    if ("" != args.credentialsFile and "" == args.notificationRate):
        print("INFO: 'credentials.json' location specified, but --notification-rate not passed.  Assuming default notification rate of 60 minutes.")
        args.notificationRate = "60"

    if ("" != args.notificationRate and "" == args.credentialsFile):
        print("ERROR: --credentials file location must be passed when --notification-rate is supplied")
        sys.exit(-1)
    
    if (args.notificationRate != ""):
        try:
            args.notificationRate = int(args.notificationRate)
            if (args.notificationRate < 0):
                raise Exception()
        except Exception as e:
            print("ERROR: --notification-rate must be a positive number")
            sys.exit(-1)
    else:
        args.notificationRate = 0

    vc = vaccineChecker(args.websitesFile, args.outputDir, args.credentialsFile, args.notificationRate, args.enableArchive, args.requestRate, args.verbose)
    vc.run()
