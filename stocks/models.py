from django.db import models

# Create your models here.
class Stock(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=10)
    exchange = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol

class UsStock(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=10)
    exchange = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol
    
class CustomStock(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=10)
    exchange = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol

class StockAnalysis(models.Model):
    ticker = models.CharField(max_length=20, unique=True)
    
    # Valuation Data
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    analyst_target = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Consensus 12-Month Price Target")
    analyst_target_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    analyst_target_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    upside_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    analyst_rating = models.CharField(max_length=20, blank=True, null=True)  # e.g., "Buy"
    price_action = models.CharField(max_length=20, blank=True, null=True)    # e.g., "Raises"
    current_target = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    previous_target = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Fundamental Ratios
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    forward_pe = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Risk Metrics
    beta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Analysis Result
    verdict = models.CharField(max_length=50, default="Neutral")
    last_updated = models.DateTimeField(auto_now=True)

    # We use "period_" instead of "ten_year_" so it is flexible
    period_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    period_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stores the number of years used for the calculation (e.g., 5, 10, 20)
    period_years = models.IntegerField(null=True, blank=True, help_text="Number of years used for high/low calc")
    
    # Timestamp to know when this specific data was last fetched
    history_updated_at = models.DateTimeField(null=True, blank=True)

    # Add these new fields for the AI Module
    p1 = models.FloatField(null=True, blank=True, help_text="Worst Case Prob")
    p2 = models.FloatField(null=True, blank=True, help_text="Base Case Prob")
    p3 = models.FloatField(null=True, blank=True, help_text="Best Case Prob")
    
    price1 = models.FloatField(null=True, blank=True, help_text="Worst Case Impact %")
    price2 = models.FloatField(null=True, blank=True, help_text="Base Case Impact %")
    price3 = models.FloatField(null=True, blank=True, help_text="Best Case Impact %")

    # The Final Output
    expected_target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,  help_text="Kelley Expect Price (P1, P2, P3 weighted calculation", verbose_name="Kelley Expected Price")
    top_ai_driver = models.CharField(max_length=50, blank=True, null=True)

    kelly_accuracy_score = models.FloatField(null=True, blank=True, help_text="AI Model R-Squared Score (0-100%)")
    kelly_avg_error_margin = models.FloatField(null=True, blank=True, help_text="Average percentage error in past predictions")
    backtest_sample_count = models.IntegerField(null=True, blank=True, help_text="Number of historical years used for training")

    # Compound Growth Analysis Fields
    compound_profit_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    projected_price_by_profit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    period_low_compound = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    period_years_compound = models.IntegerField(null=True, blank=True)
    analysis_note_compound = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.ticker} ({self.verdict})"   

    @property
    def price_diff_percentage(self):
        """Calculates (Current - Low) / Current"""
        # 1. Safety check: ensure both prices exist and current_price is not 0
        if not self.current_price or not self.period_low or self.current_price == 0:
            return None
        
        # 2. Perform the math
        # We multiply by 100 to get a percentage (e.g., 0.15 becomes 15.0)
        diff = self.current_price - self.period_low # how much is current price increased, based on the history low price.
        return (diff / self.period_low) * 100

    @property
    def upside_to_low(self):
        """Returns the % upside/downside to the LOW analyst target."""
        if self.current_price and self.analyst_target_low and self.current_price > 0:
            return ((self.analyst_target_low - self.current_price) / self.current_price) * 100
        return None

    @property
    def upside_to_high(self):
        """Returns the % upside/downside to the HIGH analyst target."""
        if self.current_price and self.analyst_target_high and self.current_price > 0:
            return ((self.analyst_target_high - self.current_price) / self.current_price) * 100
        return None

    @property
    def kelly_ai_upside_percent(self):
        """
        Calculates the percentage difference between the AI Expected Target Price 
        and the Current Price.
        Formula: ((Expected - Current) / Current) * 100
        """
        if not self.expected_target_price or not self.current_price or self.current_price == 0:
            return None
        
        # Calculate the raw difference
        diff = self.expected_target_price - self.current_price
        
        # Calculate percentage relative to current price
        return (diff / self.current_price) * 100
    
    @property
    def profit_projection_upside(self):
        if not self.projected_price_by_profit or not self.current_price or self.current_price == 0:
            return None
        return ((self.projected_price_by_profit - self.current_price) / self.current_price) * 100
    
class StockScore(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    
    # UPDATED LINE BELOW
    score = models.IntegerField(
        verbose_name="12-Mo Target Score", 
        help_text="AI prediction of performance over the next 12 months (0-100)"
    )
    buy_score = models.IntegerField(default=0)  # Save the raw buy prob
    sell_score = models.IntegerField(default=0)       # Save the raw sell prob
    trustworthy_count = models.IntegerField(default=0)
    untrustworthy_count = models.IntegerField(default=0)
    
    # Text recommendation (e.g., "Strong Buy")
    recommendation = models.CharField(max_length=50)

    # We save the raw data too, so you can display it on the website later
    pe_ratio = models.FloatField(null=True, blank=True)
    roe = models.FloatField(null=True, blank=True)
    debt_to_equity = models.FloatField(null=True, blank=True)
    revenue_growth = models.FloatField(null=True, blank=True)

    # Timestamp to know when the AI last ran
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock Forecast"
        verbose_name_plural = "Stock Forecasts Score(12 Mo)" # <--- Changes the Main Table Name in Admin

    def __str__(self):
        return f"{self.symbol}: {self.score}"

    @property
    def total_predictions(self):
        return self.trustworthy_count + self.untrustworthy_count

    @property
    def trust_percentage(self):
        """Returns accuracy as a whole number (0-100), or None if no data."""
        total = self.total_predictions
        if total == 0:
            return 0
        return int((self.trustworthy_count / total) * 100)

    @property
    def trust_label(self):
        """Returns a label for the UI."""
        total = self.total_predictions
        if total < 3: # Not enough data yet
            return "Learning"
        
        pct = self.trust_percentage
        if pct >= 75:
            return "Verified"
        elif pct >= 50:
            return "Mixed"
        else:
            return "Unreliable"

# 1. The Summary Log (One row per training session)
class AIModelLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField(help_text="Test Set Accuracy")
    precision = models.FloatField(help_text="Test Set Precision (Win Rate)")
    recall = models.FloatField(default=0.0, help_text="Test Set Recall")
    f1_score = models.FloatField(default=0.0, help_text="Test Set F1-Score")
    roc_auc = models.FloatField(default=0.0, help_text="Test Set ROC-AUC Score")
    oob_accuracy = models.FloatField(null=True, blank=True, help_text="Out-of-Bag Score")
    data_points = models.IntegerField(help_text="Total rows of data used")

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} | Prec: {self.precision:.1%} | Rec: {self.recall:.1%} | F1: {self.f1_score:.1%} | AUC: {self.roc_auc:.1%}"

# 2. The Detailed Backtest (Many rows per session - one for each stock tested)
class BacktestResult(models.Model):
    log = models.ForeignKey(AIModelLog, on_delete=models.CASCADE, related_name='results')
    ticker = models.CharField(max_length=20)
    date = models.DateField(null=True)
    prob_score = models.FloatField(help_text="AI Confidence score (0-100)")
    prediction = models.IntegerField(help_text="1=Buy, 0=Wait")
    actual_target = models.IntegerField(help_text="1=Up, 0=Down")
    correct = models.IntegerField(help_text="1=Correct, 0=Wrong")

    def __str__(self):
        return f"{self.ticker}: {self.correct}"