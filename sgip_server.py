#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SGIP server for receiving SGIP message from SMG
文档 3.7.2.6
"""

import logging
import logging.handlers
from binascii import *
from datetime import datetime
from optparse import OptionParser

import eventlet

from sgip import *
from sgip_client import *

# config logger
log_name = 'sgip_server'
logger = logging.getLogger(log_name)
logger.setLevel(logging.INFO)
lh = logging.handlers.TimedRotatingFileHandler(
    log_name + '.log', when='midnight')
lh.setLevel(logging.INFO)
lf = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
lh.setFormatter(lf)
logger.addHandler(lh)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s : %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


# SGIP Message Processor
class SGIPProcessor(object):
    def __init__(self, ssd):
        self.ssock = ssd

    # receive data by specified size
    def __recv(self, size):
        data = self.ssock.recv(size)
        # logger.info('recv data: %s', hexlify(data))
        return data

    # send data
    def __send(self, data):
        fd = self.ssock.makefile('w')
        fd.write(data)
        fd.flush()
        fd.close()

    # read SGIP message header
    def __read_msg_header(self):
        logger.info('read msg header')
        raw_data = self.__recv(SGIPHeader.size())
        logger.debug('# header raw data: %s', hexlify(raw_data))
        if raw_data == '':
            return None
        header = SGIPHeader()
        header.unpack(raw_data)
        # logger.info('# msg len: %d', header.MessageLength)
        # logger.info('# command id: %d', header.CommandID)
        # logger.info('# sequence number: {0} {1} {2}'.format(
        #    header.SequenceNumber[0], header.SequenceNumber[
        #        1], header.SequenceNumber[2]))
        return header

    # process SGIP message
    def process(self):
        logger.info('process SGIP message')
        while True:
            # read message header
            header = self.__read_msg_header()
            if header is None:
                logger.info('No header received, close the socket')
                break
            # report userrpt trace_resp
            if header.CommandID == SGIPBind.ID:
                self.__handle_bind_msg(header)
            elif header.CommandID == SGIPDeliver.ID:
                self.__handle_deliver_msg(header)
            elif header.CommandID == SGIPReport.ID:
                self.__handle_report_msg(header)
            elif header.CommandID == SGIPUnbind.ID:
                self.__send_sgip_unbind_resp(header)
                break
        self.ssock.close()

    # send SGIP message
    def __send_sgip_msg(self, sgip_msg, header):
        if sgip_msg is None or header is None:
            return
        seq_num = header.SequenceNumber[:]
        sgip_msg.header = SGIPHeader(SGIPHeader.size() + sgip_msg.size(),
                                     sgip_msg.ID, seq_num)
        raw_data = sgip_msg.pack()
        logger.debug('# send raw data: %s', hexlify(raw_data))
        self.__send(raw_data)

    def __send_sgip_unbind_resp(self, header):
        logger.info('send unbind resp')
        unbind_resp_msg = SGIPUnbindResp()
        self.__send_sgip_msg(unbind_resp_msg, header)

    def __handle_report_msg(self, header):
        """
        对短信回执的处理(report指令)
        """
        logger.info('handler report msg')
        report_msg_len = header.MessageLength - header.size()
        raw_data = self.__recv(report_msg_len)
        logger.debug('# report raw data: %s', hexlify(raw_data))
        report_msg = SGIPReport()
        report_msg.unpackBody(raw_data)
        logger.info('report state: %s', report_msg.State)
        self.__send_sgip_msg(SGIPReportResp(), header)

    def __handle_bind_msg(self, header):
        logger.info('handle bind msg')
        # continue to receive bind msg body
        raw_data = self.__recv(SGIPBind.size())
        logger.debug('# bind raw data: %s', hexlify(raw_data))
        bind_msg = SGIPBind()
        bind_msg.unpackBody(raw_data)
        # logger.info('login type: %d', bind_msg.LoginType)
        logger.debug('login name: %s', bind_msg.LoginName)
        # logger.info('login pwd: %s', bind_msg.LoginPassword)

        # send Bind Resp
        logger.debug('send bind resp')
        bind_resp_msg = SGIPBindResp()
        self.__send_sgip_msg(bind_resp_msg, header)

    def __handle_deliver_msg(self, header):
        """
        上行短信类型的处理
        """
        logger.info('handle deliver msg')
        # continue to receive deliver msg body
        deliver_msg_len = header.MessageLength - header.size()
        raw_data = self.__recv(deliver_msg_len)
        logger.debug('# deliver raw data: %s', hexlify(raw_data))
        deliver_msg = SGIPDeliver()
        deliver_msg.contentLength = deliver_msg_len - SGIPDeliver.size()
        deliver_msg.unpackBody(raw_data)
        # send Deliver Resp
        logger.debug('send deliver resp')
        deliver_resp_msg = SGIPDeliverResp()
        self.__send_sgip_msg(deliver_resp_msg, header)
        # process Deliver Msg content
        self._process_deliver_content(deliver_msg)

    # do actual work according to the content of deliver message
    def _process_deliver_content(self, deliver_msg):
        logger.debug('process deliver content')
        if deliver_msg.UserNumber.find('86') == 0:
            userNumber = deliver_msg.UserNumber[2:]
        else:
            userNumber = deliver_msg.UserNumber

        msg_content = deliver_msg.MessageContent
        logger.info('user number: %s msg content: %s' %
                    (userNumber, msg_content))
        status = ''


def handle_msg(ssd):
    logger.info(
        'client connected, start to handle request, .......................')
    processor = SGIPProcessor(ssd)
    processor.process()
    logger.info("close connection, ******************************")


def main():
    parser = OptionParser()
    parser.add_option(
        "-p", "--port", dest="port", help="input port to listen", default=8801)
    (options, args) = parser.parse_args()

    logger.info("server is listening on port %d" % options.port)
    server = eventlet.listen(('0.0.0.0', options.port))
    pool = eventlet.GreenPool(100000)
    while True:
        try:
            new_sock, address = server.accept()
            logger.info("accepted %s %s", address, new_sock)
            pool.spawn_n(handle_msg, new_sock)
        except (SystemExit, KeyboardInterrupt):
            logger.info('server caught exception')
            break
    return


if __name__ == "__main__":
    main()
