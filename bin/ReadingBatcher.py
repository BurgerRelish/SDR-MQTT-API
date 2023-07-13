from supabase import Client
import datetime
import threading
import logging
import time
from bin import Reading

class ReadingBatcher:
    def __init__(self, client: Client, min_batch_size=10, min_interval=5):
        self.client = client
        self.readings = []
        self.min_batch_size = int(min_batch_size)
        self.min_interval = int(min_interval)
        self.batch_lock = threading.Lock()
        self.batch_thread = threading.Thread(target=self._process_batch)
        self.enable_sending = True
        self.batch_thread.start()

    def add_reading(self, reading: Reading):
        with self.batch_lock:
            self.readings.append(reading)
            if len(self.readings) >= self.max_batch_size:
                self._process_batch()

    def _send_batch(self, min_size):
        with self.batch_lock:
            if len(self.readings) > min_size:
                # Send the batch to Supabase
                self.client.table('readings').insert(self.readings).execute()
                logging.info(f"Sent {len(self.readings)} readings to Supabase at {datetime.now()}")
                self.readings = []

    def _process_batch(self):
        while (self.enable_sending):
            time.sleep(self.min_interval) # Only send batches every min_interval seconds
            self._send_batch(self.min_batch_size)

    def stop(self):
        self.enable_sending = False
        self.batch_thread.join(timeout=self.min_interval + 2.5)
        if self.batch_thread.is_alive():
            logging.error("Batch processing thread did not complete within the specified interval.")
        else:
            logging.info("Batch processing thread stopped successfully.")

        self._send_batch(0) # Send any remaining readings out before returning.