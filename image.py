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
from helpers import create_logger, check_donemark

create_logger()

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-b", "--beamsize", type=lambda s: [int(item) for item in s.split(',')],
                    required=True, help="List of beam sizes in arcsec")
parser.add_argument("-f", "--fov", required=True, help="Field of view", type=float)
parser.add_argument("-o", "--outdir", required=True, help="Output directory")
parser.add_argument("-x", "--donemark_input", required=False, help="Input donemark dependency. (not required)")
args = parser.parse_args()

if args.donemark_input:
    check_donemark(args.donemark_input)

for beamsize in args.beamsize:
    CALIB.wsclean_image(ms=args.ms,
                        beamsize=beamsize,
                        field_of_view=args.fov,
                        outdir=args.outdir)
