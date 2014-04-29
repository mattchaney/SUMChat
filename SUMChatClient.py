#! /usr/bin/python

import errno, sctp, signal, socket, sys, time, select, struct

class SUMClient(object):
	def __init__(self, host, port, strat_code):
		# Set up signal handler
		signal.signal(signal.SIGINT, self.request_list)
		signal.signal(signal.SIGQUIT, self.exit)
		
		self.server_addr = (host, int(port))
		# Create TCP connection with server to recv server data
		self.tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.tcpsock.connect(self.server_addr)
		if strat_code == 'm':
			self.client_code = 0
		elif strat_code == 'u':
			self.client_code = 1
		elif strat_code == 's':
			self.client_code = 2
		
		# Send username and client code
		self.tcpsock.send('umclient ' + str(self.client_code))
		try:
			data = self.tcpsock.recv(1024)
			if self.client_code == 0:
				self.mcast_group = (data.split(' ')[0], int(data.split(' ')[1]))
				self.listpwd = data.split(' ')[2]
				self.exitpwd = data.split(' ')[3]
			elif self.client_code == 1 or self.client_code == 2:
				self.mcast_group = (host, int(data.split(' ')[0]))
				self.listpwd = data.split(' ')[1]
				self.exitpwd = data.split(' ')[2]
			else:
				print('Incorrect client code')
				self.exit(None, None)
			print('\nChatServer host NAME:   {}'.format(host))
			print('ChatServer IP address:  {}'.format(socket.gethostbyname(host)))
			print('ChatServer TCP Port:        {}'.format(port))
			if self.client_code == 0:
				print('\nReceived Multicast IP:   {}'.format(self.mcast_group[0]))
				print('Received Multicast Port: {}'.format(self.mcast_group[1]))
			else:
				print('\nReceived Unicast IP:   {}'.format(self.mcast_group[0]))
				print('Received Unicast Port: {}'.format(self.mcast_group[1]))
			print('List pwd: {} Exit pwd: {}'.format(self.listpwd, self.exitpwd))
		except socket.error:
			raise
		# Create send and recv sockets based on strategy applied
		self.create_sockets(host)
		print('\nType messages to be sent to the group followed by ENTER\nType CTRL-D to Quit')

	def create_sockets(self, host):
		if self.client_code == 0:
			print 'creating mcast sockets'
			self.sendsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			self.sendsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
			self.sendsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.sendsock.bind(('', self.tcpsock.getsockname()[1]))
			print('binding sendsock to {}'.format(self.sendsock.getsockname()))
			self.recvsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			self.recvsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
			self.recvsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
			self.recvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.recvsock.bind(('', self.mcast_group[1]))
			print('binding recvsock to {}'.format(self.recvsock.getsockname()))
			mreq = struct.pack("4sl", socket.inet_aton(self.mcast_group[0]), socket.INADDR_ANY)
			self.recvsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
		elif self.client_code == 1:
			print 'creating unicast sockets'
			self.recvsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			self.recvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.recvsock.bind(('', self.tcpsock.getsockname()[1]))
			print('binding recvsock to {}'.format(self.recvsock.getsockname()))
			self.sendsock = self.recvsock
		else:
			print 'creating sctp sockets'
			self.recvsock = sctp.sctpsocket_udp(socket.AF_INET)
			self.recvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.recvsock.bind(('', self.tcpsock.getsockname()[1]))
			print('binding recvsock to {}'.format(self.recvsock.getsockname()))
			self.sendsock = self.recvsock
			self.sendsock.connect(self.server_addr)
		
	def run(self):
		inlist = [self.recvsock, sys.stdin]
		while True:
			try:
				inputready, __, __ = select.select(inlist, [], [])
			except select.error as v:
				if v[0] != errno.EINTR:
					raise
				else:
					continue
			for item in inputready:
				if item == self.recvsock:
					data, _ = self.recvsock.recvfrom(1024)
					if data == str(self.exitpwd):
						self.exit(None, None)
					print(data)
				elif item == sys.stdin:
					data = sys.stdin.readline()
					if data:
						self.sendsock.sendto(data, self.server_addr)
					else:
						self.exit(None, None)
			time.sleep(0.01)
	
	def request_list(self, signal, frame):
		self.sendsock.sendto(self.listpwd, self.server_addr)
	
	def exit(self, signal, frame):
		print('\nChatClient terminated')
		self.sendsock.sendto(self.exitpwd, self.server_addr)
		try:
			self.tcpsock.close()
		except Exception:
			pass
		try:
			self.sendsock.close()
		except Exception:
			pass
		try:
			self.recvsock.close()
		except Exception:
			pass
		sys.exit()

def main(argv):
	if len(argv) != 4:
		print "Usage is:\n\tpython umclient.py <host> <port> <s|u|m>"
		sys.exit(1)
	client = SUMClient(argv[1], argv[2], argv[3])
	client.run()
	
if __name__ == '__main__':
	main(sys.argv)