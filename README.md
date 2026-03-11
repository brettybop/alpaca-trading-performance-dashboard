# Alpaca Trading Performance – Python + Power BI

A Python + Power BI project that transforms raw Alpaca trade history into a clean analytics model and an interactive trading performance dashboard.

This project is part of a broader portfolio focused on **real trading data**, **reproducible ETL**, and **professional BI modeling**.

---

## 🎯 Project Objective

Answer one core question:

> “Is my Alpaca trading strategy actually working – and where exactly is it strong or weak?”

To do that, the project:

- Extracts trade data (from Alpaca export or API)
- Cleans and aggregates trades to position / session level
- Builds a star-schema-style model for analysis
- Surfaces performance metrics in a polished Power BI report

---

## 📊 Key Business Questions

The dashboard is designed to answer:

- What is my **overall performance** (P&L, win rate, expectancy)?
- Which **symbols** and **strategies** are truly profitable?
- When do I perform best/worst (**day of week**, **time of day**, **market regime**)?
- How deep are my **drawdowns**, and how long does recovery take?
- How does performance change with **holding time**, **position size**, or **side** (long vs short)?

---

## 🧱 Architecture & Flow

High-level flow:

1. **Data Source**  
   - Alpaca trade history (CSV export or API pull)

2. **Python ETL (`src/`)**  
   - Clean raw fills
   - Construct `fact_trades` table
   - Derive fields (R-multiple, holding period, realized P&L, trade tags)
   - Export `data/processed/trades_model_input.csv`

3. **Power BI Data Model (`powerbi/Alpaca_Trading_Performance.pbix`)**  
   - Load the processed CSV
   - Create dimensions: calendar, symbol, strategy
   - Build DAX measures for KPIs and time-intelligence

4. **Power BI Report Pages**  
   - Overview KPIs + Equity Curve
   - Symbol & Strategy Breakdown
   - Time-of-Day / Day-of-Week performance
   - Risk / Drawdown view

---

## 🛠 Tech Stack

- **Python**
  - `pandas` for cleaning / feature engineering
  - `python-dotenv` for reading API keys (optional)
  - `requests` / `alpaca-py` if you pull directly via API

- **Power BI**
  - Power Query for final shaping
  - Star schema data model
  - DAX for metrics (win rate, expectancy, drawdown, time intelligence)

- **Version Control**
  - Git + GitHub for reproducible, portfolio-ready project

---

## 📁 Repository Structure

```text
.
├─ README.md
├─ .gitignore
├─ requirements.txt
├─ .env.example
│
├─ data/
│   ├─ raw/
│   │   └─ sample_trades.csv              # small example dataset
│   └─ processed/
│       └─ trades_model_input.csv         # model input for Power BI
│
├─ src/
│   ├─ 01_download_trades.py              # optional: call Alpaca API
│   ├─ 02_build_fact_trades.py            # ETL → trades_model_input.csv
│   └─ utils.py                           # helper functions
│
├─ powerbi/
│   └─ Alpaca_Trading_Performance.pbix    # main report
│
└─ docs/
    ├─ project_overview.md
    ├─ data_model.md
    └─ dax_measures.md
