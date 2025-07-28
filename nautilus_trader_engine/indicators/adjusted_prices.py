# Function to calculate the adjusted Open, High, Low, and Close (OHLC) prices (for Stock Splits and Dividends) for a given stock data DataFrame

def calculate_adjusted_ohlc(df, adjustment="split"):
    """
    This function calculates the adjusted Open, High, Low, and Close (OHLC) prices for a given stock data DataFrame.
    
    The adjustment takes into account the cumulative effect of stock splits and dividends over time. The adjusted prices provide a more accurate reflection of the stock"s value over time, which is useful for historical comparisons.
    
    Parameters:
    df (DataFrame): A pandas DataFrame containing the stock data. The DataFrame should have the following columns: 
    "Open", "High", "Low", "Close", "Stock Splits", "Dividends".

    adjustment (str): The type of adjustment to perform. Can be one of the following: "split", "dividend", "both" (default is "split").

    Note:
    If the stock data is fetched from a source which has already adjusted the data for stock splits and dividends, then this finction should not be used on that data. This function should only be used on data which has not been adjusted for stock splits and dividends. 
    
    Returns:
    df (DataFrame): The input DataFrame, but with four additional columns: "Adj Open", "Adj High", "Adj Low", "Adj Close", which represent the adjusted OHLC prices.
    """
    # Calculate the cumulative product of the stock splits factor. This is done by dividing 1 by the sum of 1 and the "Stock Splits" column, and then taking the cumulative product of the resulting series.
    split_factor = (1.0 / (1.0 + df["Stock Splits"])).cumprod()

    # Calculate the cumulative sum of the dividends. This is done by taking the cumulative sum of the "Dividends" column.
    cumulative_dividends = df["Dividends"].cumsum()

    if adjustment == "split":
        # Calculate the adjusted OHLC prices using only stock splits.
        df["Adj Open"] = df["Open"] * split_factor
        df["Adj High"] = df["High"] * split_factor
        df["Adj Low"] = df["Low"] * split_factor
        df["Adj Close"] = df["Close"] * split_factor
    elif adjustment == "dividend":
        # Calculate the adjusted OHLC prices using only dividends.
        df["Adj Open"] = df["Open"] + cumulative_dividends
        df["Adj High"] = df["High"] + cumulative_dividends
        df["Adj Low"] = df["Low"] + cumulative_dividends
        df["Adj Close"] = df["Close"] + cumulative_dividends
    elif adjustment == "both":
        # Calculate the adjusted OHLC prices using both stock splits and dividends.
        df["Adj Open"] = (df["Open"] + cumulative_dividends) * split_factor
        df["Adj High"] = (df["High"] + cumulative_dividends) * split_factor
        df["Adj Low"] = (df["Low"] + cumulative_dividends) * split_factor
        df["Adj Close"] = (df["Close"] + cumulative_dividends) * split_factor
    else:
        raise ValueError('Invalid adjustment type. Must be one of "split", "dividend", or "both"')

    return df
