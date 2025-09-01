"""Data Loader module.

This module contains the DataLoader class for loading market and trade data.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads market data from Excel file and trade data from CSV files."""

    def __init__(self):
        self.market_data = self.load_market_data('etf_data.xlsx')

    def load_market_data(self, file_path):
        """Load market data from an Excel file with multiple sheets, each representing a different ETF."""
        try:
            # 获取Excel文件中的所有表格名称
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            logger.info(f"找到的表格名称: {sheet_names}")

            all_data = []
            for sheet in sheet_names:
                logger.info(f"正在读取表格: {sheet}")
                # 读取每个表格
                df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                logger.info(f"表格 {sheet} 的列名: {df.columns.tolist()}")

                # 查找日期列
                date_col = None
                for col in df.columns:
                    if isinstance(col, str) and any(keyword in col.lower() for keyword in ['日期', 'date', '时间']):
                        date_col = col
                        break
                if date_col is None:
                    logger.warning(f"在表格 {sheet} 中未找到日期列，使用第一列作为日期")
                    date_col = df.columns[0]

                # 查找开盘价列
                open_col = None
                for col in df.columns:
                    if isinstance(col, str) and any(keyword in col.lower() for keyword in ['开盘', 'open']):
                        open_col = col
                        break
                if open_col is None:
                    logger.warning(f"在表格 {sheet} 中未找到开盘价列，使用第二列作为开盘价")
                    open_col = df.columns[1] if len(df.columns) > 1 else None

                if date_col and open_col:
                    # 提取日期和开盘价列
                    temp_df = df[[date_col, open_col]].copy()
                    temp_df['code'] = sheet  # 使用表格名称作为标的代码
                    temp_df.columns = ['date', 'open', 'code']
                    all_data.append(temp_df)
                else:
                    logger.error(f"无法在表格 {sheet} 中找到必要的列")

            if not all_data:
                raise ValueError("未找到任何有效的数据表格")

            # 合并所有表格的数据
            market_data = pd.concat(all_data, ignore_index=True)
            market_data['date'] = pd.to_datetime(market_data['date'])
            market_data.set_index(['date', 'code'], inplace=True)
            logger.info(f"最终市场数据前几行:\n{market_data.head()}")
            return market_data

        except Exception as e:
            logger.error(f"读取市场数据时出错: {e}")
            raise

    def load_trade_data(self, before_file, after_file):
        """Load trade data from CSV files."""
        try:
            trades_before = pd.read_csv(before_file)
            trades_after = pd.read_csv(after_file)
            return trades_before, trades_after
        except Exception as e:
            logger.error(f"读取交易数据时出错: {e}")
            raise
