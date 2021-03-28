# savaccine

## What is this page?

This project is used by https://amasmiller.com/savaccine/ to show availablity of the COVID-19 vaccine in San Antonio, TX.

## How does it work?

Vaccine provider websites are periodically queried to look for presence or absence of phrases like "currently no vaccine".

`index.php` is the website, `vaccineChecker.py` is the background task for querying the websites.  See respective README information at the top `index.php` / `vaccineChecker.py`.

## What if I want to use it for my city?

The setup is not a one-click-easy-button, but it's not too complicated:

You'll need to:
* have a Linux server with:
    * PHP (v5.5 known to work) 
    * Python (v3.4.3 known to work)
    * Python dependencies in the `import`s of `vaccineChecker.py` (a.k.a. `pip install....`)

* download and extract a copy of this repository to a location NOT served by the web server.  example:
```
/home/[your-user]/savaccine/
  .gitignore
  LICENSE
  README.md
  index.php
  vaccineChecker.py
  input/
    websites.json
```  

* in the extracted directory:
  * create your own `input/credentials.json` (see top of `vaccineChecker.py` for format)
  * modify `input/websites.json` for the websites you wish to monitor
  * run `vaccineChecker.py` as a background task

* after running `vaccineChecker.py` at least once, so it creates `status/status.json`, create a new directory to be served by the webserver.  within this new directory, create softlinks to `index.php` and `status.json`.  example:

```
/var/www/html/savaccine/
  index.php -> /home/[your-user]/savaccine/index.php
  status.json -> /home/[your-user]/savaccine/status/status.json
```

* view `index.php` on your site!  debug, test, repeat!

