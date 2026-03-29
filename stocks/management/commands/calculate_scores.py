from django.core.management.base import BaseCommand

import os
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import time
from django.utils import timezone
from datetime import datetime

from stocks.models import Stock 
from stocks.models import UsStock
from stocks.models import CustomStock
from stocks.ai_model import StockPredictor
from stocks.models import StockScore  # <--- MAKE SURE THIS MATCHES YOUR APP NAME
from stocks.models import BacktestResult

##
# python manage.py calculate_scores
# 

class Command(BaseCommand):
    help = 'Calculates Stock Health Scores for a defined watchlist'

    # ==========================================
    # YOUR WATCHLIST (Edit this anytime)
    # ==========================================
    # WATCHLIST = [
    #     "SU.TO",   # Suncor
    #     "RY.TO",   # Royal Bank
    #     "TD.TO",   # TD Bank
    #     "SHOP.TO", # Shopify
    #     "CNQ.TO",  # Canadian Natural Resources
    #     "ENB.TO",  # Enbridge
    #     "BMO.TO",  # Bank of Montreal
    #     "CNR.TO",  # CN Railway
    #     "CP.TO",   # CP Railway
    #     "BCE.TO",  # BCE Inc
    # ]

    WATCHLIST = []
    tickers_CA = list(Stock.objects.order_by('symbol').values_list('symbol', flat=True))
    tickers_US = list(UsStock.objects.order_by('symbol').values_list('symbol', flat=True))
    tickers_CUSTOM = list(CustomStock.objects.order_by('symbol').values_list('symbol', flat=True))
    WATCHLIST.extend(tickers_CA)
    WATCHLIST.extend(tickers_US)
    WATCHLIST.extend(tickers_CUSTOM)
    # tickers = ["UPS", "AP-UN.TO", "TAL.TO", "TD.TO", "ENB.TO"] 
    WATCHLIST = list(set(WATCHLIST))
    WATCHLIST.sort()

    def handle(self, *args, **options):
        tickers = self.WATCHLIST
        self.stdout.write(self.style.MIGRATE_HEADING(f"--- Starting AI Analysis on {len(tickers)} Stocks ---"))
        
        # 1. FETCH LIVE DATA
        data = []
        
        for symbol in tickers:
            try:
                self.stdout.write(f"Fetching {symbol}...", ending='')
                stock = yf.Ticker(symbol)
                info = stock.info
                
                # We use .get() with defaults to prevent crashes if Yahoo data is missing
                metrics = {
                    'symbol': symbol,
                    'pe_ratio': info.get('forwardPE', info.get('trailingPE', 25.0)),
                    'roe': info.get('returnOnEquity', 0.1),
                    'debt_to_equity': info.get('debtToEquity', 100.0),
                    'profit_margins': info.get('profitMargins', 0.1),
                    'revenue_growth': info.get('revenueGrowth', 0.0)
                }
                
                # Basic validation: If P/E is None, skip it
                if metrics['pe_ratio'] is None:
                    metrics['pe_ratio'] = 25.0 # assume average
                    
                data.append(metrics)
                self.stdout.write(self.style.SUCCESS(" OK"))
                
                # Pause to be polite to the API
                time.sleep(0.5)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f" FAIL: {e}"))

        if not data:
            self.stdout.write(self.style.ERROR("No data found."))
            return

        df = pd.DataFrame(data)

        # 3. USE THE SEPARATE AI MODULE
        self.stdout.write("Training AI Model...")
        predictor = StockPredictor() # Initialize the class we made above
        
        self.stdout.write("Predicting Scores...")
        final_scores = predictor.predict(df) # Get the answer

        # 2. CREATE SYNTHETIC TRAINING DATA (The "Teacher")
        # We teach the AI what a "Good Stock" looks like using investing rules
        # logic: Good = Low PE, High ROE, Moderate Debt, Positive Growth
        
        # train_size = 2000
        # np.random.seed(42)
        
        # # Generate random companies
        # fake_pe = np.random.uniform(5, 60, train_size)
        # fake_roe = np.random.uniform(-0.1, 0.5, train_size)
        # fake_debt = np.random.uniform(0, 300, train_size)
        # fake_margins = np.random.uniform(-0.1, 0.4, train_size)
        # fake_growth = np.random.uniform(-0.2, 0.5, train_size)

        # X_train = pd.DataFrame({
        #     'pe_ratio': fake_pe,
        #     'roe': fake_roe,
        #     'debt_to_equity': fake_debt,
        #     'profit_margins': fake_margins,
        #     'revenue_growth': fake_growth
        # })

        # # The Rules: Label as "1" (Good) if it meets these strict criteria
        # y_train = np.where(
        #     (fake_pe < 25) & 
        #     (fake_roe > 0.12) & 
        #     (fake_debt < 150) & 
        #     (fake_growth > 0.05), 
        #     1, 0
        # )

        # # 3. TRAIN THE MODEL
        # rf = RandomForestClassifier(n_estimators=100, random_state=42)
        # rf.fit(X_train, y_train)

        # # 4. PREDICT SCORES FOR REAL STOCKS
        # X_real = df[['pe_ratio', 'roe', 'debt_to_equity', 'profit_margins', 'revenue_growth']]
        
        # # Get probability (0-1) and multiply by 100
        # scores = rf.predict_proba(X_real)[:, 1] * 100

        # # 5. STORE RESULTS IN DATABASE
        # self.stdout.write(self.style.MIGRATE_HEADING("\n--- Saving to Database ---"))
        
        # --- [NEW] Initialize list for CSV report ---
        report_data = []

        for (index, row), score in zip(df.iterrows(), final_scores):
            # final_score = int(scores[i])
            # final_score = int(score)
            # final_score_temp = int(score)
            final_score_temp = score['buy_prob']
            sell_score = score['sell_prob']
            # 1. Fetch Trust History
            trust_count = BacktestResult.objects.filter(ticker=row['symbol'], correct=1).count()
            untrust_count = BacktestResult.objects.filter(ticker=row['symbol'], correct=0).count()
            total = trust_count + untrust_count

            # 2. Calculate Trust Percentage
            trust_ratio = 0.5 # Default neutral if no history
            if total > 0:
                trust_ratio = trust_count / total

            # 3. PENALIZE THE SCORE if trust is low
            # If trust is 0%, the score becomes 0. If trust is 100%, score stays same.
            # This is a simple "Confidence Weighting"
            # final_score = final_score_temp * trust_ratio ##Single possibility doesn't matter with general trustworthy value.
            final_score = final_score_temp
            
            # Determine Recommendation Label
            if final_score >= 80:
                rec = "Strong Buy"
                color = self.style.SUCCESS
            elif final_score >= 70:
                rec = "Buy"
                color = self.style.SUCCESS
            # elif final_score <= 20:
            #     rec = "High Risk"
            #     color = self.style.ERROR
            # else:
            #     rec = "Hold"
            #     color = self.style.WARNING
            elif sell_score >= 85:
                rec = "Strong Sell"
                color = self.style.ERROR
            elif sell_score >= 70:
                rec = "Sell / High Risk"
                color = self.style.ERROR
            else:
                rec = "Hold"
                color = self.style.WARNING

            # Save to Django Database
            StockScore.objects.update_or_create(
                symbol=row['symbol'],
                defaults={
                    'score': final_score,
                    'buy_score': final_score_temp,  # Save the raw buy prob
                    'sell_score': sell_score,       # Save the raw sell prob
                    'recommendation': rec,
                    'pe_ratio': row['pe_ratio'],
                    'roe': row['roe'],
                    'debt_to_equity': row['debt_to_equity'],
                    'revenue_growth': row['revenue_growth'],
                }
            )

            # --- [NEW] Append data for CSV report ---
            report_data.append({
                'symbol': row['symbol'],
                'date': timezone.now().date(),
                'final_score': final_score,
                'recommendation': rec,
                'raw_model_score': final_score_temp,
                'trust_ratio': trust_ratio,
                'pe_ratio': row['pe_ratio'],
                'roe': row['roe'],
                'debt_to_equity': row['debt_to_equity'],
                'revenue_growth': row['revenue_growth'],
                'profit_margins': row['profit_margins']
            })
            
            self.stdout.write(color(f"{row['symbol']}: {final_score}/100 ({rec})"))

        self.update_trust_metrics()

        # --- [NEW] Generate and Save CSV Report ---
        if report_data:
            # 1. Create 'reports' directory if it doesn't exist
            report_dir = 'reports'
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)

            # 2. Generate Timestamped Filename (e.g., scores_2023-10-25_14-30-00.csv)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"scores_{timestamp}.csv"
            file_path = os.path.join(report_dir, filename)

            # 3. Convert to DataFrame and Save
            report_df = pd.DataFrame(report_data)
            report_df.to_csv(file_path, index=False)
            
            self.stdout.write(self.style.SUCCESS(f"Report saved to: {file_path}"))
        
        self.stdout.write(self.style.SUCCESS('Successfully updated scores and trust metrics.'))

    def update_trust_metrics(self):
        """
        Aggregates BacktestResult data and saves summaries to StockScore.
        """
        print("--- Aggregating Backtest Results into StockScore ---")
        
        # Get all scores (or all stocks you care about)
        # We loop through StockScore because that's where we save the data
        all_scores = StockScore.objects.all()

        count = 0
        for score_obj in all_scores:
            ticker = score_obj.symbol
            
            # Efficiently count from the Backtest History
            # correct=1 means Trustworthy
            # correct=0 means Untrustworthy
            trust_count = BacktestResult.objects.filter(ticker=ticker, correct=1).count()
            untrust_count = BacktestResult.objects.filter(ticker=ticker, correct=0).count()

            # Update the score object only if data changed (optimization)
            if (score_obj.trustworthy_count != trust_count or 
                score_obj.untrustworthy_count != untrust_count):
                
                score_obj.trustworthy_count = trust_count
                score_obj.untrustworthy_count = untrust_count
                score_obj.save()
                count += 1
        
        print(f"--- Updated Trust Metrics for {count} stocks ---")