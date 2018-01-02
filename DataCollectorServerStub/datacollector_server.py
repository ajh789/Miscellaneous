#!/usr/bin/python3

import os
import re
import sys
import fcntl
import getopt
import signal
import socket
import struct
import binascii
import threading

import cnc_pb2
from google.protobuf import json_format

# Thread safe file for stdour & stderr
#import tsf

gKeyboardInterrupt = False
gBinBuffer = b''

class ConnThread(threading.Thread):
  def __init__(self, conn, addr, dfmt):
    super(ConnThread, self).__init__()
    self.conn = conn
    self.addr = addr
    self.dfmt = dfmt
  def run(self):
    global gKeyboardInterrupt
    global gBinBuffer
    file = self.conn.makefile('rwb', buffering=0)
    try:
      while not gKeyboardInterrupt:
        data = ''
        if self.dfmt == 'json':
          data = nonBlockingReadLine(file)
        else:
          data = nonBlockingRead(file, -1) # Read till EOF. ONLY works in Python3!!!
        if data:
          if self.dfmt == 'json':
            print('Received: %s' % data.rstrip())
          else:
            print('Raw data:')
            print(binascii.hexlify(data))
            gBinBuffer = b''.join([gBinBuffer, data])
            print('Buffer len: ', len(gBinBuffer))
#           self.conn.sendall(data)
            if len(gBinBuffer)>6:
              (ok, rawlen, msglen) = decodeAndParse(gBinBuffer)
              if ok:
                gBinBuffer = gBinBuffer[rawlen:] # Remove full msg encapsulation
#           print repr(buffer[0])
#           print ' '.join(x.encode('hex') for x in data)
        else:
          pass
#         print('No more data from', self.addr, file=sys.stderr)
#         break
      print('Exit thread loop!')
    finally:
      file.close()
      self.conn.close()

def decodeAndParse(binBuff):
  header = struct.unpack("IH", binBuff[:6])
  magic  = socket.ntohl(header[0])
  msglen = socket.ntohs(header[1])
  rawlen = 4+2+msglen # 4 bytes magic number + 2 bytes msg len + msg content
  if (magic == 0xdeadbeef) and (len(binBuff) >= rawlen):
    print('+-----------------------------------+')
    print('|   See a full msg encapsulation!   |')
    print('+-----------------------------------+')
    print('Msg len: %d' % (msglen,))
    msg = cnc_pb2.CncMsg()
    msg.ParseFromString(binBuff[6:rawlen]) # [start:stop:step]
    print('JSON data:')
    print(json_format.MessageToJson(msg).replace('\n', '').replace('\r', '').replace(' ', ''), '\n')
    return (True, rawlen, msglen)
  else:
    return (False, 0, 0)

def nonBlockingReadLine(stream):
  fd = stream.fileno()
  fl = fcntl.fcntl(fd, fcntl.F_GETFL)
  fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
  try:
    return stream.readline()
  except:
    return ''

def nonBlockingRead(stream, size):
  fd = stream.fileno()
  fl = fcntl.fcntl(fd, fcntl.F_GETFL)
  fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
  try:
    return stream.read(size)
  except:
    return ''

def usage():
  pass
  print(sys.argv[0], '''
  -h|--help, show usage
  -a|--ip, set server ip address
  -n|--port, set server port number
  -f|--format, set data format
  ''')

def parseOpt(optstr):
  ret, ip, port, dfmt = True, 'localhost', 10000, 'json'
  try:
    opts, args = getopt.getopt(optstr, "ha:n:f:", ["help", "ip=", "port=", "format="])
  except getopt.GetoptError as err:
    print(str(err))

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      usage()
    elif opt in ('-a', '--ip'):
      ip = arg
      if not re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ip):
        print('Invalid IP address: %s' % (ip,), file=sys.stderr)
        ret = False
    elif opt in ('-n', '--port'):
      try:
        port = int(arg)
      except ValueError:
        print('Invalid port "%s", default to 10000.' % arg, file=sys.stderr)
    elif opt in ('-f', '--format'):
      dfmt = arg
      if dfmt not in ('json', 'protobuf'):
        print('Format should be "json" or "protobuf".')
        ret = False
    else:
      assert False, 'unhandled option'
    
  return (ret, ip, port, dfmt)


def main():
  (ret, ip, port, dfmt) = parseOpt(sys.argv[1:])

  print('server=%s:%d\tformat=%s' % (ip, port, dfmt))

  global gKeyboardInterrupt

  # Create a TCP socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverName = ip if len(ip)>1 else 'localhost'
  serverAddr = (serverName, port) if port else (serverName, 10000)
  print('Starting up on %s port %s' % serverAddr, file=sys.stderr)
  sock.bind(serverAddr)
  sock.listen(1) # Listen for incoming connections
  while not gKeyboardInterrupt:
    print('Waiting for a connection', file=sys.stderr)
    conn, clientAddr = sock.accept()
    print('Connection from', clientAddr, file=sys.stderr)
    ConnThread(conn, clientAddr, dfmt).start()

def signalHandler(signal, frame):
  global gKeyboardInterrupt
  print('Got Ctrl+C !')
  gKeyboardInterrupt = True
  sys.exit(1)

if __name__ == '__main__':
  signal.signal(signal.SIGINT, signalHandler)
  main()
