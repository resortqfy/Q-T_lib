"""Performance Analyzer module.

This module contains the PerformanceEvaluator class for evaluating trading performance.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# 使用另一种方式指定支持中文的字体
try:
    font = fm.FontProperties(family='SimSun')
    plt.rcParams['font.family'] = font.get_family()
except:
    print("警告：无法设置支持中文的字体，图像中的中文可能无法正确显示。")

plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class PerformanceEvaluator:
    """Evaluates the performance of trading strategies."""

    def __init__(self, pnls, total_assets_history):
        self.pnls = pnls
        self.total_assets_history = total_assets_history

    def calculate_metrics(self):
        """Calculate performance metrics like annualized return, Sharpe ratio, and max drawdown."""
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return 0.0, 0.0, 0.0

        # 确保日期列是 datetime 类型
        self.total_assets_history['date'] = pd.to_datetime(self.total_assets_history['date'])
        # 计算总天数
        total_days = (self.total_assets_history['date'].iloc[-1] - self.total_assets_history['date'].iloc[0]).days
        if total_days == 0:
            return 0.0, 0.0, 0.0

        # 计算年化收益率
        initial_assets = self.total_assets_history['assets'].iloc[0]
        final_assets = self.total_assets_history['assets'].iloc[-1]
        annualized_return = (final_assets / initial_assets) ** (365.0 / total_days) - 1 if initial_assets > 0 else 0.0

        # 计算每日收益率
        daily_returns = self.total_assets_history['assets'].pct_change().dropna()
        if len(daily_returns) == 0:
            return annualized_return, 0.0, 0.0

        # 计算年化夏普比率（假设无风险收益率为0）
        annualized_sharpe = daily_returns.mean() * 252 / (daily_returns.std() * (252 ** 0.5)) if daily_returns.std() != 0 else 0.0

        # 计算最大回撤
        self.total_assets_history['peak'] = self.total_assets_history['assets'].cummax()
        self.total_assets_history['drawdown'] = (self.total_assets_history['assets'] - self.total_assets_history['peak']) / self.total_assets_history['peak']
        max_drawdown = self.total_assets_history['drawdown'].min()

        return annualized_return, annualized_sharpe, max_drawdown

    def plot_assets_curve(self):
        """Plot the total assets over time."""
        if self.total_assets_history.empty:
            return

        plt.figure(figsize=(10, 6))
        plt.plot(self.total_assets_history['date'], self.total_assets_history['assets'])
        plt.title('总资产随时间变化曲线')
        plt.xlabel('日期')
        plt.ylabel('总资产 (人民币)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        # 确保输出目录存在
        output_dir = os.path.dirname('assets_curve.png')
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        plt.savefig('assets_curve.png')
        plt.close()

    def plot_pnl_per_trade(self):
        """Plot PNL per trade over time."""
        if self.pnls.empty:
            return

        plt.figure(figsize=(10, 6))
        plt.bar(self.pnls['date'], self.pnls['pnl'], color=['green' if x > 0 else 'red' for x in self.pnls['pnl']])
        plt.title('每次交易的盈亏')
        plt.xlabel('日期')
        plt.ylabel('盈亏 (人民币)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        # 确保输出目录存在
        output_dir = os.path.dirname('pnl_per_trade.png')
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        plt.savefig('pnl_per_trade.png')
        plt.close()

    def plot_performance_metrics(self, annualized_return, sharpe, max_drawdown):
        """Plot performance metrics as a bar chart."""
        metrics = ['年化收益率', '夏普比率', '最大回撤']
        values = [annualized_return * 100, sharpe, max_drawdown * 100]  # 转换为百分比
        colors = ['blue', 'green', 'red']

        plt.figure(figsize=(8, 5))
        plt.bar(metrics, values, color=colors)
        plt.title('交易策略绩效指标')
        plt.ylabel('值 (%)')
        plt.grid(True, axis='y')
        plt.tight_layout()
        # 确保输出目录存在
        output_dir = os.path.dirname('performance_metrics.png')
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        plt.savefig('performance_metrics.png')
        plt.close()

    def generate_detailed_report(self):
        """Generate a detailed performance report."""
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return "无法生成详细报告：数据不足"

        annualized_return, sharpe, max_drawdown = self.calculate_metrics()
        report = []
        report.append("=== 交易系统绩效报告 ===")
        report.append(f"年化收益率: {annualized_return:.2%}")
        report.append(f"夏普比率: {sharpe:.2f}")
        report.append(f"最大回撤: {max_drawdown:.2%}")
        report.append("")
        report.append("--- 总资产统计 ---")
        report.append(f"初始资产: {self.total_assets_history['assets'].iloc[0]:.2f} 人民币")
        report.append(f"最终资产: {self.total_assets_history['assets'].iloc[-1]:.2f} 人民币")
        report.append(f"资产增长: {(self.total_assets_history['assets'].iloc[-1] - self.total_assets_history['assets'].iloc[0]):.2f} 人民币")
        report.append(f"资产增长率: {(self.total_assets_history['assets'].iloc[-1] / self.total_assets_history['assets'].iloc[0] - 1):.2%}")
        report.append("")
        report.append("--- 交易统计 ---")
        if not self.pnls.empty:
            report.append(f"总交易次数: {len(self.pnls)}")
            report.append(f"盈利交易次数: {len(self.pnls[self.pnls['pnl'] > 0])}")
            report.append(f"亏损交易次数: {len(self.pnls[self.pnls['pnl'] < 0])}")
            report.append(f"胜率: {len(self.pnls[self.pnls['pnl'] > 0]) / len(self.pnls):.2%}")
            report.append(f"平均每笔交易盈亏: {self.pnls['pnl'].mean():.2f} 人民币")
            report.append(f"总盈亏: {self.pnls['pnl'].sum():.2f} 人民币")
            report.append(f"总手续费: {self.pnls['fee'].sum():.2f} 人民币")
        else:
            report.append("无交易数据")
        report.append("")
        report.append("--- 回撤分析 ---")
        if 'drawdown' in self.total_assets_history.columns:
            report.append(f"最大回撤金额: {(self.total_assets_history['peak'].max() - self.total_assets_history['assets'].min()):.2f} 人民币")
            max_drawdown_date = self.total_assets_history.loc[self.total_assets_history['drawdown'].idxmin(), 'date']
            report.append(f"最大回撤日期: {max_drawdown_date.strftime('%Y-%m-%d')}")
        else:
            report.append("无回撤数据")
        report.append("")
        report.append("=== 报告结束 ===")
        return "\n".join(report)
