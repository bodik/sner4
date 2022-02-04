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

from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService
from sner.server.scheduler.models import Excl, ExclFamily, Job, Queue, Readynet, Target
from sner.server.utils import yaml_dump
from tests import BaseModelFactory


class QueueFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test queue model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test queue model factory"""
        model = Queue

    name = 'testqueue'
    config = yaml_dump({'module': 'dummy', 'args': '--arg1 abc --arg2'})
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
    hashval = SchedulerService.hashval(target)

    @post_generation
    def make_output(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """create on-disk output if create requested"""

        if not create:
            return

        # if target gets created in database, readynets must be updated in order to be assignable
        if self.hashval not in SchedulerService.grep_hot_hashvals([self.hashval]):
            db.session.merge(Readynet(queue_id=self.queue.id, hashval=self.hashval))  # pylint: disable=no-member
            db.session.commit()


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

    @post_generation
    def account_heatmap(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """account heatmap with prefabricated job targets"""

        if not create:
            return

        SchedulerService.get_lock()
        for target in json.loads(self.assignment)['targets']:
            SchedulerService.heatmap_put(SchedulerService.hashval(target))
        SchedulerService.release_lock()


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

    @post_generation
    def account_heatmap(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """override JobFactory heatmap accounting"""

        return


class ExclNetworkFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test excl network model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test excl network model factory"""
        model = Excl

    family = ExclFamily.NETWORK
    value = '127.66.66.0/26'
    comment = 'blocked test netrange, no traffic should go there'


class ExclRegexFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test excl regex model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test excl regex model factory"""
        model = Excl

    family = ExclFamily.REGEX
    value = 'notarget[012]'
    comment = 'targets blocked by regex'
