from django.shortcuts import render
import requests # This is like PHP's CURL



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

    # print(f"search_results: {search_results}")

    # 5. Render the page with the results (if any)
    return render(request, 'stock_symbol.html', {
        'search_results': search_results,
        'query': query,
        'exchange': exchange
    })