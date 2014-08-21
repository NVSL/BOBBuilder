#!/usr/bin/env python

from lxml import etree as ET;
import argparse
import pipes
import sys
import csv
import time
import StringIO
import unicodedata
import re
import gcom
import datetime
import XMLUtil
import pyUtil

from lxml import html
from lxml import etree


class ScrapeError(Exception):
    def __init__(self, s):
        self.s = s
    def __str__(self):
        return repr(self.s)
    
def scrapeAdaFruit(productID):
    t = pipes.Template()
    print "Scraping Adafruit product "  + str(productID),
    url = "http://adafru.it/"+ str(productID)
    t.prepend("wget " +url + " -O - 2>/dev/null", ".-")
    f = t.open("", "r")
        
    parser = etree.HTMLParser(recover=True)
    tree = etree.parse(f, parser)
#    for i in parser.error_log:
#        print i

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
        return {"id": productID,
                "name": name.text.strip(), 
                "price": price.text.strip(),
                "url" : url}

def scrapeSparkFun(productID):
    raise Exception("Spark fun is broken at the moment")

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


parser = argparse.ArgumentParser(description="Tool for auto-generating packages for breakout boards.  Give it a product id and a vendor, and a keyname for the component, and it will, by default, create a direcotry for it and put the .gcom file there with some fields filled in.")
parser.add_argument("-m", required=True, type=str, nargs=1, dest='manufacturer', help="manufacturer (currently adafruit or sparkfun)")
parser.add_argument("--productid", required=False, type=str, nargs=1, dest='id', help="product id")
parser.add_argument("--keyname", required=True, type=str, nargs=1, help="keyname for this component")
parser.add_argument("-o", required=False, type=str, nargs=1, help="output file. default == keyname")

args = parser.parse_args()

scrapers = {"ADAFRUIT": scrapeAdaFruit,
            "SPARKFUN": scrapeSparkFun}

URLPrefix = {"ADAFRUIT": "http://adafru.it/",
            "SPARKFUN": "https://www.sparkfun.com/products/"}

normalizedManufacturers = {"ADAFRUIT": "Adafruit",
                          "SPARKFUN": "Sparkfun"}

url = URLPrefix[args.manufacturer[0].upper()] + "/" + str(args.id)
scraper = scrapers[args.manufacturer[0].upper()]

try:
    r = scraper(args.id[0])
    print r
except ScrapeError as e:
    print str(e) + ", retrying"
    time.sleep(5)
    try:
        r = scraper(args.id[0])
        print r
    except:
        print str(e) + ", giving up"
        sys.exit(1)

default="""
<component>
  <name></name>
  <QA tested="false"/>
  <keyname></keyname>
  <variant>
    <supplier/>
    <documentationURL></documentationURL>
    <longname></longname>
  </variant>
</component>
"""

et = ET.fromstring(default)
et.find("keyname").text =args.keyname[0]
et.find("name").text =r["name"]
updates={"name":normalizedManufacturers[args.manufacturer[0].upper()], 
          "price":r["price"].replace("$",""),
         "updated": str(datetime.date.today()),
         "part-number":args.id[0]}

et.find("variant/documentationURL").text =r["url"]
et.find("variant/longname").text = r["name"]


for i in updates:
    et.find("variant/supplier").set(i,updates[i])    

e = ET.ElementTree()
e._setroot(et)


if args.o is not None:
    fname = args.o[0]
else:
    pyUtil.docmd("mkdir -p " + args.keyname[0])
    fname = args.keyname[0] + "/" + args.keyname[0] + ".gcom"

XMLUtil.formatAndWrite(e,fname, xml_declaration=True)
