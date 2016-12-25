# coding:utf-8
"""
sgip server test
"""

import eventlet
from eventlet.green import socket
from feiying import sgip
import unittest


class TestSGIPServer(unittest.TestCase):
    def setUp(self):
        self.msg_content = 'DZFY'
        self.user_number = '13813005100'
        self.socket = socket.socket()
        ip = '127.0.0.1'
        port = 8801
        self.socket.connect((ip, port))
        print 'server %s connected' % ip

    def test_Business(self):
        # send bind msg
        bindMsg = sgip.SGIPBind(2, 'star', 'test')
        header = sgip.SGIPHeader(sgip.SGIPHeader.size() + bindMsg.size(),
                                 sgip.SGIPBind.ID)
        bindMsg.header = header
        raw_data = bindMsg.pack()
        self.socket.sendall(raw_data)
        # recv bind resp msg
        resp_header_data = self.socket.recv(sgip.SGIPHeader.size())
        resp_body_data = self.socket.recv(sgip.SGIPBindResp.size())
        bindRespMsg = sgip.SGIPBindResp()
        bindRespMsg.unpackBody(resp_body_data)
        respHeader = sgip.SGIPHeader()
        respHeader.unpack(resp_header_data)
        self.assertEqual(respHeader.CommandID, sgip.SGIPBindResp.ID)
        self.assertEqual(bindRespMsg.Result, 0)
        # send deliver msg
        deliverMsg = sgip.SGIPDeliver(self.user_number, '10010', 0, 0, 0,
                                      len(self.msg_content), self.msg_content,
                                      '')
        deliverMsg.contentLength = len(self.msg_content)
        header = sgip.SGIPHeader(sgip.SGIPHeader.size() + deliverMsg.mySize(),
                                 sgip.SGIPDeliver.ID)
        deliverMsg.header = header
        raw_data = deliverMsg.pack()
        self.socket.sendall(raw_data)
        # recv deliver resp msg
        resp_header_data = self.socket.recv(sgip.SGIPHeader.size())
        resp_body_data = self.socket.recv(sgip.SGIPDeliverResp.size())
        deliverRespMsg = sgip.SGIPDeliverResp()
        deliverRespMsg.unpackBody(resp_body_data)
        respHeader = sgip.SGIPHeader()
        respHeader.unpack(resp_header_data)
        self.assertEqual(respHeader.CommandID, sgip.SGIPDeliverResp.ID)
        self.assertEqual(deliverRespMsg.Result, 0)
        # send unbind msg
        unbindMsg = sgip.SGIPUnbind()
        header = sgip.SGIPHeader(sgip.SGIPHeader.size() + unbindMsg.size(),
                                 sgip.SGIPUnbind.ID)
        unbindMsg.header = header
        raw_data = unbindMsg.pack()
        self.socket.sendall(raw_data)
        # recv unbind resp msg
        resp_header_data = self.socket.recv(sgip.SGIPHeader.size())
        resp_body_data = self.socket.recv(sgip.SGIPUnbindResp.size())
        respHeader = sgip.SGIPHeader()
        respHeader.unpack(resp_header_data)
        self.assertEqual(respHeader.CommandID, sgip.SGIPUnbindResp.ID)

    def tearDown(self):
        self.socket.close()


if __name__ == '__main__':
    unittest.main()
