#!/usr/bin/python

import argparse
import sys
import csv
import base64
import EagleBoardToDevice
import re

parser = argparse.ArgumentParser(description="Tool for auto-generating packages for breakout boards")
parser.add_argument("-db", required=True, type=str, nargs=1, dest='dbFile', help="Break out board database file")
parser.add_argument("-lbr", required=True, type=str, nargs=1, dest='lbrFile', help="Eagle Library to Target")
parser.add_argument("--boards", required=True, type=str, nargs=1, dest='boardsDirectory', help="Directory with the brd files")
args = parser.parse_args()

dbf = open(args.dbFile[0], "rb")
db = csv.DictReader(dbf)

class Args:
    pass

template = """<b>{shortname}</b><p>{name}</p><p><b>Further information:</b><a href="{url}">{linktext}</a></p><p><b>Cost:</b>{cost}</p>"""

for row in db:

    if row["Filename"] == "" or row["Skip"] == "TRUE":
        continue;

    print "Adding " + row["Filename"]

    nargs = Args()
    setattr(nargs, "libname", args.lbrFile)
    setattr(nargs, "boardsDirectory", args.boardsDirectory)
    setattr(nargs, "boardname", [row["Filename"]])
    setattr(nargs, "schematicFile", [re.sub("\.brd$", ".sch", row["Filename"])])
    setattr(nargs, "pinMap", [row["PinMap"]])
    setattr(nargs, "headers", row["Connectors"].split(" "))

    if row["CopyComponents"] != "":
        setattr(nargs, "toCopy", row["CopyComponents"].split(" "))
    else:
        setattr(nargs, "toCopy", [])

    packageName = re.sub('[ \.\-_/\(\)]+', "_", row["Name"].strip())
    setattr(nargs, "packagename", [packageName])
    setattr(nargs, "description", [template.format(shortname=row["Name"],
                                                   name=row["Name"],
                                                   url=row["DocURL"],
                                                   linktext=row["DocURL"],
                                                   cost=row["Price"])])
    setattr(nargs, "mirrorheader", row["MirroredConnector"] == "TRUE")
    setattr(nargs, "outlibname", None)
    setattr(nargs, "backwards", row["Backwards"] == "TRUE")
    setattr(nargs, "overwrite", True)

#    try:
    EagleBoardToDevice.ImportBOB(nargs)
 #   except:
  #      print "Failed to import " + row["Name"]

        

