This directory should contain:

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

- a valid `websites.json` file.   This file defines the websites to query, along with the positive/negative phrases to search for.  Example 'websites.json' file:

```
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
```

- Any site defined in `websites.json` with special keywords is handled in a custom way.  These keywords include:
    * Any site with "CVS" in the name will use the "state" and "city" keys for lookup on the cvs.com website.
    * Any site with "Walgreens" in the name will use the "query" key for lookup on the walgreens.com website.
    * Any site with "HEB" in the name will use the "city" key for lookup on the heb.com website.
