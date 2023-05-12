import socket
import threading
import sys
from os import _exit
from sys import stdout
from time import sleep

DELAY_TIME = 0.01

PROCESS_ID = -1
PROCESS_PORT = -1
SERVER_IP = socket.gethostbyname('localhost')
SERVER_PORT = 9000
sockets = 6 * [None] # 0 is for server; rest are for other nodes


def get_user_input():
	while True:
		user_input = input()
		parameters = user_input.split()
		if 0 == len(parameters) or "exit" == parameters[0]:
			for sock in sockets:
				if None != sock:
					sock.close()
			stdout.flush()
			_exit(0)
		elif "wait" == parameters[0]:
			sleep(int(parameters[1]))
		elif "hi" == parameters[0]: # say hi to all clients, for debugging
			for i in range(1, 6):
				if PROCESS_ID != i and None != sockets[i]:
					try:
						sockets[i].sendall(bytes(f"Hello from P{PROCESS_ID}", "utf-8"))
					except:
						print(f"can't send hi to {i}\n")

def handle_message_from(id, data): #id is the id that current process receives from
	print(f"{data}")
	parameters = data.split(" ")

	if "connect" == parameters[0]:
		if int(parameters[1]) >= PROCESS_ID: # only connect to client with smaller id
			return
		sockets[int(parameters[1])] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sockets[int(parameters[1])].connect((SERVER_IP, int(parameters[2])))
		sockets[int(parameters[1])].sendall(bytes(f"init {PROCESS_ID}\n", "utf-8"))
		threading.Thread(target=listen_message_from, args=[int(parameters[1])]).start() # listen to message from the target client

def listen_message_from(id):
	while True:
		try:
			data = sockets[id].recv(4096)
		except:
			break
		if not data: # connection closed
			sockets[id].close()
			break
		
		data = data.decode()
		data = data.split("\n") # to prevent recving mutiple messgaes, the last element is always ""
		for line in data:
			if "" == line:
				continue
			threading.Thread(target=handle_message_from, args=[id, line]).start()

def accept_connection():
	while True:
		try:
			conn, addr = sockets[PROCESS_ID].accept() # accept connection from client with larger id
			client_id = conn.recv(1024)
			client_id = client_id.decode()
			client_id = client_id.split()
			sockets[int(client_id[1])] = conn
			threading.Thread(target=listen_message_from, args=[int(client_id[1])]).start() # listen to message from the target client
		except:
			break

if __name__ == "__main__":
	PROCESS_ID = int(sys.argv[1])
	sockets[PROCESS_ID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sockets[PROCESS_ID].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sockets[PROCESS_ID].bind((SERVER_IP, 0))
	sockets[PROCESS_ID].listen()
	threading.Thread(target=accept_connection).start()

	sleep(DELAY_TIME)
	sockets[0] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sockets[0].connect((SERVER_IP, SERVER_PORT))
	sockets[0].sendall(bytes(f"init {PROCESS_ID} {sockets[PROCESS_ID].getsockname()[1]}", "utf-8")) # send client id and port to the server when connecting

	threading.Thread(target=get_user_input).start() # listen to user input from terminal
	threading.Thread(target=listen_message_from, args=[0]).start() # listen to message from server

	while True:
		pass # do nothing
