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