# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler test models
"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from factory import LazyAttribute, post_generation, SubFactory

from sner.server.scheduler.models import Excl, ExclFamily, Job, Queue, Target
from tests import BaseModelFactory


class QueueFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test queue model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test queue model factory"""
        model = Queue

    name = 'testqueue'
    module = 'test'
    config = '--arg1 abc --arg2'
    group_size = 1
    priority = 10
    active = True


class TargetFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test target model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test target model factory"""
        model = Target

    queue = SubFactory(QueueFactory)
    target = 'testtarget'


class JobFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test job model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test job model factory"""
        model = Job

    id = LazyAttribute(lambda x: str(uuid4()))
    queue = SubFactory(QueueFactory)
    assignment = json.dumps({'module': 'testjob', 'targets': ['1', '2']})
    retval = None
    time_start = datetime.now()
    time_end = None


class JobCompletedFactory(JobFactory):  # pylint: disable=too-few-public-methods
    """test completed job model factory"""

    retval = 0
    time_end = datetime.utcnow()

    @post_generation
    def make_output(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """create on-disk output if create requested"""

        if not create:
            return

        output_abspath = self.output_abspath  # pylint: disable=no-member ; sqla computed property
        Path(output_abspath).parent.mkdir(parents=True, exist_ok=True)
        if extracted:
            Path(output_abspath).write_bytes(extracted)
        else:
            with open(output_abspath, 'wb') as job_file:
                with ZipFile(job_file, 'w') as zip_file:
                    zip_file.writestr('assignment.json', self.assignment)

        return


class ExclNetworkFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test excl network model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test excl network model factory"""
        model = Excl

    family = ExclFamily.network
    value = '127.66.66.0/26'
    comment = 'blocked test netrange, no traffic should go there'


class ExclRegexFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test excl regex model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test excl regex model factory"""
        model = Excl

    family = ExclFamily.regex
    value = 'notarget[012]'
    comment = 'targets blocked by regex'
