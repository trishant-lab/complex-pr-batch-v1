from enum import Enum, IntEnum


class SGMailStatus(IntEnum, Enum):
    processing = 0
    delivered = 1
    opened = 2
    not_delivered = -1
    bounced = -2


class MessageProvider(IntEnum, Enum):
    sendgrid = 1


class CommunicationMedium(IntEnum, Enum):
    email = 1
    sms = 2
