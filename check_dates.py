import pandas as pd

# 读取 Excel 文件
xl = pd.ExcelFile('etf_data.xlsx')
dates = []
for sheet in xl.sheet_names:
    df = pd.read_excel('etf_data.xlsx', sheet_name=sheet, header=1)
    date_col = next((col for col in df.columns if isinstance(col, str) and any(k in col.lower() for k in ['日期', 'date', '时间'])), df.columns[0])
    df[date_col] = pd.to_datetime(df[date_col])
    dates.extend(df[date_col].values)

# 输出日期范围
min_date = pd.Timestamp(min(dates))
max_date = pd.Timestamp(max(dates))
print('数据日期范围:', min_date.strftime('%Y-%m-%d'), '到', max_date.strftime('%Y-%m-%d'))
