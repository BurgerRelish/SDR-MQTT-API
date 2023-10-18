from fastapi import FastAPI, HTTPException, status, Response, Depends, Request
from pydantic import BaseModel
from starlette.background import BackgroundTask
from fastapi.routing import APIRoute
from starlette.types import Message
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client, create_client

import brotli, base64, datetime, json, time, logging, configparser, logging
import requests

from auth import JWTBearer, encode_jwt, BrokerJWTBearer, encode_broker_jwt

from models import (
    MQTTDataPacket,
    ACL,
    BrokerPublishMessage,
    ControlUnitJWTInfo,
    BrokerWebhook,
    EgressMessage,
    IngressMessage,
    ReadingDataItem,
    ReadingMessage,
    RuleUpdateMessage,
    DeviceRule,
    ModuleRuleUpdate,
    StateChangeItem,
    ScheduleUpdateMessage,
    ScheduleItem,
    ControlUnitParameters
)

logging.basicConfig(filename='info.log', level=logging.DEBUG)

app = FastAPI()

origins = ["*"]

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Config variables

supabase_url: str
supabase_service_key: str
emqx_broker_ip: str
emqx_broker_http_port: int
emqx_api_key: str
emqx_secret: str
api_hostname: str
api_port: str

supabase_client: Client
emqx_headers: str
emqx_broker_url: str

async def decompress_message_brotli(message: str) -> str:
    logging.info("Decompressing: " + message)
    return str(brotli.decompress(base64.b64decode(message)).decode('utf-8'))

async def compress_message(message: str) -> MQTTDataPacket:
    ret = str(base64.b64encode(brotli.compress(message.encode('utf-8'))).decode('UTF-8'))  # Encode the message with utf-8, compress it, then convert the bytes to base64, and return a string of it.
    return ret

async def publish_message(topic: str, message: EgressMessage):
    """Publish a message to the provided topic. Compresses and formats the message accordingly"""

    message_str = message.model_dump_json()
    payload = await compress_message(message_str)

    request_data = BrokerPublishMessage(
        payload_encoding="plain",
        topic = topic,
        payload = payload,
        qos=0,
        retain=False,
    )

    # Send message to broker with post request
    result = requests.post(emqx_broker_url, json = request_data.model_dump(), headers=emqx_headers)
    
    if (result.status_code == 200):
        return {"result" : "ok", "message" : "The message was delivered to at least one subscriber."}
    if (result.status_code == 202):
        return {"result" : "ok", "message" : "No matched subscribers."}
    if (result.status_code == 400):
        raise HTTPException(status_code=result.status_code, detail={"result" : "fail", "message" : "Message is invalid."})
    logging.log(1, "code: " + str(result.status_code))
    return {"result" : "fail", "message" : "Failed to deliver the message to subscriber(s)"}


async def get_acl(unit_id: str) -> ACL:
    """Get the assosciated Access Control List for the control unit."""

    # Fetch topic info for the unit.
    data = supabase_client.table("topic_allocations").select("unit_id, ingress, all, topics(topic)").eq("unit_id", unit_id).execute()

    if (not data):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Not provisioned.")
    print(data.data)

    # Arrange the topics into the ACL format
    all_topics = []
    pub_topics = []
    sub_topics = []

    for row in data.data:
        topic = row["topics"]["topic"]
        if row["all"]:
            all_topics.append(topic)
        if row["ingress"]:
            pub_topics.append(topic)
        else:
            sub_topics.append(topic)
                
    return ACL(pub=pub_topics, sub=sub_topics, all=all_topics)

@app.get("/mqtt/v1/auth", dependencies=[Depends(JWTBearer())])
async def create_unit_token(user_id: str, unit_id: str) -> str:
    """ Creates an MQTT access token for a control unit. Assosciates the unit with a user, and queries the database for assigned topics. Raises a 406 error if no topics are provisioned for t>
    """
    # Assign the unit to the user.
    supabase_client.table("control_units").update(
        {
            "user_id" : user_id,
        }
    ).eq("id", unit_id).execute()

    broker_info = supabase_client.table("control_units").select("id, brokers(address, port)").eq("id", unit_id).single().execute()
    if (not broker_info):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Not provisioned.")
    print(broker_info)        
    ret = ControlUnitJWTInfo(
        address=broker_info.data["brokers"]["address"],
        port=broker_info.data["brokers"]["port"],
        exp=int(time.time() + 3600 * 24 * 365 * 10), # Expire after 10 years.
        acl=await get_acl(unit_id)
    )

    return encode_broker_jwt(ret.model_dump())


@app.post("/mqtt/v1/schedule", dependencies=[Depends(JWTBearer())])
async def send_schedule(unit_id: str, payload: ScheduleUpdateMessage):
    to_send = EgressMessage(
        type=1,
        data=payload
    )

    return await publish_message("/egress/" + unit_id, to_send)

@app.post("/mqtt/v1/parameters", dependencies=[Depends(JWTBearer())])
async def send_parameters(unit_id: str, payload: ControlUnitParameters):
    to_send = EgressMessage(
        type=2,
        data=payload
    )

    return await publish_message("/egress/" + unit_id, to_send)

@app.post("/mqtt/v1/rules", dependencies=[Depends(JWTBearer())])
async def send_rules(unit_id: str, payload: RuleUpdateMessage):
    to_send = EgressMessage(
        type=0,
        data=payload
    )

    return await publish_message("/egress/" + unit_id, to_send)

@app.get("/mqtt/v1/sync", dependencies=[Depends(JWTBearer())])
async def sync_commands(unit_id: str):
    """Sync the database and Control Unit commands."""
    message = RuleUpdateMessage(
        action = "replace",
        unit_rules=[],
        rules=[]
    )

    # Query for unit rules:
    unit_rule_request = supabase_client.table("unit_rule_allocations").select("unit_id, rules(priority, expression, command)").eq("unit_id", unit_id).execute();

    # Load unit rules into update message.
    if unit_rule_request.data:
        for rule in unit_rule_request.data:
            message.unit_rules.append(
                DeviceRule.model_validate_json(
                    rule
                )
            )

    # Query for modules by unit_id
    module_id_request = supabase_client.table("modules").select("id, unit_id").eq("unit_id", unit_id).execute()

    if not module_id_request.data:
        return False

    module_ids = [module["id"] for module in module_id_request.data]

    # Query for rule_allocations by module_ids
    rule_id_data = supabase_client.table("module_rule_allocations").select("module_id, rule_id").in_("module_id", module_ids).execute()

    if not rule_id_data.data:
        return {"result": "ok", "message": "No rules configured"}

    rule_ids = [rule_alloc["rule_id"] for rule_alloc in rule_id_data.data]

    # Query for rules by rule_ids
    rule_data = supabase_client.table("rules").select("id, priority, expression, command").in_("id", rule_ids).execute()

    for rule in rule_data.data:
        message.rules.append(DeviceRule.model_validate_json(rule))

    to_send = EgressMessage(
        type="rules",
        data=message
    )

    # Send new commands to the device.
    return await publish_message("/egress/" + unit_id, to_send)

async def insert_readings(data: ReadingMessage):
    """Insert a reading packet into the database."""
    readings_to_insert = []
    state_changes_to_insert = []

    period_start = datetime.datetime.fromtimestamp(data.period_start).strftime("%Y-%m-%d %H:%M:%S+00")
    period_end = datetime.datetime.fromtimestamp(data.period_end).strftime("%Y-%m-%d %H:%M:%S+00")

    # Unpack the reading data into the two lists.
    for reading in data.readings:
        readings_to_insert.append({
            "iqr_apparent_power": reading.apparent_power[2],
            "iqr_power_factor": reading.power_factor[2],
            "kurtosis_apparent_power": reading.apparent_power[3],
            "kurtosis_power_factor": reading.power_factor[3],
            "kwh_usage": reading.kwh_usage,
            "max_apparent_power": reading.apparent_power[1],
            "max_power_factor": reading.power_factor[1],
            "mean_apparent_power": reading.apparent_power[0],
            "mean_frequency": reading.mean_frequency,
            "mean_power_factor": reading.power_factor[0],
            "mean_voltage": reading.mean_voltage,
            "module_id": reading.module_id,
            "period_end_time": period_end,
            "period_start_time": period_start,
            "sample_count": reading.sample_count
        })


        for state_change in reading.state_changes:
            state_changes_to_insert.append({
                    "module" : reading.module_id,
                    "state" : state_change.state,
                    "timestamp" : datetime.datetime.fromtimestamp(state_change.timestamp).strftime("%Y-%m-%d %H:%M:%S+00")
                })

    # Insert the data into the database.
    supabase_client.table("readings").upsert(readings_to_insert).execute()    
    supabase_client.table("module_state_changes").insert(state_changes_to_insert).execute()

# Define the endpoint to receive MQTTBrokerWebhook data
@app.post("/mqtt/v1/ingress", dependencies=[Depends(BrokerJWTBearer())])
async def receive_mqtt_webhook(data: BrokerWebhook):
    try:
        # Decompress the data.
        decompressed_data = await decompress_message_brotli(data.data)

        # Parse the data as Ingress Message
        decompressed_data_message = IngressMessage.model_validate_json(decompressed_data)

        # Check the 'type' field for data type
        if decompressed_data_message.type == 0: # Type 0 - Reading
            await insert_readings(decompressed_data_message.data)

            return {"result" : "ok", "message": "success"}
        else:
            return {"result" : "fail", "message": f"Unsupported data type: {decompressed_data_message.type}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")


    
def log_info(req_body, res_body):
    logging.info(req_body)
    logging.info(res_body)

async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {'type': 'http.request', 'body': body}
    request._receive = receive

@app.middleware('http')
async def some_middleware(request: Request, call_next):
    req_body = await request.body()
    await set_body(request, req_body)
    response = await call_next(request)
    
    res_body = b''
    async for chunk in response.body_iterator:
        res_body += chunk
    
    task = BackgroundTask(log_info, req_body, res_body)
    return Response(content=res_body, status_code=response.status_code, 
        headers=dict(response.headers), media_type=response.media_type, background=task)

def load_config():
    global supabase_url, supabase_service_key, emqx_broker_ip, emqx_broker_http_port, emqx_api_key, emqx_secret, api_hostname, api_port, supabase_client, emqx_headers, emqx_broker_url

    config = configparser.ConfigParser()
    config.read("configuration.ini")
    supabase_url = config["SUPABASE"]["supabase_url"]
    supabase_service_key = config["SUPABASE"]["supabase_service_key"]
    emqx_broker_ip = config["EMQX"]["emqx_broker_ip"]
    emqx_broker_http_port = int(config["EMQX"]["emqx_broker_http_port"])
    emqx_api_key = config["EMQX"]["emqx_api_key"]
    emqx_secret = config["EMQX"]["emqx_secret"]
    api_hostname = config["API"]["hostname"]
    api_port = int(config["API"]["port"])

    # Initialize Supabase client
    supabase_client = create_client(supabase_url, supabase_service_key)

    # JWT Auth to access EMQX HTTP API
    emqx_headers = { "Authorization" : "Basic " + base64.b64encode((emqx_api_key + ":" + emqx_secret).encode()).decode(),
                    "Content-Type": "application/json" }
    emqx_broker_url = "http://" + emqx_broker_ip + ":" + str(emqx_broker_http_port) + "/api/v5/publish"

if __name__ == "__main__":
    import uvicorn
    load_config()
    print("API Token:" + encode_jwt({
        "test" : "test"
    }))

    print("Broker Token: " + encode_broker_jwt({
        "test" : "test"
    }))

    uvicorn.run(app, host=api_hostname, port=api_port)
