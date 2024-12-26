from datetime import datetime, timedelta
from flask import Flask, render_template, request
from flask_migrate import Migrate
from sqlalchemy import text
from models.db import db
from import_csv import import_csv_to_db
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

from technical_analysis.calculations import calculate_for_date_range
from your_scraping_script import update_single_company_data, get_company_codes  # Import scraping functions

# Initialize the WebDriver options (for better performance)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode for speed
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


# Create Flask app and configure the database
def create_app():
    app = Flask(__name__)

    # Configure your database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:LeaPsql@localhost/StockCompaniesData'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the db with the app
    db.init_app(app)
    migrate = Migrate(app, db)

    # Create tables
    with app.app_context():
        db.create_all()

    return app


app = create_app()


@app.route("/company/<company_code>", methods=["GET", "POST"])
def company_info(company_code):
    # Fetch the last_info_date for the selected company from the Companies table
    query = text('SELECT last_info_date FROM public."Companies" WHERE company_code = :company_code')
    result = db.session.execute(query, {'company_code': company_code}).fetchone()

    # Handle cases where no data is found
    if result is None or result.last_info_date is None:
        return f"No data available for company {company_code}", 400

    last_info_date = result.last_info_date

    if request.method == "POST":
        # Get the selected period
        selected_period = request.form.get('period')

        # Calculate the start date based on the selected period
        if selected_period == 'day':
            start_date = last_info_date - timedelta(days=1)
        elif selected_period == 'week':
            start_date = last_info_date - timedelta(weeks=1)
        elif selected_period == 'month':
            start_date = last_info_date - timedelta(days=30)
        else:
            return "Invalid period selected!", 400

        # Define the date range
        date_range = (start_date, last_info_date)

        # Simulate fetching data for the date range and calculating indicators/oscillators
        indicators, oscillators = calculate_for_date_range(date_range)

        # Render the results or return as a string
        return f"Calculated for {company_code}: period {selected_period} from {start_date} to {last_info_date}"

    return render_template("company_info.html", company_code=company_code)


# @app.route('/')
# def initialize_app():
#     return 'App initialized! Visit /import-csv to import data.'


@app.route('/import-csv')
def import_csv():
    try:
        csv_folder = os.path.join(os.path.dirname(__file__), 'csv last')
        import_csv_to_db(csv_folder)
        return 'CSV import completed successfully!'
    except Exception as e:
        return f'Error during import: {str(e)}', 500


# Route to display the company dropdown and update data for selected company
@app.route("/", methods=["GET", "POST"])
def index():
    # Start the Selenium WebDriver (ensure you have the appropriate WebDriver installed)
    driver = webdriver.Chrome(options=options)  # Update path to chromedriver

    # Fetch all company codes to populate the dropdown
    company_codes = get_company_codes(driver)

    if request.method == "POST":
        # Get the selected company code from the form
        selected_code = request.form.get("company_code")
        if selected_code:
            # Call the update function for the selected company code
            update_single_company_data(selected_code, driver, db.session)
            return f"Data for company {selected_code} has been updated successfully!"

    # Render the HTML template with company codes for the dropdown
    return render_template("index.html", company_codes=company_codes)


if __name__ == '__main__':
    app.run(debug=True)
