import os
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, accuracy_score, roc_curve
import matplotlib.pyplot as plt
from django.utils import timezone

from stocks.models import Stock, UsStock, CustomStock
# --- IMPORT YOUR MODELS ---
from stocks.models import AIModelLog, BacktestResult

class StockPredictor:
    def __init__(self, auto_train=True):
        """Create predictor. Trains on real data by default."""
        self.model = None
        self.api_key = os.getenv("FMP_API_KEY", "")
        self.years_limit = 10
        self.quarters_limit = self.years_limit * 4 
        
        # THE TEACHERS:
        # A list of diverse, liquid stocks the AI will "study" to learn patterns.
        # We mix US and Canadian stocks to get good data.
        # self.teacher_tickers = ["AAPL", "MSFT", "GOOGL", "JPM", "XOM", "TD", "RY", "SU", "SHOP", "ENB"]
        # self.teacher_tickers = []

        # option 2:
        # self.teacher_tickers = [
        #     # --- GLOBAL TECH LEADERS (Rules of Growth) ---
        #     "AAPL", "MSFT", "GOOGL", "NVDA", "SHOP.TO", # SHOP is Canadian!
        #     "OTEX.TO", # OpenText (Canadian Tech)

        #     # --- CANADIAN BANKS (The "Big 5" Stability Rules) ---
        #     "RY.TO",   # Royal Bank of Canada
        #     "TD.TO",   # TD Bank
        #     "BMO.TO",  # Bank of Montreal
        #     "BNS.TO",  # Scotiabank
        #     "CM.TO",   # CIBC

        #     # --- CANADIAN ENERGY (Oil Sands & Pipelines) ---
        #     "SU.TO",   # Suncor Energy
        #     "CNQ.TO",  # Canadian Natural Resources
        #     "ENB.TO",  # Enbridge
        #     "TRP.TO",  # TC Energy
        #     "CVE.TO",  # Cenovus Energy

        #     # --- CANADIAN UTILITIES & TELECOM (Dividend Safety) ---
        #     "BCE.TO",  # BCE Inc (Bell)
        #     "TU",   # Telus (Ticker is 'TU' on NYSE)
        #     "RCI-B.TO",  # Rogers Communications
        #     "FTS.TO",  # Fortis Inc.
        #     "AQN.TO",  # Algonquin Power

        #     # --- CANADIAN RAIL & INDUSTRIAL ---
        #     "CNR.TO",  # CN Railway
        #     "CP.TO",   # CP Kansas City
        #     "WCN.TO",  # Waste Connections (Dual listed)

        #     # --- CANADIAN MATERIALS (Gold & Fertilizer) ---
        #     "NTR.TO",  # Nutrien (Potash/Agri)
        #     "ABX.TO", # Barrick Gold (Ticker is 'GOLD')
        #     "AEM.TO",  # Agnico Eagle Mines
        #     "TECK-B.TO", # Teck Resources

        #     # --- RETAIL CONSUMER (Mix of US/CA) ---
        #     "WMT",  # Walmart (US - Benchmark for retail)
        #     "COST", # Costco (US - Benchmark for efficiency)
        #     "ATD.TO",  # Alimentation Couche-Tard (Check if API supports ATD, if not use US peers)
        # ]
        
        # option 3:
        tickers = []
        tickers_CA = list(Stock.objects.order_by('symbol').values_list('symbol', flat=True))
        tickers_US = list(UsStock.objects.order_by('symbol').values_list('symbol', flat=True))
        tickers_CUSTOM = list(CustomStock.objects.order_by('symbol').values_list('symbol', flat=True))
        tickers.extend(tickers_CA)
        tickers.extend(tickers_US)
        tickers.extend(tickers_CUSTOM)

        self.teacher_tickers = list(set(tickers))
        self.teacher_tickers.sort()

        if auto_train:
            print("   [AI] Initializing and training on real history...")
            self._train_with_real_data()

    def _train_with_real_data(self):
        """Fetches data, runs a backtest, logs results to DB, and trains final model."""
        training_data = []

        print(f"   [AI] Fetching data for {len(self.teacher_tickers)} teacher stocks...")

        for ticker in self.teacher_tickers:
            try:
                # 1. Get Historical Ratios (The "X" - Features)
                # We ask for 5 years of annual data
                url = f"https://financialmodelingprep.com/api/v3/ratios/{ticker}?period=quarter&limit={self.quarters_limit}&apikey={self.api_key}"
                ratios = requests.get(url).json()
                
                if not ratios or (isinstance(ratios, dict) and 'Error' in ratios):
                    continue

                # 2. Get Price History (The "Y" - Target)
                # We need 10 years to ensure we cover the 5 years of ratio data + 1 year future lookahead
                stock = yf.Ticker(ticker)
                hist = stock.history(period="10y")

                # Normalize timezone handling safely
                try:
                    if getattr(hist.index, 'tz', None) is not None:
                        hist.index = hist.index.tz_convert('UTC').tz_localize(None)
                except Exception:
                    pass

                for year_data in ratios:
                    date_str = year_data.get('date')
                    if not date_str: continue

                    report_date = pd.to_datetime(date_str)

                    # FIND TARGET: Did price go up 1 year later?
                    try:
                        price_then = hist['Close'].reindex(pd.DatetimeIndex([report_date]), method='ffill').iloc[0]
                        future_date = report_date + pd.DateOffset(years=1)
                        price_future = hist['Close'].reindex(pd.DatetimeIndex([future_date]), method='ffill').iloc[0]

                        if pd.isna(price_then) or pd.isna(price_future):
                            continue

                        target = 1 if price_future > price_then else 0

                        # BUILD ROW (Now includes Ticker and Date)
                        row = {
                            'ticker': ticker,               # <--- KEEPING THIS FOR DB
                            'date': report_date,            # <--- KEEPING THIS FOR DB
                            'pe_ratio': year_data.get('priceEarningsRatio'),
                            'roe': year_data.get('returnOnEquity'),
                            'debt_to_equity': year_data.get('debtEquityRatio'),
                            'profit_margins': year_data.get('netProfitMargin'),
                            'revenue_growth': 0.05, 
                            'Target': target
                        }
                        training_data.append(row)

                    except Exception:
                        continue
            except Exception as e:
                print(f"   [AI] Failed to train on {ticker}: {e}")

        # Convert to DataFrame
        if not training_data:
            print("   [AI] WARNING: No training data found. Using fallback synthetic model.")
            self._train_synthetic_fallback()
            return

        df_train = pd.DataFrame(training_data)
        df_train = df_train.replace([np.inf, -np.inf], np.nan).dropna()

        # Define Features (X) - Exclude ticker/date for the actual AI training
        feature_cols = ['pe_ratio', 'roe', 'debt_to_equity', 'profit_margins', 'revenue_growth']

        # ---------------------------------------------------------
        # STEP 1: TEST SPLIT (Split the ROWS, not just X/y)
        # ---------------------------------------------------------
        # We split the whole dataframe so we keep the tickers associated with the test set
        train_df, test_df = train_test_split(df_train, test_size=0.2, random_state=42)

        # Prepare Training Sets
        X_train = train_df[feature_cols]
        y_train = train_df['Target']
        
        # Prepare Test Sets
        X_test = test_df[feature_cols]
        y_test = test_df['Target']

        # Train Test Model
        # Option 1: Simple Random Forest (Good for tabular data and interpretability)
        # test_model = RandomForestClassifier(n_estimators=100, random_state=42)
        # test_model.fit(X_train, y_train)

        # Predict
        # predictions = best_eval_model.predict(X_test)
        # probs = best_eval_model.predict_proba(X_test)[:, 1] # Get confidence score (0.0 to 1.0)

        # # Calculate Metrics
        # acc = accuracy_score(y_test, predictions)
        # prec = precision_score(y_test, predictions, zero_division=0)

        # print("\n   [AI] --- Training Report ---")
        # print(f"   [AI] Data Points: {len(df_train)} (Split: {len(X_train)} Train, {len(X_test)} Test)")
        # print(f"   [AI] Accuracy:  {acc:.2%}")
        # print(f"   [AI] Precision: {prec:.2%}")

        # Option 2: Grid Search CV for Hyperparameter Tuning (Uncomment if you want to try this, but it will be slower)
        # Define the search grid
        rf_params = {
            'n_estimators': [50, 100],
            'max_depth': [10, 20, None],
        }

        # Run GridSearchCV on the TRAINING set only
        grid_search = GridSearchCV(
            RandomForestClassifier(random_state=42),
            param_grid=rf_params,
            cv=3, 
            scoring='precision', # Or 'roc_auc' depending on your goal
            n_jobs=-1
        )
        grid_search.fit(X_train, y_train)

        # This is your "Honest" best model
        best_eval_model = grid_search.best_estimator_
        
        # Get metrics by testing this best model on the TEST SET (unseen data)
        test_preds = best_eval_model.predict(X_test)
        test_probs = best_eval_model.predict_proba(X_test)[:, 1]

        # Calculate the metrics you will save to Django
        metrics_to_save = {
            'accuracy': accuracy_score(y_test, test_preds),
            'precision': precision_score(y_test, test_preds, zero_division=0),
            'recall': recall_score(y_test, test_preds, zero_division=0),
            'f1_score': f1_score(y_test, test_preds, zero_division=0),
            'roc_auc': roc_auc_score(y_test, test_probs)
        }
        

        # ---------------------------------------------------------
        # STEP 2: SAVE TO DATABASE
        # ---------------------------------------------------------
        # Using update_or_create is cleaner than an if/else block
        log_entry, created = AIModelLog.objects.update_or_create(
            id=1, # Assuming you only keep one primary log
            defaults={
                'accuracy': metrics_to_save['accuracy'],
                'precision': metrics_to_save['precision'],
                'recall': metrics_to_save['recall'],
                'f1_score': metrics_to_save['f1_score'],
                'roc_auc': metrics_to_save['roc_auc'],
                'data_points': len(df_train),
                'timestamp': timezone.now()
            }
        )
        
        # Clear old results
        log_entry.results.all().delete()

        # Create Detailed Backtest Rows
        results_list = []
        test_df = test_df.reset_index(drop=True)

        # 2. Create Detailed Backtest Rows
        results_list = []
        test_df = test_df.reset_index(drop=True) # Reset index to align with predictions array
        
        for i, row in test_df.iterrows():
            # FIX: Use test_probs and test_preds here!
            is_correct = 1 if test_preds[i] == y_test.iloc[i] else 0
            results_list.append(BacktestResult(
                log=log_entry,
                ticker=row['ticker'],
                date=row['date'],
                prob_score=test_probs[i] * 100, # Fixed variable
                prediction=test_preds[i],      # Fixed variable
                actual_target=y_test.iloc[i],
                correct=is_correct
            ))
        
        # Bulk create is much faster than loop saving
        BacktestResult.objects.bulk_create(results_list)
        print(f"   [AI] Logged {len(results_list)} backtest results to DB.")

        # ---------------------------------------------------------
        # STEP 3: FINAL TRAINING (For Live Use)
        # ---------------------------------------------------------
        # Train on 100% of the data for maximum smarts
        # FIX: Use the winning parameters from GridSearch!
        best_params = grid_search.best_params_
        print(f"   [AI] Training final model with best params: {best_params}")

        self.model = RandomForestClassifier(**best_params, oob_score=True, random_state=42)
        
        # Use full dataset
        X_all = df_train[feature_cols]
        y_all = df_train['Target']
        
        self.model.fit(X_all, y_all)

        # Update the Log with the Out-of-Bag (OOB) score
        if hasattr(self.model, 'oob_score_'):
            log_entry.oob_accuracy = self.model.oob_score_
            log_entry.save()
            print(f"   [AI] Final Model OOB Accuracy: {self.model.oob_score_:.2%}")

        print(f"   [AI] Final Model trained and ready.")

    def _train_synthetic_fallback(self):
        """Original fake data method, just in case API fails"""
        pass

    def predict(self, df):
        if not self.model:
            print("[AI] Model not ready.")
            return []
            
        X_real = df[['pe_ratio', 'roe', 'debt_to_equity', 'profit_margins', 'revenue_growth']]
        X_real = X_real.fillna(0) 
        
        # --- UPDATED FOR SELL LOGIC ---
        # Instead of just taking the 'Buy' probability, we get the full probability matrix.
        # probabilities[:, 1] = Confidence in price going UP (Buy Score)
        # probabilities[:, 0] = Confidence in price going DOWN/STAGNANT (Sell Score)
        probabilities = self.model.predict_proba(X_real)
        
        # We return a list of dictionaries so calculate_scores.py can distinguish 
        # between a "Weak Buy" and a "Strong Sell".
        results = []
        for prob in probabilities:
            results.append({
                'buy_prob': int(prob[1] * 100),
                'sell_prob': int(prob[0] * 100)
            })
            
        return results # Returns a list of dicts instead of just a list of ints