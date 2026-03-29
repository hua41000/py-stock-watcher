from django.shortcuts import render
from django.http import JsonResponse
import json
import requests, datetime
from .models import Stock 
from .models import UsStock
from .models import CustomStock
from .models import StockAnalysis
from .models import StockScore
from .models import AIModelLog
from django.db.models import Sum, Count
from stocks.models import StockAnalysis, StockScore, BacktestResult


def home(request):
    return render(request, 'home.html')

# 1. The Search Page View
def stock_symbol(request):
    api_key = '' # Ideally, hide this in env variables later
    search_results = None
    
    # 1. Check if the user submitted data (GET request with parameters)
    query = request.GET.get('query')
    exchange = request.GET.get('exchange')

    # --- DEBUGGING PRINT ---
    print(f"DEBUG CHECK: Query is '{query}' and Exchange is '{exchange}'")
    # -----------------------

    # 2. Build the API URL dynamically
    # url = f"https://financialmodelingprep.com/api/v3/search?query={query}&exchange={exchange}&apikey={api_key}"
    # if query and exchange, then concate the query based on condition.
    if query != "":
        qString = f"query={query}"
    if exchange != "":
        qString = f"{qString}&exchange={exchange}"
    
    url = f"https://financialmodelingprep.com/api/v3/search?{qString}&apikey={api_key}"
        
    # --- DEBUGGING PRINT ---
    print(f"DEBUG CHECK: Calling URL -> {url}")
    # -----------------------

    # 3. Make the request (CURL equivalent)
    response = requests.get(url)
    
    # 4. If the call was successful (HTTP 200), get the JSON data
    if response.status_code == 200:
        search_results = response.json()

    print(f"search_results: {search_results}")

    # 5. Render the page with the results (if any)
    return render(request, 'stock_symbol.html', {
        'search_results': search_results,
        'query': query,
        'exchange': exchange
    })

# 2. The AJAX Handler (Hidden)
def add_stock_ajax(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from JavaScript
            data = json.loads(request.body)
            symbol = data.get('symbol')
            
            # Check for duplicates
            if Stock.objects.filter(symbol=symbol).exists():
                return JsonResponse({'status': 'exists', 'message': f'{symbol} is already in your list.'})
            
            # Save to DB
            Stock.objects.create(
                symbol=symbol,
                name=data.get('name'),
                currency=data.get('currency'),
                exchange=data.get('exchange')
            )
            return JsonResponse({'status': 'success', 'message': 'Saved successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid_request'}, status=400)

# 2. The AJAX Handler (Hidden)
def add_us_stock_ajax(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from JavaScript
            data = json.loads(request.body)
            symbol = data.get('symbol')
            
            # Check for duplicates
            if UsStock.objects.filter(symbol=symbol).exists():
                return JsonResponse({'status': 'exists', 'message': f'{symbol} is already in your list.'})
            
            # Save to DB
            UsStock.objects.create(
                symbol=symbol,
                name=data.get('name'),
                currency=data.get('currency'),
                exchange=data.get('exchange')
            )
            return JsonResponse({'status': 'success', 'message': 'Saved successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid_request'}, status=400)

# 2. The AJAX Handler (Hidden)
def add_custom_stock_ajax(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from JavaScript
            data = json.loads(request.body)
            symbol = data.get('symbol')
            
            # Check for duplicates
            if CustomStock.objects.filter(symbol=symbol).exists():
                return JsonResponse({'status': 'exists', 'message': f'{symbol} is already in your list.'})
            
            # Save to DB
            CustomStock.objects.create(
                symbol=symbol,
                name=data.get('name'),
                currency=data.get('currency'),
                exchange=data.get('exchange')
            )
            return JsonResponse({'status': 'success', 'message': 'Saved successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid_request'}, status=400)

def stock_list(request):
    # 1. Fetch all data from the database
    # all_stocks = Stock.objects.all().order_by('-created_at') # Newest first
    all_stocks = Stock.objects.all().order_by('symbol') # Newest first
    print(all_stocks)
    # 2. Send it to the template
    return render(request, 'stock_list.html', {'stocks': all_stocks})

def stock_us_list(request):
    # 1. Fetch all data from the database
    # all_stocks = Stock.objects.all().order_by('-created_at') # Newest first
    all_stocks = UsStock.objects.all().order_by('symbol') # Newest first
    
    # 2. Send it to the template
    return render(request, 'stock_us_list.html', {'stocks': all_stocks})

def stock_custom_list(request):
    # 1. Fetch all data from the database
    # all_stocks = Stock.objects.all().order_by('-created_at') # Newest first
    all_stocks = CustomStock.objects.all().order_by('symbol') # Newest first
    
    # 2. Send it to the template
    return render(request, 'stock_custom_list.html', {'stocks': all_stocks})

def get_stock_details(request):
    symbol = request.GET.get('symbol')
    api_key = ''
    
    if symbol:
        # Call the external API from Python (Server-side)
        url = f"https://financialmodelingprep.com/api/v3/stock-price-change/{symbol}?apikey={api_key}"
        response = requests.get(url)
        
        # Return the data to our Frontend
        # safe=False is required because this API returns a List, not a Dictionary
        return JsonResponse(response.json(), safe=False)
        
    return JsonResponse({'error': 'No symbol provided'}, status=400)

def get_historical_analysis(request):
    symbol = request.GET.get('symbol')
    # Default to 10 years if not provided in the request
    years_back = int(request.GET.get('years', 10)) 
    api_key = ''

    if symbol:
        # 1. Calculate Dates
        current_date = datetime.date.today()
        to_date_str = f"{current_date.year}-12-31" # End of current year
        
        start_year = current_date.year - years_back
        from_date_str = f"{start_year}-01-01" # Start of the past year

        # 2. Build URL
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={from_date_str}&to={to_date_str}&apikey={api_key}"
        
        print(f"DEBUG: Fetching {url}") # Helpful for debugging
        
        response = requests.get(url)
        data = response.json()

        # 3. Process Data (Find Highs/Lows)
        yearly_stats = {}
        global_high = -1
        global_low = float('inf')

        # The API returns a dictionary with a "historical" key containing the list
        historical_data = data.get('historical', [])

        for day in historical_data:
            date_str = day.get('date') # Format: "2025-12-14"
            year = date_str[:4]        # Extract "2025"
            high = day.get('high')
            low = day.get('low')

            # Update Global Stats
            if high > global_high: global_high = high
            if low < global_low: global_low = low

            # Update Yearly Stats
            if year not in yearly_stats:
                yearly_stats[year] = {'high': high, 'low': low}
            else:
                if high > yearly_stats[year]['high']:
                    yearly_stats[year]['high'] = high
                if low < yearly_stats[year]['low']:
                    yearly_stats[year]['low'] = low

        # 4. Return Processed Data
        return JsonResponse({
            'symbol': symbol,
            'global_high': global_high,
            'global_low': global_low,
            'yearly_stats': yearly_stats,
            'duration': f"{from_date_str} to {to_date_str}"
        })

    return JsonResponse({'error': 'No symbol provided'}, status=400)

def load_price(request):
    symbol = request.GET.get('symbol')
    api_key = ''
    # 3. Call the "Quote Short" API

    url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey={api_key}"
    try:
        response = requests.get(url)
        # data = response.json() # Returns a list: [{'symbol': 'T.TO', 'price': 24.50, ...}, ...]
        
        # 4. Create a Dictionary for easy lookup: {'T.TO': 24.50, 'AAPL': 150.00}
        # latest_price = data['price']
        print(f"Load Price == {response.json()}")
        return JsonResponse(response.json(), safe=False)
            
    except Exception as e:
        print(f"Error fetching prices: {e}")
            
    # return render(request, 'stock_list.html', {'latest_price': latest_price})

def analysis_view(request):
    # 1. Fetch all data from the database
    # data = StockAnalysis.objects.all().order_by('-upside_percent')
    data = StockAnalysis.objects.all().order_by('ticker')
    last_updated = data.first().last_updated if data.exists() else None

    context = {
        'stocks': data,
        'last_updated': last_updated
    }
    
    # 2. Send it to the template
    return render(request, 'analysis_results.html', context)

def stock_dashboard(request):
    # 1. Fetch all stocks from the database
    # We order them by '-score' so the best stocks appear at the top
    # stocks = StockScore.objects.all().order_by('-score')
    stocks = StockScore.objects.all().order_by('symbol')
    
    # 2. Get the "Last Updated" timestamp
    # We check if stocks exist first to prevent a crash if the DB is empty
    if stocks.exists():
        # Since they are all updated at roughly the same time by the script,
        # taking the first one is sufficient.
        last_updated = stocks.first().updated_at
    else:
        last_updated = None

    # 3. Package the data for the HTML template
    context = {
        'stocks': stocks,
        'last_updated': last_updated
    }
    
    # 4. Send it to the browser
    return render(request, 'score_dashboard.html', context)

def combined_dashboard(request):
    # 1. Fetch BOTH datasets
    # We use select_related() if you had foreign keys, but here we just grab everything.
    analysis_qs = StockAnalysis.objects.all().order_by('ticker')
    score_qs = StockScore.objects.all()

    reliability_stats = BacktestResult.objects.values('ticker').annotate(
        wins=Sum('correct'),      # Sum of 1s (Trustworthy)
        total=Count('id')         # Total attempts
    )

    reliability_dict = {}
    for item in reliability_stats:
        wins = item['wins'] or 0 # Handle potential None
        total = item['total'] or 0
        reliability_dict[item['ticker']] = {
            'trustworthy': wins,
            'untrustworthy': total - wins
        }
    
    score_dict = {s.symbol: s for s in score_qs}


    order = request.GET.get('order')
    print("order: == ", order)

    order_upside = request.GET.get('order_upside')

    order_trust_ratio = request.GET.get('order_trust_ratio')
    order_compound_rate = request.GET.get('order_compound_rate')

    # Check if the user requested this specific sort
    # You might need to add a checkbox named 'order_low_diff' in your HTML form first
    order_low_diff = request.GET.get('order_low_diff')

    order_divident_rate = request.GET.get('divident_rate')
    order_ai_score_reliable = request.GET.get('ai_score_reliable')
    order_verdict = request.GET.get('order_verdict')
    order_rating = request.GET.get('order_rating')
    order_kelly_ratio = request.GET.get('order_kelly_ratio')

    # 2. OPTIMIZATION: Convert the "Join Table" (Scores) into a Dictionary
    # Key = Symbol, Value = The whole object
    # This makes looking up a score take 0.00001 seconds (Instant)
    score_dict = {s.symbol: s for s in score_qs}

    combined_data = []

    # 3. PERFORM THE JOIN
    for stock in analysis_qs:
        # Check if this ticker exists in the Score table
        if stock.ticker in score_dict:
            # INNER JOIN: We only proceed if it exists in BOTH
            score_obj = score_dict[stock.ticker]
            
            # 4. ATTACH DATA
            # We "inject" the score object into the analysis object as a new attribute.
            # You can name this attribute anything, like 'ai_data'
            stock.ai_data = score_obj

            stats = reliability_dict.get(stock.ticker, {'trustworthy': 0, 'untrustworthy': 0})
            stock.trustworthy_count = stats['trustworthy']
            stock.untrustworthy_count = stats['untrustworthy']
            
            combined_data.append(stock)

    # 4.5. SORT BY SCORE (Numeric)
    # reverse=True puts the highest numbers at the top
    if order_low_diff:
        # Sort by Price Difference (High -> Low)
        # We use (x.price_diff_percentage or -999) to handle missing values safely
        # order 10Y low price and current price diff percentage.
        combined_data.sort(key=lambda x: (x.price_diff_percentage or -999), reverse=False)

    if order_divident_rate:
        # Sort by Price Difference (High -> Low)
        # We use (x.dividend_yield or -999) to handle missing values safely
        combined_data.sort(key=lambda x: (x.dividend_yield or -999), reverse=True)

    # if order_trust_ratio:
    #     def get_trust_ratio(x):
    #         # Safe access to counts
    #         t = getattr(x.ai_data, 'trustworthy_count', 0)
    #         u = getattr(x.ai_data, 'untrustworthy_count', 0)
    #         total = t + u
            
    #         if total == 0: 
    #             return 0
    #         return (t / total) * 100

    #     # Sort High to Low
    #     combined_data.sort(key=get_trust_ratio, reverse=True)
        
    # if order:
        # combined_data.sort(key=lambda x: x.ai_data.score, reverse=True)

    # if order_ai_score_reliable:
    #     combined_data = sorted(
    #         combined_data, 
    #         key=lambda x: (x.ai_data.trust_label == "Verified", x.ai_data.score), 
    #         reverse=True
    #     )

    if order_kelly_ratio:
        combined_data = sorted(
            combined_data, 
            key=lambda x: (
                # Since reverse=True, 1s come before 0s.
                1 if (x.kelly_avg_error_margin is not None and float(x.kelly_avg_error_margin) <= 10) else 0,

                # 1. Primary: Accuracy (Higher is better)
                float(x.kelly_accuracy_score) if x.kelly_accuracy_score is not None else -float('inf'),

                # 2. Secondary: Error Margin (Lower is better, so we use negative)
                -float(x.kelly_avg_error_margin) if x.kelly_avg_error_margin is not None else -float('inf'),
                
                # 3. Tertiary: Upside % (Higher is better)
                float(x.kelly_ai_upside_percent) if x.kelly_ai_upside_percent is not None else -float('inf')
            ), 
            reverse=True
        )

    # if order_verdict:
    #     # Define the Ranking Logic (1 is best, 6 is worst)
    #     def get_verdict_rank(stock):
    #         # Convert to string and lowercase just to be safe
    #         v = str(stock.verdict or "").lower()
            
    #         if "undervalued" in v: return 1      # 💎 Top Priority
    #         if "high potential" in v: return 2   # 🚀 Second
    #         if "recovery" in v: return 2         # 🚀 Second (Alternative text)
    #         if "defensive" in v: return 3        # 🛡️ Third
    #         if "safe" in v: return 3             # 🛡️ Third (Alternative text)
    #         if "neutral" in v: return 4          # Middle
    #         if "overvalued" in v: return 5       # ⚠️ Worst
    #         return 6                             # Unknown/Bottom

    #     # Sort the list in-place based on the rank we just defined
    #     # Ascending order (1 -> 6) puts the best stocks at the top
    #     combined_data.sort(key=get_verdict_rank)

    # if order_rating:
    #     def get_rating_weight(stock):
    #         # Yahoo API keys mapped to numeric weights
    #         r = str(stock.analyst_rating or "").lower()
    #         weights = {
    #             'strong buy': 1,
    #             'buy': 2,
    #             'hold': 3,
    #             'underperform': 4,
    #             'sell': 5
    #         }
    #         return weights.get(r, 6)
    #     combined_data.sort(key=get_rating_weight)

    # if order_upside:
    #     # Correct: Access upside_percent directly on 'x' (StockAnalysis object)
    #     # We use (x.upside_percent or -999) to treat None/Empty values as the lowest
    #     # combined_data.sort(key=lambda x: (x.upside_percent or -999), reverse=True)

    #     #option 1: Weighted Score Calculation
    #     # def get_weighted_score(stock):
    #     #     # 1. Get raw values (default to 0.0)
    #     #     u_mean = float(stock.upside_percent or 0)
    #     #     u_low  = float(stock.upside_to_low or 0)
    #     #     u_high = float(stock.upside_to_high or 0)

    #     #     # --- 🛑 STRICT SAFETY CHECK ---
    #     #     # If the "Safe" (Low) target is negative, the stock is disqualified 
    #     #     # from the top spots immediately. We return a negative score based 
    #     #     # solely on its downside, ignoring the High/Mean entirely.
    #     #     if u_low < 0:
    #     #         # Return a massive negative number so it drops to the bottom.
    #     #         # Example: -17% becomes -1700 score.
    #     #         return u_low * 100

    #     #     # 2. Define Weights
    #     #     w_low  = 0.50  
    #     #     w_mean = 0.30  
    #     #     w_high = 0.20  

    #     #     # 3. Calculate Score
    #     #     score = (u_low * w_low) + (u_mean * w_mean) + (u_high * w_high)
    #     #     return score

    #     # combined_data.sort(key=get_weighted_score, reverse=True)

    #     #option 2: Sort by upside_to_low only.
    #     combined_data.sort(key=lambda x: (x.upside_to_low or -999), reverse=True)

    # Combined Sort: Trust Label (Verified first) -> Trust Ratio -> Score
    if order:
        def get_combined_reliability_score(x):
            # 1. Trust Label Priority (Verified=1, others=0)
            label_weight = 1 if getattr(x.ai_data, 'trust_label', '') == "Verified" else 0
            
            # 2. Trust Ratio calculation (Percentage of wins)
            t = getattr(x.ai_data, 'trustworthy_count', 0)
            u = getattr(x.ai_data, 'untrustworthy_count', 0)
            total = t + u
            ratio = (t / total * 100) if total > 0 else 0
            
            # 3. AI Score
            score = getattr(x.ai_data, 'score', 0)
            
            # Return as a tuple for multi-level sorting
            return (score, label_weight, ratio)

        combined_data.sort(key=get_combined_reliability_score, reverse=True)    

    # Combined Sort: Rating (Strong Buy first) -> Verdict (Undervalued first) -> Upside %
    if order_rating:
        def get_combined_investment_score(stock):
            # 1. Rating Weight (1 is Strong Buy, 6 is Sell/Unknown)
            # We subtract from 6 so that Strong Buy(5) is "higher" than Sell(1) for reverse=True
            r = str(stock.analyst_rating or "").lower()
            rating_weights = {'strong buy': 5, 'buy': 4, 'hold': 3, 'underperform': 2, 'sell': 1}
            r_score = rating_weights.get(r, 0)

            # 2. Verdict Rank (1 is Undervalued, 6 is Overvalued)
            # We invert this so Undervalued(6) is "higher" than Overvalued(1)
            v = str(stock.verdict or "").lower()
            if "undervalued" in v: v_score = 6
            elif "high potential" in v or "recovery" in v: v_score = 5
            elif "defensive" in v or "safe" in v: v_score = 4
            elif "neutral" in v: v_score = 3
            elif "overvalued" in v: v_score = 2
            else: v_score = 1

            # 3. Upside to Low (Highest percentage is best)
            u_score = float(stock.upside_to_low or -999)

            # Return as a tuple: (Priority 1, Priority 2, Priority 3)
            return (r_score, v_score, u_score)

        # We use reverse=True so that the highest scores (Strong Buy/Undervalued) are at the top
        combined_data.sort(key=get_combined_investment_score, reverse=True)
    
    if order_compound_rate:
        # 1. Create a sort key function
        def compound_sort_key(stock):
            upside = stock.profit_projection_upside
            
            # 2. Assign values based on consistency
            if upside is not None:
                # First group (Valid data): Sorted from Big to Small
                # We return (0, upside) so these come before the second group (1, ...)
                return (0, float(upside))
            else:
                # Second group (Inconsistent data): 
                # We return (1, 0) to put them last. 
                # Because Django/Python sorting is 'stable', their relative 
                # original position is kept within this group.
                return (1, 0)

        # 3. Perform the sort
        # Group 0 comes before Group 1. Inside Group 0, we reverse for Big -> Small.
        combined_data.sort(key=compound_sort_key, reverse=False)
        
        # Note: Because the first group (0) needs to be 'Big to Small' and the 
        # second group (1) just needs to be 'Last', we adjust the logic slightly:
        combined_data.sort(key=lambda x: (
            0 if x.profit_projection_upside is not None else 1, 
            -float(x.profit_projection_upside or 0)
        ))

    # 5. Handle "Last Updated"
    # We prefer the timestamp from the AI Score since that runs daily
    if combined_data:
        last_updated = combined_data[0].ai_data.updated_at
    else:
        last_updated = None

    context = {
        'stocks': combined_data,
        'last_updated': last_updated
    }
    
    return render(request, 'combined_dashboard.html', context)

def backtest_report(request):
    latest_log = AIModelLog.objects.last()
    
    if not latest_log:
        return render(request, 'backtest_report.html', {'no_data': True})

    # Get results
    results = latest_log.results.all().order_by('ticker', '-date')

    # --- THE FIX: Pre-format numbers here in Python ---
    # This bypasses the template filter error completely.
    
    # 1. Format the Summary Stats
    log_precision_str = f"{latest_log.precision * 100:.2f}" # e.g. "74.5"
    log_accuracy_str = f"{latest_log.accuracy * 100:.2f}"   # e.g. "65.1"
    log_recall_str = f"{latest_log.recall * 100:.2f}"       # e.g. "60.2"
    log_f1_str = f"{latest_log.f1_score * 100:.2f}"         # e.g. "62.5"
    log_auc_str = f"{latest_log.roc_auc * 100:.2f}"          # e.g. "0.75"

    # 2. Format the list of stocks
    # We loop through results and attach a temporary string attribute to each row
    for row in results:
        row.prob_display = f"{row.prob_score:.0f}" # e.g. "92" (No decimals)

    context = {
        'log': latest_log,
        'log_precision_str': log_precision_str, 
        'log_accuracy_str': log_accuracy_str,
        'log_recall_str': log_recall_str,
        'log_f1_str': log_f1_str,
        'log_auc_str': log_auc_str,
        'results': results,
        'no_data': False
    }
    return render(request, 'backtest_report.html', context)