import yfinance as yf
import pandas as pd

def load_data(stocks, start, end):
    data = yf.download(stocks, start=start, end=end)

    if isinstance(data.columns, pd.MultiIndex):
        data = data['Close']
    else:
        data = data[['Close']]

    return data
