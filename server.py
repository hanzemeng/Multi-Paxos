import socket
import threading
from os import _exit
from sys import stdout
from time import sleep
from control_character import *

IP = socket.gethostbyname('localhost')
PORT = 9000
in_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_sockets = 5 * [None]
client_ports = 5 * [-1]
id_to_port = 5 * [-1] # id_to_port[i] has the port number of the client with id i+1

connect_lock = threading.Lock()

def get_user_input():
	while True:
		user_input = input()
		parameters = user_input.split()
		if 0 == len(parameters) or "exit" == parameters[0]:
			in_sock.close()
			for sock in client_sockets:
				if None != sock:
					sock[0].close()
			#print("exiting program", flush=True)
			stdout.flush()
			_exit(0)
		elif "wait" == parameters[0]:
			sleep(int(parameters[1]))

def respond(conn, addr):
	while True: # handle message sent from a client
		try:
			data = conn.recv(1024)
		except:
			break
		
		if not data:
			conn.close()
			break

		threading.Thread(target=handle_msg, args=(data, conn, addr)).start()

def handle_msg(data, conn, addr):
	global server_logical_time 
	data = data.decode()
	parameters = data.split()

	if "init" == parameters[0]:
		connect_lock.acquire()
		client_ports[int(parameters[1])-1] = int(parameters[2])

		for sock in client_sockets: # tell existing clients to connect to the new client
			if None != sock:
				try:
					sock[0].sendall(bytes(f"connect{RS}{parameters[1]}{RS}{parameters[2]}{GS}", "utf-8"))
				except:
					continue

		for i in range(5): # tell the new client to connect to existing clients
			if None != client_sockets[i]:
				conn.sendall(bytes(f"connect{RS}{i+1}{RS}{client_ports[i]}{GS}", "utf-8"))
		
		id_to_port[int(parameters[1])-1] = addr[1]
		client_sockets[int(parameters[1])-1] = (conn, addr)
		connect_lock.release()

if __name__ == "__main__":
	in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	in_sock.bind((IP, PORT))
	in_sock.listen()
	
	threading.Thread(target=get_user_input).start() # handle user inputs to the server

	while True: # handle connection from clients
		try:
			conn, addr = in_sock.accept()
		except:
			#print("exception in accept", flush=True)
			break

		threading.Thread(target=respond, args=(conn, addr)).start()