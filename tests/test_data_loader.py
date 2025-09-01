"""Unit tests for DataLoader class."""

import unittest
import pandas as pd
import os
from data.data_loader import DataLoader

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()

    def test_load_market_data(self):
        market_data = self.loader.market_data
        self.assertIsInstance(market_data, pd.DataFrame)
        self.assertIn('open', market_data.columns)
        self.assertIn('date', market_data.index.names)
        self.assertIn('code', market_data.index.names)

    def test_load_trade_data(self):
        trade_before = self.loader.trade_before
        trade_after = self.loader.trade_after
        self.assertIsInstance(trade_before, pd.DataFrame)
        self.assertIsInstance(trade_after, pd.DataFrame)
        self.assertIn('交易时间', trade_before.columns)
        self.assertIn('标的', trade_before.columns)
        self.assertIn('价格', trade_before.columns)
        self.assertIn('数量', trade_before.columns)
        self.assertIn('交易时间', trade_after.columns)
        self.assertIn('标的', trade_after.columns)
        self.assertIn('价格', trade_after.columns)
        self.assertIn('数量', trade_after.columns)

if __name__ == '__main__':
    unittest.main()
