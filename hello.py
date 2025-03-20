import sys
import os.path

import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent




class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that appends created and modified files to a list.
    """

    def __init__(self):
        super().__init__()
        self.file_list = []

    def on_created(self, event):
        """
        Called when a file or directory is created.
        """
        if isinstance(event, FileCreatedEvent):
            self.file_list.append(event.src_path)
            logging.info(f"File created: {event.src_path}")

    def on_modified(self, event):
        """
        Called when a file or directory is modified.
        """
        if isinstance(event, FileModifiedEvent):
            self.file_list.append(event.src_path)
            logging.info(f"File modified: {event.src_path}")

    def get_file_list(self):
        """
        Returns the list of created and modified files.
        """
        return self.file_list


def main():
    """
    Monitors a directory for file creation and modification events.
    """
    return

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    # Object creation
    event_handler = MyEventHandler()
    observer = Observer()

    
    print("\n   === Monitor de Ordenes de trabajo ====")



    if len(sys.argv) > 1:
        # if there is an argument 
        base_dir = sys.argv[1]       
    else:
        print(  "   Es necesario introducir el directorio (carpeta) donde se almacenarán las órdenes de trabajo")
        base_dir = input("   Por favor, introduce el directorio: ")

    #Validate the directory
    if os.path.isdir(base_dir):
        print(f"   Se ha iniciado a monitorear el directorio: \n   ==>: '{base_dir}'\n")

        observer.schedule(event_handler, base_dir, recursive=False)  # recursive False, only monitor base directory
        observer.start()
        try:
            while observer.is_alive():
                observer.join(1)
        except KeyboardInterrupt:
            print("\n   === Monitor de Ordenes de trabajo detenido ====\n\n")
        finally:
            observer.stop()
            observer.join()
            
            # Print the list of files after the observer has stopped
            print("\n   === Lista de archivos creados o modificados ===")
            for file_path in event_handler.get_file_list():
                print(f"   - {file_path}")
            print("\n")
    else:
            print(f"   Error: > '{base_dir}' < no es un directorio válido.\n\n")

    
    main()
