#!/usr/bin/env python

# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#

from __future__ import with_statement
"""
This example requires:
- A set of science exposures
- A file containing the paths to each, as:
  exposure1
  exposure2
  ...
The first exposure's WCS and size are used for the coadd.
"""
import os
import sys

import lsst.pex.logging as pexLog
import lsst.pex.policy as pexPolicy
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.display.ds9 as ds9
import lsst.coadd.utils as coaddUtils
import lsst.coadd.chisquared as coaddChiSq

SaveDebugImages = False

BackgroundCellSize = 512

PolicyPackageName = "coadd_utils"
PolicyDictName = "WarpAndCoaddDictionary.paf"

if __name__ == "__main__":
    pexLog.Trace.setVerbosity('lsst.coadd', 5)
    helpStr = """Usage: warpAndCoadd.py coaddPath indata [policy]

where:
- coaddPath is the desired name or path of the output coadd
- indata is a file containing a list of:
    pathToExposure
  where:
  - pathToExposure is the path to an Exposure (without the final _img.fits)
  - the first exposure listed is taken to be the reference exposure,
    which determines the size and WCS of the coadd
  - empty lines and lines that start with # are ignored.
- policy: path to a policy file

The policy dictionary is: policy/%s
""" % (PolicyDictName,)
    if len(sys.argv) not in (3, 4):
        print helpStr
        sys.exit(0)
    
    outName = sys.argv[1]
    if os.path.exists(outName + "_img.fits"):
        print "Coadd file %s already exists" % (outName,)
        print helpStr
        sys.exit(1)
    weightOutName = outName + "_weight.fits"
    
    indata = sys.argv[2]
    
    if len(sys.argv) > 3:
        policyPath = sys.argv[3]
        policy = pexPolicy.Policy(policyPath)
    else:
        policy = pexPolicy.Policy()

    policyFile = pexPolicy.DefaultPolicyFile(PolicyPackageName, PolicyDictName, "policy")
    defPolicy = pexPolicy.Policy.createPolicy(policyFile, policyFile.getRepositoryPath(), True)
    policy.mergeDefaults(defPolicy.getDictionary())
    warpPolicy = policy.getPolicy("warpPolicy")
    coaddPolicy = policy.getPolicy("coaddPolicy")

    # process exposures
    ImageSuffix = "_img.fits"
    warp = None
    coadd = None
    with file(indata, "rU") as infile:
        for lineNum, line in enumerate(infile):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            filePath = line
            fileName = os.path.basename(filePath)
            if not os.path.isfile(filePath + ImageSuffix):
                print "Skipping exposure %s; image file %s not found" % (fileName, filePath + ImageSuffix,)
                continue
            
            print "Processing exposure %s" % (filePath,)
            exposure = afwImage.ExposureF(filePath)
            
            if not coadd:
                print "Create coadd"
                warp = coaddUtils.Warp(exposure.getMaskedImage().getDimensions(), exposure.getWcs(), warpPolicy)
                coadd = coaddChiSq.Coadd(exposure.getMaskedImage().getDimensions(), exposure.getWcs(), coaddPolicy)
            
            print "Warp exposure"
            warpedExposure = warp.warpExposure(exposure)
            if SaveDebugImages:
                warpedExposure.writeFits("warped%s" % (fileName,))
            
            print "Add warped exposure to coadd"
            warpedExposure = coadd.addExposure(warpedExposure)

    weightMap = coadd.getWeightMap()
    weightMap.writeFits(weightOutName)
    coaddExposure = coadd.getCoadd()
    coaddExposure.writeFits(outName)