# database/__init__.py
# Makes 'database' a Python package.
# Import the db instance from here if needed elsewhere.

from database.extensions import db

__all__ = ["db"]