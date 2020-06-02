#!/usr/bin/python3

from config import yamlCfg
import requests
import os
import difflib
import time
import subprocess
import sys
from pprint import pprint
import datetime
import time
import re
import json
from shlex import quote
from bs4 import BeautifulSoup
import yagmail

configFile = os.path.dirname(__file__) + "/config.yml"
now = datetime.datetime.now()

class webpageProcessor:
    args = list()
    checkOnlyThisPage = False
    debug = False

    def __init__(self, page, config):
        self.page = page
        self.config = config
        self.dir = os.path.dirname(__file__)
        self.savepath = os.path.join(self.dir, './' + self.config['scrapeFilesFolder'] + '/')  # where the files are located
        self.checkCmdLineArgs()

    # Check if any command line arguments supplied, then set self.args if there are some...
    def checkCmdLineArgs(self):
        self.checkOnlyThisPage = False
        self.args = list()  # re-initialise args
        pageArgIsSet = False

        if len(sys.argv) > 1:
            i = 0
            for arg in sys.argv:
                i += 1
                if i > 1:  # Skip argv[0], which is the script name
                    self.args.append(arg)

                    if arg == "--debug":
                        self.debug = True
                    if arg == "--help" or arg == "-h":
                        self.showHelp()

                    # check if preceding argument was "--page" and then set
                    if pageArgIsSet:
                        self.checkOnlyThisPage = arg
                    if arg == "--page":
                        pageArgIsSet = True
                    else:
                        pageArgIsSet = False

    def showHelp(self):
        print("Scrape all pages specified in config.yml")
        print("Usage:")
        print("Run without parameters to scrape according to configured timetable")
        print("--now            Scrape now, ignore timetables")
        print("--page [pagename]    Scrape only pagename")
        print("--debug              Debug, don't send emails")
        quit()

    def getPage(self):
        url = self.page['url']
        headers = {
            'User-Agent': self.config['useragent'],
        }

        try:
            r = requests.get(url, headers=headers)
        except requests.exceptions.Timeout:
            print("getPage: Timeout error")
            return "Timeout"
        except requests.exceptions.TooManyRedirects:
            print("getPage: TooManyRedirects error")
            return "Too many redirects?"
        except requests.exceptions.RequestException as e:
            print("getPage: Some other error:")
            print(e)
            return e
        self.printDebug(r.text, "FULL FETCH TEXT")
        return r.text

    def stripWhitespaces(self, content):
        out = ""
        for line in content.splitlines():
            out += line.strip() + "\n"
        return out

    def compareFile(self, latestPageContent, oldPageContent):
        compare = ""
        for line in difflib.unified_diff(self.stripWhitespaces(oldPageContent).splitlines(), self.stripWhitespaces(latestPageContent).splitlines(), fromfile='oldContent', tofile='latestContent', lineterm=''):
            if 'onlyAdditions' not in self.page or line.startswith("+"):  # if 'onlyAdditions' is set, ignore anything removed from the page
                compare += line + "\n"
        self.printDebug(compare, "DIFF BETWEEN LATEST & OLD")
        return compare

    def saveFile(self, filename, content):
        with open(filename, 'w') as file:
            file.write(content)

    def returnContentBetweenTags(self, searchWithinTagDict):
        html = ''
        content = self.latestPageContent
        if 'strip' in self.page:
            for striptag in self.page['strip']:
                content = re.sub(r'<\/?' + striptag + '>', '', content)

        #  If xml is specified in 'parser' (such as with RSS), then parse as xml in beautiful soup
        if ('parser' in self.page
                and self.page['parser'] == 'xml'):
            soup = BeautifulSoup(content, 'xml')
        else:
            soup = BeautifulSoup(content, 'html.parser')

        # Select seems to actually work here, so use this instead in transition...
        if 'tag' not in searchWithinTagDict:
            htmlSoup = soup.select(searchWithinTagDict)
        # Fallback: if separate tag and attr are specified, then run find_all
        else:
            htmlSoup = soup.find_all(searchWithinTagDict['tag'], searchWithinTagDict['attr'])
            if not htmlSoup:  # If nothing found with attr (as class), then try searching for attr as ID fallback
                htmlSoup = soup.find_all(searchWithinTagDict['tag'], id=searchWithinTagDict['attr'])
        # htmlSoup = soup.find(class_=searchWithinTagDict['attr'])
        # html = soup.get_text()
        # print(htmlSoup)
        # html = htmlSoup.get_text() #" ".join(htmlSoup)
        for oneSoup in htmlSoup:
            self.printDebug(str(oneSoup), "CONTENT BETWEEN TAGS")
            # pprint(oneSoup)
            if ('parser' in self.page
                    and self.page['parser'] == 'html'):
                # html += oneSoup.prettify()
                html += str(oneSoup)
            else:
                html += oneSoup.get_text() + "\n"  # .get_text() #" ".join(htmlSoup)
        return html

    # Called manually in config.yml, to extract hyperlinks from found homepage
    def followhyperlinks(self, regexparser=""):
        #  Extract anything between title, name or https: etc...
        if not regexparser:
            regexparser = r'href=["\'][^"\']+["\']'
        pattern = re.compile(regexparser, re.MULTILINE | re.DOTALL)
        matches = pattern.findall(self.latestPageContent)
        #  if no hrefs found, then go for https://xyz url search, such as in RSS feeds
        if not matches:
            pattern = re.compile(r'(https?:\/\/[^\n\s<]+)', re.MULTILINE | re.DOTALL)
            matches = pattern.findall(self.latestPageContent)
        outstr = ("\n\n").join(matches)
        # Extract from hyperlinks the page: <div class="story-element story-element-text">
        self.latestPageContent = outstr


    # Called manually in config, to scrape each of the URLs found in followhyperlinks
    # And email their contnet
    def followHyperlinksGetArticle(self, diffString):
        # Grab the actual href urls only
        pattern = re.compile(r'href=["\']([^"\']+)["\']')
        matches = pattern.findall(diffString)
        for match in matches:
            pageurl = match
            pageurl = self.makeOneRelativeLinkAbsolute(pageurl)            

            #  populate a new onepage object, to launch
            #  a new webpageProcessor object so we can re-use its parsing functions
            onepage = {}
            onepage['url'] = pageurl
            onepage['name'] = self.page['name']

            #  Set return variable to "html" (or whatever it is, to ensure we're cleaning it right)
            if 'parser' in self.page:
                onepage['parser'] = self.page['parser']
            else:
                onepage['parser'] = "text"

            #  Specify the tags to scrape on the spider-scraped article content page
            #  as supplied by articleWithinTags values such as "h2, div, p.attribname"
            if 'articleWithinTags' in self.page['followhyperlinks']:
                onepage['searchWithinTagDict'] = self.page['followhyperlinks']['articleWithinTags']
            else:
                onepage['searchWithinTagDict'] = 'body'

            #  Run the specified scraper of the actual article content
            if 'mercury-parser' in self.page['followhyperlinks']:
                #mercury = 'mercury-parser onepage['url']'
                SinglePage = webpageProcessor(onepage, cfg['config'])
                print("Parsing with MERCURY-PARSER!")
                mercuryparserexecutable = str(self.config['mercuryparser'])
                fetchedhtml = os.popen(mercuryparserexecutable + ' "' + quote(onepage['url']) + '"').read()
                mercury_json = json.loads(fetchedhtml)
                print(fetchedhtml)
                subject = onepage['name'] + ": " + mercury_json.get('title')
                fetchedhtml = mercury_json.get('url') + "<br><br>" + \
                    mercury_json.get('title') + "<br><br>By: " + \
                    mercury_json.get('author') +  "<br><br>" + \
                    mercury_json.get('content')
            else:
                SinglePage = webpageProcessor(onepage, cfg['config'])
                SinglePage.latestPageContent = SinglePage.getPage()
                fetchedhtml = SinglePage.returnContentBetweenTags(onepage['searchWithinTagDict'])

                #  Add page's hyperlink to the top of page
                fetchedhtml = "<a href='" + pageurl + "'>" + pageurl + "</a>\n\n" + fetchedhtml

                # Create the subject line, rerunning returnContentBetweenTags to get page title
                if 'articlePageTitleTag' in self.page['followhyperlinks']:
                    SinglePage.page['parser'] = "text"
                    SinglePage.latestPageContent = fetchedhtml
                    scrapedTitle = SinglePage.returnContentBetweenTags(self.page[
                        'followhyperlinks']['articlePageTitleTag'])
                    print("$scrapedTitle: " + scrapedTitle)
                    subject = onepage['name'] + ": " + re.sub(r'[\n\s]+', ' ', scrapedTitle)
                else:
                    subject = onepage['name'] + ": " + fetchedhtml.partition('\n')[0]

                fetchedhtml = self.makeAllRelativeLinksAbsolute(fetchedhtml)
            
            #if not self.printDebug("$subject: " + subject + "\n\n" + fetchedhtml, "ARTICLE SCRAPED"):
            SinglePage.sendAlertEmail(fetchedhtml, subject)

    def coloriseEmailBodyDiff(self, string):
        out = ''
        for line in string.splitlines():
            if len(line) < 3:
                out += ""
            elif line.startswith("+"):
                out += "<span style='color:green'>" + line + "</span><br>"
            elif line.startswith("-"):
                out += "<span style='color:red'>" + line + "</span><br>"
            else:
                out += "<span style='color:#ccc'>" + line + "</span><br>"
        return out

    #  Add the website URL before the URL, if it starts with /
    def makeOneRelativeLinkAbsolute(self, pageurl):
        if not pageurl.startswith("http"):
            pageurl = self.getBaseUrl() + pageurl
        return pageurl
        
    #  Find all href URL links in the html and make sure they are not relative links
    #  If they are relative links, replace with baseurl
    def makeAllRelativeLinksAbsolute(self, htmlcontent):
        baseurl = self.getBaseUrl()
        htmlcontent = re.sub(r'(href=[\"\'])(\/[^\.\"\']+)', r'\1' + baseurl + r'\2', htmlcontent)
        return htmlcontent

    #  Ensure to strip also to get the base URL of the domai,n if we're scraping a sub-page
    def getBaseUrl(self):
        baseurl = re.sub(r'(https?:\/\/[^\/]+).*', r'\1', self.page['url'])
        return baseurl

    def printDebug(self, message="", header=""):
        if self.debug:
            if header:
                print("\n\n*************************** " + header + " ***************************\n")
            if message:
                print(message)
            return True
        else:
            return False

    #  Send email alert with body and (optional) subject via yagmail as configured
    def sendAlertEmail(self, body, subject=""):
        if not self.printDebug():
            yag = yagmail.SMTP({self.config['emailAccount']: "[ALERT]"}, self.config['emailPassword'])
            contents = [body]
            if not subject:
                subject = '[Changed] ' + page['name']
            yag.send(self.config['emailRecipient'], subject, contents)
        else:
            print("==============  DEBUG ==============")
            print("Would normally be sending this email:")
            print("Subject: " + page['name'])
            print(body)

    #  Check scrape file last touched time, to see if it's time to scrape it again
    #  Return true if it is time, false if it's not yet
    def isScheduledToRunNow(self):
        if "--now" in self.args:
            print("Forced scanning now due to command line parameter --now")
            return True
        elif ('minutes' in self.page
                or 'hours' in self.page):
            # Convert intervalTimeToMinutes
            if 'minutes' in self.page:
                scanTimeIntervalInMinutes = self.page['minutes']
            elif 'hours' in self.page:
                scanTimeIntervalInMinutes = self.page['hours'] * 60

            fileLastTouchedTime = getFileTouchedTime(self.filename)
            # print(fileLastTouchedTime)
            if beenRunMoreRecentlyThan(fileLastTouchedTime, scanTimeIntervalInMinutes):
                print(self.page['name'] + ":\tNot scanning, previous scan " + str(round((time.time() - fileLastTouchedTime) / 60)) + "mins ago, fewer than " + str(scanTimeIntervalInMinutes) + "mins interval.")
                return False
        return True

    #  The main page scrape processing function, which can also invoke followhyperlinks spider
    def processPage(self):
        if self.checkOnlyThisPage:
            if self.checkOnlyThisPage != self.page['name']:
                # if the --page argument was provided with a page name, skip any pages that are NOT this page name
                return False

        filename = self.savepath + self.page['name'] + ".txt"
        self.filename = filename
        
        if self.isScheduledToRunNow():
            touchFileNow(filename)
        else:
            return False

        try:
            print("***************************")
            print("Scanning " + self.page['name'])
            self.latestPageContent = self.getPage()
            # self.latestPageContent = '' #debugging only fast
        except:
            self.latestPageContent = 'some error in scanning page...'
            return False

        if 'json' in self.page:
            convertedFromJson = json.loads(self.latestPageContent)
            self.latestPageContent = convertedFromJson[self.page['json']]

        if 'searchWithinTag' in self.page:
            self.latestPageContent = self.returnContentBetweenTags(self.page['searchWithinTag'])

        # Run a specified custom function from yml, and parse the text through that...
        #  Deprecated, refactored into followhyperlinks
        if 'parseWithCustomFunction' in self.page:
            self.latestPageContent = globals()[self.page['parseWithCustomFunction']](self.latestPageContent)

        if 'followhyperlinks' in self.page:
            self.followhyperlinks()
        
        # print(self.latestPageContent)

        if (os.path.isfile(filename)
                and not self.latestPageContent == 'error'
                and len(self.latestPageContent) > 10):
            with open(filename, 'r') as file:
                oldPageContent = file.read()
            
            diffString = self.compareFile(self.latestPageContent, oldPageContent)
            if diffString:
                # print(diffString)
                print("Difference found, renamed to " + filename + ".old, saving new file")

                # If the string in processdiffWithFunciton exists in global function name space,
                # then run that on the diffstring (or crash right now, if doesn't exist)
                if 'processDiffWithFunction' in self.page:
                    globals()[self.page['processDiffWithFunction']](diffString)

                if ('followhyperlinks' in self.page):
                    #and ( 'articleWithinTags' in self.page['followhyperlinks'] or 'mercury-parser' in self.page['followhyperlinks']) ):
                    self.followHyperlinksGetArticle(diffString)

                self.printDebug(self.latestPageContent, "LATEST PAGE CONTENT")
                self.printDebug(diffString, "LATEST PAGE DIFF")

                diffString = self.makeAllRelativeLinksAbsolute(diffString)

                # DO NOT SEND EMAIL if...
                # - we are also craping URLs
                # - we are in debug mode...
                if (not self.printDebug()
                        and 'followhyperlinks' not in self.page):
                    print(filename + ": Emailing")
                    emailbody = "<a href='" + self.page['url'] + "'>" \
                        + self.page['url'] \
                        + "</a><br>" \
                        + self.coloriseEmailBodyDiff(diffString)
                    self.sendAlertEmail(emailbody)
                
                #  Save new files. Do last, in case email or other network functions crash
                if not self.printDebug():
                    #  input("Press any key to open .diff (no files modified)")
                    os.rename(filename, filename + ".old")
                    self.saveFile(filename, self.latestPageContent)
                    self.saveFile(filename + ".diff", diffString)

            else:
                print("No change in url " + self.page['name'])

        elif len(self.latestPageContent) > 10 and not self.printDebug():
            self.saveFile(filename, self.latestPageContent)
            print(filename + ": no file exists, saving first")
        
        print("***************************")

        if "--now" not in self.args:
            time.sleep(2)



try:
    open(configFile, 'r')
except IOError:
    configFile = os.path.dirname(__file__) + "/config_default.yml"

cfg = yamlCfg(configFile)


def touchFileNow(filename):
    os.utime(filename, (round(time.time()), round(time.time())))  # touch lastRun file as current time


def getFileTouchedTime(filename):
    try:
        file = open(filename, 'r')
    except IOError:
        file = open(filename, 'w')
    lastTouchTime = os.path.getmtime(filename)
    return lastTouchTime


def beenRunMoreRecentlyThan(lastTime, maxAgeMinutes):
    diffTime = time.time() - lastTime
    # print(time.time())
    # print(lastTime)
    # print(diffTime)
    if diffTime > (maxAgeMinutes * 60):
        print(">>> Running now, it's been more than " + str(maxAgeMinutes) + " minutes")
        return False
    else:
        #  print("Last run: " + str(now) + " (" + str(round(diffTime)) + " seconds ago)")
        return True


for key, page in cfg['pages'].items():
    page['name'] = key
    Processor = webpageProcessor(page, cfg['config'])
    # Processor.checkCmdLineArgs()
    Processor.processPage()

lastRunFile = os.path.dirname(__file__) + "/" + cfg['config']['scrapeFilesFolder'] + "/lastRun"
touchFileNow(lastRunFile)  # touch lastRun file as current time
