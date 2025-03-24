from typing import Dict, List, Optional, Tuple
import numpy as np

from xopt.errors import SeqGeneratorError
from xopt.generator import Generator
import pandas as pd


class SequentialGenerator(Generator):
    """
    A generator that runs a sequential optimization algorithm, such as Nelder-Mead, extremum seeking, RCDS, etc.

    Generally, these algorithms need an internal state to keep track of the optimization process.
    Additionally, users cannot interrupt the optimization process to add new points.
    These algorithms will start from the last point in the history.
    """

    is_active: bool = False
    _last_candidate: Optional[List[Dict[str, float]]] = None
    _data_set: bool = False

    def add_data(self, new_data: pd.DataFrame):
        """
        Add new data to the generator.

        Parameters
        ----------
        new_data : pd.DataFrame
            The new data to add.

        Raises
        ------
        ValueError
            If the generator is active but no candidate was generated, or if the new data does not contain the last candidate.
        """
        # if the generator is active then the new data must contain the last candidate
        if self.is_active:
            if self._last_candidate is None:
                raise SeqGeneratorError(
                    "Generator is active, but no candidate was generated. Cannot add data."
                )
            if len(new_data) > 1:
                raise SeqGeneratorError(
                    "Cannot add more than one data point when generator is active."
                )
            else:
                # check if the last candidate is in the new data
                self.validate_point(self._last_candidate[0])

        # do not call super, this will likely need to be customized for some generators
        if self.data is not None:
            self.data = pd.concat([self.data, new_data], axis=0)
        else:
            self.data = new_data

        # update internal state of the generator
        self._add_data(new_data)

    def validate_point(self, point: Dict[str, float]):
        """determine if a point was generated by the generator"""
        last_candidate = np.array(
            [self._last_candidate[0][ele] for ele in self.vocs.variable_names]
        )
        point_variables = np.array(
            [point[ele] for ele in self.vocs.variable_names]
        ).flatten()
        if not np.allclose(last_candidate, point_variables, atol=0.0, rtol=1e-6):
            raise SeqGeneratorError(
                "Cannot add data that was not generated by the generator when generator is active. "
                "Call reset() to reset the generator first in order to add data via other methods."
            )

    def _add_data(self, new_data: pd.DataFrame):
        """
        Customization of adding data to the algorithm.

        Parameters
        ----------
        new_data : pd.DataFrame
            The new data to add.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            "Sequential generators must implement _add_data method."
        )

    def set_data(self, data: pd.DataFrame):
        """
        Set the full dataset for the generator. Typically only used when loading from a save file. This skips active
        generator lockout.

        Parameters
        ----------
        data : pd.DataFrame
            The data to set.
        """
        # TODO: make a flag for generator that support multiple data sets
        if self._data_set:
            raise ValueError("Data has already been initialized for this generator.")
        self._set_data(data)
        self._data_set = True

    def _set_data(self, data: pd.DataFrame):
        raise NotImplementedError(
            "Sequential generators must implement _set_data method."
        )

    def generate(self, n_candidates: int = 1) -> dict:
        """
        Generate a new candidate point.

        Parameters
        ----------
        n_candidates : int, optional
            Number of candidates to generate, by default 1.

        Returns
        -------
        dict
            A dictionary representing the candidate point.

        Raises
        ------
        ValueError
            If more than one candidate is requested.
        """
        # we cannot generate more than one candidate at a time
        if n_candidates > 1:
            raise SeqGeneratorError(
                "Sequential generators can only generate one candidate at a time."
            )

        # if the generator is not active, we need to start it
        if not self.is_active:
            candidate = self._generate(True)
            self.is_active = True
        else:
            candidate = self._generate()

        # need to store the candidate to validate adding data to the generator
        self._last_candidate = candidate

        return candidate

    def _generate(self, first_gen: bool = False) -> Optional[List[Dict[str, float]]]:
        """
        Generate a new candidate point.

        Returns
        -------
        dict
            A dictionary representing the candidate point.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            "Sequential generators must implement _generate method."
        )

    def reset(self):
        """
        Reset the generator.
        """
        self.is_active = False
        self._last_candidate = None
        self._reset()

    def _reset(self):
        """
        Reset the generator.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError("Sequential generators must implement _reset method.")

    def _get_initial_point(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get the initial x0, f0 value from data.

        Returns
        -------
        np.ndarray
            The initial point as a NumPy array.
        np.ndarray
            The corresponding function value as a NumPy array.

        Raises
        ------
        ValueError
            If there are no points in the data.
        """
        # get the initial x0 value from data
        if self.data is None or len(self.data) == 0:
            raise ValueError(
                f"At least one point is required to start {self.__class__.__name__}, add data manually or via Xopt.random_evaluate() or Xopt.evaluate_data()"
            )
        x0 = self.data.iloc[-1][self.vocs.variable_names].to_numpy(dtype=float)
        f0 = self.data.iloc[-1][self.vocs.objective_names].to_numpy(dtype=float)
        return x0, f0
