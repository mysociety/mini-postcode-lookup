from __future__ import annotations

import bisect
import json
import re
from array import array
from pathlib import Path
from typing import TypedDict, Union

import pandas as pd
import requests

from .util import StrEnum


class AllowedAreaTypes(StrEnum):
    PCON_2010 = "pcon_2010"
    PCON_2024 = "pcon_2024"
    LOCAL_AUTHORITIES = "local_authorities"
    LSOA = "lsoa"


areas_with_lookups = [AllowedAreaTypes.PCON_2024, AllowedAreaTypes.LOCAL_AUTHORITIES]


postcode_regex = re.compile(
    r"^(?:"
    r"[A-Z]{2}[0-9][A-Z]|"  # AA9A
    r"[A-Z][0-9][A-Z]|"  # A9A
    r"[A-Z][0-9]|"  # A9
    r"[A-Z][0-9]{2}|"  # A99
    r"[A-Z]{2}[0-9]|"  # AA9
    r"[A-Z]{2}[0-9]{2}"  # AA99
    r")[0-9][A-Z]{2}$"
)


data_folder = Path(__file__).parent / "data"


def load_lookup(area_type: AllowedAreaTypes) -> pd.DataFrame:
    file_loc = data_folder / "lookups" / f"{area_type}_lookup.json"

    df = pd.read_json(file_loc, orient="index")  # type: ignore
    df = df.reset_index().rename(columns={"index": area_type})
    return df


def check_real_postcode(postcode: Union[str, float]) -> bool:
    """
    Check if a postcode is a valid UK postcode
    """
    if not isinstance(postcode, str):
        return False
    return bool(postcode_regex.match(postcode.replace(" ", "").upper()))


class StoredData(TypedDict):
    postcode_keys: list[int]
    value_key: list[int]
    value_values: list[str]


def reverse_difference_compression(list_a: list[int]) -> list[int]:
    """
    Given a list of integers increasing in value,
    compress the list by storing the difference between each value
    """
    result: list[int] = []
    last_value = 0
    for value in list_a:
        last_value += value
        result.append(last_value)
    return result


def reverse_drop_minus_one(list_a: list[int]) -> list[int]:
    """
    list_a is a list of integers, where it is common enough that
    list_a[i] is equal to list_a[i-2]
    where this is the case, we can compress it by storing it as None
    """
    result: list[int] = list_a[:2]

    for value in list_a[2:]:
        if value == 0:
            result.append(result[-2])
        else:
            result.append(value)

    # make zero indexed again
    return [x - 1 for x in result]


def postcode_to_int(postcode: str) -> int:
    """
    remove spaces and convert UK postcodes to integers
    Postcodes have letter and numbers, but we can treat this as a base 36 number
    """
    return int(postcode.replace(" ", "").upper(), 36)


DEBUG = False


class PostcodeRangeLookup:
    def __init__(
        self, postcode_keys: array[int], value_key: array[int], value_values: list[str]
    ):
        self.postcode_keys = postcode_keys
        self.value_key = value_key
        self.value_values = value_values

    def get_value(self, postcode: str, check_valid_postcode: bool = True):
        if check_valid_postcode and not check_real_postcode(postcode):
            if DEBUG:
                print(f"Invalid postcode: {postcode}")
            return None

        int_postcode = postcode_to_int(postcode)

        # use binary search to find the index of the first postcode_key that is greater than int_postcode
        left = bisect.bisect_left(self.postcode_keys, int_postcode)
        # if left is 0, then the postcode is less than the first postcode_key
        if left == 0 and int_postcode != self.postcode_keys[0]:
            return None

        if left < len(self.postcode_keys) and self.postcode_keys[left] != int_postcode:
            left -= 1
        if left == len(self.postcode_keys):
            left -= 1

        value_index = self.value_key[left]

        if value_index == -1 or value_index >= len(self.value_values):
            return None
        else:
            return self.value_values[value_index]

    @classmethod
    def from_dict(cls, data: StoredData):
        return cls(
            postcode_keys=array(
                "Q", reverse_difference_compression(data["postcode_keys"])
            ),
            value_key=array("Q", reverse_drop_minus_one(data["value_key"])),
            value_values=data["value_values"],
        )

    @classmethod
    def from_json(cls, path: Path):
        with path.open("r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_json_url(cls, url: str):
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return cls.from_dict(data)

    @classmethod
    def from_area_type(cls, area_type: str):
        return cls.from_json(data_folder / f"{area_type}.json")


class MiniPostcodeLookup:
    def __init__(self, preload: list[AllowedAreaTypes] = []):
        self.lookups: dict[AllowedAreaTypes, PostcodeRangeLookup] = {}
        for area_type in preload:
            self.check_and_load_area(area_type)

    def check_and_load_area(self, area_type: AllowedAreaTypes):
        if area_type not in self.lookups:
            self.lookups[area_type] = PostcodeRangeLookup.from_area_type(area_type)

    def get_multiple_values(self, postcode: str, *, area_types: list[AllowedAreaTypes]):
        return {
            area_type: self.get_value(postcode, area_type=area_type)
            for area_type in area_types
        }

    def add_to_csv(
        self,
        file_loc: Path,
        *,
        area_type: AllowedAreaTypes = AllowedAreaTypes.PCON_2024,
        postcode_col: str = "postcode",
        include_extra_cols: bool = False,
    ):
        """
        Add a column to a csv with the area type
        """

        dest_path = file_loc.parent / f"{file_loc.stem}_with_{area_type}.csv"

        df = pd.read_csv(file_loc)  # type: ignore
        df = self.add_to_df(
            df,
            area_type=area_type,
            postcode_col=postcode_col,
            include_extra_cols=include_extra_cols,
        )
        df.to_csv(dest_path, index=False)

    def get_series(
        self, series: pd.Series, *, area_type: AllowedAreaTypes
    ) -> pd.Series:
        self.check_and_load_area(area_type)
        return series.apply(  # type: ignore
            lambda x: self.get_value(x, area_type=area_type)  # type: ignore
        )

    def add_to_df(
        self,
        df: pd.DataFrame,
        *,
        area_type: AllowedAreaTypes = AllowedAreaTypes.PCON_2024,
        postcode_col: str = "postcode",
        include_extra_cols: bool = False,
    ):
        """
        Add a column to a dataframe with the area type
        """
        df[area_type] = df[postcode_col].apply(  # type: ignore
            lambda x: self.get_value(x, area_type=area_type)  # type: ignore
        )

        if area_type in areas_with_lookups and include_extra_cols:
            lookup_df = load_lookup(area_type)
            df = df.merge(lookup_df, on=area_type, how="left")  # type: ignore

        return df

    def get_value(self, postcode: str, *, area_type: AllowedAreaTypes):
        self.check_and_load_area(area_type)
        return self.lookups[area_type].get_value(postcode)
