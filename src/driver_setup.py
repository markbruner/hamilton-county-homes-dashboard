import logging
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException
from urllib.parse import urlparse

from utils.form_helpers import safe_quit

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def init_driver(base_url, driver_type="firefox", max_retries=3, timeout=10):
    if not is_valid_url(base_url):
        logging.error(f"Invalid URL provided: {base_url}")
        raise ValueError(f"Invalid URL: {base_url}")
    
    driver = None
    for attempt in range(max_retries):
        try:
            if driver_type.lower() == "firefox":
                driver = webdriver.Firefox()
            elif driver_type.lower() == "chrome":
                driver = webdriver.Chrome()
            else:
                raise ValueError(f"Unsupported driver type: {driver_type}")
            driver.get(base_url)
            logging.info(f"Driver initialized and navigated to {base_url}.")
            return driver, WebDriverWait(driver, timeout)   
        except WebDriverException as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
        except TimeoutException as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    if driver:
        safe_quit(driver)
    logging.error(f"Failed to initialize WebDriver after {max_retries} attempts.")
    raise WebDriverException(f"Failed to initialize WebDriver after {max_retries} attempts.")