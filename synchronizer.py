#!/usr/bin/env python

__author__ = "Devin Kelly"

import argparse
import os
import threading
import json
import socket
import time
import copy
import sys
import select


def parseArgs():
   """@todo: Docstring for parseArgs.
   :returns: parsed arguments as an argparse object

   """

   parser = argparse.ArgumentParser(description="Syncronize Note Databases")
   parser.add_argument("name", type=str, nargs=1,
                       help="Set the node name")
   parser.add_argument("--config", "-c", type=str, nargs=1,
                       default=os.path.expanduser("~/.note.conf"),
                       help="Set the path to the config file")

   return parser.parse_args()


def getConfig(filepath):
   """returns a json object from the given config file

   :filepath: Path to config file
   :returns: Json object

   """
   with open(filepath, 'r') as fd:
      config = json.loads(fd.read())

   return config


class Beaconer(threading.Thread):
   def __init__(self, helloInterval, config, activeNeighbors, nodeName, lock):
      threading.Thread.__init__(self)
      self.daemon = True
      self.helloInterval = helloInterval
      self.nodeName = nodeName
      self.lock = lock
      self.activeNeighbors = activeNeighbors
      helloDict = {"NOTEMSG": "HELLO",
                   "FROM": self.nodeName,
                   "DATE": time.time()}
      self.helloMessage = json.dumps(helloDict)
      self.config = copy.deepcopy(config)

      # Extract the dict for the localNode and then delete it from the neighor
      # list.
      for ind, item in enumerate(self.config['neighbors']):
         if item['name'] == self.nodeName:
            self.localNode = copy.deepcopy(item)
            break
      del self.config['neighbors'][ind]

      self.setupSocket()

   def run(self):
      self.lastSocketCall = time.time()
      timeout = self.helloInterval

      while True:

         read, write, exc = select.select([self.sock], [], [], timeout)

         if read:
            [self.readSocket(s) for s in read]
            timeout = self.helloInterval - (time.time() - self.lastSocketCall )
         else:
            self.writeSocket(self.sock)
            self.lastSocketCall = time.time()
            timeout = self.helloInterval

   def processSockets(self):
      """ Reads the socket and sends out the beacon
      :returns: @todo

      """

      # set the timeout
      timeout = self.helloInterval - (time.time() - self.lastSocketCall)
      if timeout < 0.0:
         timeout = 0.0

      read, write, exc = select.select([self.sock], [], [], timeout)

      [self.readSocket(s) for s in read]
      self.writeSocket(self.sock)

      self.lastSocketCall = time.time()

   def writeSocket(self, sock):
      """Send a beacon from the given socket

      :sock: A socket object
      """

      for neigh in self.config['neighbors']:
         sock.sendto(self.helloMessage,
                     (neigh['address'], self.config['port']))

   def readSocket(self, sock):
      """Get the message from the socket and call adNeighbor

      :sock: A socket object
      """
      (message, senderAddr) = sock.recvfrom(2048)

      msg = json.loads(message)

      self.addNeighbor(msg)

      # TODO keep this as debug for now, remove later
      print "{0} from {1}".format(msg['NOTEMSG'], msg['FROM'])

   def addNeighbor(self, neighborMsg):
      """@todo: Docstring for addNeighbor.

      :neighbor: @todo
      :returns: @todo

      """
      neighborName = neighborMsg['FROM']
      sentTime = neighborMsg['DATE']
      receiveTime = time.time()
      with self.lock:
         self.activeNeighbors[neighborName] = {"sentTime": sentTime,
                                               "receivedTime": receiveTime}

   def setupSocket(self):

      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.sock.bind(('', self.config['port']))
      self.sockFD = self.sock.fileno()

      self.sock.setblocking(0)


class NeighborReaper(threading.Thread):

   def __init__(self, checkInterval, reapInterval, activeNeighbors, lock):

      threading.Thread.__init__(self)
      self.reapInterval = reapInterval
      self.checkInterval = checkInterval
      self.activeNeighbors = activeNeighbors
      self.lock = lock

   def run(self):

      while True:
         startTime = time.time()
         activeNeighborsKeys = self.activeNeighbors.keys()

         with self.lock:
            for neigh in activeNeighborsKeys:
               delay = startTime - self.activeNeighbors[neigh]['receivedTime']
               if delay > self.reapInterval:
                  print 'reaping {0}'.format(neigh)
                  del self.activeNeighbors[neigh]

         endTime = time.time()
         timeWaited = self.checkInterval - (endTime - startTime)
         if timeWaited < 0.0:
            timeWaited = 0.0
         time.sleep(timeWaited)


class NeighborManager(threading.Thread):
   """Find Note Neighber and keep track of them as they come and go"""

   def __init__(self, threadName, nodeName, config):
      """Initialize NeighborManager """
      threading.Thread.__init__(self)
      self.threadName = threadName
      self.nodeName = nodeName
      self.helloInterval = 3.0  # 30.0  # seconds
      self.reapCheck = 5.0
      self.reapTimeout = 15.0
      self.config = config
      self.activeNeighbors = {}
      self.threads = []

      self.neighborLock = threading.Lock()

      self.sender = Beaconer(self.helloInterval,
                             self.config,
                             self.activeNeighbors,
                             self.nodeName,
                             self.neighborLock)
      self.sender.setDaemon(True)

      self.threads.append(self.sender)

      self.reaper = NeighborReaper(self.reapCheck,
                                   self.reapTimeout,
                                   self.activeNeighbors,
                                   self.neighborLock)
      self.reaper.setDaemon(True)
      self.threads.append(self.reaper)

   def startThreads(self):
      """Start the beacon sender, receiver, time threads
      :returns: @todo

      """

      [t.start() for t in self.threads]

      while True:
         try:
            [t.join(1) for t in self.threads]
         except KeyboardInterrupt:
            print "Exiting"
            sys.exit(1)

   def getNeighbors(self):
      with self.neighborLock:
         neighbors = copy.deepcopy(self.activeNeighbors)
      return neighbors


class NoteSynchronizer(threading.Thread):

   def __init__(self, neighborManager):

      self.neighborManager = neighborManager

   def run(self):

      neighbors = self.neighborManager.getNeighbors()

      for neigh in neighbors:




def main():

   args = parseArgs()
   name = args.name[0]
   config = getConfig(args.config[0])

   neighbors = copy.deepcopy(config['sync'])

   nm = NeighborManager("neighbor manager", name, neighbors)
   nm.startThreads()

if __name__ == "__main__":
   main()
