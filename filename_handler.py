import os
import re
from glob import glob

from core import DateHandler
from config import Config


class FilenameHandler:
    data_dir = "../../data/berlys/"
    attachments_dir = f"{data_dir}attachments/"
    download_dir = "../../../../Downloads/"

    def __init__(self):
        self.config = Config().get_config()
        self.default_filename = self.config['default_filename']
        self.path = ''
        self.filename = ''
        self.basename = ''
        self.ext = ''
        self.absolute_filename = ''

    def set_attributes(self, path, filename):
        self.basename, self.ext = os.path.splitext(filename)
        self.path = path
        self.filename = f"{self.basename}{self.ext}"
        self.absolute_filename = f"{self.path}/{self.filename}"

    def from_download_dir(self):
        self.set_attributes(self.download_dir, self.default_filename)
        return self.absolute_filename

    def from_data_dir(self):
        dirs = glob(f"{self.data_dir}/*/*/")
        files = []
        for dir_ in dirs:
            if re.search(r"\d{2,4}", dir_):
                dir_ = dir_.replace(os.sep, '/')
                for file in glob(f"{dir_}*.txt"):
                    files.append(file)
        path, filename = os.path.split(files[-1])
        self.set_attributes(path, filename)
        return self.absolute_filename

    def to_data_dir(self, date: DateHandler):
        year = date.get_year()
        month = date.get_month()
        self.set_attributes(f"{self.data_dir}/{year}/{month}/", f"{date}.txt")
        return self.absolute_filename

    def to_attachments_dir(self, filename):
        self.set_attributes(self.attachments_dir, f"{filename}")
        return self.absolute_filename
