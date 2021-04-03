<?php

/*
OVERVIEW:

    This is the webpage that reads the `status.json` produced by 
    `vaccine-checker.py`.

    This file must be in the same directory as 'status.json' (or a symlink to it).

    The webpage displays a list of boxes with fields populated by 'vaccineChecker.py'
    into a 'status.json' file.  This webpage cares about the 'status', 'website', and 'update_time'
    fields.

    Example 'status.json':

{
    "UT Health San Antonio" : 
        {
            "status": "probably not",
            "update_time": "26-Mar-2021 10:28:39 PM",
            "website": "https://schedule.utmedicinesa.com/Identity/Account/Register"
        },
    "University Health" :
        {
            "status": "probably not",
            "update_time": "26-Mar-2021 10:28:40 PM",
            "website": "https://www.universityhealthsystem.com/coronavirus-covid19/vaccine/vaccine-appointments"
        }
}

REQUIREMENTS:

    This script was developed with PHP v5.5.9.
*/

?>

<html>

<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-186062303-1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'UA-186062303-1');
</script>

<style>

#button 
{
    font-family: Calibri, sans-serif;
    border: 0.2em solid; 
    border-radius: 2em; 
    padding: 20px 20px 20px 20px;
    margin: 8px 1px 8px 1px;
}

body 
{ 
    background-color:  #D6ECf3;
    margin: 1em;
    font-family: Calibri, sans-serif;
}

@media only screen and (orientation: portrait)
{
    #button 
    {
        font-size: 30px;
        width: 95%;
        margin: 4px 1px 4px 1px;
    }

    body 
    { 
        font-size: 30px;
    }
}

@media only screen and (orientation: landscape)
{
    #button 
    {
        font-size: 20px;
        width: 45%;
    }

    body 
    { 
        font-size: 20px;
    }

}

</style>
<?php
use \Datetime;

// utility function so HTML looks nice
function print_n($s) { echo $s."\n"; }

// if needed, comment in
//error_reporting(-1);
//ini_set('display_errors', 'On');

// for developers
if (isset($_GET["debug_raw"])) { $DEBUG_RAW = True; }
else { $DEBUG_RAW = False; }
if (isset($_GET["debug_fast"])) { $DEBUG_FAST = True; }
else { $DEBUG_FAST = False; }
if (isset($_GET["debug_test"])) { $DEBUG_TEST = True; }
else { $DEBUG_TEST = False; }

// what's my name again?
$SITE_TITLE = "San Antonio COVID-19 Vaccine Availability";
print_n("<title>$SITE_TITLE</title>");

$REFRESH_RATE = 5; // minutes
print_n("<meta http-equiv=\"refresh\" content=\"".(($DEBUG_FAST) ? "1" : strval($REFRESH_RATE*60))."\">");

// read the output of vaccine-checker.py
$STATUS_JSON = "status.json";
if (!file_exists($STATUS_JSON)) { print_n("Sorry, the site's not working."); return; }; 
$items = json_decode(file_get_contents($STATUS_JSON), true);
ksort($items);

// get the HTML party started
print_n("<body>");
print_n("<center>");

print_n("<b>$SITE_TITLE</b>");
print_n("<br>");
print_n("<a href=http://sanantoniovaccine.com>sanantoniovaccine.com</a>");
print_n("<br><br>");
$allurls = "";
foreach ($items as $name => $info)
{
    if ($name == "Test Site" && !$DEBUG_TEST) { continue; }

    $text = "<b>$name</b><br>slots " . $info['status'] . " available<br>";
    $text .= (array_key_exists('update_time', $info) && $info['update_time'] != "") ? ("as of " . $info['update_time']) : "<br>";

    $style = "";
    switch ($info['status'])
    {
        case "probably":
            $style .= "background-color: #82CA9D";
            break;
        case "probably not":
            $style .= "background-color: #F7977A";
            break;
        case "maybe":
            $style .= "background-color: #FFF79A";
            break;
        default;
            $style .= "background-color: gray";
            break;
    }

    // special case
    $website = "";
    if (array_key_exists('display_website', $info)) { $website = $info['display_website']; } 
    else { $website = $info['website']; }

    print_n("<button style=\"$style\" id=\"button\" onclick=\"window.open('".$website."', '_blank');\"/>");
    print_n("<span>$text</span>");
    print_n("</button>");

    $allurls .= "window.open('".$website."', '_blank');";
}

$text = "I'm not sure I trust this site.<br><br>Open all of them.";
print_n("<button style=\"background-color: #F9F1F0\" id=\"button\" onclick=\"$allurls\">");
print_n("<span>$text</span>");
print_n("</button>");

print_n("<br>");
print_n("<br>");
$now = new DateTime("now", new DateTimeZone('America/Chicago'));
print_n("Last page refresh: ".$now->format('d-M-Y h:i:s A'));  
print_n("<br>");

print_n("This page refreshes every ".($DEBUG_FAST ? "second" : "$REFRESH_RATE minutes" . " or by clicking <a href=\"\">here</a>.")); 

print_n("</center>");

if ($DEBUG_RAW)
{
    print_n("<pre style=\"text-align:left;\">");
    print_n(file_get_contents($STATUS_JSON, true));
    print_n("</pre>");
}

?>
<br>
<hr>

<center>
<h3>FAQ</h3>

<div style="padding: 0 2em 1em 2em">
<b>What is this page?</b>
<br>
This page provides the current status of vaccine availability from major distribution sites in San Antonio, TX.
<br>
<br>
<b>How does it work?</b>
<br>
Provider sites are periodically queried to look for presence or absences of phrases like "currently no vaccine" or "Available Now".
<br>
<br>
<b>Why isn't [X] site shown?</b>
<br>
I may not know about provider [X].  Email me at <a href="mailto:amasmiller.com">amasmiller@gmail.com</a>.
<br>
<br>
<b>Is this available in other cities?</b>
<br>
Don't know.  This was homegrown for San Antonio, like an HEB tortilla.  The source code is an open source project available at <a href="https://github.com/amasmiller/savaccine/">this site</a>.
<br>
<br>
<b>Doesn't this spam the provider servers?</b>
<br>
Even if 1 million people refresh this site every second, the providers servers still only get <?php print_n(strval(60/$REFRESH_RATE)); ?> requests per hour.  The requests to provider websites are run in a throttled background task.  This site is a funnel of information, not a spambot.
<br>
<br>
<b>Is this different than vaccinespotter.org?</b>
<br>
Similar concept, but includes local providers that vaccinespotter.org does not (UT Health Science Center, SA Metro, and University Health). Not affiliated with <a href="http://vaccinespotter.org">vaccinespotter.org</a>.
<br>
<br>
<b>Who made this?</b>
<br>
Squirrels, with help from a human you can contact at <a href="mailto:amasmiller@gmail.com">amasmiller@gmail.com</a> or read about <a href="https://amasmiller.com/wp/about/">here</a>.
</div>
</center>

</body>
</html>

