from pprint import pprint
import json
import logging
import sys

from quixstreams import Application
from quixstreams.models import StringDeserializer
from confluent_kafka import Message

from eerssa.secret import Keys
from eerssa import gestionOT as OrdenTrabajo            
from eerssa import procesarActividades as Actividades  

import pymongo
from pymongo.errors import ConnectionFailure
import pandas as pd
from deltalake import DeltaTable, write_deltalake


#Kafka Topic Name for concatenating to Delta Laje
KAFKA_TO_DELTA = "to_delta"
# Karka KEY for the Delta Topic
KAFKA_KEY = "MBID"
# Where is the DELTA LAKE TABLE
# DELTA_TABLE_PATH_ON_HOST 
table_path = "/home/vlad/delta_V30"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up DeltaLake PATH to table


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
    CurrentCollection = db_eerssa.ot_v30        # Coleccion actual
    ReloadCollection  = db_eerssa.ot_reload  # Aqui se cargan OTs repetidas
    logging.info(":::: Conexion exitosa con MongoDB ::::")

except ConnectionFailure as e:
    logging.error(f"\n\n ><><> Error de conexion a MongoDB: {e}")
    sys.exit(1) # Exit the script if we can't connect to MongoDB.


# Quix Stream app configuration from your request
app = Application(
    broker_address="localhost:29092",
    consumer_group="delta_writer_group",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="INFO",
    on_consumer_error=on_consumer_error_handler,
)

input_topic = app.topic(KAFKA_TO_DELTA, key_deserializer="str", value_deserializer=StringDeserializer())

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

    new_data_frames = []     # Aqui van las nuevas filas para incluir a DataLake
    reload_data_frames = []  # Aqui van las ot repetidas para acutalizar Mongo y Delta
    for i, value in enumerate(window_values.get('value'),1):
        
        try:
            # Parse the JSON string
            json_data = json.loads(value)

            # --- FILTRA HEARTBEAT ---
            if json_data.get('type') == 'heartbeat':
                logger.debug(f"  <3 Heartbeat : {value}")
                continue
            
            
            # --- CLASIFICA MENSAJES  NUEVOS | REEMPLAZO  ---
            is_replacement = json_data.get('is_replacement')
            logger.info(f"  - Item {i}: <| {value} |> REPLACEMENT: {is_replacement}")
            
            if not is_replacement: # Se trata de una OT nueva en el servidor MongoDB
                id_ot_value = json_data.get('id_ot')
                if id_ot_value is None:
                    logger.warning(f" [X] El mensaje no contiene 'id_ot'. Saltado: {value}")
                    continue

                json_ot = CurrentCollection.find_one({"id_ot": id_ot_value})
                if not json_ot:
                    logger.warning(f"No se pudo encontrar la OT con id_ot '{id_ot_value}' en MongoDB. Saltando.")
                    continue
                
                obj_ot = OrdenTrabajo.GestionOt.from_v30(json_ot)
                new_data_frames.append(Actividades.ConvertirOT_a_ActividadesCSV(obj_ot))
            else:
                # Replacement OT are treated later down the pipe
                reload_data_frames.append(json_data.get('id_ot'))
        

        except json.JSONDecodeError as e:
            logger.error(f"Fallo al parsear JSON del item {value}. Error: {e}")
            continue # Continue with the next message in the batch
        except Exception as e:
            logger.error(f"Fallo al procesar el item {value}. Error: {e}")
            continue # Continue with the next message in the batch

    # ---- Escribir los nuevos cambios a DELTA LAKE  ----
    if new_data_frames:
        try:
            new_df = pd.concat(new_data_frames, ignore_index=True)
            write_deltalake(table_path, new_df, mode='append')
            logger.info(f" [ EXITO ] DELTA LAKE Se han añadido {len(new_df)} filas a la tabla Delta en '{table_path}'.")
        except Exception as e:
            logger.error(f"Fallo al escribir en la tabla Delta: {e}")
    
    # ---- Actualizar los nuevos cambios a DELTA LAKE y a MONGODB  ----
    if reload_data_frames:
        for i, value in enumerate(reload_data_frames,1):
            try:
                id_ot_value = value
                json_new = ReloadCollection.find_one({"id_ot": id_ot_value})
                if not json_new:
                    logger.info(f" [x] Error no se pudo encontrar la OT de reemplazo: {value}")
                    continue
                json_old = CurrentCollection.find_one({"id_ot": id_ot_value})
                if not json_old:
                    logger.info(f" [x] Error no se pudo encontrar la OT original: {value}")
                    continue

            # 2. Compare documents to see if an update is needed.
                # We create copies and remove fields that shouldn't be compared,
                # like the database ID and the log history.
                json_new_for_compare = json_new.copy()
                json_old_for_compare = json_old.copy()
                json_new_for_compare.pop("_id", None)
                json_old_for_compare.pop("_id", None)
                json_new_for_compare.pop("log", None)
                json_old_for_compare.pop("log", None)

                if json_new_for_compare == json_old_for_compare:
                    logging.info(f" [=] No changes detected for OT '{id_ot_value}'. Skipping update.")
                    ReloadCollection.delete_one({"id_ot": id_ot_value})
                    continue

            # 3. Replace the document from ReloadCollection to Current Collection.
                # To avoid the immutable _id error, we must remove the _id from the
                # replacement document. The original _id in CurrentCollection will be preserved.
                del json_new["_id"]
                CurrentCollection.replace_one({"id_ot": id_ot_value}, json_new)
                ReloadCollection.delete_one({"id_ot": id_ot_value})
                logging.info(f" [ MONGODB ] Successfully updated OT '{id_ot_value}' in MongoDB collection '{CurrentCollection.name}'.")

            # 4. Apply updates to Delta Lake
                updated_ot_doc = CurrentCollection.find_one({"id_ot": id_ot_value})
                obj_ot = OrdenTrabajo.GestionOt.from_v30(updated_ot_doc)
                new_activities_df = Actividades.ConvertirOT_a_ActividadesCSV(obj_ot)

                # The predicate must uniquely identify each row. For activities, this is
                # the combination of the work order ID and the item number.
                unique_key_predicate = "target.id_ot = source.id_ot AND target.Item = source.Item"

                # This merge operation will atomically update the activities for a given OT
                dt = DeltaTable(table_path)
                (dt.merge(
                    source=new_activities_df,
                    predicate=unique_key_predicate,
                    source_alias="source",
                    target_alias="target"
                )
                .when_matched_update_all()  # Rule 1: If an activity exists, update it.
                .when_not_matched_insert_all()  # Rule 2: If it's a new activity, insert it.
                .when_not_matched_by_source_delete(  # Rule 3: If an old activity is now gone...
                    predicate=f"target.id_ot = {id_ot_value}"  # ...delete it, but only for the current OT.
                )
                .execute())
                logging.info(f" [EXITO] DELTA LAKE Se ha actualizado la OT: '{id_ot_value}' en la tabla '{table_path}'")

            except Exception as e:
                logger.error(f"Fallo OT Recargada, al procesar el item {value}. Error: {e}")



# Apply a 5-second tumbling window to batch messages
sdf = sdf.tumbling_window(duration_ms=5000)

# The initializer for reduce receives the first value of the window
# and must return the initial state of the aggregate.
def initializer(first_value):
    logger.debug(f" > INIT: Initializing window with: {first_value}")
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
        print("\nLa aplicación se ha detenido manualmente.")
    finally:
        # Clean up resources, e.g., close DB connection
        if client:
            client.close()
            print("\nCerrada la conexion con MongoDB.\n\n")