#!/usr/bin/env python

# Written by Georg Sluyterman (georg@sman.dk) 2012.
LOCKFILE	= "status.html"			# Both a statuspage and a semaphore restricting the running of more than one instance of the script
INDEXSITE	= "http://wiki.hal9k.dk/qr"	# The page we fetch with a list of the pages we visit
LOGFILE		= "lastrun.html"		# A log of the last run
MAPPINGFILE	= "mapping.html"		# The qrMap list printed for the users to view it
HTACCESSFILE	= ".htaccess"			# The location of the resulting .htaccess

HTMLHEAD	= """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>

  <meta content="text/html; charset=utf-8" http-equiv="Content-Type">

  <title>qrRedirectGenerator</title>
</head>

<body>
"""
HTMLTAIL	= """
  <p>
    <a href="http://validator.w3.org/check?uri=referer"><img
      src="http://www.w3.org/Icons/valid-html401" alt="Valid HTML 4.01 Transitional" height="31" width="88"></a>
  </p>
</body>
</html>
"""
HTACCESSHEAD 	= """Options +FollowSymLinks
RewriteEngine on
"""
HTACCESSTAIL 	= """
RewriteRule (HQR.*) http://wiki.hal9k.dk/infrastruktur/it-services/qr/qr-kode_infoside [R=307,L]
"""
REWRITETAIL	= "[R=307,L]"	# Temporary redirect, last rule to match

# Import modules
try:
    import time, sys, re, urllib, HTMLParser, lxml.etree, StringIO, urlparse, os
    from natsort import natsorted
except ImportError as e:
    print "Failed loading one or more modules: ({})".format(e)
    print "Exiting!"
    exit(1)

# ISO 8601 start time
timestart = time.strftime("%Y-%m-%dT%H:%M:%S") 

## Check if script is already running
# FIXME something more atomar should be made. E.g. with a file lock that would also work on AFS
# open lockfile
try: 
    lockfile = open(LOCKFILE,'r+')
except:
    sys.stderr.write(timestart + ": Failed to open " + LOCKFILE + "\nTouch it if it does not exist.\nExiting\n")
    exit(1)
# Check if program is already running
prgRunning = False
for line in lockfile:
    match = re.search(re.compile(r'PROGRAM CURRENTLY RUNNING'), line)
    if match:
        prgRunning = True
# Sometimes the script does not complete. FIXME An improvement would be to actually test if the script is running.
if ( time.time() - os.path.getmtime(LOCKFILE) ) > 3600.0:
    prgRunning = False
if prgRunning:
    sys.stderr.write(timestart + ": An instance of " + sys.argv[0] + " is already running.\nExiting!\n")
    exit(2)
# Program was not running. Truncate file.
lockfile.seek(0, 0)
lockfile.truncate()

# Write new content
try:
    lockfile.write(HTMLHEAD + timestart + ": " + sys.argv[0] + " - PROGRAM CURRENTLY RUNNING" +  HTMLTAIL)
except:
    sys.stderr.write(timestart + ": Failed to write to " + LOCKFILE + "\nExiting!\n")
    lockfile.close()
    exit(1)
try:
    lockfile.close()
except:
    sys.stderr.write(timestart + ": Failed to close " + LOCKFILE + "\nExiting!\n")
    exit(1)

# FIXME should be made in to a class with the above and the be made to use file locking.
def releaseLockFile(LOCKFILE, exitstatus=0):
    try: 
        lockfile = open(LOCKFILE,'w')
    except:
        sys.stderr.write(timestart + ": Failed to open " + LOCKFILE + "\nTouch it if it does not exist.\nExiting\n")
        exit(1)
    # Write new content
    try:
        lockfile.write(HTMLHEAD + timestart + ": " + sys.argv[0] + " started<br>\n" + timeend + ": " + sys.argv[0] + " ended\n"  +  HTMLTAIL)
    except:
        sys.stderr.write(timestart + ": Failed to write to " + LOCKFILE + "\nExiting!\n")
        lockfile.close()
        exit(1)
    try:
        lockfile.close()
    except:
        sys.stderr.write(timestart + ": Failed to close " + LOCKFILE + "\nExiting!\n")
        exit(1)
    exit(exitstatus)

# object for writing to output files
class LogToFile:
    def __init__(self, logfile):
        self.logfile = logfile
    def open(self):
        try:
            self.log = open(self.logfile, 'w') # An existing file is overwritten
        except:
            sys.stderr.write("Failed to open file " + self.logfile + "\n")
            raise IOError()
        return self
    def write(self, message):
        try:
            self.log.write(message)
        except:
            sys.stderr.write("Failed to write to file " + self.logfile + "\n")
            raise IOError()

    def close(self):
        try:
            self.log.close()
        except:
            sys.stderr.write("Failed closing file " + self.logfile + "\n")
            raise IOError()
        # FIXME fsync of file and folder would be pretty

# Open logfile for writing
log = LogToFile(LOGFILE)
try:
    log = log.open()
except:
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    log.write(HTMLHEAD + time.strftime("%Y-%m-%dT%H:%M:%S") + sys.argv[0] + " logging started<br>\n")
except:
    releaseLockFile(LOCKFILE, exitstatus=1)
# Fetch homepage
try:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Opening URL " + INDEXSITE + "<br>")
    indexsite = urllib.urlopen(INDEXSITE)
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to fetch page " + INDEXSITE + "Exiting!<br>")
    releaseLockFile(LOCKFILE, exitstatus=1)
sitecontent = indexsite.read()
indexsite.close()

### Parse indexpage for links
# parse through lxml, otherwise HTMLParser wont eat the table from DokuWiki..
parser = lxml.etree.HTMLParser()
tree   = lxml.etree.parse(StringIO.StringIO(sitecontent), parser)
result = lxml.etree.tostring(tree.getroot(), pretty_print=True, method="html")
## create urlList with all URLs we need to parse for QR identifiers
urlList = []
baseURL = urlparse.urlparse(INDEXSITE)[0] + "://" + urlparse.urlparse(INDEXSITE)[1]
# Modified class to let us fish out the links we need
class MyHTMLParser(HTMLParser.HTMLParser):
    def handle_starttag(self, tag, attrs):
        try:
            a = attrs[1][1]
            if tag == "a" and attrs[1][1] == 'wikilink1':
                url = baseURL + attrs[0][1]
                if url not in urlList:
                    urlList.append(url)
        except:
            pass

parser = MyHTMLParser()
result = parser.feed(result)
urlList.sort()

# Parse all subsequent pages
def getPageContent(url):
    try:
        site = urllib.urlopen(url)
        content = site.read()
        site.close()
        return content
    except:
        log.write("Failed to retrieve " + url + "<br>\n")
        return None
mappingDict = {}
for url in urlList:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " URL " + url + "<br>")
    content = getPageContent(url)
    if content:
        match = re.findall(re.compile(r'HQR\d{1,6}'), content)
        if match:
            while True:
                try:
                    key = match.pop()
                    if mappingDict.has_key(key) and mappingDict[key] != url:
                        log.write("Ignoring key " + key + " since it is already registered to the URL " +  mappingDict[key] + " but is also found the page " + url + "<br>\n")
                    else:
                        mappingDict[key] = url
                except:
                    break
log.write("Fetched " + str(len(urlList)) + " pages from " + baseURL + " with " + str(len(mappingDict)) + " unique keys<br>\n")

## Write .htaccess file
# Create sorte list over keys
keys = []
for key, url in mappingDict.iteritems():
    keys.append(key)
keys = natsorted(keys)

# Create content for .htaccess file
htcontent = HTACCESSHEAD
for key in keys:
    htcontent += "RewriteRule " + key + "$ " + mappingDict[key] + " " + REWRITETAIL + "\n"
htcontent += HTACCESSTAIL

# Write htcontent to .htaccess file
htfile = LogToFile(HTACCESSFILE)
try:
    htfile.open()
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to open " + HTACCESSFILE + "\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    htfile.write(htcontent)
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to write to " + HTACCESSFILE + "<br>\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    htfile.close()
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to close " + HTACCESSFILE + "<br>\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)

## Write mappingtable
# Brepare content
mtcontent = HTMLHEAD
mtcontent += "<H2>Mappingtable from the last run</H2>\n<table>"
for key in keys:
    mtcontent += "<tr><td><strong>" + key + "&nbsp</strong></td><td><a href=\"" + mappingDict[key] + "\">" + mappingDict[key] + "</a></td></tr>\n"
mtcontent += "</table>" + HTMLTAIL

# write mtcontent to file
mtfile = LogToFile(MAPPINGFILE)
try:
    mtfile.open()
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to open " + MAPPINGFILE + "<br>\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    mtfile.write(mtcontent)
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to write to " + MAPPINGFILE + "<br>\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    mtfile.close()
except:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " Failed to close " + MAPPINGFILE + "<br>\nExiting!<br>\n" + HTMLTAIL)
    releaseLockFile(LOCKFILE, exitstatus=1)

# Write last parts to logfile
try:
    log.write(time.strftime("%Y-%m-%dT%H:%M:%S") + sys.argv[0] + " logging ended<br>\n" + HTMLTAIL)
except:
    log.close()
    releaseLockFile(LOCKFILE, exitstatus=1)
try:
    log.close()
except:
    releaseLockFile(LOCKFILE, exitstatus=1)

timeend = time.strftime("%Y-%m-%dT%H:%M:%S")
## Ending of program. Write the last time we ran in the lockfile
releaseLockFile(LOCKFILE)
