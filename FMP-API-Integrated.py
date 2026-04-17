import pandas as pd
import requests
import os


# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
api_key = "Your API KEY HERE"
symbols = ['AAPL', 'SOFI', 'NKE', 'CELH', 'LLY'] # Can choose to input as many stocks as you want
insider_csv_file = r"insider_data_sample.csv" 
ownership_csv_file = r"ownership_data_sample.csv"
# ==========================================
# 2. DEFINING THE ENGINE FUNCTIONS
# ==========================================

def get_insider_data(ticker, key):
    url = f"https://financialmodelingprep.com/stable/insider-trading?symbol={ticker}&apikey={key}"
    response = requests.get(url)
    
    #Check if the HTTP request was successful
    if response.status_code == 200:
        json_data = response.json()
        #Convert the raw text from the website into python dictionary/lists
        
        if not json_data or isinstance(json_data, dict):  # Check for whether the return data is empty as well as check whether there is an error code that occured.
            return pd.DataFrame()
        
        #put the python dict/lists into a panda data frame    
        df = pd.DataFrame(json_data)
        
        # Filter for 'P-Purchase' (Market Buys only with own cash )
        if 'transactionType' in df.columns:
            df = df[df['transactionType'] == 'P-Purchase'].copy()
            
            df['transactionValue'] = df['securitiesTransacted'] * df['price']
            
            df = df[df['transactionValue'] > 50000]
            return df
    return pd.DataFrame()

def process_insider_titles(df):
    # Ranks insiders based on their seniority/influence.
    if df.empty: 
        return df
    
    df['typeOfOwner'] = df['typeOfOwner'].str.lower()

    def rank_title(title):
        if 'ceo' in title or 'chief executive' in title:
            return 1
        elif 'cfo' in title or 'chief financial' in title:
            return 2
        elif 'director' in title:
            return 3
        else:
            return 4

    df['priorityRank'] = df['typeOfOwner'].apply(rank_title)
    df['cleanTitle'] = df['typeOfOwner'].str.title()
    return df

def get_cluster_signals(df, days_window=30, min_insiders=3):
    #Groups trades to find 'Cluster' buying events.
    if df.empty:
        return pd.DataFrame()
    
    df['fillingDate'] = pd.to_datetime(df['fillingDate'])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days_window)
    recent_buys = df[df['fillingDate'] >= cutoff]
    
    if recent_buys.empty: 
        return pd.DataFrame()
    
    cluster_stats = recent_buys.groupby('symbol').agg({
        'reportingName': 'nunique',
        'transactionValue': 'sum',
        'price': 'mean'
    }).reset_index()

    cluster_stats.columns = ['Ticker', 'Num_of_UniqueInsiders', 'TotalClusterValue', 'AvgPrice']
    high_signal = cluster_stats[cluster_stats['Num_of_UniqueInsiders'] >= min_insiders]
    return high_signal.sort_values(by='Num_of_UniqueInsiders', ascending=False)

def get_ownership_structure(ticker, key):
    #Fetches Institutional vs. Retail vs. Insider breakdown.
    url = f"https://financialmodelingprep.com/api/v4/is-the-market-cap-real?symbol={ticker}&apikey={key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Select key columns and convert decimals to percentages
        cols = ['symbol', 'institutionalWeight', 'retailWeight', 'insiderWeight']
        clean_df = df[cols].copy()
        for col in cols[1:]:
            clean_df[col] *= 100
        return clean_df
    return pd.DataFrame()

# ==========================================
# 3. MAIN EXECUTION LOOP (The Data Pipeline)
# ==========================================

all_insider_list = []
all_ownership_list = []

print("--- Starting Pipeline ---")

for ticker in symbols:
    print(f"Fetching data for: {ticker}...")
    
    # Run Insider Data
    trades = get_insider_data(ticker, api_key)
    if not trades.empty:
        all_insider_list.append(trades)
        
    # Run Ownership Data
    owners = get_ownership_structure(ticker, api_key)
    if not owners.empty: 
        all_ownership_list.append(owners)

#This code is only when we do not have access to the paid subscription, but allows us to test the code in power bi
if not all_insider_list:
    print("API returned no data. Looking for CSV fallback...")
    if os.path.exists(insider_csv_file):
        csv_df = pd.read_csv(insider_csv_file)
        # Ensure the data types match the API format
        csv_df['fillingDate'] = pd.to_datetime(csv_df['fillingDate'])
        csv_df['transactionValue'] = csv_df['securitiesTransacted'] * csv_df['price']
        all_insider_list.append(csv_df)
        print("Successfully loaded sample data from CSV.")

if not all_ownership_list:
    print("API returned no ownership data. Looking for CSV fallback...")
    if os.path.exists(ownership_csv_file):
        own_df = pd.read_csv(ownership_csv_file)
        all_ownership_list.append(own_df)
        print("Successfully loaded ownership sample data.")

# ==========================================
# 4. FINAL TABLE GENERATION FOR POWER BI
# ==========================================

# TABLE 1: Master Insider Trades
if all_insider_list:
    #Combine all the small dataframe that the for loop created and combine them to become a singular dataframe 
    raw_insider_data = pd.concat(all_insider_list, ignore_index=True)
    final_insider_trades = process_insider_titles(raw_insider_data)
else:
    final_insider_trades = pd.DataFrame(columns=['symbol', 'transactionValue', 'priorityRank'])

# TABLE 2: Cluster Signals
final_cluster_signals = get_cluster_signals(final_insider_trades)

# TABLE 3: Master Ownership Data
if all_ownership_list:
    final_ownership_data = pd.concat(all_ownership_list, ignore_index=True)
else:
    final_ownership_data = pd.DataFrame(columns=['symbol', 'institutionalWeight', 'retailWeight'])

print("--- Pipeline Complete! ---")

    



