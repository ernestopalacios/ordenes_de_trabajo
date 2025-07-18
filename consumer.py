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
KAFKA_KEY = "MBID"

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
ReloadCollection = None


try:
    # Add a timeout to avoid blocking indefinitely
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    # The ping command is cheap and does not require auth.
    client.admin.command('ping')
    db_eerssa = client.eerssa                   # Base de datos EERSSA
    CurrentCollection = db_eerssa.ot_v23        # Coleccion actual
    ReloadCollection  = db_eerssa.ot_reload  # Aqui se cargan OTs repetidas
    logging.info(":::: Conexion exitosa con MongoDB ::::")
    
except ConnectionFailure as e:
    logging.error(f"\n\n ><><> Error de conexion a MongoDB: {e}")
    sys.exit(1) # Exit the script if we can't connect to MongoDB, as it's a critical dependency.


# Quix Stream app configuration

app = Application(
    broker_address="localhost:29092",
    consumer_group="dev_consumer_group",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="INFO",
    on_consumer_error=on_consumer_error_handler,
)

input_topic = app.topic("json_ot_v23", value_serializer = JSONSerializer())
output_topic = app.topic("new_id_v23", key_serializer   = "str", value_serializer="json")
reload_topic = app.topic("stage_id", key_serializer   = "str", value_serializer="json")
sdf = app.dataframe(input_topic)

def process_row(row: Row):
    """
    Processes a single message (Row) from the Kafka topic.
    Checks if a document with the same 'id_ot' exists in the main collection.
    - If it exists, the new document is sent to the 'ot_reemplazo' collection
      for later processing. The original document in the main collection is
      left untouched.
    - If it does not exist, the new document is inserted into the main collection.
    Produces the 'id_ot' to the appropriate Kafka topic.
    """
    try:
        
        ot = row
        is_replacement = False
        ot_id = ot["id_ot"]
        logging.info(f"\n ~~~ (1) Recibido el mensaje Orden de Trabajo con ID: {ot_id}")

        # Check if a document with this ID already exists in the main collection
        if CurrentCollection.find_one({"id_ot": ot_id}, {"_id": 1}):
            # If it exists, this is a replacement. Send to ReloadCollection.
            is_replacement = True
            ReloadCollection.replace_one({"id_ot": ot_id}, ot, upsert=True)
            logging.info(f" ~~~ (2a) OT ya existe. Enviando reemplazo con ID: {ot_id} a la colección '{ReloadCollection.name}'")
        else:
            # If it's a new OT, insert into the main collection.
            CurrentCollection.insert_one(ot)
            logging.info(f" ~~~ (2) Guardada en MongoDB nueva Orden de Trabajo con ID: {ot_id}")

        # The RowProducer is part of the app's processing context and is safe to use here.
        message = output_topic.serialize(key = KAFKA_KEY, value={"id_ot": ot_id})
        topic = reload_topic.name if is_replacement else output_topic.name

        app._producer.produce(
            topic = topic,
            key = message.key,
            value=message.value,
        )

        logging.info(f" ~~~ (3) Enviado a Kafka la OT con ID: {ot_id} a: >> '{topic}'")
    
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
