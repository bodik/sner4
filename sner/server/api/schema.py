# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 schema
"""

from marshmallow import fields, INCLUDE, Schema, post_dump, validate


class BaseSchema(Schema):
    """base api schema"""

    @post_dump
    def remove_none(self, data, **kwargs):  # pylint: disable=unused-argument
        """Remove None fields"""

        return {key: value for key, value in data.items() if (value is not None) and (value != [])}


class JobAssignArgsSchema(BaseSchema):
    """/api/v2/scheduler/job/assign request"""

    queue = fields.String()
    caps = fields.List(fields.String)


class JobAssignmentConfigSchema(BaseSchema):
    """
    nested assignment config schema.
    tweaked in order to serialize unknown fields, modules config attributes are of free-form
    """

    class Meta:  # pylint: disable=too-few-public-methods,missing-class-docstring
        unknown = INCLUDE
    module = fields.String(required=True)

    # allow uknown fields to be dumped
    # https://github.com/marshmallow-code/marshmallow/issues/1545
    @post_dump(pass_original=True)
    def keep_unknowns(self, output, orig, **kwargs):  # pylint: disable=unused-argument
        """postprocess during serialize"""

        for key in orig:
            if key not in output:
                output[key] = orig[key]
        return output


class JobAssignmentSchema(BaseSchema):
    """assignment schema"""

    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    config = fields.Nested(JobAssignmentConfigSchema, required=True)
    targets = fields.List(fields.String, required=True)


class JobOutputSchema(BaseSchema):
    """job output schema"""

    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    retval = fields.Integer()
    output = fields.String()


class PublicHostArgsSchema(BaseSchema):
    """public host args schema"""

    address = fields.IP(required=True)


class PublicNoteSchema(BaseSchema):
    """public note schema"""

    via_target = fields.String()
    xtype = fields.String()
    data = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    import_time = fields.DateTime()


class PublicServiceSchema(BaseSchema):
    """service schema"""

    proto = fields.String(required=True)
    port = fields.Integer(required=True)
    state = fields.String()
    info = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    rescan_time = fields.DateTime()
    import_time = fields.DateTime()
    notes = fields.List(fields.Nested(PublicNoteSchema))


class PublicHostSchema(BaseSchema):
    """public host schema"""

    address = fields.String(required=True)
    hostname = fields.String()
    os = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    rescan_time = fields.DateTime()
    services = fields.List(fields.Nested(PublicServiceSchema))
    notes = fields.List(fields.Nested(PublicNoteSchema))


class PublicRangeArgsSchema(BaseSchema):
    """public cidr schema"""

    cidr = fields.IPInterface(required=True)


class PublicRangeServiceSchema(BaseSchema):
    """public range service schema"""

    proto = fields.String(required=True)
    port = fields.Integer(required=True)
    state = fields.String()
    info = fields.String()


class PublicRangeSchema(BaseSchema):
    """public range schema"""

    address = fields.String(required=True)
    hostname = fields.String()
    os = fields.String()
    services = fields.List(fields.Nested(PublicRangeServiceSchema))


class PublicServicelistArgsSchema(BaseSchema):
    """public service list args schema"""

    filter = fields.String()


class PublicServicelistSchema(BaseSchema):
    """public service list schema"""

    address = fields.String()
    hostname = fields.String()
    proto = fields.String()
    port = fields.Integer()
    state = fields.String()
    info = fields.String()


class PublicNotelistArgsSchema(BaseSchema):
    """public note list args schema"""

    filter = fields.String()


class PublicNotelistSchema(BaseSchema):
    """public note list schema"""

    address = fields.String()
    hostname = fields.String()
    proto = fields.String()
    port = fields.Integer()
    via_target = fields.String()
    xtype = fields.String()
    data = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    import_time = fields.DateTime()


class ElasticHostSchema(PublicHostSchema):
    """elastic storage_host schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()
    services_count = fields.Integer()
    vulns_count = fields.Integer()
    notes_count = fields.Integer()


class ElasticServiceSchema(PublicServiceSchema):
    """elastic storage_service schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()


class ElasticNoteSchema(PublicNoteSchema):
    """elastic storage_note schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()
    service_proto = fields.String()
    service_port = fields.Integer()


class PublicVersionInfoArgsSchema(BaseSchema):
    """public versioninfo args schema"""

    filter = fields.String()
    product = fields.String()
    versionspec = fields.String()


class PublicVersionInfoSchema(BaseSchema):
    """public versioninfo schema"""

    # endpoint data
    host_address = fields.String()
    host_hostname = fields.String()
    service_proto = fields.String()
    service_port = fields.Integer()
    via_target = fields.String()
    # product data
    product = fields.String()
    version = fields.String()
    extra = fields.Dict()


class PublicVulnsearchArgsSchema(BaseSchema):
    """public vulnsearch list args schema"""

    filter = fields.String()


class PublicVulnsearchSchema(BaseSchema):
    """public vulnsearch schema"""

    # endpoint data
    host_address = fields.String()
    host_hostname = fields.String()
    service_proto = fields.String()
    service_port = fields.Integer()
    via_target = fields.String()

    # vulnsearch data
    cveid = fields.String()
    name = fields.String()
    description = fields.String()
    cvss = fields.Float()
    cvss3 = fields.Float()
    attack_vector = fields.String()
    data = fields.String()
    cpe = fields.Dict()
    cpe_full = fields.String()
