import yfinance as yf
from decimal import Decimal
from django.core.management.base import BaseCommand
from stocks.models import Stock, UsStock, CustomStock, StockAnalysis

import os
import csv
from django.conf import settings
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fetches live financial data with Sticky History logic to track analyst changes.'

    def handle(self, *args, **kwargs):
        # 1. Collect all tickers from your database models
        tickers = []
        tickers_CA = list(Stock.objects.values_list('symbol', flat=True))
        tickers_US = list(UsStock.objects.values_list('symbol', flat=True))
        tickers_CUSTOM = list(CustomStock.objects.values_list('symbol', flat=True))
        
        tickers.extend(tickers_CA)
        tickers.extend(tickers_US)
        tickers.extend(tickers_CUSTOM)
        
        tickers = sorted(list(set(tickers))) # Unique and sorted
        
        self.stdout.write(f"Starting Sticky Analysis for {len(tickers)} tickers...")

        for ticker in tickers:
            try:
                # 2. Fetch fresh data from Yahoo Finance
                yf_ticker = yf.Ticker(ticker)
                info = yf_ticker.info
                
                # Raw API data (In-Memory)
                current_price_raw = info.get('currentPrice')
                new_target_raw = info.get('targetMeanPrice')
                target_high_raw = info.get('targetHighPrice')
                target_low_raw = info.get('targetLowPrice')
                
                # Process Rating (e.g., "buy" -> "Buy")
                raw_rating = info.get('recommendationKey', 'neutral')
                new_rating = raw_rating.replace('_', ' ').capitalize()

                # 3. Retrieve existing record (The "Memory")
                analysis_obj, created = StockAnalysis.objects.get_or_create(ticker=ticker)

                # --- STICKY HISTORY LOGIC ---
                # We only shift the data if the new API target is different from our stored target.
                if new_target_raw and analysis_obj.analyst_target:
                    new_val_dec = Decimal(new_target_raw)
                    old_val_dec = analysis_obj.analyst_target
                    
                    if new_val_dec > old_val_dec:
                        analysis_obj.price_action = "Raises"
                        analysis_obj.previous_target = old_val_dec
                        analysis_obj.analyst_target = new_val_dec
                    elif new_val_dec < old_val_dec:
                        analysis_obj.price_action = "Lowers"
                        analysis_obj.previous_target = old_val_dec
                        analysis_obj.analyst_target = new_val_dec
                    # ELSE: new_val == old_val, so we do NOTHING. 
                    # This keeps the 'Raises' or 'Lowers' state active in the DB.
                
                elif new_target_raw and not analysis_obj.analyst_target:
                    # First time capturing data for this stock
                    analysis_obj.analyst_target = Decimal(new_target_raw)
                    analysis_obj.price_action = "Maintains"

                # 4. Update non-historical fields (Metrics that change daily)
                if current_price_raw:
                    analysis_obj.current_price = Decimal(current_price_raw)
                
                # Update targets and other metrics
                analysis_obj.analyst_target_high = Decimal(target_high_raw) if target_high_raw else None
                analysis_obj.analyst_target_low = Decimal(target_low_raw) if target_low_raw else None
                analysis_obj.analyst_rating = new_rating
                
                # Calculate Upside % based on the freshest price
                if analysis_obj.current_price and analysis_obj.analyst_target:
                    upside = ((analysis_obj.analyst_target - analysis_obj.current_price) / analysis_obj.current_price) * 100
                    analysis_obj.upside_percent = Decimal(upside)

                # Update Ratios
                pb = info.get('priceToBook')
                div = info.get('dividendYield', 0)
                beta = info.get('beta')
                
                analysis_obj.pb_ratio = Decimal(pb) if pb else None
                analysis_obj.dividend_yield = Decimal(div) if div else None
                analysis_obj.beta = Decimal(beta) if beta else None

                # 5. Verdict Engine (Re-running rules based on updated data)
                verdict = "Neutral"
                if analysis_obj.current_price and analysis_obj.analyst_target_low:
                    if analysis_obj.current_price < analysis_obj.analyst_target_low:
                        verdict = "💎 Undervalued (Below Low)"
                    elif analysis_obj.upside_percent > 20 or (analysis_obj.pb_ratio and analysis_obj.pb_ratio < 1.0):
                        verdict = "🚀 High Potential"
                    elif analysis_obj.beta and analysis_obj.beta < 0.85 and analysis_obj.dividend_yield > 2.0:
                        verdict = "🛡️ Defensive/Safe"
                    elif analysis_obj.analyst_target_high and analysis_obj.current_price > analysis_obj.analyst_target_high:
                        verdict = "⚠️ Overvalued"
                
                analysis_obj.verdict = verdict

                # 6. Final Save to DB
                analysis_obj.save()
                
                self.stdout.write(self.style.SUCCESS(f"✔ {ticker}: {analysis_obj.price_action} ({verdict})"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✘ Error processing {ticker}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("All stocks processed successfully."))

        self.save_to_csv()
        self.stdout.write(self.style.SUCCESS("All stocks processed and CSV exported successfully."))

    def save_to_csv(self):
        """Exports the StockAnalysis database table to a CSV file with cleaned verdicts."""
        root_path = settings.BASE_DIR
        folder_path = os.path.join(root_path, 'reports')
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"analyze-stocks-{timestamp}.csv"
        file_path = os.path.join(folder_path, filename)

        queryset = StockAnalysis.objects.all()
        fields = [field.name for field in StockAnalysis._meta.fields]

        # Define the cleaning map for your Verdicts
        verdict_map = {
            "🚀 High Potential": "High Potential",
            "💎 Undervalued (Below Low)": "Undervalued",
            "🛡️ Defensive/Safe": "Defensive/Safe",
            "⚠️ Overvalued": "Overvalued"
        }

        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(fields)

                for obj in queryset:
                    row = []
                    for field in fields:
                        value = getattr(obj, field)
                        
                        # Check if this specific field is 'verdict' and clean it
                        if field == 'verdict' and value in verdict_map:
                            value = verdict_map[value]
                            
                        row.append(value)
                    writer.writerow(row)
            
            self.stdout.write(self.style.MIGRATE_LABEL(f"CSV Report generated (Cleaned): {file_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to generate CSV: {str(e)}"))