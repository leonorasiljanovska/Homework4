import os
import pandas as pd

from models import Company, db, CompanyData


def handle_price(price):

    """Handles price fields: removes thousands separators and replaces commas with dots."""
    if isinstance(price, str):
        # Remove thousands separators (.)
        price = price.replace('.', '')
        # Replace commas with dots for decimal point
        price = price.replace(',', '.')
        try:
            # Convert to float
            price = float(price)
        except ValueError:
            price = None  # Set to None if conversion fails
    return price



def import_csv_to_db(csv_folder_path):
    """Imports data from all CSV files in a given folder into the database."""
    for csv_file in os.listdir(csv_folder_path):
        if csv_file.endswith('.csv'):
            file_path = os.path.join(csv_folder_path, csv_file)
            print(f"Processing {file_path}...")

            # Read CSV
            df = pd.read_csv(file_path)

            # Filter rows with empty "Мак." or "Мин."
            df = df.dropna(subset=["Мак.", "Мин."])

            latest_dates = df.groupby('Код')['Датум'].max().to_dict()

            for _, row in df.iterrows():
                # Retrieve or create the Company instance
                company = Company.get_by_code(row['Код'])
                if not company:
                    print(f"Company with code {row['Код']} not found, adding it to the database.")

                    # Create a new Company instance and add it to the database
                    company = Company(
                        company_code=row['Код'],  # Use the company code
                        last_transaction_price=handle_price(row['Цена на последна трансакција']),
                        # Ensure it's a string and replace commas
                        last_info_date=pd.to_datetime(latest_dates[row['Код']]).date()
                    )
                    db.session.add(company)
                    db.session.commit()  # Commit to generate the company ID

                # Handle price fields with the handle_price function
                last_transaction_price = handle_price(row['Цена на последна трансакција'])
                max_price = handle_price(row['Мак.'])
                min_price = handle_price(row['Мин.'])
                average_price = handle_price(row['Просечна цена'])
                price_change_percentage = handle_price(row['%пром.'])
                turnover_best_bests = handle_price(row['Промет во БЕСТ во денари'])
                total_turnover = handle_price(row['Вкупен промет во денари'])

                # Create a CompanyData instance
                company_data = CompanyData(
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
                db.session.add(company_data)

            # Commit changes after processing all rows in the CSV
            db.session.commit()
            print(f"Data from {csv_file} imported successfully!")
