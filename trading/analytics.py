"""
trading/analytics.py
--------------------
Performance metrics calculation for the Trading Engine.
"""

from typing import List
import pandas as pd
import numpy as np


class PerformanceAnalytics:
    """Computes trading performance metrics from an execution history."""
    
    @staticmethod
    def compute_metrics(execution_logs: List[dict], initial_cash: float) -> dict:
        """
        Takes a list of execution dictionaries (from TradeLedger.get_history())
        and the initial starting cash. Returns a dictionary of computed metrics.
        """
        if not execution_logs:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "average_return_pct": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0
            }

        df = pd.DataFrame(execution_logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Compute Cashflow (Buys are negative cashflow, Sells are positive)
        df['cashflow'] = df.apply(
            lambda r: (-1 if r['side'] == 'BUY' else 1) * (r['price'] * r['quantity']) - r['fees'], 
            axis=1
        )
        
        # PnL math requires matching trades. 
        # For simplicity in this aggregated method, we'll track realized PnL per symbol (FIFO).
        # To keep it lightweight and matching requirements, we'll do a simple loop for Realized PnL.
        realized_pnl_trades = []
        positions = {}  # symbol -> list of dicts {price, qty}

        for _, row in df.iterrows():
            sym = row['symbol']
            qty = row['quantity']
            side = row['side']
            price = row['price']
            
            if sym not in positions:
                positions[sym] = []
                
            if side == 'BUY':
                positions[sym].append({'price': price, 'qty': qty})
            elif side == 'SELL':
                qty_to_sell = qty
                trade_pnl = 0.0 - row['fees']  # Deduct fees of the sell
                
                while qty_to_sell > 0 and positions[sym]:
                    lot = positions[sym][0]
                    if lot['qty'] <= qty_to_sell:
                        # Sell entire lot
                        trade_pnl += (price - lot['price']) * lot['qty']
                        qty_to_sell -= lot['qty']
                        positions[sym].pop(0)
                    else:
                        # Sell partial lot
                        trade_pnl += (price - lot['price']) * qty_to_sell
                        lot['qty'] -= qty_to_sell
                        qty_to_sell = 0
                        
                realized_pnl_trades.append(trade_pnl)

        realized_series = pd.Series(realized_pnl_trades) if realized_pnl_trades else pd.Series(dtype=float)
        
        # Metrics
        total_trades = len(df)
        winning_trades = len(realized_series[realized_series > 0])
        total_closed = len(realized_series)
        
        win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0.0
        
        gross_profit = realized_series[realized_series > 0].sum()
        gross_loss = abs(realized_series[realized_series < 0].sum())
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)
        
        average_return = float(realized_series.mean()) if total_closed > 0 else 0.0
        
        # Equity Curve and Max Drawdown (Cashflow based for simplicity here, assumes starting cash)
        df['cumulative_cashflow'] = df['cashflow'].cumsum()
        df['equity'] = initial_cash + df['cumulative_cashflow']
        
        # NOTE: True equity includes Unrealized PnL, but for basic transaction logs, we use Realized Cash + Value of holdings.
        # This simplistic calculation acts as a realized equity curve.
        peak = df['equity'].cummax()
        drawdowns = (df['equity'] - peak) / peak
        max_drawdown = float(drawdowns.min() * 100) if not drawdowns.empty else 0.0
        
        final_equity = df['equity'].iloc[-1] if not df.empty else initial_cash
        total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100
        
        # Sharpe Ratio (assumes risk free rate = 0, annualized over 252 days)
        # Using trade-by-trade returns:
        if len(realized_series) > 1:
            mean_pnl = realized_series.mean()
            std_pnl = realized_series.std()
            sharpe_ratio = float((mean_pnl / std_pnl) * np.sqrt(252)) if std_pnl > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "average_return_trade": round(average_return, 2),
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2)
        }
