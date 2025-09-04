# Q-T_lib 交易系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/yourusername/Q-T_lib/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)

Q-T_lib 是一个开源的交易系统框架，旨在帮助用户设计、测试和优化交易策略，并计算交易的盈亏（PNL）。该项目支持多种交易策略，包括动量策略、均值回归策略和相对强弱指数（RSI）策略。通过提供灵活的参数优化和详细的绩效报告，Q-T_lib 适用于交易员和量化分析师。

## 功能特性

- **多策略支持**：包括动量策略、均值回归策略和 RSI 策略，用户可以轻松扩展自己的策略。
- **数据处理**：支持从 Excel 文件读取多表格市场数据，自动处理不同格式的数据。
- **PNL 计算**：根据交易数据计算每次交易的盈亏，考虑交易手续费。
- **绩效评估**：提供年化收益率、夏普比率、最大回撤等关键指标，并生成详细报告。
- **可视化结果**：生成总资产变化曲线、每次交易盈亏图表和绩效指标图表。
- **参数优化**：通过网格搜索优化策略参数，找到最佳参数组合。
- **命令行界面**：提供用户友好的 CLI，方便运行和测试策略。

## 项目结构

```
Q-T_lib/
│
├── analysis/                # 绩效分析模块
│   └── performance_analyzer.py
├── config/                  # 配置文件
│   └── settings.py
├── core/                    # 核心计算模块
│   └── pnl_calculator.py
├── data/                    # 数据加载模块
│   └── data_loader.py
├── strategies/              # 交易策略模块
│   ├── base_strategy.py
│   ├── momentum_strategy.py
│   ├── mean_reversion_strategy.py
│   └── rsi_strategy.py
├── tests/                   # 单元测试
│   ├── test_data_loader.py
│   ├── test_performance_analyzer.py
│   ├── test_pnl_calculator.py
│   └── test_strategies.py
├── cli.py                   # 命令行界面
├── main.py                  # 主程序入口
├── requirements.txt         # 依赖包列表
├── README.md                # 项目说明文件
├── LICENSE                  # 许可证文件
└── .gitignore               # Git 忽略文件
```

## 安装指南

### 前提条件

- Python 3.6 或更高版本
- Git（可选，用于克隆仓库）

### 步骤

1. **克隆仓库**（如果您是从 GitHub 下载的代码）：
   ```bash
   git clone https://github.com/yourusername/Q-T_lib.git
   cd Q-T_lib
   ```

2. **创建并激活虚拟环境**（可选但推荐）：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. **安装依赖包**：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

Q-T_lib 提供了两种方式运行交易系统：通过主程序 `main.py` 或通过命令行界面 `cli.py`。

### 通过 main.py 运行

```bash
python main.py --strategy momentum --optimize
```

- `--strategy`：选择交易策略，可选值为 `momentum`、`mean_reversion` 或 `rsi`。
- `--optimize`：是否优化策略参数（可选）。

### 通过 CLI 运行

```bash
python cli.py run --strategy rsi --optimize --initial-capital 100000 --rsi-period 14 --rsi-overbought 70 --rsi-oversold 30
```

- `--strategy`：选择交易策略。
- `--optimize`：是否优化策略参数（可选）。
- `--initial-capital`：初始资本（可选，默认 100000）。
- 其他参数：根据策略不同，可以指定特定参数，如 `--lookback-period`、`--top-n`（动量策略）、`--window`、`--threshold`（均值回归策略）、`--rsi-period`、`--rsi-overbought`、`--rsi-oversold`（RSI 策略）。

查看可用策略：

```bash
python cli.py strategies
```

### 输出结果

运行后，系统会生成以下输出文件：
- `results.txt`：包含年化收益率、夏普比率、最大回撤和每次交易的 PNL。
- `detailed_report.txt`：详细的绩效报告，包括资产统计、交易统计和回撤分析。
- `assets_curve.png`：总资产随时间变化曲线。
- `pnl_per_trade.png`：每次交易的盈亏图表。
- `performance_metrics.png`：绩效指标柱状图。
- `trade_before.csv` 和 `trade_after.csv`：交易前后的持仓数据。

## 策略设计

### 动量策略 (Momentum Strategy)

- **逻辑**：基于历史收益率选择表现最好的 ETF 进行投资。假设过去表现好的资产未来也会继续表现好。
- **参数**：
  - `lookback_period`：回溯周期，用于计算历史收益率（默认 30 天）。
  - `top_n`：选择收益率最高的前 N 个 ETF（默认 3）。
- **优势**：能够捕捉市场趋势，适合趋势性强的市场。

### 均值回归策略 (Mean Reversion Strategy)

- **逻辑**：当价格偏离其均值一定程度时，预期价格会回归均值。买入低于均值的资产，卖出高于均值的资产。
- **参数**：
  - `window`：计算均值的窗口大小（默认 20 天）。
  - `threshold`：偏离均值的阈值（默认 2.0 标准差）。
- **优势**：适合震荡市场，能够在价格回归均值时获利。

### RSI 策略 (Relative Strength Index Strategy)

- **逻辑**：使用相对强弱指数（RSI）识别超买和超卖状态。RSI 高于超买线时卖出，低于超卖线时买入。
- **参数**：
  - `rsi_period`：计算 RSI 的周期（默认 14 天）。
  - `rsi_overbought`：超买阈值（默认 70）。
  - `rsi_oversold`：超卖阈值（默认 30）。
- **优势**：能够识别市场极端情况，适合波动较大的市场。

## 代码规范

本项目遵循 Google Python 风格指南，确保代码的可读性和一致性。主要规范包括：
- 缩进：使用 2 个空格作为缩进单位。
- 命名：类名使用 `CamelCase`，函数和变量名使用 `snake_case`。
- 注释：每个模块、类和函数都应有详细的文档字符串，说明其功能和参数。
- 代码结构：模块化设计，每个模块负责特定功能。

更多详情请参考 [Google Python Style Guide](https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules.html).

## 针对 PNL 计算任务的说明

### 任务背景

本项目是为满足以下任务需求而设计的：编写 Python 代码计算交易系统的 PNL（利润和损失）。任务要求指定一个交易策略，并计算指定时间段内的 PNL。数据来源于 `etf_data.xlsx` 文件，交易前后的持仓数据以 CSV 文件形式提供。

### 代码使用方式

1. **运行程序**：通过 `main.py` 或 `cli.py` 运行交易系统，选择策略并生成交易数据和 PNL 计算结果。
   - 示例命令：`python main.py --strategy momentum --optimize`
   - 输出文件：`trade_before.csv` 和 `trade_after.csv` 包含交易数据，`results.txt` 和 `detailed_report.txt` 包含 PNL 和绩效报告。
2. **查看结果**：运行后，查看生成的图表（如 `assets_curve.png`、`pnl_per_trade.png`）和文本报告，了解总资产变化、每次交易的 PNL 以及策略的年化收益率、夏普比率和最大回撤。

### 使用 CMake 构建和运行 Windows 可执行文件

为了方便 Windows 用户直接运行 Q-T_lib 项目，我们提供了 CMake 配置，以便将项目打包为可执行文件（`.exe`）。以下是构建和运行步骤：

1. **安装 CMake**：从 [CMake 官方网站](https://cmake.org/download/) 下载并安装 CMake。
2. **克隆仓库**：如果您还没有克隆仓库，请按照前面的安装指南克隆 Q-T_lib 仓库。
3. **构建项目**：
   - 打开命令提示符或 PowerShell，导航到项目目录：`cd D:\Desktop\Q-T_lib`
   - 创建构建目录并导航到该目录：`mkdir build && cd build`
   - 运行 CMake 配置：`cmake ..`
   - 构建项目：`cmake --build . --config Release`
4. **运行可执行文件**：
   - 构建完成后，可执行文件 `Q-T_lib.exe` 将位于 `build/bin` 目录下。
   - 运行：`bin\Q-T_lib.exe --strategy momentum --optimize`
   - 输出文件和图表将生成在运行目录中。

**注意**：确保 `etf_data.xlsx` 文件位于运行目录中，以便程序能够读取市场数据。

### 策略设计的思考逻辑

- **策略选择**：项目实现了三种策略（动量、均值回归、RSI），每种策略基于不同的市场假设。动量策略捕捉趋势，均值回归策略利用价格回归，RSI 策略识别超买超卖状态。用户可根据市场特点选择合适的策略。
- **参数优化**：通过网格搜索（`optimize_parameters` 函数）测试不同参数组合，选择年化收益率最高的参数，以提高 PNL。
- **资金管理**：初始资本限制在10万元以内，后续交易金额上限为本金加策略收益，确保资金使用符合任务要求。
- **交易单位**：最小交易单位设为100股，符合任务规定。

### PNL 计算逻辑

PNL 计算器 (`PNLCalculator` 类) 是 Q-T_lib 交易系统的核心组件之一，负责计算每次交易的已实现盈亏（PNL）、手续费和总 PNL。以下是详细的计算逻辑：

- **数据读取**：
  - **市场数据**：从 `etf_data.xlsx` 文件读取市场数据，通常包含多个标的在不同交易时间的价格信息（如开盘价）。数据结构为 MultiIndex 格式，索引为 (交易时间, 标的)。
  - **交易数据**：从 `trade_before.csv` 和 `trade_after.csv` 文件读取交易前后的持仓数据。每个文件包含交易时间、标的、价格和数量等信息，分别表示交易前和交易后的持仓状态。

- **计算公式**：
  - 对于每次交易，PNL 计算器会遍历所有交易日期，比较 `trade_before` 和 `trade_after` 中每个标的的数量变化，计算已实现 PNL 和手续费。
  - **已实现 PNL**：
    - 买入操作在当前时点不产生已实现 PNL，只会产生手续费。
    - 卖出操作会产生已实现 PNL，计算公式为：`PNL = (卖出价格 - 成本价格) * 卖出数量`。
  - **手续费**：每次交易（买入或卖出）都会产生手续费，计算公式为：`手续费 = 交易金额 * 手续费率`，其中交易金额为 `价格 * 数量`，手续费率默认为 0.06%（双边）。
  - **总 PNL**：每次交易的总 PNL 为已实现 PNL 减去手续费，即：`总 PNL = 已实现 PNL - 手续费`。

- **买卖逻辑**：
  - **买入逻辑**：如果某个标的在 `trade_after` 中的数量大于 `trade_before` 中的数量，视为买入操作。买入数量为数量差值，买入价格取自 `trade_after` 的价格；如果价格缺失，则回退到市场数据的开盘价。买入操作只产生手续费，不产生已实现 PNL。
  - **卖出逻辑**：如果某个标的在 `trade_after` 中的数量小于 `trade_before` 中的数量，视为卖出操作。卖出数量为数量差值的绝对值，成本价格取自 `trade_before` 的价格，卖出价格取自 `trade_after` 的价格；如果完全清仓后 `trade_after` 中没有该标的记录，则回退到市场数据的开盘价。卖出操作会产生已实现 PNL 和手续费。

- **结果输出**：
  - 每次交易的计算结果记录为一个 DataFrame，包含以下列：
    - `交易时间`：交易发生的日期。
    - `realized_pnl`：当次交易的已实现 PNL。
    - `fee`：当次交易产生的手续费。
    - `total_pnl`：当次交易的总 PNL（已实现 PNL 减去手续费）。
    - `details`（可选）：包含每个标的的交易明细，如标的名称、动作（买入/卖出）、数量、成交价、成本价、已实现 PNL 和手续费。
  - 最终结果输出到 `results.txt` 文件中，包含每次交易的 PNL 信息；总资产变化曲线和绩效指标通过图表（如 `assets_curve.png` 和 `pnl_per_trade.png`）可视化呈现。

通过以上逻辑，PNL 计算器能够准确计算每次交易的盈亏情况，并为后续的绩效分析提供数据支持。

## 贡献指南

欢迎对 Q-T_lib 项目做出贡献！如果您有改进建议或发现了 bug，请按照以下步骤操作：

1. **Fork 仓库**：在 GitHub 上 fork 本仓库。
2. **创建分支**：在您的 fork 中创建一个新分支，分支名应反映您的更改内容（如 `feature/add-new-strategy` 或 `bugfix/fix-data-loader`）。
3. **提交更改**：进行您的更改并提交，提交信息应清晰描述更改内容。
4. **运行测试**：确保您的更改通过所有单元测试（如果有新的功能，请添加相应的测试）。
5. **提交 Pull Request**：创建一个 pull request，详细说明您的更改及其影响。

请确保您的代码符合项目的代码规范，并通过所有测试。我们会尽快审查您的 pull request。

## 许可证

本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。

## 联系方式

如果您有任何问题或建议，请通过 GitHub Issues 联系我们，或者发送邮件至 [feiyuanqiao52@gmail.com]。

---

感谢使用 Q-T_lib 交易系统！
