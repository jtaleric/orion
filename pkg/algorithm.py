"""Module for Generic Algorithm class"""
from abc import ABC, abstractmethod
import pkg.constants as cnsts

class Algorithm(ABC):
    """Generic Algorithm class for algorithm factory
    """

    def __init__(self, matcher, dataframe, test):
        self.matcher = matcher
        self.dataframe = dataframe
        self.test = test

    @abstractmethod
    def output_json(self):
        """Outputs the data in json format
        """
    @abstractmethod
    def output_text(self):
        """Outputs the data in text/tabular format
        """

    def output(self,output_format):
        """Method to select output method

        Args:
            output_format (str): format of the output

        Raises:
            ValueError: In case of unmatched output

        Returns:
            method: return method to be used
        """
        if output_format==cnsts.JSON:
            return self.output_json()
        if output_format==cnsts.TEXT:
            return self.output_text()
        raise ValueError("Unsupported output format {output_format} selected")
