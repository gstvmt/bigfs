# Entrega 1: BigFS Cliente/Servidor socket

## Comandos implementados

- cd -> (Change Directory) Muda o diretorio de referencia no servidor
- ls -> (List) Lista o conteudo presente no diretorio do servidor
- cp -> (Copy) Copia um ou mais arquivos do cliente para o servidor, o destino deve ser um diretorio. (Os arquivos copiados receberao o mesmo nome no servidor)
- get -> (Get) Baixa um ou mais arquivos presentes no servidor para o cliente.

## Organizacao do repositorio:

```
sd_bigfs
    ├── client
    │   ├── client.py               # implementacao do cliente
    │   └── client_ws               # espaco de arquivos do cliente - destino padrao do comando get
    │       ├── teste1.txt
    │       ├── teste2.txt
    │       └── teste3.txt
    ├── README.md
    └── server
        ├── home                    # sistema de arquivos remoto
        │   └── bigfs
        │       ├── teste1.txt
        │       ├── teste2.txt
        │       └── teste3.txt
        └── server.py               # implementacao do servidor
```

