Quick and dirty Python 3 script that checks web pages for changes at regular intervals, and sends you a nicely-colourful email alert of the diff of the page (need to specify a gmail account in config, if you set up an app-specific password).

You can configure which sites to scrape via a human readable config file (see below). Can either be run manually whenever you want to check for changes, or set up as a scheduled task or cron job. 

Only tested on Linux so far, but should work on other platforms with Python 3 installed.

Please do share any feedback, feature requests or bug reports.

### Configuration

Configure by editing the config_default.yml file (in yaml format https://yaml.org/start.html) with the pages you would like to regularly scrape (you can also rename and modify this file to config.yml to contain your personal configuration).

For email alerts, need to set emailAccount, emailPassword and emailRecipient in the "config:" section of the file. Do NOT use your standard Gmail password here - you can create app-specific Gmail passwords, which is much safer: https://myaccount.google.com/apppasswords

To add a page to crawl, find the "pages:" section in the yml file, and add or uncomment the required below options (make sure you include appropriate spaces or tabs):

	pages:
		Example: # the name of the page
			url: http://www.example.org
			searchWithinTag: # optionally, only search for diffs within the following XML tags
				tag: div # e.g., only search divs
				attr: # optionally specify a class or id attribute for the 'tag'
			#hours: 6 # requires cronjob - enable this to only scrape every even 6th or nth hour the script is run (i.e., at 6am, 12pm and 6pm)
			#minutes: 5 # requires cronjob - enable this to scrape every even 5th or nth minute the script is run (i.e., 605pm, 610pm, 615pm, etc)
			#strip: # add this if you want to strip the following tags from the page
			#  - strong # this will strip <strong> tags from the fetched file
			#onlyAdditions: True # If set to True, this only alerts for additions rather than also deletions in page

To use automatically, create a cron or other scheduled task that runs this script every minute, and set 'hours' or 'minutes' for each 'page' in the config file to throttle your scraping of specific pages (otherwise the pages will be scraped every time the cron is run).

### Command line options

Run ./sitePingDiff.py either without parameters (after setting the config as above), or with the following command line options

--now: runs the script immediately, ignoring any timetables that have been set

--page [pagename]: only run the script on [pagename] as specified in config.yml 'name' parameter


### Requires following Python libraries

Please install the following Python libraries with pip from the command line, if you don't have them loaded already

* pip3 install bs4
- pip3 install yagmail
