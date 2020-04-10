from abc import ABC, abstractmethod


class AbstractRate(ABC):

    @property
    @abstractmethod
    def energy(self):
        pass

    @property
    @abstractmethod
    def demand(self):
        pass

    @property
    @abstractmethod
    def flatdemand(self):
        pass
