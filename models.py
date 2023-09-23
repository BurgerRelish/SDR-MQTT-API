from pydantic import BaseModel
from typing import List, Union



"""
SDR MQTT Data Packets
"""

# Reading Packets

class StateChangeItem(BaseModel):
    """
    State changes of module switch.
    """
    state: bool
    timestamp: int

class ReadingDataItem(BaseModel):
    """
    Data of module readings.

    Note the order of the apparent_power and power_factor lists: [mean, max, iqr, kurtosis]
    """
    module_id: str
    sample_count: int
    mean_voltage: float
    mean_frequency: float
    apparent_power: List[float] # [mean, max, iqr, kurtosis]
    power_factor: List[float] # [mean, max, iqr, kurtosis]
    kwh_usage: float
    state_changes: List[StateChangeItem]

class ReadingMessage(BaseModel):
    """
    MQTT Reading Message. DecompressedDataMessage.type = "reading"
    """
    period_start: int
    period_end: int
    data: List[ReadingDataItem]

class IngressMessage(BaseModel):
    """Format of MQTTDataPacket.msg when decompressed. Should be used to compress to this format when sending to the device.
    
    `type`: type of data
        - 0 - ReadingMessage - Ingress

    `data`:
        - ReadingMessage
    """
    type: int
    data: ReadingMessage

# Rule Packets

class DeviceRule(BaseModel):
    """
    Rule content.
    """
    priority: int
    expression: str
    command: str

class ModuleRuleUpdate(BaseModel):
    """
    Per module rules to be sent to the device.
    """
    module_id: str
    action: str
    rules: List[DeviceRule]

class RuleUpdateMessage(BaseModel):
    """
    Packet sent to the control module to configure rules.

    Action:
        - "append" - Appends the command to the current commands.
        - "replace" - Replaces the current commands with the provided one(s).
        - "exec" - Directly run the command on the module.
        - "execif" - Executes the command if the expression evaluates true.
    """
    action: str
    unit_rules: List[DeviceRule]
    module_rules: List[ModuleRuleUpdate]

# Egress Packets

class EgressMessage(BaseModel):
    """ Format of all egress data types.


        `type` type of data contained:
        - 0 - rules

        `data` - contained data.

    """

    type: int
    data: RuleUpdateMessage


# Common Packets

class MQTTDataPacket(BaseModel):
    """ Format of the transmission packet for ALL MQTT messages.

    Values: 
        - `e` - Message Compression type
            - 0 - Brotli Compression
        - `m` - base64 encoded, compressed message data.
    """
    e: int
    m: str

"""
EMQX Broker Communication
"""

class BrokerPublishMessage(BaseModel):
    """Format of HTTP POST request to publish message to topic."""
    payload_encoding: str
    topic: str
    qos: int
    payload: str
    retain: bool

    class Config:
        arbitrary_types_allowed = True
        
class BrokerWebhook(BaseModel):
    """
    HTTP POST webhook from the broker for each new message received.
    """
    clientId: str
    topic: str
    data: MQTTDataPacket

class ACL(BaseModel):
    """Format of the Access Control List for the EMQX broker."""
    pub: List[str]
    sub: List[str]
    all: List[str]


class ControlUnitJWTInfo(BaseModel):
    """
    Data used to generate a new JWT access token for the unit.
    """
    broker_address: str
    port: int
    exp: int
    acl: ACL
