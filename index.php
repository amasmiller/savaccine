<!--

index.php

Webpage that reads the `status.json` produced by `vaccine-checker.py`.

This is the page the user will see.

This file must be in the same directory as 'status.json'.

-->

<html>
<style>
#button {
    font-family: 'Verdana';
    font-size: 1.2em;
    border: 0.16em solid; 
    border-radius: 2em; 
    padding: 0.4em 0 0.4em 0;
    margin: 0.6em 0.1em 0.2em 0.2em;
    width: 60%;
}
body 
{ 
    margin: 1em;
    font-family: 'Verdana';
    font-size: 1.3em;
}
</style>
<?php
use \Datetime;

// if needed, comment in
// error_reporting(-1);
// ini_set('display_errors', 'On');

// for developers
if (isset($_GET["debug"]))
{
    $DEBUG = True; 
}

// utility function so HTML looks nice
function print_n($s) { echo $s."\n"; }

// what's my name again?
$SITE_TITLE = "San Antonio COVID-19 Vaccine Availability Website";
print_n("<title>$SITE_TITLE</title>");

$REFRESH_RATE = 5; // minutes
print_n("<meta http-equiv=\"refresh\" content=\"".strval($REFRESH_RATE*60)."\">");

// read the output of vaccine-checker.py
$STATUS_JSON = "status.json";
if (!file_exists($STATUS_JSON)) { print_n("Sorry, the site's not working."); return; }; 
$items = json_decode(file_get_contents($STATUS_JSON, true));

// get the HTML party started
print_n("<body>");
print_n("<center>");

print_n("<b>$SITE_TITLE</b>".($DEBUG ? " (Debug)" : ""));
print_n("<br><br>");
print_n("Clicking the button opens the site.");
print_n("<br><br>");
$allurls = "";
foreach ($items as $item)
{
    if ($item->name == "Test Site" && !$DEBUG) { continue; }

    $text = "<b>$item->name</b><br>slots " . $item->status . " available<br>as of " . $item->update_time;

    $style = "";
    switch ($item->status)
    {
        case "probably":
            $style .= "background-color: lightgreen";
            break;
        case "probably not":
            $style .= "background-color: lightcoral";
            break;
        case "maybe":
            $style .= "background-color: khaki";
            break;
        default;
            $style .= "background-color: gray";
            break;
    }
    
    print_n("<button style=\"$style\" id=\"button\" onclick=\"window.open('".$item->website."', '_blank');\"/>");
    print_n("<span>$text</span>");
    print_n("</button>");

    $allurls .= "window.open('".$item->website."', '_blank');";
}

$text = "I'm not sure I trust this site.<br><br>Open all of them.";
print_n("<button style=\"background-color: lightgray\" id=\"button\" onclick=\"$allurls\">");
print_n("<span>$text</span>");
print_n("</button>");

print_n("<br>");
print_n("<br>");
$now = new DateTime("now", new DateTimeZone('America/Chicago'));
print_n("Last page refresh: ".$now->format('d-M-Y h:i:s A'));  
print_n("<br><br>");

print_n("This page refreshes every $REFRESH_RATE minutes."); 

print_n("</center>");

if ($DEBUG)
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
This page provides the current status of vaccine availability in San Antonio, TX.
<br>
<br>
<b>How does it work?</b>
<br>
Provider sites are periodically queried to look for presence or absences of phrases like "currently no vaccine".
<br>
<br>
<b>Doesn't this spam the provider servers?</b>
<br>
This site limits the number of requests to every <?php print_n($REFRESH_RATE); ?> minutes, regardless of how many people visit or refresh this page.  This site is a funnel of information, not a spambot.
<br>
<br>
<b>Is this available in other cities?</b>
<br>
Don't know.  This was homegrown for San Antonio, like an HEB tortilla.  The source code is available at <a href="https://github.com/amasmiller/savaccine/">this site</a>.
<br>
<br>
<b>Who made this?</b>
<br>
Squirrels, with help from a human you can contact at <a href="mailto:amasmiller@gmail.com">amasmiller@gmail.com</a> or read about <a href="https://amasmiller.com/wp/about/">here</a>.
</div>
</center>

</body>
</html>

