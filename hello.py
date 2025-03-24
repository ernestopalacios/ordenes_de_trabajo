import sys
import os.path
import logging
import queue
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
)
import time
from datetime import datetime

from eerssa import gestionOT
from pathlib import Path

from dask.distributed import Client, LocalCluster, get_client


import json
from quixstreams import Application


class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that appends created and modified files to a queue.
    """

    def __init__(self, client, KafkaApp):
        super().__init__()
        self.file_queue = queue.Queue()
        self.client = client  # DASK LocalClient
        self.KafkaApp = KafkaApp  # KAFKA Application

    def on_created(self, event):
        """
        Called when a file or directory is created.
        """
        if isinstance(event, FileCreatedEvent):
            self.file_queue.put(event.src_path)
            logging.info(f"File created: {event.src_path}")

    def on_modified(self, event):
        """
        Called when a file or directory is modified.
        """
        if isinstance(event, FileModifiedEvent):
            self.file_queue.put(event.src_path)
            logging.info(f"File modified: {event.src_path}")

    def get_queue(self):
        """
        Returns the queue of created and modified files.
        """
        return self.file_queue

    def process_all_items(self):
        """
        Removes and processes all items from the queue at once.
        """
        items_to_process = []
        obj_lists = []

        while not self.file_queue.empty():
            item = self.file_queue.get_nowait()
            items_to_process.append(item)
            self.file_queue.task_done()

        # Filter only PDF files
        items_to_process = [
            file for file in items_to_process if file.lower().endswith(".pdf")
        ]

        start_time = time.time()
        start_datetime = datetime.now()

        # For more than eight elements process them using DASAK Distributed Computing
        if len(items_to_process) > 8:
            print(
                f"   Procesando {len(items_to_process)} archivos. Hora de inicio: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            items_to_process = list(set(items_to_process))

            futures = [
                self.client.submit(gestionOT.GestionOt, file)
                for file in items_to_process
            ]
            ot_array = [future.result() for future in futures]
            ot_cargada = [ot.load_ot() for ot in ot_array]
            obj_lists = [ot for ot in ot_cargada]

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(
                f"   Procesados todos los {len(obj_lists)} items. Tiempo transcurrido: {elapsed_time:.2f} segundos.\n"
            )

        # Maybe we could only use DASK, but I'll leave this code if I encounter errors with DASK in the future
        elif len(items_to_process) > 0:
            print(
                f"   Procesando {len(items_to_process)} archivos. Hora de inicio: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            obj_lists = []
            for file in items_to_process:
                ot = gestionOT.GestionOt(file)
                ot.load_ot()
                obj_lists.append(ot)

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(
                f"   Procesados todos los {len(obj_lists)} items. Tiempo transcurrido: {elapsed_time:.2f} segundos.\n"
            )

        # Once i got the list of objects I send to KAFKA only those that are VALID objects
        if obj_lists:
            with self.KafkaApp.get_producer() as producer:
                
                for ot in obj_lists:
                    if ot.valido:
                        print(
                            f"   [OK] > {ot.link} < se ha enviado a la base de datos"
                        )
                        producer.produce(
                            topic="json_ot",
                            key="Development",
                            value=json.dumps(ot.data),
                            
                        )
                    else:
                        print(
                            f"   [x]  > {ot.link} < No es un archivo Orden de Trabajo"
                        )
                producer.flush()


def main(event_handler):
    """
    Monitors a directory for file creation and modification events.
    """
    while True:
        event_handler.process_all_items()
        time.sleep(0.5)


def get_or_create_client():
    """
    Checks if a Dask client is already running. If so, connects to it.
    Otherwise, creates a new LocalCluster and client.
    """
    try:
        # Try to get the default client (if one exists)
        client = get_client()
        print("   Conectado a un cluster existente.")
        return client
    except ValueError:
        # No client exists, create a new LocalCluster and client
        print("   Creando un nuevo cluster local.")
        cluster = LocalCluster()
        client = Client(cluster)
        return client


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get or create the Dask client
    client = get_or_create_client()

    # Object creation
    KafkaApp = Application(
        broker_address="localhost:29092",
        loglevel="DEBUG",
    )

    # Watchdog configuration
    event_handler = MyEventHandler(client, KafkaApp)
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
            client.close()
            client.cluster.close()

            print("\n   === Fin del proceso ===\n")
