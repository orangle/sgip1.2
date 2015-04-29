#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
 SGIP server for receiving SGIP message from SMG
"""
from optparse import OptionParser
import eventlet
from sgip import *
from binascii import *
from sgip_client import *
import logging
import logging.handlers
from datetime import datetime


# config logger
log_name = 'sgip_server'
logger = logging.getLogger(log_name)
logger.setLevel(logging.DEBUG)
lh = logging.handlers.TimedRotatingFileHandler(log_name + '.log', when = 'midnight')
lh.setLevel(logging.INFO)
lf = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
lh.setFormatter(lf)
logger.addHandler(lh)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

# SGIP Message Processor
class SGIPProcessor(object):
    def __init__(self, ssd):
        self.ssock = ssd

    # receive data by specified size
    def __recv(self, size):
        logger.info('...receiving raw data...')
        data = self.ssock.recv(size)
        logger.info('recv data: %s', hexlify(data))
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
        logger.info('# header raw data: %s', hexlify(raw_data))
        if raw_data == '':
            return None
        header = SGIPHeader()
        header.unpack(raw_data)
        logger.info('# msg len: %d', header.MessageLength)
        logger.info('# command id: %d', header.CommandID)
        logger.info('# sequence number: {0} {1} {2}'.format(header.SequenceNumber[0], header.SequenceNumber[1], header.SequenceNumber[2]))
        return header

    # process SGIP message
    def process(self):
        logger.info('process SGIP message')
        while True:
            # read message header
            header = self.__read_msg_header()
            if header == None:
                logger.info('No header received, close the socket')
                break

            if header.CommandID == SGIPBind.ID:
                self.__handle_bind_msg(header)
            elif header.CommandID == SGIPDeliver.ID:
                self.__handle_deliver_msg(header)
            elif header.CommandID == SGIPUnbind.ID:
                self.__send_sgip_unbind_resp(header)
                break

        self.ssock.close()

    # send SGIP message
    def __send_sgip_msg(self, sgip_msg, header):
        logger.info('send sgip msg')
        if sgip_msg == None or header == None:
            return
        seq_num = header.SequenceNumber[:]
        msgHeader = SGIPHeader(SGIPHeader.size() + sgip_msg.size(), sgip_msg.ID, seq_num)
        sgip_msg.header = msgHeader
        raw_data = sgip_msg.pack()
        logger.info('# send raw data: %s', hexlify(raw_data))
        self.__send(raw_data)

    def __send_sgip_unbind_resp(self, header):
        logger.info('send unbind resp')
        unbindRespMsg = SGIPUnbindResp()
        self.__send_sgip_msg(unbindRespMsg, header)

    def __handle_bind_msg(self, header):
        logger.info('handle bind msg')
        # continue to receive bind msg body
        raw_data = self.__recv(SGIPBind.size())
        logger.info('# bind raw data: %s', hexlify(raw_data))
        bindMsg = SGIPBind()
        bindMsg.unpackBody(raw_data)
       	logger.info('login type: %d', bindMsg.LoginType)
        logger.info('login name: %s', bindMsg.LoginName)
        logger.info('login pwd: %s', bindMsg.LoginPassword)

	# send Bind Resp
        logger.info('send bind resp')
        bindRespMsg = SGIPBindResp()
        self.__send_sgip_msg(bindRespMsg, header)

    def __handle_deliver_msg(self, header):
        logger.info('handle deliver msg')
        # continue to receive deliver msg body
        deliver_msg_len = header.MessageLength - header.size()
        logger.info(' deliver msg len: %d', deliver_msg_len)
        raw_data = self.__recv(deliver_msg_len)
        logger.info('# deliver raw data: %s', hexlify(raw_data))
        deliverMsg = SGIPDeliver()
        deliverMsg.contentLength = deliver_msg_len - SGIPDeliver.size()
        logger.info('msg content len: %d - SGIPDeliver origin size: %d' % (deliverMsg.contentLength, SGIPDeliver.size()))
        deliverMsg.unpackBody(raw_data)
        # send Deliver Resp
        logger.info('send deliver resp')
        deliverRespMsg = SGIPDeliverResp()
        self.__send_sgip_msg(deliverRespMsg, header)
        # process Deliver Msg content
        self._process_deliver_content(deliverMsg)

    # do actual work according to the content of deliver message
    def _process_deliver_content(self, deliverMsg):
        logger.info('process deliver content')
        if deliverMsg.UserNumber.find('86') == 0:
            userNumber = deliverMsg.UserNumber[2:]
        else:
            userNumber = deliverMsg.UserNumber
        msg_content = deliverMsg.MessageContent.upper()
        logger.info('user number: %s msg content: %s' % (userNumber, msg_content))
        status = ''
        if 'DZFY' == msg_content:
            # update the business status as opened
            status = 'opened'
        elif 'TDFY' == msg_content:
            # update the business status as unopened
            status = 'unopened'

    # update business status in database
    def _update_status(self, cursor, userNumber, status):
        # update database
        logger.info('updating business status in database - status: %s userNumber: %s' % (status, userNumber))


def handleMsg(ssd):
    logger.info('client connected, start to handle request, .......................')
    processor = SGIPProcessor(ssd)
    processor.process()
    logger.info("close connection, ******************************")

def main():
    parser = OptionParser()
    parser.add_option("-p", "--port", dest = "port", help = "input port to listen", default = 8801)
    (options, args) = parser.parse_args()

    logger.info("server is listening on port %d" % options.port)
    server = eventlet.listen(('0.0.0.0', options.port))
    pool = eventlet.GreenPool(100000)
    while True:
        try:
            new_sock, address = server.accept()
            logger.info("accepted %s", address)
	    pool.spawn_n(handleMsg, new_sock)
	    logger.info('illegal SMG addr: %s - close' % address[0])
	    new_sock.close()
        except (SystemExit, KeyboardInterrupt):
            logger.info('server caught exception')
            break;

    return

if __name__ == "__main__":
    main()
