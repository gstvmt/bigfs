import Pyro5.api
import socket
from threading import Lock
import base64
import os

@Pyro5.api.expose
class Worker:

    def __init__(self):
        self.opened_files = []
        self.lock = Lock()

        self.file_space_path= "data/"  # Local directory for file storage
        if not os.path.exists(self.file_space_path):
            os.makedirs(self.file_space_path)
    
    def open_file(self, hash, mode):
        """
        Open a file in the local file space.
        :param hash: The hash of the file to open.
        :param mode: The mode in which to open the file (e.g., 'rb', 'wb').
        :return: The opened file object.
        """
        try:
            with self.lock:
                file = open(f"{self.file_space_path}{hash}", mode)
                self.opened_files.append(file)
                index = len(self.opened_files) - 1
                return index
        except Exception as e:
            raise e
        
    def write_chunk(self, chunk, index):
        """
        Write a chunk of data to the opened file.
        :param chunk: The chunk of data to write.
        :param index: The index of the opened file.
        :return: True if EOF, False otherwise.
        """
        try:
            chunk = base64.b64decode(chunk.get("data"))
            with self.lock:
                file = self.opened_files[index]
                if not chunk:
                    file.close()
                    self.opened_files.pop(index)
                    return True
                
                file.write(chunk)
                return False
        except Exception as e:
            raise e
        
    def read_chunks(self, index):
        """
        Read data chunks from the opened file.
        :param index: The index of the opened file.
        :return: The chunk of data read from the file.
        """
        try:
            with self.lock:
                file = self.opened_files[index]
                while True:
                    chunk = file.read(1024*64)
                    if not chunk:
                        file.close()
                        self.opened_files.pop(index)
                        break
                    yield chunk
                
        except Exception as e:
            raise e
        
    def rm(self, hash):
        """
        Remove a file from the local file space.
        :param hash: The hash of the file to remove.
        """
        try:
            with self.lock:
                file_path = f"{self.file_space_path}{hash}"
                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    raise Exception("File not found")
        except Exception as e:
            raise e
        
        
       

def main():
    nome = f"worker_{socket.gethostname()}"
    daemon = Pyro5.server.Daemon()
    w = Worker()
    uri = daemon.register(w)

    ns = Pyro5.api.locate_ns(host="192.168.1.4", port=9090)
    server_uri = ns.lookup("fs_server")
    server = Pyro5.api.Proxy(server_uri)
    server.register_worker(nome, uri)

    print(f"Worker {nome} iniciado.")
    daemon.requestLoop()

if __name__ == "__main__":
    main()
