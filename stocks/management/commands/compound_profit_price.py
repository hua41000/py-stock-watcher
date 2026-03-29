import requests
from django.core.management.base import BaseCommand
from stocks.models import StockAnalysis

##
# python manage.py compound_profit_price
# python manage.py compound_profit_price --years 5
# python manage.py compound_profit_price --years 20
#

class Command(BaseCommand):
    help = 'Strictly updates DB with Net Profit CAGR and Projected Prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years', 
            type=int, 
            default=5, 
            help='Number of years for the compound calculation'
        )

    def handle(self, *args, **options):
        years_back = options['years']
        api_key = ''
        stocks = StockAnalysis.objects.all()

        self.stdout.write(self.style.MIGRATE_HEADING(f"--- Starting {years_back}Y Strict Compound Analysis ---"))

        for stock in stocks:
            symbol = stock.ticker
            limit = years_back + 1 # We need X+1 years to get X years of growth
            
            # 1. Fetch Income Statement
            url = f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?limit={limit}&apikey={api_key}"
            
            try:
                response = requests.get(url)
                data = response.json()
                
                if not data or len(data) < limit:
                    stock.analysis_note_compound = f"insufficient data (needed {limit} years)"
                    stock.compound_profit_rate = None
                    stock.projected_price_by_profit = None
                    stock.period_low_compound = None
                    stock.period_years_compound = None
                    stock.save()
                    continue

                # Profits: Reverse from [Newest...Oldest] to [Oldest...Newest]
                profits = [item['netIncome'] for item in data[:limit]][::-1]

                # 2. Strict Consistency Check
                # # Rule A: Each year MUST be higher than the previous year
                # is_strictly_increasing = all(profits[i+1] > profits[i] for i in range(len(profits)-1))
                # # Rule B: No losses allowed (all must be > 0)
                # has_no_losses = all(p > 0 for p in profits)

                # if not is_strictly_increasing or not has_no_losses:
                #     stock.analysis_note_compound = "inconsistent increasing net profit"
                #     # Reset calculated fields so old data doesn't persist
                #     stock.compound_profit_rate = None
                #     stock.projected_price_by_profit = None
                #     stock.period_low_compound = None
                #     stock.period_years_compound = None
                #     stock.save()
                #     self.stdout.write(self.style.WARNING(f"{symbol}: Failed strict growth check."))
                #     continue

                # Count specifically how many years declined or stayed flat
                decline_years = 0
                flat_years = 0
                prof_loss_years = 0
                
                for i in range(len(profits) - 1):
                    current = profits[i+1]
                    previous = profits[i]
                    
                    if current < previous:
                        # Decline: Dropped by more than 25% (less than 75% of prev)
                        if current < (previous * 0.75):
                            decline_years += 1
                        # Flat: Dropped, but stayed above 75% threshold
                        else:
                            flat_years += 1
                    elif current == previous:
                        # Flat: Exactly the same
                        flat_years += 1
                
                # has_no_losses = all(p > 0 for p in profits)
                loss_years = sum(1 for p in profits if p <= 0)

                # Determine the descriptive note
                if decline_years == 0 and flat_years == 0 and loss_years == 0:
                    current_note = f"{years_back}-Y strict increase"
                else:
                    parts = []
                    if decline_years > 0:
                        parts.append(f"{decline_years}-Y decline")
                    if flat_years > 0:
                        parts.append(f"{flat_years}-Y flat")
                    # if not has_no_losses:
                    #     parts.append("contains profit losses")
                    if loss_years > 0:
                        parts.append(f"{loss_years}-Y loss")
                    current_note = ", ".join(parts)

                # 3. Data Overwrite Protection (The Loophole Fix)
                # If there are ANY declines or more than 1 flat year, we reset the numeric data
                # but keep the descriptive note so you know why it failed.
                if decline_years > 0 or flat_years > 2 or loss_years > 0:
                    # CRITICAL: If ANY loss years exist, we MUST skip CAGR to avoid Complex Number crash
                    # if loss_years > 0:
                    stock.analysis_note_compound = current_note
                    stock.compound_profit_rate = None
                    stock.projected_price_by_profit = None
                    stock.period_low_compound = None
                    stock.period_years_compound = None
                    stock.save()
                    self.stdout.write(self.style.WARNING(f"{symbol}: Failed by profit decline to less than 75%, flat year more than 1 or profit loss year."))
                    continue

                # 3. Calculate CAGR
                # Formula: (End Value / Start Value)^(1/Years) - 1
                start_val = profits[0]
                end_val = profits[-1]
                cagr = (end_val / start_val)**(1 / years_back) - 1

                # 4. Fetch Period Low (252 trading days per year)
                price_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?serietype=line&apikey={api_key}"
                price_data = requests.get(price_url).json()
                historical = price_data.get('historical', [])[:(years_back * 252)]
                
                if not historical:
                    stock.analysis_note_compound = "missing price history"
                    stock.compound_profit_rate = None
                    stock.projected_price_by_profit = None
                    stock.period_low_compound = None
                    stock.period_years_compound = None
                    self.stdout.write(self.style.WARNING(f"{symbol}: Failed by missing price history."))
                    stock.save()
                    continue
                
                low_price = min(day['close'] for day in historical)

                # 5. Calculate Projected Price
                # Formula: Period Low * (1 + CAGR)^Years
                proj_price = low_price * ((1 + cagr) ** years_back)

                # 6. Save to DB
                stock.period_low_compound = low_price
                stock.period_years_compound = years_back
                stock.compound_profit_rate = cagr
                stock.projected_price_by_profit = proj_price
                # stock.analysis_note_compound = f"Strict {years_back}Y growth confirmed"
                stock.analysis_note_compound = current_note
                stock.save()

                self.stdout.write(self.style.SUCCESS(f"✓ {symbol}: CAGR {cagr:.2%} | Projected: ${proj_price:.2f}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error {symbol}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"--- {years_back}Y Update Complete ---"))