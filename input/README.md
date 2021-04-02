The `vaccineChecker.py` program always expects a valid 'websites.json' file in the directory specified by --input-dir.  This file defines the websites to query, along with the positive/negative phrases to search for.  This directory contains an example `websites.json`.


If the argument --notification-rate is passed, the program also expects a valid 'credentials.json' file specified by the --credentials argument.  This file should contain the authentication credentials for an SMTP server and login and email recipients for status messages to be sent to.  This file could be placed in this directory.  Example 'credentials.json' file:

```
{
  "email" : "foo@gmail.com",
  "password" : "bar",
  "recipients" : "foobar@tmomail.net, myname@yahoo.com",
  "smtp_host" : "smtp.myserver.com",
  "smtp_port" : 465
 }
 ```
