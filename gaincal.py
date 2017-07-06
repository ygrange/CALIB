import CALIB
import argparse

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-o", "--output", required=True help="Output pathname of calibration solutions")
parser.add_argument("-s", "--skymodel", required=True, help="Path of skymodel to use")
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
args = parser.parse_args()

CALIB.ndppp_calibration(ms=args.ms, skymodel=args.skymodel, calsoln=args.output)

donemark.create_donemark(args.donemark)
