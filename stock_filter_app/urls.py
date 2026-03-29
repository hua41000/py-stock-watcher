"""
URL configuration for stock_filter_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
# from . import views
from stocks import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # path('', views.home, name='home'),
    path('', views.stock_dashboard, name='home'),
    path('stock-symbol/', views.stock_symbol, name='stock_symbol'),

    # The Hidden AJAX URL
    path('add-stock-ajax/', views.add_stock_ajax, name='add_stock_ajax'),
    path('add-us-stock-ajax/', views.add_us_stock_ajax, name='add_us_stock_ajax'),
    path('add-custom-stock-ajax/', views.add_custom_stock_ajax, name='add_custom_stock_ajax'),

    path('stock-list/', views.stock_list, name='stock_list'),
    path('stock-us-list/', views.stock_us_list, name='stock_us_list'),
    path('stock-custom-list/', views.stock_custom_list, name='stock_custom_list'),
    path('analysis/', views.analysis_view, name='analysis_results'),
    path('combined_dashboard/', views.combined_dashboard, name='combined_dashboard'),
    path('backtest/', views.backtest_report, name='backtest_report'),

    path('get-stock-details/', views.get_stock_details, name='get_stock_details'),

    path('historical-analysis/', views.get_historical_analysis, name='historical_analysis'),
    path('current-price/', views.load_price, name='getCurPrice'),
]
