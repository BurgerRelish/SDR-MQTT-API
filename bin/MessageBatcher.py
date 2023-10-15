from supabase import Client
import time, json, logging, threading, datetime
from Types import Reading, RelayStatus

class MessageBatcher:
    def __init__(self, client: Client, min_batch_size=10, min_interval=5):
        self.client = client
        self.readings = []
        self.status_updates = []
        self.min_batch_size = int(min_batch_size)
        self.min_interval = int(min_interval)
        self.batch_lock = threading.Lock()
        self.batch_thread = threading.Thread(target=self._process_batch)
        self.enable_sending = True
        self.batch_thread.start()

    def add_reading(self, readings: dict):
        new_readings = [] # Process readings.
        for reading in readings["readings"]:
            timestamps = []
            for timestamp in reading["timestamp"]:
                timestamps.append(datetime.datetime.fromtimestamp(timestamp))
            
            new_reading = Reading(
                module=reading["moduleid"],
                count=reading["count"],
                voltage=reading["voltage"],
                apparent_power=reading["apparent"],
                power_factor=reading["factor"],
                kwh_usage=reading["kwh"],
                timestamp=timestamps
            )
            new_readings.append(new_reading)

        new_updates = [] # Process relay statuses.
        for update in reading["relays"]:
            new_update = RelayStatus(
                module=update["moduleid"],
                timestamp=datetime.datetime.fromtimestamp(new_update["timestamp"]),
                status=update["status"]
            )
            new_updates.append(new_update)

        with self.batch_lock: # Take batch lock once all processing has been completed.
            for new_reading in new_readings: # Add readings to the queue.
                self.readings.append(new_reading)
            
            for new_update in new_updates: # Add status updates to the queue.
                self.status_updates.append(new_update)

    def _send_batch(self, min_size):
        with self.batch_lock:
            if len(self.readings) > min_size:
                # Send the batch to Supabase
                self.client.table('readings').insert(self.readings).execute()
                self.client.table('relay_status').insert(self.status_updates).execute()
                logging.info(f"Sent {len(self.readings)} readings to Supabase at {datetime.now()}")
                self.readings = []
                self.status_updates = []

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