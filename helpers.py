#!/usr/bin/env python
#
#     LOFAR pipeline demonstrator
#     Copyright (C) 2016  ASTRON (Netherlands Institute for Radio Astronomy)
#     P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import ConfigParser
from datetime import datetime
from __main__ import __file__ as functionname
from os.path import basename
from CALIB import config_logger



class FileReturner(object):

    def __init__(self, input_files='/tmp/inputfiles.dat'):
        parser = ConfigParser.ConfigParser()
        parser.read(input_files)
        self.files = {"calibrator": parser.get('files', 'calibrators'),
                      "target": parser.get('files', 'targets')}

    def get(self, filetype):
        return self.files[filetype]

def create_donemark(fname):
    file_content = "{functionname} done on {timestamp}\n"
    timestamp = datetime.now().isoformat()
    with open(fname, "w") as wrf:
        wrf.write(file_content.format(functionname=functionname,
                                      timestamp=timestamp))
def check_donemark(fname):
    logger = logging.getLogger(__name__)
    with open(fname) as fh:
        logtext = "Contents of DoneMark file {fname}: {content}"
        logger.debug(logtext.format(fname=fname, content=fh.read()))

def create_logger():
    fnam = basename(functionname)
    logfile = fnam + datetime.now().isoformat() + ".log"
    config_logger(2, logfile)

if __name__ == "__main__":
    print "Don't run this script; import it."

