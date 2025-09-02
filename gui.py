import tkinter as tk
from tkinter import ttk, messagebox
import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import main as run_trading_system

class Q_T_lib_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Q-T_lib 交易系统")
        self.root.geometry("600x400")

        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 交易策略选择
        ttk.Label(self.main_frame, text="交易策略:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.strategy_var = tk.StringVar(value="momentum")
        strategies = ["momentum", "mean_reversion", "rsi"]
        ttk.Combobox(self.main_frame, textvariable=self.strategy_var, values=strategies, state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 是否优化参数
        self.optimize_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.main_frame, text="优化策略参数", variable=self.optimize_var).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # 初始资本
        ttk.Label(self.main_frame, text="初始资本:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.capital_var = tk.StringVar(value="100000")
        ttk.Entry(self.main_frame, textvariable=self.capital_var).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 策略特定参数
        self.parameters_frame = ttk.LabelFrame(self.main_frame, text="策略参数", padding="5")
        self.parameters_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 动量策略参数
        self.momentum_frame = ttk.Frame(self.parameters_frame)
        ttk.Label(self.momentum_frame, text="回溯周期:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.lookback_var = tk.StringVar(value="30")
        ttk.Entry(self.momentum_frame, textvariable=self.lookback_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.momentum_frame, text="选择前 N 个 ETF:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.top_n_var = tk.StringVar(value="3")
        ttk.Entry(self.momentum_frame, textvariable=self.top_n_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 均值回归策略参数
        self.mean_reversion_frame = ttk.Frame(self.parameters_frame)
        ttk.Label(self.mean_reversion_frame, text="窗口大小:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.window_var = tk.StringVar(value="20")
        ttk.Entry(self.mean_reversion_frame, textvariable=self.window_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.mean_reversion_frame, text="偏离阈值:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.threshold_var = tk.StringVar(value="2.0")
        ttk.Entry(self.mean_reversion_frame, textvariable=self.threshold_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # RSI 策略参数
        self.rsi_frame = ttk.Frame(self.parameters_frame)
        ttk.Label(self.rsi_frame, text="RSI 周期:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.rsi_period_var = tk.StringVar(value="14")
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_period_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.rsi_frame, text="超买阈值:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.rsi_overbought_var = tk.StringVar(value="70")
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_overbought_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.rsi_frame, text="超卖阈值:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.rsi_oversold_var = tk.StringVar(value="30")
        ttk.Entry(self.rsi_frame, textvariable=self.rsi_oversold_var).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 根据策略显示不同的参数框架
        self.strategy_var.trace("w", self.update_parameters_frame)
        self.update_parameters_frame()

        # 运行按钮
        ttk.Button(self.main_frame, text="运行交易系统", command=self.run_system).grid(row=4, column=0, columnspan=2, pady=10)

    def update_parameters_frame(self, *args):
        strategy = self.strategy_var.get()
        for frame in [self.momentum_frame, self.mean_reversion_frame, self.rsi_frame]:
            frame.grid_forget()
        if strategy == "momentum":
            self.momentum_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        elif strategy == "mean_reversion":
            self.mean_reversion_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        elif strategy == "rsi":
            self.rsi_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

    def run_system(self):
        try:
            strategy = self.strategy_var.get()
            optimize = self.optimize_var.get()
            initial_capital = float(self.capital_var.get())

            # 构建参数字典
            args = argparse.Namespace()
            args.strategy = strategy
            args.optimize = optimize
            # 在 config.settings 中设置初始资本
            from config.settings import TRADING_CONFIG
            TRADING_CONFIG['initial_capital'] = initial_capital

            if strategy == "momentum":
                args.lookback_period = int(self.lookback_var.get())
                args.top_n = int(self.top_n_var.get())
            elif strategy == "mean_reversion":
                args.window = int(self.window_var.get())
                args.threshold = float(self.threshold_var.get())
            elif strategy == "rsi":
                args.rsi_period = int(self.rsi_period_var.get())
                args.rsi_overbought = int(self.rsi_overbought_var.get())
                args.rsi_oversold = int(self.rsi_oversold_var.get())

            # 运行交易系统
            run_trading_system(strategy_name=args.strategy, optimize=args.optimize)
            messagebox.showinfo("成功", "交易系统运行完成。结果已保存到输出文件中。")
        except ValueError as e:
            messagebox.showerror("错误", f"输入参数无效：{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"运行交易系统时出错：{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = Q_T_lib_GUI(root)
    root.mainloop()
