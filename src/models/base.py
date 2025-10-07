"""
Base model for all SQLAlchemy models.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create base class for all models
Base = declarative_base()

# This Base will be imported by all other models