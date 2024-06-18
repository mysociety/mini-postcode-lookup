"""
Fetch ONSPD file
"""

import tempfile
import zipfile
from pathlib import Path

import requests

data_dir = Path("data", "raw")

onspd_loc = data_dir / "onspd.csv"

onspd = "https://parlvid.mysociety.org/os/ONSPD/2022-11.zip"
latest_file = "ONSPD_NOV_2022_UK.csv"


def get_onspd():
    # download the file
    r = requests.get(onspd)

    # write the file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(r.content)
        f.flush()
        f.close()
        with zipfile.ZipFile(f.name) as z:
            # Extract Data/ONSPD_NOV_2022_UK.csv to the data directory
            z.extract(f"Data/{latest_file}", data_dir)
            (data_dir / "Data" / latest_file).rename(onspd_loc)
        Path(f.name).unlink()


def get_onspd_if_not_present():
    if not onspd_loc.exists():
        get_onspd()


if __name__ == "__main__":
    get_onspd_if_not_present()
    print("Done")
