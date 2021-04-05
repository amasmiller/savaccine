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

use \Datetime;

// utility function so HTML looks nice
function print_n($s) { echo $s."\n"; }

// if needed, comment in
//error_reporting(-1);
//ini_set('display_errors', 'On');

// for developers
if (isset($_GET["debug_raw"])) { $DEBUG_RAW = True; }
else { $DEBUG_RAW = False; }
if (isset($_GET["debug_test"])) { $DEBUG_TEST = True; }
else { $DEBUG_TEST = False; }


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

/* slider/switch CSS courtesy of https://www.w3schools.com/howto/howto_css_switch.asp */
.switch {
  position: relative;
  display: inline-block;
  width: 120px;
  height: 68px;
}
.switch input { 
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  -webkit-transition: .4s;
  transition: .4s;
}
.slider:before {
  position: absolute;
  content: "";
  height: 52px;
  width: 52px;
  left: 8px;
  bottom: 8px;
  background-color: white;
  -webkit-transition: .4s;
  transition: .4s;
}
input:checked + .slider {
  background-color: #2196F3;
}
input:focus + .slider {
  box-shadow: 0 0 1px #2196F3;
}
input:checked + .slider:before {
  -webkit-transform: translateX(52px);
  -ms-transform: translateX(52px);
  transform: translateX(52px);
}
.slider.round {
  border-radius: 68px;
}
.slider.round:before {
  border-radius: 50%;
}

/* custom CSS */
.button 
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
    padding:0;
}

/* phones */
@media only screen and (orientation: portrait)
{
    .button 
    {
        font-size: 30px;
        width: 95%;
        margin: 4px 1px 4px 1px;
    }

    body
    { 
        font-size: 30px;
    }

    table {
        font-size: 30px;
    }
}


/* iPads, monitors, etc.. anything but phones */
@media only screen and (orientation: landscape)
{
    .button 
    {
        font-size: 20px;
        width: 45%;
    }

    body 
    { 
        font-size: 20px;
    }

    table {
        font-size: 20px;
    }

    /* override slider/switch sizes */
    .switch {
      width: 60px;
      height: 34px;
    }

    .slider:before {
      height: 26px;
      width: 26px;
      left: 4px;
      bottom: 4px;
    }

    input:checked + .slider:before {
      -webkit-transform: translateX(26px);
      -ms-transform: translateX(26px);
      transform: translateX(26px);
    }

    .slider.round {
      border-radius: 24px;
    }

}

</style>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
<script>

    // handle the sound alert 
    var audio = new Audio('https://www.fesliyanstudios.com/play-mp3/6630'); // sheep
    var soundAlertEnabled = false;
    var lastSoundAlertEnabled = false;
    function soundHandler() {
        soundAlertEnabled = $("#sound").is(':checked');
        if (!lastSoundAlertEnabled && soundAlertEnabled)
        {
            alert("When a site shows possible slots, you will hear a sheep.  Like this:");
            audio.play();
        }
        lastSoundAlertEnabled = soundAlertEnabled;
    }

    // periodically update color and update time based on most current status.json
    var lastSiteStatus = Object.create(null);
    function update(data) {

        // debug if enabled
        if (<?php echo json_encode($DEBUG_RAW); ?>)
        {
            $("#raw-json").html("<pre>" +JSON.stringify(data, null, 4) + "</pre>");
        }

        // update color and time
        for (var name in data)
        {
            site = data[name];
            text = "<b>" + name + "</b><br>slots " + site.status + " available<br>" +
                ((("update_time" in site) && ("" != site.update_time)) ? ("as of " + site.update_time) : "<br>");
            id = name.replace(new RegExp(" ", "g"), "-");
            $("#".concat(id)).html(text);
            switch (site.status) 
            {
                case "probably": 
                    $("#".concat(id)).css("background-color", "#82CA9D");
                    break;
                case "maybe": 
                    $("#".concat(id)).css("background-color", "#FFF79A");
                    break;
                case "probably not": 
                    $("#".concat(id)).css("background-color", "#F7977A");
                    break;
                default:
                    $("#".concat(id)).css("background-color", "gray");
                    break;
            }

            // play sound if site transitions away from "probably not"
            if ("probably not" != site.status && lastSiteStatus[name] != site.status && soundAlertEnabled)
            {
                audio.play();
            }

            lastSiteStatus[name] = site.status;
        }

        // show current time
        var time = new Date();
        t = time.toLocaleString('en-US', { hour: 'numeric', minute: 'numeric', second : 'numeric', hour12: true });
        $("#last-refresh").text(t);
    }

    // setup the polling
    var status_file = "status.json";
    setInterval(function() { $.getJSON(status_file, function(data) { update(data); }).fail(function(jqXHR) { console.log(jqXHR.status); })}, 1000);
    $(document).ready(function() { 
        $.ajaxSetup({ cache: false }); 
        $.getJSON(status_file, function(data) { update(data); });
    });
</script>
<?php

// what's my name again?
$SITE_TITLE = "San Antonio COVID-19 Vaccine Availability";
print_n("<title>$SITE_TITLE</title>");

$REFRESH_RATE = 5; // minutes

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

// print out each button
$allurls = "";
foreach ($items as $name => $info)
{
    // TODO handle in javascript.  maybe make hidden here?
    if ($name == "Test Site" && !$DEBUG_TEST) { continue; }

    // special case
    $website = "";
    if (array_key_exists('display_website', $info)) { $website = $info['display_website']; } 
    else { $website = $info['website']; }

    // text is filled in by javascript
    $id = str_replace(" ", "-", $name); // ids cannot have spaces
    print_n("<button id=\"$id\" style=\"$style\" class=\"button\" onclick=\"window.open('".$website."', '_blank');\"/></button>");

    // for bottom button
    $allurls .= "window.open('".$website."', '_blank');";
}

$text = "Open all of them.";
print_n("<button style=\"background-color: #F9F1F0\" class=\"button\" onclick=\"$allurls\">");
print_n("$text");
print_n("</button>");

print_n("<br><br>");
?>
<table width=100%>
<tr>
<td align="center">
<label class="switch">
  <input id="sound" onchange="soundHandler()" type="checkbox">
  <span class="slider round"></span>
</label>
<div>sound alert</div>
</td>
<td align="center">
<?php
print_n("Data refreshes every $REFRESH_RATE minutes.");
?>
</td>
<td align="center">
<div id="last-refresh"></div>
</td>
</tr>
</table>

<?php
print_n("<br>");
print_n("<br>");

print_n("</center>");

if ($DEBUG_RAW) { print_n("<div id=\"raw-json\"></div>"); }

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
Don't know.  This was homegrown for San Antonio, like an HEB tortilla.  It could be adapted to other cities via the open source project I've published at <a href="https://github.com/amasmiller/savaccine/">this site</a>.
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

