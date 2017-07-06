from datetime import datetime
from __main__ import __file__ as functionname

def create_donemark(fname):
    file_content = "{functionname} done on {timestamp}\n"
    timestamp = datetime.now().isoformat()
    with open(fname, "w") as wrf:
        wrf.write(file_content.format(functionname=functionname,
                                      timestamp=timestamp))