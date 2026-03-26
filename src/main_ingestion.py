# Update config_file_path to where you saved your config file.
config_file_path = ""

##################################### Section 1: Config, Modules, and Imports ############################
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import alpaca_trade_api as tradeapi
import datetime as dt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone as dt_timezone
from pytz import timezone
import time
import yaml
from typing import Optional, List, Dict

# Load YAML configuration
with open(config_file_path, "r") as file:
    config = yaml.safe_load(file)

API_KEY = config['API_KEY']
SECRET_KEY = config["SECRET_KEY"]
api_base_url = config["api_base_url"]
symbols = config["symbols"]
position_size = config["position_size"]
start_time = config["start_time"]
end_time = config["end_time"]

# Client/Acc Info
print("ACC INFO: ")
print("-----------------------------------------")

# Infer paper/live from URL so account info matches endpoint
paper_mode = "paper-api" in str(api_base_url).lower()

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=paper_mode)
account = trading_client.get_account()

# More robust account printing
try:
    account_items = account.model_dump().items()
except AttributeError:
    try:
        account_items = dict(account).items()
    except Exception:
        account_items = []

for property_name, value in account_items:
    print(f"\"{property_name}\":{value}")

hist_data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)  # key validation
api = tradeapi.REST(API_KEY, SECRET_KEY, api_base_url, api_version='v2')

# symbol list length
num_of_symbols = len(symbols)
print("-----------------------------------------")
print(f"The number of tickers in this list are {num_of_symbols}")

# Daily Buying power
daytrading_buying_power = int(round(float(account.daytrading_buying_power)))
print(f"Position sizes are currently set to: ${position_size}")
print(f"Day Trading Buying Power: ${daytrading_buying_power}")

# Max Trade Attempts
max_trade_attempts = int(round(float(daytrading_buying_power / position_size))) if float(position_size) > 0 else 0

##################################### Section 1-B: Helpers ############################
def _to_utc(ts):
    """Safely convert to timezone-aware UTC pandas Timestamp."""
    if pd.isna(ts):
        return pd.NaT
    t = pd.to_datetime(ts, utc=True, errors="coerce")
    return t

def _localize(ts, tz="America/Los_Angeles"):
    if pd.isna(ts):
        return pd.NaT
    return _to_utc(ts).tz_convert(tz)

def _add_bi_fields(trades: pd.DataFrame) -> pd.DataFrame:
    """Add derived BI fields to the trades table."""
    exit_local = trades["exit_at"].dt.tz_convert("America/Los_Angeles")
    trades["close_date"] = exit_local.dt.date
    trades["day_of_week"] = exit_local.dt.day_name()
    trades["hour_of_day"] = exit_local.dt.hour
    trades["win_flag"] = (trades["realized_pnl"] > 0).astype(int)
    return trades

def _get_exec_qty(df: pd.DataFrame) -> pd.Series:
    """
    Use filled_qty when available for accurate execution-based trade math.
    Falls back to qty if filled_qty is missing.
    """
    if "filled_qty" in df.columns:
        filled_qty = pd.to_numeric(df["filled_qty"], errors="coerce")
        order_qty = pd.to_numeric(df["qty"], errors="coerce")
        exec_qty = filled_qty.fillna(order_qty)
    else:
        exec_qty = pd.to_numeric(df["qty"], errors="coerce")
    return exec_qty

def _fifo_to_trades(orders_df: pd.DataFrame,
                    fee_per_share: float = 0.0,
                    slippage_bps: float = 0.0) -> pd.DataFrame:
    """
    Convert order-level fills (chronological) into trade-level closed lots via FIFO.

    Parameters
    ----------
    orders_df : DataFrame
        Must include: symbol, side, qty, filled_avg_price, submitted_at, filled_at
        If filled_qty exists, it will be used internally for better accuracy.
    fee_per_share : float
        Per-share fee (commission, ECN, etc.)
    slippage_bps : float
        Kept for compatibility but NOT used in this BI-safe version.

    Returns
    -------
    DataFrame
        One row per closed lot with BI-friendly fields.
    """
    df = orders_df.copy()

    # Standardize/parse
    for col in ["submitted_at", "filled_at", "canceled_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    for col in ["qty", "filled_avg_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["exec_qty"] = _get_exec_qty(df)

    # Only rows with actual executions should be used for trade reconstruction
    df = df[
        df["filled_at"].notna() &
        df["filled_avg_price"].notna() &
        df["exec_qty"].notna() &
        (df["exec_qty"] > 0)
    ].copy()

    df = df.sort_values(["filled_at", "submitted_at"], kind="stable").reset_index(drop=True)

    # Queues per symbol: list of open lots dicts
    # lot = {"qty": remaining_shares, "price": entry_price, "ts": filled_time, "side": "long"/"short", "order_id": ...}
    open_lots: Dict[str, List[dict]] = {}
    trade_rows = []
    trade_idx_by_symbol: Dict[str, int] = {}

    for idx, row in df.iterrows():
        sym = row["symbol"]
        side = str(row["side"]).lower()  # 'buy'/'sell'
        qty = float(row["exec_qty"])
        px = float(row["filled_avg_price"])
        t_f = row["filled_at"]
        oid = row.get("order_id", None)

        q = open_lots.setdefault(sym, [])
        trade_idx_by_symbol.setdefault(sym, 0)

        if side == "buy":
            # Cover shorts first
            while qty > 0 and q and q[0]["side"] == "short":
                lot = q[0]
                close_qty = min(qty, lot["qty"])

                pnl = (lot["price"] - px) * close_qty  # short profit formula
                fees = fee_per_share * (close_qty + close_qty)
                net_pnl = pnl - fees
                entry_notional = lot["price"] * close_qty

                trade_idx_by_symbol[sym] += 1
                trade_rows.append({
                    "trade_id": f"{sym}-{trade_idx_by_symbol[sym]}",
                    "symbol": sym,
                    "closed_side": "short",
                    "qty_closed": close_qty,
                    "entry_price": lot["price"],
                    "exit_price": px,
                    "entry_at": lot["ts"],
                    "exit_at": t_f,
                    "entry_order_id": lot["order_id"],
                    "exit_order_id": oid,
                    "realized_pnl": net_pnl,
                    "fees": fees,
                    "return_pct": net_pnl / entry_notional if entry_notional > 0 else np.nan,
                    "holding_minutes": (t_f - lot["ts"]).total_seconds() / 60.0
                })

                lot["qty"] -= close_qty
                qty -= close_qty
                if lot["qty"] <= 1e-12:
                    q.pop(0)

            # leftover opens long
            if qty > 0:
                q.append({"qty": qty, "price": px, "ts": t_f, "side": "long", "order_id": oid})

        elif side == "sell":
            # Close longs first
            while qty > 0 and q and q[0]["side"] == "long":
                lot = q[0]
                close_qty = min(qty, lot["qty"])

                pnl = (px - lot["price"]) * close_qty
                fees = fee_per_share * (close_qty + close_qty)
                net_pnl = pnl - fees
                entry_notional = lot["price"] * close_qty

                trade_idx_by_symbol[sym] += 1
                trade_rows.append({
                    "trade_id": f"{sym}-{trade_idx_by_symbol[sym]}",
                    "symbol": sym,
                    "closed_side": "long",
                    "qty_closed": close_qty,
                    "entry_price": lot["price"],
                    "exit_price": px,
                    "entry_at": lot["ts"],
                    "exit_at": t_f,
                    "entry_order_id": lot["order_id"],
                    "exit_order_id": oid,
                    "realized_pnl": net_pnl,
                    "fees": fees,
                    "return_pct": net_pnl / entry_notional if entry_notional > 0 else np.nan,
                    "holding_minutes": (t_f - lot["ts"]).total_seconds() / 60.0
                })

                lot["qty"] -= close_qty
                qty -= close_qty
                if lot["qty"] <= 1e-12:
                    q.pop(0)

            # leftover opens short
            if qty > 0:
                q.append({"qty": qty, "price": px, "ts": t_f, "side": "short", "order_id": oid})

    trades = pd.DataFrame(trade_rows)
    if not trades.empty:
        trades[["entry_at", "exit_at"]] = trades[["entry_at", "exit_at"]].apply(pd.to_datetime, utc=True)
        trades = _add_bi_fields(trades)
    return trades

##################################### Section 1-C: Order-export utility ############################
def export_orders_to_csv(
        after: Optional[str] = None,
        until: Optional[str] = None,
        status: str = "all",
        out_file: str = "alpaca_orders.csv",
        fee_per_share: float = 0.0,
        slippage_bps: float = 0.0
    ) -> str:
    """
    Pull Alpaca order history and save to CSV + trade-level tables.

    Parameters
    ----------
    after : str | None
        ISO-8601 date (e.g., '2024-01-01') – only orders submitted after this.
    until : str | None
        ISO-8601 date – only orders before this.
    status : {'open','closed','all'}
    out_file : str
        Base path to CSV output.
    fee_per_share : float
        Per-share fee to subtract from PnL (applied at both entry and exit).
    slippage_bps : float
        Kept for compatibility but NOT used in this BI-safe version.

    Returns
    -------
    str
        Path to the orders CSV written (the *_pnl.csv file).
    """
    print(f"[EXPORT] Fetching orders → {out_file} ...")

    orders = []
    cursor_after = after

    while True:
        batch = api.list_orders(
            status=status,
            limit=500,
            nested=False,   # flat rows so we capture all order records/legs for BI
            after=cursor_after,
            until=until,
            direction="asc"
        )
        if not batch:
            break

        orders.extend(batch)
        if len(batch) < 500:
            break

        last_ts = batch[-1].submitted_at
        if isinstance(last_ts, str):
            cursor_after = last_ts
        else:
            cursor_after = (last_ts + timedelta(microseconds=1)).isoformat()

    if not orders:
        print("[EXPORT] No orders returned.")
        return ""

    # Pull a slightly richer raw dataset internally, but keep output columns the same
    raw_df = pd.DataFrame(o._raw for o in orders).rename(columns={"id": "order_id"})

    KEEP = [
        "order_id", "submitted_at", "filled_at", "canceled_at",
        "symbol", "qty", "filled_avg_price",
        "type", "side", "position_intent"
    ]

    # Parse raw types if present
    for col in ["submitted_at", "filled_at", "canceled_at", "created_at", "updated_at", "expired_at"]:
        if col in raw_df.columns:
            raw_df[col] = pd.to_datetime(raw_df[col], utc=True, errors="coerce")

    for col in ["qty", "filled_avg_price", "filled_qty"]:
        if col in raw_df.columns:
            raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce")

    # Build full output table with original columns only
    df = raw_df.copy()
    for col in KEEP:
        if col not in df.columns:
            df[col] = np.nan
    df = df[KEEP].copy()

    # Add computed columns (same names as original script)
    df["realized_pnl"] = 0.0
    df["closed_side"] = ""

    # Create execution-only frame for accurate realized PnL math
    exec_df = raw_df.copy()
    exec_df["exec_qty"] = _get_exec_qty(exec_df)

    exec_df = exec_df[
        exec_df["filled_at"].notna() &
        exec_df["filled_avg_price"].notna() &
        exec_df["exec_qty"].notna() &
        (exec_df["exec_qty"] > 0)
    ].copy()

    exec_df = exec_df.sort_values(["filled_at", "submitted_at"], kind="stable").reset_index(drop=True)

    # Per-symbol open lots (for order-level realized attribution)
    open_lots = {}

    order_realized = {}
    order_closed_side = {}

    for idx, row in exec_df.iterrows():
        sym = row["symbol"]
        side = str(row["side"]).lower()
        qty = float(row["exec_qty"])
        price = float(row["filled_avg_price"])
        order_id = row["order_id"]

        lot_queue = open_lots.setdefault(sym, [])
        realized = 0.0
        closed_side = ""

        if side == "buy":
            while qty > 0 and lot_queue and lot_queue[0]["side"] == "short":
                lot = lot_queue[0]
                cover_qty = min(qty, lot["qty"])
                realized += (lot["price"] - price) * cover_qty
                lot["qty"] -= cover_qty
                qty -= cover_qty
                closed_side = "short"
                if lot["qty"] <= 1e-12:
                    lot_queue.pop(0)

            if qty > 0:
                lot_queue.append({"qty": qty, "price": price, "side": "long"})

        elif side == "sell":
            while qty > 0 and lot_queue and lot_queue[0]["side"] == "long":
                lot = lot_queue[0]
                close_qty = min(qty, lot["qty"])
                realized += (price - lot["price"]) * close_qty
                lot["qty"] -= close_qty
                qty -= close_qty
                closed_side = "long"
                if lot["qty"] <= 1e-12:
                    lot_queue.pop(0)

            if qty > 0:
                lot_queue.append({"qty": qty, "price": price, "side": "short"})

        order_realized[order_id] = realized
        order_closed_side[order_id] = closed_side

    # Map order-level realized values back to the full orders table
    df["realized_pnl"] = df["order_id"].map(order_realized).fillna(0.0)
    df["closed_side"] = df["order_id"].map(order_closed_side).fillna("")

    # Write enhanced orders file(s)
    clean_file = out_file.replace(".csv", "_pnl.csv")
    df.to_csv(clean_file, index=False)
    print(f"[TIDY] {len(df):,} orders → {clean_file}")

    realized = df[df.realized_pnl != 0].copy()
    realized_file = out_file.replace(".csv", "_realized.csv")
    realized.to_csv(realized_file, index=False)
    print(f"[TIDY] {len(realized):,} orders with realised P/L → {realized_file}")

    # Build trades (closed lots) and daily aggregate
    trades = _fifo_to_trades(raw_df, fee_per_share=fee_per_share, slippage_bps=slippage_bps)
    trades_file = out_file.replace(".csv", "_trades.csv")
    trades.to_csv(trades_file, index=False)
    print(f"[TRADES] {len(trades):,} closed lots → {trades_file}")

    if not trades.empty:
        trades_daily = (trades
            .groupby(["close_date", "symbol"], as_index=False)
            .agg(total_pnl=("realized_pnl", "sum"),
                 wins=("win_flag", "sum"),
                 trades=("trade_id", "count"),
                 avg_holding_min=("holding_minutes", "mean"))
        )
        trades_daily_file = out_file.replace(".csv", "_trades_daily.csv")
        trades_daily.to_csv(trades_daily_file, index=False)
        print(f"[TRADES] daily summary → {trades_daily_file}")

    return clean_file

#############################################################################################
if __name__ == "__main__":
    # TEMP TEST RUN
    export_orders_to_csv(
        after=start_time,
        until=end_time,
        out_file="orders.csv",
        fee_per_share=0.0,     # set > 0 only if you later want fee-adjusted PnL
        slippage_bps=0.0       # kept for compatibility; not used in this version
    )
