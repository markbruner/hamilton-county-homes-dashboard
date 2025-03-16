import re
import os
import time
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import logging

from config import XPATHS, school_city_map, street_type_map

from utils.address_cleaners import owner_address_cleaner, tag_address

# Selenium-related imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException

def fill_form_field(wait, field_id, value, retries=3, delay=1, clear_field=True):
    """
    Fills in a form field given its ID and value to enter.

    Parameters:
    - wait (WebDriverWait): Selenium WebDriverWait instance for handling explicit waits.
    - field_id (str): The ID of the form field to locate.
    - value (str): The value to enter into the form field.
    - retries (int): Number of retries if the field is not immediately available. Default is 3.
    - delay (int): Delay in seconds between retries. Default is 1.
    - clear_field (bool): Whether to clear the existing value before entering a new one. Default is True.

    Returns:
    - bool: True if the field was successfully filled, False otherwise.
    """
    # Validate parameters
    if not isinstance(field_id, str) or not field_id.strip():
        logging.error("Invalid field ID provided.")
        raise ValueError("field_id must be a non-empty string.")
    if value is None:
        logging.error("Value to enter in the form field cannot be None.")
        raise ValueError("value must not be None.")

    for attempt in range(1, retries + 1):
        try:
            # Locate the form field by its ID
            field = wait.until(EC.presence_of_element_located((By.ID, field_id)))

            # Optionally clear the existing value
            if clear_field:
                field.clear()

            # Enter the provided value
            field.send_keys(value)
            logging.info(f"Successfully filled form field {field_id} with value '{value}'.")
            return True
        except TimeoutException as e:
            logging.warning(f"Attempt {attempt}/{retries} to locate form field {field_id} timed out: {e}")
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Unexpected error while interacting with form field {field_id}: {e}")
            raise

    # Log failure after exhausting retries
    logging.error(f"Failed to fill form field {field_id} after {retries} attempts.")
    return False


def get_text(driver, wait, xpath, retries=3, delay=1):
    """
    Retrieves the text from an element located by its XPATH with retry logic.

    Parameters:
    - wait (WebDriverWait): Selenium WebDriverWait instance for waiting on elements.
    - xpath (str): The XPATH of the element to retrieve text from.
    - retries (int): Number of retries if the element is not found or is inaccessible. Default is 3.
    - delay (int): Delay in seconds between retries. Default is 1.

    Returns:
    - str: The text of the element if found, or raises an exception if all retries fail.
    """
    for attempt in range(1, retries + 1):
        try:
            # Wait for the element to be located
            element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            text = element.text.strip()
            if not text:
                logging.warning(f"Element located at {xpath} exists but contains no text.")
            return text
        
        except ElementClickInterceptedException as e:
            logging.warning(
                f"Attempt {attempt}/{retries} to get text at {xpath} intercepted by another element: {e}"
            )
            time.sleep(delay)

        except TimeoutException as e:
            logging.error(
                f"Attempt {attempt}/{retries} timed out while waiting for element at {xpath}: {e}"
            )
            time.sleep(delay)
            
        except StaleElementReferenceException as e:
            logging.warning(
                f"Stale element encountered at {xpath}. Retrying... (Attempt {attempt}/{retries})"
            )
            time.sleep(delay)

        except Exception as e:
            logging.error(f"Unexpected error while attempting to get text at {xpath}: {e}")
            raise

    # Raise a timeout error if all retries fail
    raise TimeoutException(f"Failed to retrieve text from element at {xpath} after {retries} attempts.")

# Function to format column names
def format_column_name(name, to_lower=True, strip_underscores=False, prefix=None):
    """
    Formats a column name by replacing spaces with underscores, removing special characters,
    and optionally converting to lowercase, stripping leading/trailing underscores, or adding a prefix.

    Parameters:
    - name (str): The column name to format.
    - to_lower (bool): Whether to convert the name to lowercase. Default is True.
    - strip_underscores (bool): Whether to strip leading/trailing underscores. Default is False.
    - prefix (str): Optional prefix to add to the column name. Default is None.

    Returns:
    - str: The formatted column name.
    """
    if not isinstance(name, str) or not name:
        logging.error(f"Invalid column name: {name}")
        raise ValueError("Column name must be a non-empty string")
    
    # Replace spaces and remove special characters
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_]+", "", name)
    
    # Apply transformations
    if to_lower:
        name = name.lower()
    if strip_underscores:
        name = name.strip("_")
    if prefix:
        name = f"{prefix}_{name}"
    
    return name

def safe_to_datetime(date, description="date"):
    try:
        return pd.to_datetime(date)
    except Exception as e:
        logging.error(f"Invalid {description}: {date}. Error: {e}")
        raise

def str_format_date(date):
    """
    Converts a datetime object into a string in the format MM/DD/YYYY.

    Parameters:
    - date (datetime): The datetime object to format.

    Returns:
    - str: The formatted date string.
    
    Raises:
    - ValueError: If the input is not a valid datetime object.
    """
    if not isinstance(date, datetime):
        raise ValueError(f"Input must be a datetime object, but got {type(date).__name__}.")
    
    return f"{date:%m/%d/%Y}"

def split_replace_add_time_slice(dates, old_date, new_date, additional_slice):
    """
    Replaces a specific end date in a date range and adds a new time slice after it.

    Parameters:
    - dates (list of tuples): List of date ranges as (start, end) tuples.
    - old_date (str): The end date to replace.
    - new_date (str): The new end date to replace `old_date` with.
    - additional_slice (tuple): A new time slice to add after the modified date range.

    Returns:
    - list of tuples: The modified list of date ranges.
    """
    # Validate inputs
    if not isinstance(dates, list) or not all(isinstance(d, tuple) and len(d) == 2 for d in dates):
        logging.error("Dates must be a list of tuples with start and end dates. The dates in the list are: f{dates}")
        raise ValueError("Invalid dates format")
    if not isinstance(additional_slice, tuple) or len(additional_slice) != 2:
        logging.error("Additional slice must be a tuple with two elements (start, end).")
        raise ValueError("Invalid additional slice format")
    
    old_date = safe_to_datetime(old_date,"old date")
    new_date = safe_to_datetime(new_date, "new date")

    updated_dates = dates.copy()
    modified = False

    # Iterate through the date ranges to find and replace old_date
    for i, (start, end) in enumerate(updated_dates):
        start = safe_to_datetime(start, "start date")
        end = safe_to_datetime(end, "end date")

        if end == old_date:
            # Replace the end date with the new date
            start = str_format_date(start)
            new_date = str_format_date(new_date)
            updated_dates[i] = (start, new_date)
            # Insert the additional time slice
            updated_dates.insert(i + 1, additional_slice)
            modified = True
            logging.info(f"Replaced {old_date} with {new_date} and added new slice {additional_slice}.")
            break

    if not modified:
        logging.warning(f"Old date {old_date} not found in any date range. No modifications made.")

    return updated_dates, modified

def safe_quit(driver):
    try:
        driver.quit()
        logging.info("Driver quit successfully.")
    except Exception as e:
        logging.error(f"Failed to quit the driver gracefully: {e}")

def check_reset_needed(driver, wait, start, end, dates):
    """
    Checks if the search needs to be reset due to 1000 entries and updates the time slice.

    Parameters:
    - driver: Selenium WebDriver instance.
    - wait: WebDriverWait instance for handling explicit waits.
    - start (str): Start date of the current search range.
    - end (str): End date of the current search range.
    - dates (list): List of date ranges to modify if resetting is needed.

    Returns:
    - reset_needed (bool): Whether the search was reset.
    - updated_dates (list): Updated list of date ranges.
    - total_entries (int): Number of entries in the current search.
    """
    start_dt = safe_to_datetime(start, "start date")
    end_dt = safe_to_datetime(end, "end date")

    try:
        # Getting the number of search results based on the critieria provided by user
        raw_text = get_text(driver, wait, XPATHS["results"]["search_results_number"])
        total_entries = pd.to_numeric(raw_text.split(" ")[5].replace(",", ""))
    except Exception as e:
        raise ValueError(f"Failed to extract number of entries: {e}")   

    if total_entries >= 1000:
        logging.info(f"Entries = {total_entries} for {start} to {end}. Splitting dates further since the entries are greater than or equal to the threshold of 1000.")

        # Calculating the midpoint of the start and end date
        midpoint = start_dt + (end_dt - start_dt) / 2
        midpoint_str = f"{midpoint:%m/%d/%Y}"

        # Creating the new time slice
        new_slice = (
            f"{midpoint + timedelta(days=1):%m/%d/%Y}"
            ,f"{end_dt:%m/%d/%Y}"
            )
        
        # Updating the list of dates        
        updated_dates, modified = split_replace_add_time_slice(
            dates, f"{end_dt:%m/%d/%Y}", midpoint_str, new_slice
            )
        return True, modified, updated_dates, total_entries
    
    if total_entries < 1:
        logging.warning(f"Search parameters between {start_dt} and {end_dt} yielded no results. Moving to next date range.")
        safe_quit(driver)
        return False, False, dates, total_entries

    return False, False, dates, total_entries

def clean_and_format_columns(df, drop_cols):
    """
    Replaces the current df's columns with ones that have been formatted or better readability.
    """
    formatted_columns = [format_column_name(col) for col in df.columns]
    df.columns = formatted_columns
    return df.drop([col for col in drop_cols if col in df.columns], axis=1)

def get_file_path(base_dir, filename):
    """
    Constructs a file path given the base directory and filename.
    """
    return os.path.join(base_dir, "data", "raw", filename)

def save_to_csv(df, file_path, overwrite=False, index=False):
    """
    Saves a Pandas DataFrame to a CSV file with robust error handling.
    
    Parameters:
    - df (pd.DataFrame): The DataFrame to save.
    - file_path (str): The file path where the CSV will be saved.
    - overwrite (bool): Whether to overwrite the file if it exists. Default is False.
    - index (bool): Whether to include the DataFrame index in the CSV. Default is False.
    
    Returns:
    - bool: True if the file is saved successfully, False otherwise.
    """
    if not isinstance(df, pd.DataFrame):
        logging.error("Provided object is not a Pandas DataFrame.")
        raise ValueError("The input data must be a Pandas DataFrame.")
    
    if not isinstance(file_path, str):
        logging.error("File path is not a string.")
        raise ValueError("The file path must be a string.")
    
    # Determine file write modes
    mode, header = ("w", True) if overwrite else ("a", False) if os.path.exists(file_path) else ("w", True)
    
    try:
        df.to_csv(file_path, mode=mode, header=header, index=index)
        logging.info(f"Saved {df.shape[0]} rows and {df.shape[1]} columns to {file_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving CSV to {file_path}: {e}")
        raise

def final_csv_conversion(all_data_df, appraisal_data_df, dates, start_date, end_date, year):
    """
    Processes and saves home data to CSV files with additional cleaning and address concatenation.
    """
    if appraisal_data_df.empty:
        logging.warning("Appraisal data is empty. Exiting function.")
        return None

    # Validate dates
    if not isinstance(dates, list) or not all(isinstance(d, tuple) and len(d) == 2 for d in dates):
        logging.error("Dates must be a list of tuples with start and end dates.")
        raise ValueError("Invalid dates format")

    # Merge and process data

    final_df = all_data_df.merge(appraisal_data_df, left_on="Parcel Number", right_on="parcel_id", how="left")
    logging.info(f'These are the dates in the list: {dates}')

    logging.info("Beginning cleaning and formatting data.")
    final_df = clean_and_format_columns(final_df, ["last_transfer_date", "last_sale_amount", "parcel_id"])

    logging.info("Beginning replacing of the street type (i.e. dr, rd, way, etc...) with the new mapping.")    
    pattern = r'\b(' + '|'.join(map(re.escape, street_type_map.keys())) + r')\b'
    final_df['address'] = final_df['address'].str.replace(
                            pattern,
                            lambda m: street_type_map[m.group(0)],
                            regex=True
                        )
    
    logging.info("Owners data is starting the cleaning and formatting data process.")
    final_df = owner_address_cleaner(final_df)


    # Address processing
    logging.info("Processing address columns for geocoding.")
    address_parts = [
    {**tag_address(address), 'parcel_number': parcel}
    for parcel, address in zip(final_df.parcel_number, final_df.address)
    ]
    address_df = pd.DataFrame.from_dict(address_parts)
    address_df = address_df.drop_duplicates()
    print(address_df.parcel_number.value_counts())
    final_df = final_df.merge(address_df, left_on='parcel_number', right_on='parcel_number',how='left')

    # Add city and state
    final_df["city"] = final_df.school_district.map(school_city_map)
    final_df["state"] = "OH"

    # Create concatenated address field
    final_df["new_address"] = np.where(
        final_df["owner_home_address_match"] == "Y",
        final_df["owner_street_address"] + " " + final_df["owner_city"] + ", " +
        final_df["owner_state"] + " " + final_df["owner_postal_code"],
        final_df["st_num"] + " " + final_df["street"] + " " + final_df["city"] + ", " + final_df["state"]
    )
    
    final_df = final_df.drop_duplicates()
    logging.info(f'Removing these dates: {start_date} and {end_date}')
    dates.remove((start_date, end_date))

    # Save CSV files
    homes_csv_path = get_file_path("..", f"{year} Homes.csv")
    all_homes_csv_path = get_file_path("..", "All Homes.csv")
    save_to_csv(final_df, homes_csv_path)
    save_to_csv(final_df, all_homes_csv_path)

    return {"homes_csv": homes_csv_path, "all_homes_csv": all_homes_csv_path}
