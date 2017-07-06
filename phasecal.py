import CALIB
import argparse

parser = argparse.ArgumentParser(description="Phase calibration.")
parser.add_argument("-m", "--ms", required=True, help="MS to calibrate")
parser.add_argument("-c", "--correct-model-beam", action='store_true', help="Correct model beam (i.e. target obs)")
parser.add_argument("-d", "--donemark", required=True, help="Donemark file")
parser.add_argument("-s", "--skymodel", required=True, help="Path of skymodel to use")
parser.add_argument("-x", "--donemark_input", required=True, help="Input donemark dependency.")
args = parser.parse_args()

donemark.check_donemark(args.donemark_input)

CALIB.ndppp_phasecal(ms=args.ms,
               correctModelBeam=args.correct_model_beam,
               skymodel=args.skymodel,
               keep_parsets=self.keep_parsets)

donemark.create_donemark(args.donemark)

