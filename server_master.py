'''
Esse arquivo busca implementar o servidor mestre do sistema de arquivos distribuido.
Ele sera responsavel por gerenciar os nos do sistema distribuido e os clientes.
'''

from pathlib import Path
import Pyro5.api
import hashlib
from uhashring import HashRing 
import base64

@Pyro5.api.expose
class ServerMaster():

    def __init__(self):
        # dicionario de workers
        self.workers = {}

        # hash ring para o balanceamento de carga entre os workers
        self.hash_ring = None
        
        # mapa de arquivos
        # TODO: substituir esse metodo por algo que suporte maiores cargas 
        #       (talvez um banco de dados local)
        self.files = {} #path : hash path
        self.files_map = {}  #hash path : worker_name

        # dicionario de usuarios
        self.users = {'admin': 'admin'}
        '''
            O caminho do usuario será --> /NFS/user_name
        '''
        self.load() # carrega os usuarios do servidor mestre

    def register_worker(self, name, uri):
        '''
        Registra um worker no servidor mestre.
        :param name: nome do worker
        :param uri: uri do worker
        '''
        proxy = Pyro5.api.Proxy(uri)
        
        self.workers[name] = proxy
        self.hash_ring = HashRing(list(self.workers.keys()))
        print(f"Worker {name} registrado com sucesso.")

    def register_user(self, user, password):
        '''
        Registra um usuario no servidor mestre.
        :param user: nome do usuario
        :param password: senha do usuario
        '''
        if user in self.users:
            raise Exception("Usuario ja existe")
        else:
            self.users[user] = password
            self.save_user(user, password)
            return "/NFS/" + user
        
    def login_user(self, user, password):
        '''
        Faz o login de um usuario no servidor mestre.
        :param user: nome do usuario
        :param password: senha do usuario
        '''
        if user in self.users and self.users[user] == password:
            return "/NFS/" + user
        else:
            raise Exception("Usuario ou senha invalidos")
        
    def save_user(self, user, password):
        '''
        Salva um usuario no servidor mestre.
        :param user: nome do usuario
        :param password: senha do usuario
        '''
        with open("user_table.txt", "a") as f:
            f.write(f"{user}:{password}\n")

    def load(self):
        '''
        Carrega os metadados do servidor.
        '''
        try:
            with open("user_table.txt", "r") as f:
                for line in f:
                    user, password = line.strip().split(":")
                    self.users[user] = password
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Erro ao carregar o arquivo de usuarios: {e}")
        
        try:
            with open("files.txt", "r") as f:
                for line in f:
                    path, hash = line.strip().split(":")
                    self.files[path] = hash
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Erro ao carregar o arquivo de usuarios: {e}")

        try:
            with open("files_map.txt", "r") as f:
                for line in f:
                    hash, worker_name = line.strip().split(":")
                    self.files_map[hash] = worker_name
            self.hash_ring = HashRing(nodes=list(self.workers.keys()), replicas=3)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Erro ao carregar o arquivo de usuarios: {e}")

    def ls(self, path, user):
        '''
        Lista os arquivos e diretorios de um caminho.
        :param path: caminho a ser listado
        '''
        try:
            ret_set = set()
            path = Path(path)

            # verifica se o caminho esta no formato correto
            if not path.is_absolute():
                path = Path(f"/NFS/{user}") / path

            p_string = str(path)

            for p in self.files.keys():
                if p.startswith(p_string):
                    ret_set.add(Path(p).relative_to(path).parts[0])

            return ret_set
        except Exception as e:
            raise e
        
    def cp_from(self, path, user):
        '''
        Copia um arquivo de um cliente para um worker.
        :param path: caminho do arquivo de destino
        '''
        try:
            # verifica se o caminho esta no formato correto
            path = Path(path)
            if not path.is_absolute():
                path = Path(f"/NFS/{user}") / path

            p_string = str(path)

            # verifica se o arquivo nao existe
            if p_string not in self.files.keys():
                hash = hashlib.sha256(p_string.encode()).hexdigest()
                self.files[p_string] = hash
                self.files_map[hash] = self.hash_ring.get_node(hash)
                self.save_file()

            path_hash = self.files[p_string]
            worker_name = self.files_map[path_hash]
            worker = self.workers[worker_name]
            worker._pyroClaimOwnership()
            index = worker.open_file(path_hash, "wb")
            endpoint = (index, worker_name) # indice do arquivo aberto no worker e o nome do worker
            return endpoint

        except Exception as e:
            raise e
        
    def receive_chunk(self, chunk, endpoint):
        '''
        Recebe um chunk de um arquivo.
        :param chunk: chunk a ser recebido
        :param index: indice do arquivo
        '''
        try:
            worker = self.workers[endpoint[1]]
            eof = worker.write_chunk(chunk, endpoint[0])
            return eof
        except Exception as e:
            raise e
        
    def cp_to(self, path, user):
        '''
        Copia um arquivo do worker para o cliente
        :param path: caminho do arquivo de origem
        '''
        try:
            # verifica se o caminho esta no formato correto
            path = Path(path)
            if not path.is_absolute():
                path = Path(f"/NFS/{user}") / path

            p_string = str(path)

            # verifica se o arquivo existe
            if p_string not in self.files.keys():
                raise Exception("Arquivo nao encontrado")

            hash = self.files[p_string]
            worker_name = self.files_map[hash]
            worker = self.workers[worker_name]
            worker._pyroClaimOwnership()
            index = worker.open_file(hash, "rb")
            endpoint = (index, worker_name) # indice do arquivo aberto no worker e o nome do worker
            return endpoint

        except Exception as e:
            raise e
        
    def send_chunk(self, endpoint):
        '''
        Envia um chunk de um arquivo.
        :param index: indice do arquivo
        '''
        try:
            worker = self.workers[endpoint[1]]
            for chunk in worker.read_chunks(endpoint[0]):
                yield chunk
        except Exception as e:
            raise e
        
    def rm(self, paths, user):
        '''
        Remove um arquivo do servidor mestre.
        :param path: caminho do arquivo a ser removido
        '''
        try:
            for path in paths:
                path = Path(path)
                if not path.is_absolute():
                    path = Path(f"/NFS/{user}") / path

                p_string = str(path)

                # verifica se o arquivo existe
                if p_string not in self.files.keys():
                    raise Exception("Arquivo nao encontrado")

                hash = self.files[p_string]
                worker_name = self.files_map[hash]
                self.workers[worker_name].rm(hash)
                del self.files[p_string]
                del self.files_map[hash]
                self.save_file()

                return True
        
        except Exception as e:
            raise e
        
    def save_file(self):
        '''
        Salva o arquivo de arquivos do servidor mestre.
        '''
        try:
            with open("files.txt", "w") as f:
                for key, value in self.files.items():
                    f.write(f"{key}:{value}\n")

            with open("files_map.txt", "w") as f:
                for key, value in self.files_map.items():
                    f.write(f"{key}:{value}\n")

        except Exception as e:
            print(f"Erro ao salvar o arquivo de arquivos: {e}")
        
def main():
    daemon = Pyro5.server.Daemon()         # make a Pyro daemon
    ns = Pyro5.api.locate_ns()       # find the name server
    server = ServerMaster()             
    uri = daemon.register(server)   # register the greeting maker as a Pyro object
    ns.register("fs_server", uri)   # register the object with a name in the name server

    print("Ready.")
    daemon.requestLoop() 

if __name__ == "__main__":
    main()