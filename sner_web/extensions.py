"""extension registry (mainly flask global singletons)"""

from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy


toolbar = DebugToolbarExtension() # pylint: disable=invalid-name
db = SQLAlchemy() # pylint: disable=invalid-name
