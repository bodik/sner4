"""extension registry for the project. flask heavily uses global singletons pattern"""

from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy



toolbar = DebugToolbarExtension() # pylint: disable=invalid-name
db = SQLAlchemy() # pylint: disable=invalid-name
