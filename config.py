import json
import os

class Config:
    def __init__(self):
        self.filename = os.path.join('..', '..', "resources", "python-berlys-config.json")

    def get_config(self):
        with open(self.filename) as f:
            return json.load(f)


