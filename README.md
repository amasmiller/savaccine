# savaccine

## What is this page?

This project is used to show availablity of the COVID-19 vaccine in San Antonio, TX at the website http://sanantoniovaccine.com.  It can be adapted for other cities.

## How does it work?

Vaccine provider websites in a configuration file are periodically queried by a Python script to look for current availability.  The status is written to a file, which is then ready by a PHP file for display on a website.

`index.php` is the website, `vaccineChecker.py` is the background task for querying the websites.  See respective README information at the top `index.php` / `vaccineChecker.py`, along with `vaccineChecker.py --help`.

An example file `input/websites.json` is provided in this source tree.  The sites in `websites.json` can be one of four `type` values:
* `phrase` : Looks for the presence or absence of phrases specified by `pos_phrase` or `neg_phrase`.
* `cvs`: Queries the `cvs.com` website with with the `state` and `city` parameters supplied.
* `heb`: Queries the `heb.com` website with with the `city` parameter supplied.
* `walgreens`: Queries the `walgreens.com` website with with the `query` parameter supplied.

## What if I want to use it for my city?

The setup is not a one-click-easy-button, but it's not too complicated:

### Prerequisites
* have a Linux server with:
    * PHP (v5.5 known to work) 
    * Python (v3.4.3 known to work)
    * Python dependencies in the `import`s of `vaccineChecker.py` (a.k.a. `pip install....`)
    * if querying Walgreens, you need the `selenium` Python package and the Linux Firefox `geckodriver`driver for the OS.  The script assumes the `geckodriver` binary is in the path. See https://askubuntu.com/questions/851401/where-to-find-geckodriver-needed-by-selenium-python-package for setup.

### Step 1
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
### Step 2
* in the extracted directory:
  * if you would like notifications to an email with script status to be sent, as enabled by the `--notification-rate` argument, create your own `credentials.json` file and pass it to the script with `--credentials`. See README in `vaccineChecker.py` for format.
  * modify `input/websites.json` for the websites you wish to monitor
  * run `vaccineChecker.py` as a background task

### Step 3
* after running `vaccineChecker.py` at least once, so it creates `status/status.json`, create a new directory to be served by the webserver.  within this new directory, create softlinks to `index.php` and `status.json`.  example:

```
/var/www/html/savaccine/
  index.php -> /home/[your-user]/savaccine/index.php
  status.json -> /home/[your-user]/savaccine/status/status.json
```

### Step 4
* view `index.php` on your site!  debug, test, repeat!

