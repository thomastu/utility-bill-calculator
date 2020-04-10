from ubc.rates.openei.api import RateSchedule
from dataclasses import dataclass


@dataclass
class BillCalculator:
    """Single-Site Bill Calculator
    """

    schedule: RateSchedule

    def calculate_energy_charges(self, load):
        """
        Args:
            load (pd.Series):  Time indexed series of load data in kWh.
        """
        load = load.copy()
        load.rename(load.name or "kWh", inplace=True)
        load.rename_axis(load.index.name or "timestamp", inplace=True)

        load_grain = [
            ~load.index.dayofweek.isin([5, 6]),
            load.index.month,
            load.index.hour
        ]
        schedule_grain = ["is_weekday", "month", "hour"]

        # Assign rates to the provided load data.
        rates = self.schedule.energy.merge(
            load.reset_index(),
            right_on=load_grain,
            left_on=schedule_grain,
            how="right"
        )[[load.index.name, load.name, "rate"]]

        rates["cost"] = rates[load.name] * rates["rate"]
        rates.rename(columns={"rate": f"{load.name}_rate"}, inplace=True)
        return rates.set_index(load.index.name).sort_index()

    def calculate_demand_charges(self, load):
        """
        Args:
            load (pd.Series):  Time indexed series of load data in kW.
        """
        load = load.copy()
        load.rename(load.name or "kW", inplace=True)
        load.rename_axis(load.index.name or "timestamp", inplace=True)

        # Resample to 15min intervals and then upsample to month level taking maximum demand
        load = load.resample("15 min").mean().fillna(method="pad").resample("H").max()

        load_grain = [
            ~load.index.dayofweek.isin([5, 6]),
            load.index.month,
            load.index.hour
        ]
        schedule_grain = ["is_weekday", "month", "hour"]

        # Assign rates to the provided load data.
        rates = self.schedule.demand.merge(
            load.reset_index(),
            right_on=load_grain,
            left_on=schedule_grain,
            how="right"
        )[[load.index.name, load.name, "rate", "schedule_id"]]
        # Calculate max demand over 15 min. period for each month
        
        rates[f"cost"] = rates[load.name] * rates["rate"]
        rates = rates.set_index(load.index.name).sort_index()
        rates.rename(columns={"rate": f"{load.name}_rate"}, inplace=True)
        # Finally, only take the maximum demand charge in each billing period for each schedule ID
        # Each schedule ID represents a different demand charge type (part peak, full peak)
        rates = rates.pivot(
            columns="schedule_id", values=[load.name, f"{load.name}_rate", f"cost"])
        return rates.resample("M").max()


    def calculate_flatdemand_charges(self, load):
        """
        Args:
            load (pd.Series):  Time indexed series of load data in kW.
        """
        load = load.copy()
        load.rename(load.name or "kW", inplace=True)
        load.rename_axis(load.index.name or "timestamp", inplace=True)

        # Resample to 15min intervals and then upsample to month level taking maximum demand
        load = load.resample("15 min").mean().fillna(method="pad").resample("M").max()

        load_grain = [load.index.month]
        schedule_grain = ["month"]

        # Assign rates to the provided load data.
        rates = self.schedule.flatdemand.merge(
            load.reset_index(),
            right_on=load_grain,
            left_on=schedule_grain,
            how="right"
        )[[load.index.name, load.name, "rate"]]

        # Calculate max demand over 15 min. period for each month
        rates["cost"] = rates[load.name] * rates["rate"]
        rates.rename(columns={"rate": f"{load.name}_rate"}, inplace=True)
        return rates.set_index(load.index.name).sort_index()
    
    def calculate_total(self, load_kw, interval=1):
        """
        Args:
            load_kw (pd.Series): timestamp series of demand data.
            interval (float): Fraction of an hour for timestamp.
        """
        energy_charges = self.calculate_energy_charges(load_kw*interval)["cost"].resample("M").sum()
        demand_charges = self.calculate_demand_charges(load_kw)["cost"].sum(axis=1)
        flatdemand_charges = self.calculate_flatdemand_charges(load_kw)["cost"]
        return (energy_charges + demand_charges + flatdemand_charges).rename("total_cost")
