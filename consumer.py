import json
from quixstreams import Application, State
from quixstreams.models.serializers import JSONSerializer
from quixstreams.models.serializers.quix import QuixDeserializer
from quixstreams.models.rows import Row
import time
import logging

logging.basicConfig(level=logging.INFO)

app = Application(
    broker_address="localhost:29092",
    consumer_group="my-group",
    auto_create_topics=True,
    consumer_extra_config={"auto.offset.reset": "earliest"}
)

topic = app.topic("json_ot", value_serializer=JSONSerializer())

sdf = app.dataframe(topic)

def process_row(row: Row):
    logging.info(f"Received row: {row}")
    # Add your processing logic here
    time.sleep(1)

sdf = sdf.apply(process_row)

if __name__ == "__main__":
    app.run(sdf)
