#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SGIP Message Send

orangleliu@2015-04-29
"""

from datetime import datetime
import eventlet
from eventlet.green import socket
from sgip import *
from binascii import *
import logging
import logging.handlers
from optparse import OptionParser
import base64
import threading

from conf import NODE_NUM, SP_PARAM

# config logger
log_name = 'sgip_client'
logger = logging.getLogger(log_name)
logger.setLevel(logging.DEBUG)
lh = logging.handlers.TimedRotatingFileHandler(
    log_name + '.log', when='midnight')
lh.setLevel(logging.INFO)
lf = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
lh.setFormatter(lf)
logger.addHandler(lh)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s : %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

count = 0
lock = threading.Lock()


def get_count():
    lock.acquire()
    try:
        global count
        count = count + 1
        if count > 99999:
            count = 0
    finally:
        lock.release()
    return count


class SMSClient(object):
    def __init__(self, host, port, corp_id, username, pwd, sp_number):
        self._host = host
        self._port = port
        self._corp_id = corp_id
        self._username = username
        self._pwd = pwd
        self._sp_number = sp_number

    def _init_sgip_connection(self):
        self.__csock = socket.socket()
        ip = socket.gethostbyname(self._host)
        self.__csock.connect((ip, self._port))
        logger.info('%s connected' % self._host)

    def _close_sgip_connection(self):
        if self.__csock != None:
            self.__csock.close()
        logger.info('connection to %s closed' % self._host)

    def gen_seq_number(self):
        seq_num1 = NODE_NUM
        today = datetime.today()
        seq_num2 = (((today.month * 100 + today.day) * 100 + today.hour) * 100
                    + today.minute) * 100 + today.second
        seq_num3 = today.microsecond
        seq_num3 = get_count()
        return [seq_num1, seq_num2, seq_num3]

    def send_data(self, data):
        logger.info('send data: %s', hexlify(data))
        fd = self.__csock.makefile('w')
        fd.write(data)
        fd.flush()
        fd.close()

    def recv_data(self, size):
        fd = self.__csock.makefile('r')
        data = fd.read(size)
        logger.info('recv raw data: %s', hexlify(data))
        """
        while len(data) < size:
            nleft = size - len(data)
            t_data = fd.read(nleft)
            data = data + t_data
        """
        fd.close()
        return data

    def _bind(self):
        logger.info('do bind')
        # send bind msg
        bindMsg = SGIPBind(1, self._username, self._pwd)
        header = SGIPHeader(SGIPHeader.size() + bindMsg.size(), SGIPBind.ID,
                            self.gen_seq_number())
        bindMsg.header = header
        raw_data = bindMsg.pack()
        self.send_data(raw_data)
        # recv bind resp msg
        resp_header_data = self.recv_data(SGIPHeader.size())
        logger.info('header raw data: %s', hexlify(resp_header_data))
        if resp_header_data == '':
            return False
        respHeader = SGIPHeader()
        respHeader.unpack(resp_header_data)
        logger.info('resp command id: {0}'.format(respHeader.CommandID))
        resp_body_data = self.recv_data(SGIPBindResp.size())
        if resp_body_data == '':
            return False
        bindRespMsg = SGIPBindResp()
        bindRespMsg.unpackBody(resp_body_data)
        if respHeader.CommandID == SGIPBindResp.ID and bindRespMsg.Result == 0:
            return True
        else:
            return False

    def _unbind(self):
        logger.info('do unbind')
        unbindMsg = SGIPUnbind()
        header = SGIPHeader(SGIPHeader.size() + unbindMsg.size(),
                            SGIPUnbind.ID, self.gen_seq_number())
        unbindMsg.header = header
        raw_data = unbindMsg.pack()
        self.send_data(raw_data)

    def _submit(self, userNumber, message):
        logger.info('do submit')
        message = message.decode('utf-8').encode('gbk')
        # send submit msg
        submitMsg = SGIPSubmit(
            sp_number=self._sp_number,
            user_number=userNumber,
            corp_id=self._corp_id,
            msg_len=len(message),
            msg_content=message)
        header = SGIPHeader(SGIPHeader.size() + submitMsg.mySize(),
                            SGIPSubmit.ID, self.gen_seq_number())
        submitMsg.header = header
        raw_data = submitMsg.pack()
        self.send_data(raw_data)
        # recv submit msg
        resp_header_data = self.recv_data(SGIPHeader.size())
        if resp_header_data == '':
            logger.error('sms submit failed')
            return 1
        resp_body_data = self.recv_data(SGIPSubmitResp.size())
        if resp_body_data == '':
            logger.error('sms submit failed')
            return 1
        submitRespMsg = SGIPSubmitResp()
        submitRespMsg.unpackBody(resp_body_data)
        respheader = SGIPHeader()
        respheader.unpack(resp_header_data)
        if respheader.CommandID == SGIPSubmitResp.ID and submitRespMsg.Result == 0:
            logger.info('sms submitted ok')
            return 0
        else:
            return 1

    def send_sms(self, user_number, message):
        retFlag = 0
        try:
            self._init_sgip_connection()
            bindRet = self._bind()
            if bindRet:
                # submit msg
                self._submit(user_number, message)
            else:
                logger.error('bind failed')
                retFlag = 1
            self._unbind()
        except socket.error as (errno, strerror):
            logger.error("socket error({0}): {1}".format(errno, strerror))
            retFlag = 2
        finally:
            self._close_sgip_connection()
        return retFlag

    instance = None

    @classmethod
    def get_instance(cls):
        if cls.instance == None:
            cls.instance = SMSClient(**SP_PARAM)
        return cls.instance


def send_sms(phone_number, message):
    sc = SMSClient.get_instance()
    logger.info('message to send:%s ----->%s' % (phone_number, message))
    return sc.send_sms(phone_number, message)


def main():
    parser = OptionParser()
    parser.add_option(
        "-n", "--number", dest="phone_number", help="phone number to send")
    parser.add_option(
        "-m", "--message", dest="message", help="message content")
    parser.add_option(
        "-b", "--base64msg", dest="base64msg", help="base64 message content")
    (options, args) = parser.parse_args()
    if options.phone_number == None or (options.message == None and
                                        options.base64msg == None):
        logger.info('please input phone number or message')
        return 3
    phone_number = options.phone_number
    msgContent = options.message
    if options.base64msg != None:
        msgContent = base64.b64decode(options.base64msg)
    return send_sms(phone_number, msgContent)


if __name__ == "__main__":
    main()
