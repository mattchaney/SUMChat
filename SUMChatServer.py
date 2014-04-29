#!/usr/bin/python

import errno, random, sctp, select, signal, socket, struct, sys
from threading import Thread

class SUMServer(object):
	def __init__(self, port):
		signal.signal(signal.SIGINT, self.print_clients)
		signal.signal(signal.SIGQUIT, self.exit)
		
		self.port = int(port)
		self.ulist = []
		self.mlist = []
		self.slist = []
		
		# Create exitpwd and listpwd
		self.exitpwd = random.randint(1000000, 9999999)
		self.listpwd = random.randint(1000000, 9999999)
		
		# Create multicast address
		self.mcastaddr = str(random.randint(224, 239)) + '.' + '.'.join([str(random.randint(0, 255)) for __ in xrange(3)])
		self.mcastport = random.randint(9999, 11001)
		self.mcast_group = (self.mcastaddr, self.mcastport)
		
		# Create all sockets
		self.tcpsock = self.create_tcp()
		self.udpsock = self.create_udp()
		self.sctpsock = self.create_sctp()
		
		print('\nServer Port:     {}'.format(self.tcpsock.getsockname()[1]))
		print('Multicast IP:    {}\nMulticast Port:  {}\n'.format(self.mcastaddr, self.mcastport))
		
		# Create multiprocessing workers
		self.connection_thread = Thread(target=self.connection_monitor)
		self.connection_thread.setDaemon(True)
	
	def create_tcp(self):
		tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			tcpsock.bind(('', self.port))
		except Exception as e:
			print(e)
			self.exit(None, None)
		return tcpsock
		
	def create_udp(self):
		try:
			udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			udpsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
			udpsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
			udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			udpsock.bind(('', self.port))
			print('binding udpsock to {}'.format(udpsock.getsockname()))
			mreq = struct.pack("4sl", socket.inet_aton(self.mcast_group[0]), socket.INADDR_ANY)
			udpsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
		except Exception as e:
			print(e)
			self.exit(None, None)
		return udpsock
	
	def create_sctp(self):
		sctpseq = sctp.sctpsocket_udp(socket.AF_INET)
		sctpseq.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			sctpseq.bind(('', self.port))
			print('binding sctpsock to {}'.format(sctpseq.getsockname()))
		except Exception as e:
			print(e)
			self.exit(None, None)
		return sctpseq
	
	def start(self):
		self.connection_thread.start()
		self.msg_monitor()
		
	def connection_monitor(self):
		self.tcpsock.listen(5)
		self.sctpsock.listen(5)
		inlist = [self.tcpsock]
		while True:
			inrdy, __, __ = select.select(inlist, [], [])
			for s in inrdy:
				if s == self.tcpsock:
					self.handle_tcp()
					
	def handle_tcp(self):
		try:
			sock, addr = self.tcpsock.accept()
		except socket.error as e:
			print('connection_monitor exception {}'.format(e))
			if e.errno == errno.EINTR:
				return
			else:
				print(e)
				self.exit(None, None)
		username, c_type = sock.recv(1024).split(' ')
		print('New ChatClient: {}@{}:{}'.format(username, addr[0], addr[1]))
		if c_type == '0':
			sock.send(self.mcastaddr + ' ' + str(self.mcastport) + ' ' + str(self.listpwd) + ' ' + str(self.exitpwd))
			self.mlist.append((username, addr[0], addr[1]))
		elif c_type == '1':
			sock.send(str(self.mcastport) + ' ' + str(self.listpwd) + ' ' + str(self.exitpwd))
			self.ulist.append((username, addr[0], addr[1]))
		elif c_type == '2':
			sock.send(str(self.mcastport) + ' ' + str(self.listpwd) + ' ' + str(self.exitpwd))
			self.slist.append((username, addr[0], addr[1]))
		
	def msg_monitor(self):
		inlist = [self.udpsock, self.sctpsock]
		while True:
			try:
				inready, __, __ = select.select(inlist, [], [])
			except Exception as (code, __):
				if code == errno.EINTR:
					continue
				else:
					raise
			for sock in inready:
				data, addr = sock.recvfrom(1024)
				data = data.replace('\n','')
				try:
					num = int(data)
					if num == self.listpwd:
						self.send_list(addr)
						continue
					elif num == self.exitpwd:
						self.remove_client(addr)
						continue
				except ValueError:
					pass
				print('Received {} from {}'.format(data, addr))
				self.forward_msg(data, addr)

	def send_list(self, addr):
		clients = self.build_list()
		for client in self.ulist:
			if addr[1] == client[2]:
				self.udpsock.sendto(clients, (client[1], client[2]))
				return
		for client in self.mlist:
			if addr[1] == client[2]:
				self.udpsock.sendto(clients, self.mcast_group)
				return
		for client in self.slist:
			if addr[1] == client[2]:
				self.sctpsock.sendto(clients, (client[1], client[2]))
				return
		
	def forward_msg(self, data, addr):
		print('sending {} to {}'.format(data, self.mcast_group))
		self.udpsock.sendto('{}:{}>{}'.format(addr[0], addr[1], data), self.mcast_group)
		for client in self.ulist:
			print('sending {} to {}'.format(data, client))
			self.udpsock.sendto('{}:{}> {}'.format(addr[0], addr[1], data), (client[1], client[2]))
		for client in self.slist:
			print('sending {} to {}'.format(data, client))
			self.sctpsock.sendto('{}:{}> {}'.format(addr[0], addr[1], data), (client[1], client[2]))

	def remove_client(self, addr):
		print('Removing client @ {}:{}'.format(addr[0], addr[1]))
		for client in self.ulist:
			if client[2] == addr[1]:
				self.ulist.remove((client[0], client[1], client[2]))
				return
		for client in self.mlist:
			if client[2] == addr[1]:
				self.mlist.remove((client[0], client[1], client[2]))
				return
		for client in self.slist:
			if client[2] == addr[1]:
				self.slist.remove((client[0], client[1], client[2]))
				return
			
	def build_list(self):
		clients = '\n\nChatClients List:\n----  Unicast  ----\n'
		for client in self.ulist:
			clients += '{}@{}:{}\n'.format(client[0], client[1], client[2])
		clients += '---- Multicast ----\n'
		for client in self.mlist:
			clients += '{}@{}:{}\n'.format(client[0], client[1], client[2])
		clients += '----   SCTP    ----\n'
		for client in self.slist:
			clients += '{}@{}:{}\n'.format(client[0], client[1], client[2])
		clients += '---- Total: {}  ----\n'.format(len(self.ulist) + len(self.mlist) + len(self.slist))
		return clients
	
	def print_clients(self, signal, frame):
		print self.build_list()

	def exit(self, signal, frame):
		for client in self.ulist:
			self.udpsock.sendto(str(self.exitpwd), (client[1], client[2]))
		for client in self.slist:
			self.sctpsock.sendto(str(self.exitpwd), (client[1], client[2]))
		try:
			self.udpsock.sendto(str(self.exitpwd), self.mcast_group)
		except Exception:
			pass
		try:
			self.tcpsock.close()
		except Exception:
			pass
		try:
			self.udpsock.close()
		except Exception:
			pass
		try:
			self.sctpsock.close()
		except Exception:
			pass
		print('ChatServer terminated')
		sys.exit()

def main(argv):
	if len(argv) != 2:
		print "Wrong number of arguments, usage is:\n\tpython umserver.py <port>"
		sys.exit(1)
	server = SUMServer(argv[1])
	server.start()	
	
if __name__ == '__main__':
	main(sys.argv)