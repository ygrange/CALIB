import CALIB
import argparse

parser = argparse.ArgumentParser(description="Calibrate gains.")
parser.add_argument("-m", "--ms", required=True, help="Input measurement set")
parser.add_argument("-b", "--beamsize", type=lambda s: [int(item) for item in s.split(',')],
                    required=True, help="List of beam sizes in arcsec")
parser.add_argument("-f", "--fov", required=True, help="Field of view")
parser.add_argument("-r", "--fileroot", required=True, help="Output file root")
args = parser.parse_args()




CALIB.wsclean_image(ms = args.ms,
                    beamsize = args.beamsize,
                    field_of_view = args.fov,
                    fileroot = args.fileroot)