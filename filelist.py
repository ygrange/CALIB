class FileReturner(object):

    def __init__(self):
        self.files = {"calibrator": "L12345C.MS", "target": "L12345T.MS"}

    def get(self, filetype):
        return self.files[filetype]
