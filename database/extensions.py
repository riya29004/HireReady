# # ============================================================
# #  HireReady — database/extensions.py
# #
# #  Why does this file exist?
# #  ─────────────────────────
# #  If we created db = SQLAlchemy() inside models.py and also
# #  imported it in app.py, Python would create circular imports
# #  (A imports B, B imports A — infinite loop).
# #
# #  The fix: create db here in a neutral file.
# #  Both app.py and models.py import db from THIS file.
# #  No circular imports, clean separation.
# # ============================================================

# from flask_sqlalchemy import SQLAlchemy

# # This is the single shared db instance used everywhere
# db = SQLAlchemy()

# ============================================================
#  HireReady — database/extensions.py
#
#  Single db instance shared across the entire app.
#  Defined here to avoid circular imports.
#
#  Usage everywhere else:
#      from database.extensions import db
# ============================================================

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()