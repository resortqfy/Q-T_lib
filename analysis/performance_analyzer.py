"""
Performance Analyzer module (enhanced).

提供交易绩效评估：
- 年化收益率（基于交易日）
- 年化夏普比率（可指定无风险利率）
- 最大回撤（比例 + 金额 + 起止日期）
- 生成图表（资产曲线、单笔交易PNL、指标）
- 生成详细文本报告
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from dataclasses import dataclass
from typing import Tuple, Optional, Dict

# ================= 字体与全局 Matplotlib 设置 =================
try:
  font = fm.FontProperties(family='SimSun')
  plt.rcParams['font.family'] = font.get_name()
except Exception:
  print("警告：无法设置中文字体，图像中的中文可能无法正确显示。")
plt.rcParams['axes.unicode_minus'] = False

@dataclass
class MaxDrawdownInfo:
    ratio: float                # 负数，例如 -0.23
    amount: float               # 金额（正数）
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp

class PerformanceEvaluator:
    """
    Evaluates the performance of trading strategies.
    
    Parameters
    ----------
    pnls : pd.DataFrame
        期望包含列:
          - 交易时间 (str or datetime)
          - total_pnl (float)  单笔净PNL
          - fee (float, 可选)   手续费
    total_assets_history : pd.DataFrame
        期望包含列:
          - date (str or datetime)
          - assets (float)
    risk_free_rate : float
        年化无风险收益率（默认 0）。夏普比率使用。
    trading_days_per_year : int
        年化使用的交易日数，默认 252。
    """
    def __init__(self,
                 pnls: pd.DataFrame,
                 total_assets_history: pd.DataFrame,
                 risk_free_rate: float = 0.0,
                 trading_days_per_year: int = 252):
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        
        # 复制，避免外部副作用
        self.pnls = pnls.copy() if pnls is not None else pd.DataFrame()
        self.total_assets_history = total_assets_history.copy() if total_assets_history is not None else pd.DataFrame()
        
        # 预处理
        if not self.total_assets_history.empty:
            self.total_assets_history['date'] = pd.to_datetime(self.total_assets_history['date'])
            self.total_assets_history = self.total_assets_history.sort_values('date').reset_index(drop=True)
        if not self.pnls.empty:
            self.pnls['交易时间'] = pd.to_datetime(self.pnls['交易时间'])
            self.pnls = self.pnls.sort_values('交易时间').reset_index(drop=True)

    # ================== 核心指标计算 ==================
    def _compute_daily_returns(self) -> pd.Series:
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return pd.Series(dtype=float)
        rets = self.total_assets_history['assets'].pct_change()
        return rets.dropna()

    def _annualized_return(self) -> float:
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return 0.0
        initial = self.total_assets_history['assets'].iloc[0]
        final = self.total_assets_history['assets'].iloc[-1]
        if initial <= 0:
            return 0.0
        daily_returns = self._compute_daily_returns()
        n = len(daily_returns)  # 交易日个数
          # 防止 n=0
        if n == 0:
            return 0.0
        return (final / initial) ** (self.trading_days_per_year / n) - 1

    def _annualized_sharpe(self) -> float:
        daily_returns = self._compute_daily_returns()
        if daily_returns.empty:
            return 0.0
        # 日无风险收益率
        rf_daily = (1 + self.risk_free_rate) ** (1 / self.trading_days_per_year) - 1
        excess = daily_returns - rf_daily
        std = excess.std(ddof=1)
        if std == 0 or np.isnan(std):
            return 0.0
        return excess.mean() / std * np.sqrt(self.trading_days_per_year)

    def _max_drawdown(self) -> MaxDrawdownInfo:
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return MaxDrawdownInfo(ratio=0.0, amount=0.0,
                                   peak_date=pd.NaT, trough_date=pd.NaT)
        assets = self.total_assets_history['assets']
        peaks = assets.cummax()
        drawdown = assets / peaks - 1.0  # 负数
        trough_idx = drawdown.idxmin()
        trough_date = self.total_assets_history.loc[trough_idx, 'date']
        # 峰值在该谷值之前（含当天）最大资产位置
        peak_slice = self.total_assets_history.loc[:trough_idx]
        peak_idx = peak_slice['assets'].idxmax()
        peak_date = self.total_assets_history.loc[peak_idx, 'date']
        ratio = drawdown.min()
        amount = self.total_assets_history.loc[peak_idx, 'assets'] - self.total_assets_history.loc[trough_idx, 'assets']
        return MaxDrawdownInfo(ratio=ratio, amount=amount, peak_date=peak_date, trough_date=trough_date)

    def calculate_metrics(self) -> Tuple[float, float, float, MaxDrawdownInfo]:
        """
        Returns
        -------
        annual_ret : float
        sharpe : float
        vol_annual : float  年化波动率
        mdd_info : MaxDrawdownInfo
        """
        daily_returns = self._compute_daily_returns()
        annual_ret = self._annualized_return()
        sharpe = self._annualized_sharpe()
        if daily_returns.empty:
            vol_annual = 0.0
        else:
            vol_annual = daily_returns.std(ddof=1) * np.sqrt(self.trading_days_per_year)
        mdd_info = self._max_drawdown()
        return annual_ret, sharpe, vol_annual, mdd_info

    # ================ 辅助分析 =================
    def get_drawdown_table(self) -> pd.DataFrame:
        """
        返回每日回撤表（日期, 资产, 峰值, 回撤比例）。
        """
        if self.total_assets_history.empty:
            return pd.DataFrame()
        df = self.total_assets_history.copy()
        df['peak'] = df['assets'].cummax()
        df['drawdown'] = df['assets'] / df['peak'] - 1.0
        return df[['date', 'assets', 'peak', 'drawdown']]

    # ================== 图表 ==================
    def plot_assets_curve(self, filename: str = 'assets_curve.png'):
        if self.total_assets_history.empty:
            return
        plt.figure(figsize=(10, 5))
        plt.plot(self.total_assets_history['date'], self.total_assets_history['assets'], label='资产')
        # 叠加峰值
        plt.plot(self.total_assets_history['date'],
                 self.total_assets_history['assets'].cummax(),
                 linestyle='--', alpha=0.6, label='历史峰值')
        plt.title('总资产曲线')
        plt.xlabel('日期')
        plt.ylabel('资产')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        self._ensure_dir(filename)
        plt.savefig(filename)
        plt.close()

    def plot_pnl_per_trade(self, filename: str = 'pnl_per_trade.png'):
        """Plot PNL per trade over time."""
        if self.pnls.empty:
            return
        
        df = self.pnls.copy()
        x = df['交易时间']
        y = df['total_pnl']
        num_trades = len(df)
        
        # 优化图表尺寸 - 避免过度拉伸
        fig_width = min(max(12, num_trades * 0.08), 24)  # 限制最大宽度为24
        fig_height = 8  # 固定合适的高度
        
        plt.figure(figsize=(fig_width, fig_height), dpi=100)
        
        # 使用索引位置而非日期，避免x轴拥挤
        x_positions = range(len(x))
        
        # 专业配色和样式
        colors = ['#2E8B57' if pnl > 0 else '#DC143C' for pnl in y]  # 深绿和深红
        bars = plt.bar(x_positions, y, color=colors, width=0.8, alpha=0.8, 
                        edgecolor='white', linewidth=0.5)
        
        # 添加零线
        plt.axhline(0, color='black', linewidth=1.2, alpha=0.7)
        
        # 标题和标签
        plt.title('每次交易的盈亏分析', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('交易序号', fontsize=12, fontweight='bold')
        plt.ylabel('盈亏 (人民币)', fontsize=12, fontweight='bold')
        
        # 优化网格
        plt.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # 智能x轴标签显示
        if num_trades <= 20:
            # 少量交易：显示所有序号
            plt.xticks(x_positions, [f'{i+1}' for i in x_positions], fontsize=10)
        elif num_trades <= 50:
            # 中等数量：每隔几个显示
            step = max(1, num_trades // 10)
            indices = range(0, num_trades, step)
            plt.xticks(indices, [f'{i+1}' for i in indices], fontsize=9)
        else:
            # 大量交易：显示关键点
            step = max(1, num_trades // 8)
            indices = range(0, num_trades, step)
            if indices[-1] != num_trades - 1:
                indices = list(indices) + [num_trades - 1]
            plt.xticks(indices, [f'{i+1}' for i in indices], fontsize=9)
        
        # 添加统计信息
        total_pnl = sum(y)
        win_count = sum(1 for pnl in y if pnl > 0)
        loss_count = sum(1 for pnl in y if pnl < 0)
        win_rate = (win_count / num_trades * 100) if num_trades > 0 else 0
        avg_win = sum(pnl for pnl in y if pnl > 0) / win_count if win_count > 0 else 0
        avg_loss = sum(pnl for pnl in y if pnl < 0) / loss_count if loss_count > 0 else 0
        
        # 统计信息文本框
        stats_text = (f'总交易: {num_trades} | 总PNL: {total_pnl:.0f}元 | '
                    f'胜率: {win_rate:.1f}% ({win_count}胜/{loss_count}负)\n'
                    f'平均盈利: {avg_win:.0f}元 | 平均亏损: {avg_loss:.0f}元')
        
        plt.figtext(0.5, 0.02, stats_text, ha='center', fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.8', facecolor='lightblue', alpha=0.8))
        
        # Y轴格式化
        plt.ticklabel_format(style='plain', axis='y')
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.18)  # 为统计信息留出更多空间
        
        # 保存图片
        self._ensure_dir(filename)
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

    def plot_performance_metrics(self,
                                 filename: str = 'performance_metrics.png',
                                 use_percent: bool = True):
        ann_ret, sharpe, vol_ann, mdd = self.calculate_metrics()
        metrics = []
        values = []
        if use_percent:
            metrics.extend(['年化收益(%)', '年化波动(%)', '最大回撤(%)', '夏普'])
            values.extend([
                ann_ret * 100,
                vol_ann * 100,
                mdd.ratio * 100,
                sharpe
            ])
        else:
            metrics.extend(['年化收益', '年化波动', '最大回撤', '夏普'])
            values.extend([ann_ret, vol_ann, mdd.ratio, sharpe])
        colors = ['#1f77b4', '#ff7f0e', '#d62728', '#2ca02c']
        plt.figure(figsize=(8, 5))
        plt.bar(metrics, values, color=colors)
        plt.title('绩效指标')
        plt.grid(True, axis='y', alpha=0.3)
        for i, v in enumerate(values):
            plt.text(i, v, f"{v:.2f}", ha='center', va='bottom', fontsize=9)
        plt.tight_layout()
        self._ensure_dir(filename)
        plt.savefig(filename)
        plt.close()

    # ================== 报告 ==================
    def generate_detailed_report(self) -> str:
        if self.total_assets_history.empty or len(self.total_assets_history) < 2:
            return "无法生成详细报告：资产数据不足"
        ann_ret, sharpe, vol_ann, mdd = self.calculate_metrics()
        report = []
        report.append("=== 交易策略绩效报告 ===")
        # 基础资产变化
          # 资产段
        initial = self.total_assets_history['assets'].iloc[0]
        final = self.total_assets_history['assets'].iloc[-1]
        growth = final - initial
        report.append("【资产表现】")
        report.append(f"初始资产: {initial:,.2f}")
        report.append(f"最终资产: {final:,.2f}")
        report.append(f"绝对增长: {growth:,.2f}  (增长率: {growth / initial:.2%})")
        report.append("")
        # 指标
        report.append("【核心指标】")
        report.append(f"年化收益率: {ann_ret:.2%}")
        report.append(f"年化波动率: {vol_ann:.2%}")
        report.append(f"夏普比率: {sharpe:.2f} (Rf年化={self.risk_free_rate:.2%})")
        report.append(f"最大回撤: {mdd.ratio:.2%}")
        if pd.notna(mdd.peak_date):
            report.append(f"最大回撤金额: {mdd.amount:,.2f}")
            report.append(f"回撤区间: {mdd.peak_date.date()} → {mdd.trough_date.date()}")
        report.append("")
        # 交易统计
        report.append("【交易统计】")
        if not self.pnls.empty and 'total_pnl' in self.pnls.columns:
            pnl_series = self.pnls['total_pnl']
            fees = self.pnls['fee'] if 'fee' in self.pnls.columns else pd.Series([0]*len(pnl_series))
            win_mask = pnl_series > 0
            lose_mask = pnl_series < 0
            wins = pnl_series[win_mask]
            loses = pnl_series[lose_mask]
            total_trades = len(pnl_series)
            win_trades = win_mask.sum()
            lose_trades = lose_mask.sum()
            report.append(f"总交易次数: {total_trades}")
            report.append(f"盈利笔数: {win_trades}  亏损笔数: {lose_trades}")
            win_rate = win_trades / total_trades if total_trades else 0
            report.append(f"胜率: {win_rate:.2%}")
            avg_win = wins.mean() if not wins.empty else 0.0
            avg_loss = loses.mean() if not loses.empty else 0.0
            report.append(f"平均盈利: {avg_win:,.2f}")
            report.append(f"平均亏损: {avg_loss:,.2f}")
            if avg_loss != 0:
                report.append(f"盈亏比(平均盈利/绝对平均亏损): {(avg_win / abs(avg_loss)):.2f}")
            report.append(f"最大单笔盈利: {pnl_series.max():,.2f}")
            report.append(f"最大单笔亏损: {pnl_series.min():,.2f}")
            report.append(f"累计净PNL: {pnl_series.sum():,.2f}")
            report.append(f"累计手续费: {fees.sum():,.2f}")
        else:
            report.append("无交易数据")
        report.append("")
        # 回撤细节
        report.append("【回撤分析】")
        if pd.notna(mdd.peak_date):
            dd_table = self.get_drawdown_table()
            worst5 = dd_table.nsmallest(5, 'drawdown')
            report.append("最深回撤阶段（前5行，drawdown为负数）:")
            for _, r in worst5.iterrows():
                report.append(f"  {r['date'].date()}  资产 {r['assets']:.2f}  峰值 {r['peak']:.2f}  回撤 {r['drawdown']:.2%}")
        else:
            report.append("回撤数据不足")
        report.append("")
        report.append("=== 报告结束 ===")
        return "\n".join(report)

    # ================== 工具方法 ==================
    @staticmethod
    def _ensure_dir(path: str):
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

