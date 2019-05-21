"""agent to server protocol definitions"""
# pylint: disable=invalid-name

common_definitions = {
    "UUID": {
        "type": "string",
        "pattern": r"^[a-f0-9\-]{36}$"
    }
}

assignment = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": common_definitions,

    "type": "object",
    "required": ["id", "module", "params", "targets"],
    "additionalProperties": False,
    "properties": {
        "id": {
            "$ref": "#/definitions/UUID"
        },
        "module": {
            "type": "string"
        },
        "params": {
            "type": "string"
        },
        "targets": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

output = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": common_definitions,

    "type": "object",
    "required": ["id", "retval", "output"],
    "additionalProperties": False,
    "properties": {
        "id": {
            "$ref": "#/definitions/UUID"
        },
        "retval": {
            "type": "integer"
        },
        "output": {
            "type": "string"
        }
    }
}
