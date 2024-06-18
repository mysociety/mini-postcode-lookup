import typer
from .process import MiniPostcodeLookup, AllowedAreaTypes
from trogon import Trogon  # type: ignore
from typer.main import get_group
from pathlib import Path

app = typer.Typer(help="")


@app.command()
def ui(ctx: typer.Context):
    """
    Open terminal UI
    """
    Trogon(get_group(app), click_context=ctx).run()


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
):
    """
    Add a column to a csv with the area type
    """
    lookup = MiniPostcodeLookup()
    lookup.add_to_csv(
        Path(file_loc),
        area_type=area_type,
        postcode_col=postcode_col,
        include_extra_cols=include_extra_cols,
    )


@app.command()
def generate_lookups(force: bool = False):
    """
    Refresh the lookup tables from source.
    """
    from .generate import generate
    from .get_latest_onspd import get_onspd_if_not_present
    from .extra_values import make_extra_values

    get_onspd_if_not_present()
    generate(force=force)
    make_extra_values(force=force)


if __name__ == "__main__":
    app()
