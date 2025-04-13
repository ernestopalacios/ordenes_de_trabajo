import json
from quixstreams import Application, State
from quixstreams.models.serializers import JSONSerializer
from quixstreams.models.serializers.quix import QuixDeserializer
from quixstreams.models.rows import Row
import time
import logging
from eerssa.secret import Keys
import pymongo


uri = Keys.MONGO_KEY.value
client = pymongo.MongoClient( uri )

# Ping para confirmar que se ha establecido la conexion
try:
    client.admin.command('ping')
    print("Conexion exitosa!!!!")
except Exception as e:
    print(f"\n\n ><><> Error de conexion a MongoDB: {e}") # More specific error message




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
    """
    Processes a single message (Row) from the Kafka topic.
    Converts the Row value to a dictionary and logs the 'ot_id'.
    """
    try:
        
        ot = row
        ot_id = ot["id_ot"]
        logging.info(f"\n ~~~ (1) Recibido el mensaje: {ot_id}")
        # Add your processing logic here
    except Exception as e:
        logging.info(f"No se ha podido procesar el mensaje: {row}")

        print(f"\n\nError: {e}")
    
    

sdf = sdf.apply(process_row)

# Define a function to run the application (good practice)
def run_app():
    """Starts the Quix Streams application."""
    print("Starting Quix Streams application...")
    app.run(sdf)
    print("Quix Streams application stopped.")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("Application stopped manually.")
    finally:
        # Clean up resources if needed, e.g., close DB connection
        if client:
            client.close()
            print("MongoDB connection closed.")
