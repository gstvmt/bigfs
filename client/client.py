import socket
from pathlib import Path

class Client:

    def __init__(self, ip_server="localhost", port=65534):
        
        self.server_ip = ip_server
        self.server_port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_path = "home"
        self.download_path = Path("client_ws")
        self.last_cmd = ""

        self.msgs = {"cmd" : self.send_command, "msg" : self.receive_msg, "get" : self.receive_file, "lst" : self.receive_ls, "pth" : self.receive_path, "cpy": self.send_files}


    def connect(self):
        while True:
            self.socket.connect((self.server_ip, self.server_port))
            print("\nConexao Estabelecida com o Servidor")
            break

    def run(self):
        while True:
            try:
                msg_type = self.socket.recv(3).decode('utf-8')
                self.msgs.get(msg_type)()
            except KeyboardInterrupt:
                break
        print("Encerrando conexao com o servidor.")
        self.socket.close()

    def send_command(self):
        command = input(f"{self.server_path}$ ")
        self.socket.sendall(command.encode('utf-8'))
        self.last_cmd = command
    
    def receive_msg(self):
        size = int.from_bytes(self.socket.recv(4), 'big')
        data = self.socket.recv(size).decode("utf-8")
        print(data)
    
    def receive_path(self):
        size = int.from_bytes(self.socket.recv(4), 'big')
        data = self.socket.recv(size).decode("utf-8")
        self.server_path = data

    def receive_ls(self):
        quantidade = int.from_bytes(self.socket.recv(4), 'big')
        for i in range(quantidade):
            msg_type = self.socket.recv(3).decode('utf-8')
            size = int.from_bytes(self.socket.recv(4), 'big')
            data = self.socket.recv(size).decode('utf-8')
            if msg_type == 'err':
                print("Erro:" + data)
                return
            else:
               print("- " + data) 

    def receive_file(self):
        tamanho = int.from_bytes(self.socket.recv(4), 'big')
        nome_arq = self.socket.recv(tamanho).decode('utf-8')

        download_path = self.download_path / nome_arq
        with download_path.open('wb') as file:
            while True:
                msg_type = self.socket.recv(3).decode('utf-8')
                if msg_type == 'err':
                    size = int.from_bytes(self.socket.recv(4), 'big')
                    data = self.socket.recv(size)
                    print(f"Erro ao transferir o arquivo: {data}")
                    break
                elif msg_type == 'eof':
                    break
                else:
                    size = int.from_bytes(self.socket.recv(4), 'big')
                    buffer = self.socket.recv(size)
                    file.write(buffer)
    
    def send_files(self):
        try:
            files = self.last_cmd.split()[1:-1]
            for file in files:
                with open(file, 'rb') as f:
                    while True:
                        if self.socket.recv(3).decode("utf-8") != "ok!":
                            return
                        buffer = f.read(4096)
                        if not buffer:
                            self.socket.sendall(b"eof")
                            break
                        msg = b"cpy"
                        size = len(buffer).to_bytes(4, 'big')
                        self.socket.sendall(msg + size + buffer)

        except Exception as e:
            print(f"Client: Erro: {e}")

        

def main():
    client = Client()
    client.connect()
    client.run()


if __name__ == '__main__':
    main()