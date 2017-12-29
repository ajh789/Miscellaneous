#/bin/bash -

protoc -I=. --cpp_out=./ ./cnc.proto
protoc -I=. --python_out=./ ./cnc.proto
