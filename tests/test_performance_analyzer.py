"""Unit tests for PerformanceEvaluator class."""

import unittest
import pandas as pd
from analysis.performance_analyzer import PerformanceEvaluator

class TestPerformanceEvaluator(unittest.TestCase):
    def setUp(self):
        # 创建测试数据
        pnls = pd.DataFrame({
            'date': [pd.to_datetime('2023-01-01'), pd.to_datetime('2023-01-02'), pd.to_datetime('2023-01-03')],
            'pnl': [100, -50, 200],
            'fee': [10, 5, 20]
        })
        total_assets_history = pd.DataFrame({
            'date': [pd.to_datetime('2023-01-01'), pd.to_datetime('2023-01-02'), pd.to_datetime('2023-01-03')],
            'assets': [100100, 100050, 100250]
        })
        self.evaluator = PerformanceEvaluator(pnls, total_assets_history)

    def test_calculate_metrics(self):
        annualized_return, sharpe, max_drawdown = self.evaluator.calculate_metrics()
        self.assertIsInstance(annualized_return, float)
        self.assertIsInstance(sharpe, float)
        self.assertIsInstance(max_drawdown, float)

    def test_plot_assets_curve(self):
        # 测试绘图功能不会抛出异常
        try:
            self.evaluator.plot_assets_curve()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"plot_assets_curve raised an exception: {e}")

if __name__ == '__main__':
    unittest.main()
