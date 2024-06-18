from mini_postcode_lookup import MiniPostcodeLookup, generate


def test_postcode_validity():
    """
    Check generated postcodes against the original source data
    """
    creators = [
        generate.FutureConstituenciesLookupCreator(),
        generate.LocalAuthoritiesLookupCreator(),
        generate.PCONLookupCreator(),
        generate.LSOALookupCreator(),
    ]

    plookup = MiniPostcodeLookup()

    for creator in creators:
        df = creator.get_df(test=True)
        df.columns = ["postcode", "original_value"]
        # reduce to random 10000
        df["new_value"] = df["postcode"].apply(  # type: ignore
            lambda x: plookup.get_value(x, area_type=creator.slug)  # type: ignore
        )  # type: ignore
        df["match"] = df["original_value"] == df["new_value"]
        # reduce just to those where the new_value is not None
        df = df[df["new_value"].notnull()]

        # df.to_csv("test.csv")

        # assert there is a length
        assert len(df) > 0

        # assert the new_value is the same as the old one
        assert df["match"].all()  # type: ignore
