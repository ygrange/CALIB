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

parser = argparse.ArgumentParser(description="Generate sky model for calibrator or get from gsm for target.")
parser.add_argument("-m", "--ms", required=True, help="Measurement set with source name in meta data.")
parser.add_argument("-o", "--outfile", required=True, help="Filename of the output skymodel.")
parser.add_argument("-c", "--calib", action='store_true', help="Get built-in sky model of calibrator")
args = parser.parse_args()

if args.calib:
    CALIB.generate_calibrator_skymodel(ms=args.ms, filename=args.outfile)
else:
    CALIB.get_gsm_skymodel(ms=args.ms, filename=args.outfile)
