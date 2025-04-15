# server class
# adicionar multithreading para o servidor
from pathlib import Path
import socket
import threading

stop = threading.Event()

class MainServer:
    def __init__(self, ip='localhost', port = 65534):
        
        self.ip = ip #utilizar o localhost como padrao
        self.port = port #definir uma por padrao tambem
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # socket do servidor

        # self.conection = socket.socket()
        # self.client_ip = ''
        self.server_threads = []

        self.socket.bind((self.ip, self.port)) # faz o bind do ip e porta

    def server_wait(self): #espera por uma conexao
        while True:
            try:
                self.socket.listen(1) # espera pelo cliente
                connection, client_ip = self.socket.accept() #estabelece a conexao
                thread = TaskServer(connection=connection, client_ip=client_ip)
                self.server_threads.append(thread)
                print(f"Conexao estabelecida com sucesso | cliente_ip:{client_ip}")
                break
            except KeyboardInterrupt:
                print("Closing Server")
                stop.set()
                map(lambda thr : thr.join(), self.server_threads)
                self.socket.close()
                break
            except Exception as e:
                print(f"Nao foi possivel conectar ao client: {e}")


class TaskServer(threading.Thread):
    def __init__(self, connection, client_ip, group = None, name = None, args = ..., kwargs = None, *, daemon = None):
        
        super().__init__(group, name, args, kwargs, daemon=daemon) # parametros da superclasse thread
        
        self.connection = connection  # socket com a conexao ao cliente
        self.client_ip = client_ip 
        self.comandos = {'cd' : self.cd, 'ls' : self.ls, 'rm' : self.rm, 'get' : self.get, 'cp' : self.cp}

        self.root_path = "./home"
        self.current_path = Path(self.root_path)
        self.client_path = Path('/home')

        self.start()


    def run(self):

        while not stop.is_set():
            # envia mensagem indicando que esta esperando a conexao
            msg = b'cmd'
            self.connection.sendall(msg)
            # recebe o comando e extrai o comando
            msg = self.connection.recv(1024)
            if not msg : break
            cmd = self.get_cmd(msg)
            # processa o comando 
            self.comandos.get(cmd.get('cmd'))(cmd.get('flags'), cmd.get('args'))
        
        print(f"Encerrando a conexao com o cliente {self.client_ip}")
        self.connection.close()
            

    def get_cmd(self, msg):
        # vou seguir a forma do shell -> comando -flag args
        string = msg.decode()
        command = string.split()
        cmd = command[0]
        flags = []
        args = []
        for item in command[1:]:
            if item.startswith('-'):
                flags.append(item[1:])
            else:
                args.append(item)
        command = {'cmd': cmd, 'flags': flags, 'args': args}
        return command
    
    def cd(self, flags, args):

        self.send_msg('Este comando nao suporta flags, todas as flags serao desconsideradas.') if len(flags) != 0 else None
        if len(args) > 1:
            self.send_msg('Este comando suporta apenas um argumento. digite (help comando) para saber mais.')
            return
        
        if len(args) == 0:
            self.current_path = Path(self.root_path)
            self.client_path = str(self.current_path)
            self.send_path(self.client_path)
            return
        
        tmp_path = self.current_path / args[0] if not Path(args[0]).is_absolute() else Path(("." + args[0]))

        if tmp_path.exists():

            if str(tmp_path).endswith('..'):
                tmp_path = self.current_path.parent

            self.current_path = tmp_path
            self.client_path = str(self.current_path)
            self.send_path(self.client_path)
        
        else:
            self.send_msg(f'Arquivo ou diretorio inexistente -> {tmp_path}')


    def ls(self, flags, args):
        
        if len(args) > 1:
            self.send_msg('Este comando suporta apenas um argumento. digite (help comando) para saber mais.')
            return
        elif len(args) == 0:  
            self.send_ls(list(self.current_path.iterdir()))
        else:
            tmp_path = self.current_path / args[0]
            if tmp_path.exists():
                self.send_ls(list(tmp_path.iterdir()))
            else: 
                self.send_msg(f'Arquivo ou diretorio inexistente -> {tmp_path}')

    
    def rm(self, flags, args):
        
        for p in args:
            if p.endswith('*'):
                tmp_path = self.current_path / p[:-1]
                if tmp_path.exists():
                    for file in tmp_path.iterdir():
                        aux = tmp_path / file.name
                        aux.unlink() if aux.is_file() else self.send_msg(f'Nao é possivel remover um diretorio -> {aux}')
                else:
                    self.send_msg(f"Arquivo ou diretorio inexistente -> {tmp_path}")
            else:
                tmp_path = self.current_path / p
                tmp_path.unlink() if tmp_path.exists() else self.send_msg(f"Arquivo ou diretorio inexistente -> {tmp_path}")

    def get(self, flags, args):

        for p in args:
            tmp_path = self.current_path / p
            if tmp_path.exists():
                self.send_file(tmp_path)
            else:
                self.send_msg(f"Arquivo ou diretorio inexistente -> {tmp_path}") 

    def cp(self, flags, args):
        try:
            command = b"cpy"
            self.connection.sendall(command)

            target = args[-1]
            path = self.current_path / target if not Path(target).is_absolute() else Path(("." + target)) 
            for file in args[:-1]:
                file_name = Path(file).name
                aux = path / file_name
                with aux.open("wb") as file:
                    while True:
                        self.connection.sendall(b"ok!")
                        msg = self.connection.recv(3).decode("utf-8")
                        if msg == 'eof':
                            break
                        size = int.from_bytes(self.connection.recv(4), 'big')
                        buffer = self.connection.recv(size)
                        file.write(buffer)
        
        except Exception as e:
            self.connection.sendall("err")
            self.send_msg(f"Erro ao copiar um arquivo: {e}")
        
    def send_msg(self, text): # mensagens que devem ser printadas no terminal do cliente
        msg_type = b'msg'
        size = len(text).to_bytes(4, 'big')
        t = text.encode('utf-8')
        self.connection.sendall(msg_type + size + t)

    def send_file(self, path): # resposta ao comando get
        try:
            msg_type = b'get'
            file_name = path.name
            file_name_size = len(file_name).to_bytes(4, 'big')
            self.connection.sendall(msg_type + file_name_size + file_name.encode('utf-8'))
            with path.open('rb') as file:
                while True:
                    buffer = file.read(4096)
                    buf_size = len(buffer).to_bytes(4, 'big')
                    if not buffer:
                        msg_type = b'eof'
                        self.connection.sendall(msg_type)
                        break
                    self.connection.sendall(msg_type + buf_size + buffer)
        
        except Exception:
            msg_type = b'err'
            msg = f"{Exception}".encode('utf-8')
            size = len(msg).to_bytes(4, 'big')
            self.connection.sendall(msg_type + size + msg)


    def send_ls(self, items_list): # ls command output
        try:  
            msg_type = b"lst"
            quantidade = len(items_list).to_bytes(4, "big")
            self.connection.sendall(msg_type + quantidade)
            for item in items_list:
                msg_type = b'lst'
                size = len(str(item.name)).to_bytes(4, 'big')
                self.connection.sendall(msg_type + size + str(item.name).encode('utf-8'))
        except Exception as e:
            msg_type = b'err'
            msg = f"{e}".encode('utf-8')
            size = len(msg).to_bytes(4, 'big')
            self.connection.sendall(msg_type + size + msg)
            

    def send_path(self, path): # atualiza o shell mostrado no terminal do cliente
        path = str(path)
        msg_type = b"pth" # 3 bytes
        size = len(path).to_bytes(4, 'big') # enviando um valor numerico de 4 bytes em big endian que representa o tamanho da mensagem a ser enviada
        p = path.encode("utf-8")
        self.connection.sendall(msg_type + size + p)
        
        
def main():
    server = MainServer()
    server.server_wait()


if __name__ == '__main__':
    main()
