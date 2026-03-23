# Alpaca Trading Performance Dashboard | Python + Power BI

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
```

## 📊 Data Pipeline

The Python script is the core data engine behind the dashboard.

1. **Inputs**

- Alpaca Order History
- YAML configuration file containing:
   - API key
   - secret key
   - API base URL
   - date range
   - position size
   - optional symbol list

2. **Transformations**

The ETL script:
- retrieves Alpaca order history
- keeps all order records for auditability
- identifies executed trades using filled order data
- reconstructs closed lots using FIFO logic
- calculates realized trade-level PnL
- derives time-based features for BI analysis

3. **Outputs**

The script writes the following CSVs:
- orders_pnl.csv
   - all orders with order-level realized PnL attribution where applicable
- orders_realized.csv
   - subset of orders with non-zero realized PnL
- orders_trades.csv
   - primary fact table used for trade-level analysis in Power BI
- orders_trades_daily.csv
   - daily summary by close date and symbol

## 🗐 Power BI Dashboard Pages

### **Intro Page**

A landing page for the report that introduces the project and serves as a navigation hub for the dashboard.

### **01 – Performance Overview**

This page provides the executive summary of the strategy.

Key metrics include:
- Win Rate
- Total Trades
- Total PnL
- Profit Factor
- Expectancy
- Profit by Symbol
- Average Win
- Average Loss
- Number of Winners
- Number of Losers
- Average Hold Time

**This page answers:**
*1. How is the strategy performing overall?*
*2. Is the edge statistically and financially meaningful?*
*3. Which symbols are driving results?*

### **02 – Time Heatmap**

This page uses `DIM_HOUR` and `DIM_WEEKDAY` with audit measures to visualize Total PnL in a heatmap matrix.

Green and red shading highlight the strongest and weakest time windows.

**This page answers:**
*1. Which days and hours produce the strongest performance?*
*2. Where does the strategy consistently lose money?*

### **03 – Time by Symbol Analysis**

This page drills into intraday performance by symbol, specifically between 6:00 AM and 10:00 AM.

Built primarily from FACT_TRADES, it uses a line and clustered column chart to analyze PnL by hour and by symbol.

**This page answers:**
*1. When do winning trades happen?*
*2. Does timing edge vary across symbols?*
*3. Are certain symbols stronger at specific hours?*

### **04 – PnL Curve**

This page plots Total PnL over Date from the Calendar table.

It provides a time-based view of performance and helps evaluate strategy consistency.

**This page answers:**
*1. How has performance evolved over time?*
*2. Are returns steady or volatile?*
*3. Where are the major drawdowns and recoveries?*

## 📝 Data Model Notes
This project primarily relies on Python for transformation logic and Power BI for semantic modeling and measures.

**Core model components include:**
- FACT_TRADES
- DIM_HOUR
- DIM_WEEKDAY
- Calendar
- Audit Measures

No SQL was used in this project. The heavy lifting is performed in Python, with Power BI handling DAX calculations, dimensional slicing, and presentation.

## 🥷 Key SKills Demonstrated

**This project demonstrates:**
- Python ETL development
- extracting live broker data from Alpaca
- transforming raw order history into analytics-ready trade tables
- exporting reproducible CSV outputs for BI consumption
- Trading analytics
- FIFO trade reconstruction
- realized PnL logic
- expectancy, profit factor, win/loss analysis
- intraday timing analysis
- Power BI development
- DAX-based KPI modeling
- dimensional reporting with date/hour/weekday tables
- matrix heatmaps, time-series visuals, and performance dashboards

## 🔑 Why This Project Matters

**This project goes further by asking:**
- when does the strategy work?
- where is the timing edge?
- which symbols actually contribute to results?
- how stable is the performance through time?
  
By combining Python-based transformation logic with Power BI reporting, this project turns raw broker data into a reusable analytics workflow.

## 🎛️ How to Refresh the Dashboard

Update the YAML config with the desired date window and credentials

1.) Run the Python ingestion script
2.) Save or replace the generated CSV output in the connected OneDrive folder
3.) Open the Power BI report and refresh the dataset. Connector must point to the folder containing the CSV. Can setup gateway if needed.

## 👮 Security / Notes

- Real API credentials are not stored in this repository
- The tracked YAML file should be an example config only
- Sensitive or personal account details should be excluded from public sample data where needed

##  📈 Future Improvements

**Possible next enhancements:**
- broker-agnostic ingestion layer
- strategy tagging by setup type
- rolling expectancy / rolling win-rate windows
- drawdown depth and recovery duration measures
- database-backed storage instead of flat CSV export
