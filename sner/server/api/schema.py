# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 schema
"""

from marshmallow import fields, INCLUDE, Schema, post_dump, validate


class JobAssignArgsSchema(Schema):
    """/api/scheduler/job/assign request"""

    queue = fields.String()
    caps = fields.List(fields.String)


class JobAssignmentConfigSchema(Schema):
    """
    nested assignment config schema.
    tweaked in order to serialize unknown fields (modules config attributes are of free-form
    """

    class Meta:  # pylint: disable=too-few-public-methods,missing-class-docstring
        unknown = INCLUDE
    module = fields.String(required=True)

    # allow uknown fields to be dumped
    # https://github.com/marshmallow-code/marshmallow/issues/1545
    @post_dump(pass_original=True)
    def keep_unknowns(self, output, orig, **kwargs):  # pylint: disable=no-self-use,unused-argument
        """postprocess during serialize"""

        for key in orig:
            if key not in output:
                output[key] = orig[key]
        return output


class JobAssignmentSchema(Schema):
    """/api/scheduler/job/assign response"""

    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    config = fields.Nested(JobAssignmentConfigSchema, required=True)
    targets = fields.List(fields.String, required=True)


class JobOutputSchema(Schema):
    """/api/scheduler/job/output request"""

    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    retval = fields.Integer()
    output = fields.String()


class PublicHostQuerySchema(Schema):
    """/api/public/storage/host query"""

    address = fields.IP(required=True)


class PublicHostSchema(Schema):
    """/api/public/storage/host response"""

    address = fields.String(required=True)
    hostname = fields.String()
    os = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    rescan_time = fields.DateTime()
