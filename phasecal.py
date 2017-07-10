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

parser = argparse.ArgumentParser(description="Phase calibration.")
parser.add_argument("-m", "--ms", required=True, help="MS to calibrate")
parser.add_argument("-c", "--correct-model-beam", action='store_true', help="Correct model beam (i.e. target obs)")
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
parser.add_argument("-s", "--skymodel", required=True, help="Path of skymodel to use")
parser.add_argument("-x", "--donemark_input", required=True, help="Input donemark dependency.")
args = parser.parse_args()

donemark.check_donemark(args.donemark_input)

CALIB.ndppp_phasecal(ms=args.ms,
               correctModelBeam=args.correct_model_beam,
               skymodel=args.skymodel,
               keep_parsets=self.keep_parsets)

donemark.create_donemark(args.donemark)

