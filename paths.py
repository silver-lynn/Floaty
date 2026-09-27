import os
from pathlib import Path

def data_dir():
    return Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData/Local")))/"Floaty"
