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
from helpers import create_logger

create_logger()

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-o", "--output", required=True help="Output pathname of calibration solutions")
parser.add_argument("-s", "--skymodel", required=True, help="Path of skymodel to use")
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
args = parser.parse_args()

CALIB.ndppp_calibration(ms=args.ms, skymodel=args.skymodel, calsoln=args.output)

donemark.create_donemark(args.donemark)
