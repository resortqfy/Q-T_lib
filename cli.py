"""Command Line Interface for Q-T_lib Trading System."""

import click
import logging
import pandas as pd
from config.settings import TRADING_CONFIG
from core.pnl_calculator import PNLCalculator
from data.data_loader import DataLoader
from strategies.momentum_strategy import TradingStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.rsi_strategy import RSIStrategy
from analysis.performance_analyzer import PerformanceEvaluator
from main import optimize_parameters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Q-T_lib Trading System CLI."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

@cli.command()
@click.option('--strategy', type=click.Choice(['momentum', 'mean_reversion', 'rsi']), default='momentum', help='Trading strategy to use')
@click.option('--optimize', is_flag=True, help='Whether to optimize strategy parameters')
@click.option('--initial-capital', type=float, default=TRADING_CONFIG['initial_capital'], help='Initial capital for trading')
@click.option('--lookback-period', type=int, help='Lookback period for momentum strategy')
@click.option('--top-n', type=int, help='Top N ETFs to select for momentum strategy')
@click.option('--window', type=int, help='Window size for mean reversion strategy')
@click.option('--threshold', type=float, help='Threshold for mean reversion strategy')
@click.option('--rsi-period', type=int, help='RSI period for RSI strategy')
@click.option('--rsi-overbought', type=int, help='RSI overbought threshold for RSI strategy')
@click.option('--rsi-oversold', type=int, help='RSI oversold threshold for RSI strategy')
def run(strategy, optimize, initial_capital, lookback_period, top_n, window, threshold, rsi_period, rsi_overbought, rsi_oversold):
    """Run the trading system with the specified strategy and parameters."""
    loader = DataLoader()
    best_params = None
    if optimize:
        best_params = optimize_parameters(strategy, loader.market_data)
    
    TRADING_CONFIG['initial_capital'] = initial_capital
    
    if strategy == 'momentum':
        if best_params:
            strategy_instance = TradingStrategy(loader.market_data, 
                                               lookback_period=best_params['lookback_period'], 
                                               top_n=best_params['top_n'])
        elif lookback_period and top_n:
            strategy_instance = TradingStrategy(loader.market_data, 
                                               lookback_period=lookback_period, 
                                               top_n=top_n)
        else:
            strategy_instance = TradingStrategy(loader.market_data)
    elif strategy == 'mean_reversion':
        if best_params:
            strategy_instance = MeanReversionStrategy(loader.market_data, 
                                                     window=best_params['window'], 
                                                     threshold=best_params['threshold'])
        elif window and threshold:
            strategy_instance = MeanReversionStrategy(loader.market_data, 
                                                     window=window, 
                                                     threshold=threshold)
        else:
            strategy_instance = MeanReversionStrategy(loader.market_data)
    elif strategy == 'rsi':
        if best_params:
            strategy_instance = RSIStrategy(loader.market_data, 
                                           rsi_period=best_params['rsi_period'], 
                                           rsi_overbought=best_params['rsi_overbought'], 
                                           rsi_oversold=best_params['rsi_oversold'])
        elif rsi_period and rsi_overbought and rsi_oversold:
            strategy_instance = RSIStrategy(loader.market_data, 
                                           rsi_period=rsi_period, 
                                           rsi_overbought=rsi_overbought, 
                                           rsi_oversold=rsi_oversold)
        else:
            strategy_instance = RSIStrategy(loader.market_data)
    
    trades_before, trades_after = strategy_instance.generate_trades()
    calculator = PNLCalculator(loader.market_data, trades_before, trades_after)
    pnls = calculator.calculate_pnl()
    
    total_assets_history = pd.DataFrame()
    if not pnls.empty:
        total_assets_history['date'] = pd.to_datetime(pnls['date'])
        total_assets_history['assets'] = TRADING_CONFIG['initial_capital'] + pnls['pnl'].cumsum()
    evaluator = PerformanceEvaluator(pnls, total_assets_history)
    annualized_return, sharpe, max_drawdown = evaluator.calculate_metrics()
    evaluator.plot_assets_curve()
    evaluator.plot_pnl_per_trade()
    evaluator.plot_performance_metrics(annualized_return, sharpe, max_drawdown)
    
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
                date_str = row['date'].strftime('%Y%m%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
                f.write(f"日期: {date_str}, PNL: {row['pnl']:.2f}, 手续费: {row['fee']:.2f}\n")
    
    click.echo(f"Trading system run completed. Results saved to results.txt, detailed_report.txt, assets_curve.png, pnl_per_trade.png, and performance_metrics.png")

@cli.command()
def strategies():
    """List available trading strategies."""
    click.echo("Available trading strategies:")
    click.echo("- momentum: Momentum Strategy")
    click.echo("- mean_reversion: Mean Reversion Strategy")
    click.echo("- rsi: RSI Strategy")

if __name__ == '__main__':
    cli()
