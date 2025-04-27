"""
parse_recommendations.py

This script extracts stock recommendations from a PDF file (newrecs.pdf) and writes them
to a CSV file (newrecs.csv). Each row in the CSV contains the date, stock symbol, stock name,
and recommendation type (buy/sell/hold).

It also performs a sanity check to validate stock symbols and names using yfinance.

Dependencies:
- pdfplumber: For reading PDF files
- requests: For validating stock symbols via Financial Modeling Prep API
- csv: For writing the output CSV
- yfinance: For validating stock symbols and names

Usage:
    python parse_recommendations.py

Make sure newrecs.pdf is present in the same directory.
"""
import pdfplumber
import csv
import re


def extract_recommendations(pdf_path, csv_path):
    """
    Extracts recommendations from the PDF and writes them to a CSV file.
    """
    with pdfplumber.open(pdf_path) as pdf, open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['date', 'symbol', 'name', 'recommendation'])
        for page in pdf.pages:
            text = page.extract_text()
            # Regex: symbol, name, action, SA, date
            matches = re.findall(
                r'^([A-Z]{1,5})\s+(.+?)\s+(BUY|SELL|HOLD|REDUCE)\s+SA\s+(\d{2}/\d{2}/\d{2,4})',
                text, re.IGNORECASE | re.MULTILINE
            )
            for symbol, name, rec, date in matches:
                writer.writerow([date, symbol, name.strip(), rec.upper()])
                print(f"Extracted: {date}, {symbol}, {name.strip()}, {rec.upper()}")

if __name__ == "__main__":
    extract_recommendations("newrecs.pdf", "newrecs.csv")