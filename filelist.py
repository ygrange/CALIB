import ConfigParser


class FileReturner(object):

    def __init__(self, input_files='/tmp/inputfiles.dat'):
        parser = ConfigParser.ConfigParser()
        parser.read(input_files)
        self.files = {"calibrator": parser.get('files', 'calibrators'),
                      "target": parser.get('files', 'targets')}

    def get(self, filetype):
        return self.files[filetype]
