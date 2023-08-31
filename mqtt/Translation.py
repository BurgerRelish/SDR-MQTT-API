import logging
import paho.mqtt.client as mqtt
from bin.MessageSerializer import MessageSerializer
from supabase_py import Client

class Translation:
    """ Handles bidirectional compression and MQTT messages between the broker and database. """
    def __init__(self, id: str, address: str, port: int, username: str, password: str, supabase: Client) -> None:
        self.client = mqtt.Client(client_id=id)
        self.supabase = supabase
        self.client.username_pw_set(username, password)
        self.serializer = MessageSerializer(compression_callback=self.compr_callback, decompression_callback=self.decomp_callback)

        self.client.connect(address, port)
        self.client.on_message(self.on_message)
        self.client.message_callback_add()

    def on_message(self, topic, message):
        self.serializer.decompress_message(topic, message)

    def compr_callback(self, topic, message):
        pass

    def decomp_callback(self, topic, message):
        pass

    def handle_reading_message():
        pass

    def handle_update_request():
        pass

def on_connect():
    """MQTT Callback called on client connection."""
    pass

def on_message(client, userdata, message):
    """Default Callback for all unfiltered messages."""
    global serializer
    serializer.decompress_message(userdata, message) # Decompresses the MQTT message and calls the ingress callback.

def connect_mqtt(host: str, port: int, username: str, password: str):
    global mqtt_client
    mqtt_client = mqtt.Client(self_mqtt_client_id, True)
    mqtt_client.username_pw_set(username, password)
    mqtt_client.on_connect(on_connect)
    mqtt_client.on_message(on_message)

    mqtt_client.connect(host, port)
    mqtt_client.loop_start()

def ingress_callback(topic: str, message: str):
    """Callback to handle all ingress messages."""
    msg: dict[str, any] = json.loads(message)
    msg_type = msg.get("type")
    if (not msg_type) : return # Ignore messages without a "type" key.

    if (msg_type == "reading") :
        pass
    elif (msg_type == "update") : 
        pass
    else :
        return

def egress_callback(topic: str, message: str):
    """Callback to handle all egress messages."""
    global mqtt_client
    mqtt_client.publish(topic, message) # Publish the message to the provided topic.

def send_message(topic: str, message: str):
    """Compress and send a message to the provided topic."""
    global serializer
    serializer.compress_message(topic, message) # Compresses the message and then calls the egress callback.