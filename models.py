from pydantic import BaseModel
from typing import List, Optional, Any

class BrokerMessageProperties:
    payload_format_indicator: int
    message_expiry_interval: int
    response_topic: str
    correlation_data: str
    user_properties: dict[Any]
    content_type: str 


class BrokerPublishMessage(BaseModel):
    payload_encoding: str
    topic: str
    qos: int
    payload: str
    retain: bool

    class Config:
        arbitrary_types_allowed = True
        
class MQTTBrokerWebhook(BaseModel):
    """
    HTTP POST Request from the broker for each new message.
    """
    clientId: str
    topic: str
    data: str


class MQTTDataPacket(BaseModel):
    """ Format of the data string for all MQTT transmissions.

    Values: 
        - `enc` - "br"
        - `msg` - Brotli compressed, base64 encoded data.
    """
    enc: str
    msg: str


class DecompressedDataMessage(BaseModel):
    """Format of MQTTDataPacket.msg when decompressed. Should be used to compress to this format when sending to the device.
    
    `type`: type of data
        - "reading" - MQTTReadingDataItem - Ingress
        - "update" - ControlUnitSetupRequestMessage - Ingress, or ControlUnitSetupResponsePacket - Egress
        - "rules" - ModuleRuleUpdate - Egress
        - "command" - Direct Command
        - "setup" - ControlUnitSetupRequestMessage - Ingress

    `data` - JSON formatted string of data type. 
    """
    type: str
    data: str


class MQTTStateChange(BaseModel):
    """
    State changes of module switch.
    """
    state: bool
    timestamp: int


class MQTTReadingDataItem(BaseModel):
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
    state_changes: List[MQTTStateChange]


class MQTTReadingMessage(BaseModel):
    """
    MQTT Reading Message. DecompressedDataMessage.type = "reading"
    """
    period_start: int
    period_end: int
    data: List[MQTTReadingDataItem]


class ControlUnitMQTTInfo(BaseModel):
    """
    Data used to generate a new JWT access token with ACL for the unit.
    """
    ingress_topics: List[str]
    egress_topics: List[str]
    broker_address: str
    port: str


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
    rules: List[ModuleRuleUpdate]



class ControlUnitSetupRequestMessage(BaseModel):
    """Packet sent by the control unit to the MQTT topic: /setup. 
    
    DecompressedDataMessage.type = "setup"

    - setup_token - JWT used to connect to /setup channel:
        - User ID -> The ID of the user to assosciate the unit with.
        - ACL -> Publish: "/setup", Subscribe: "/egress/{unit_id}"


    - module_ids - List of module IDs to assosciate with this unit.
    """
    setup_token: str
    module_ids: List[str]

"""
Packet sent by the backend to the MQTT topic: /ingress/{unit_id}
"""
class ControlUnitSetupResponsePacket(BaseModel):
    rules: List[ModuleRuleUpdate]

class MQTTJWTACL(BaseModel):
    pub: List[str]
    sub: List[str]
    all: List[str]

class UnitJWToken(BaseModel):
    username: str
    exp: int
    acl: MQTTJWTACL


"""
Database Table Schema
"""

class AllocationsTable(BaseModel):
    id: str
    module_id: Optional[str]
    rule_id: Optional[str]

class BrokersTable(BaseModel):
    address: str
    id: str
    port: Optional[int]

class ControlUnitsTable(BaseModel):
    address: Optional[str]
    created_at: str
    id: str

class ModuleStateChangesTable(BaseModel):
    id: str
    module: Optional[str]
    state: Optional[bool]
    timestamp: str

class ModulesTable(BaseModel):
    created_at: str
    id: str
    unit_id: Optional[str]

class ReadingsTable(BaseModel):
    id: str
    iqr_apparent_power: Optional[float]
    iqr_power_factor: Optional[float]
    kurtosis_apparent_power: Optional[float]
    kurtosis_power_factor: Optional[float]
    kwh_usage: Optional[float]
    max_apparent_power: Optional[float]
    max_power_factor: Optional[float]
    mean_apparent_power: Optional[float]
    mean_frequency: Optional[float]
    mean_power_factor: Optional[float]
    mean_voltage: Optional[float]
    module_id: Optional[str]
    period_end_time: Optional[str]
    period_start_time: str
    sample_count: Optional[int]

class RulesTable(BaseModel):
    command: Optional[str]
    created_at: str
    expression: Optional[str]
    id: str
    priority: Optional[int]

class TopicAllocationsTable(BaseModel):
    broker_id: Optional[str]
    created_at: str
    id: str
    ingress: Optional[bool]
    topic_id: Optional[str]
    unit_id: Optional[str]

class TopicsTable(BaseModel):
    id: str
    topic: str
