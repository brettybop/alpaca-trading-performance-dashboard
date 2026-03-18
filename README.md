# Alpaca Trading Perf Dashboard | Python + Power BI

A Python + Power BI project that transforms Alpaca order history into a clean trade-level dataset for performance analytics and interactive BI reporting.

This project is part of my analytics portfolio and demonstrates how Python can be used to extract and shape live trading data, while Power BI handles modeling, DAX measures, and dashboard presentation.

---

## 🎯 Project Objective

The goal of this project is to answer a simple but important question:

> Is this trading strategy actually performing well, and when does it perform best?

To answer that, I built a lightweight ETL workflow in Python that pulls Alpaca order history, converts order activity into trade-level analytics, and exports a CSV dataset that feeds a Power BI dashboard.

The report is designed to evaluate:
- overall strategy performance
- trade quality and edge
- intraday timing edge
- symbol-level profitability
- performance over time

---

## 🧱 Architecture Overview

This project is built around a Python-to-Power-BI workflow:

1. **YAML Configuration**
   - Stores Alpaca API credentials and runtime parameters such as date range and position size.

2. **Python ETL Script**
   - Pulls order history from Alpaca
   - Reconstructs closed trades using FIFO logic
   - Derives BI-friendly fields such as:
     - realized PnL
     - win flag
     - close date
     - day of week
     - hour of day
     - holding time
   - Exports CSV outputs used by Power BI

3. **OneDrive Refresh Layer**
   - The Python script writes the output CSV into a OneDrive-backed folder
   - The Power BI report points to that folder
   - When the CSV is replaced and Power BI is refreshed, the dashboard updates automatically

4. **Power BI Dashboard**
   - Uses DAX measures and supporting dimension tables
   - Surfaces strategy performance through interactive visuals and KPI pages

---

## 📁 Repository Structure

```text
.
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ LICENSE
│
├─ config/
│   └─ paper_main_config_example.yml
│
├─ src/
│   └─ main_ingestion.py
│
├─ data/
│   └─ processed/
│       ├─ orders_pnl.csv
│       ├─ orders_realized.csv
│       ├─ orders_trades.csv
│       └─ orders_trades_daily.csv
│
└─ powerbi/
    └─ Alpaca_Trading_Performance.pbix
