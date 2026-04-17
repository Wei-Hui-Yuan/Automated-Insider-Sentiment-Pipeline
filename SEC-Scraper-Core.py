import pandas as pd
import requests
import os
import xml.etree.ElementTree as ET

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
# IMPORTANT: The SEC requires you to declare your identity or they will block you.
HEADERS = {'User-Agent': 'Your name (your.real.email@example.com)'}

api_key = "Your API KEY HERE" #Please input your Financial Modeling Prep API key here, only works for premium members
symbols = ['AAPL', 'SOFI', 'NKE', 'CELH', 'LLY','PLTR'] 

insider_csv_file = r"insider_data_sample.csv" #Please include the full file path when importing the code to power BI
ownership_csv_file = r"ownership_data_sample.csv" #Please include the full file path when importing the code to power BI

# ==========================================
# 2. DEFINING THE ENGINE FUNCTIONS
# ==========================================

#Find the ticker with the CIK number 
def get_cik_mapping():
    #Fetches the SEC master list to convert Tickers to CIK numbers.
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=HEADERS)
    mapping = {}
    if response.status_code == 200:
        for key, data in response.json().items():
            # CIKs must be exactly 10 digits long (padded with zeros)
            mapping[data['ticker']] = str(data['cik_str']).zfill(10)
    return mapping

def get_insider_data(ticker, cik):
    #Fetches and parses raw Form 4 XMLs directly from the SEC EDGAR database.
    if not cik: # safety check, just in case no cik number
        return pd.DataFrame()
        
    # 1. Get the list of all recent filings for the company
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    sub_res = requests.get(submissions_url, headers=HEADERS)
    print(f"SEC Status Code for {ticker}: {sub_res.status_code}")
    if sub_res.status_code != 200:
        return pd.DataFrame()
        
    recent_filings = sub_res.json()['filings']['recent']
    df_filings = pd.DataFrame(recent_filings)
    
    # Filter for Form 4 (Insider Trading)
    form4s = df_filings[df_filings['form'] == '4'].head(10) # Look at the 10 most recent can edit to however many we want
    
    trades = []
    
    # 2. Loop through each Form 4 and download the raw XML document
    for index, row in form4s.iterrows():
        accession_no = row['accessionNumber']
        accession_no_clean = accession_no.replace("-", "")
        xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_clean}/{accession_no}.xml"
        
        xml_res = requests.get(xml_url, headers=HEADERS)
        if xml_res.status_code == 200:
            try:
                root = ET.fromstring(xml_res.text)
                
                # Parse reporting owner data
                owner = root.find('.//reportingOwnerId/rptOwnerName')
                title = root.find('.//reportingOwnerRelationship/officerTitle')
                is_director = root.find('.//reportingOwnerRelationship/isDirector')
                
                owner_name = owner.text if owner is not None else "Unknown"
                
                # Determine title
                if title is not None and title.text:
                    owner_title = title.text
                elif is_director is not None and is_director.text in ['true', '1']:
                    owner_title = "Director"
                else:
                    owner_title = "Officer"

                # Parse transaction data
                for trans in root.findall('.//nonDerivativeTransaction'):
                    code = trans.find('.//transactionCoding/transactionCode')
                    if code is not None and code.text == 'P': 
                        shares = trans.find('.//transactionAmounts/transactionShares/value')
                        price = trans.find('.//transactionAmounts/transactionPricePerShare/value')
                        date = trans.find('.//transactionDate/value')
                        
                        if shares is not None and price is not None:
                            trades.append({
                                'symbol': ticker,
                                'reportingName': owner_name,
                                'typeOfOwner': owner_title,
                                'transactionType': 'P-Purchase',
                                'securitiesTransacted': float(shares.text),
                                'price': float(price.text),
                                'fillingDate': date.text if date is not None else row['filingDate']
                            })
            except Exception as e:
                continue # Skip unparseable XMLs
                
    # 3. Format the final table
    df = pd.DataFrame(trades)
    if not df.empty:
        df['transactionValue'] = df['securitiesTransacted'] * df['price']
        # Filter for significant trades over $50k
        df = df[df['transactionValue'] > 50000]
        
    return df

def process_insider_titles(df):
    if df.empty: 
        return df
    df['typeOfOwner'] = df['typeOfOwner'].astype(str).str.lower()
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
    #Only avaliable to test if have a FMP premium subscription, can see instituion and retail ownership
    url = f"https://financialmodelingprep.com/api/v4/is-the-market-cap-real?symbol={ticker}&apikey={key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        df = pd.DataFrame(data)
        cols = ['symbol', 'institutionalWeight', 'retailWeight', 'insiderWeight']
        clean_df = df[cols].copy()
        for col in cols[1:]:
            clean_df[col] *= 100
        return clean_df
    return pd.DataFrame()

# ==========================================
# 3. MAIN EXECUTION LOOP
# ==========================================

all_insider_list = []
all_ownership_list = []

print("--- Starting Pipeline ---")

# Pre-fetch the CIK dictionary to save time
print("Fetching SEC CIK Dictionary...")

cik_map = get_cik_mapping()


for ticker in symbols:
    print(f"Fetching data for: {ticker}...")
    
    # Run SEC Insider Data
    cik = cik_map.get(ticker)
    trades = get_insider_data(ticker, cik)
    if not trades.empty:
        all_insider_list.append(trades)
        
    # Run Ownership Data
    owners = get_ownership_structure(ticker, api_key)
    if not owners.empty: 
        all_ownership_list.append(owners)

# CSV Fallbacks
if not all_insider_list:
    print("SEC API returned no recent large purchases. Looking for CSV fallback...")
    if os.path.exists(insider_csv_file):
        csv_df = pd.read_csv(insider_csv_file)
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
# 4. FINAL TABLE GENERATION
# ==========================================

if all_insider_list:
    raw_insider_data = pd.concat(all_insider_list, ignore_index=True)
    final_insider_trades = process_insider_titles(raw_insider_data)
else:
    final_insider_trades = pd.DataFrame(columns=['symbol', 'transactionValue', 'priorityRank'])

final_cluster_signals = get_cluster_signals(final_insider_trades)

if all_ownership_list:
    final_ownership_data = pd.concat(all_ownership_list, ignore_index=True)
else:
    final_ownership_data = pd.DataFrame(columns=['symbol', 'institutionalWeight', 'retailWeight'])

print("--- Pipeline Complete! ---")