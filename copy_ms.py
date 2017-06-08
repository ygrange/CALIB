import CALIB
import argparse

parser = argparse.ArgumentParser(description="Copy measurementset")
parser.add_argument("-c", "--column", required=True, default="DATA", help="Data column")
parser.add_argument("-i", "--msin", required=True, help="input MS")
parser.add_argument("-o", "--msout", required=True, help="output MS")

args = parser.parse_args()

CALIB.ndppp_copy(msin=args.msin,
                indatacol=args.column,
                msout=args.msout,
                outdatacol=args.column)
