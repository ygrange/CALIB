import CALIB

parser = argparse.ArgumentParser(description="Flag measurementset")
parser.add_argument("-i", "--msin", required=True)
parser.add_argument("-o", "--msout", required=True)
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
parser.add_argument("-x", "--donemark_input", required=True, help="Input donemark dependency.")

args = parser.parse_args()

donemark.check_donemark(args.donemark_input)

CALIB.ndppp_flagger(ms=args.msin,
                    flagged_ms=args.msout)
donemark.create_donemark(args.donemark)
