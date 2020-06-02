#!/usr/bin/python3
import requests
import os
import difflib
import time
import subprocess
from bs4 import BeautifulSoup
import sys
from pprint import pprint
import datetime
import time
import yagmail
import re
import json

now = datetime.datetime.now()

class webpageProcessor:
	args = list()
	checkOnlyThisPage = False
	debug = False


	def __init__(self, page, config):
		self.page = page
		self.config = config
		self.dir = os.path.dirname(__file__)
		self.savepath = os.path.join(self.dir, './'+ self.config['scrapeFilesFolder'] +'/')  # where the files are located
		self.checkCmdLineArgs()
		self.processPage()

	# Check if any command line arguments supplied, then set self.args if there are some...
	def checkCmdLineArgs(self):
		self.checkOnlyThisPage = False
		self.args = list() #re-initialise args
		pageArgIsSet = False
		
		if len(sys.argv) > 1:
			i = 0
			for arg in sys.argv:
				i += 1
				if i > 1: # Skip argv[0], which is the script name
					self.args.append(arg)

					if arg == "--debug":
						self.debug = True
					if arg == "--help" or arg == "-h":
						self.showHelp()

					#check if preceding argument was "--page" and then set
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
		quit()


	def getPage(self):
		url = self.page['url']
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
		}

		r = requests.get(url, headers=headers)
		if self.debug:
			print("----------------Full FETCH TEXT-----------------")
			print(r.text)
		return r.text


	def stripWhitespaces(self, content):
		out = ""
		for line in content.splitlines():
			out += line.strip() + "\n"
		return out


	def compareFile(self, latestPageContent, oldPageContent):
		compare = "";
		for line in difflib.unified_diff(self.stripWhitespaces(oldPageContent).splitlines(), self.stripWhitespaces(latestPageContent).splitlines(), fromfile='oldContent', tofile='latestContent', lineterm=''):
			if not 'onlyAdditions' in self.page or line.startswith("+"): # if 'onlyAdditions' is set, ignore anything removed from the page
				compare += line + "\n"
		if self.debug:
			print("-------------------DEBUG DIFF--------------------")
			print(compare)
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
		soup = BeautifulSoup(content, 'html.parser')
		htmlSoup = soup.find_all(searchWithinTagDict['tag'], searchWithinTagDict['attr'])
		if not htmlSoup: # If nothing found with attr (as class), then try searching for attr as ID fallback
			htmlSoup = soup.find_all(searchWithinTagDict['tag'], id=searchWithinTagDict['attr'])
		#htmlSoup = soup.find(class_=searchWithinTagDict['attr'])
		# html = soup.get_text()
		# print(htmlSoup)
		# html = htmlSoup.get_text() #" ".join(htmlSoup)
		for oneSoup in htmlSoup:
			if self.debug:
				print("---------------------------------------------")
				print("-----------------SOUP CONTENT----------------")
				print("---------------------------------------------")
				pprint(oneSoup)
			#input()
			html += oneSoup.get_text() + "\n" #.get_text() #" ".join(htmlSoup)
		return html


	def coloriseEmailBodyDiff(self, string):
		out = ''
		for line in string.splitlines():
			if line.startswith("+"):
				out += "<span style='color:green'>" + line + "</span><br>"
			elif line.startswith("-"):
				out += "<span style='color:red'>" + line + "</span><br>"
			else:
				out += "<span style='color:#ccc'>" + line + "</span><br>"
		return out


	def sendAlertEmail(self, body):
		yag = yagmail.SMTP({self.config['emailAccount']: "[ALERT]"}, self.config['emailPassword'])
		contents = [body]
		yag.send(self.config['emailRecipient'], '[Changed] ' + page['name'], contents)


	def executeAtThisTime(self):
		#Skip if page['minutes'] is set and script execution time is not a multiple of 'minutes'
		if 'minutes' in self.page:
			if now.minute % self.page['minutes'] == 0:
				return True
		elif 'hours' in self.page:
			if now.hour % self.page['hours'] == 0 and (now.minute == self.config['defaultCheckOnMinute'] or self.config['defaultCheckOnMinute'] == "*"): # if hours is set, then checks only when current time equals to self.config['defaultCheckOnMinute'] 
				return True
		# Else only execute scripts every hour on the 1st minute
		elif now.minute == self.config['defaultCheckOnMinute'] or self.config['defaultCheckOnMinute'] == "*":
			return True
		else:
			return False


	def processPage(self):
		if not self.executeAtThisTime() and "--now" not in self.args:
			# print("Time not right")
			return False

		if self.checkOnlyThisPage:
			if self.checkOnlyThisPage != self.page['name']:
				# if the --page argument was provided with a page name, skip any pages that are NOT this page name
				return False

		try:
			print("Checking for " + self.page['name'])
			self.latestPageContent = self.getPage()
			# self.latestPageContent = '' #debugging only fast
		except: 
			self.latestPageContent = 'error'
		filename = self.savepath + self.page['name'] + ".txt"

		if 'json' in self.page:
			convertedFromJson = json.loads(self.latestPageContent)
			self.latestPageContent = convertedFromJson[self.page['json']]

		if 'searchWithinTag' in self.page:
			self.latestPageContent = self.returnContentBetweenTags(self.page['searchWithinTag'])
			print(self.latestPageContent)

		if os.path.isfile(filename) and not self.latestPageContent == 'error' and len(self.latestPageContent) > 10:
			with open(filename, 'r') as file:
				oldPageContent = file.read()
			diffString = self.compareFile(self.latestPageContent, oldPageContent)
			if diffString:
				#print(diffString)
				print("Difference found, renamed to " + filename + ".old, saving new file")
				
				if self.debug:
					print("-----------------LATEST PAGE CONTENT----------------")
					print(self.latestPageContent)
					#input("Press any key to open .diff (no files modified)")
				else:
					os.rename(filename, filename + ".old")
					self.saveFile(filename, self.latestPageContent)
					self.saveFile(filename + ".diff", diffString)

				if not self.debug:
					print(filename + ": Emailing")
					emailbody = "<a href='" + self.page['url'] + "'>" + self.page['url'] + "</a><br>" + self.coloriseEmailBodyDiff(diffString)
					self.sendAlertEmail(emailbody)

			else:
				print("No change in url " + self.page['name'])

		elif len(self.latestPageContent) > 10 and not self.debug:
			self.saveFile(filename, self.latestPageContent)
			print(filename + ": no file exists, saving first")
		
		if not "--now" in self.args:
			time.sleep(2)


from config import yamlCfg

configFile = os.path.dirname(__file__) + "/config.yml"
try:
	open(configFile, 'r')
except IOError:
	configFile = os.path.dirname(__file__) + "/config_default.yml"

cfg = yamlCfg(configFile)

def checkLastRunTime(config):
	scrapesFolder = os.path.dirname(__file__) + "/" + config['scrapeFilesFolder']
	lastRunFile = scrapesFolder + "/lastRun"
	if not os.path.exists(scrapesFolder):
		os.makedirs(scrapesFolder)
	try:
		file = open(lastRunFile, 'r')
	except IOError:
		file = open(lastRunFile, 'w')
	lastRunTime = os.path.getmtime(lastRunFile)
	maxAge = config['runAtLeastEveryXHours']*60*60
	diffTime = time.time() - lastRunTime
	if diffTime > maxAge:
		print("Not run within the last " + str(config['runAtLeastEveryXHours']) + " hours, will run all scrapes now")
		sys.argv.append("--now")
	else:
		print("Last run: " + str(round(diffTime)) + " seconds ago")

checkLastRunTime(cfg['config'])

for key, page in cfg['pages'].items():
	page['name'] = key
	Processor = webpageProcessor(page, cfg['config'])

lastRunFile = os.path.dirname(__file__) + "/" + cfg['config']['scrapeFilesFolder'] + "/lastRun"
os.utime(lastRunFile,(round(time.time()), round(time.time()))) # touch lastRun file as current time