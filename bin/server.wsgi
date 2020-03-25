# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner server wsgi wrapper
"""

from sner.server.app import create_app


application = create_app()
