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
import argparse
from helpers import create_logger, make_splitted_data

create_logger()

parser = argparse.ArgumentParser(description="Split observation to process and write to files.")
parser.add_argument("output", metavar = "OUT", help="List of output files.", nargs='+')
parser.add_argument('--config', '-c', help='Config file to read from', default='/tmp/Calibfiles.cfg')
args = parser.parse_args()

dat_split = make_splitted_data(args.config)

for outfile in args.output:
    try:
        cfg = dat_split.next()
    except StopIteration:
        raise StopIteration("More processing units than available files found")
    with open(outfile, "w") as wf:
        cfg.write(wf)
