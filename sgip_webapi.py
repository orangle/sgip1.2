#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SGIP Server, Http server, client->server->sgip(联通)
"""
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import urllib
import httplib
try:
    import json
except:
    import simplejson as json

HOST = '127.0.0.1'
PORT = 30059


def send_sms(mobile, content):
    body = {"phone": mobile, "message": content}
    jsonbody = json.dumps(body)
    headers = {
        "User-Agent": "SMS-Sender/1.0",
        'Content-Length': '%d' % len(jsonbody),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        http_conn = httplib.HTTPConnection(host=HOST, port=PORT)
        http_conn.request(
            method='POST', url='/smsapi', body=jsonbody, headers=headers)
        http_response = http_conn.getresponse()
        code = http_response.read()
        try:
            code = json.loads(code)['code']
            return code
        except:
            return 3
    except Exception, e:
        print e
        return 3
    finally:
        try:
            http_conn.close()
        except:
            pass


if __name__ == '__main__':
    print send_sms('15010283629', u'您的手机验证码是：472380')
