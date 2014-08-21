#!/usr/bin/env python

import argparse
import sys
import csv
import re
import subprocess
import StringIO

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

parser = argparse.ArgumentParser(description="Automatically download updated versions of boards")
parser.add_argument("-db", required=True, type=str, nargs=1, dest='dbFile', help="Break out board database file.")
parser.add_argument("--boards", required=True, type=str, nargs=1, dest='boardsDirectory', help="Where to keep the board sources.")
args = parser.parse_args()

dbf = open(args.dbFile[0], "rb")
db = csv.DictReader(dbf)

header = GetCSVHeader(args.dbFile[0])
output = StringIO.StringIO()
out = csv.DictWriter(output, header)
t = {}
for i in header:
    t[i] = i
out.writerow(t)

class Args:
    pass

updateLog = open("update.log", "w")

for row in db:
    if row["DownloadType"] == "svn":
        print "Updating (SVN) " + row["Name"] + " " + row["DownloadURL"]
        cmd = "cd " + args.boardsDirectory[0] + "; svn co \""+ row["DownloadURL"] + "\""
        subprocess.call(cmd, shell=True, stderr=updateLog, stdout=updateLog);
        subDirectory=row["DownloadURL"].split("/")[-1] + "/trunk"
        proxyName = row["DownloadURL"].split("/")[-1]
    elif row["DownloadType"] == "zip":
        print "Updating (ZIP) " + row["Name"] + " " + row["DownloadURL"]
        zipName = re.sub('[ \.\-_/\(\)]+', "_", row["Name"]).strip("_")
        cmd = "cd " + args.boardsDirectory[0] + "; rm -rf " + zipName + "; curl -o " + zipName + ".zip " + row["DownloadURL"] + "; mkdir " + zipName +  " ; unzip -d " + zipName + " " + zipName + ".zip"
#        print cmd
        subprocess.call(cmd, shell=True, stderr=updateLog, stdout=updateLog);
        subDirectory = zipName

    if row["Name"] == "":
        row["Name"] = proxyName

#    brds = StringIO.StringIO()
  #  print "Likely brd paths: ",
   # subprocess.call("cd " + args.boardsDirectory[0] + "; find " + subDirectory + " -name '*.brd'", shell=True)
    
 #   if row["Filename"] == "":
 #       row["Filename"] = brds.getvalue().split("\n")[0]

    out.writerow(row)

dbf.close()
open(args.dbFile[0], "wb").write(output.getvalue())
