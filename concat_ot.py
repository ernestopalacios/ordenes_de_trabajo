from pprint import pprint
import json
import logging
import sys
from quixstreams import Application
from quixstreams.models import StringDeserializer
#from quixstreams.models.serializers import JSONSerializer, JSONDeserializer
from confluent_kafka import Message
from eerssa.secret import Keys
from eerssa import gestionOT as OrdenTrabajo             # Convert from PDF_ot to obj_ot
from eerssa import matrizActividades as Actividades     # process ot.data["actividades"]
import pymongo
from pymongo.errors import ConnectionFailure
import pandas as pd


from deltalake import DeltaTable, write_deltalake


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up DeltaLake PATH to table
table_path = "./test/deltalake_2025"

# --- DELTA LAKE Database Check ---
# Verify the existence of the DELTA LAKE table
if not DeltaTable.is_deltatable(table_path):
    logger.error(
        f"No se ha encontrado la base de datos PARQUET-DELTALAKE en la direccion:\n NO_DELTA_LAKE : {table_path}"
    )
    sys.exit(1)
else:
    logger.info(f"Conectado a la tabla Delta Lake en: {table_path}")


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
# Establish the connection once for the app's lifetime.
# Exit if the connection fails, as it's a critical dependency.
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
    sys.exit(1) # Exit the script if we can't connect to MongoDB.


# Quix Stream app configuration from your request
app = Application(
    broker_address="localhost:29092",
    consumer_group="concat_v3",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="DEBUG",
    on_consumer_error=on_consumer_error_handler,
)

input_topic = app.topic("new_id_v23", value_deserializer=StringDeserializer())

sdf = app.dataframe(input_topic)


def reducer(aggregated_values, new_value):
    """
    Append each new value to a list for batching.
    """
    aggregated_values.append(new_value)
    logger.debug(f" > APPENDING: Initializing window with: {new_value}")
    return aggregated_values


def process_batch(window_values):
    if not window_values:
        return

    logger.info(f"Processing batch of {len(window_values)} messages.")

    new_data_frames = []
    for i, value in enumerate(window_values.get('value'),1):
        
        try:
            # Parse the JSON string
            json_data = json.loads(value)

            # --- FILTER HEARTBEAT MESSAGES HERE ---
            if json_data.get('type') == 'heartbeat':
                logger.debug(f"  <3 Heartbeat : {value}")
                continue
            # --- END FILTER ---

            logger.info(f"  - Item {i}: <| {value} |>")
            
            # Find document with id_ot on MongoDB
            id_ot_value = json_data.get('id_ot')
            if id_ot_value is None:
                logger.warning(f" [X] El mensaje no contiene 'id_ot'. Saltado: {value}")
                continue

            json_ot = CurrentCollection.find_one({"id_ot": id_ot_value})
            if not json_ot:
                logger.warning(f"No se pudo encontrar la OT con id_ot '{id_ot_value}' en MongoDB. Saltando.")
                continue
            
            obj_ot = OrdenTrabajo.GestionOt.from_dict(json_ot)
            new_data_frames.append(Actividades.ConvertirOT_a_ActividadesCSV(obj_ot))
        except json.JSONDecodeError as e:
            logger.error(f"Fallo al parsear JSON del item {value}. Error: {e}")
            continue # Continue with the next message in the batch
        except Exception as e:
            logger.error(f"Fallo al procesar el item {value}. Error: {e}")
            continue # Continue with the next message in the batch

    if not new_data_frames:
        logger.debug("No hay nuevos datos para agregar a la tabla Delta.")
        return

    try:
        new_df = pd.concat(new_data_frames, ignore_index=True)
        write_deltalake(table_path, new_df, mode='append')
        logger.info(f" [EXITO] Se han añadido {len(new_df)} filas a la tabla Delta en '{table_path}'.")
    except Exception as e:
        logger.error(f"Fallo al escribir en la tabla Delta: {e}")


# Apply a 5-second tumbling window to batch messages
sdf = sdf.tumbling_window(duration_ms=5000)

# The initializer for reduce receives the first value of the window
# and must return the initial state of the aggregate.
def initializer(first_value):
    logger.debug(f" > I N I T: Initializing window with: {first_value}")
    return [first_value]

sdf = sdf.reduce(reducer=reducer, initializer=initializer)

# Use .final() to process the accumulated list when the window closes
sdf = sdf.final().apply(process_batch)


def run_app():
    """Starts the Quix Streams application."""
    print("\n\n = = = =   Iniciando BATCH CONSUMER [Quix Streams application] ...  = = = =")
    app.run()
    print("\n\n = = = =   Se ha detenido [Quix Streams application] = = = =")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nApplication stopped manually.")
    finally:
        # Clean up resources, e.g., close DB connection
        if client:
            client.close()
            print("\nCerrada la conexion con MongoDB.\n\n")