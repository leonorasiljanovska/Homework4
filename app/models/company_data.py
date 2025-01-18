# models/company_data.py
from .db import db


class CompanyData(db.Model):
    __tablename__ = 'CompaniesData'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('Companies.id'), nullable=False)  # Note the capital C in Companies
    date = db.Column(db.Date, nullable=False)
    last_transaction_price = db.Column(db.Float, nullable=False)
    max_price = db.Column(db.Float, nullable=True)
    min_price = db.Column(db.Float, nullable=True)
    average_price = db.Column(db.Float, nullable=True)
    price_change_percentage = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    turnover_best_bests = db.Column(db.Float, nullable=True)
    total_turnover = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<CompanyData CompanyID: {self.company_id}, Date: {self.date}>"

    def add_to_db(self):
        db.session.add(self)
        db.session.commit()
