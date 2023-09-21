from fastapi import FastAPI, HTTPException, status, Response, Depends, Request
from pydantic import BaseModel
from starlette.background import BackgroundTask
from fastapi.routing import APIRoute
from starlette.types import Message
from starlette.background import BackgroundTask

from supabase import Client, create_client

import brotli, base64, datetime, json, time, logging
import requests

from auth import create_emqx_jwt, JWTBearer, decode_jwt, encode_jwt
from models import (
    MQTTBrokerWebhook,
    MQTTDataPacket,
    DecompressedDataMessage,
    MQTTReadingMessage,
    ControlUnitSetupRequestMessage,
    ControlUnitSetupResponsePacket,
    UnitJWToken,
    MQTTJWTACL,
    DeviceRule,
    RuleUpdateMessage,
    BrokerPublishMessage
)

app = FastAPI()

# Move to config
emqx_broker_ip = "localhost"
emqx_broker_http_port = 8081
emqx_api_key = "1535fe6c47b8ae00"
emqx_secret = "9AnLg9B2shVwl9Cv5cFMFLGzLV4RINYZQfMeIqGKzrYt1B"
jwt_secret = "secret123"
supabase_url = "https://pdmoslivyqyvjcbgtjek.supabase.co"
supabase_service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkbW9zbGl2eXF5dmpjYmd0amVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY5NTI5Mzc2OCwiZXhwIjoyMDEwODY5NzY4fQ.yenF8AVYyR5PMSN7AD8sLEriFMTxmKNC8YVTTO_XiYo"

# Initialize your Supabase client
supabase_client = create_client(supabase_url, supabase_service_key)

# JWT Auth to access EMQX HTTP API
emqx_auth_header = "Basic " + base64.b64encode((emqx_api_key + ":" + emqx_secret).encode()).decode()


async def decompress_message(message: str) -> str:
    return str(brotli.decompress(base64.b64decode(message)).decode('utf-8'))

async def compress_message(message: str) -> MQTTDataPacket:
    ret = MQTTDataPacket(enc="br",msg=str(base64.b64encode(brotli.compress(message.encode('utf-8'))).decode('UTF-8')))  # Encode the message with utf-8, compress it, then convert the bytes to base64, and return a string of it.
    return ret

async def publish_message(topic: str, message: DecompressedDataMessage):
    """Publish a message to the provided topic. Compresses and formats the message accordingly"""

    message_str = message.model_dump_json()
    payload = await compress_message(message_str)

    request_data = BrokerPublishMessage(
        payload_encoding="plain",
        topic = topic,
        payload = payload.model_dump_json(),
        qos=0,
        retain=False,
    )

    # Send message to broker with post request
    result = requests.post("http://localhost:18083/api/v5/publish",
                           json = request_data.model_dump(), headers={"Authorization" : emqx_auth_header, "Content-Type": "application/json"})
    
    if (result.status_code == 200):
        return {"result" : "ok", "message" : "The message was delivered to at least one subscriber."}
    if (result.status_code == 202):
        return {"result" : "ok", "message" : "No matched subscribers."}
    if (result.status_code == 400):
        raise HTTPException(status_code=result.status_code, detail={"result" : "fail", "message" : "Message is invalid."})

    return Response({"result" : "fail", "message" : "Failed to deliver the message to subscriber(s)"}, result.status_code)


async def get_acl(unit_id: str) -> MQTTJWTACL:
    """Get the assosciated Access Control List for the control unit."""

    # Fetch topic info for the unit.
    data = supabase_client.table("topic_allocations").select("unit_id, ingress, all, topics(topic)").eq("unit_id", unit_id).execute()

    if (not data):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Not provisioned.")
    print(data.data)
    # Arrange the topics into the ACL format
    all = []
    pub = []
    sub = []

    for row in data.data:
        topic = row["topics"]["topic"]
        if row["all"]:
            all.append(topic)
        if row["ingress"]:
            pub.append(topic)
        else:
            sub.append(topic)
                
    return MQTTJWTACL(pub=pub, sub=sub, all=all)

@app.get("/mqtt/v1/auth", dependencies=[Depends(JWTBearer())])
async def create_unit_token(user_id: str, unit_id: str) -> str:
    """ Creates an MQTT access token for a control unit. Assosciates the unit with a user, and queries the database for assigned topics. Raises a 406 error if no topics are provisioned for the device.
    """
    # Assign the unit to the user.
    supabase_client.table("control_units").update(
        {
            "user_id" : user_id,
        }
    ).eq("id", unit_id).execute()

    ret = UnitJWToken(
        username=unit_id,
        exp=int(time.time() + 3600 * 24 * 365 * 10), # Expire after 10 years.
        acl=await get_acl(unit_id)
    )

    return encode_jwt(ret.model_dump())

@app.post("/mqtt/v1/send", dependencies=[Depends(JWTBearer())])
async def send_command(unit_id: str, payload: RuleUpdateMessage):
    to_send = DecompressedDataMessage(
        type="command",
        data=payload.model_dump_json()
    )

    return await publish_message("/egress/" + unit_id, to_send)

@app.get("/mqtt/v1/sync", dependencies=[Depends(JWTBearer())])
async def sync_commands(unit_id: str):
    """Sync the database and Control Unit commands."""
    message = RuleUpdateMessage(
        action = "replace",
        rules=[]
    )

    # Query for modules by unit_id
    module_id_request = supabase_client.table("modules").select("id, unit_id").eq("unit_id", unit_id).execute()

    if not module_id_request.data:
        return False

    module_ids = [module["id"] for module in module_id_request.data]

    # Query for rule_allocations by module_ids
    rule_id_data = supabase_client.table("rule_allocations").select("module_id, rule_id").in_("module_id", module_ids).execute()

    if not rule_id_data.data:
        return {"result": "ok", "message": "No rules configured"}

    rule_ids = [rule_alloc["rule_id"] for rule_alloc in rule_id_data.data]

    # Query for rules by rule_ids
    rule_data = supabase_client.table("rules").select("id, priority, expression, command").in_("id", rule_ids).execute()

    for rule in rule_data.data:
        message.rules.append(DeviceRule.model_validate_json(rule))

    to_send = DecompressedDataMessage(
        type="rules",
        data=message.model_dump_json()
    )

    return await publish_message("/egress/" + unit_id, to_send)

async def insert_readings(data: str):
    """Insert a reading packet into the database.
    """
    # Parse the data as MQTTReadingMessage
    reading_data = MQTTReadingMessage.model_validate_json(data)

    readings_to_insert = []
    state_changes_to_insert = []

    # Insert the data into the 'readings' table in Supabase with the retrieved user_id
    for reading in reading_data.data:
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
            "period_end_time": datetime.datetime.fromtimestamp(reading_data.period_end).strftime("%Y-%m-%d %H:%M:%S+00"),
            "period_start_time": datetime.datetime.fromtimestamp(reading_data.period_start).strftime("%Y-%m-%d %H:%M:%S+00"),
            "sample_count": reading.sample_count
        })


        for state_change in reading.state_changes:
            state_changes_to_insert.append({
                    "module" : reading.module_id,
                    "state" : state_change.state,
                    "timestamp" : datetime.datetime.fromtimestamp(state_change.timestamp).strftime("%Y-%m-%d %H:%M:%S+00")
                })

    supabase_client.table("readings").upsert(readings_to_insert).execute()    
    supabase_client.table("module_state_changes").insert(state_changes_to_insert).execute()

# Define the endpoint to receive MQTTBrokerWebhook data
@app.post("/mqtt/v1/ingress", dependencies=[Depends(JWTBearer())])
async def receive_mqtt_webhook(data: MQTTBrokerWebhook):
    try:
        # Decode the data field from base64
        data_packet = MQTTDataPacket.model_validate_json(data.data)

        # Check the 'enc' field for compression type ('br' for Brotli)
        if data_packet.enc == "br":
            # Decompress the 'msg' field from Brotli
            decompressed_data = await decompress_message(data_packet.msg)

            # Parse the data as DecompressedDataMessage
            decompressed_data_message = DecompressedDataMessage.model_validate_json(decompressed_data)

            # Check the 'type' field for data type ('reading' for MQTTReadingMessage)
            if decompressed_data_message.type == "reading":
                await insert_readings(decompressed_data_message.data)
            # if decompressed_data_message.type == "update":
            #     handle_update_request(decompressed_data_message.data)

            return {"result" : "ok", "message": "success"}
        else:
            return {"result" : "fail", "message": f"Unsupported data type: {decompressed_data_message.type}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")


# logging.basicConfig(filename='info.log', level=logging.DEBUG)
    
# def log_info(req_body, res_body):
#     logging.info(req_body)
#     logging.info(res_body)

# async def set_body(request: Request, body: bytes):
#     async def receive() -> Message:
#         return {'type': 'http.request', 'body': body}
#     request._receive = receive

# @app.middleware('http')
# async def some_middleware(request: Request, call_next):
#     req_body = await request.body()
#     await set_body(request, req_body)
#     response = await call_next(request)
    
#     res_body = b''
#     async for chunk in response.body_iterator:
#         res_body += chunk
    
#     task = BackgroundTask(log_info, req_body, res_body)
#     return Response(content=res_body, status_code=response.status_code, 
#         headers=dict(response.headers), media_type=response.media_type, background=task)

if __name__ == "__main__":
    import uvicorn
    print(encode_jwt({
        "broker_id" : "51b99c79-9541-4df2-9863-fb6409245754"
    }))

    uvicorn.run(app, host="0.0.0.0", port=8000)
