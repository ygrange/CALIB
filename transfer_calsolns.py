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
import donemark

parser = argparse.ArgumentParser(description="Transfer gain calibration solutions from calibrator to target.")
parser.add_argument("-t", "--target", required=True, help="Target MS")
parser.add_argument("-s", "--skymodel", required=True, help="Skymodel file")
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
parser.add_argument("-c", "--calsolns", required=True help="Pathname of calibration solutions")

args = parser.parse_args()

# apply solutions to the target field
CALIB.transfer_calibration_to_target(target_ms=args.target,
                                     skymodel=args.skymodel,
                                     calsolns=args.calsolns,
                                     filename_id=None)
donemark.create_donemark(args.donemark)
