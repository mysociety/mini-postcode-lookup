# mini-postcode-lookup

Approach for small lookup files for postcode geographies.

Don't use NI postcodes except for statistical/internal business uses. See [ONSPD source](https://geoportal.statistics.gov.uk/datasets/a2f8c9c5778a452bbf640d98c166657c).


## Install tool
```
pip install git+https://github.com/mysociety/mini-postcode-lookup
```

## Example of adding deprivation data to a dataset

```python

import pandas as pd
from mini_postcode_lookup import AllowedAreaTypes, MiniPostcodeLookup

df = pd.read_csv(...) # source here with a postcode column

deprivation_df = pd.read_csv("https://pages.mysociety.org/composite_uk_imd/data/uk_index/latest/UK_IMD_E.csv")[["lsoa", "UK_IMD_E_pop_decile"]]

lookup = MiniPostcodeLookup()

df["lsoa"] = lookup.get_series(df["postcode"], area_type=AllowedAreaTypes.LSOA)
df = df.merge(deprivation_df)

```