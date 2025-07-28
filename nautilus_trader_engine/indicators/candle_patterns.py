import pandas as pd

def apply_candle_properties(df: pd.DataFrame):
    """
    This function calculates various properties of a candlestick in a given DataFrame.

    Parameters:
    df (pd.DataFrame): A DataFrame containing the Open, High, Low, and Close prices of a stock.

    Returns:
    df_an (pd.DataFrame): A DataFrame with additional columns for the calculated candlestick properties.
    """
    df_an = df.copy(deep=True)

    #Calculate the Direction of a Candle and if the Candle is a Green Candle (Close > Open) or a Red Candle (Open > Close)
    direction = df_an["Mid_Close"] - df_an["Mid_Open"]

    #Calculate the Size of the Candle
    body_size = abs(direction)

    #Convert the variable direction to 1 if it is a Green Candle and to -1 if it is a Red Candle
    direction = [1 if x >= 0 else -1 for x in direction]

    #Calculate the Full range of the Candle (High - Low)
    full_range = df_an["Mid_High"] - df_an["Mid_Low"]

    #Calculate the Percentage of the Body Size of the Candle with respect to the Full Range of the Candle
    body_perc = (body_size / full_range) * 100

    #Find the Upper Body and the Lower Body of the Candle
    body_upper = df_an[["Mid_Open", "Mid_Close"]].max(axis = 1)
    body_lower = df_an[["Mid_Open", "Mid_Close"]].min(axis = 1)

    #Find the Upper Body and Lower Body Percentage with respect to the Full Range of the Candle
    body_top_perc = 100 - (((df_an["Mid_High"] - body_upper) / full_range) * 100)
    body_bottom_perc = ((body_lower - df_an["Mid_Low"]) / full_range) * 100

    #Find the Mid Point of a Candle
    mid_point = (full_range / 2) + df_an["Mid_Low"]

    #Shift the values of Open, High, Low, Close to get the previous values
    df_an["Mid_Open_Prev"] = df_an["Mid_Open"].shift(1)
    df_an["Mid_High_Prev"] = df_an["Mid_High"].shift(1)
    df_an["Mid_Low_Prev"] = df_an["Mid_Low"].shift(1)
    df_an["Mid_Close_Prev"] = df_an["Mid_Close"].shift(1)

    #Calculate the percentage change in High and Low
    high_change = df_an["Mid_High"].pct_change() * 100
    df_an["Mid_High_Change"] = high_change
    low_change = df_an["Mid_Low"].pct_change() * 100
    df_an["Mid_Low_Change"] = low_change

    #Calculate the size of the upper and lower wick
    df_an["Upper_Wick_Size"] = df_an["Mid_High"] - df_an[["Mid_Open", "Mid_Close"]].max(axis = 1)
    df_an["Lower_Wick_Size"] = df_an[["Mid_Open", "Mid_Close"]].min(axis = 1) - df_an["Mid_Low"]

    #Add the calculated properties to the DataFrame
    df_an["Body_Upper"] = body_upper
    df_an["Body_Lower"] = body_lower
    df_an["Body_Top_Perc"] = body_top_perc
    df_an["Body_Perc"] = body_perc
    df_an["Body_Perc_Prev"] = df_an["Body_Perc"].shift(1)
    df_an["Body_Perc_Prev_2"] = df_an["Body_Perc"].shift(2)
    df_an["Body_Bottom_Perc"] = body_bottom_perc
    df_an["Direction"] = direction
    df_an["Direction_Prev"] = df_an["Direction"].shift(1)
    df_an["Direction_Prev_2"] = df_an["Direction"].shift(2)
    df_an["Body_Size"] = body_size
    df_an["Body_Size_Prev"] = df_an["Body_Size"].shift(1)

    #Calculate the percentage change in body size
    body_size_change = df_an["Body_Size"].pct_change() * 100
    df_an["Body_Size_Change"] = body_size_change

    #Add the mid point of the candle to the DataFrame
    df_an["Mid_Point"] = mid_point
    df_an["Mid_Point_Prev_2"] = df_an["Mid_Point"].shift(2)
    
    return df_an


#Create a Function to calculate Hanging Man / Hammer Candlestick Pattern
def apply_hanging_man(row):
    """
    This function checks if a given row represents a 'Hanging Man' pattern in candlestick charting.

    Parameters:
    row (dict): A dictionary representing a row of data. It should contain the keys "Body_Bottom_Perc" and "Body_Perc", 
                which represent the percentage of the total candlestick height that is below the body, and the percentage 
                of the total candlestick height that is the body, respectively.

    Returns:
    bool: True if the row represents a 'Hanging Man' pattern, False otherwise.

    """
    #Define the threshold for the body and height of the 'Hanging Man' pattern
    #The body should be less than 15% of the total height, and the part below the body should be more than 75% of the total height
    hanging_man_body = 15.0
    hanging_man_height = 75.0

    #Check if the row meets the criteria for a 'Hanging Man' pattern
    #The 'Hanging Man' pattern is identified when the percentage of the total candlestick height that is below the body is greater than the defined height threshold and the percentage of the total candlestick height that is the body is less than the defined body threshold.
    #First, check if the part below the body is greater than the defined height threshold
    if row["Body_Bottom_Perc"] > hanging_man_height:
        #If the first condition is met, check if the body is less than the defined body threshold
        if row["Body_Perc"] < hanging_man_body:
            #If both conditions are met, the row represents a 'Hanging Man' pattern
            return True
    
    #If either condition is not met, the row does not represent a 'Hanging Man' pattern
    return False


#Create a Function to calculate Shooting Star / Inverted Hammer Candlestick Pattern
def apply_shooting_star(row):
    """
    This function checks if a given row represents a shooting star pattern in candlestick charting.

    Parameters:
    row (dict): A dictionary representing a row of data. It should contain keys "Body_Top_Perc" and "Body_Perc" 
                representing the top percentage and body percentage of a candlestick respectively.

    Returns:
    bool: True if the row represents a shooting star pattern (i.e., body percentage is less than 15.0 and 
          top percentage is less than 25.0), False otherwise.
    """
    #Define the body and height percentage thresholds for a shooting star pattern
    shooting_star_body = 15.0
    shooting_star_height = 25.0

    #Check if the top percentage of the candlestick is less than the defined shooting star height
    if row["Body_Top_Perc"] < shooting_star_height:
        #If the above condition is met, check if the body percentage of the candlestick is less than the defined shooting star body
        if row["Body_Perc"] < shooting_star_body:
            #If both conditions are met, return True indicating a shooting star pattern
            return True
    
    #If either of the conditions is not met, return False
    return False


#Create a Function to calculate Spinning Top Candlestick Pattern
def apply_spinning_top(row):
    """
    This function checks if a given row satisfies the conditions to be classified as a spinning top.
    A spinning top is a candlestick pattern used in technical analysis to predict market trends.

    Parameters:
    row (dict): A dictionary representing a row of data. It should contain the keys "Body_Top_Perc", "Body_Bottom_Perc", and "Body_Perc".

    Returns:
    bool: True if the row satisfies the conditions to be a spinning top, False otherwise.
    """
    #Define the thresholds for the spinning top body, max, and min
    spinning_top_body = 15.0
    spinning_top_max = 60.0
    spinning_top_min = 40.0

    #Check if the row's body top percentage is less than the max
    if row["Body_Top_Perc"] < spinning_top_max:
        #If the above condition is met, check if the row's body bottom percentage is greater than the min
        if row["Body_Bottom_Perc"] > spinning_top_min:
            #If the above two conditions are met, check if the row's body percentage is less than the body threshold
            if row["Body_Perc"] < spinning_top_body:
                #If all conditions are met, return True
                return True
    
    #If any condition is not met, return False
    return False


#Create a Function to calculate Marubozu Candlestick Pattern
def apply_marubozu(row):
    """
    This function checks if the body percentage of a candlestick in a row is greater than a defined threshold.
    A Marubozu in candlestick charting represents a single candlestick with no shadow, indicating a strong trend in one direction.
    
    Parameters:
    row (dict): A dictionary representing a row of candlestick data. It should contain a key "Body_Perc" representing the body percentage of the candlestick.

    Returns:
    bool: True if the body percentage of the candlestick is greater than the defined threshold (98.0 in this case), False otherwise.
    """
    #Define the threshold for the body percentage of a Marubozu candlestick
    marubozu_body = 98.0

    #Check if the body percentage of the candlestick is greater than the defined threshold
    if row["Body_Perc"] > marubozu_body:
        #Return True if the body percentage is greater than the threshold
        return True
    
    #Return False if the body percentage is not greater than the threshold
    return False


#Create a Function to calculate Bullish & Bearish Engulfing Candlestick Patterns
def apply_engulfing(row):
    """
    This function checks if the current candlestick 'engulfs' the previous one in a candlestick chart.
    A candlestick is said to 'engulf' the previous one if it opens above/below the previous one's close and closes below/above the previous one's open.
    Additionally, the body size of the current candlestick should be 1.1 times the size of the previous one.
    The function returns True if the current candlestick engulfs the previous one, else it returns False.

    Parameters:
    row (Series): A row of a DataFrame that represents a candlestick in a candlestick chart. 
                  It should contain the following columns: 
                  'Direction', 'Direction_Prev', 'Body_Size', 'Body_Size_Prev', 'Mid_Open', 'Mid_Close_Prev', 'Mid_Close', 'Mid_Open_Prev', 'Mid_High', 'Mid_High_Prev', 'Mid_Low', 'Mid_Low_Prev'

    Returns:
    bool: True if the current candlestick engulfs the previous one, else False.
    """
    #Define the factor for engulfing
    engulfing_factor = 1.1

    #Check if the direction of the current candlestick is different from the previous one
    if row["Direction"] != row["Direction_Prev"]:
        #Check if the body size of the current candlestick is greater than 1.1 times the body size of the previous one
        if row["Body_Size"] > (row["Body_Size_Prev"] * engulfing_factor):
            #Check if the current candlestick opens above/below the previous one's close and closes below/above the previous one's open
            if (row["Mid_Open"] > row["Mid_Close_Prev"]) & (row["Mid_Close"] < row["Mid_Open_Prev"]) | (row["Mid_Close"] > row["Mid_Open_Prev"]) & (row["Mid_Open"] < row["Mid_Close_Prev"]):
                #Check if the current candlestick's high is greater than the previous one's high and its low is less than the previous one's low
                if (row["Mid_High"] > row["Mid_High_Prev"]) & (row["Mid_Low"] < row["Mid_Low_Prev"]):
                    #If all conditions are met, return True
                    return True
    
    #If any of the conditions are not met, return False
    return False


#Create a Function to calculate Tweezer Top Candlestick Pattern
def apply_tweezer_top(row):
    """
    Function to identify a Tweezer Top candlestick pattern in a given row of financial data.
    
    Parameters:
    row (Series): A row of financial data containing Open, High, Low, Close prices and other derived features.
    
    Returns:
    bool: True if the row represents a Tweezer Top pattern, False otherwise.
    """
    #Define constants for the Tweezer Top pattern
    tweezer_body = 0.15                     # Candlestick Body Size is 15% of the Candle 
    tweezer_high_low_perc_diff = 0.01       # Percentage Difference between the (Current High and Previous High) AND (Current Low and Previous Low)
    tweezer_open_close_perc_diff = 0.01     # Percentage Difference between the (Current Open and Previous Close) AND (Current Close and Previous Open)
    tweezer_top_body = 40.0                 # Top of the Tweezer Top Body
    epsilon = 1e-6                            # The epsilon is added to the denominator to ensure that the division is not done by Zero.

    #Check if the body size of the current and previous candlestick is less than 15%
    if (abs(row["Body_Size"] - row["Body_Size_Prev"]) / (row["Body_Size"] + epsilon)) < tweezer_body:
        #Check if the direction of the current candlestick is different from the previous one and if it is negative
        if (row["Direction"] != row["Direction_Prev"]) & (row["Direction"] == -1):
            #Check if the percentage difference between the mid-close of the previous candlestick and the mid-open of the current one, and the mid-open of the previous candlestick and the mid-close of the current one, is less than 1%
            if ((abs(row["Mid_Close_Prev"] - row["Mid_Open"]) / (row["Mid_Open"] + epsilon)) < tweezer_open_close_perc_diff) & ((abs(row["Mid_Open_Prev"] - row["Mid_Close"]) / (row["Mid_Close"] + epsilon)) < tweezer_open_close_perc_diff):
                #Check if the absolute change in the mid-high and mid-low is less than 1%
                if (abs(row["Mid_High_Change"]) < tweezer_high_low_perc_diff) & (abs(row["Mid_Low_Change"]) < tweezer_high_low_perc_diff):
                    #Check if the percentage of the body top is less than 40%
                    if row["Body_Top_Perc"] < tweezer_top_body:
                        #If all conditions are met, return True indicating a Tweezer Top pattern
                        return True
    
    #If any of the conditions are not met, return False
    return False


#Create a Function to calculate Tweezer Bottom Candlestick Pattern
def apply_tweezer_bottom(row):
    """
    Function to identify a Tweezer Bottom candlestick pattern in a given row of financial data.
    
    Parameters:
    row (Series): A row of financial data containing Open, High, Low, Close prices and other derived features.
    
    Returns:
    bool: True if the row represents a Tweezer Bottom pattern, False otherwise.
    """
    #Candlestick Body Size is 15% of the Candle 
    tweezer_body = 0.15
    #Percentage Difference between the (Current High and Previous High) AND (Current Low and Previous Low)
    tweezer_high_low_perc_diff = 0.01
    #Percentage Difference between the (Current Open and Previous Close) AND (Current Close and Previous Open)
    tweezer_open_close_perc_diff = 0.01
    #Bottom of the Tweezer Bottom Body
    tweezer_bottom_body = 60.0
    #The epsilon is added to the denominator to ensure that the division is not done by Zero.
    epsilon = 1e-6

    #Check if the body size of the current and previous candle is less than 15%
    if (abs(row["Body_Size"] - row["Body_Size_Prev"]) / (row["Body_Size"] + epsilon)) < tweezer_body:
        #Check if the direction of the current candle is different from the previous one and if it is a down candle
        if (row["Direction"] != row["Direction_Prev"]) & (row["Direction"] == -1):
            #Check if the percentage difference between the mid-points of open and close of current and previous candle is less than 1%
            if ((abs(row["Mid_Close_Prev"] - row["Mid_Open"]) / (row["Mid_Open"] + epsilon)) < tweezer_open_close_perc_diff) & ((abs(row["Mid_Open_Prev"] - row["Mid_Close"]) / (row["Mid_Close"] + epsilon)) < tweezer_open_close_perc_diff):
                #Check if the change in mid-points of high and low of current and previous candle is less than 1%
                if (abs(row["Mid_High_Change"]) < tweezer_high_low_perc_diff) & (abs(row["Mid_Low_Change"]) < tweezer_high_low_perc_diff):
                    #Check if the bottom of the body is more than 60%
                    if row["Body_Bottom_Perc"] > tweezer_bottom_body:
                        #If all conditions are met, return True indicating a Tweezer Bottom pattern
                        return True
    
    #If any of the conditions are not met, return False
    return False


#Create a Function to calculate Morning Star Candlestick Pattern
def apply_morning_star(row):
    """
    This function checks if a row of data matches the criteria for a Morning Star candlestick pattern.
    
    Parameters:
    row (dict): A dictionary where keys are column names and values are column values for a specific row in a DataFrame.
    
    Returns:
    bool: True if the row matches the Morning Star pattern, False otherwise.
    """
    #The Body Size Percentage of the Previous_2 Candle is 90% of the Current Candle
    morning_star_body_prev_2 = 90.0
    #The Body Size Percentage of the Previous Candle is 10% of the Current Candle
    morning_star_body_prev = 10.0

    #Check if the body percentage of the second previous candle is greater than 90%
    if row["Body_Perc_Prev_2"] > morning_star_body_prev_2:
        #Check if the body percentage of the previous candle is less than 10%
        if row["Body_Perc_Prev"] < morning_star_body_prev:
            #Check if the current candle is bullish and the second previous candle is bearish
            if (row["Direction"] == 1) & (row["Direction_Prev_2"] == -1):
                #Check if the mid-close of the current candle is greater than the mid-point of the second previous candle
                if row["Mid_Close"] > row["Mid_Point_Prev_2"]:
                    #If all conditions are met, return True indicating a Tweezer Top pattern
                        return True
    
    #If any of the conditions are not met, return False
    return False


#Create a Function to calculate Evening Star Candlestick Pattern
def apply_evening_star(row):
    """
    This function checks if the given row of data represents an evening star pattern in candlestick charting.
    
    Parameters:
    row (Series): A row of data containing information about a candlestick. 
                  It should include the following columns: 
                  "Body_Perc_Prev_2", "Body_Perc_Prev", "Direction", "Direction_Prev_2", "Mid_Close", "Mid_Point_Prev_2".
    
    Returns:
    bool: True if the row represents an evening star pattern, False otherwise.
    """
    #The Body Size Percentage of the Previous_2 Candle is 90% of the Current Candle
    evening_star_body_prev_2 = 90.0
    #The Body Size Percentage of the Previous Candle is 10% of the Current Candle
    evening_star_body_prev = 10.0

    #Check if the body percentage of the second previous candle is greater than 90%
    if row["Body_Perc_Prev_2"] > evening_star_body_prev_2:\
        #Check if the body percentage of the previous candle is less than 10%
        if row["Body_Perc_Prev"] < evening_star_body_prev:
            #Check if the current candle is bearish and the second previous candle is bullish
            if (row["Direction"] == -1) & (row["Direction_Prev_2"] == 1):
                #Check if the mid-close of the current candle is less than the mid-point of the second previous candle
                if row["Mid_Close"] < row["Mid_Point_Prev_2"]:
                    #If all conditions are met, return True indicating a Tweezer Top pattern
                    return True
    
    #If any of the conditions are not met, return False
    return False


def set_candle_patterns(df_an: pd.DataFrame):
    """
    This function applies various candlestick pattern detection functions to a given DataFrame.
    
    Parameters:
    df_an (pd.DataFrame): The DataFrame to which the candlestick pattern detection functions will be applied.
    
    Returns:
    None: The function modifies the DataFrame in-place, adding new columns for each detected candlestick pattern.
    """
    
    #Apply the Hanging Man pattern detection function to the DataFrame
    df_an["Hanging_Man"] = df_an.apply(apply_hanging_man, axis=1)

    #Apply the Shooting Star pattern detection function to the DataFrame
    df_an["Shooting_Star"] = df_an.apply(apply_shooting_star, axis=1)

     #Apply the Spinning Top pattern detection function to the DataFrame
    df_an["Spinning_Top"] = df_an.apply(apply_spinning_top, axis=1)

    #Apply the Marubozu pattern detection function to the DataFrame
    df_an["Marubozu"] = df_an.apply(apply_marubozu, axis=1)

    #Apply the Engulfing pattern detection function to the DataFrame
    df_an["Engulfing"] = df_an.apply(apply_engulfing, axis=1)

    #Apply the Tweezer Top pattern detection function to the DataFrame
    df_an["Tweezer_Top"] = df_an.apply(apply_tweezer_top, axis=1)

    #Apply the Tweezer Bottom pattern detection function to the DataFrame
    df_an["Tweezer_Bottom"] = df_an.apply(apply_tweezer_bottom, axis=1)

    #Apply the Morning Star pattern detection function to the DataFrame
    df_an["Morning_Star"] = df_an.apply(apply_morning_star, axis=1)

    #Apply the Evening Star pattern detection function to the DataFrame
    df_an["Evening_Star"] = df_an.apply(apply_evening_star, axis=1)


def apply_candle_patterns(df: pd.DataFrame):
    """
    This function applies candle patterns to a given DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame to which the candle patterns will be applied.

    Returns:
    df_an (pd.DataFrame): The DataFrame after the application of the candle patterns.
    """
    #Apply candle properties to the DataFrame
    df_an = apply_candle_properties(df)

    #Set candle patterns in the DataFrame
    set_candle_patterns(df_an)

    #Return the DataFrame after applying the candle patterns
    return df_an



#Alternate code to Create a Function to calculate Hanging Man Candlestick Pattern
def is_uptrend(df, index, lookback=3):
    """
    Check if there is an uptrend in the 'Mid_Close' values of a dataframe before a given index.

    Parameters:
    df (pandas.DataFrame): The dataframe containing the 'Mid_Close' column.
    index (int): The index in the dataframe to check for an uptrend before.
    lookback (int, optional): The number of previous rows to check for an uptrend. Defaults to 3.

    Returns:
    bool: True if there is an uptrend in the 'Mid_Close' values before the given index, False otherwise.
    """
    #If the index is less than the lookback period, return False
    if index < lookback:
        return False
    
    #Loop through the lookback period
    for i in range(1, lookback + 1):
        #If the 'Mid_Close' value at a previous index is less than or equal to the 'Mid_Close' value at the index before it, return False
        if df['Mid_Close'][index - i] <= df['Mid_Close'][index - i - 1]:
            return False
    
    #If none of the 'Mid_Close' values in the lookback period are less than or equal to the 'Mid_Close' values before them, return True
    return True


def is_hanging_man(df, index):
    """
    Determine if the candlestick at index is a Hanging Man.

    Parameters:
    df (DataFrame): DataFrame of prices, including "Open", "High", "Low", "Close", and "Volume".
    index (int): The index of the candlestick to check.

    Returns:
    bool: True if the last candlestick is a Hanging Man, False otherwise.

    """
    #Extract the open, high, low, close prices and volume at the given index
    open_price = df['Mid_Open'][index]
    high_price = df['Mid_High'][index]
    low_price = df['Mid_Low'][index]
    close_price = df['Mid_Close'][index]
    volume = df['Volume'][index]
    
    #Calculate the size of the body and the upper and lower wicks of the candlestick
    body_size = abs(open_price - close_price)
    upper_wick_size = high_price - max(open_price, close_price)
    lower_wick_size = min(open_price, close_price) - low_price
    
    # Criteria for a Hanging Man:
    # 1. The lower wick is at least twice the size of the body
    # 2. There is little or no upper wick
    # 3. The candle appears after an uptrend (last close is higher than the previous close)
    # 4. The volume of the current candle is higher than the previous one
    is_hanging_man = (lower_wick_size >= 2 * body_size and
                      upper_wick_size < body_size and
                      close_price > df['Mid_Close'][index - 1] and
                      volume > df['Volume'][index - 1])

    #Return True if the last candlestick is a Hanging Man, False otherwise
    return is_hanging_man


def find_hanging_man_patterns(df):
    """
    This function is used to find and return indices of Hanging Man patterns in a given dataframe.
    
    Parameters:
    df (DataFrame): The input dataframe which contains the stock price data.
    
    Returns:
    hanging_man_indices (list): A list of indices where Hanging Man patterns are found.
    """
    #Initialize an empty list to store the indices of Hanging Man patterns
    hanging_man_indices = []

    #Loop through the dataframe from the second row to the end
    for i in range(1, len(df)):
        #Check if the current pattern is an uptrend and a Hanging Man pattern
        if is_uptrend(df, i) and is_hanging_man(df, i):
            #If true, append the index to the list
            hanging_man_indices.append(i)
    
    #Return the list of indices
    return hanging_man_indices