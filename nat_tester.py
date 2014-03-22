#!/usr/bin/env python

__author__ = "Devin Kelly"

import zmq
import argparse
import socket
import time


def server():
   """remote server function, waits for UDP packet on dest port 12000, replies to src port
   :returns: None

   """
   timeouts = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 45, 60, 70, 80, 90, 100, 110, 120]
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   sock.bind(('', 12000))

   for t in timeouts:
      data, addr = sock.recvfrom(1024)
      print "received message:", data, ", from: ", addr
      time.sleep(t)
      sock.sendto("world! - {0}".format(t), addr)

   sock.close()


def client():
   """local client, initiates connection with remote server
   :returns: @todo

   """
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   sock.bind(('', 12001))

   while True:
      time.sleep(1)
      sock.sendto("hello", ("162.243.115.10", 12000))
      data, addr = sock.recvfrom(1024)
      print "received ", data, ", from: ", addr

   sock.close()


def main():
   parser = argparse.ArgumentParser(description="NAT Traversal Test")
   parser.add_argument("name", type=str, nargs=1,
                       help="Set the node name")

   args = parser.parse_args()

   f = {"server": server, "client": client}
   f[args.name[0]]()

   return

if __name__ == "__main__":
   main()
