import pandas as pd
from dataclasses import dataclass

from .calculator import SingleSite


@dataclass
class MonthlyBillReport:

    load: pd.Series
    name: str
    calculator: SingleSite

    def __post_init__(self):
        self.load = self.load.copy()
        self.load.name = self.load.name or "kW"
        self.load.index.name = self.load.index.name or "timestamp"

    @property
    def seasonal_load(self):
        rate_grain = ["is_weekday", "month", "hour", ]
        load = self.load.reset_index()

        # Load is a function of month, hour, is_weekday
        load_grain = [
            ~load[self.load.index.name].dt.dayofweek.isin([5, 6]),
            load[self.load.index.name].dt.month,
            load[self.load.index.name].dt.hour,
        ]

        load = load.merge(
            self.calculator.schedule.energy,
            right_on=rate_grain,
            left_on=load_grain,
            how="left"
        )
        load["season"] = load["schedule_id"].map(
            self.calculator.schedule.seasons)

        return load[[self.load.name, self.load.index.name, "season"]].set_index(self.load.index.name)

    @property
    def demand(self):
        """
        Aggregates all demand charges and values to a single value.
        """
        cols = {"cost": "Demand ($)", self.load.name: "Demand (kW)"}
        flatdemand_charges = self.calculator.calculate_flatdemand_charges(self.load).rename(
            columns=cols
        )
        flat_charges = flatdemand_charges[list(cols.values())]

        cols = {"cost": "Demand ($)", self.load.name: "Demand (kW)"}
        peak_charges = self.calculator.calculate_demand_charges(self.load).rename(
            columns=cols
        ).rename(
            columns=self.calculator.schedule.demand_periods,
            level=1
        )

        for dup_col in peak_charges.columns[peak_charges.columns.duplicated()]:
            S = peak_charges[dup_col].sum()
            peak_charges.drop(columns=dup_col, inplace=True)
            peak_charges[dup_col] = S

        peak_charges = peak_charges[list(cols.values())]
        peak_charges.columns = peak_charges.columns.map(' - '.join)
        return peak_charges.join(flat_charges)

    @property
    def energy(self):
        energy_cols = {"cost": "Energy ($)", "kWh": "Energy (kWh)"}
        energy_charges = self.calculator.calculate_energy_charges(
            self.load.rename("kWh")).rename(columns=energy_cols)
        return energy_charges[list(energy_cols.values())].resample("M").sum()

    @property
    def meter(self):
        meter_charges = self.calculator.calculate_meter_charges(
            self.load).rename("Meter ($)")
        return meter_charges

    @property
    def monthly(self):
        monthly = self.energy.join(self.demand).join(self.meter)
        billing_cols = monthly.columns[monthly.columns.str.contains(r"\(\$\)")]
        monthly["Total ($)"] = monthly[billing_cols].sum(
            axis=1).rename("Total ($)")
        return monthly.rename_axis("Month")

    @property
    def annual(self):
        return self.monthly.sum(axis=0).rename(self.name)
