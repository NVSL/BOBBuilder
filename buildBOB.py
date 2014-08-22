#!/usr/bin/env python

import argparse
from lxml import etree as ET;
import sys
from EagleLibrary import *
from EagleBoard import *
from EagleCoordinateSystem import *
from EagleSymbol import *
from EagleDevice import *
from EagleDeviceSet import *
from EaglePackage import *
from EagleSchematic import *
from EagleLayers import *
import pipes
import os

def buildPackage(args, board, lib, pinMapping):
    # get the package
    try:
        newPackage = lib.newPackage(args.packagename[0]);
    except EagleError as e:
        print e
        if args.overwrite:
            lib.deletePackage(args.packagename[0]);
            newPackage = lib.newPackage(args.packagename[0]);
        else:
            print e
            print "Use --force to override.  Manual updates will be lost"
            sys.exit(1)

    # set up coordinate system        
    coord = EagleCoordinateSystem()

    # If the board is upside down, flip it.
    if args.backwards:
        coord.push(0,0,0,True);
    else:
        coord.push(0,0,0,False);

    # Copy board outline to silkscreen
    coord.push(0,0,0,False);
    for t in ["wire", "rectangle", "circle", "text", "hole"]:
        for l in board.getPlain().findall(t + "[@layer='20']"):
            p = copy.deepcopy(l)
            p.set("layer", "21");
            p.set("width", ".1");
            newPackage.append(coord.transformElement(p))
    coord.pop()

    def copyFlattenedElement(element, dst, mirror = False):
        e = copy.deepcopy(element)
#        print "flattening "
#        ET.dump(e)
        cpackage = board.getLibraries().find("library/packages/package[@name='" + e.get("package") + "']");
        coord.pushElement(e)

        for attribute in e.findall("attribute"):
            if attribute.get("name") in ["NAME", "VALUE"]:
                e.remove(attribute)

        if mirror:
#            print "mirroring..."
#            ET.dump(e)
            if e.get("rot") is None:
                e.set("rot","M0")
            elif e.get("rot")[0] == "R":
                e.set("rot","M"+e.get("rot"))
        

        for piece in cpackage: 
            p = copy.deepcopy(piece)
            if p.tag == "pad":
                longName = e.get("name") + "." + p.get("name")
#                print "pad " + p.get("name") + " to " + longName
                if longName in pinMapping:
                    p.set("name", pinMapping[longName])
                else:
                    p.set("name", longName)
            if p.get("layer") not in ["25", "26", "27", "28"]: # cut name and value tags
                newPackage.append(coord.transformElement(p))
        coord.pop();

    # copy connectors
#    print "here"
    if args.headers:
        for header in args.headers:
            element = board.getElements().find("./element[@name='" + header + "']")
            if element is None:
                raise EagleError("Couldn't find header '" + header + "'")
            copyFlattenedElement(element, newPackage, args.mirrorheader)

    # copy other components (E.g., mounting holes that are packages)
    if args.toCopy:
        for part in args.toCopy:
            element = board.getElements().find("./element[@name='" + part + "']")
            if element is None:
                raise EagleError("Couldn't find component '" + part + "'")
            copyFlattenedElement(element, newPackage, False)

    # copy the silkscreen and documentation from all the other elements
    for element in board.getElements().findall("element"):
        coord.pushElement(element);
        package = board.getLibraries().find("library/packages/package[@name='" + element.get("package") + "']");
        for t in ["wire", "rectangle", "circle", "text"]:
            for packagePiece in package.findall(t):
                if int(packagePiece.get("layer")) in [51, 52, 21, 22, 150]:
                    if coord.isElementOnTop(packagePiece):
                        newPackage.append(coord.transformElement(packagePiece))
        coord.pop()

    # Copy over the other the lines etc. that aren't attached to any part
    for t in ["wire", "rectangle", "circle", "text", "hole"]:
        for m in board.getPlain().findall(t):
            if coord.isElementOnTop(m) or t is "hole" or m.get("layer") == "150":
                ET.dump(m)
                newPackage.append(coord.transformElement(m))
                if t is "hole":
                    newPackage.append(ET.SubElement(newPackage, "circle", {"layer":"150",
                                                                           "x":m.get("x"),
                                                                           "y":m.get("y"),
                                                                           "radius":str(float(m.get("drill"))/2)}))
                                                                           
    return EaglePackage(newPackage)

def buildSymbol(args, board, lib, pinMapping):

    try:
        newSymbol = lib.newSymbol(args.packagename[0]);
    except EagleError as e:
        if args.overwrite:
            lib.deleteSymbol(args.packagename[0]);
            newSymbol = lib.newSymbol(args.packagename[0]);
        else:
            raise e

    pinList = []
    if args.headers:
        for header in args.headers:
            h = board.getElements().find("./element[@name='" + header + "']")
            package = board.getLibraries().find("library/packages/package[@name='" + h.get("package") + "']");
            for pad in package.findall("pad"): 
                longName = header + "." + pad.get("name")
                if longName in pinMapping:
                    pinList = pinList + [pinMapping[longName]]
    
    height = len(pinList) + 1
    width = 10

    s = EagleSymbol(newSymbol,2.54);
    s.AddArt("wire", 0, 0, 0, height)
    s.AddArt("wire", 0, height, width, height)
    s.AddArt("wire", width, height, width, 0)
    s.AddArt("wire", width, 0, 0, 0,)
    
    c = 0;
    for i in pinList:
        s.AddPin(i, -2, height - (1 + c))
        c = c + 1

    return s

def buildDeviceSet(args, symbol, package, board, lib, pinMapping):
    try:
        newDeviceSet = lib.newDeviceSet(args.packagename[0]);
    except EagleError as e:
        if args.overwrite:
            lib.deleteDeviceSet(args.packagename[0]);
            newDeviceSet = lib.newDeviceSet(args.packagename[0]);
        else:
            raise e
    
    ds = EagleDeviceSet(newDeviceSet);
    ds.setGate(symbol.getName())
    newDevice = ds.newDevice("-BOB")
    d = EagleDevice(newDevice)
    d.setPackage(package.getName())
    
    for i in symbol.getPinList():
        d.Connect(i.get("name"),i.get("name"))
    
    return ds

def ImportBOB(args):
    # open library and board

    schematic = EagleSchematic(args.boardsDirectory[0] + "/" + args.schematicFile[0])
    board = EagleBoard(args.boardsDirectory[0] + "/" + args.boardname[0])
    print args.outlibname[0]
    lib = EagleLibrary(args.outlibname[0])

    def uniquify(m):
        count = {}

        for i in m:
            if m[i] not in count:
                count[m[i]] = 1
            else:
                count[m[i]] = count[m[i]] + 1

        for i in m:
            if count[m[i]] is 1:
                pass
            else:
                count[m[i]] = count[m[i]] - 1
                m[i] = m[i] + str(count[m[i]])

        return m

    def remapPins(m, r):
        for i in m:
            if m[i] in r:
                m[i] = r[m[i]]
        return m

    pinMapping = schematic.findPinsOnNets(args.headers)
    if args.pinMap[0] != "":
        pinMapping = remapPins(pinMapping, eval(args.pinMap[0]))
    pinMapping = uniquify(pinMapping)
    
    package = buildPackage(args, board, lib, pinMapping)
    symbol = buildSymbol(args, board, lib, pinMapping)
    deviceSet = buildDeviceSet(args, symbol, package, board, lib, pinMapping)

    if args.description:
        deviceSet.setDescription(args.description[0])

# determine where to put the output.

    try:
        EagleLayers(lib.getLayers()).checkForMissingLayers(lib.getRoot())
    except EagleError as e:
        print str(e)
        print "contiuning..."

    f = args.outlibname[0]
# write it out.  Eagle has trouble reading xml with no newlines.  Run it through xmllint to make it pretty.
    t = pipes.Template()
    t.append("xmllint --format $IN", "f-")
    lib.write(t.open(f, 'w'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool for auto-generating packages for breakout boards")

    parser.add_argument("--library", required=False,  type=str, nargs=1, dest='outlibname', default=None, help="target library file")
    parser.add_argument("--gcom", required=True,  type=str, nargs=1, dest='gcom', help="Component description file")
    parser.add_argument("--force", action="store_true", help="Replace current device, schematic, and package")

    parser.add_argument("--board", required=False,  type=str, nargs=1, dest='boardname', help="board to import relative to BoardsDirecotry")
    parser.add_argument("--headers", required=False, type=str, nargs='+', dest='headers', help="header part identifier")
    parser.add_argument("--copy", type=str, nargs='+', dest='toCopy', help="Components to be replicated")
    parser.add_argument("--name", required=False, type=str, nargs=1, dest='packagename', help="Name for the new package")
    parser.add_argument("--mirrorheader", action='store_true', help="Force the header to be mirrored.")
    parser.add_argument("--backwards", action='store_true', help="Mirror the board.")
    parser.add_argument("--overwrite", action='store_true', help="Overwrite existing package")
    parser.add_argument("--outlibrary", type=str, nargs=1, default=None, dest='outlibname', help="output library file")
    parser.add_argument("--description", type=str, nargs=1, dest='description', help="BOB description") 
    parser.add_argument("--boards", required=False, type=str, nargs=1, dest='boardsDirectory', help="Directory with the brd files")
    parser.add_argument("-sch", required=False,  type=str, nargs=1, dest='schematicFile', help="schematic file")
    parser.add_argument("--pinmap", required=False,  type=str, nargs=1, dest='pinMap', help="Schematic pin remapping")

    args = parser.parse_args()

    gcom = ET.parse(args.gcom[0])
    bspec = gcom.getroot().findall("bobspec");
    for bobspec in bspec:
        args.boardname = [bobspec.find("brdfile").text]
        if bobspec.find("brdfile").get("upside-down") is None or bobspec.find("brdfile").get("upside-down").upper() == "FALSE":
            args.backwards = False
        else:
            args.backwards = True

        args.packagename = [bobspec.get("device-name")]
        args.description = [gcom.getroot().find("name").text]
        args.schematicFile = [bobspec.find("schfile").text]
        args.headers = [ j.get("name") for j in bobspec.findall("connector")]
        if args.gcom[0][0] != "/" and args.gcom[0][0] != ".":
            args.gcom[0] = "./"+ args.gcom[0]
        args.boardsDirectory = ["/".join(args.gcom[0].split("/")[0:-1])]
        print args.boardsDirectory
        pinmap = {}
        for m in bobspec.findall("pinmap"):
            pinmap[m.get("schematic-pin")] = m.get("package-pin")
        args.pinMap = [repr(pinmap)]
        print args.outlibname
        if args.outlibname is None:
            args.outlibname = [os.getenv("EAGLE_LIBS") + "/" + "BOBs.lbr"]
         
        args.overwrite = args.force
        #print args.outlibname

        ImportBOB(args)    
    
