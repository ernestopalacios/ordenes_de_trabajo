import sys
import os
import logging
import queue
import time

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
)
from datetime import datetime
from pathlib import Path
from dask.distributed import Client, LocalCluster, get_client

import json
from quixstreams import Application

from eerssa import gestionOT              # Convert from PDF_ot to obj_ot
from eerssa import procesarOt as OrdenTrabajo  # Version 0.3.0 
from eerssa import procesarActividades as Actividades      # process ot.data["actividades"]
from eerssa import organizar as gdrive    # download sheet from Google Drive

from eerssa import reporte_ot as reporte_pdf # Para generar el reporte del PDF
import typst

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# get the data table from Google Sheets
# If this is not possible, df_datos_cuadrilla will be just a 'Failed' String
df_datos_cudarilla = gdrive.get_gsheet_df() 

# Global timer to track the time since the last message was produced.
LAST_MESSAGE_TIMESTAMP = None
IS_FIRST_MESSAGE_SENT = False

# Kafka Topic Name with json format documents
KAFKA_JSON = "json_ot_v30"


# Dask Helper function to call the method on the result of a future
def call_load_ot(orden_trabajo_object):
    """
    Takes the result of the first task (an OrdenTrabajo object) 
    and calls the load_ot() method on it.
    """
    return (gestionOT.GestionOt.from_v30(orden_trabajo_object))


class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that appends created and modified files to a queue.
    """

    def __init__(self, client, KafkaApp):
        super().__init__()
        self.file_queue = queue.Queue()
        self.client = client               # DASK LocalClient
        self.KafkaApp = KafkaApp           # KAFKA Application

    def on_created(self, event):
        """
        Called when a file or directory is created.
        """
        if isinstance(event, FileCreatedEvent):
            self.file_queue.put(event.src_path)
            logging.debug(f"Nuevo archivo Creado:      '{event.src_path}'")

    def on_modified(self, event):
        """
        Called when a file or directory is modified.
        """
        if isinstance(event, FileModifiedEvent):
            self.file_queue.put(event.src_path)
            logging.debug(f"[*] Nuevo archivo Modificado: '{event.src_path}'")

    def get_queue(self):
        """
        Returns the queue of created and modified files.
        """
        return self.file_queue

    def process_all_items(self):
        """
        Removes and processes all items from the queue at once.
        """
        items_to_process = set()
        obj_lists = []

        while not self.file_queue.empty():
            item = self.file_queue.get_nowait()
            items_to_process.add(item)
            self.file_queue.task_done()

        items_to_process = list(items_to_process)

        # Filter only PDF files
        items_to_process = [
            file for file in items_to_process if file.lower().endswith(".pdf")
        ]

        start_time = time.time()
        start_datetime = datetime.now()

    # ===   PARALLEL PROCESING USING DASK  ========== #
        if len(items_to_process) >= 3:

            items_to_process = list(set(items_to_process))
            logger.info(
                f"   Procesando {len(items_to_process)} archivos. Hora de inicio: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            futures_step_1 = [
                self.client.submit(OrdenTrabajo.procesarOt, file, pure=False)
                for file in items_to_process
            ]

            futures_step_2 = [
                self.client.submit(call_load_ot, future)
                for future in futures_step_1
            ]

            futures_step_3 = [
                self.client.submit(Actividades.ConvertirOT_a_ActividadesCSV, future)
                for future in futures_step_2
            ]

            # Group the collections of futures you want to retrieve
            futures_to_gather = [futures_step_2, futures_step_3]

            # Call gather just ONCE
            # Dask will efficiently compute everything needed for both lists
            obj_lists, matriz_list = self.client.gather(futures_to_gather)

            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(
                f"   Procesados todos los {len(obj_lists)} items. Tiempo transcurrido: {elapsed_time:.2f} segundos.\n"
            )

            # Delete from Memory The proccessed Ot
            try:
                self.client.cancel([futures_step_1, futures_step_2, futures_step_3])
                logger.info(f"  [ DASK ] Se cancela la memoria de DASK ")
            except Exception as e:
                logger.warning(f"  [ DASK ] No se pudo borrar las 'futures' ")



    # ===   SINGLE THREAD PROCESING    ========== #

        elif len(items_to_process) > 0:
            logger.info(
                f"   Procesando {len(items_to_process)} archivos. Hora de inicio: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            obj_lists = []
            for file in items_to_process:
                ot = OrdenTrabajo.procesarOt(file)
                ot_obj = gestionOT.GestionOt.from_v30(ot)
                Actividades.ConvertirOT_a_ActividadesCSV(ot_obj)
                obj_lists.append(ot_obj)

            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(
                f"   Procesados todos los {len(obj_lists)} items. Tiempo transcurrido: {elapsed_time:.2f} segundos.\n"
            )

        




        # Once i got the list of objects I send to KAFKA only those that are VALID objects
        if obj_lists:
            with self.KafkaApp.get_producer() as producer:
                for ot in obj_lists:
                    if ot.valido:
                        # Aqui estoy reubicando el archivo.
                        nuevo_path = gdrive.renombrar_ot(
                                        ot.link,
                                        gdrive.get_nombre_archivo( ot, df_datos_cudarilla )
                        )

                        if nuevo_path != "Failed":
                          ot.link = nuevo_path
                          ot.data["link"] = nuevo_path
                        
                        #GENERACION DEL REPORTE
                        reporte_typst = reporte_pdf.create_typst_doc( ot )

                        if reporte_typst != "todo_ok":
                            with open("reporte_code.typ", mode="wt") as f:
                                f.write(reporte_typst.render())
                                logger.debug(" ::: Creado el archivo de reporte")
                            
                            if nuevo_path != "Failed":
                                report_filename = "REPORTE_"+os.path.basename(ot.link)
                                report_filename = os.path.join(os.path.dirname(ot.link),report_filename)
                            else:
                                report_filename = "REPORTE_"+os.path.basename(ot.link)
                                report_filename = os.path.join("ot_procesados",os.path.dirname(ot.link),report_filename)

                            logger.debug(f" ::: Se guardará en {report_filename}")
                            typst.compile("reporte_code.typ",  output= report_filename )

                        #SE ENVIAN LAS OT QUE SE ENCUENTRAN TERMINADAS Y SIN FALLAS
                        if ot.data["estado"] != "ECURSO" and ot.data["n_fatales"] == 0:
                            producer.produce(
                                topic=KAFKA_JSON,
                                key="Development",
                                value=json.dumps(ot.data),    
                            )
                            # Reset the global timer every time a message is produced
                            global LAST_MESSAGE_TIMESTAMP
                            global IS_FIRST_MESSAGE_SENT
                            LAST_MESSAGE_TIMESTAMP = time.time()
                            IS_FIRST_MESSAGE_SENT = True
                            logger.info(f"   [OK] > {os.path.basename(ot.link)} < se ha enviado a la base de datos")
                        else:
                            #TODO: Este mensaje lo deberia hacer conocer a Kafka como parte de la reporteria
                            logger.info(f"   [?]  > {os.path.basename(ot.link)} < REVISAR: No se ha enviado a la base de datos")    
                    else:
                        logger.info(f"   [X]  > {ot.link} < No es un archivo Orden de Trabajo")
                producer.flush()
            
            


def main(event_handler):
    """
    Monitors a directory for file creation and modification events.
    """
    while True:
        event_handler.process_all_items()
        # Check the elapsed time and act on it.
        global IS_FIRST_MESSAGE_SENT
        global LAST_MESSAGE_TIMESTAMP

        if IS_FIRST_MESSAGE_SENT and (time.time() - LAST_MESSAGE_TIMESTAMP > 5):
        #     logging.warning("No messages produced to 'json_ot' in the last 30 seconds.")
        #     # Reset timer to avoid repeated warnings, or maybe send a heartbeat message.
            logging.info(" <3 Es momento de enviar un HeartBeat han transcurrido 5 segundos desde la ultima vez que se envio un mensaje al Broker")
            LAST_MESSAGE_TIMESTAMP = time.time()
            IS_FIRST_MESSAGE_SENT = False
        
        time.sleep(1.5)


def get_or_create_DASK_client():
    """
    Checks if a Dask client is already running. If so, connects to it.
    Otherwise, creates a new LocalCluster and client.
    """
    try:
        # Try to get the default client (if one exists)
        client = get_client()
        logger.info("  [ DASK ]  Conectado a un cluster existente.")
        logger.info(f" [ DASK ]  Se puede encontrar el Dashboard en: {client.dashboard_link}")
        return client
    except ValueError:
        # No client exists, create a new LocalCluster and client
        logger.info("  [ DASK ]   Creando un nuevo cluster local.")
        cluster = LocalCluster()
        client = Client(cluster)
        logger.info(f" [ DASK ]  Se puede encontrar el Dashboard en: {client.dashboard_link}")
        return client


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Initialize the global timer when the script starts
    LAST_MESSAGE_TIMESTAMP = time.time()
        
    dask_client = get_or_create_DASK_client()

    KafkaApp = Application(
        broker_address="localhost:29092",
        loglevel="INFO"
    )


    event_handler = MyEventHandler(dask_client, KafkaApp)
    observer = Observer()


    print("\n   === Monitor de Ordenes de trabajo ====")

    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        print(
            "   Es necesario introducir el directorio (carpeta) donde se almacenarán las órdenes de trabajo"
        )
        base_dir = input("   Por favor, introduce el directorio: ")

    if not os.path.isdir(base_dir):
        print(f"   Error: > '{base_dir}' < no es un directorio válido.\n\n")
    else:
        print(
            f"   Se ha iniciado a monitorear el directorio:\n   ==>: '{base_dir}'\n"
        )



        # En caso de que existan Documentos PDF en el directorio, procesarlos primero,
        # antes de iniciar el monitor
        initial_pdfs = [str(p) for p in Path(base_dir).glob("*.pdf")]
        if initial_pdfs:
            print(
                f"   Se encontraron {len(initial_pdfs)} archivos PDF para procesar inicialmente."
            )
            for pdf_path in initial_pdfs:
                event_handler.file_queue.put(pdf_path)
 
        observer.schedule(event_handler, base_dir, recursive=False)
        observer.start()

        try:
            main(event_handler)
            while observer.is_alive():
                observer.join(1)
        except KeyboardInterrupt:
            print("\n   === Monitor de Ordenes de trabajo detenido ====\n\n")

        finally:
            observer.stop()
            observer.join()
            Client.close()
            Client.cluster.close()

            print("\n   === Fin del proceso ===\n")
