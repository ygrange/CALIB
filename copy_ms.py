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
