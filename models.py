from pydantic import BaseModel
from typing import List, Union, Optional



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
    apparent_power: List[float]  # [mean, max, iqr, kurtosis]
    power_factor: List[float]  # [mean, max, iqr, kurtosis]
    kwh_usage: float
    state_changes: Optional[List[StateChangeItem]]  # Allow an empty list

class ReadingMessage(BaseModel):
    """
    MQTT Reading Message. DecompressedDataMessage.type = "reading"
    """
    period_start: int
    period_end: int
    readings: List[ReadingDataItem]

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

    Action:
        - 0 - "append" - Appends the command to the current commands.
        - 1 - "replace" - Replaces the current commands with the provided one(s).
        - 2 -  "exec" - Directly run the command on the module.
        - 3 - "execif" - Executes the command if the expression evaluates true.
    """
    module_id: str
    action: int
    rules: List[DeviceRule]

class UnitRuleUpdate(BaseModel):
    """
    Per unit rules to be sent to the device.

    Action:
        - 0 - "append" - Appends the command to the current commands.
        - 1 - "replace" - Replaces the current commands with the provided one(s).
        - 2 -  "exec" - Directly run the command on the module.
        - 3 - "execif" - Executes the command if the expression evaluates true.
    """
    action: int
    rules: List[DeviceRule]

class RuleUpdateMessage(BaseModel):
    """
    Packet sent to the control module to configure rules.

    """
    unit_rules: UnitRuleUpdate
    module_rules: List[ModuleRuleUpdate]

class ScheduleItem(BaseModel):
    """Schedule item."""
    module_id: str
    state: bool
    timestamp: int
    period: int
    count: int

class ScheduleUpdateMessage(BaseModel):
    """Packet sent to the control module to configure schedule.
    
    Action:
    - 0 - "append" - Appends the command to the current schedule.
    - 1 - "replace" - Replaces the current schedule with the provided one(s).
    """
    action: int
    schedule: List[ScheduleItem]


class ControlUnitParameters(BaseModel):
    """
    Parameters relating to the operation of the control unit.
    """
    sample_period: int # Number of seconds between sampling a module.
    serialization_period: int # Number of seconds between sending readings to the server.

# Egress Packets

class EgressMessage(BaseModel):
    """ Format of all egress data types.


        `type` type of data contained:
        - 0 - rules
        - 1 - schedule
        - 2 - parameters

        `data` - contained data.

    """

    type: int
    data: Union[RuleUpdateMessage, ScheduleUpdateMessage, ControlUnitParameters]

"""
EMQX Broker Communication
"""

class MQTTDataPacket(BaseModel):
    e: int
    m: str

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
    data: str

class ACL(BaseModel):
    """Format of the Access Control List for the EMQX broker."""
    pub: List[str]
    sub: List[str]
    all: List[str]


class ControlUnitJWTInfo(BaseModel):
    """
    Data used to generate a new JWT access token for the unit.
    """
    address: str
    port: int
    exp: int
    acl: ACL
