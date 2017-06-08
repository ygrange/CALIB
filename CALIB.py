#!/usr/bin/env python
#
#     LOFAR pipeline demonstrator
#     Copyright (C) 2016  ASTRON (Netherlands Institute for Radio Astronomy)
#     P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program. If not, see <http://www.gnu.org/licenses/>.
#

"""
This script is a pipeline to GAIN calibrate a MS and transfer solutions.
RM corrections, flagging, and imaging is also done.
Inputs needed:
- the sub-bands range (wrt the target)
- (optional) the IONEX files for RM corrections
- (optional) if smoothing amp sol
- list of beam sizes

Originally written by Marco Iacobelli @ ASTRON, NL.
Rewritten by Yan Grange and Matthias Petschow in 04/2016 @ ASTRON, NL.
"""

# general TODO:
# - update all doc strings
# - do not create so many copys of the MS: maybe first copy + creation
#   of CORRECTED_DATA column; then all steps performed on CORRECTED_DATA
#   + maybe rename of file *_2.MS -> _3.MS to indicate steps already done
# - do not store parsets, skymodel etc just in directory where executed
#   as temporary files now written in PWD, not in output directory
# - use more named parameters for clarity
# - radius=5, fluxthresh=1, fov, int or floating point? as parameters?
# - introduce parameter "--use-multiscale" or so
# - include RM correction again
# - MS overwrite everywhere
# - how to deal with RMParmDB? Remove it at the end?



import os
import sys
import shutil
import argparse
import warnings
import datetime
import math
import subprocess as sp
import scipy.constants as sc
import scipy.signal
import numpy as np
import warnings
import glob
import logging
import time

try:
    from pyrap import tables as pt
except ImportError:
    raise ImportError("Could not import pyrap. Check if you initialised python-casacore.")
try:
    from lofar.parameterset import parameterset as parset
except ImportError:
    raise ImportError("Could not import from lofar. Check if you initialised lofar.")

logging.getLogger(__name__).addHandler(logging.NullHandler())

with warnings.catch_warnings():
    warnings.simplefilter("ignore") # Suppressing warnings that arise when importing
                                    # both parset and parmdb from lofar
    from lofar import parmdb

# auxiliary functions


def get_logfile(postfix, fileid):
    """
    Function to convert the command line argument -l to a logfile name.
    :param postfix: False means not provided
                    None means provided but no postfix
                    Anything else means provided with postfix.
    :returns: A string with the file name, or None when no file needs to be written.
    """

    return_filename = "CALIB-run-{fileid}{postfix}.log"
    postfix_string = ''

    if not postfix and postfix is not None: # then it's False
        return None  # this is a bit confusing...

    if postfix:
        postfix_string = "." + postfix

    return return_filename.format(fileid=fileid,
                                  postfix=postfix_string)


def config_logger(verbosity_level, logfile):
    """Helperfunction to configure the root logger. 
    :param verbosity_level: verbosity level input. This translates to:
             verbosity level, logging level
                           0, WARNING
                           1, INFO
                           2, DEBUG
    :param logfile: File used for logging output. If None, no logging to file.
    """
    # TODO: Maybe the output format should depend on verbosity level too. That should be done here.

    logger = logging.getLogger()
    loglevels = [logging.WARNING, # 0
                 logging.INFO,    # 1
                 logging.DEBUG]   # 2

    # very simple default formatter. We could add some complexity by using a custom
    # formatter that prints the function name for debug calls for example
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(loglevels[verbosity_level])
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def fileid():
    """
    Helper function to return a string attached to all written files
    """
    logger = logging.getLogger(__name__)
    return datetime.datetime.now().strftime("%y%m%d%H%M")

# subprocess print live output wrapper
def live_output(cmd):
    """
    Helper function to run the command specified as cmd via subprocess.Popen and provide
    a near-live output. It will send a line to the CALIB logger for each line that is printed.
    If there is a line that takes time to print (e.g. a progress bar), the script will send a line
    to the logger whenever the line has changed and the waiting time was more than a minute.
    """
    logger = logging.getLogger(__name__)
    process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    outstr = ""
    oldoutstr=""
    timer = 0
    wait_time = 60
    while True:
        output = process.stdout.read(1)
        if output == "\n":
            logger.debug(outstr)
            outstr = ""
            timer = time.time()
        elif output == '' and process.poll() is not None:
            if len(outstr) > 1:
                logger.debug(outstr)
            break
        elif output:
            if output != '':
                outstr += output
                if (time.time() - timer) > wait_time:
                    if outstr != oldoutstr:
                        logger.debug(outstr)
                        oldoutstr = outstr
                        timer = time.time()

    rc = process.poll()
    if rc != 0:
        raise sp.CalledProcessError(rc, cmd)

# run command wrapper
def run_command(cmd):
    """
    Wrapper to running commands. Execute only if not "--no-exec" specified.
    :param cmd: command to run
    """
    logger = logging.getLogger(__name__)
    logger.info("EXECUTE: {cmd}".format(cmd=cmd))
    cmd = "time -p " + cmd
    try:
        live_output(cmd.split())
    except sp.CalledProcessError as cpe:
        # if cmd returns non-zero exit status
        logger.error("ERROR: {cmd} raised: {cpe}".format(cmd=cmd, cpe=cpe), exc_info=True)
        raise

# get the imaging parameters
def get_imaging_parameters(ms, angular_resolution, field_of_view):
    """Find the imaging parameters for the achievable angular resolutions.
    :param ms: ...
    :param angular_resolution: ...
    :param field_of_view: ...
    :returns: ...
    """
    logger = logging.getLogger(__name__)
    # open ms and extract frequency, then convert to wavelength [m]
    try:
        sw = pt.table(ms + '/SPECTRAL_WINDOW')
    except RuntimeError:
        raise RuntimeError("{} does not exist".format(ms))

    # Convert from frequency to wavelength [m]
    obs_freq = sw.col('REF_FREQUENCY')[0]
    lambda_obs = sc.speed_of_light / obs_freq

    # Get the minimum baseline length "1.05 * lambda / angular_resulution"
    # Note: arc second in radians (=(pi/180) * 1./(60*60))
    dist = lambda_obs / (sc.arcsec*float(angular_resolution))
    dist_eff = 1.05 * dist    # MP: magic number

    # Check if this not flagged baseline is in the measurement set
    try:
        tab0 = pt.table(ms, readonly=False, ack=True)
    except RuntimeError:
        raise RuntimeError("{} does not exist".format(ms))

    pos0 = tab0.getcol('UVW')
    flag0 = tab0.getcol('FLAG_ROW')

    indexes = np.where(flag0[:] == 0)[0]
    uvdist = np.hypot(pos0[indexes,0], pos0[indexes,1])

    if np.max(uvdist) > dist_eff:
        cell_size = float(angular_resolution)/6.0  # MP: magic number
        n_pixels = int(3600. * (field_of_view/cell_size))
        uvmax = dist_eff/1000.   # in km
        uvmax_in_lambda = 1000.*uvmax/lambda_obs
        uvmax_in_meters = 1000.*uvmax

        logger.info('Resolution {} arcsec achievable!'.format(float(angular_resolution)))
        logger.info("cell_size = {}".format(cell_size))
        logger.info("n_pixels = {}".format(n_pixels))
        logger.info("uvmax = {}".format(uvmax))
        logger.info("uvmax_in_meters = {}".format(uvmax_in_meters))

    else:
       # For sure the question whether to use warnings.warn or logging.warning will come up. Found this clear answer:
       # warnings.warn() in library code if the issue is avoidable and the client application should be modified to eliminate the warning
       # logging.warning() if there is nothing the client application can do about the situation, but the event should still be noted
       # (https://stackoverflow.com/questions/9595009/python-warnings-warn-vs-logging-warning)

        warnings.warn("'Resolution {} arcsec not achievable.".format(float(angular_resolution)),
                      RuntimeWarning)

    sw.close()
    tab0.close()

    return cell_size, n_pixels, uvmax_in_meters, uvmax_in_lambda


def parse_subbands_argument(str_list):
    """
    Convert list of strings such as "['11','14-17','20']" to list of integers
    such as "[11,14,15,16,17,20]"
    :param ms: list of strings of target subbands to process
    :returns: list of integers of target subbands to process
    """
    int_list = list()
    for item in str_list:
        try:
            int_list.append(int(item))
        except ValueError:
            item_split = item.split('-')
            try:
                int_list.extend(range(int(item_split[0]),int(item_split[1])+1))
            except:
                raise ValueError("Invalid subband list.")
    return int_list



def parse_stages_argument(inlist):
    """
    Convert list of strings to a dictonary with True/False for each of the for stages
    """
    stages = {'copy' : False, 'gaincal' : False, 'phasecal' : False, 'image' : False}
    for stage in inlist:
        stages[stage.lower()] = True
    return stages



def get_source_name(ms):
    """
    Get the name from the observed source from a measurement set
    :param ms: Measuement Set (full path)
    :type ms: str or unicode
    :returns: name of source
    :rtype: str or unicode
    """
    try:
        tabobs = pt.table(ms + '/OBSERVATION')
    except RuntimeError:
        raise RuntimeError("{} does not exist".format(ms))
    sourcename = tabobs.getcell('LOFAR_TARGET',0)[0].strip()
    tabobs.close()

    return sourcename


class CALIB(object):
    """
    This is essentially an object that holds all confoguration information and the run script. Right now
    configuration has to be done using argparse. 
    """
    #TODO: Add a way to configure CALIB from pure python. I (YG) have a jupyter notebook with an example implementation.
    def __init__(self, arguments=None):
        """
        Initialise the CALIB script.
        :param arguments: List of argumentsin the format of sys.argv. If none, sys.argv is parsed.
        """
        self.logger = logging.getLogger(__name__)
        self.filename_id = fileid()
        self._create_parser()
        self._parse_command_line_pars(arguments)
        try:
            self._generate_dirlist()
        except ValueError:
            self.logger.error("Error generating dir list", exc_info=True)
        raise


    def _create_parser(self):
        """
        Create the parser object. This will be use to parse either command-line parameters or manual settings.
        :return: parser object
        """
        parser = argparse.ArgumentParser(
            description="Pipeline to gain calibrate a Measurement Set (MS), " + \
                        "transfer solutions, RM correct, flag, and image. " + \
                        "Requires the LOFAR software suite, WSClean, RMextract, gsm_wrapper to be available. " + \
                        "Assumes measurement set naming according to the following convention: " + \
                        "target MSs are named *SB[ddd]*[postfix], where ddd are 3 digit subband indices, " + \
                        "and calibrator Ms *SB[ddd+244]*[postfix] have implicit indices with 244 added.")
        parser.add_argument('-d', '--indir',
                            help='Input directory (default: .)',
                            required=False, default=".")
        parser.add_argument('-o', '--outdir',
                            help='Output directory (default: same as input directory)',
                            required=False)
        parser.add_argument('-p', '--postfix',
                            help='Ending of processed MS file names (default: .MS)',
                            required=False, default=".MS")
        parser.add_argument('-SB', '--subbands',
                            type=lambda s: [str(item) for item in s.split(',')],
                            help='List of subbands ',
                            required=True)
        parser.add_argument('--stages',
                            type=lambda s: [str(item) for item in s.split(',')],
                            help='List of stages to perform (default "copy,gaincal,phasecal,image"). ',
                            default="copy,gaincal,phasecal,image",
                            required=False)
        parser.add_argument('--correct-rm', action='store_true',
                            help='Apply RM correction (default: false)',
                            required=False)
        parser.add_argument('--smooth-amplitudes', action='store_true',
                            help='Smoothing amplitudes of calibration results (default: false)',
                            required=False)
        parser.add_argument('-B', '--beamsizes',
                            type=lambda s: [int(item) for item in s.split(',')],
                            help='List of beam sizes in arcsec (e.g. "80,60,40,28,24,10") ',
                            required=True)
        parser.add_argument("-v", "--verbosity", type=int,
                            choices=[0, 1, 2],
                            help="Output verbosity level",
                            default=1,
                            required=False)
        parser.add_argument('-l', '--logfile',
                            type=str,
                            help='In addition to logging to screen, the logging will also be written to'
                                 'a file. The log file will be written in the current directory.'
                                 'The filename follows the format CALIB-run-{ymdHM}[.{postfix}].log'
                                 'where ymdHM represents the date in ISO format. You can optionally'
                                 'add a postfix to the file naming by adding it as an argument to the log'
                                 'file option (i.e. -l/--logfile postfix).',
                            nargs='?',
                            default=False,
                            required=False)
        parser.add_argument("--target-obsid",
                            type=str,
                            help='Obsid of the target observation when target and calibrator are two different'
                                 'observations. Using this requires --calibr_obsid too.',
                            required=False)
        parser.add_argument("--calibr-obsid",
                            type=str,
                            help='Obsid of the calibrator observation when target and calibrator are two different'
                                 'observations. Using this requires --target_obsid too.',
                            required=False)
        parser.add_argument('--keep-parsets', action='store_true',
                            help='Keep parsets, i.e. do not delete them (default: false)',
                            required=False)
        parser.add_argument('--keep-skymodels', action='store_true',
                            help='Keep skymodels, i.e. do not delete them (default: false)',
                            required=False)
        parser.add_argument('--keep-solutions', action='store_true',
                            help='Keep gaincal solutions, i.e. do not delete them (default: false)',
                            required=False)
        parser.add_argument("--interleaved", action='store_true',
                            help='Interleaved observation. Placeholder keyword. Will generate an error if used.')
        self.parser = parser

    def _parse_command_line_pars(self, arguments=None):
        """
        Parse the input. By default it will parse the command line arguments given
        to the script (sys.argv). If you want to set your own values, provide thiose
        as a list resembling sys.argv (i.e. split by space).
        :return: set global variables for object
        """

        args                = self.parser.parse_args()

        self.verbosity = args.verbosity
        self.logfile = get_logfile(args.logfile, self.filename_id)
        config_logger(self.verbosity, self.logfile)

        self.indir          = args.indir
        self.outdir         = args.outdir if args.outdir else args.indir
        self.postfix        = args.postfix
        try:
            self.subbands       = parse_subbands_argument(args.subbands)
        except ValueError:
            logger.error("Error parsing subbands argument: {sbarg}.".format(sbarg=args.subbands))

        self.stages         = parse_stages_argument(args.stages)
        self.correct_rm     = args.correct_rm
        self.smooth_amps    = args.smooth_amplitudes
        self.beamsizes      = args.beamsizes
        self.keep_parsets   = args.keep_parsets
        self.keep_skymodels = args.keep_skymodels
        self.keep_solutions = args.keep_solutions
        try:
            self.target_obsid   = int(args.target_obsid.lstrip("L"))  # Want to accept both L12345 as 12345 as input.
            self.calibr_obsid    = int(args.calibr_obsid.lstrip("L"))
        except AttributeError:
            pass      # this means that either of those is not set, which can happen if doing calibration on source in field.
        self.separate_calibr = bool(args.target_obsid)   # They should either both exist or be None so check pnly one.
        self.interleaved    = args.interleaved

        if bool(args.target_obsid) != bool(args.calibr_obsid):  # This is essentially not (target_obsid xor calibr_obsid).
            parser.error("--target_obsid and --calibr_obsid should be provided together!")

        if self.interleaved:
            parser.error("Handling of interleaved observations has not been implemented yet!")

        self.print_settings()


    def _generate_dirlist(self):
        # list of full path MS names in directory
        self.dirlist = [os.path.join(self.indir,name) for name in os.listdir(self.indir)
                          if os.path.isdir(os.path.join(self.indir,name)) and
                          name.endswith(self.postfix)]

        self.logger.info(" ")
        self.logger.info("############### START PROCESSING ###############")
        self.logger.info(" ")
        self.logger.info('Found {} MS ending with {}'.format(len(self.dirlist), self.postfix))
        if len(self.dirlist) == 0:
            raise ValueError("No valid MS found.")

    def print_settings(self):
        self.logger.debug("INPUT PARAMETERS:")
        self.logger.debug("{0:30}{1:<40}".format("Input directory:", self.indir))
        self.logger.debug("{0:30}{1:<40}".format("Output directory:", self.outdir))
        self.logger.debug("{0:30}{1:<40}".format("MS postfix:", self.postfix))
        self.logger.debug("{0:30}{1:<40}".format("Subbands:", self.subbands))
        self.logger.debug("{0:30}{1:<40}".format("RM correction:", self.correct_rm))
        self.logger.debug("{0:30}{1:<40}".format("Smoothing amplitudes:", self.smooth_amps))
        self.logger.debug("{0:30}{1:<40}".format("Beam sizes:", self.beamsizes))
        if self.separate_calibr:
            self.logger.info("Using separate calibrator observation")
            self.logger.debug("{0:30}{1:<40}".format("Target ObsID:", self.target_obsid))
            self.logger.debug("{0:30}{1:<40}".format("Calibrator ObsID:", self.calibr_obsid))
        self.logger.debug(" ")

    def raw_print_all_set_variables(self):
        """
        Print all the variables set in this class. This can be used for debugging purposes.
        """
        for key, val in self.__dict__.items():
            self.logger.debug(key, val)

    def run(self):
        """
        Run the demo pipeline: ... MORE DESCRIPTION ...
        Uses the following parameters from the class:
        :param dirlist: list of Measurement Sets to process (full path)
        :type dirlist: str or unicode
        :param subbands: integer list of subbands
        :type subbands: list
        :param outdir: Output directory
        :type subbands: str or unicode
        :param filename_id: string used in filenaming of current processing
        :type filename_id: str or unicode        :param filename_id: string used in filenaming of current processing
        :type filename_id: str or unicode
        :param separate_calibr: Flag to set whether calibrator is subarray pointing (False)
                               or different observation (True)
        :type separate_calibr: bool
        :param target_obsid: obsid of target observation (ignored if separate_calibr is False)
        :type target_obsid: int
        :param calibr_obsid: obsid of calibrator observation (ignored if separate_calibr is False)
        :type calibr_obsid: int

        """

        # TODO: arguments: list pairs of MSs as arguments, for target and matching calibr
        # Assumption is that both Target and Calibrator data are in the same directory
        # removes naming conventions, ...

        for sb_target in self.subbands:
            # TODO: write in description about this assumed data naming scheme
            # TODO: and how it depends on flags set
            if self.separate_calibr:
                sb_calibr = sb_target
            else:
                sb_calibr = sb_target + 244

            filename_id_target = "SB{:03d}_{}".format(sb_target, self.filename_id)
            filename_id_calibr = "SB{:03d}_{}".format(sb_calibr, self.filename_id)

            # Create list containing all target/calibrator MS
            input_target_ms = [s for s in self.dirlist if "SB{:03d}".format(sb_target) in s]
            if self.separate_calibr:
                input_target_ms = [s for s in input_target_ms if "L{}".format(self.target_obsid) in s]
            if len(input_target_ms) == 0:
                warnings.warn("Failing to find data for subband {}".format(sb_target),
                              RuntimeWarning)
                continue
            if len(input_target_ms) > 1:
                warnings.warn("Found too many data files for {}".format(sb_target),
                              RuntimeWarning)
                continue
            input_calibr_ms = [s for s in self.dirlist if "SB{:03d}".format(sb_calibr) in s]
            if self.separate_calibr:
                input_calibr_ms = [s for s in input_calibr_ms if "L{}".format(self.calibr_obsid) in s]

            if len(input_calibr_ms) == 0:
                warnings.warn("Failing to find data for subband {}".format(sb_calibr),
                              RuntimeWarning)
                continue
            if len(input_calibr_ms) > 1:
                warnings.warn("Found too many data files for {}".format(sb_calibr),
                              RuntimeWarning)
                continue

            # Store names of MSs in variables
            input_target_ms = input_target_ms[0]
            input_calibr_ms = input_calibr_ms[0]
            dir_target_ms = os.path.dirname(input_target_ms)
            dir_calibr_ms = os.path.dirname(input_calibr_ms)

            self.logger.info("Working on parsets {} and {}".format(input_target_ms,
                                                                   input_calibr_ms))

            self.logger.info(" ")
            self.logger.info("############### PIPELINE STAGE 0 ###############")

            stage = 0
            if self.stages['copy']:

                # Make copy of target and calibrator MS
                filename_target = "target_{}.MS.{}".format(filename_id_target, stage)
                filename_calibr = "calibr_{}.MS.{}".format(filename_id_calibr, stage)
                target_ms = os.path.join(self.outdir, filename_target)
                calibr_ms = os.path.join(self.outdir, filename_calibr)

                ndppp_copy(msin=input_target_ms,
                           indatacol='DATA',
                           msout=target_ms,
                           outdatacol='DATA',
                           keep_parsets=self.keep_parsets,
                           filename_id=filename_id_target)

                ndppp_copy(msin=input_calibr_ms,
                           indatacol='DATA',
                           msout=calibr_ms,
                           outdatacol='DATA',
                           keep_parsets=self.keep_parsets,
                           filename_id=filename_id_calibr)

            else:
                target_ms = input_target_ms
                calibr_ms = input_calibr_ms


            self.logger.info(" ")
            self.logger.info("############### PIPELINE STAGE 1 ###############")

            stage = stage + 1
            if self.stages['gaincal']:

                # Generate a sky model for the calibrator
                try:
                    skymodel = generate_calibrator_skymodel(ms=calibr_ms,
                                                            filename_id=filename_id_calibr)
                except RuntimeError:
                    logger.error("Error generating calibrator sky model with parameters {ms}, {filename_id}".format(ms=calibr_ms,
                                                                                                                    filename_id=filename_id_calibr),
                                 exc_info=True)
                    raise

                # Calibration of flux calibrator
                ndppp_calibration(ms=calibr_ms,
                                  skymodel=skymodel,
                                  caltype="diagonal",
                                  usebeammodel=True,
                                  keep_parsets=self.keep_parsets,
                                  keep_skymodels=self.keep_skymodels,
                                  filename_id=filename_id_calibr)

                # # apply RM correction to calibrator
                # if self.correct_rm:
                #    bbs_RM_correct(ms = calibr_ms,
                #                   calibrator_ms = calibr_ms,
                #                   keep_parsets = self.keep_parsets,
                #                   filename_id = filename_id_calibr)

                # Smooth / normalize amplitude
                if self.smooth_amps:
                    in_instr_parmdb = os.path.join(calibr_ms, 'instrument')
                    out_instr_parmdb = in_instr_parmdb
                    try:
                        smooth_amplitudes(calibr_ms, in_instr_parmdb, out_instr_parmdb)
                    except RuntimeError:
                        logger.error("Error smoothing amplitudes with parameters: {calms}, {inparmdb} {outparmdb}".format(calms=calibr_ms,
                                                                                                                          inparmdb=in_instr_parmdb,
                                                                                                                          outparmdb=out_instr_parmdb), exc_info=True)
                        raise


                # apply solutions to the target field
                transfer_calibration_to_target(calibrator_ms = calibr_ms,
                                               target_ms = target_ms,
                                               keep_parsets = self.keep_parsets,
                                               keep_skymodels = self.keep_skymodels,
                                               keep_solutions = self.keep_solutions,
                                               filename_id = filename_id_target)

                # apply RM correction to target
                # if self.correct_rm:
                #    bbs_RM_correct(ms = target_ms,
                #                   calibrator_ms = calibr_ms,  # Q: no need for MS I guess
                #                   keep_parsets = self.keep_parsets,
                #                   filename_id = filename_id_target)

                # flag corrected data
                filename_target = "target_{}.MS.{}".format(filename_id_target, stage)
                filename_calibr = "calibr_{}.MS.{}".format(filename_id_calibr, stage)
                calibr_flag_ms = os.path.join(self.outdir, filename_calibr)
                target_flag_ms = os.path.join(self.outdir, filename_target)

                ndppp_flagger(ms = calibr_ms,
                              flagged_ms = calibr_flag_ms,
                              keep_parsets = self.keep_parsets,
                              filename_id = filename_id_calibr)
                ndppp_flagger(ms = target_ms,
                              flagged_ms = target_flag_ms,
                              keep_parsets = self.keep_parsets,
                              filename_id = filename_id_target)

            else:
                target_flag_ms = input_target_ms
                calibr_flag_ms = input_calibr_ms


            self.logger.info(" ")
            self.logger.info("############### PIPELINE STAGE 2 ###############")

            stage = stage + 1
            if self.stages['phasecal']:

                # (1) Calibrator
                ndppp_phasecal(ms = calibr_flag_ms,
                               correctModelBeam = False,
                               keep_parsets = self.keep_parsets,
                               keep_skymodels = self.keep_skymodels,
                               filename_id = filename_id_calibr)

                # Flag phase corrected data calibrator
                filename_calibr = "calibr_{}.MS.{}".format(filename_id_calibr, stage)
                calibr_phaseflag_ms = os.path.join(self.outdir, filename_calibr)

                ndppp_flagger(ms = calibr_flag_ms,
                              flagged_ms = calibr_phaseflag_ms,
                              keep_parsets = self.keep_parsets,
                              filename_id = filename_id_calibr)

                # (2) Target
                ndppp_phasecal(ms = target_flag_ms,
                               correctModelBeam = True,
                               keep_parsets = self.keep_parsets,
                               keep_skymodels = self.keep_skymodels,
                               filename_id = filename_id_calibr)

                # Flag phase corrected data calibrator
                filename_target = "target_{}.MS.{}".format(filename_id_target, stage)
                target_phaseflag_ms = os.path.join(self.outdir, filename_target)
                ndppp_flagger(target_flag_ms, target_phaseflag_ms, filename_id_target)

            else:
                target_phaseflag_ms = input_target_ms
                calibr_phaseflag_ms = input_calibr_ms


            self.logger.info(" ")
            self.logger.info('############### PIPELINE STAGE 3 ###############')

            stage = stage + 1
            if self.stages['image']:

                # wide field imaging WSClean
                fov = 10 # degrees, hard coded

                for beamsize in self.beamsizes:
                    # (1) image calibrator
                    wsclean_image(ms = calibr_phaseflag_ms,
                                  outdir = self.outdir,
                                  beamsize = beamsize,
                                  field_of_view = fov,
                                  filename_id = filename_id_calibr)

                    # (2) image target

                    wsclean_image(ms = target_phaseflag_ms,
                                  outdir = self.outdir,
                                  beamsize = beamsize,
                                  field_of_view = fov,
                                  filename_id = filename_id_target)




# Sky models derived from CEP /globaldata/COOKBOOK/Models

# Pipeline functions.
def bbs_RM_correct(ms,
                   calibrator_ms,
                   keep_parsets = False,
                   filename_id = fileid() ):
    """
    Apply RM correction to calibrator
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: RM correction {}".format(os.path.basename(ms)))

    sourcename = get_source_name(ms)

    # Generate a global sky model with R=5 deg Flux threshold 1 Jy
    try:
        skymodel = generate_calibrator_skymodel(ms = calibrator_ms,
                                                filename_id=filename_id)
    except RuntimeError:
        logger.error("Error generating calibrator sky model with parameters {ms}, {filename_id}".format(ms=calibrator_ms,
                                                                                                        filename_id=filename_id),
                     exc_info=True)
        raise

    # CreateRMparmdb using ROBR
    # RACE CONDITION: dangerous if multiple prcesses uses these files
    rmparmdb_name = sourcename+'_RMPARMDB'
    if not os.path.exists(rmparmdb_name):
        cmd = 'createRMParmdb '+ str(ms) +' --out='+ rmparmdb_name + \
              ' --IONprefix=ROBR --IONserver=ftp://gnss.oma.be/gnss/products/IONEX/ --all'
        run_command(cmd)

    # Generate calibration solutions
    parset_file = "RMcorrect_{}.parset".format(filename_id)
    p = parset()
    p.add("Strategy.InputColumn", "DATA")  # Q: DATA or CORRECTED_DATA?
    p.add("Strategy.ChunkSize", "500")
    p.add("Strategy.Baselines", "[CR]S*&")
    p.add("Strategy.UseSolver", "F")
    p.add("Strategy.Correlations", "[]")
    p.add("Strategy.Steps", "[correct]")
    p.add("Step.correct.Operation", "CORRECT")
    p.add("Step.correct.Model.Sources", sourcename)
    p.add("Step.correct.Model.Cache.Enable", "T")
    p.add("Step.correct.Model.Gain.Enable", "F")
    p.add("Step.correct.Model.Beam.Enable", "F")
    p.add("Step.correct.Model.FaradayRotation.Enable", "T")
    p.add("Step.correct.Output.Column", "CORRECTED_DATA")
    p.writeFile(parset_file)

    cmd = 'calibrate-stand-alone -f --parmdb '+ rmparmdb_name + ' ' + \
           str(ms) + ' ' + parset_file +  ' ' + str(skymodel)
    run_command(cmd)

    if not keep_parsets:
        os.remove(parset_file)

    # if remove_rmparmdb:
    #     shutils.rmtree(rmparmdb_name)

    [os.remove(x) for x in glob.glob("ROBR*I")]

    logger.info("FINISHED: RM correction {}".format(os.path.basename(ms)))



# TODO: clean up routine
def median_window_filter(amplitudes, half_window, threshold):
    """Smooth and normalize amplitude (diagonal) solutions
    :param amplitudes: ...
    :type amplitudes: numpy.ndarray
    :param half_window: ...
    :type half_window: int
    :param threshold: ...
    :type threshold: float
    :returns: filtered amplitudes
    :rtype: numpy.ndarray
    """
    logger=logging.getLogger(__name__)
    n = len(amplitudes)
    window = 2*half_window

    amplitudes_copy = np.copy(amplitudes)
    flags = np.zeros(n, dtype=bool)
    sol = np.zeros(n + window)
    sol[half_window:half_window+n] = amplitudes

    for i in range(0, half_window):
        # Mirror at left edge.
        idx = min(n-1, half_window-i)
        sol[i] = amplitudes[idx]

        # Mirror at right edge
        idx = max(0, n-2-i)
        sol[n+half_window+i] = amplitudes[idx]

    median_array  = scipy.signal.medfilt(sol, window-1)

    sol_flag = np.zeros(n + window, dtype=bool)
    sol_flag_val = np.zeros(n + window, dtype=bool)

    for i in range(half_window, half_window + n):
        # Compute median of the absolute distance to the median.
        window = sol[i-half_window:i+half_window+1]
        window_flag = sol_flag[i-half_window:i+half_window+1]
        window_masked = window[~window_flag]

        if len(window_masked) < math.sqrt(len(window)):
            # Not enough data to get accurate statistics.
            continue

        # Flag sample if it is more than 1.4826 * threshold * the
        # median distance away from the median.
        # Q: name "Median Absolute Deviation"
        # Q: use 1/0.67448975019608171 instead of 1.4826?
        median = np.median(window_masked)
        mad = 1.4826 * np.median(np.abs(window_masked - median))

        if abs(sol[i] - median) > (threshold * mad):
            sol_flag[i] = True

        # Q: why the next two lines here? Why not at beginning?
        # Q: is comment with "1.0" wrong? Should be 0.0?
        idx = np.where(sol == 0.0) # to remove 1.0 amplitudes
        sol[idx] = True   # Q: should we update sol_flags here?

    mask = sol_flag[half_window:half_window + n]

    # Q: can we use numpy syntax here
    for i in range(len(mask)):  # Q: use n instead of len(mask)?
        if mask[i]:
           amplitudes_copy[i] = median_array[half_window+i] # fixed 2012
    # Q: what does "fixed 2012" comment means?
    return amplitudes_copy




# TODO: clean up routine
def smooth_amplitudes(ms, instrument_name, instrument_name_smoothed):
    """
    Smoothing calibration amplitudes. [...]
    :param ms: Input MS
    :type ms: str or unicode
    :param instrument_name: ?
    :type instrument_name: str or unicode
    :param instrument_name: ?
    :type instrument_name_smoothed: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: Smoothing calibration amplitudes of {}".format(os.path.basename(ms)))

    pdb = parmdb.parmdb(instrument_name)
    parms = pdb.getValuesGrid('*')
    pdb = 0

    # Get a list of antenna names
    try:
        anttab = pt.table(ms + '::ANTENNA')
    except RuntimeError:
        raise RuntimeError("{} has not been created".format(ms))
    antenna_list = anttab.getcol('NAME')
    anttab.close()

    gain = 'Gain'
    pol_list = ['0:0','1:1']
    amplist = []

    # Smooth
    for pol in pol_list:
        for antenna in antenna_list:

            key_real = gain + ':' + pol + ':Real:'+ antenna
            key_imag = gain + ':' + pol + ':Imag:'+ antenna

            real = np.copy(parms[key_real]['values'][:, 0])
            imag = np.copy(parms[key_imag]['values'][:, 0])
            phase = np.arctan2(imag, real)
            amp   = np.hypot(imag, real)

            half_window = 4
            amp = np.log10(amp)
            amp = median_window_filter(amplitudes=amp, half_window=half_window, threshold=6)
            amp = median_window_filter(amplitudes=amp, half_window=half_window, threshold=6)
            amp = median_window_filter(amplitudes=amp, half_window=7, threshold=6)
            amp = median_window_filter(amplitudes=amp, half_window=4, threshold=6)
            amp = median_window_filter(amplitudes=amp, half_window=3, threshold=6)
            amp = 10**amp

            parms[key_real]['values'][:, 0] = amp*np.cos(phase)
            parms[key_imag]['values'][:, 0] = amp*np.sin(phase)

    # Q: Can we fuse all three loop nests?

    # Normalize
    for pol in pol_list:
        for antenna in antenna_list:
            real = np.copy(parms[key_real]['values'][:, 0])
            imag = np.copy(parms[key_imag]['values'][:, 0])
            amp  = np.copy(np.hypot(real, imag))
            amplist.append(amp)
            norm_factor = 1./(np.mean(amplist))

    for pol in pol_list:
        for antenna in antenna_list:
            real = np.copy(parms[key_real]['values'][:, 0])
            imag = np.copy(parms[key_imag]['values'][:, 0])
            parms[key_real]['values'][:, 0] = np.copy(imag*norm_factor)
            parms[key_imag]['values'][:, 0] = np.copy(real*norm_factor)

    if os.path.exists(instrument_name_smoothed):
        shutil.rmtree(instrument_name_smoothed)

    pdbnew = parmdb.parmdb(instrument_name_smoothed, create=True)
    pdbnew.addValues(parms)
    pdbnew.flush(fsync=True)
    pdbnew = 0

    logger.info("FINISHED: Smoothing calibration amplitudes of {}".format(os.path.basename(ms)))







# copy ms via ndppp to make the FLAG table writable and be able to use
# the CORRECTED_DATA columns.
def ndppp_copy(msin,
               indatacol,  # usually 'DATA' or 'CORRECTED_DATA'
               msout,
               outdatacol, # usually 'DATA' or 'CORRECTED_DATA'
               keep_parsets = False,
               filename_id = fileid()):
    """
    Copy ms via ndppp to make the FLAG table writable and be able to use
    the CORRECTED_DATA columns. Overwrite existing 'msout' file.
    :param msin: Input MS
    :type msin: str or unicode
    :param msout: Output MS
    :type msout: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: Copy {} to {}".format(os.path.basename(msin),
                                              os.path.basename(msout)))

    p = parset()
    p.add("msin", msin)
    p.add("msin.datacolumn", indatacol)
    p.add("steps", "[]")
    p.add("msout", msout)
    p.add("msout.datacolumn", outdatacol)
    p.add("msout.overwrite", "true")
    parset_file = "ndppp_copy_{}.parset".format(filename_id)
    p.writeFile(parset_file)

    run_command("NDPPP {parset}".format(parset=parset_file))

    if not keep_parsets:
        os.remove(parset_file)

    logger.info("FINISHED: Copy {} to {}".format(os.path.basename(msin),
                                                 os.path.basename(msout)))



def generate_calibrator_skymodel(ms, filename_id = fileid(), filename = None):
    """Generate a sky model for the calibrator
    :param: ms: measurement set
    :type ms: str or unicode
    :returns: filename of created file containing the sky model
    :rtype: str or unicode
    """
    logger = logging.getLogger(__name__)
    calibrator_model_dict = {
        '3C48' : {'type' : 'POINT', 'ra' : '01:37:41.299431', 'dec' : '+33.09.35.132990', 'stokesI' : 70.399325,
                  'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172,
                  'spindx2' : 0.335733, 'spindx3' : -0.059050},
        '3C123' : {'type' : 'POINT', 'ra' : 1.2089586805287118, 'dec' : 0.51784800297944011, 'stokesI' : 70.399325,
                   'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172, 'spindx2' : 0.335733,
                   'spindx3' : -0.059050},
        '3C147' : {'type' : 'POINT', 'ra' : 1.4948845329950251, 'dec' : 0.87008170276516283, 'stokesI' : 70.399325,
                   'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172, 'spindx2' : 0.335733,
                   'spindx3' : -0.059050},
        '3C196' : {'type' : 'POINT', 'ra' : '08:13:36.15', 'dec' : '+48.13.04.7', 'stokesI' : 136.4,
                   'refFREQ' : '74.0e6', 'spindx0' : -0.8, 'spindx1' : 0.000000, 'spindx2' : 0.000000,
                   'spindx3' : 0.000000},
        '3C286' : {'type' : 'POINT', 'ra' : 3.5392577712237649, 'dec' : 0.53248520675129063, 'stokesI' : 70.399325,
                   'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172, 'spindx2' : 0.335733,
                   'spindx3' : -0.059050},
        '3C287' : {'type' : 'POINT', 'ra' : 3.5370326736496778, 'dec' : 0.43900304025459363, 'stokesI' : 70.399325,
                   'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172, 'spindx2' : 0.335733,
                   'spindx3' : -0.059050},
        '3C295a' : {'type' : 'POINT', 'ra' : '14:11:20.49', 'dec' : '+52.12.10.70', 'stokesI' : 48.8815,
                    'refFREQ' : '150.0e6', 'spindx0' : -0.582, 'spindx1' : -0.298, 'spindx2' : 0.583,
                    'spindx3' : -0.363},
        '3C295b' : {'type' : 'POINT', 'ra' : '14:11:20.79', 'dec' : '+52.12.07.90', 'stokesI' : 48.8815,
                    'refFREQ' : '150.0e6', 'spindx0' : -0.582, 'spindx1' : -0.298, 'spindx2' : 0.583,
                    'spindx3' : -0.363},
        '3C380' : {'type' : 'POINT', 'ra' : 4.8412365231310863, 'dec' : 0.85078091290947200, 'stokesI' : 70.399325,
                   'refFREQ' : '150.0e6', 'spindx0' : -0.396150, 'spindx1' : -0.650172, 'spindx2' : 0.335733,
                   'spindx3' : -0.059050} }

    logger.info(" ")
    logger.info("START: Creating sky model for {}".format(os.path.basename(ms)))

    source_name = get_source_name(ms)

    Nkey = 1 # By default we have 1 key for a calibrator
    source_name_list = [source_name]

    try:
        data = [calibrator_model_dict[source_name]]
    except KeyError:
        Nkey = 2  # number of keys for this one is 0 or 2. Set to 2 for next test

    if Nkey == 2:
        try:
            data = [calibrator_model_dict[source_name+"a"]]  # assuming coherent naming scheme
        except KeyError:
            raise RuntimeError("Calibrator {} is not in dictionary and no model is generated.".format(source_name))
        try:
            data.append(calibrator_model_dict[source_name+"b"])
        except KeyError:
            raise RuntimeError("Calibrator {} has an a component but no b component.".format(source_name))
        source_name_list = [source_name+"a",source_name+"b"]

    if not filename:
        filename = source_name + "_" + filename_id + '.skymodel'
    with open(filename, 'w') as f:
        f.write("# (Name, Type, Ra, Dec, I, ReferenceFrequency='{}', " \
                "SpectralIndex='[0.0]') = format\n".format(data[0]['refFREQ']))
        for ctr, data_line in enumerate(data):
            f.write("{name}, {type}, {ra}, {dec}, {stokesI}, {refFREQ}, "\
                    "[{spindx0}, {spindx1}, {spindx2}, {spindx3}]\n".format(
                        name=source_name_list[ctr], type=data_line['type'], ra=data_line['ra'],
                        dec=data_line['dec'], stokesI=data_line['stokesI'],
                        refFREQ=data_line['refFREQ'], spindx0=data_line['spindx0'],
                        spindx1=data_line['spindx1'], spindx2=data_line['spindx2'],
                        spindx3=data_line['spindx3']))

    logger.info("FINISHED: Creating sky model for {}".format(os.path.basename(ms)))

    return filename



def ndppp_calibration(ms,
                      skymodel,
                      caltype = "diagonal",  # "diagonal" or "fulljones"
                      usebeammodel = True,
                      keep_parsets = False,
                      keep_skymodels = False,
                      filename_id = fileid()):
    """Calibrate the (full) Jones matrix with NDPPP
    :param ms: ...
    :type ms: str or unicode
    :param usebeammodel: ...
    :type usebeammodel: bool
    :param filename_id: ...
    :type filename_id: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: Use and apply gaincal on {}".format(os.path.basename(ms)))

    # Add the sky model to the MS
    # Note: Putting the < in quotes will make the command fail
    skymodel_db = os.path.join(ms, 'sky')
    cmd = 'makesourcedb in='+str(skymodel)+' out='+str(skymodel_db)+' format=<'
    run_command(cmd)

    # Generate calibration solutions
    gaincal_parset_name = "gaincal_{}.parset".format(filename_id)
    p1 = parset()
    p1.add("msin", ms)
    p1.add("msin.datacolumn", "DATA")
    p1.add("msin.baseline", "[CR]S*&")
    p1.add("msout", ms)
    p1.add("msout.datacolumn", "CORRECTED_DATA")
    p1.add("steps", "[calibrate]")
    p1.add("calibrate.type", "gaincal")
    p1.add("calibrate.caltype", caltype)
    p1.add("calibrate.sourcedb", skymodel_db)
    p1.add("calibrate.usemodelcolumn", "F")
    p1.add("calibrate.usebeammodel", str(usebeammodel)[0])
    p1.add("calibrate.tolerance", "1.e-5")
    p1.add("calibrate.parmdb", os.path.join(ms, "instrument"))
    p1.writeFile(gaincal_parset_name)

    run_command("NDPPP " + gaincal_parset_name)

    # Apply calibration solutions
    apply_parset_name = "applycal_{}.parset".format(filename_id)
    p2 = parset()
    p2.add("msin", ms)
    p2.add("msin.datacolumn", "CORRECTED_DATA")
    p2.add("msin.baseline", "[CR]S*&")
    p2.add("msout", ms)
    p2.add("msout.datacolumn", "CORRECTED_DATA")
    p2.add("steps", "[applycal]")
    p2.add("applycal.type" , "applycal")
    p2.add("applycal.correction", "gain")
    p2.add("applycal.parmdb", os.path.join(ms, "instrument"))
    p2.writeFile(apply_parset_name)

    run_command("NDPPP " + apply_parset_name)

    if not keep_parsets:
        os.remove(gaincal_parset_name)
        os.remove(apply_parset_name)

    if not keep_skymodels:
        logger.debug("Removing sky model {smfile}".format(smfile=skymodel))
        os.remove(skymodel)

    logger.info("FINISHED: Use and apply gaincal on {}".format(os.path.basename(ms)))



def export_calibration_solutions(ms, filename_id = fileid()):
    """Export time independent solutions before transfer to target.
    :param ms: ...
    :type ms: str or unicode
    :param filename_id: ...
    :type filename_id: str or unicode
    :returns: folder name containing the exported solutions
    :rtype: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: Export calibration solutions of {}".format(ms))

    source_name = get_source_name(ms)
    solns   = source_name + "_" + filename_id + '.solutions'
    cmd = 'parmexportcal in=' + os.path.join(ms, 'instrument') + ' out=' + solns
    run_command(cmd)

    logger.info("FINISHED: Export calibration solutions of {}".format(os.path.basename(ms)))

    return solns




def transfer_calibration_to_target(calibrator_ms,
                                   target_ms,
                                   keep_parsets = False,
                                   keep_skymodels = False,
                                   keep_solutions = False,
                                   filename_id = fileid()):
    """Apply solutions to the target field
    :param ms: ...
    :param solutions: ...
    :param filename_id: ...
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: transfer calibration solutions from {} to {}".format(
                os.path.basename(calibrator_ms),
                os.path.basename(target_ms)))

    # Export time independent solutions before transfer to target
    # Q: since simultatious measurement, is really necassary? TJ says no.
    solutions = export_calibration_solutions(ms=calibrator_ms,
                                             filename_id=filename_id)

    # Generate a global sky model with default radius R=5 deg and flux threshold 1 Jy
    try:
        skymodel = get_gsm_skymodel(target_ms, filename_id=filename_id)
    except RuntimeError:
        logger.error("Error generating gsm sky model with parameters {ms}, {filename_id}".format(ms=target_ms,
                                                                                                 filename_id=filename_id),
                     exc_info=True)
        raise

    source_name = get_source_name(target_ms)

    #add the sky model to the MS
    skymodel_db = os.path.join(target_ms, 'sky')
    cmd = 'makesourcedb in='+str(skymodel)+' out='+str(skymodel_db)+' format=<'
    run_command(cmd)

    #create a NDPPP parset to apply solutions
    parset_name = "applycal_target_{}.parset".format(filename_id)
    p = parset()
    p.add("msin", target_ms)
    p.add("msin.datacolumn", "DATA")
    p.add("msin.baseline", "[CR]S*&")
    p.add("msout", target_ms)
    p.add("msout.datacolumn", "CORRECTED_DATA")
    p.add("steps", "[applycal]")
    p.add("applycal.type", "applycal")
    p.add("applycal.correction", "gain")
    p.add("applycal.parmdb", solutions) # no /instrument because sols were exported
    p.writeFile(parset_name)

    #create a NDPPP parset to apply solutions
    run_command("NDPPP " + parset_name)

    if not keep_parsets:
        os.remove(parset_name)

    if not keep_skymodels:
        os.remove(skymodel)

    if not keep_solutions:
        shutil.rmtree(solutions)

    logger.info("FINISHED: transfer calibration solutions from {} to {}".format(
                os.path.basename(calibrator_ms),
                os.path.basename(target_ms)))


def ndppp_flagger(ms,
                  flagged_ms,
                  keep_parsets = False,
                  filename_id = fileid()):
    # type: (object, object, object, object) -> object
    """Doc striung goes here
    :param ms: ...
    :type ms: str or unicode
    :param flagged_ms: ...
    :type flagged_ms: str or unicode
    :param filename_id: ...
    :type filename_id: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: flagging {}".format(os.path.basename(ms)))

    # Q: why create a new MS and not just flag the old one?
    parset_name = "ndppp_flagger_{}.parset".format(filename_id)
    p = parset()
    p.add("msin" , ms)
    p.add("msin.datacolumn", "CORRECTED_DATA")
    p.add("msout", flagged_ms)
    p.add("msout.datacolumn", "DATA")
    p.add("steps", "[preflagger,aoflagger]")
    p.add("preflagger.corrtype", "auto")
    p.add("preflagger.type", "preflagger")
    p.add("aoflagger.autocorr", "F")
    p.add("aoflagger.keepstatistics", "T")
    p.add("aoflagger.timewindow", "0")
    p.add("aoflagger.type", "aoflagger")
    p.writeFile(parset_name)

    run_command("NDPPP " + parset_name)

    if not keep_parsets:
        os.remove(parset_name)

    logger.info("FINISHED: flagging {}".format(os.path.basename(ms)))



def ndppp_phasecal(ms, correctModelBeam,
                   keep_parsets = False,
                   keep_skymodels = False,
                   filename_id = fileid()):
    """Function to phase calibrate a peeled MS with GainCal.
    :param ms: ...
    :type ms: str or unicode
    :param correctModelBeam: ...
    :type correctModelBeam: bool
    :param filename_id: ...
    :type filename_id: str or unicode
    """
    logger = logging.getLogger(__name__)
    # TODO: use python boolean as input; use str(False) etc in parset possible?
    logger.info(" ")
    logger.info("START: phase calibrating {}".format(os.path.basename(ms)))

    # Generate a global sky model with R=5 deg Flux threshold 1 Jy
    try:
        skymodel = get_gsm_skymodel(ms, filename_id=filename_id)
    except RuntimeError:
        logger.error("Error generating gsm sky model with parameters {ms}, {filename_id}".format(ms=ms, filename_id=filename_id),
                     exc_info=True)
        raise

    source_name = get_source_name(ms)
    source_db = os.path.join(ms, 'faint')
    cmd = 'makesourcedb in='+str(skymodel)+' out='+str(source_db)+' format=<'
    run_command(cmd)

    # Compute gains
    phasesolve_parset_name = "phasesolve_{}.parset".format(filename_id)
    p1 = parset()
    p1.add("msin", ms)
    p1.add("msin.datacolumn", "DATA")
    p1.add("msout", ".")
    p1.add("msout.datacolumn", "CORRECTED_DATA")
    p1.add("steps", "[solve]")
    p1.add("solve.type", "gaincal")
    p1.add("solve.caltype", "phaseonly")
    p1.add("solve.sourcedb", source_db)
    p1.add("solve.usebeammodel", str(correctModelBeam)[0])
    p1.add("solve.parmdb", ms+"/instrument")
    p1.add("solve.maxiter", "200")
    p1.writeFile(phasesolve_parset_name)

    run_command('NDPPP ' + phasesolve_parset_name)

    # Apply computed gains
    phasecorrect_parset_name = "phasecorrect_{}.parset".format(filename_id)
    p2 = parset()
    p2.add("msin", ms)
    p2.add("msin.datacolumn", "CORRECTED_DATA")
    p2.add("msout", ".")
    p2.add("msout.datacolumn", "CORRECTED_DATA")
    p2.add("steps", "[correct]")
    p2.add("correct.type", "applycal")
    p2.add("correct.correction", "gain")
    p2.add("correct.parmdb", os.path.join(ms, "instrument"))
    p2.writeFile(phasecorrect_parset_name)

    run_command('NDPPP ' + phasecorrect_parset_name)

    if not keep_parsets:
        os.remove(phasesolve_parset_name)
        os.remove(phasecorrect_parset_name)

    if not keep_skymodels:
        os.remove(skymodel)

    logger.info("FINISHED: phase calibrating {}".format(os.path.basename(ms)))



def get_gsm_skymodel(ms,
                     radius = 5,
                     fluxthresh = 1,
                     filename_id = fileid(),
                     filename = None):
    """Generate a global sky model with default R=5 deg Flux threshold 1 Jy
    :param ms: ...
    :type ms: str or unicode
    :param radius: int
    :param fluxTHRES: ...
    :param filename_id: ...
    :returns: filename of created file that contains the model
    :rtype: str or unicode
    """
    logger = logging.getLogger(__name__)
    logger.info(" ")
    logger.info("START: get GSM skymodel for {} with radius {} deg and flusx threshold {} Jy".format(os.path.basename(ms), radius, fluxthresh))

    try:
        tabtarget = pt.table(ms+'/FIELD')
    except RuntimeError:
        raise RuntimeError("{} has not been created".format(ms))
    coords	= tabtarget.getcell('REFERENCE_DIR',0)
    target	= coords[0]*180./math.pi    # radians -> degrees
    ra_target   = target[0]+360.
    dec_target  = target[1]
    source_name = get_source_name(ms)
    if not filename:
        filename = 'GSM_' + source_name + '_R' + \
                   str(radius) +'deg_Ft' + str(fluxthresh) + 'Jy_' + filename_id + '.skymodel'
    arguments = "{} {} {} {} {} 0.01".format(filename, ra_target, dec_target,
                                             radius, fluxthresh)
    cmd         = "gsm_wrapper " + arguments

    run_command(cmd)

    logger.info("FINISHED: get GSM skymodel for {}".format(os.path.basename(ms),
                                                               radius, fluxthresh))

    tabtarget.close()

    return filename





def wsclean_image(ms,
                  beamsize,
                  field_of_view,
                  robust_briggs = -2.0,
                  data_column = 'DATA',
                  outdir = None,
                  filename_id = fileid(),
                  fileroot = None):
    """Wide field imaging of the calibrator and target with WSClean.
    :param ms: ...
    :param robust_briggs: ...
    :param data_column: ...
    :param beamsize: ...
    :param field_of_view: ...
    :param filename_id: ...
    """
    logger = logging.getLogger(__name__)

    logger.info(" ")
    logger.info("START: imaging {}".format(os.path.basename(ms)))

    try:
        cell_size, n_pixels, tmp, uvmax_wsclean = get_imaging_parameters(ms,
                                                                         beamsize,
                                                                         field_of_view)
    except RuntimeError:
        logger.error("Error in get_imaging_parameters with arguments {ms}, {beamsize}, {field_of_view}".format(ms=ms,
                                                                                                               beamsize=beamsize,
                                                                                                               field_of_view=field_of_view),
                     exc_info=True)
        raise

    source_name = get_source_name(ms)

    # TODO: fov hardcoded, directory global variable
    if fileroot:
        image_name = fileroot
    elif outdir:
        image_name = str(source_name)+'_'+str(field_of_view)+'deg_StokesI_'+str(filename_id)
        image_name = os.path.join(outdir, image_name)
    else:
        raise RunTimeError("You need to either provide an output directory or an output file root. None present.")

    logger.info("Will write to output file {}".format(image_name))

    image_threshold = 0.005

    if os.path.exists(image_name):
        os.remove(image_name)

    # # with multiscale cleaning
    # cmd = 'wsclean -mem 30 -reorder -name '+ str(image_name) + \
    #       ' -size '+ str(n_pixels) +' ' + str(n_pixels) + \
    #       ' -scale '+ str(cell_size) + \
    #       'asec -weight briggs '+ str(robust_briggs) + \
    #       ' -pol I -datacolumn ' + str(data_column) + ' -maxuv-l '+ str(uvmax_wsclean) + \
    #       ' -niter 20000 -threshold '+ str(image_threshold) + \
    #       ' -mgain 0.9 -multiscale -fitbeam '+ str(ms)

    # without multiscale cleaning
    cmd = 'wsclean -mem 30 -reorder -name '+ str(image_name) + \
          ' -size '+ str(n_pixels) + ' '+ str(n_pixels) + \
          ' -scale '+ str(cell_size) + \
          'asec -weight briggs '+ str(robust_briggs) + \
          ' -pol I -datacolumn '+ str(data_column) +' -maxuv-l '+ str(uvmax_wsclean) + \
          ' -niter 10000 -threshold '+ str(image_threshold) + \
          ' -mgain 0.9 -dft-with-beam -beamsize '+ str(beamsize) + \
          'asec -circularbeam -nofitbeam '+ str(ms)

    run_command(cmd)

    logger.info("FINISHED: imaging {}".format(os.path.basename(ms)))

def testlogger():
    """
    Helper function to test logger functionality. Just prints a warning
    """
    logger = logging.getLogger(__name__)
    logger.warning("If you can read this, it looks like the logger works.")

# MAIN ROUTINE START HERE
if __name__ == "__main__":

    calrun = CALIB()
    logger = logging.getLogger(__name__)

    # add handlers and so...
    # Run the demo pipeline
    calrun.run()
