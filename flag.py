import CALIB

parser = argparse.ArgumentParser(description="Flag measurementset")
parser.add_argument("-i", "--msin", required=True)
parser.add_argument("-o", "--msout", required=True)

args = parser.parse_args()

CALIB.ndppp_flagger(ms=args.msin,
                    flagged_ms=args.msout)
