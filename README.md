# py-stock-watcher
An AI-Driven Fundamental Analysis & Stock Filtering Engine
py-stock-watcher is a sophisticated Django-based web application designed to automate the process of fundamental stock analysis. By integrating real-time financial data with machine learning, the platform helps investors identify "hidden champions" and high-growth opportunities across Canadian and US markets.

🚀 Key Features
AI Stock Scoring Engine: Utilizes a Random Forest Classifier to analyze core fundamentals (P/E ratio, ROE, Debt-to-Equity, and Growth metrics). It generates a proprietary Stock Health Score (0-100) and actionable recommendations like "Strong Buy" or "High Risk."

Automated Data Ingestion: Seamlessly fetches live market data, analyst price targets, and ratings from Yahoo Finance to ensure analysis is always grounded in the latest market sentiment.

Deep Fundamental Analysis:

CAGR Calculations: Automatically calculates 5-year compound annual growth rates for net profits.

Strict Consistency Checks: Filters stocks based on projected price targets and historical growth reliability.

Valuation Tracking: Monitors 5-year price lows and projected upside potential.

Multi-Market Watchlists: Dedicated support for tracking and analyzing stocks across Canadian (TSX), US (NYSE/NASDAQ), and custom user-defined watchlists.

Interactive Dashboard: A clean, AJAX-powered interface for real-time price updates and quick filtering of the stock database.

🛠️ Technical Stack
Backend: Python 3.x, Django Web Framework

Data Science: Pandas, Scikit-learn (Random Forest)

Data Source: Yahoo Finance API (yfinance)

Database: SQLite (Development) / PostgreSQL (Production)

Frontend: HTML5, CSS3, JavaScript (AJAX)

🎯 Project Goals
The primary objective of this project is to bridge the gap between raw financial data and informed decision-making. By leveraging AI to process complex fundamental indicators, py-stock-watcher aims to provide a systematic, emotion-free approach to identifying value in the stock market.

How to use this in your Repo:
Open your README.md file.

Paste the content above.

Commit and push:

PowerShell
git add README.md
git commit -m "docs: add professional project introduction"
git push origin main

This project includes a few commands to fetch data and analyze data.
analyze_stocks -> update_historical_data -> compound_profit_price -> kelly_exp -> calculate_scores, these commands form a whole workflow to fetch stock price history, fluctuation, Yahoo finance rating, combined with local AI algorithm analysis.

You can simply run "python manage.py fetch-all-data" to execute the whole workflow to perform your daily stock analysis.
*As the public repo doesn't include my API key to the paid data center, it will cause an error when you run the code. 
