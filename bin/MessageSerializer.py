import concurrent.futures
import logging, base64, brotli, json
from typing import List, Any

class MessageSerializer:
    def __init__(self, compression_callback, decompression_callback, max_threads: int = 5):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=int(max_threads)) # Thread Pool for MQTT Compression/Decompression
        self.decompression_callback = decompression_callback
        self.compression_callback = compression_callback

    def decompress_message(self, topic: str, message: str):
        with self.executor.submit(self.brotli_decompress, args = [topic, message]) as future:
            future.add_done_callback(self.handle_decompressed_message)
            

    def compress_message(self, topic: str, message: str):
        with self.executor.submit(self.brotli_compress, args = [topic, message]) as future:
            future.add_done_callback(self.handle_compressed_message)

    def handle_compressed_message(self, future):
        result = future.result()
        self.compression_callback(result[0], result[1])
    
    def handle_decompressed_message(self, future):
        result = future.result()
        self.decompression_callback(result[0], result[1])

    # Compresses a message with brotli and creates a json packet ready for interpretation by SDR units. Returns a list, with the first
    # element being the destination topic, and the second the json packet in str format.
    def brotli_compress(self, topic: str, message: str) -> List[str, str]:
        retval = {}
        retval['enc'] = "br"

        try:
            retval['msg'] = base64.b64encode(brotli.compress(message.encode('utf-8'))).decode('utf-8')
            logging.info("Message Compressed:\nTopic: " + topic + "\nMessage: " + message)
        except Exception as e:
            logging.error("Compression error: " + str(e))
            return [str(), str()]
        
        return [topic, json.dumps(retval)]


    # Decompresses a message with brotli compression and returns a json packet containing the data, or an empty json packet if failed.
    def brotli_decompress(self, topic: str, message: str) -> List[str, Any]:
        msg_object = json.loads(message)
        if(msg_object['enc'] != "br"):
            logging.error("Invalid encoding format.")
            return [topic, json.loads(str())]
        
        try:
            data = brotli.decompress(base64.b64decode(msg_object["msg"])).decode('utf-8')
            logging.info("Message Decompressed:\nMessage: " + data + "\nRatio: " + str(len(message) * 100 / len(data)) + "%.")
            return [topic, json.loads(data)]
        except Exception as e:
            print("Decompression Error:", str(e))
            return [topic, json.loads(str())]
