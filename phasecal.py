import CALIB
import argparse

parser = argparse.ArgumentParser(description="Phase calibration.")
parser.add_argument("-m", "--ms", required=True, help="MS to calibrate")
parser.add_argument("-c", "--correct-model-beam", action='store_true', help="Correct model beam (i.e. target obs)")
args = parser.parse_args()


CALIB.ndppp_phasecal(ms=args.ms,
               correctModelBeam=False,
               keep_parsets=self.keep_parsets,
               keep_skymodels=self.keep_skymodels,
               filename_id=filename_id_calibr)