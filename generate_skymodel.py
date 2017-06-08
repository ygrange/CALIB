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