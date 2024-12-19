import os
import csv
import warnings
from flask import Flask, render_template, request
import pdfplumber
import pandas as pd
import requests
from urllib.parse import urlparse
import re

warnings.filterwarnings("ignore", category=DeprecationWarning)

app = Flask(__name__)

# Constants
PDF_FILE = "All_deals_word.pdf"  # Your PDF file path
CSV_FILE = "deals_data.csv"  # Output CSV file to store deals
LOGO_DIR = os.path.join(app.root_path, 'static/logos')
if not os.path.exists(LOGO_DIR):
    os.makedirs(LOGO_DIR)


# Step 1: Extract data from PDF and save to CSV
def extract_pdf_to_csv(PDF_FILE, CSV_FILE):
    data = []

    with pdfplumber.open(PDF_FILE) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            pattern = r"Add this (.+?) deal which expires on (\d{2}/\d{2}/\d{2}).*?(\d+%)"
            matches = re.findall(pattern, text)

            for match in matches:
                company_name, expire_date, offer_percentage = match
                print(f"Parsed: {company_name}, {offer_percentage}, {expire_date}")  # Debug
                data.append({
                    "Company": company_name.strip(),
                    "Offer": offer_percentage.strip(),
                    "Expire Date": expire_date.strip(),
                })

    deals_df = pd.DataFrame(data)
    # Remove spaces and '%', then convert to integer
    deals_df["Offer"] = deals_df["Offer"].str.strip().str.replace("%", "").astype(int)
    deals_df.to_csv(CSV_FILE, index=False)


# Step 2: Fetch logo dynamically (using Clearbit for now)
def fetch_logo(company_name):
    try:
        company_name = re.sub(r"[ ']", "", company_name)
        # Remove content after dots (e.g., .com)
        company_name = re.split(r"\.", company_name)[0]
        search_url = f"https://logo.clearbit.com/{company_name}.com"
        response = requests.get(search_url)
        if response.status_code == 200:
            logo_name = f"{company_name}.png"
            logo_path = os.path.join(LOGO_DIR, logo_name)
            with open(logo_path, "wb") as f:
                f.write(response.content)
            return f"/static/logos/{logo_name}"
    except Exception as e:
        print(f"Failed to fetch logo for {company_name}: {e}")
    return "/static/logos/default_logo.png"


# Step 3: Load CSV data into a list of dictionaries
def load_csv_data(csv_path):
    try:
        data = pd.read_csv(csv_path)
        if data.empty:
            print("CSV is empty.")
            return []
    except pd.errors.EmptyDataError:
        print("Error: CSV file is empty. Please check PDF extraction.")
        return []

    deals = []
    for _, row in data.iterrows():
        logo_url = fetch_logo(row["Company"])
        cleaned_name = clean_company_name(row["Company"])
        deals.append({
            "Company": row["Company"],
            "Offer": row["Offer"],
            "Expire Date": row["Expire Date"],
            "Logo": logo_url,
            "CleanName": cleaned_name,
        })
    return deals

#import re

def clean_company_name(company_name):
    # Remove spaces, quotes, and unnecessary characters like '.com'
    company_name = re.sub(r"[ ']", "", company_name)  # Remove spaces and quotes
    company_name = re.split(r"\.", company_name)[0]  # Remove content after a dot (like .com)
    company_name = company_name.strip().lower()  # Convert to lowercase and remove any surrounding spaces
    return company_name.lower()

# Step 4: Flask Routes
@app.route("/", methods=["GET"])
def index():
    extract_pdf_to_csv(PDF_FILE, CSV_FILE)
   
    data = load_csv_data(CSV_FILE)
    search_company = request.args.get("company", "").strip()
    # Filter data by percentage offer if search input exists
    

    if search_company:
        data = [deal for deal in data if search_company.lower() in deal["Company"].lower()]

    return render_template("index.html", deals=data, search_company=search_company)

   # return render_template("index.html", deals=data, search_offer=search_offer)


# Step 5: Company Details Page
@app.route("/company/<company_name>")
def company_details(company_name):
    data = load_csv_data(CSV_FILE)
    company_deal = next((deal for deal in data if deal["Company"].lower() == company_name.lower()), None)

    if company_deal:
        #website_url = fetch_company_website(company_name)  # Fetch the company website dynamically
        return render_template("company_details.html", deal=company_deal)# website_url=website_url)
    else:
        return "Company not found", 404


if __name__ == "__main__":
    app.run(debug=True)
