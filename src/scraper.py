import time
import logging
import random 
import pandas as pd
import numpy as np

from config import XPATHS

from utils.form_helpers import get_text
from utils.table_extraction import scrape_table_by_xpath, transform_table, find_click_row
from utils.navigation import safe_click, next_navigation

def extract_property_details(driver, wait):
    """
    Extracts detailed property information, including appraisal, tax, and transfer data.

    Parameters:
    - wait (WebDriverWait): Selenium WebDriverWait instance for handling explicit waits.

    Returns:
    - pd.DataFrame: DataFrame containing property details, or None if an error occurs.
    """
    try:
        # Retrieve and process the parcel ID
        parcel_text = get_text(driver, wait, XPATHS["property"]["parcel_id"])
        parcel_parts = parcel_text.split("\n")
        if len(parcel_parts) < 2 or not parcel_parts[1].strip():
            logging.warning(f"Unexpected format for parcel_id: {parcel_text}")
            return None
        parcel_id = parcel_parts[1].strip()

        # Scrape and transform the appraisal table
        appraisal_table = scrape_table_by_xpath(wait, XPATHS["view"]["appraisal_information"])

        if appraisal_table is None or appraisal_table.empty:
            logging.warning(f"Appraisal table is empty for parcel {parcel_id}.")
            return None
        appraisal_table = transform_table(appraisal_table)
        # Drop unwanted columns
        columns_to_drop = ["Year Built", "Deed Number", "# of Parcels Sold"]
        appraisal_table = appraisal_table.drop(
            [col for col in columns_to_drop if col in appraisal_table.columns], axis=1
        )

        # Rename columns
        appraisal_table.rename(
            columns={
                "# Bedrooms": "Bedrooms",
                "# Full Bathrooms": "Full Baths",
                "# Half Bathrooms": "Half Baths"
            }, inplace=True
        )

        # Add additional property details
        appraisal_table["parcel_id"] = parcel_id
        appraisal_table["school_district"] = get_text(driver, wait, XPATHS["property"]["school_district"])
        appraisal_table["owner_address"] = get_text(driver, wait, XPATHS["property"]["owner"])

        return appraisal_table

    except Exception as e:
        logging.error(f"Error extracting details for parcel {parcel_id if 'parcel_id' in locals() else 'unknown'}: {e}")
        return None

    
def scrape_results_page(wait):
    """Scrapes the results page for the main table."""
    try:
        table = scrape_table_by_xpath(wait, XPATHS["results"]["results_table"])
        return table
    except Exception as e:
        logging.error(f"Error scraping results page: {e}")
        return pd.DataFrame()

def scrape_data(driver, wait, NUM_ENTRIES):
    """
    Handles data scraping, including navigating pages and extracting details.
    """
    all_data, appraisal_data = [], []
    PAGE_NUMBER = pd.to_numeric(get_text(driver, wait, XPATHS["results"]["number_pages"]))

    for i in range(PAGE_NUMBER):
        logging.info(f"Scraping results on page {i+1}...")
        results_data = scrape_results_page(wait)
        
        if results_data is not None and not results_data.empty:
            all_data.append(results_data)

        else:
            logging.warning(f"No data found on page {i+1}. Ending scrape.")
            break

        if not next_navigation(driver, wait, XPATHS["results"]["next_page_button"]):
            break

    # Navigate to the first property details page
    if all_data:
        safe_click(wait, XPATHS["results"]["first_results_table_page"])
        find_click_row(driver, wait, XPATHS["results"]["first_row_results_table"])
    else:
        logging.warning("No all_data to navigate for property details.")

    # Scrape property details
    for i in range(NUM_ENTRIES):
        logging.info(f"Scraping property details for property({i+1} of {NUM_ENTRIES})...")
        appraisal_table = extract_property_details(driver, wait)
        if appraisal_table is not None:
            appraisal_data.append(appraisal_table)
        else:
            logging.info("Failed to extract property details.")

        time.sleep(random.uniform(5, 8))

        if not next_navigation(driver, wait, XPATHS["property"]["next_property"]):
            break

    return all_data, appraisal_data
