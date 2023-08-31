from fastapi import HTTPException, FastAPI, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supabase import Client, create_client
from realtime.connection import Socket

from requests import post

from auth import JWTBearer, create_emqx_jwt
from bin.CompressionHandler import CompressionHandler
from bin.MessageBatcher import MessageBatcher

import logging

origins = [
   "127.0.0.1",
]

app = FastAPI()

supabase: Client
auth: Auth
serializer: CompressionHandler
message_batcher: MessageBatcher

broker_id = "dsd" # v4 uuid of API id.
broker_mqtt_publish_qos = 1 # QoS to use when publishing messages.

supabase_url = "127.0.0.1" # IP address of Supabase instance.
supabase_key = "fdsfd" # Service Key of Supabase database.

broker_host = "127.0.0.1" # IP address of EMQX MQTT Broker.
broker_port = 1883 # Port of EMQX MQTT Broker HTTP API.
broker_publish_endpoint = "/api/v4/mqtt/publish" # Publish endpoint of MQTT API.

jwt_secret = "secret123" # Secret to sign new JWTs with.
access_token_duration = 10 * 365 * 24 * 3600 # Number of seconds an access token is valid for from creation.

def ingress_callback(client_id: str, topic: str, payload: dict):
    """Callback from MessageSerializer to handle incoming messages from MQTT devices."""
    msg_type = payload.get("type")

    if (not msg_type) : return # Ignore messages without a type.

    if (msg_type == "reading"):
        logging.info("Got Reading Message: " + str(payload))
        global message_batcher
        message_batcher.add_reading(payload)
    elif (msg_type == "update"):
        logging.info("Got Update Message: " + str(payload))

def egress_callback(client_id: str, topic: str, payload: str):
    """Callback from MessageSerializer to publish the message using the EMQX HTTP API."""
    message = {
        "clientid" : client_id,
        "topic" : topic,
        "payload" : payload,
        "qos" : broker_mqtt_publish_qos
    }

    ret = post(url=broker_host + ":" + broker_port + broker_publish_endpoint, data=message)

    if (ret.status_code != status.HTTP_200_OK):
        logging.error("MQTT Publish failed.")

def main():
    global auth, jwt_secret, supabase, broker_id, serializer, message_batcher
    auth = Auth(jwt_secret)
    serializer = CompressionHandler(egress_callback, ingress_callback)
    supabase = create_client(supabase_url=supabase_url, supabase_key=supabase_key) # Connect to the supabase instance
    message_batcher = MessageBatcher(supabase)

    # Fetch broker and API details

if (__name__ == "__main__"):
    main()

class BrokerWebhookRequest(BaseModel):
    client: str
    topic: str
    payload: str

class BrokerWebhookResponse(BaseModel):
    result: bool
    message: str

@app.post("/sdr/v1/ingress", dependencies=[Depends(JWTBearer())], response_model=BrokerWebhookResponse)
def mqtt_ingress(request: BrokerWebhookRequest):
    """API Endpoint to receive messages from the MQTT Broker."""
    global serializer
    serializer.decompress_message(request.topic, request.payload)
    return BrokerWebhookResponse(result=True, message="success"), status.HTTP_200_OK

class CreateUnitJWTResponse(BaseModel):
    result: bool
    access_token: str

@app.get("/sdr/v1/create_token/{unit_id}", dependencies=[Depends(JWTBearer())], response_model=CreateUnitJWTResponse)
def create_unit_access_token(unit_id: str):
    """Searches the Supabase for a unit with matching ID, then creates a JWT Access token with the fetched data."""
    global auth, access_token_duration, supabase

    try:
        unit_params = supabase.table("units").select("*").eq("id", unit_id).execute()
    except:
        logging.error("Failed to query database.")
        return CreateUnitJWTResponse(result=False, access_token=""), status.HTTP_404_NOT_FOUND

    if (not unit_params) : 
        logging.error("No matching unit parameters were found.")
        return CreateUnitJWTResponse(result=False, access_token=""), status.HTTP_404_NOT_FOUND
    unit_params = unit_params[0]

    return CreateUnitJWTResponse(result=True, access_token=create_emqx_jwt(expiry_s=access_token_duration, username=unit_id, publish_topics=unit_params["publish_topics"], subscribe_topics=unit_params["subscribe_topics"], all_topics=unit_params["all_topics"])), status.HTTP_200_OK

class MQTTEgressMessageRequest(BaseModel):
    client_id: str
    topic: str
    message: str

@app.post("/sdr/v1/send")
def publish_egress_message(request: MQTTEgressMessageRequest, dependencies=[Depends(JWTBearer())]):
    global serializer, supabase
    serializer.compress_message(request.client_id, request.topic, request.message)

@app.get("/sdr/v1/sign_in")
def sign_in(request):
    global supabase
    res = supabase.auth.sign_in()
    pass

@app.get("/sdr/v1/sign_out", dependencies=[Depends(JWTBearer())])
def sign_out():
    pass