from pathlib import Path

import typer
from trogon.typer import init_tui  # type: ignore

from .process import AllowedAreaTypes, IMDInclude, MiniPostcodeLookup

app = typer.Typer(help="")

init_tui(app)


@app.command()
def get_postcode(
    postcode: str, area_type: AllowedAreaTypes = AllowedAreaTypes.PCON_2024
):
    """
    Get the ID for an area type
    """
    lookup = MiniPostcodeLookup()
    typer.echo(lookup.get_value(postcode, area_type=area_type))


@app.command()
def add_to_csv(
    file_loc: str,
    area_type: AllowedAreaTypes = AllowedAreaTypes.PCON_2024,
    postcode_col: str = "postcode",
    include_extra_cols: bool = False,
    include_imd: IMDInclude = IMDInclude.NONE,
    remove_postcode: bool = False,
):
    """
    Add a column to a csv with the area type
    """

    if include_imd != IMDInclude.NONE and area_type != AllowedAreaTypes.LSOA:
        raise ValueError("IMD can only be included for LSOA")

    lookup = MiniPostcodeLookup()
    lookup.add_to_csv(
        Path(file_loc),
        area_type=area_type,
        postcode_col=postcode_col,
        include_extra_cols=include_extra_cols,
        include_imd=include_imd,
        remove_postcode=remove_postcode,
    )


@app.command()
def generate_lookups(force: bool = False):
    """
    Refresh the lookup tables from source.
    """
    from .extra_values import make_extra_values
    from .generate import generate
    from .get_latest_onspd import get_onspd_if_not_present

    get_onspd_if_not_present()
    generate(force=force)
    make_extra_values(force=force)


if __name__ == "__main__":
    app()
