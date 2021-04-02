This directory can contain:

- a valid `credentials.json` file if the `--alert-rate` argument is passed to `vaccineChecker.py`.  This file should contain the authentication credentials for an SMTP server and login and email recipients for status messages to be sent to.  Example `credentials.json` file:
```
{
"email" : "foo@gmail.com",
"password" : "bar",
"recipients" : "foobar@tmomail.net, myname@yahoo.com",
"smtp_host" : "smtp.myserver.com",
"smtp_port" : 465
}
````

- a valid `websites.json` file.   This file defines the websites to query.  Example:

```
{
    "UT Health San Antonio": {
        "type" : "phrase",
        "website": "https://schedule.utmedicinesa.com/Identity/Account/Register",
        "neg_phrase": "are full",
        "pos_phrase": "you confirm your understanding"
    },
    "San Antonio CVS" : {
        "type" : "cvs",
        "website" : "https://www.cvs.com/immunizations/covid-19-vaccine",
        "state" : "TX",
        "city" : "San Antonio"
    },
    "San Antonio Walgreens" : {
        "type" : "walgreens",
        "website" : "https://www.walgreens.com/findcare/vaccination/covid-19/location-screening",
        "query" : "San Antonio, TX"
    }
}
```
