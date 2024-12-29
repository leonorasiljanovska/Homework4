import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from import_csv import handle_price
from models import Company, CompanyData, db


def get_company_codes(driver):
    url = "https://www.mse.mk/mk/stats/symbolhistory/ADIN"
    driver.get(url)
    time.sleep(3)

    dropdown = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "Code"))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    options = soup.select('#Code option')
    company_codes = [option['value'] for option in options if option['value'] and not re.search(r'\d', option['value'])]

    print(f"Retrieved {len(company_codes)} company codes.")
    # print(company_codes)
    return company_codes


def update_single_company_data(code, driver, db_session):
    """
    Scrapes data for a single company starting from its last_info_date in the database.
    Updates the database with new data.

    :param code: The company code to scrape data for.
    :param driver: Selenium WebDriver instance for scraping.
    :param db_session: SQLAlchemy session for database interaction.
    """
    from datetime import timedelta
    from datetime import datetime
    import pandas as pd

    # Fetch the company from the database
    company = db_session.query(Company).filter(Company.company_code == code).first()

    if not company:
        print(f"Company with code {code} does not exist in the database. Adding it.")
        # Default start date if the company is new, no need from going 10 years back
        start_date = datetime.today() - timedelta(days=365)
        company = Company(company_code=code, last_transaction_price=0, last_info_date=start_date.date())
        db_session.add(company)
        db_session.commit()
    else:
        # Fetch the company's last info date from the database
        start_date = company.last_info_date  # Start from the next day after last_info_date

    # + timedelta(days=1)
    # Get today's date as the end date
    end_date = datetime.today().date()
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    if start_date > end_date:
        print(f"No new data to fetch for {code}. Start date ({start_date}) is after today's date ({end_date}).")
        return

    print(f"Scraping data for company {code} from {start_date} to {end_date}.")

    current_date = start_date

    while current_date <= end_date:
        days_diff = (end_date - current_date).days

        # Define the range to fetch based on the current date
        if days_diff <= 7:
            to_date = current_date + timedelta(days=days_diff)  # Weekly
        elif days_diff <= 30:
            to_date = current_date + timedelta(days=7)  # Weekly
        elif days_diff <= 365:
            to_date = current_date + timedelta(days=30)  # Monthly
        else:
            to_date = current_date + timedelta(days=365)  # Yearly

        # Ensure 'from_date' is always earlier than or equal to 'to_date'
        if to_date <= current_date:
            to_date = current_date

        from_date_str = current_date.strftime('%d.%m.%Y')
        to_date_str = to_date.strftime('%d.%m.%Y')

        url = f"https://www.mse.mk/mk/stats/symbolhistory/{code}"
        driver.get(url)

        try:
            from_date_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "FromDate")))
            to_date_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "ToDate")))

            # Input date range
            from_date_input.clear()
            from_date_input.send_keys(from_date_str)
            to_date_input.clear()
            to_date_input.send_keys(to_date_str)

            show_button = driver.find_element(By.CSS_SELECTOR, 'input[value="Прикажи"]')
            show_button.click()

            # Wait for table to load
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#resultsTable")))

            # Scrape data from the table
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.select_one('#resultsTable tbody')
            rows = [
                [col.get_text(strip=True) if col.get_text(strip=True) != '0' else None for col in row.select('td')]
                for row in table.select('tr') if row.select('td')
            ]

            # Convert the scraped rows to a DataFrame for easy handling
            df = pd.DataFrame(rows, columns=[
                "Датум", "Цена на последна трансакција", "Мак.", "Мин.", "Просечна цена", "%пром.",
                "Количина", "Промет во БЕСТ во денари", "Вкупен промет во денари"
            ])

            # Drop rows where "Мак." or "Мин." are missing or empty
            df = df.dropna(subset=["Мак.", "Мин."])

            # Insert new data into the database
            last_transaction_price = None  # Track the last transaction price

            valid_rows = []

            for _, row in df.iterrows():
                # Check for required fields
                if not row["Датум"] or not row["Цена на последна трансакција"]:
                    continue  # Skip rows with missing essential data

                data_date = datetime.strptime(row["Датум"], '%d.%m.%Y').date()
                # Handle price fields with the handle_price function
                last_transaction_price = handle_price(row['Цена на последна трансакција'])

                # Skip rows where transaction price is invalid after processing
                if last_transaction_price is None:
                    continue

                max_price = handle_price(row['Мак.'])
                min_price = handle_price(row['Мин.'])
                average_price = handle_price(row['Просечна цена'])
                price_change_percentage = handle_price(row['%пром.'])
                turnover_best_bests = handle_price(row['Промет во БЕСТ во денари'])
                total_turnover = handle_price(row['Вкупен промет во денари'])

                # Create a CompanyData instance
                valid_rows.append(
                    CompanyData(
                        company_id=company.id,
                        date=pd.to_datetime(row['Датум']),
                        last_transaction_price=last_transaction_price,  # Store as string
                        max_price=max_price,
                        min_price=min_price,
                        average_price=average_price,
                        price_change_percentage=price_change_percentage,
                        quantity=row['Количина'],
                        turnover_best_bests=turnover_best_bests,
                        total_turnover=total_turnover
                    )
                )
            if valid_rows:
                db_session.bulk_save_objects(valid_rows)
                db_session.commit()
                print(f"Inserted {len(valid_rows)} valid rows for company {code}.")
            else:
                print(f"No valid rows to insert for company {code}.")

            latest_company_data = db_session.query(CompanyData).filter(
                CompanyData.company_id == company.id,
                CompanyData.date <= end_date
            ).order_by(CompanyData.date.desc()).first()

            # Update the company's last transaction price if data exists
            if latest_company_data:
                company.last_transaction_price = latest_company_data.last_transaction_price
                db_session.commit()

            # # Update the company's last transaction price with the latest one
            # if last_transaction_price is not None:
            #     company.last_transaction_price = last_transaction_price
            #     db_session.commit()

            print(f"Data for {code} updated from {from_date_str} to {to_date_str}.")

        except TimeoutException:
            print(f"Timeout while fetching data for {code} from {from_date_str} to {to_date_str}. Skipping this range.")

        # Move to the next range
        current_date = to_date + timedelta(days=1)

    # Update the company's last_info_date in the database
    company.last_info_date = end_date
    db_session.commit()
    print(f"Finished updating data for company {code}. Last info date set to {end_date}.")

# def update_single_company_data(code, driver, db_session):
#     """
#     Scrapes data for a single company starting from its last_info_date in the database.
#     Updates the database with new data.
#
#     :param code: The company code to scrape data for.
#     :param driver: Selenium WebDriver instance for scraping.
#     :param db_session: SQLAlchemy session for database interaction.
#     """
#     from datetime import timedelta
#     from datetime import datetime
#     import pandas as pd
#
#     # Fetch the company from the database
#     company = db_session.query(Company).filter(Company.code == code).first()
#
#     if not company:
#         print(f"Company with code {code} does not exist in the database. Adding it.")
#         # Default start date if the company doesn't exist: 10 years ago
#         start_date = datetime.today() - timedelta(days=365 * 10)
#         company = Company(company_code=code, last_info_date=start_date.date())
#         db_session.add(company)
#         db_session.commit()
#     else:
#         # Fetch the company's last info date from the database
#         start_date = company.last_info_date + timedelta(days=1)  # Start from the next day after last_info_date
#
#     # Get today's date as the end date
#     end_date = datetime.today().date()
#
#     if start_date > end_date:
#         print(f"No new data to fetch for {code}. Start date ({start_date}) is after today's date ({end_date}).")
#         return
#
#     print(f"Scraping data for company {code} from {start_date} to {end_date}.")
#
#     current_date = start_date
#
#     while current_date <= end_date:
#         days_diff = (end_date - current_date).days
#
#         # Define the range to fetch based on the current date
#         if days_diff <= 7:
#             to_date = current_date + timedelta(days=days_diff)  # Weekly
#         elif days_diff <= 30:
#             to_date = current_date + timedelta(days=7)  # Weekly
#         elif days_diff <= 365:
#             to_date = current_date + timedelta(days=30)  # Monthly
#         else:
#             to_date = current_date + timedelta(days=365)  # Yearly
#
#         # Ensure 'from_date' is always earlier than or equal to 'to_date'
#         if to_date <= current_date:
#             to_date = current_date
#
#         from_date_str = current_date.strftime('%d.%m.%Y')
#         to_date_str = to_date.strftime('%d.%m.%Y')
#
#         url = f"https://www.mse.mk/mk/stats/symbolhistory/{code}"
#         driver.get(url)
#
#         try:
#             from_date_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "FromDate")))
#             to_date_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "ToDate")))
#
#             # Input date range
#             from_date_input.clear()
#             from_date_input.send_keys(from_date_str)
#             to_date_input.clear()
#             to_date_input.send_keys(to_date_str)
#
#             show_button = driver.find_element(By.CSS_SELECTOR, 'input[value="Прикажи"]')
#             show_button.click()
#
#             # Wait for table to load
#             WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#resultsTable")))
#
#             # Scrape data from the table
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             table = soup.select_one('#resultsTable tbody')
#             rows = [
#                 [col.get_text(strip=True) if col.get_text(strip=True) != '0' else None for col in row.select('td')]
#                 for row in table.select('tr') if row.select('td')
#             ]
#
#             # Convert the scraped rows to a DataFrame for easy handling
#             df = pd.DataFrame(rows, columns=[
#                 "Date", "Цена на последна трансакција", "Мак.", "Мин.", "Просечна цена", "%пром.",
#                 "Количина", "Промет во БЕСТ во денари", "Вкупен промет во денари"
#             ])
#
#             # Drop rows where "Мак." or "Мин." are missing or empty
#             df = df.dropna(subset=["Мак.", "Мин."])
#
#             # Insert new data into the database
#             for _, row in df.iterrows():
#                 data_date = datetime.strptime(row["Date"], '%d.%m.%Y').date()
#
#                 # Insert the data without checking for existing entries
#                 new_entry = CompanyData(
#                     company_id=company.id,  # Use the company's ID from the Companies table
#                     date=data_date,
#                     last_transaction_price=row["Цена на последна трансакција"],
#                     max_price=row["Мак."],
#                     min_price=row["Мин."],
#                     average_price=row["Просечна цена"],
#                     price_change_percentage=row["%пром."],
#                     quantity=row["Количина"],
#                     turnover_best_bests=row["Промет во БЕСТ во денари"],
#                     total_turnover=row["Вкупен промет во денари"]
#                 )
#                 db_session.add(new_entry)
#
#             db_session.commit()
#             print(f"Data for {code} updated from {from_date_str} to {to_date_str}.")
#
#         except TimeoutException:
#             print(f"Timeout while fetching data for {code} from {from_date_str} to {to_date_str}. Skipping this range.")
#
#         # Move to the next range
#         current_date = to_date + timedelta(days=1)
#
#     # Update the company's last_info_date in the database
#     company.last_info_date = end_date
#     db_session.commit()
#     print(f"Finished updating data for company {code}. Last info date set to {end_date}.")
