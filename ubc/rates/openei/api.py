import requests
import pandas as pd

from dataclasses import dataclass, field
from urllib.parse import urljoin

from ..abstract import AbstractRate
from .schemas import URDBMeta, Energy, Demand, FlatDemand, Meter


root = "https://api.openei.org"


class UnknownRateStructure(Exception):
    pass


@dataclass
class RateSchedule(AbstractRate):

    apikey: str = field(repr=False)
    openei_schedule_id: str

    _rate: "typing.Any" = field(init=False, repr=False, default=None)
    _energy: "typing.Any" = field(init=False, repr=False, default=None)
    _demand: "typing.Any" = field(init=False, repr=False, default=None)
    _flatdemand: "typing.Any" = field(init=False, repr=False, default=None)
    _meter: "typing.Any" = field(init=False, repr=False, default=None)

    url = urljoin(root, "utility_rates")

    def __post_init__(self):
        self.name = URDBMeta.name.search(self.rate)
        self.description = URDBMeta.description.search(self.rate)

    @property
    def rate(self):
        """Get OpenEI Rate.
        """
        if self._rate is None:
            self._rate = self.load_rate()
        return self._rate

    def load_rate(self):
        params = {
            "api_key": self.apikey,
            "getpage": self.openei_schedule_id,
            "format": "json",
            # Unclear whether 'version' changes response schema.  7 at time of development.
            "version": "latest",
            "detail": "full",
        }
        rate = requests.get(self.url, params=params).json()

        # Python 3.8
        # assert (n := len(rate["items"])) == 1, f"Expected 1 rate, found {n}"
        n = len(rate["items"])
        assert n == 1, f"Expected 1 rate, found {n}"
        return rate["items"][0]

    @property
    def energy(self):
        """Create a month-hour schedule for $/kWh charges.

        Returns:
            DataFrame of rate schedules with granularity of Month, hour of day and weekday.
            Length should be 12 * 24 * 2

        Schema:

            month            int64
            hour            object
            schedule_id      int64
            rate           float64
            is_weekday        bool
        """
        if self._energy is None:
            self._energy = self._parse_tou_schedule(Energy)
        return self._energy

    @property
    def demand(self):
        if self._demand is None:
            self._demand = self._parse_tou_schedule(Demand)
        return self._demand

    def _parse_tou_schedule(self, schema):
        """
        """
        rate = pd.Series(schema.path.search(self.rate))
        # Create empty dataframe to hold rate schedules.
        rate_schedule = pd.DataFrame()
        for _s in (schema.weekend_schedule, schema.weekday_schedule,):

            # Each row represents 1 month
            schedule = pd.DataFrame(_s.search(self.rate)).rename_axis(
                "month").reset_index()
            schedule = pd.melt(schedule, id_vars=[
                "month"], var_name="hour", value_name="schedule_id")

            # Increment 0-indexed months to 1-indexed months
            schedule["month"] += 1

            # Map Rates
            schedule["rate"] = schedule["schedule_id"].map(rate)

            # Add to master rate schedule
            rate_schedule = rate_schedule.append(
                schedule.assign(**_s.metadata), ignore_index=True)

        return rate_schedule

    @property
    def flatdemand(self):
        """Flat demand charges, applicable over a monthly billing period.

        Flat demand charges have only a single, flat value per month.

        Schema:

            month            int64
            schedule_id      int64
            rate           float64
        """
        if self._flatdemand is None:
            self._flatdemand = self._parse_flatdemand_rates()
        return self._flatdemand

    def _parse_flatdemand_rates(self):
        """Get flat demand charges.

        Flat Demand charges are monthly $/kW charges for the maximum 15-min averages.
        """
        rate = pd.Series(FlatDemand.path.search(self.rate))

        schedule = pd.Series(
            FlatDemand.schedule.search(
                self.rate)
        ).rename_axis("month").rename("schedule_id").reset_index()
        schedule["month"] += 1
        schedule["rate"] = schedule["schedule_id"].map(rate)
        return schedule

    def _parse_charge_period(self, attrs, period_attr):
        """

        Args:
            attrs (list[dict]): List of dictionaries from openEI.
            period_attr (str): One of "season" or "period"
        """
        component_parser = {
            "season": lambda x: x.split(":", 1)[0].split("-")[1].title(),
            "period": lambda x: x.split(":", 1)[1].title(),
        }
        try:
            parser = component_parser[period_attr]
        except KeyError:
            raise Exception("Invalid period attribute")

        components = {}

        for rate_attribute in attrs:
            if not len(rate_attribute) == 1:
                raise UnknownRateStructure("Expected 1 attribute per rate attribute list.")
            slug, schedule_id = list(rate_attribute.items())[0]
            # Filter for only seasons/periods.
            # e.g. "TOU-winter:Off-Peak"
            if ":" not in slug:
                continue
            # 0-index the schedule id to be internally consistent
            schedule_id = int(schedule_id) - 1
            period = parser(slug)
            components[schedule_id] = period
        return components

    @property
    def seasons(self):
        energy_attrs = Energy.attrs.search(self.rate)
        if energy_attrs:
            return self._parse_charge_period(energy_attrs, "season") 
        else:
            return {i: f"Season-{i}" for i, rate in Energy(Demand.path.search(self.rate))}

    @property
    def energy_periods(self):
        energy_attrs = Energy.attrs.search(self.rate)
        if energy_attrs:
            return self._parse_charge_period(energy_attrs, "period")
        else:
            return {i: f"Period-{i}" for i, rate in Energy(Demand.path.search(self.rate))}

    @property
    def demand_periods(self):
        """Mapping between schedule ids in rates and human readable period names.
        """
        demand_attrs = Demand.attrs.search(self.rate)
        # Not every rate has descriptive attributes for the demand schedule
        if demand_attrs:
            demand_periods = self._parse_charge_period(demand_attrs, "period")
        else:
            demand_periods = {i: f"Period-{i}" for i, rate in enumerate(Demand.path.search(self.rate))}
        return demand_periods

    @property
    def meter_charge_unit(self):
        rate = self.rate
        return Meter.charge_unit.search(rate)

    @property
    def meter(self):
        rate = self.rate
        return Meter.path.search(rate)