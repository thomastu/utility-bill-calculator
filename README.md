# Quickstart

```
pip install ubc
```

```
import pandas as pd
import numpy as np

from ubc.rates.openei import OpenEI
from ubc.calculator import SingleSite

# Register for an API Key @ https://openei.org/services/api/signup/
URDB_APIKEY = "changeme"

rate = OpenEI(
    URDB_APIKEY,
    "5e17b4ef5457a3556573e3b0", # 2020 PG&E B19R
)

calculator = SingleSite(rate)

# Generate some fake load data indexed by a pandas DatetimeIndex
# The data will be resampled regardless of what frequency you pass in
# so you do not necessarily need to have 8760 data if you have something more or less granular.

idx = pd.date_range(start="Jan 1st, 2019", end="Dec 31st, 2019 23:59:00", freq="30 min")
load = pd.Series(pd.np.random.random(len(idx)), index=idx)
load.name = "kWh"

calculator.calculate_energy_charges(load)
calculator.calculate_demand_charges(load)
calculator.calculate_flatdemand_charges(load)
calculator.calculate_meter_charges(load)
```

# Disclaimer

This package was developed rapidly for an academic context to automate some otherwise tedious tasks in a take-home exam.
There are currently no tests, or a guarantee that all bill rates have been appropriately modeled.

This was developed for use with a B19 (Option R) rate from PG&E.
