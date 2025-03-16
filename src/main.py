import subprocess
import sys

def install_packages(requirements_file):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])

# Check and install requirements
install_packages("requirements.txt")

import time
import pandas as pd
from datetime import datetime
import logging

from config import BASE_URL
from driver_setup import init_driver

from utils.navigation import initialize_search, check_allowed_webscraping
from utils.form_helpers import check_reset_needed, final_csv_conversion, safe_quit

from scraper import scrape_data

def main(allowed, start, end, dates, ids, values):
    driver, wait = init_driver(BASE_URL)
    # Ensuring that webscraping on the website is allowed.
    if not allowed:
        allowed = check_allowed_webscraping(driver)

    try:
        initialize_search(wait, start, end, ids, values)
        time.sleep(2)
        reset_needed, modified, dates, NUM_ENTRIES = check_reset_needed(driver, wait, start, end, dates)
        if reset_needed:
            logging.info("Reset needed, closing WebDriver.")
            return pd.DataFrame(), pd.DataFrame(), dates, driver, modified
        # Scrape data
        all_data, appraisal_data = scrape_data(driver, wait, NUM_ENTRIES)    
        assert all_data, "No all_data returned!"
        assert appraisal_data, "No appraisal_data returned!"            
        # Consolidate data

        if not all_data:
            logging.error("No data scraped from the website.")
            return pd.DataFrame(), pd.DataFrame(), dates, driver, modified
        all_data_df = pd.concat(all_data).reset_index(drop=True)
        all_data_df.columns = ['Parcel Number', 'Address', 'BBB', 'FinSqFt', 'Use', 'Year Built','Transfer Date', 'Amount']
        appraisal_data_df = pd.concat(appraisal_data).reset_index(drop=True)
        logging.info(f'Completed the main scraping of property data for {start_date} and {end_date}. Beginning address cleaning and converting to a csv file.')
        return all_data_df, appraisal_data_df, dates, driver, modified
    
    finally:
        safe_quit(driver)


# Search parameters
sale_price_low = int(input("What is the lowest price? "))
sale_price_high = int(input("What is the highest price? "))
finished_sq_ft_low = int(input("What is the lowest square feet? "))
finished_sq_ft_high = int(input("What is the highest square feet? "))
bedrooms_low = int(input("What is the lowest number of bedrooms? "))

query_ids = ["sale_price_low","sale_price_high","finished_sq_ft_low","finished_sq_ft_high","bedrooms_low"]
query_values = [sale_price_low, sale_price_high, finished_sq_ft_low, finished_sq_ft_high, bedrooms_low]

# Define years to process
start_year = input("What year do you want to start the search? ")
end_year = input("What year do you want to end the search? ")
years = range(int(start_year), int(end_year)+1)

# Set up the root logger
logging.basicConfig(
    filename="scraper.log",
    filemode="a",  # Append mode
    level=logging.INFO,  # Minimum log level for messages to be recorded
    format="%(asctime)s - %(levelname)s - %(message)s"
)
allowed = False

# Main loop to process each year
for YEAR in years:
    start = datetime.strptime(f"01/01/{YEAR}", "%m/%d/%Y")
    end = datetime.strptime(f"12/31/{YEAR}", "%m/%d/%Y")
    
    start_date = f"{start:%m/%d/%Y}"
    end_date = f"{end:%m/%d/%Y}"
    dates = [(start_date, end_date)]

    if __name__ == "__main__":
        logging.info(f"Starting scraping process for year {YEAR}")

        while dates:
            logging.info(f"Starting scraping process for start date, {start_date}, and end date, {end_date}")
            for start_date, end_date in dates[:]:

                # Initialize empty DataFrames for each set of dates
                all_data_df = pd.DataFrame()
                appraisal_data_df = pd.DataFrame()

                # Call main function with the full date range for the year
                all_data, appraisal_data, dates, driver, modified = main(
                    allowed=allowed,
                    start=start_date,
                    end=end_date,
                    ids=query_ids,
                    values=query_values,
                    dates=dates
                )
                if modified:
                    break

                # Concatenate data
                all_data_df = pd.concat([all_data_df, all_data], axis=0, ignore_index=True)
                appraisal_data_df = pd.concat([appraisal_data_df, appraisal_data], axis=0, ignore_index=True)

                # Final data processing and saving
                final_csv_conversion(all_data_df, appraisal_data_df, dates, start_date, end_date, YEAR)