import CALIB
import argparse

parser = argparse.ArgumentParser(description="Transfer gain calibration solutions from calibrator to target.")
parser.add_argument("-c", "--calib", required=True, help="Calibration MS")
parser.add_argument("-t", "--target", required=True, help="Target MS")
args = parser.parse_args()

# apply solutions to the target field
CALIB.transfer_calibration_to_target(calibrator_ms=args.calib,
                                     target_ms=args.target)
