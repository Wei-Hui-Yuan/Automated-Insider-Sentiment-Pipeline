# Automated Insider Sentiment Pipeline
**An Automated Data Engineering & Equity Analysis Suite**

## 📌 Project Overview
This project automates the collection and visualization of SEC Form 4 filings to identify **"Cluster Signals"**—instances where multiple company insiders (CEOs, CFOs, Directors) purchase their own company's stock with personal cash. 

The goal is to provide a high-conviction alternative to traditional technical analysis by following "smart money." By identifying consensus among leadership, this tool filters market noise to highlight high-probability sentiment signals.

## ⚖️ Model Comparison: API vs. SEC Scraper
This repository provides two distinct methodologies for data acquisition. While both aim to identify the same "Cluster Signals," they differ in technical execution and use cases.

| Feature | **API-Integrated Model** (FMP) | **Direct SEC Scraper** (EDGAR) |
| **Complexity** | **Low** - Clean JSON response from a single endpoint. | **High** - Multi-step process (CIK mapping → JSON index → XML parsing). |
| **Data Source** | Third-party financial data aggregator. | Direct primary source (US Government Servers). |
| **Reliability** | Depends on third-party uptime and database updates. | Most accurate/raw data; "Source of Truth" for all filings. |
| **Speed** | **Fast** - Highly optimized for large batches of stocks. | **Throttled** - Complies with SEC rate limits (10 requests/sec). |
| **Parsing Logic** | Pre-processed by the API provider. | Manual extraction of specific XML nodes (e.g., `rptOwnerName`, `transactionCode`). |
| **Best For...** | Rapid dashboarding and high-frequency updates. | Deep-dive forensic auditing and data engineering demonstration. |


## 🚀 Key Features
- **Hybrid Data Sourcing:** Choose between a streamlined API version or a robust direct-to-source XML scraper.
- **Automated CIK Mapping:** Dynamically converts ticker symbols to the 10-digit Central Index Keys (CIK) required by SEC servers.
- **Insider Seniority Ranking:** Implements a custom prioritization logic to weight trades by executive role (e.g., CEO > Director).
- **Cluster Detection Algorithm:** Specialized logic that flags "Cluster Buys" (3+ unique insiders buying within a 90-day window).
- **Resilient Architecture:** Integrated fallback logic that automatically switches to local CSV repositories if API limits are reached or no live signals are found.

## 🛠️ Tech Stack
- **Language:** Python 3.x
- **Libraries:** Pandas (Data manipulation), Requests (Networking), ElementTree (XML Parsing)
- **Visualization:** Power BI
- **Data Source:** US SEC EDGAR / Financial Modeling Prep API

## 📊 Dashboard Visuals
<img width="1223" height="709" alt="image" src="https://github.com/user-attachments/assets/fba34725-f534-4b3b-a6f7-2152d3b62570" />

The pipeline generates structured data optimized for the following Power BI visuals:
1. **The Conviction Bar Chart:** Highlights tickers with 3+ unique insider buyers using conditional formatting.
2. **Seniority Donut Chart:** Breakdown of purchases by executive title to assess signal quality.
3. **Insider Weighting Matrix:** Comparison of insider ownership levels vs. institutional and retail holdings.

## ⚙️ Setup Instructions
1. **Clone the repository.**
2. **Install dependencies:** `pip install pandas requests`.
3. **Configure Identity:** - In the **SEC Version**, update the `HEADERS` dictionary with your email to comply with SEC fair-access policies.
   - In the **API Version**, add your Financial Modeling Prep API key.
4. **Set File Paths:** Ensure the file paths for `insider_data_sample.csv` and `ownership_data_sample.csv` are correctly mapped in the script.
5. **Run in Power BI:** Copy the script into the Power BI "Get Data > Python Script" connector.



