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
try:
    from __main__ import __file__ as functionname
except ImportError: # Running in a python shell
    functionname = 'shell_run.py'
from os.path import basename
from CALIB import config_logger
import logging
import ast
from uuid import uuid4

def make_splitted_data(fname_in):
    cfg = ConfigParser.ConfigParser()
    cfg.read(fname_in)

    files_section = 'files'
    cfg_out = ConfigParser.ConfigParser()
    target_list = ast.literal_eval(cfg.get(files_section, 'targets'))
    calibrator_list = ast.literal_eval(cfg.get(files_section, 'calibrators'))
    if len(target_list) != len(calibrator_list):
        raise IndexError("List of targets and calibrators need to be of equal length.")
    cfg_out.add_section(files_section)
    for num, tgt in enumerate(target_list):
        cfg_out.set(files_section, 'target', tgt)
        cfg_out.set(files_section, 'calibrator', calibrator_list[num])
        yield cfg_out

class FileReturner(object):

    def __init__(self, input_files='/tmp/inputfiles.dat'):
        parser = ConfigParser.ConfigParser()
        parser.read(input_files)
        self.files = {"calibrator": parser.get('files', 'calibrator'),
                      "target": parser.get('files', 'target')}

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
    uuid = str(uuid4())
    fnam = basename(functionname.strip(".py"))
    logfile = fnam + datetime.now().isoformat() + "_" + uuid + ".log"
    config_logger(2, logfile)
    return uuid

if __name__ == "__main__":
    print "Don't run this script; import it."

