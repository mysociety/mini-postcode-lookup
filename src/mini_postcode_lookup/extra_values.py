from pathlib import Path

import pandas as pd

data_folder = Path(__file__).parent / "data" / "lookups"


def get_parlcon_values(force: bool = False):
    dest = data_folder / "pcon_2024_lookup.json"
    if dest.exists() and not force:
        return

    df = pd.read_parquet(
        "https://pages.mysociety.org/2025-constituencies/data/parliament_con_2025/0.1.4/parl_constituencies_2025.parquet"
    )

    key = "short_code"
    to_keep = ["name", "name_cy", "gss_code", "three_code"]
    df = df[to_keep + [key]].set_index(key)  # type: ignore

    # add prefix of "parlcon_2024_" to the columns

    df = df.rename(columns={col: f"parlcon_2024_{col}" for col in df.columns})

    if not data_folder.exists():
        data_folder.mkdir(parents=True)

    # convert to json
    df.to_json(dest, orient="index")  # type: ignore


def get_la_values(force: bool = False):
    dest = data_folder / "local_authorities_lookup.json"
    if (dest).exists() and not force:
        return

    df = pd.read_parquet(
        "https://pages.mysociety.org/uk_local_authority_names_and_codes/data/uk_la_past_current/latest/uk_local_authorities_current.parquet"
    )

    key = "local-authority-code"
    to_keep = ["official-name", "nice-name", "gss-code"]
    df = df[to_keep + [key]].set_index(key)  # type: ignore

    # add prefix of "parlcon_2024_" to the columns

    df = df.rename(columns=lambda x: "la_" + x.replace("-", "_"))

    if not data_folder.exists():
        data_folder.mkdir(parents=True)

    # convert to json
    df.to_json(dest, orient="index")  # type: ignore


def make_extra_values(force: bool = False):
    get_parlcon_values(force)
    get_la_values(force)
