import json
from quixstreams import Application, State
from quixstreams.models.serializers import JSONSerializer
from quixstreams.models.rows import Row
import time
import logging
from eerssa.secret import Keys
import pymongo


logging.basicConfig(level=logging.INFO)


uri = Keys.MONGO_KEY.value
client = pymongo.MongoClient( uri )

# Ping para confirmar que se ha establecido la conexion
try:
    client.admin.command('ping')
    db_eerssa = client.eerssa               # Base de datos EERSSA
    CurrentCollection = db_eerssa.ot_v22    # Coleccion actual
    logging.info(":::: Conexion exitosa con MongoDB ::::")
except Exception as e:
    logging.error(f"\n\n ><><> Error de conexion a MongoDB: {e}") # More specific error message

# Quix Stream app cnfiguration

app = Application(
    broker_address="localhost:29092",
    consumer_group="my-group",
    auto_create_topics=True,
    auto_offset_reset="earliest"
)

topic = app.topic( "json_ot", value_serializer = JSONSerializer() )
sdf = app.dataframe(topic)

def process_row(row: Row):
    """
    Processes a single message (Row) from the Kafka topic.
    Converts the Row value to a dictionary and logs the 'ot_id'.
    """
    try:
        
        ot = row
        ot_id = ot["id_ot"]
        logging.info(f"\n ~~~ (1) Recibido el mensaje Orden de Trabajo con ID: {ot_id}")

        # Check if there already exist a document in CurrentCollection with the same `id_ot`
        if CurrentCollection.find_one({"id_ot": ot_id}):
            pass
        else:
            #upload the ot to the CurrentCollection
            CurrentCollection.insert_one(ot)
            logging.info(f"\n ~~~ (2) Guardado en MongoDB Orden de Trabajo con ID: {ot_id}")

        # Add your processing logic here
    except Exception as e:
        logging.info(f"No se ha podido procesar el mensaje:\n>| {row} |<")
        logging.error(f"\n\nError: {e}")
    
    






sdf = sdf.apply(process_row)

# Define a function to run the application (good practice)
def run_app():
    """Starts the Quix Streams application."""
    print("\n\n = = = =   Iniciando CONSUMIDOR [Quix Streams application] ...  = = = =")
    app.run(sdf)
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
