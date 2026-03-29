# stocks/ai_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

class StockPredictorStatic:
    def __init__(self):
        self.model = None
        self._train_model()

    def _train_model(self):
        """Internal method to bootstrap the AI with synthetic data"""
        train_size = 2000
        np.random.seed(42)
        
        # Generate synthetic data
        fake_pe = np.random.uniform(5, 60, train_size)
        fake_roe = np.random.uniform(-0.1, 0.5, train_size)
        fake_debt = np.random.uniform(0, 300, train_size)
        fake_margins = np.random.uniform(-0.1, 0.4, train_size)
        fake_growth = np.random.uniform(-0.2, 0.5, train_size)

        X_train = pd.DataFrame({
            'pe_ratio': fake_pe,
            'roe': fake_roe,
            'debt_to_equity': fake_debt,
            'profit_margins': fake_margins,
            'revenue_growth': fake_growth
        })

        y_train = np.where(
            (fake_pe < 25) & (fake_roe > 0.12) & 
            (fake_debt < 150) & (fake_growth > 0.05), 
            1, 0
        )

        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

    def predict(self, df):
        """Takes a DataFrame of real stock data and returns scores (0-100)"""
        if not self.model:
            self._train_model()
            
        X_real = df[['pe_ratio', 'roe', 'debt_to_equity', 'profit_margins', 'revenue_growth']]
        scores = self.model.predict_proba(X_real)[:, 1] * 100
        return scores.astype(int)