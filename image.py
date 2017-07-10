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

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-b", "--beamsize", type=lambda s: [int(item) for item in s.split(',')],
                    required=True, help="List of beam sizes in arcsec")
parser.add_argument("-f", "--fov", required=True, help="Field of view")
parser.add_argument("-r", "--fileroot", required=True, help="Output file root")
parser.add_argument("-x", "--donemark_input", required=True, help="Input donemark dependency.")
args = parser.parse_args()

donemark.check_donemark(args.donemark_input)

CALIB.wsclean_image(ms=args.ms,
                    beamsize=args.beamsize,
                    field_of_view=args.fov,
                    fileroot=args.fileroot)
