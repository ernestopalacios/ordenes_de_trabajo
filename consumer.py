import time
from datetime import datetime
import sys
import threading
from quixstreams import Application
from quixstreams.models.serializers import JSONSerializer
from quixstreams.models.rows import Row
import logging
from eerssa.secret import Keys
import pymongo
from confluent_kafka import Message
from pymongo.errors import ConnectionFailure

# --- Global State & Configuration ---
# Global timer to track the time since the last message was produced.
LAST_MESSAGE_TIMESTAMP = None
IS_FIRST_MESSAGE_SENT = False
# Event to signal the heartbeat thread to stop
SHUTDOWN_EVENT = threading.Event()
# Kafka Topic Name with json format documents
KAFKA_JSON = "json_ot_v30"
# Kafka Topic Name for concatenating to Delta Laje
KAFKA_TO_DELTA = "to_delta"
# Karka KEY for the Delta Topic
KAFKA_KEY = "MBID"


#Setup Logging
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
uri = Keys.MONGO_KEY.value
client = None
db_eerssa = None
CurrentCollection = None
ReloadCollection = None

try:
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db_eerssa = client.eerssa
    CurrentCollection = db_eerssa.ot_v30
    ReloadCollection  = db_eerssa.ot_reload
    logging.info(":::: Conexion exitosa con MongoDB ::::")
except ConnectionFailure as e:
    logging.error(f"\n\n ><><> Error de conexion a MongoDB: {e}")
    sys.exit(1)

# --- Quix Stream App Configuration ---
app = Application(
    broker_address="localhost:29092",
    consumer_group="dev_consumer_group",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="INFO",
    on_consumer_error=on_consumer_error_handler,
)

input_topic = app.topic(KAFKA_JSON, value_serializer=JSONSerializer())
output_topic = app.topic(KAFKA_TO_DELTA, key_serializer="str", value_serializer="json")

sdf = app.dataframe(input_topic)

def process_row(row: Row):
    """
    Processes a single message (Row) from the Kafka topic.
    """
    try:
        ot = row
        is_replacement = False
        ot_id = ot["id_ot"]
        logging.info(f"\n ~~~ (1) Recibido el mensaje Orden de Trabajo con ID: {ot_id}") 

        if CurrentCollection.find_one({"id_ot": ot_id}, {"_id": 1}):
            is_replacement = True
            ReloadCollection.replace_one({"id_ot": ot_id}, ot, upsert=True)
            logging.info(f" ~~~ (2a) OT ya existe. Enviando reemplazo con ID: {ot_id} a la colección '{ReloadCollection.name}'")
        else:
            CurrentCollection.insert_one(ot)
            logging.info(f" ~~~ (2) Guardada en MongoDB nueva Orden de Trabajo con ID: {ot_id}")

        # Use the public get_producer() method for safety outside stream context
        with app.get_producer() as producer:
            message = output_topic.serialize(
                key = KAFKA_KEY, 
                value = {"id_ot": ot_id, "is_replacement": int(is_replacement)})
            
            topic = output_topic.name
            
            producer.produce(
                topic=topic,
                key=message.key,
                value=message.value,
            )
            producer.flush()
            logging.info(f" TIMESTAMP envio de OT : {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")


        global LAST_MESSAGE_TIMESTAMP, IS_FIRST_MESSAGE_SENT
        LAST_MESSAGE_TIMESTAMP = time.time()
        IS_FIRST_MESSAGE_SENT = True

        logging.info(f" ~~~ (3) Enviado a Kafka la OT con ID: {ot_id} a: >> '{topic}'")
    except Exception as e:
        logging.info(f"No se ha podido procesar el mensaje:\n>| {row} |<")
        logging.error(f"\n\nError: {e}")

sdf = sdf.apply(process_row)

# = = = =   H E A R T B E A T   = = = = #
# Esta porcion del codigo monitorea cuanto tiempo ha transcurrido.
# desde la ultima vez que se envio un mensaje al topic 'to_delta'
# El objetivo es asegurarse de que se complete la ventana de 5 segundos
# asegurandose la ejecucion de la ultima ventana y evitando llenar el
# topic Kafka de mensajes de <3 
def heartbeat_loop():
    """
    Continuously checks for inactivity and sends a heartbeat message if needed.
    This function is designed to run in a loop until the SHUTDOWN_EVENT is set.
    """
    # Get a thread-safe producer instance for this thread
    producer = app.get_producer()
    
    while not SHUTDOWN_EVENT.is_set():
        global LAST_MESSAGE_TIMESTAMP, IS_FIRST_MESSAGE_SENT, KAFKA_KEY
        
        # Check if a message has been sent and if 5 seconds have passed
        if IS_FIRST_MESSAGE_SENT and (time.time() - LAST_MESSAGE_TIMESTAMP > 5.5):
            logging.info(f" <3 Inactivity detected. Sending heartbeat to: {KAFKA_TO_DELTA}")
            try:
                heartbeat_payload = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "source": "consumer"
                }
                heartbeat_message = output_topic.serialize(key=KAFKA_KEY, value=heartbeat_payload)
                
                producer.produce(
                    topic=output_topic.name,
                    key=heartbeat_message.key,
                    value=heartbeat_message.value,
                )
                logging.info(" <3 Heartbeat sent.")
                
                # Reset the flag to prevent repeated heartbeats for the same inactivity period
                IS_FIRST_MESSAGE_SENT = False
                
            except Exception as e:
                logging.error(f"Error sending heartbeat: {e}")
        
        # Wait for 1 second before checking again, or until shutdown is triggered
        SHUTDOWN_EVENT.wait(1.0)
    
    logging.info("Heartbeat thread is shutting down.")


# --- Main Application Execution ---
def run_app():
    """Starts the Quix Streams application."""
    print("\n\n = = = =   Iniciando CONSUMIDOR [Quix Streams application] ...  = = = =")
    app.run()
    print("\n\n = = = =   Se ha detenido [Quix Streams application] = = = =")

if __name__ == "__main__":
    heartbeat_thread = None
    try:
        # Initialize the global timer
        LAST_MESSAGE_TIMESTAMP = time.time()
        
        # Create and start the heartbeat thread
        print("... Iniciando Heartbeat thread ...")
        heartbeat_thread = threading.Thread(target=heartbeat_loop)
        heartbeat_thread.daemon = True  # Allows main program to exit even if thread is running
        heartbeat_thread.start()
        
        # Run the main Quix application (this is a blocking call)
        run_app()
        
    except KeyboardInterrupt:
        print("\nSe ha detenido el consumidor manualmente.\n")
    except Exception as e:
        logging.error(f"\n\n [X] An unexpected error occurred: {e}")
    finally:
        # Signal the heartbeat thread to shut down
        if heartbeat_thread:
            print("... Deteniendo Heartbeat thread ...")
            SHUTDOWN_EVENT.set()
            # Wait for the thread to finish its current loop
            heartbeat_thread.join(timeout=2)

        # Clean up other resources
        if client:
            client.close()
            print("\nCerrada la conexion con MongoDB.\n")
