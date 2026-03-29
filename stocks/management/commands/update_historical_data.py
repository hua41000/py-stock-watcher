# stocks/management/commands/update_historical_data.py

import requests
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
# REPLACE 'stocks' with your actual app name
from stocks.models import StockAnalysis 

##
# python manage.py update_historical_data
# python manage.py update_historical_data --years 5
# python manage.py update_historical_data --years 20
#
class Command(BaseCommand):
    help = 'Fetches historical high/low data for all stocks for a variable number of years.'

    def add_arguments(self, parser):
        # Allow the year to be a variable argument (defaults to 10 if not specified)
        parser.add_argument(
            '--years', 
            type=int, 
            default=10, 
            help='Number of years to look back (default: 10)'
        )

    def handle(self, *args, **options):
        # 1. Setup Variables
        years_back = options['years']
        api_key = ''  # Your FMP API Key
        
        # Calculate Dates
        current_date = datetime.date.today()
        to_date_str = f"{current_date.year}-12-31"
        start_year = current_date.year - years_back
        from_date_str = f"{start_year}-01-01"

        # Get all stocks from DB
        stocks = StockAnalysis.objects.all()
        total_stocks = stocks.count()

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"--- Starting Historical Update ---"
            f"\nPeriod: {years_back} Years ({from_date_str} to {to_date_str})"
            f"\nStocks to process: {total_stocks}"
        ))

        # 2. Loop through stocks
        for index, stock in enumerate(stocks, 1):
            symbol = stock.ticker
            
            # Construct FMP API URL
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={from_date_str}&to={to_date_str}&apikey={api_key}"
            
            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                
                # FMP returns data in a 'historical' list inside the dictionary
                historical_data = data.get('historical', [])

                if not historical_data:
                    self.stdout.write(self.style.WARNING(f"[{index}/{total_stocks}] No historical data found for {symbol}"))
                    continue

                # 3. Calculate Highs and Lows
                # Initialize with the first available day's data
                current_high = historical_data[0].get('high', 0)
                current_low = historical_data[0].get('low', float('inf'))

                for day in historical_data:
                    day_high = day.get('high')
                    day_low = day.get('low')

                    # Skip days with missing data
                    if day_high is None or day_low is None:
                        continue

                    if day_high > current_high: 
                        current_high = day_high
                    if day_low < current_low: 
                        current_low = day_low

                # 4. Save to Database
                # 4. LOGIC TO PREVENT UNNECESSARY SAVES
                # Check if the new values are different from what is already in the DB
                # or if the "years back" setting has changed.
                
                has_changed = (
                    stock.period_high != current_high or 
                    stock.period_low != current_low or 
                    stock.period_years != years_back
                )

                if has_changed:
                    stock.period_high = current_high
                    stock.period_low = current_low
                    stock.period_years = years_back
                    stock.history_updated_at = timezone.now()
                    
                    stock.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"[{index}/{total_stocks}] UPDATED {symbol}: High ${current_high} / Low ${current_low}"
                    ))
                else:
                    # Optional: Log that we skipped it
                    self.stdout.write(f"[{index}/{total_stocks}] SKIPPED {symbol} (No change)")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{index}/{total_stocks}] Error processing {symbol}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('--- Historical Data Update Complete ---'))