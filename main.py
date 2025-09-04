"""Q-T_lib 主入口文件

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

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def optimize_parameters(strategy_name, market_data):
    """Optimize parameters for the given strategy."""
    best_params = None
    best_annualized_return = float('-inf')
    
    if strategy_name == 'momentum':
        lookback_periods = TRADING_CONFIG['momentum']['lookback_period']
        top_ns = TRADING_CONFIG['momentum']['top_n']
        param_combinations = list(itertools.product(lookback_periods, top_ns))
        for lookback_period, top_n in param_combinations:
            logger.info(f"Testing Momentum Strategy with lookback_period={lookback_period}, top_n={top_n}")
            strategy = TradingStrategy(market_data, lookback_period=lookback_period, top_n=top_n)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            total_assets_history = pd.DataFrame()
            if not pnls.empty:
                total_assets_history['date'] = pd.to_datetime(pnls['交易时间'])
                total_assets_history['assets'] = TRADING_CONFIG['initial_capital'] + pnls['total_pnl'].cumsum()
            evaluator = PerformanceEvaluator(pnls, total_assets_history)
            annualized_return, *_ = evaluator.calculate_metrics()
            if annualized_return > best_annualized_return:
                best_annualized_return = annualized_return
                best_params = {'lookback_period': lookback_period, 'top_n': top_n}
    elif strategy_name == 'mean_reversion':
        windows = TRADING_CONFIG['mean_reversion']['window']
        thresholds = TRADING_CONFIG['mean_reversion']['threshold']
        param_combinations = list(itertools.product(windows, thresholds))
        for window, threshold in param_combinations:
            logger.info(f"Testing Mean Reversion Strategy with window={window}, threshold={threshold}")
            strategy = MeanReversionStrategy(market_data, window=window, threshold=threshold)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            total_assets_history = pd.DataFrame()
            if not pnls.empty:
                total_assets_history['date'] = pd.to_datetime(pnls['交易时间'])
                total_assets_history['assets'] = TRADING_CONFIG['initial_capital'] + pnls['total_pnl'].cumsum()
            evaluator = PerformanceEvaluator(pnls, total_assets_history)
            annualized_return, _, _ = evaluator.calculate_metrics()
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
            logger.info(f"Testing RSI Strategy with rsi_period={rsi_period}, rsi_overbought={rsi_overbought}, rsi_oversold={rsi_oversold}")
            strategy = RSIStrategy(market_data, rsi_period=rsi_period, rsi_overbought=rsi_overbought, rsi_oversold=rsi_oversold)
            trades_before, trades_after = strategy.generate_trades()
            calculator = PNLCalculator(market_data, trades_before, trades_after)
            pnls = calculator.calculate_pnl()
            total_assets_history = pd.DataFrame()
            if not pnls.empty:
                total_assets_history['date'] = pd.to_datetime(pnls['交易时间'])
                total_assets_history['assets'] = TRADING_CONFIG['initial_capital'] + pnls['total_pnl'].cumsum()
            evaluator = PerformanceEvaluator(pnls, total_assets_history)
            annualized_return, _, _ = evaluator.calculate_metrics()
            if annualized_return > best_annualized_return:
                best_annualized_return = annualized_return
                best_params = {'rsi_period': rsi_period, 'rsi_overbought': rsi_overbought, 'rsi_oversold': rsi_oversold}
    
    logger.info(f"Best parameters for {strategy_name}: {best_params} with annualized return: {best_annualized_return:.2%}")
    return best_params

def main(strategy_name='momentum', optimize=False):
    loader = DataLoader()
    best_params = None
    if optimize:
        best_params = optimize_parameters(strategy_name, loader.market_data)
    
    if strategy_name == 'momentum':
        if best_params:
            strategy = TradingStrategy(loader.market_data, 
                                      lookback_period=best_params['lookback_period'], 
                                      top_n=best_params['top_n'])
        else:
            strategy = TradingStrategy(loader.market_data)
    elif strategy_name == 'mean_reversion':
        if best_params:
            strategy = MeanReversionStrategy(loader.market_data, 
                                            window=best_params['window'], 
                                            threshold=best_params['threshold'])
        else:
            strategy = MeanReversionStrategy(loader.market_data)
    elif strategy_name == 'rsi':
        if best_params:
            strategy = RSIStrategy(loader.market_data, 
                                  rsi_period=best_params['rsi_period'], 
                                  rsi_overbought=best_params['rsi_overbought'], 
                                  rsi_oversold=best_params['rsi_oversold'])
        else:
            strategy = RSIStrategy(loader.market_data)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    trades_before, trades_after = strategy.generate_trades()
    calculator = PNLCalculator(loader.market_data, trades_before, trades_after)
    pnls = calculator.calculate_pnl()
    
    total_assets_history = pd.DataFrame()
    if not pnls.empty:
        total_assets_history['date'] = pd.to_datetime(pnls['交易时间'])
        # 确保初始资产等于初始资本
        initial_assets = TRADING_CONFIG['initial_capital']
        total_assets_history['assets'] = initial_assets + pnls['total_pnl'].cumsum().shift(1).fillna(0)
        # 修正第一条记录的资产值为初始资本
        if not total_assets_history.empty:
            total_assets_history.loc[0, 'assets'] = initial_assets
    evaluator = PerformanceEvaluator(pnls, total_assets_history)
    annualized_return, sharpe, vol_ann, mdd_info = evaluator.calculate_metrics()
    max_drawdown = mdd_info.ratio
    evaluator.plot_assets_curve()
    evaluator.plot_pnl_per_trade()
    evaluator.plot_performance_metrics()
    
    detailed_report = evaluator.generate_detailed_report()
    with open('detailed_report.txt', 'w', encoding='utf-8') as f:
        f.write(detailed_report)
    
    with open('results.txt', 'w', encoding='utf-8') as f:
        f.write(f'年化收益率: {annualized_return:.2%}\n')
        f.write(f'夏普比率: {sharpe:.2f}\n')
        f.write(f'最大回撤: {max_drawdown:.2%}\n')
        if best_params:
            f.write(f'最佳参数: {best_params}\n')
        if not pnls.empty:
            f.write('\n每次交易的PNL:\n')
            for _, row in pnls.iterrows():
                date_str = row['交易时间'].strftime('%Y%m%d') if isinstance(row['交易时间'], pd.Timestamp) else str(row['交易时间'])
                f.write(f"日期: {date_str}, PNL: {row['total_pnl']:.2f}, 手续费: {row['fee']:.2f}\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Q-T_lib Trading System')
    parser.add_argument('--strategy', type=str, default='momentum', choices=['momentum', 'mean_reversion', 'rsi'], help='Trading strategy to use')
    parser.add_argument('--optimize', action='store_true', help='Whether to optimize strategy parameters')
    args = parser.parse_args()
    main(strategy_name=args.strategy, optimize=args.optimize)
