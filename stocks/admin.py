from django.contrib import admin
from django.utils.html import format_html
from .models import Stock
from .models import UsStock
from .models import CustomStock
from .models import StockAnalysis
from .models import StockScore
from .models import AIModelLog, BacktestResult

# Register your models here.
# This line adds the Stock model to the Admin dashboard
admin.site.register(Stock)
admin.site.register(UsStock)
admin.site.register(CustomStock)

class StrictGrowthFilter(admin.SimpleListFilter):
    title = 'Strict Growth Status'
    parameter_name = 'strict_growth'

    def lookups(self, request, model_admin):
        return (
            ('confirmed', 'Strict Growth Confirmed'),
            ('inconsistent', 'Inconsistent Profit'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'confirmed':
            return queryset.filter(analysis_note_compound__icontains="confirmed")
        if self.value() == 'inconsistent':
            return queryset.filter(analysis_note_compound__icontains="inconsistent")
        return queryset

@admin.register(StockAnalysis)
class StockAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        'ticker', 
        'current_price', 
        'expected_target_price', # This will show as "Kelley Expected Price"
        'kelly_accuracy_score',        # Reliability metric
        'backtest_sample_count', # How many years were tested
        'verdict', 
        'upside_percent', 
        'last_updated', 
        'compound_profit_rate_display',  # Method defined below
        'projected_price_by_profit',     
        'profit_upside_display',         # Method defined below
    )
    
    # Allows you to click these fields to sort high-to-low
    sortable_by = ('ticker', 'expected_target_price', 'kelly_accuracy_score', 'last_updated', 'compound_profit_rate')
    
    # Adds a sidebar filter for easier decision making
    list_filter = ('verdict', 'top_ai_driver', StrictGrowthFilter)
    
    search_fields = ('ticker', 'verdict')
    
    # Organizes the edit page into sections
    fieldsets = (
        ("Basic Info", {
            'fields': ('ticker', 'current_price', 'verdict')
        }),
        ("Compound Growth Analysis", {
            'fields': (
                'compound_profit_rate', 
                'projected_price_by_profit', 
                'period_low_compound', 
                'period_years_compound', 
                'analysis_note_compound'
            ),
            'description': "Strict consistency check metrics."
        }),
        ("AI Analysis (Kelley)", {
            'fields': (
                'expected_target_price', 
                ('p1', 'p2', 'p3'), 
                ('price1', 'price2', 'price3'),
                'top_ai_driver'
            ),
            'description': "Scenario modeling based on weighted probabilities P1 (Worst), P2 (Base), P3 (Best)."
        }),
        ("Model Reliability", {
            'fields': ('kelly_accuracy_score', 'backtest_sample_count', 'kelly_avg_error_margin')
        }),
    )

    def compound_profit_rate_display(self, obj):
        """Formats the decimal CAGR as a percentage (0.125 -> 12.50%)"""
        if obj.compound_profit_rate is not None:
            return f"{obj.compound_profit_rate:.2%}"
        return "-"
    compound_profit_rate_display.short_description = "Profit CAGR"
    compound_profit_rate_display.admin_order_field = 'compound_profit_rate'

    def profit_upside_display(self, obj):
        """Displays the @property from models.py as a simple string"""
        upside = obj.profit_projection_upside
        if upside is not None:
            # Simply return the formatted string without HTML tags
            return f"{upside:.1f}%"
        return "-"
    profit_upside_display.short_description = "Proj. Upside"

@admin.register(StockScore)
class StockScoreAdmin(admin.ModelAdmin):
    # This controls what columns you see in the list
    list_display = ('symbol', 'score','buy_score', 'sell_score', 'recommendation', 'pe_ratio', 'updated_at')
    
    # This adds a search bar at the top to find specific stocks
    search_fields = ('symbol', 'recommendation')
    
    # This adds a filter sidebar (e.g., to show only "Strong Buy" stocks)
    list_filter = ('recommendation', 'updated_at')

class BacktestResultInline(admin.TabularInline):
    model = BacktestResult
    readonly_fields = ('ticker', 'date', 'prob_score', 'prediction', 'actual_target', 'correct')
    extra = 0
    can_delete = False

@admin.register(AIModelLog)
class AIModelLogAdmin(admin.ModelAdmin):
    # Added recall, f1, and roc_auc to the list
    list_display = (
        'timestamp', 
        'precision_display', 
        'recall_display', 
        'f1_display', 
        'auc_display', 
        'accuracy_display', 
        'data_points'
    )
    
    # Make sure the new fields are readonly so the AI controls them, not users
    readonly_fields = ('timestamp', 'accuracy', 'precision', 'recall', 'f1_score', 'roc_auc', 'oob_accuracy', 'data_points')
    inlines = [BacktestResultInline]

    # Helper methods to format decimals as percentages (0.85 -> 85.0%)
    def precision_display(self, obj):
        return f"{obj.precision:.1%}"
    precision_display.short_description = "Precision"

    def recall_display(self, obj):
        return f"{obj.recall:.1%}"
    recall_display.short_description = "Recall"

    def f1_display(self, obj):
        return f"{obj.f1_score:.1%}"
    f1_display.short_description = "F1-Score"

    def auc_display(self, obj):
        return f"{obj.roc_auc:.2f}" # AUC is usually shown as a decimal 0.0-1.0
    auc_display.short_description = "ROC-AUC"

    def accuracy_display(self, obj):
        return f"{obj.accuracy:.1%}"
    accuracy_display.short_description = "Accuracy"

@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'date', 'prob_score', 'prediction', 'actual_target', 'correct')
    list_filter = ('correct', 'prediction')
    search_fields = ('ticker',)
    # This enables the sorting you're looking for
    ordering = ('ticker', '-date')