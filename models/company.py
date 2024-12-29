# models/company.py
from datetime import date
from .db import db


class Company(db.Model):
    __tablename__ = 'Companies'

    id = db.Column(db.Integer, primary_key=True)
    company_code = db.Column(db.String(100), unique=True, nullable=False)
    last_transaction_price = db.Column(db.Float, nullable=False)
    last_info_date = db.Column(db.Date, nullable=False, default=date.today)
    forecast_day = db.Column(db.String(10), nullable=True)
    forecast_week = db.Column(db.String(10), nullable=True)
    forecast_month = db.Column(db.String(10), nullable=True)
    NLP_recommendation = db.Column(db.String(50), nullable=True)
    LSTM_prediction = db.Column(db.String(50), nullable=True)


    # Relationship with CompanyData
    company_data = db.relationship('CompanyData', backref='company', lazy=True)

    def __repr__(self):
        return f"<Company {self.company_code}, Last Info Date {self.last_info_date}>"

    def add_to_db(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_by_code(company_code):
        return Company.query.filter_by(company_code=company_code).first()
