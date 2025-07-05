import json
import sys
from quixstreams import Application
from quixstreams.models.serializers import JSONSerializer, SerializationError
from quixstreams.models.rows import Row
import logging
from eerssa.secret import Keys
import pymongo
from confluent_kafka import Message
from pymongo.errors import ConnectionFailure



logging.basicConfig(level=logging.INFO)


def on_consumer_error_handler(
    exc: Exception,
    msg: Message,
    logger: logging.Logger,
) -> bool:
    """
    Callback to handle exceptions during message deserialization.
    This will log the problematic message and allow the consumer to continue.
    """
    logger.error(
        f"Failed to deserialize message. Exception: {exc}\n"
        f"Topic: {msg.topic()}, Partition: {msg.partition()}, Offset: {msg.offset()}\n"
        f"Message value (raw): {msg.value()!r}"
    )
    # Returning True tells the consumer to ignore the message and continue.
    return True

# --- MongoDB Connection ---
# It's better to establish the connection once and keep it open for the app's lifetime.
# We will also exit if the connection fails, as the consumer can't do its job without it.
uri = Keys.MONGO_KEY.value
client = None  # Initialize client to None
db_eerssa = None
CurrentCollection = None

try:
    # Add a timeout to avoid blocking indefinitely
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    # The ping command is cheap and does not require auth.
    client.admin.command('ping')
    db_eerssa = client.eerssa               # Base de datos EERSSA
    CurrentCollection = db_eerssa.ot_v22    # Coleccion actual
    logging.info(":::: Conexion exitosa con MongoDB ::::")
except ConnectionFailure as e:
    logging.error(f"\n\n ><><> Error de conexion a MongoDB: {e}")
    sys.exit(1) # Exit the script if we can't connect to MongoDB, as it's a critical dependency.


# Quix Stream app configuration

app = Application(
    broker_address="localhost:29092",
    consumer_group="my-group",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="INFO",
    on_consumer_error=on_consumer_error_handler,
)

topic = app.topic("json_ot", value_serializer=JSONSerializer())
sdf = app.dataframe(topic)

def process_row(row: Row):
    """
    Processes a single message (Row) from the Kafka topic.
    Converts the Row value to a dictionary and logs the 'ot_id'.
    Inserts the document into MongoDB, replaces it if already exists.
    """
    try:
        
        ot = row
        ot_id = ot["id_ot"]
        logging.info(f"\n ~~~ (1) Recibido el mensaje Orden de Trabajo con ID: {ot_id}")

        result = CurrentCollection.replace_one({"id_ot": ot_id}, ot, upsert=True)

        if result.upserted_id:
            logging.info(f" ~~~ (2) Guardado en MongoDB nueva Orden de Trabajo con ID: {ot_id}")
        elif result.modified_count > 0:
            logging.info(f" ~~~ (2) Actualizada en MongoDB la Orden de Trabajo con ID: {ot_id}")
    
    except Exception as e:
        logging.info(f"No se ha podido procesar el mensaje:\n>| {row} |<")
        logging.error(f"\n\nError: {e}")
    
    






sdf = sdf.apply(process_row)

# Define a function to run the application (good practice)
def run_app():
    """Starts the Quix Streams application."""
    print("\n\n = = = =   Iniciando CONSUMIDOR [Quix Streams application] ...  = = = =")
    try:
        app.run()
    except Exception as e:
        logging.error(f"\n\n [X] Error: {e}")
    finally:
        print("\n\n = = = =   Se ha detenido [Quix Streams application] = = = =")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nSe ha detenido el consumidor manualmente.\n\n")
    finally:
        # Clean up resources if needed, e.g., close DB connection
        if client:
            client.close()
            print("\nCerrada la conexion con MongoDB.\n\n")
