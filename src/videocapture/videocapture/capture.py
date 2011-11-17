# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Eideticker.
#
# The Initial Developer of the Original Code is
# Mozilla foundation
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   William Lachance <wlachance@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import Image
import os
from zipfile import ZipFile
import json
import tempfile

class CaptureDimensions(object):
    def __init__(self, bbox):
        self.bbox = bbox
        self.size = (self.bbox[2] - self.bbox[0], self.bbox[3] - self.bbox[1])

class CaptureDimensionsLgPortrait(CaptureDimensions):
    def __init__(self):
        CaptureDimensions.__init__(self, (613, 158, 1307, 1080))

class CaptureException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class Capture(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise CaptureException("Capture file '%s' does not exist!" %
                                   filename)
        self.archive = ZipFile(filename, 'r')
        self.metadata = json.loads(self.archive.open('metadata.json').read())
        if not self.metadata or not self.metadata['version']:
            raise CaptureException("Capture file '%s' does not appear to be an "
                                   "Eideticker capture file" % filename)

        self.dimensions = None
        if self.metadata['device'] == 'LG-P999':
            self.dimensions = CaptureDimensionsLgPortrait()
        self.frames = self._get_frames()

        # If we don't have any preset dimensions, infer them from the size of frames
        if not self.dimensions:
            self.dimensions = CaptureDimensions((0, 0, self.frames[0].size[0],
                                                 self.frames[0].size[1]))

    def write_video(self, outputfile):
        outputfile.write(self.archive.open('movie.avi').read())

    def _get_frames(self):
        import re
        def natural_sorted(l):
            """ Sort the given list in the way that humans expect.
            Based on: http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
            """
            convert = lambda text: int(text) if text.isdigit() else text
            alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
            return sorted(l, key=alphanum_key)

        imagefiles = filter(lambda s: s[0:7] == "images/" and len(s) > 8,
                            natural_sorted(self.archive.namelist()))
        frames = []
        for infile in imagefiles:
            f = tempfile.TemporaryFile(suffix=".png")
            f.write(self.archive.read(infile))
            f.seek(0)
            im = Image.open(f)
            if self.dimensions:
                im2 = im.transform(self.dimensions.size, Image.EXTENT, self.dimensions.bbox)
                frames.append(im2)
            else:
                im2 = im
                frames.append(im2)

        return frames

def _diffRGB(i1, i2, dimensions):
    for x in xrange(dimensions[0]):
        for y in xrange(dimensions[1]):
            if i1[(x,y)] != i2[(x,y)]:
                return True
    return False

def _diffCountRGB(i1, i2, dimensions):
    count = 0
    for x in xrange(dimensions[0]):
        for y in xrange(dimensions[1]):
            if i1[(x,y)] != i2[(x,y)]:
                count += 1
    return count

def get_unique_frames(capture, thresehold=0):
    prev = None
    uniques = 0
    processed = 0
    for frame in capture.frames[:-1]:
        #print "Processing frame %s" % processed
        if prev:
            diff = _diffCountRGB(prev.load(), frame.load(), capture.dimensions)
            if diff > thresehold:
                uniques += 1
        else:
            uniques+=1

        processed+=1
        prev = frame

    return (uniques, processed)
