import requests
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from stocks.models import Stock, UsStock, CustomStock, StockAnalysis
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

class Command(BaseCommand):
    help = 'Global Sector-Aware AI Trading System'

    def handle(self, *args, **options):
        API_KEY = ""
        DURATION = 15 
        HORIZON = 3    
        FEATURES = ['revenueGrowth', 'netIncomeGrowth', 'freeCashFlowGrowth']

        # 1. CONSOLIDATE ALL TICKERS
        tickers = list(set(
            list(Stock.objects.values_list('symbol', flat=True)) +
            list(UsStock.objects.values_list('symbol', flat=True)) +
            list(CustomStock.objects.values_list('symbol', flat=True))
        ))

        all_samples = []
        self.stdout.write(self.style.WARNING(f"Phase 1: Collecting data for {len(tickers)} symbols..."))

        # 2. DATA COLLECTION LOOP
        for symbol in tickers:
            try:
                # 1. Fetch Growth Data (Primary data source)
                growth_url = f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit={DURATION}&apikey={API_KEY}"
                response = requests.get(growth_url)
                growth_data = response.json()

                # Validate data existence and length
                if not growth_data or len(growth_data) <= HORIZON:
                    self.stdout.write(self.style.WARNING(f"Error: Insufficient data for {symbol}"))
                    # Using return or continue depending on your loop structure
                    continue 

                # 2. Fetch Sector (Only if growth data is valid)
                profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
                profile = requests.get(profile_url).json()
                sector = profile[0].get('sector', 'Unknown') if (profile and isinstance(profile, list)) else 'Unknown'

                # 3. Vectorized Data Processing
                df = pd.DataFrame(growth_data)
                
                # Pre-calculating target allows us to drop NaN rows immediately
                df['target'] = df['revenueGrowth'].shift(HORIZON)
                df = df.dropna(subset=['target']) # Remove rows where target couldn't be shifted
                
                df['ticker_ref'] = symbol
                df['sector'] = sector
                
                all_samples.append(df)

                # Success output
                self.stdout.write(self.style.SUCCESS(f"Success: {symbol} data collected and processed."))

            except requests.exceptions.RequestException as req_err:
                self.stdout.write(self.style.ERROR(f"Network Error for {symbol}: {req_err}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {symbol}: {str(e)}"))

        if not all_samples:
            self.stdout.write(self.style.ERROR("No data collected."))
            return

        # 3. GLOBAL PREPROCESSING
        master_df = pd.concat(all_samples).dropna(subset=['target'] + FEATURES)
        # Apply One-Hot Encoding to the entire dataset at once
        master_df_encoded = pd.get_dummies(master_df, columns=['sector'])
        
        # Define the exact feature list used for training
        sector_cols = [col for col in master_df_encoded.columns if col.startswith('sector_')]
        updated_features = FEATURES + sector_cols

        # 4. TRAIN GLOBAL BRAIN
        self.stdout.write(self.style.WARNING(f"Phase 2: Training Global Model on {len(master_df_encoded)} samples..."))
        X_global = master_df_encoded[updated_features]
        y_global = master_df_encoded['target']
        
        global_model = RandomForestRegressor(n_estimators=200, random_state=42)
        global_model.fit(X_global, y_global)
        
        # Calculate Global Volatility for probability logic
        global_predictions = global_model.predict(X_global)
        global_volatility = np.std(y_global - global_predictions)

        # 5. INDIVIDUAL PREDICTION & ANALYSIS
        self.stdout.write(self.style.WARNING("Phase 3: Generating individual stock analyses..."))
        for symbol in tickers:
            try:
                # Extract this stock's specific data from the encoded master pool
                stock_data = master_df_encoded[master_df_encoded['ticker_ref'] == symbol]
                if stock_data.empty:
                    continue

                analysis, _ = StockAnalysis.objects.get_or_create(ticker=symbol)
                
                # --- THE FIX: Reindex ensures the stock has all sector columns, even if 0 ---
                X_stock = stock_data[updated_features].reindex(columns=updated_features, fill_value=0)
                y_stock = stock_data['target']
                
                predictions = global_model.predict(X_stock)

                # Metrics
                analysis.backtest_sample_count = len(stock_data)
                analysis.kelly_accuracy_score = round(max(0, r2_score(y_stock, predictions) * 100), 2)
                analysis.kelly_avg_error_margin = round(float(mean_absolute_error(y_stock, predictions)) * 100, 2)

                # Probability Logic (using global patterns)
                denom = (1.0 + global_volatility)
                raw_p2 = 1.0 / denom
                raw_p1 = global_volatility * 0.5
                raw_p3 = global_volatility * 0.5
                total = raw_p1 + raw_p2 + raw_p3

                analysis.p1, analysis.p2, analysis.p3 = round(raw_p1/total, 2), round(raw_p2/total, 2), round(raw_p3/total, 2)

                # Predict Current Case
                latest_metrics = X_stock.iloc[[0]]
                base_case_growth = float(global_model.predict(latest_metrics)[0])
                
                analysis.price2 = base_case_growth
                analysis.price1 = -0.85 
                analysis.price3 = base_case_growth + (2 * global_volatility)

                if analysis.current_price:
                    cp = float(analysis.current_price)
                    impact = ((1 + analysis.price1) * analysis.p1) + \
                             ((1 + analysis.price2) * analysis.p2) + \
                             ((1 + analysis.price3) * analysis.p3)
                    analysis.expected_target_price = cp * impact

                analysis.save()
                self.stdout.write(f"  - {symbol}: Analyzed via Global Model")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - {symbol}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("System Update Complete: All stocks processed with Sector Context."))