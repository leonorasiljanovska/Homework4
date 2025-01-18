# models/__init__.py
from .db import db
from .company import Company
from .company_data import CompanyData

# This ensures all models are imported when importing from models
__all__ = ['db', 'Company', 'CompanyData']
