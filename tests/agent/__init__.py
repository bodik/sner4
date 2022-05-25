# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent test shared functions
"""

import json

from flask import Response


def xjsonify(obj):
    """app context free jsonify helper"""

    return Response(json.dumps(obj), mimetype='application/json')
