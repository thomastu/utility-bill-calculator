import jmespath


class URDBPath:

    def __init__(self, expression, **meta):
        """Assign an expression to the URDB json path.

        Args:
            expression (str): A valid jmespath expression.
            **meta: key-value pairs associated with the expression.
        """
        self.expression = jmespath.compile(expression)
        self.metadata = meta

    def search(self, data):
        """Proxy method for compiled jmespath search.
        """
        return self.expression.search(data)


class URDBMeta:

    name = URDBPath("name")

    description = URDBPath("description")


class Energy:

    path = URDBPath("energyratestructure[].rate")

    weekend_schedule = URDBPath("energyweekendschedule", is_weekday=False)

    weekday_schedule = URDBPath("energyweekdayschedule", is_weekday=True)


class Demand:

    path = URDBPath("demandratestructure[].rate")

    weekend_schedule = URDBPath("demandweekendschedule", is_weekday=False)

    weekday_schedule = URDBPath("demandweekdayschedule", is_weekday=True)


class FlatDemand:

    path = URDBPath("flatdemandstructure[].rate")

    schedule = URDBPath("flatdemandmonths")


class Meter:
    
    path = URDBPath("fixedchargefirstmeter")