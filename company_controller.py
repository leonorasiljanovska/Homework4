from datetime import timedelta, datetime
from flask import Flask, render_template, request
from flask_migrate import Migrate
from sqlalchemy import text
import os

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from app.services.LSTM.LSTM_prediction import perform_lstm_prediction
from app.services.fundamental_analysis.NLP_prediction import perform_nlp_recommendation
from app.services.fundamental_analysis.scraping_pdfs_for_company import get_company_name, select_date_and_download
from app.models.db import db
from selenium import webdriver
from app.models import Company, CompanyData

from app.services.technical_analysis.calculations import calculate_for_date_range
from your_scraping_script import get_company_codes, update_single_company_data

# Initialize the WebDriver options (for better performance)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode for speed
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


#
#
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

@app.route("/company/<company_code>/download-pdfs", methods=["GET"])
def download_pdfs(company_code):
    company_name = get_company_name(company_code)  # Fetch the company name using the provided company code
    if company_name:
        # Call the function that selects date and downloads the PDFs for the given company
        try:
            num_pdfs = select_date_and_download("https://www.seinet.com.mk/search/10", company_name)
            if num_pdfs is None:
                return f"There were no news for the company {company_name} found."  # Update base_url accordingly
            return f"{num_pdfs} PDFs were successfully downloaded for {company_name}!"
        except Exception as e:
            return f"Error while downloading PDFs: {str(e)}", 500
    else:
        return "Invalid company code", 400


@app.route("/", methods=["GET", "POST"])
def home():
    driver = webdriver.Chrome(options=options)
    message = None
    labels = []
    prices = []

    # Calculate the first and last day of the last month
    today = datetime.today()
    first_day_of_last_month = datetime(today.year, today.month - 1, 1) if today.month > 1 else datetime(today.year - 1,
                                                                                                        12, 1)
    last_day_of_last_month = datetime(today.year, today.month, 1) - timedelta(days=1)

    if request.method == "POST":
        company_code = request.form.get('company_code')  # Get the selected company code

        if company_code:
            try:
                # Query the database to get the selected company data
                company = db.session.query(Company).filter(Company.company_code == company_code).first()

                if company:
                    last_info_date = company.last_info_date
                    last_transaction_price = company.last_transaction_price

                    # Call your update function (you'll need to pass these values to your update function)
                    update_single_company_data(company_code, driver, db.session)

                    # Fetch the company data for the last month only
                    company_data = db.session.query(CompanyData).filter(
                        CompanyData.company_id == company.id,
                        CompanyData.date >= first_day_of_last_month,
                        CompanyData.date <= last_day_of_last_month
                    ).all()

                    # Prepare the data for the chart
                    labels = [data.date.strftime('%Y-%m-%d') for data in
                              company_data]  # Formatting the date for x-axis labels
                    prices = [data.last_transaction_price for data in company_data]  # Prices for the chart

                    # Create a success message
                    message = f"Data for company {company_code} has been updated successfully!<br>Last Info Date: {last_info_date}<br>Last Transaction Price: {last_transaction_price}"
                else:
                    message = f"No data found for company {company_code}."
            except Exception as e:
                message = f"Error updating company {company_code}: {e}"
        else:
            message = "Please select a company."

    # Render the template with the message, company codes, and chart data
    return render_template(
        "home.html",
        company_codes=get_sorted_companies(),
        message=message,
        labels=labels,
        prices=prices
    )


@app.route("/about")
def about():
    # Render the about us.html template
    return render_template("about-us.html")


def get_sorted_companies():
    return sorted(Company.query.all(), key=lambda c: c.company_code)


@app.route("/lstm", methods=["GET", "POST"])
def lstm():
    if request.method == "POST":

        company_code = request.form['company_code']
        recommendation, predictions, rmse = perform_lstm_prediction(company_code)

        # Update the LSTM prediction in the database
        company = Company.query.filter_by(company_code=company_code).first()
        if company:
            company.LSTM_prediction = recommendation
            db.session.commit()

            print(company.LSTM_prediction)
        # Return results to the LSTM page
        return render_template('lstm.html', prediction=company.LSTM_prediction,
                               company_codes=get_sorted_companies())

    else:
        return render_template("lstm.html", company_codes=get_sorted_companies())


@app.route("/nlp", methods=["GET", "POST"])
def nlp():
    company_codes = sorted(Company.query.all(), key=lambda c: c.company_code)  # Sorted list of company codes

    if request.method == "POST":
        company_code = request.form.get('company_code')
        nlp_recommendation = perform_nlp_recommendation(company_code)

        # Update NLP recommendation in the database
        db.session.execute(
            text("""UPDATE public."Companies"
                    SET "NLP_recommendation" = :nlp_recommendation
                    WHERE company_code = :company_code"""),
            {'company_code': company_code, 'nlp_recommendation': nlp_recommendation}
        )
        db.session.commit()

        return render_template("nlp.html", recommendation=nlp_recommendation,
                               company_codes=get_sorted_companies()
                               )
    else:
        return render_template("nlp.html", company_codes=get_sorted_companies())


@app.route("/forecasts", methods=["GET", "POST"])
def forecasts():
    company_codes = sorted(Company.query.all(), key=lambda c: c.company_code)  # Sorted list of company codes

    if request.method == "POST":
        try:
            # Get inputs from the form
            company_code = request.form['company_code']
            selected_period = request.form['period']  # Options: day, week, month

            # Fetch the company's last_info_date
            company = Company.query.filter_by(company_code=company_code).first()
            if not company or not company.last_info_date:
                return f"No data available for company {company_code}", 400

            last_info_date = company.last_info_date

            # Determine the start_date based on the selected period
            if selected_period == 'day':
                start_date = last_info_date - timedelta(days=1)
            elif selected_period == 'week':
                start_date = last_info_date - timedelta(weeks=1)
            elif selected_period == 'month':
                start_date = last_info_date - timedelta(days=30)
            else:
                return "Invalid period selected!", 400

            # Simulate fetching forecast signals
            signal = calculate_for_date_range((start_date, last_info_date))

            # Update the relevant column in the database
            column_name = {
                'day': 'forecast_day',
                'week': 'forecast_week',
                'month': 'forecast_month'
            }.get(selected_period, 'forecast_day')

            db.session.execute(
                text(f"""
                    UPDATE public."Companies"
                    SET {column_name} = :signal
                    WHERE company_code = :company_code
                """),
                {'company_code': company_code, 'signal': signal}
            )
            db.session.commit()

            # Render results
            return render_template(
                "forecasts.html",
                company_codes=get_sorted_companies(),
                company_code=company_code,
                selected_period=selected_period,
                start_date=start_date,
                last_info_date=last_info_date,
                signal=signal
            )
        except Exception as e:
            print(f"Error in forecasts route: {e}")
            return render_template("forecasts.html", company_codes=get_sorted_companies(), signal=None)
    else:
        # Render the page with an empty form
        return render_template("forecasts.html", company_codes=get_sorted_companies(), signal=None)
