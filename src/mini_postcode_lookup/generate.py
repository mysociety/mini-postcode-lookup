"""
Script to generate lookups for different kinds of geography
"""

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pandas as pd
from tqdm import tqdm

dest_folder = Path(__file__).parent / "data"

# Remove NI data
LIMIT_NI = True


def difference_compression(input_list: list[int]) -> list[int]:
    """
    Given a list of integers increasing in value,
    compress the list by storing the difference between each value
    """
    result: list[int] = []
    last_value = 0
    for value in input_list:
        result.append(value - last_value)
        last_value = value
    return result


def drop_minus_one(input_list: list[int]) -> list[int]:
    """
    list_a is a list of integers, where it is common enough that
    list_a[i] is equal to list_a[i-2]
    where this is the case, we can compress it by storing it as None
    """
    input_list = [x + 1 for x in input_list]  # promote all zeroes up a level
    result: list[int] = input_list[:2]

    for value in input_list[2:]:
        if value == result[-2]:
            result.append(0)
        else:
            result.append(value)

    return result


@dataclass
class PostcodeRangeLookup:
    postcode_keys: list[int]
    value_key: list[int]
    value_values: list[str]

    def to_dict(self):
        return {
            "postcode_keys": difference_compression(self.postcode_keys),
            "value_key": drop_minus_one(self.value_key),
            "value_values": self.value_values,
        }

    def to_pickle(self, path: Path):
        with path.open("wb") as f:
            pickle.dump(self.to_dict(), f)

    def to_json(self, path: Path):
        with path.open("w") as f:
            json.dump(self.to_dict(), f, separators=(",", ":"))

    @classmethod
    def from_json(cls, path: Path):
        with path.open("r") as f:
            data = json.load(f)
        return cls(
            postcode_keys=data["postcode_keys"],
            value_key=data["value_key"],
            value_values=data["value_values"],
        )


def postcode_to_int(postcode: str) -> int:
    """
    remove spaces and convert UK postcodes to integers
    Postcodes have letter and numbers, but we can treat this as a base 36 number
    """
    return int(postcode.replace(" ", "").upper(), 36)


def create_range(
    df: pd.DataFrame,
    *,
    postcode_col: str,
    value_col: str,
    output_label: str,
    dest: Path,
):
    # get a dictionary of an int to unique value col

    unique_values = sorted(df[value_col].unique().tolist(), key=str)  # type: ignore
    value_to_int = {value: i for i, value in enumerate(unique_values)}
    value_to_int[None] = len(unique_values) + 1

    df["postcode_int"] = df[postcode_col].apply(postcode_to_int)  # type: ignore
    df["value_int"] = df[value_col].apply(value_to_int.get)  # type: ignore

    df = df.sort_values("postcode_int")  # type: ignore

    # now we need to iterate through this, and create a list of when postcode_int value when the value_int value changes

    range_postcode_array: list[int] = []
    range_value_array: list[int] = []

    last_value: int = -1
    for index, row in tqdm(df.iterrows(), total=len(df)):  # type: ignore
        value = int(row["value_int"])  # type: ignore
        postcode = int(row["postcode_int"])  # type: ignore
        if value != last_value or index == len(df) - 1:
            range_postcode_array.append(postcode)
            range_value_array.append(value)
        last_value = value

    result = PostcodeRangeLookup(
        postcode_keys=range_postcode_array,
        value_key=range_value_array,
        value_values=unique_values,
    )

    if not dest_folder.exists():
        dest_folder.mkdir()

    result.to_json(dest)


class BaseLookupCreator:
    slug = ""
    postcode_col = ""
    value_col = ""
    df_source: Union[Path, str] = ""
    test_df_source: Union[Path, str] = ""

    def get_df(self, test: bool = False) -> pd.DataFrame:
        str_path = str(self.test_df_source) if test else str(self.df_source)
        if str_path.lower().endswith(".parquet"):
            df = pd.read_parquet(str_path, columns=[self.postcode_col, self.value_col])
        else:
            df = pd.read_csv(  # type: ignore
                str_path,
                usecols=[self.postcode_col, self.value_col],  # type: ignore
            )

        if LIMIT_NI:
            df = df[~df[self.postcode_col].str.startswith("BT")]  # type: ignore

        if not isinstance(df, pd.DataFrame):  # type: ignore
            raise ValueError(f"Expected a DataFrame, got {type(df)}")

        return df

    def create(self, *, force: bool = False):
        dest = dest_folder / f"{self.slug}.json"

        if dest.exists() and not force:
            return

        create_range(
            self.get_df(),
            postcode_col=self.postcode_col,
            value_col=self.value_col,
            output_label=self.slug,
            dest=dest,
        )


class FutureConstituenciesLookupCreator(BaseLookupCreator):
    slug = "pcon_2024"
    postcode_col = "postcode"
    value_col = "short_code"
    df_source = "https://pages.mysociety.org/2025-constituencies/data/uk_parliament_2025_postcode_lookup/latest/postcodes_with_con.parquet"
    test_df_source = df_source


class LocalAuthoritiesLookupCreator(BaseLookupCreator):
    slug = "local_authorities"
    postcode_col = "pcd"
    value_col = "oslaua"
    df_source = Path("data", "raw", "onspd.csv")
    test_df_source = Path("data", "onspd_100000.csv")


class PCONLookupCreator(BaseLookupCreator):
    slug = "pcon_2010"
    postcode_col = "pcd"
    value_col = "pcon"
    df_source = Path("data", "raw", "onspd.csv")
    test_df_source = Path("data", "onspd_100000.csv")


class LSOALookupCreator(BaseLookupCreator):
    slug = "lsoa"
    postcode_col = "pcd"
    value_col = "lsoa11"
    df_source = Path("data", "raw", "onspd.csv")
    test_df_source = Path("data", "onspd_100000.csv")


def generate(force: bool = False):
    creators = [
        FutureConstituenciesLookupCreator(),
        LocalAuthoritiesLookupCreator(),
        PCONLookupCreator(),
        LSOALookupCreator(),
    ]

    for creator in creators:
        print(f"Creating {creator.slug}")
        creator.create(force=force)


if __name__ == "__main__":
    generate(force=True)
