#!/usr/bin/env python

import XMLVisitor
import argparse
import simpletransform
import math
import StringIO
from lxml import etree as ET
import XMLUtil
import sys
import copy
import re
import math

if __name__ == "__main__":


    parser = argparse.ArgumentParser(description="Tool to help import PADS decals in asc format.  It does lines and pads.  That's it.  You have to paste the result into an .lbr file by hand.")
    
    parser.add_argument("--in", required=True,  type=str, nargs=1, dest='inFile', help="SVG file")
    parser.add_argument("--units", required=True,  type=str, nargs=1, dest='units', help="SVG file")
    args = parser.parse_args()

    if args.units[0] == "mils":
        scaleFactor=1.0/1000.0*25.4

    def scale(x):
        return str(round(float(x)*scaleFactor, 4))

    infile = open(args.inFile[0], "rb");
    
    lines = infile.readlines();

    c = 0;

    while c < len(lines):
        lm = re.match("^(CLOSED|OPEN)\s+(\d)\s+(-?\d+\.?\d*)", lines[c])
        pm = re.match("^T(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(\S*)", lines[c])
        if lm is not None:
            #print str(c) + ": " + lines[c]
            c += 1;
            last = None;
            first = None;
            for i in range(0,int(lm.group(2))):
                #print i
                m = re.match("(-?\d+\.*\d*)\s+(-?\d+\.*\d*)", lines[c])
                c = c+1
                current = [m.group(1), m.group(2)];
                if last is not None:
                    print """<wire x1="{x1}" x2="{x2}" y1="{y1}" y2="{y2}" layer="21" width="{width}"/>""".format(x1=scale(last[0]), x2=scale(current[0]), y1=scale(last[1]), y2=scale(current[1]),width=scale(lm.group(3)));
                else:
                    first = current
                last = current
            if lm.group(1) == "CLOSED":
                print """<wire x1="{x1}" x2="{x2}" y1="{y1}" y2="{y2}" layer="21" width="{width}"/>""".format(x1=scale(last[0]), x2=scale(first[0]), y1=scale(last[1]), y2=scale(first[1]), width=scale(lm.group(3)));
        elif pm is not None:
            print """<pad x="{x}" y="{y}" name="{name}" drill="1.016" diameter="1.778"/>""".format(x=scale(pm.group(1)), y=scale(pm.group(2)),name=pm.group(5).upper());
            c= c+1
        else:
            c = c+1;
