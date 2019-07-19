# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent to server protocol definition


## Agent-Server protocol is defined by following ABNF

### Definitions

queue-id                = 1*DIGIT / 1*ALPHA

nowork                  = jsonobject
                            ; {}

assignment              = jsonobject
                            ; {
                            ;   "id": uuid,
                            ;   "module": string,
                            ;   "params": string,
                            ;   "targets": array of strings
                            ; }

output                  = jsonobject
                            ; {
                            ;   "id": uuid,
                            ;   "retval": int,
                            ;   "output": string, base64 encoded data
                            ; }

apikey                  = 1*DIGIT / 1*HEXDIG
auth-header:            = "Authorization:" SP "Apikey" SP apikey

http-ok                 = "HTTP/1.1 200 OK" CRLF CRLF
                            ; standard http response
http-bad-request        = "HTTP/1.1 400 Bad Request" CRLF CRLF
                            ; standard http response


### Request assignment/job

request-assign-job      = "GET /api/v1/scheduler/job/assign" ["/" queue-id] SP "HTTP/1.1" CRLF auth-header CRLF CRLF
response-assign-job	= response-nowork / response-assignment
response-nowork		= http-ok nowork
response-assignment	= http-ok assignment


### Upload assignment/job output

request-job-output	= "POST /api/v1/scheduler/job/output HTTP/1.1" CRLF auth-header CRLF CRLF output
response-job-output	= response-accepted / response-refused
response-accepted	= http-ok
                            ; output accepted
response-refused	= http-bad-request
                            ; malformed request or output refused
"""
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
