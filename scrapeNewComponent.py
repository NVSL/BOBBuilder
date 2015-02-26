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
from bs4 import BeautifulSoup
import requests
#import gcom
import datetime
import XMLUtil
import pyUtil
import os

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
    print "Scraping Sparkfun product " + productID
    url = "https://www.sparkfun.com/products/" + productID
    r=requests.get(url)
    soup = BeautifulSoup(r.text)
    name = soup.find(class_='product-title')
    if name is None:
        raise ScrapeError("Scrape failed")
    name = name.find('h1').text.strip()
    price = soup.find(class_='pricing').find(class_='sale-wrap').text.replace("$","").strip()
    find_id = re.compile('-(\d+)\W')
    check_id = find_id.search(soup.find(class_='sku').text).group(1)
    if check_id != productID:
        print "Product ID changed, {0} is now {1}".format(productID,check_id)
        productID = check_id
    eagle_link = soup.find( name='a', href=re.compile('.*\.zip$',flags=re.IGNORECASE), text=re.compile('eagle',flags=re.IGNORECASE) )
    if eagle_link:
        eagle_link = eagle_link["href"]
    return {"id":productID,
            "name":name,
            "price":price,
            "url":url,
            "eagle_link":eagle_link}

#TODO: Get rid of most of this stuff and just take the product URL instead?
parser = argparse.ArgumentParser(description="""Tool for auto-generating packages for breakout boards.
    Give it a product id and a vendor, and a keyname for the component, and it will, by default, create a directory for it and put the .gcom file there with some fields filled in.
    If there's a .brd and .sch file provided it'll attempt to get those too.""")
parser.add_argument("-m", required=True, type=str, nargs=1, dest='manufacturer', help="manufacturer (currently adafruit or sparkfun)")
parser.add_argument("--productid", required=True, type=str, nargs=1, dest='id', help="product id")
parser.add_argument("--keyname", required=True, type=str, nargs=1, help="keyname for this component")
parser.add_argument("-o", required=False, type=str, nargs=1, help="output file. default == keyname")
parser.add_argument("--bob",action='store_true',help="This is a breakout board")

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
<variant>
  <name></name>
  <QA tested="false"/>
  <keyname></keyname>
  <variant>
    <longname></longname>
    <supplier/>
    <documentationURL></documentationURL>
  </variant>
</variant>
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

if "eagle_link" in r:
    out_dir = os.path.dirname(fname)
    print "Downloading Eagle .brd and .sch zip file to ext folder..."
    ext_folder = out_dir + "/ext"
    pyUtil.docmd("mkdir " + ext_folder)
    pyUtil.docmd("curl -s {0} > {1}/eagle.zip".format(r["eagle_link"],ext_folder))
    if args.bob:
        et.insert(3,ET.Element('bobspec'))      #Inserts after <keyname>, wasn't sure how to just say 'insert after keyname'
        bobspec = et.find('bobspec')
        bobspec.attrib['device-name'] = args.keyname[0]
        download = ET.SubElement(bobspec,'downloadURL')
        download.attrib['protocol'] = 'zip'     #Nothing other than zip at the moment
        download.text = r['eagle_link']
        brd = ET.SubElement(bobspec,'brdfile')
        sch = ET.SubElement(bobspec,'schfile')
        try:
            pyUtil.docmd("unzip {0}/eagle.zip -d {1}".format(ext_folder,ext_folder))
            pyUtil.docmd("rm {0}/eagle.zip".format(ext_folder))
            for f in os.walk(ext_folder).next()[2]:
                if f.endswith('.brd'):
                    brd.text = 'ext/' + f
                if f.endswith('.sch'):
                    sch.text = 'ext/' + f
        except OSError as e:
            print str(e)
            print "Couldn't unzip Eagle stuff"


XMLUtil.formatAndWrite(e,fname, xml_declaration=True)
