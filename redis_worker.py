import collections
import dataclasses
import databases
import redis
import httpx
import json
import socket
import time
from time import sleep

from quart import Quart, request, abort, g
from quart_schema import QuartSchema, RequestSchemaValidationError, validate_request

app = Quart(__name__)
QuartSchema(app)

async def worker(testdata):
    r = httpx.post("http://"+socket.getfqdn("127.0.0.1:5400/results"),data=json.dumps(testdata), headers={'Content-Type': 'application/json'})
    return r
