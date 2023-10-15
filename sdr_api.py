from fastapi import FastAPI, Response, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from supabase import create_client, Client
from pydantic import BaseModel
from requests import get
import paho.mqtt.client as mqtt
import uvicorn, datetime, logging, configparser, threading, concurrent.futures, random, string
import time

from bin import MessageSerializer
from bin import ReadingBatcher
from bin import Reading


logger = logging.getLogger(__name__)

# Configure the logger to display log messages to the console
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

origins = [
   "127.0.0.1",
]



class TranslationAPI:
    def __init__(self) -> None:
        self.router = APIRouter()
       # self.router.add_route('/auth', self.auth_mqtt, methods=['POST'])

    def start(self, external_ip, supabase: Client, mqtt_server, mqtt_port, self_auth_username, self_auth_password, ingress_topics):
        self.load_config()
        self.supabase = supabase
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.ingress_topics = ingress_topics
        self.external_ip = external_ip
        time.sleep(5)
        self.initMQTT(self_auth_username, self_auth_password)

        self.message_serializer = MessageSerializer.MessageSerializer(self.handleCompressedMessage, self.handleDecompressedMessage, self.max_compression_threads)
        self.reading_batcher = ReadingBatcher.ReadingBatcher(self.mqttc, self.reading_batch_size, self.reading_batch_interval)

    # Loads the configuration for the API from the config file.
    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.reading_batch_interval = config['COMPRESSION_SETTINGS']['INTERVAL']
        self.reading_batch_size = config['COMPRESSION_SETTINGS']['BATCH_SIZE']
        self.max_compression_threads = config['COMPRESSION_SETTINGS']['MAX_THREADS']
        return

    def initMQTT(self, self_auth_username, self_auth_password):
        self.mqttc = mqtt.Client(client_id= "translation_api_" + self.external_ip, transport="websockets")
        self.mqttc.on_connect = self.onMQTTConnect
        self.mqttc.on_message = self.onMQTTMessage
        self.mqttc.username_pw_set(self_auth_username, self_auth_password)

        self.mqttc.connect(self.mqtt_server, self.mqtt_port)
        self.mqttc.loop_start()

    def onMQTTConnect(self, client, userdata, flags, rc):
        for topic in self.ingress_topics: # Subscribe to all ingress topics.
            self.mqttc.subscribe(topic)

    def onMQTTMessage(self, client, userdata, message):
        self.message_serializer.decompress_message(message.topic, message.payload)
        pass
    def handleCompressedMessage(self, topic, message):
        self.mqttc.publish(topic, message)
        pass

    def handleDecompressedMessage(self, topic, message):
        logging.info('==== New Ingress Message ====\nTopic: ' + topic)
        logging.info('Decompressed Message: ' + message)
        if (message['tp'] == "RD"):
            self.handleReadingMessage(topic, message)

    def handleReadingMessage(self, topic, message):
        logging.info("Got reading message on topic: " + topic)
        for reading in message['RD']:
            new_reading = Reading.Reading(module = float(reading['MID']),
                                        voltage = float(reading['V']),
                                        frequency = float(reading['F']),
                                        apparent_power = float(reading['SP']),
                                        power_factor = float(reading['PF']),
                                        kwh_usage = float(reading['kwh']),
                                        timestamp = datetime.datetime.fromtimestamp(float(message['ts'])),
                                        switch_status = bool(reading['state']))

            self.reading_batcher.add_reading(new_reading)

    # Queries the supabase database for an element with matching ID in table.
    def get_rows_by_id(self, table_name, id):
        try:
            response = self.supabase.table(table_name).select("*").eq('id', id).execute()
        except:
            logging.error("No data from supabase")
            return None

        return response.data if (response.data) else None

    def stop(self):
        self.mqttc.disconnect()
        self.reading_batcher.stop()


app = FastAPI()

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

translation_api = TranslationAPI()
auth_api = AuthAPI()

app.include_router(translation_api.router)
app.include_router(auth_api.router)

supabase: Client

def startAPI(external_ip, api_port):
    uvicorn.run(app, host=external_ip, port=api_port)

def randomword(length):
    letters = string.ascii_letters
    word = ''.join(random.choice(letters) for i in range(length))

    return word

def startApp(external_ip, supabase, mqtt_server, mqtt_port, mqtt_self_auth_username, mqtt_self_auth_password, ingress_topics):
    try:
        auth_api.start(supabase, mqtt_self_auth_username, mqtt_self_auth_password)
        translation_api.start(external_ip, supabase, mqtt_server, mqtt_port, mqtt_self_auth_username, mqtt_self_auth_password, ingress_topics)
    except Exception as e:
        logging.error(str(e))
        return

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    supabase_api_key = config['SUPABASE']['API_KEY']
    supabase_url = config['SUPABASE']['URL']
    logging.info("Supabase URL:" + supabase_url)
    logging.info("Supabase API Key: " + supabase_api_key)

    supabase = create_client(supabase_url, supabase_api_key)

    external_ip = get('https://api.ipify.org').content.decode('utf8')
    logging.info("External IP: " + external_ip)

    request = (supabase.table('mqtt_brokers').select('*').eq('api_address', external_ip).execute())

    if (not request.data):
        logging.error('No translation broker with this address was found.')

        return

    request = request.data[0]

    if (not bool(request['is_enabled'])):
        logging.error("Translation broker with this address is not enabled.")
        return

    api_port = request['api_port']
    api_address ="localhost" if (request['api_address'] == external_ip.strip()) else request['api_address']
    mqtt_server = "localhost" if (request['broker_address'] == external_ip.strip()) else request['broker_address']
    mqtt_port = request['broker_port']
    broker_id = request['id']

    # Fetch the ingress topics
    mqtt_topic_request = supabase.table('mqtt_topics').select("*").eq('broker', broker_id).eq('is_ingress', True).execute()

    ingress_topics = []
    if (mqtt_topic_request.data):
        for topic in mqtt_topic_request.data:
            logging.info("Got Ingress Topic: " + topic['topic'])
            ingress_topics.append(topic['topic'])

    logging.info("Got MQTT broker ID: " + broker_id)

    mqtt_self_auth_username = randomword(16)
    mqtt_self_auth_password = randomword(24)

    api_thread = threading.Thread(target=startAPI, args = [api_address, api_port])
    api_thread.start()
    app_thread = threading.Thread(target=startApp, args = [external_ip, supabase, mqtt_server, mqtt_port, mqtt_self_auth_username, mqtt_self_auth_password, ingress_topics])
    app_thread.start()

if __name__ == "__main__":
    main()