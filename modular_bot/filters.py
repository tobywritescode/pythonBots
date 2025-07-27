# filters.py
import pandas as pd


class BaseFilter:
    """A blueprint for all filter modules."""

    def apply(self, df: pd.DataFrame) -> pd.Series:
        """
        Applies the filter logic to the DataFrame.
        Must be implemented by each specific filter.
        Should return a boolean Series where True means the filter passes.
        """
        raise NotImplementedError("You must implement the apply method!")


class AdxFilter(BaseFilter):
    """
    A regime filter based on the Average Directional Index (ADX).
    It passes only when the market is considered to be trending.
    """

    def __init__(self, adx_period: int = 14, adx_threshold: int = 25):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.adx_col = f'ADX_{self.adx_period}'

    def apply(self, df: pd.DataFrame) -> pd.Series:
        """
        Returns a boolean Series that is True wherever ADX is above the threshold.
        """
        if self.adx_col not in df.columns:
            raise ValueError(f"ADX column '{self.adx_col}' not found in DataFrame. Ensure it's calculated first.")

        print(f"Applying ADX Filter (ADX > {self.adx_threshold})...")
        return df[self.adx_col] > self.adx_threshold

