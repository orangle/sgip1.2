#! /usr/bin/env python
"""
SGIP message defininitions and operations

orangleliu@2015-04-29 m
"""
import logging
from struct import *

logger = logging.getLogger(__name__)


# Error Code Definition
class ErrorCode(object):
    OK = 0
    ILLEGAL_LOGIN = 1
    REPEATED_LOGIN = 2
    CONNECTION_TOO_MUCH = 3
    WRONG_LOGIN_TYPE = 4
    WRONG_PARA_FORMAT = 5
    INVALID_PHONE_NUMBER = 6
    WRONG_MSG_ID = 7
    WRONG_MSG_LENGTH = 8
    INVALID_SEQ_NUMBER = 9
    ILLEGAL_GNS_OPERATION = 10
    NODE_BUSY = 11
    HOST_UNREACHABLE = 21
    ROUTE_ERROR = 22
    NO_ROUTE = 23
    INVALID_CHARGE_NUMBER = 24
    USER_UNREACHABLE = 25
    LOW_PHONE_MEMORY = 26
    SMS_UNSUPPORTED = 27
    ERROR_RECV_SMS = 28
    UNKNOWN_USER = 29
    FUNCTION_UNSUPPORTED = 30
    ILLEGAL_DEVICE = 31
    SYS_FAILED = 32
    SMS_CENTER_QUEUE_FULL = 33


# Ancestor of all Messages
class BaseMSG(object):
    fmt = ''  # struct format
    struct_tool = None

    def __init__(self):
        self.struct_tool = Struct(self.fmt)

    # unpack message from raw data
    def unpack(self, raw_msg):
        pass

    # get message size
    @classmethod
    def size(cls):
        return calcsize(cls.fmt)


# define SGIP Header
class SGIPHeader(BaseMSG):
    fmt = '!II3I'  # struct format

    def __init__(self, msg_len=20, command_id=0, seq_num=[0, 0, 0]):
        super(SGIPHeader, self).__init__()
        self.MessageLength = msg_len
        self.CommandID = command_id
        self.SequenceNumber = seq_num

    # unpack the message header from raw message data
    def unpack(self, raw_msg):
        header_tuple = self.struct_tool.unpack(raw_msg)
        self.MessageLength = header_tuple[0]
        self.CommandID = header_tuple[1]
        self.SequenceNumber = list(header_tuple[2:])


# define SGIP base message
class BaseSGIPMSG(BaseMSG):
    def __init__(self):
        super(BaseSGIPMSG, self).__init__()
        self._header = SGIPHeader()

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, sgip_header):
        self._header = sgip_header

    # pack the header and body into raw message data
    def pack(self):
        self_fmt = self.fmt[1:]
        msg_fmt = self.header.fmt + self_fmt
        logger.debug('SGIP MSG format: ', msg_fmt)
        raw_msg = self._pack(msg_fmt)
        return raw_msg

    # pack the message into raw data, this method should be implemented by subclasses
    def _pack(self, msg_fmt):
        return ''

    # unpack the message body from raw message data
    def unpackBody(self, raw_msg):
        pass


# define Base SGIP Resp Message
class BaseSGIPResp(BaseSGIPMSG):
    fmt = '!B8s'

    def __init__(self, result=0, reserve=''):
        super(BaseSGIPResp, self).__init__()
        self.Result = result
        self.Reserve = reserve

    def unpackBody(self, raw_msg):
        body_tuple = self.struct_tool.unpack(raw_msg)
        self.Result = body_tuple[0]
        self.Reserve = body_tuple[1]

    def _pack(self, msg_fmt):
        raw_msg = pack(
            msg_fmt, self.header.MessageLength, self.header.CommandID,
            self.header.SequenceNumber[0], self.header.SequenceNumber[1],
            self.header.SequenceNumber[2], self.Result, self.Reserve)
        return raw_msg


# SGIP Bind Message
class SGIPBind(BaseSGIPMSG):
    ID = 0x1
    fmt = '!B16s16s8s'

    def __init__(self, login_type=1, login_name='', login_pwd='', reserve=''):
        super(SGIPBind, self).__init__()
        self.LoginType = login_type
        self.LoginName = login_name
        self.LoginPassword = login_pwd
        self.Reserve = reserve

    def unpackBody(self, raw_msg):
        body_tuple = self.struct_tool.unpack(raw_msg)
        self.LoginType = body_tuple[0]
        self.LoginName = body_tuple[1]
        self.LoginPassword = body_tuple[2]
        self.Reserve = body_tuple[3]

    def _pack(self, msg_fmt):
        raw_msg = pack(msg_fmt, self.header.MessageLength,
                       self.header.CommandID, self.header.SequenceNumber[0],
                       self.header.SequenceNumber[1],
                       self.header.SequenceNumber[2], self.LoginType,
                       self.LoginName, self.LoginPassword, self.Reserve)
        return raw_msg


# SGIP Bind Resp Message
class SGIPBindResp(BaseSGIPResp):
    ID = 0x80000001

    def __init__(self, result=0, reserve=''):
        super(SGIPBindResp, self).__init__(result, reserve)


# SGIP Unbind Message
class SGIPUnbind(BaseSGIPMSG):
    ID = 0x2

    def _pack(self, msg_fmt):
        raw_msg = pack(msg_fmt, self.header.MessageLength,
                       self.header.CommandID, self.header.SequenceNumber[0],
                       self.header.SequenceNumber[1],
                       self.header.SequenceNumber[2])
        return raw_msg


# SGIP Unbind Resp Message
class SGIPUnbindResp(BaseSGIPMSG):
    ID = 0x80000002

    def _pack(self, msg_fmt):
        raw_msg = pack(msg_fmt, self.header.MessageLength,
                       self.header.CommandID, self.header.SequenceNumber[0],
                       self.header.SequenceNumber[1],
                       self.header.SequenceNumber[2])
        return raw_msg


# SGIP Submit Message
class SGIPSubmit(BaseSGIPMSG):
    ID = 0x3
    fmt = '!21s21sB21s5s10sB6s6s3B16s16s5BI0s8s'  # it's only used for calculating real message content length, using myFmt to pack or unpack

    def __init__(self,
                 sp_number='',
                 charge_number='000000000000000000000',
                 user_count=1,
                 user_number='',
                 corp_id='',
                 service_type='',
                 fee_type=0,
                 fee_value='0',
                 given_value='0',
                 agent_flag=1,
                 morelateto_mt_flag=1,
                 priority=9,
                 expire_time='',
                 schedule_time='',
                 report_flag=0,
                 tp_pid=0,
                 tp_udhi=0,
                 msg_coding=15,
                 msg_type=0,
                 msg_len=0,
                 msg_content='',
                 reserve=''):
        super(SGIPSubmit, self).__init__()
        self.SPNumber = sp_number
        self.ChargeNumber = charge_number
        self.UserCount = user_count
        if user_number[0:2] != '86':
            user_number = '86' + user_number
        self.UserNumber = user_number
        self.CorpId = corp_id
        self.ServiceType = service_type
        self.FeeType = fee_type
        self.FeeValue = fee_value
        self.GivenValue = given_value
        self.AgentFlag = agent_flag
        self.MorelatetoMTFlag = morelateto_mt_flag
        self.Priority = priority
        self.ExpireTime = expire_time
        self.ScheduleTime = schedule_time
        self.ReportFlag = report_flag
        self.TP_pid = tp_pid
        self.TP_udhi = tp_udhi
        self.MessageCoding = msg_coding
        self.MessageType = msg_type
        self.MessageLength = msg_len
        self.MessageContent = msg_content
        self.Reserve = reserve

    @property
    def myFmt(self):
        self._myFmt = '!21s21sB21s5s10sB6s6s3B16s16s5BI{0}s8s'.format(
            self.MessageLength)
        return self._myFmt

    # my fmt size
    def mySize(self):
        return calcsize(self.myFmt)

    def unpackBody(self, raw_msg):
        body_tuple = unpack(self.myFmt, raw_msg)
        self.SPNumber = body_tuple[0]
        self.ChargeNumber = body_tuple[1]
        self.UserCount = body_tuple[2]
        self.UserNumber = body_tuple[3]
        self.CorpId = body_tuple[4]
        self.ServiceType = body_tuple[5]
        self.FeeType = body_tuple[6]
        self.FeeValue = body_tuple[7]
        self.GivenValue = body_tuple[8]
        self.AgentFlag = body_tuple[9]
        self.MorelatetoMTFlag = body_tuple[10]
        self.Priority = body_tuple[11]
        self.ExpireTime = body_tuple[12]
        self.ScheduleTime = body_tuple[13]
        self.ReportFlag = body_tuple[14]
        self.TP_pid = body_tuple[15]
        self.TP_udhi = body_tuple[16]
        self.MessageCoding = body_tuple[17]
        self.MessageType = body_tuple[18]
        self.MessageLength = body_tuple[19]
        self.MessageContent = body_tuple[20]
        self.Reserve = body_tuple[21]

    # override
    def pack(self):
        self_fmt = self.myFmt[1:]
        msg_fmt = self.header.fmt + self_fmt
        raw_msg = self._pack(msg_fmt)
        return raw_msg

    def _pack(self, msg_fmt):
        raw_msg = pack(
            msg_fmt, self.header.MessageLength, self.header.CommandID,
            self.header.SequenceNumber[0], self.header.SequenceNumber[1],
            self.header.SequenceNumber[2], self.SPNumber, self.ChargeNumber,
            self.UserCount, self.UserNumber, self.CorpId, self.ServiceType,
            self.FeeType, self.FeeValue, self.GivenValue, self.AgentFlag,
            self.MorelatetoMTFlag, self.Priority, self.ExpireTime,
            self.ScheduleTime, self.ReportFlag, self.TP_pid, self.TP_udhi,
            self.MessageCoding, self.MessageType, self.MessageLength,
            self.MessageContent, self.Reserve)
        return raw_msg


# SGIP Submit Resp
class SGIPSubmitResp(BaseSGIPResp):
    ID = 0x80000003

    def __init__(self, result=0, reserve=''):
        super(SGIPSubmitResp, self).__init__(result, reserve)


# SGIP Deliver Message
class SGIPDeliver(BaseSGIPMSG):
    ID = 0x4
    fmt = '!21s21s3BI0s8s'  # it's only used for calculating real message content length, using myFmt to pack or unpack

    def __init__(self,
                 user_number='',
                 sp_number='',
                 tp_pid=0,
                 tp_udhi=0,
                 msg_code=0,
                 msg_len=0,
                 msg_content='',
                 reserve=''):
        super(SGIPDeliver, self).__init__()
        self.UserNumber = user_number
        self.SPNumber = sp_number
        self.TP_pid = tp_pid
        self.TP_udhi = tp_udhi
        self.MessageCoding = msg_code
        self.MessageLength = msg_len
        self.MessageContent = msg_content
        self.Reserve = reserve
        self._contentLength = 0

    @property
    def myFmt(self):
        self._myFmt = '!21s21s3BI{0}s8s'.format(self.contentLength)
        return self._myFmt

    # my fmt size
    def mySize(self):
        return calcsize(self.myFmt)

    def unpackBody(self, raw_msg):
        body_tuple = unpack(self.myFmt, raw_msg)
        self.UserNumber = body_tuple[0]
        self.SPNumber = body_tuple[1]
        self.TP_pid = body_tuple[2]
        self.TP_udhi = body_tuple[3]
        self.MessageCoding = body_tuple[4]
        self.MessageLength = body_tuple[5]
        self.MessageContent = body_tuple[6]
        self.Reserve = body_tuple[7]

    @property
    def contentLength(self):
        return self._contentLength

    @contentLength.setter
    def contentLength(self, len):
        self._contentLength = len

    # override
    def pack(self):
        self_fmt = self.myFmt[1:]
        msg_fmt = self.header.fmt + self_fmt
        raw_msg = self._pack(msg_fmt)
        return raw_msg

    def _pack(self, msg_fmt):
        raw_msg = pack(
            msg_fmt, self.header.MessageLength, self.header.CommandID,
            self.header.SequenceNumber[0], self.header.SequenceNumber[1],
            self.header.SequenceNumber[2], self.UserNumber, self.SPNumber,
            self.TP_pid, self.TP_udhi, self.MessageCoding, self.MessageLength,
            self.MessageContent, self.Reserve)
        return raw_msg


# SGIP Deliver Resp Message
class SGIPDeliverResp(BaseSGIPResp):
    ID = 0x80000004

    def __init__(self, result=0, reserve=''):
        super(SGIPDeliverResp, self).__init__(result, reserve)


# SGIP Report Message
class SGIPReport(BaseSGIPMSG):
    ID = 0x5
    fmt = '!3IB21s2B8s'

    def __init__(self,
                 submit_seq_num=[0, 0, 0],
                 report_type=1,
                 user_number='',
                 state=0,
                 error_code=0,
                 reserve=''):
        super(SGIPReport, self).__init__()
        self.SubmitSequenceNumber = submit_seq_num
        self.ReportType = report_type
        self.UserNumber = user_number
        self.State = state
        self.ErrorCode = error_code
        self.Reserve = reserve

    def unpackBody(self, raw_msg):
        body_tuple = self.struct_tool.unpack(raw_msg)
        self.SubmitSequenceNumber = list(body_tuple[0:3])
        self.ReportType = body_tuple[3]
        self.UserNumber = body_tuple[4]
        self.State = body_tuple[5]
        self.ErrorCode = body_tuple[6]
        self.Reserve = body_tuple[7]

    def _pack(self, msg_fmt):
        raw_msg = pack(
            msg_fmt, self.header.MessageLength, self.header.CommandID,
            self.header.SequenceNumber[0], self.header.SequenceNumber[1],
            self.header.SequenceNumber[2], self.SubmitSequenceNumber[0],
            self.SubmitSequenceNumber[1], self.SubmitSequenceNumber[2],
            self.ReportType, self.UserNumber, self.State, self.ErrorCode,
            self.Reserve)
        return raw_msg


# SGIP Report Resp Message
class SGIPReportResp(BaseSGIPResp):
    ID = 0x80000005

    def __init__(self, result=0, reserve=''):
        super(SGIPReportResp, self).__init__(result, reserve)


## for test
if __name__ == "__main__":
    header = SGIPHeader()
    raw_msg = pack('!II3I', 30, 1, 2, 1, 2)
    header.unpack(raw_msg)

    print 'Header: ', header.MessageLength, ' ', header.CommandID, ' ', header.SequenceNumber
    print 'Header size: ', SGIPHeader.size()
    print 'Base Msg size: ', BaseMSG.size()

    bind = SGIPBind()
    bind.header = header
    print 'BIND Msg size: ', SGIPBind.size(), ' | ', bind.size()
    raw_msg = bind.pack()
    print 'Bind Raw Msg: ', raw_msg
    print 'Bind Msg ID: ', bind.ID

    raw_msg = pack('!B16s16s8s', 2, 'starkingwx', 'abc', 'blank')
    bind.unpackBody(raw_msg)
    print "Bind body: ", bind.LoginType, ' ', bind.LoginName, ' ', bind.LoginPassword, ' ', bind.Reserve
