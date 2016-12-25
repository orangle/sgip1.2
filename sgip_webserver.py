#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SGIP Server, Http server, client->server->sgip(联通)
"""
import sys

from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site

from sgip_client import send_sms

reload(sys)
sys.setdefaultencoding('utf8')

try:
    import json
except:
    import simplejson as json


class SmsAPI(Resource):
    def render_GET(self, request):
        return 'error'

    def render_POST(self, request):
        res = {"code": 2}
        try:
            jsondata = request.content.getvalue()
            data = json.loads(jsondata)
            phone = data.get('phone', "")
            message = data.get('message', "")
            if phone and message:
                code = send_sms(str(phone), message)
                res["code"] = code
            else:
                code = 3
        except Exception as e:
            res["code"] = 3

        return json.dumps(res)


root = Resource()
root.putChild("smsapi", SmsAPI())
factory = Site(root)
reactor.listenTCP(30059, factory)
reactor.run()
