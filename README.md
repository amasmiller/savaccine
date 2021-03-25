# savaccine

## What is this page?

This project is used at https://amasmiller.com/savaccine/ to show availablity of the COVID-19 vaccine in San Antonio, TX.

## How does it work?

Provider's sites are periodically queried to look for presence or absences of phrases like "currently no vaccine".

`index.php` is the website, `vaccineChecker.py` is the background task for finding status.

## What if I want to use it for my city?

Go for it.  It's under the MIT license.  The setup is not a one-click-easy-button, but it's not too complicated.

There are only two files from here you need: `index.php` and `vaccineChecker.py`.

You'll need to:
* have a Linux server
* setup a server to serve PHP (v5.5 minimum)
* have Python (v3.4.3 minimum)
* have the Python dependencies in the `import`s of `vaccineChecker.py` (a.k.a. `pip install....`)
* place `index.php` in a folder served by the web server
* configure `vaccineChecker.py` to:
  * read your own `credentials.json`
  * obtain status from your own website list
  * to run as a background task
  * output `status.json` to wherever `index.php` lives
