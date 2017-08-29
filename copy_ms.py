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
import CALIB
import argparse
from helpers import FileReturner, create_logger
from shutil import copytree 

uuid = create_logger()

parser = argparse.ArgumentParser(description="Copy measurementset")
parser.add_argument("-c", "--column", required=True, default="DATA", help="Data column")
parser.add_argument("-t", "--type", required=True, choices=['calibrator','target'],
                    help="Type of MS")
parser.add_argument("-o", "--msout", required=True, help="output MS")
parser.add_argument("-i", "--input", required=True, help="input config file")
parser.add_argument("-s", "--side-effect", required=True, help="filename of local copy of input MS to prevent issues with NFS.")
args = parser.parse_args()

msin = FileReturner(args.input).get(args.type)

copytree(msin, args.side_effect)

CALIB.ndppp_copy(msin=args.side_effect,
                indatacol=args.column,
                msout=args.msout,
                outdatacol=args.column,
                keep_parsets=True,
                filename_id=uuid)
