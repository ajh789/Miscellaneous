Server stub for data acquisition program
========================================

Version of protobuf
-------------------

3.0.0

Data layout over socket
-----------------------

```
+-----------------------+
|      Magic number     |
| (4 bytes, 0xDEADBEEF) |
+-----------------------+
|     Payload length    |
|       (2 bytes)       |
+-----------------------+
|                       |
|        Payload        |
|   (protobuf message)  |
|                       |
+-----------------------+
```

Usage
-----

```
$ ./datacollector_server.py --ip=127.0.0.1 --format=json
127.0.0.1 json
Starting up on 127.0.0.1 port 10000
Waiting for a connection
Got Ctrl+C !
```
