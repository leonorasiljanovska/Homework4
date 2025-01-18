import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from app.services.fundamental_analysis.dict_file import company_name_code


def get_company_name(company_code):
    return company_name_code.get(company_code, None)


def select_date_from_calendar(driver, date_str, date_picker_id):
    # [Previous calendar selection code remains the same]
    date_obj = datetime.strptime(date_str, '%d.%m.%Y')

    def click_date_input():
        try:
            date_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, date_picker_id))
            )
            ActionChains(driver).move_to_element(date_input).click().perform()
            return True
        except:
            return False

    retry_count = 0
    while retry_count < 3:
        if click_date_input():
            break
        retry_count += 1
        if retry_count == 3:
            raise Exception(f"Failed to click date input field {date_picker_id}")

    calendar = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'react-datepicker'))
    )

    def select_year():
        year_select = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'react-datepicker__year-select'))
        )
        for option in year_select.find_elements(By.TAG_NAME, 'option'):
            if option.text == str(date_obj.year):
                option.click()
                return True
        return False

    if not select_year():
        raise ValueError(f"Year {date_obj.year} not found in the calendar")

    months_in_macedonian = [
        "јануари", "февруари", "март", "април", "мај", "јуни",
        "јули", "август", "септември", "октомври", "ноември", "декември"
    ]

    def select_month():
        month_select = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'react-datepicker__month-select'))
        )
        for option in month_select.find_elements(By.TAG_NAME, 'option'):
            if option.text == months_in_macedonian[date_obj.month - 1]:
                option.click()
                return True
        return False

    if not select_month():
        raise ValueError(f"Month {months_in_macedonian[date_obj.month - 1]} not found in the calendar")

    def select_day():
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'react-datepicker__day'))
        )

        day_xpath = f"//div[contains(@class, 'react-datepicker__day') and not(contains(@class, 'outside-month')) and normalize-space(text())='{date_obj.day}']"
        days = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, day_xpath))
        )

        for day in days:
            try:
                if day.is_displayed() and day.is_enabled():
                    day.click()
                    return True
            except:
                continue
        return False

    retry_count = 0
    while retry_count < 3:
        if select_day():
            break
        retry_count += 1
        if retry_count == 3:
            raise ValueError(f"Day {date_obj.day} not found or not clickable in the calendar")

    driver.implicitly_wait(1)


def get_company_code(company_name):
    # Reverse lookup in company_name_code dictionary
    for code, name in company_name_code.items():
        if name == company_name:
            return code
    return None


def select_date_and_download(base_url, company_name):
    download_dir = r"/src/pdfs"
    company_code = get_company_code(company_name)

    if not company_code:
        print(f"Error: Could not find company code for {company_name}")
        return None

    # Configure Chrome to wait for downloads
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    print("Initializing WebDriver...")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(base_url)

    downloaded_count = 0
    file_number = 1

    try:
        # Select language
        language_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "Dropdown_button__3Kee3"))
        )
        language_button.click()

        english_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//li[@data-key='en-GB']"))
        )
        english_option.click()
        time.sleep(1)

        # Select company
        company_select = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "formIssuerId"))
        )
        company_select.click()
        company_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//option[text()='{company_name}']"))
        )
        company_option.click()

        print("Waiting for page to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table[@class='table table-hover']//tbody//tr"))
        )

        # Set date range
        today = datetime.today()
        start_date = today - timedelta(days=19)
        target_date_from = start_date.strftime('%d.%m.%Y')
        target_date_to = today.strftime('%d.%m.%Y')

        print(f"Selecting dates from {target_date_from} to {target_date_to}")
        select_date_from_calendar(driver, target_date_from, "formDateFrom")
        select_date_from_calendar(driver, target_date_to, "formDateTo")

        while True:
            rows = driver.find_elements(By.XPATH, "//table[@class='table table-hover']//tbody//tr")
            print(f"Found {len(rows)} rows on the page.")

            if len(rows) == 0:
                break

            for row_index in range(len(rows)):
                try:
                    # Refresh rows reference
                    rows = driver.find_elements(By.XPATH, "//table[@class='table table-hover']//tbody//tr")
                    tds = rows[row_index].find_elements(By.TAG_NAME, 'td')

                    if len(tds) >= 2:
                        second_td = tds[1]
                        second_td.click()

                        try:
                            download_link = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//div[contains(@title, 'Download file')]"))
                            )

                            if download_link.is_displayed() and download_link.is_enabled():
                                print(f"Downloading file for {company_code} (#{file_number})")

                                # Click download and wait for file
                                download_link.click()
                                time.sleep(5)  # Wait for download to complete

                                # Find the most recently downloaded file
                                latest_file = max([os.path.join(download_dir, f) for f in os.listdir(download_dir)],
                                                  key=os.path.getctime)

                                # Construct new filename
                                new_filename = f"{company_code}{file_number}.pdf"
                                new_filepath = os.path.join(download_dir, new_filename)

                                # Rename the file
                                try:
                                    # If target file already exists, remove it
                                    if os.path.exists(new_filepath):
                                        os.remove(new_filepath)
                                    os.rename(latest_file, new_filepath)
                                    print(f"File renamed to: {new_filename}")
                                    downloaded_count += 1
                                    file_number += 1
                                except Exception as rename_error:
                                    print(f"Error renaming file: {rename_error}")

                        except Exception as e:
                            print(f"No download link found or error downloading: {e}")
                        finally:
                            driver.back()
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located(
                                    (By.XPATH, "//table[@class='table table-hover']//tbody//tr"))
                            )
                            time.sleep(1)

                except Exception as e:
                    print(f"Error processing row {row_index}: {e}")
                    try:
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, "//table[@class='table table-hover']//tbody//tr"))
                        )
                    except:
                        print("Error returning to previous page")
                    continue

            break  # Remove this if implementing pagination

        print(f"Total PDFs downloaded and renamed: {downloaded_count}")
        return downloaded_count

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        print("Closing the browser...")
        driver.quit()
