from datetime import datetime
from __main__ import __file__ as functionname

def create_donemark(fname):
    file_content = "{functionname} done on {timestamp}\n"
    timestamp = datetime.now().isoformat()
    with open(fname, "w") as wrf:
        wrf.write(file_content.format(functionname=functionname,
                                      timestamp=timestamp))
def check_donemark(fname):
    logger = logging.getLogger(__name__)
    with open(fname) as fh:
        logtext = "Contents of DoneMark file {fname}: {content}"
        logger.debug(logtext.format(fname=fname, content=fh.read())
