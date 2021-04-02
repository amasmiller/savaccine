The `--websites` argument to `vaccineChecker.py` expects a valid `.json` file defining the websites to query.  This directory contains an example `websites.json`.  See README in `vaccineChecker.py` for format details.

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
