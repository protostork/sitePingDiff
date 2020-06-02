Quick and dirty yet fast-becoming fairly advanced and customisable Python script that checks web pages for changes at regular intervals, and sends you a nicely-colourful email alert of the diff of the page (need to specify a gmail account in config, if you set up an app-specific password).

You can configure which sites to scrape via a human readable config file (see below). Can either be run manually whenever you want to check for changes, or set up as a scheduled task or cron job. 

Only tested on Linux so far, but should work on other platforms with Python 3 and requisite packages installed.

Has support for the fantastic mercury-parser NodeJS project to scrape some of those really hard-to-scrape websites (see more information below).

This is a hobby utility project for myself that I am using  heavily every day, but please do share any feedback, feature requests or bug reports.

### Configuration

Configure by editing the config_default.yml file (in yaml format https://yaml.org/start.html) with the pages you would like to regularly scrape (you can also rename and modify this file to config.yml to contain your personal configuration).

For email alerts, you need to set emailAccount, emailPassword and emailRecipient in the config: section of the file. Do NOT use your standard Gmail password here - you can create app-specific Gmail passwords, which is much safer: https://myaccount.google.com/apppasswords

To add a page to crawl, find the "pages:" section in the yml file, and add or uncomment the required options (make sure you include appropriate spaces so Yaml doesn't freak out). Your best bet may be to take included config_default.yml file, rename it to config.yml, and customise that.

To use this automatically, create a cron or other scheduled task that runs this script (or better, the included `sitePinger.sh` file) every few minutes, and set 'hours' or 'minutes' for each 'page' in the config file to throttle your scraping of specific pages (otherwise the pages will be scraped every time the cron is run).

### Can use mercury-parser for more advanced scraping of complex sites

If you want to use mercury-parser to grab page content (to be documented), then ensure the following:

- Read this for install and other instructions about the library: https://github.com/postlight/mercury-parser

Then make sure you have `nodejs` and `yarn` (called `yarnpkg` on Ubuntu) or `npm` installed. Then run:

`yarn global add @postlight/mercury-parser`
or
`npm global add @postlight/mercury-parser`

Then create an executable bash script somewhere you can run it, which contains: 

```
#/bin/bash
nodejs ~/.config/yarn/global/node_modules/@postlight/mercury-parser/cli.js "$1"
```

Then add the full path to this script in your config.yml's config.mercuryparser section, and use the `mercury-parser: true` setting in your config.yml page, as a child of followhyperlinks (see config_default.yml for example) 

### Command line options

Run ./sitePingDiff.py either without parameters (after setting the config as above), or with the following command line options

```
--now				: runs the script immediately, ignoring any timetables that may have been set
--page [pagename] 	: only run the script on [pagename] as specified in config.yml 'name' parameter
--debug             : Debugging mode, don't send emails but output everything to screen instead
```

I would recommend using the `sitePinger.sh` script included, which ensures that two copies of this aren't running at the same time, and kills the script if it gets stuck and runs longer than 5 minutes (see roadmap and bugs section below).

### Requires following Python libraries

Install these Python libraries with pip from the command line, if you don't have them loaded already

- pip3 install bs4
- pip3 install yagmail

### Changelog

#### Version 0.2, 3 June 2020

- Improved robustness of checks for when a site was last scraped, based on the file modification times
- Added support for mercury-parser
- General minor clean-up of code and lots of bug fixes

#### Version 0.1
- Dirty initial script that just about did the job


## Roadmap and known bugs

- Refactor code, which is a bit of a not so beautiful soup right now
- When there are internet issues, yagmail sometimes crashes, which could cause you to lose a previous scrape.
	- Get script to terminate and repeat the yagmail function if it runs for longer than a certain time, without dataloss
- Improve the config_default.yml file's examples to a more dynamic page
- Improve and refactor the config.yml format a tad, to make it a bit easier to understand and modify 
- Improve support for images and the like