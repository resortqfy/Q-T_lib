"""Configuration settings for the trading system."""

# 交易配置
TRADING_CONFIG = {
    'initial_capital': 100000,  # 初始资本（人民币）
    'transaction_fee_rate': 0.0006,  # 交易手续费率 0.06%
    'min_trade_unit': 100,  # 最小交易单位（股）
    'momentum': {
        'lookback_period': range(10, 50, 10),  # 动量策略回溯周期范围，用于参数优化
        'top_n': range(1, 5),  # 选择收益率最高的前 N 个 ETF
    },
    'mean_reversion': {
        'window': range(10, 30, 5),  # 均值回归策略窗口大小范围
        'threshold': [1.5, 2.0, 2.5],  # 均值回归策略阈值范围
    }
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
}

# 文件路径
FILE_PATHS = {
    'market_data': 'etf_data.xlsx',
    'trade_before': 'trade_before.csv',
    'trade_after': 'trade_after.csv',
    'results': 'results.txt',
    'assets_curve': 'assets_curve.png'
}
