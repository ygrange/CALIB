import CALIB
import argparse

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-s", "--skymodel", action='store_true', help="Path of skymodel to use")
args = parser.parse_args()

CALIB.ndppp_calibration(ms=args.ms, skymodel=args.skymodel)
