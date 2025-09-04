"""
Q-T_lib 主入口文件
量化交易库的主入口，提供完整的交易系统功能
"""

import logging
import argparse
import pandas as pd
import itertools
from config.settings import TRADING_CONFIG
from core.pnl_calculator import PNLCalculator
from data.data_loader import DataLoader
from strategies.momentum_strategy import TradingStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.rsi_strategy import RSIStrategy
from analysis.performance_analyzer import PerformanceEvaluator

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_assets_curve(pnls: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
    """
    根据逐日 total_pnl（策略级或交易级聚合）生成资产曲线:
    assets(t) = initial_capital + 累计收益(到 t-1)
    这样在当天 PNL 计入之前资产表示开盘前（或交易前）的状态，便于绘图对齐。
    """
    df = pd.DataFrame()
    if pnls.empty:
        return df
    df['date'] = pd.to_datetime(pnls['交易时间'])
    cumulative = pnls['total_pnl'].cumsum().shift(1).fillna(0)
    df['assets'] = initial_capital + cumulative
    # 确保第一行 = initial_capital
    if not df.empty:
        df.loc[df.index[0], 'assets'] = initial_capital
    return df


def evaluate(pnls: pd.DataFrame, total_assets_history: pd.DataFrame):
    """
    统一的评估封装，空数据时返回安全默认值。
    """
    if pnls.empty or total_assets_history.empty:
        logger.warning("PNL 或资产曲线为空，返回默认评估结果。")
        return 0.0, 0.0, 0.0, type("MDD", (), {"ratio": 0.0})
    evaluator = PerformanceEvaluator(pnls, total_assets_history)
    annualized_return, sharpe, vol_ann, mdd_info = evaluator.calculate_metrics()
    return annualized_return, sharpe, vol_ann, mdd_info, evaluator


def optimize_parameters(strategy_name, market_data):
    """
    针对指定策略穷举/网格优化参数，返回最佳参数。
    要求：
    - PerformanceEvaluator.calculate_metrics() 返回 4 个值: (annualized_return, sharpe, vol_ann, mdd_info)
    """
    best_params = None
    best_annualized_return = float('-inf')
    initial_capital = TRADING_CONFIG['initial_capital']

    if strategy_name == 'momentum':
        lookback_periods = TRADING_CONFIG['momentum']['lookback_period']
        top_ns = TRADING_CONFIG['momentum']['top_n']
        param_combinations = list(itertools.product(lookback_periods, top_ns))
        for lookback_period, top_n in param_combinations:
            logger.info(f"[Opt] Momentum: lookback_period={lookback_period}, top_n={top_n}")
            strategy = TradingStrategy(market_data, lookback_period=lookback_period, top_n=top_n)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            assets_curve = build_assets_curve(pnls, initial_capital)
            if pnls.empty:
                continue
            evaluator = PerformanceEvaluator(pnls, assets_curve)
            annualized_return, sharpe, vol_ann, mdd_info = evaluator.calculate_metrics()
            if annualized_return > best_annualized_return:
                best_annualized_return = annualized_return
                best_params = {'lookback_period': lookback_period, 'top_n': top_n}

    elif strategy_name == 'mean_reversion':
        windows = TRADING_CONFIG['mean_reversion']['window']
        thresholds = TRADING_CONFIG['mean_reversion']['threshold']
        param_combinations = list(itertools.product(windows, thresholds))
        for window, threshold in param_combinations:
            logger.info(f"[Opt] MeanReversion: window={window}, threshold={threshold}")
            strategy = MeanReversionStrategy(market_data, window=window, threshold=threshold)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            assets_curve = build_assets_curve(pnls, initial_capital)
            if pnls.empty:
                continue
            evaluator = PerformanceEvaluator(pnls, assets_curve)
            annualized_return, sharpe, vol_ann, mdd_info = evaluator.calculate_metrics()
            if annualized_return > best_annualized_return:
                best_annualized_return = annualized_return
                best_params = {'window': window, 'threshold': threshold}

    elif strategy_name == 'rsi':
        rsi_periods = range(10, 20, 2)
        rsi_overboughts = range(60, 80, 5)
        rsi_oversolds = range(20, 40, 5)
        param_combinations = list(itertools.product(rsi_periods, rsi_overboughts, rsi_oversolds))
        for rsi_period, rsi_overbought, rsi_oversold in param_combinations:
            if rsi_overbought <= rsi_oversold:
                continue
            logger.info(f"[Opt] RSI: period={rsi_period}, overbought={rsi_overbought}, oversold={rsi_oversold}")
            strategy = RSIStrategy(market_data,
                                   rsi_period=rsi_period,
                                   rsi_overbought=rsi_overbought,
                                   rsi_oversold=rsi_oversold)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            assets_curve = build_assets_curve(pnls, initial_capital)
            if pnls.empty:
                continue
            evaluator = PerformanceEvaluator(pnls, assets_curve)
            annualized_return, sharpe, vol_ann, mdd_info = evaluator.calculate_metrics()
            if annualized_return > best_annualized_return:
                best_annualized_return = annualized_return
                best_params = {'rsi_period': rsi_period,
                               'rsi_overbought': rsi_overbought,
                               'rsi_oversold': rsi_oversold}
    else:
        raise ValueError(f"Unknown strategy for optimization: {strategy_name}")

    if best_params is None:
        logger.warning(f"参数优化未找到有效（产生交易）的组合：{strategy_name}")
    else:
        logger.info(f"最优参数 {strategy_name}: {best_params} | 年化: {best_annualized_return:.2%}")
    return best_params


def build_strategy(strategy_name, market_data, best_params):
    """
    根据策略名称与最佳参数构造策略实例。
    """
    if strategy_name == 'momentum':
        if best_params:
            return TradingStrategy(market_data,
                                   lookback_period=best_params['lookback_period'],
                                   top_n=best_params['top_n'])
        return TradingStrategy(market_data)
    elif strategy_name == 'mean_reversion':
        if best_params:
            return MeanReversionStrategy(market_data,
                                         window=best_params['window'],
                                         threshold=best_params['threshold'])
        return MeanReversionStrategy(market_data)
    elif strategy_name == 'rsi':
        if best_params:
            return RSIStrategy(market_data,
                               rsi_period=best_params['rsi_period'],
                               rsi_overbought=best_params['rsi_overbought'],
                               rsi_oversold=best_params['rsi_oversold'])
        return RSIStrategy(market_data)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


def main(strategy_name='momentum', optimize=False):
    loader = DataLoader()
    market_data = loader.market_data
    initial_capital = TRADING_CONFIG['initial_capital']

    best_params = None
    if optimize:
        best_params = optimize_parameters(strategy_name, market_data)

    strategy = build_strategy(strategy_name, market_data, best_params)

    logger.info(f"开始生成交易 (strategy={strategy_name}, optimize={optimize})")
    trades_before, trades_after = strategy.generate_trades()

    logger.info("开始计算 PNL")
    calculator = PNLCalculator(market_data, trades_before, trades_after)
    pnls = calculator.calculate_pnl()

    assets_curve = build_assets_curve(pnls, initial_capital)
    annualized_return, sharpe, vol_ann, mdd_info, evaluator = evaluate(pnls, assets_curve)
    max_drawdown = mdd_info.ratio if hasattr(mdd_info, 'ratio') else 0.0

    # 生成图形（若 evaluator 存在且数据不为空）
    if pnls.empty or assets_curve.empty:
        logger.warning("无交易或无资产曲线，跳过绘图。")
    else:
        evaluator.plot_assets_curve()
        evaluator.plot_pnl_per_trade()
        evaluator.plot_performance_metrics()

    # 生成报告
    if pnls.empty:
        detailed_report = "无交易产生，无法生成详细绩效报告。"
    else:
        detailed_report = evaluator.generate_detailed_report()

    with open('detailed_report.txt', 'w', encoding='utf-8') as f:
        f.write(detailed_report)

    with open('results.txt', 'w', encoding='utf-8') as f:
        f.write(f'策略: {strategy_name}\n')
        f.write(f'是否优化参数: {optimize}\n')
        if best_params:
            f.write(f'最佳参数: {best_params}\n')
        f.write(f'年化收益率: {annualized_return:.2%}\n')
        f.write(f'夏普比率: {sharpe:.2f}\n')
        f.write(f'年化波动率: {vol_ann:.2%}\n')
        f.write(f'最大回撤: {max_drawdown:.2%}\n')
        if not pnls.empty:
            f.write('\n每次交易的PNL:\n')
            for _, row in pnls.iterrows():
                date_val = row['交易时间']
                date_str = date_val.strftime('%Y%m%d') if isinstance(date_val, pd.Timestamp) else str(date_val)
                fee_val = row['fee'] if 'fee' in row else 0.0
                pnl_val = row['total_pnl']
                f.write(f"日期: {date_str}, PNL: {pnl_val:.2f}, 手续费: {fee_val:.4f}\n")

    logger.info("执行完成。结果已写入 results.txt / detailed_report.txt")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Q-T_lib Trading System')
    parser.add_argument('--strategy', type=str, default='momentum',
                        choices=['momentum', 'mean_reversion', 'rsi'],
                        help='Trading strategy to use')
    parser.add_argument('--optimize', action='store_true',
                        help='Whether to optimize strategy parameters')
    args = parser.parse_args()
    main(strategy_name=args.strategy, optimize=args.optimize)
