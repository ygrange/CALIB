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
from filelist import FileReturner

parser = argparse.ArgumentParser(description="Copy measurementset")
parser.add_argument("-c", "--column", required=True, default="DATA", help="Data column")
parser.add_argument("-t", "--type", required=True, choices=['calibrator','target'],
                    help="Type of MS")
parser.add_argument("-o", "--msout", required=True, help="output MS")

args = parser.parse_args()

msin = FileReturner().get(args.type)

CALIB.ndppp_copy(msin=msin,
                indatacol=args.column,
                msout=args.msout,
                outdatacol=args.column)
