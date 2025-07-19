import time
import json
from datetime import datetime, timezone
from quixstreams import Application
from quixstreams.models import JSONSerializer

# Assuming your Quix Streams producer app (can be separate from consumer)
producer_app = Application(
    broker_address="localhost:29092",
    auto_create_topics=True
)

output_topic = producer_app.topic("new_id_v22", value_serializer=JSONSerializer()) # Same topic as your consumer

print("Starting heartbeat producer...")
with producer_app.get_producer() as producer:
    while True:
        try:
            heartbeat_message = {
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            producer.produce(output_topic.name, json.dumps(heartbeat_message).encode('utf-8'), key="MBID")
            print(f"Sent heartbeat: {heartbeat_message}")
            time.sleep(4.5) # Send slightly before 5 seconds to ensure window closes
        except KeyboardInterrupt:
            print("Heartbeat producer stopped.")
            break
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            time.sleep(1) # Wait a bit before retrying
