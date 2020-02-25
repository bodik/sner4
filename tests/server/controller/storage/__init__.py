# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage shared test functions
"""

from http import HTTPStatus

from flask import url_for


def check_annotate(client, route_name, test_model):
    """check annotate functionality"""

    form = client.get(url_for(route_name, model_id=test_model.id)).form
    form['tags'] = 'tag1\ntag2'
    form['comment'] = 'annotated'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK

    model = test_model.__class__.query.get(test_model.id)
    assert model.comment == 'annotated'
    assert 'tag2' in model.tags
