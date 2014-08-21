#!/usr/bin/env python

from lxml import etree as ET;
import argparse
import pipes
import sys
import csv
import time
import StringIO
import unicodedata

from lxml import html
from lxml import etree

parser = argparse.ArgumentParser(description="Tool for auto-generating packages for breakout boards")
parser.add_argument("-db", required=True, type=str, nargs=1, dest='dbFile', help="Break out board database file")
parser.add_argument("--productid", required=False, type=str, nargs=1, dest='id', help="filter on a single product id")
parser.add_argument("--force", required=False, dest='rescrape', action='store_true', help="Overwrite existing package")

args = parser.parse_args()

class ScrapeError(Exception):
    def __init__(self, s):
        self.s = s
    def __str__(self):
        return repr(self.s)
    
def scrapeAdaFruit(productID):
    t = pipes.Template()
    print "Scraping Adafruit product "  + str(productID),
    t.prepend("wget http://adafru.it/"+ str(productID) + " -O - 2>/dev/null", ".-")
    f = t.open("", "r")
        
    parser = etree.HTMLParser(recover=True)
    tree = etree.parse(f, parser)
    for i in parser.error_log:
        print i


    #tree.write(sys.stdout)
    name = None
    price = None
    if tree.getroot() is None:
        raise ScrapeError("No root for Adafruit " + str(productID))

    for i in tree.getroot().iter(): #[@id='prod-right-side']")
        if i.tag == "div" and i.get("id") == "prod-right-side":
            name = i.find("h1");
            price = i.find("div[@id='prod-price']")

    if name is None or price is None:
        raise ScrapeError("Scrape failed for Adafruit " + str(productID))
    else:
        print name.text.strip() + " " +  price.text.strip()
        return [productID,name.text.strip(), price.text.strip()]

def scrapeSparkFun(productID):
    t = pipes.Template()
    print "Scraping Sparkfun product "  + str(productID),
    cmd = "curl --location https://www.sparkfun.com/products/"+ str(productID) + " 2>/dev/null"
#    print cmd
    t.prepend(cmd, ".-")
    f = t.open("", "r")
        
    parser = etree.HTMLParser(recover=True)
    tree = etree.parse(f, parser)
#    for i in parser.error_log:
#        print i

#    tree = html.parse(f)

    #tree.write(sys.stdout)
    name = None
    price = None
    
    if tree.getroot() is None:
        raise ScrapeError("No root for Sparkfun " + str(productID))

    for i in tree.getroot().iter(): 
        if i.tag == "div" and i.get("class") == "description":
            for j in i.findall("div[@class='hidden-sm hidden-xs']"):
                for k in j.findall("div[@class='title']"):
                    for l in k.findall("h1"):
                        name = l.text.strip()
        if i.tag == "div" and i.get("class") == "sale-wrap":
#            print "1" + str(i.attrib)
            for k in i.findall("h3"):
                for l in k.findall("span"):
                    price = l.text.strip()
        if i.tag == "meta" and i.get("name") == "twitter:url":
            pid = i.get("content").split("/")[-1]
            if pid != productID:
                productID = pid
                print "Updated product ID: "  + pid

    if name is None or price is None:
        raise ScrapeError("Scrape failed for Sparkfun " + str(productID))
    else:
        if price[0] != "$":
            price = "$" + price
        print name + " " +  price
        return [productID,name, price]

def GetCSVHeader(fn):
    f = open(fn, "rb")
    r = csv.reader(f)
    x = None
    for t in r:
        x = t
        break;
    f.close()
    print x
    return x

#print scrapeAdaFruit(1856)
#sys.exit(0)
dbf = open(args.dbFile[0], "rb")
db = csv.DictReader(dbf)

header = GetCSVHeader(args.dbFile[0])
output = StringIO.StringIO()
out = csv.DictWriter(output, header)
t = {}
for i in header:
    t[i] = i
out.writerow(t)

scrapers = {"ADAFRUIT": scrapeAdaFruit,
            "SPARKFUN": scrapeSparkFun}

URLPrefix = {"ADAFRUIT": "http://adafru.it/",
            "SPARKFUN": "https://www.sparkfun.com/products/"}

for row in db:
    if row["Name"].strip() == "" or row["Price"].strip() == "" or args.rescrape:
        if row["Supplier"].upper() in scrapers:
            scraper = scrapers[row["Supplier"].upper()]

            if row["PartNumber"] == "":
                out.writerow(row)
                continue;

            for p in row["PartNumber"].split(","):
                if p == "":
                    continue
                if args.id is not None and args.id[0] != p:
#                    print p  + " " + args.id + " " + repr(row)
                    out.writerow(row)
                    continue;

                row["PartNumber"] = p
                try:
                    r = scraper(p)
                    row["PartNumber"] = r[0]
                    r[1] = unicodedata.normalize("NFKD", unicode(r[1])).encode('ascii','ignore')
                    row["Name"] = r[1]
                    row["Price"] = r[2]
                    row["DocURL"] = URLPrefix[row["Supplier"].upper()] + r[0]
                except ScrapeError as e:
                    print str(e) + ", retrying"
                    time.sleep(5)
                    try:
                        r = scraper(p)
                        row["Name"] = r[0]
                        row["Price"] = r[1]
                    except:
                        print str(e) + ", giving up"

                out.writerow(row)
        else:
            out.writerow(row)
    else:
        out.writerow(row)

dbf.close()
open(args.dbFile[0], "wb").write(output.getvalue())
