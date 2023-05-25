import socket
import threading
import sys
import random
from os import _exit
from time import sleep
from queue import Queue
from blockchain import *
from blogapp import *
from paxos import *
import numpy as np

condition_lock = threading.Condition()
forward_lock = threading.Condition()

DELAY_TIME = 0.5
TIME_OUT_TIME = 5

PROCESS_ID = -1
PROCESS_PORT = -1
SERVER_IP = socket.gethostbyname('localhost')
SERVER_PORT = 9000
sockets = 6 * [None] # 0 is for server; rest are for other nodes
link_work = 6 * [False] # 0 is for server; rest are for other nodes

leader_id = -1
ballot = Ballot()
accepted_ballot = Ballot()
accepted_block = "none"
promise_response_ballot = []
promise_response_block = []
accept_response_ballot = []
accept_response_block = []

slots = []

forum = Forum()
blockchain = Blockchain()
request_queue = Queue()
forwarded_request_queue = Queue()

def get_user_input():
	global condition_lock, leader_id, request_queue, forward_lock, forwarded_request_queue, backup_file
	while True:
		try:
			user_input = input()
		except:
			continue
		
		parameters = user_input.split()
		if 0 == len(parameters) or "crash" == parameters[0]:
			for sock in sockets:
				if None != sock:
					sock.close()
			sys.stdout.flush()
			backup_file.close()
			_exit(0)
		elif "wait" == parameters[0]:
			sleep(int(parameters[1]))
		elif "hi" == parameters[0]: # say hi to all clients, for debugging
			for i in range(1, 6):
				if PROCESS_ID != i and None != sockets[i] and True == link_work[i]:
					try:
						sockets[i].sendall(bytes(f"Hello from P{PROCESS_ID}{GS}", "utf-8"))
					except:
						print(f"can't send hi to {i}\n")
		elif "fail" == parameters[0]:
			condition_lock.acquire()
			link_work[int(parameters[1])] = False
			condition_lock.release()
		elif "fix" == parameters[0]:
			condition_lock.acquire()
			link_work[int(parameters[1])] = True
			condition_lock.release()

		elif "p" == parameters[0] or "post" == parameters[0]:
			operation = "POST"
			print("Enter username, max 16 character")
			username = sys.stdin.read(16)
			print("\nEnter title, max 32 character")
			title = sys.stdin.read(32)
			print("\nEnter content, max 256 character")
			content = sys.stdin.read(256)
			print()
			
			if 0 == len(username) or 0 == len(title) or 0 == len(content):
				print("\nPost canceled")
				continue
			
			condition_lock.acquire()

			new_block = blockchain.add_block(operation, username, title, content)
			new_block_string = Block.block_to_string(new_block)

			if leader_id == -1:
				leader_id = PROCESS_ID
				request_queue.put(new_block_string)
				condition_lock.notify_all()
				threading.Thread(target=send_prepare).start()
			elif leader_id == PROCESS_ID:
				request_queue.put(new_block_string)
				condition_lock.notify_all()
			else:
				forward_lock.acquire()
				forwarded_request_queue.put(new_block_string)
				forward_lock.notify_all()
				forward_lock.release()

			condition_lock.release()
		
		elif 'c' == parameters[0] or 'comment' == parameters[0]:
			operation = 'COMMENT'
			print("Enter username, max 16 character")
			username = sys.stdin.read(16)
			print("\nEnter title, max 32 character")
			title = sys.stdin.read(32)
			print("\nEnter content, max 256 character")
			content = sys.stdin.read(256)
			print()

			if 0 == len(username) or 0 == len(title) or 0 == len(content):
				print("\nComment canceled")
				continue
			
			condition_lock.acquire()

			new_block = blockchain.add_block(operation, username, title, content)
			new_block_string = Block.block_to_string(new_block)

			if leader_id == -1:
				leader_id = PROCESS_ID
				request_queue.put(new_block_string)
				condition_lock.notify_all()
				threading.Thread(target=send_prepare).start()
			elif leader_id == PROCESS_ID:
				request_queue.put(new_block_string)
				condition_lock.notify_all()
			else:
				forward_lock.acquire()
				forwarded_request_queue.put(new_block_string)
				forward_lock.notify_all()
				forward_lock.release()

			condition_lock.release()

		elif "b" == parameters[0]:
			blockchain.print()
		elif 'blog' == parameters[0]:
			forum.print_all()
		elif 'view' == parameters[0] and len(parameters) == 2:
			forum.view_user(parameters[1])
		elif 'read' == parameters[0]:
			title = ' '.join(parameters[1:])
			forum.read_title(title)
		else:
			print('\nInvalid input!', flush=True)

def handle_message_from(id, data): #id is the id that current process receives from
	global condition_lock, leader_id, request_queue

	print(f"{id}, {data}")
	parameters = data.split(RS)
	# print(parameters)

	sleep(DELAY_TIME)

	if "connect" == parameters[0]:
		if int(parameters[1]) >= PROCESS_ID: # only connect to client with smaller id
			return
		try:
			sockets[int(parameters[1])] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sockets[int(parameters[1])].connect((SERVER_IP, int(parameters[2])))
			sockets[int(parameters[1])].sendall(bytes(f"init {PROCESS_ID}", "utf-8")) # don't append 0x04 when initializing
			threading.Thread(target=listen_message_from, args=[int(parameters[1])]).start() # listen to message from the target client
		except:
			print(f'Error connecting to node {int(parameters[1])}', flush=True)
	elif 'prepare' == parameters[0]:
		on_receive_prepare(parameters[1:], id)
	elif 'promise' == parameters[0]:
		on_receive_promise(parameters[1:], id)
	elif 'accept' == parameters[0]:
		on_receive_accept(parameters[1:], id)
	elif 'accepted' == parameters[0]:
		on_receive_accepted(parameters[1:], id)
	elif 'decide' == parameters[0]:
		on_receive_decide(parameters[1:], id)
	elif 'forward' == parameters[0]:
		on_receive_forward(parameters[1:], id)
	else:
		print('Invalid message received from another node!', flush=True)

def listen_message_from(id):
	condition_lock.acquire()
	link_work[id] = True
	condition_lock.release()
	while True:
		try:
			data = sockets[id].recv(4096)
		except:
			break
		if not data: # connection closed
			sockets[id].close()
			break
		
		if False == link_work[id]:
			continue

		data = data.decode()
		data = data.split(GS) # to prevent recving mutiple messgaes, the last element is always ""
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

def send_prepare():
	global condition_lock, ballot, promise_response_ballot, promise_response_block
	
	condition_lock.acquire()

	ballot.seq_num = ballot.seq_num + 1
	ballot.depth = blockchain.length()
	promise_response_ballot = []
	promise_response_block = []
	threading.Thread(target=wait_for_promise).start()
	msg = f'prepare{RS}{Ballot.ballot_to_string(ballot)}{GS}'

	condition_lock.release()

	for i in range(1, 6):
		if i != PROCESS_ID:
			try:
				sockets[i].sendall(bytes(msg, 'utf-8'))
			except:
				print(f'Error sending to node {i}', flush=True)

def wait_for_promise():
	global condition_lock, leader_id, promise_response_ballot, promise_response_block, request_queue

	condition_lock.acquire()
	while len(promise_response_ballot) < 2:
		condition_lock.wait()

	max_ballot_index = np.argmax(promise_response_ballot)

	if np.max(promise_response_ballot) != Ballot():
		max_ballot_index = np.argmax(promise_response_ballot)
		request_queue.put(promise_response_block[max_ballot_index])
		condition_lock.notify_all()

	threading.Thread(target=become_leader).start()

	condition_lock.release()

def become_leader():
	global condition_lock, ballot, accept_response_ballot, accept_response_block, request_queue

	while True:
		condition_lock.acquire()
		while request_queue.empty():
			condition_lock.wait()
		new_block = request_queue.get()

		accept_response_ballot = []
		accept_response_block = []
		msg = f'accept{RS}{Ballot.ballot_to_string(ballot)}{RS}{new_block}{GS}'

		condition_lock.release()

		for i in range(1, 6):
			if i != PROCESS_ID:
				try:
					sockets[i].sendall(bytes(msg, 'utf-8'))
				except:
					print(f'Error sending to node {i}', flush=True)

		condition_lock.acquire()
		while len(accept_response_ballot) < 2:
			condition_lock.wait()
		condition_lock.release()

		execute_operation(new_block)

		msg = f'decide{RS}{new_block}{GS}'
		for i in range(1, 6):
			if i != PROCESS_ID:
				try:
					sockets[i].sendall(bytes(msg, 'utf-8'))
				except:
					print(f'Error sending to node {i}', flush=True)

def on_receive_prepare(args, id):
	global condition_lock, leader_id, ballot

	condition_lock.acquire()

	recv_bal = Ballot.string_to_ballot(args[0])
	if recv_bal < ballot:
		print('Smaller ballot, what a noob', flush=True)
		condition_lock.release()
		return

	ballot = recv_bal
	leader_id = recv_bal.pid
	msg = f'promise{RS}{Ballot.ballot_to_string(ballot)}{RS}{Ballot.ballot_to_string(accepted_ballot)}{RS}{accepted_block}{GS}'

	condition_lock.release()

	try:
		sockets[leader_id].sendall(bytes(msg, 'utf-8'))
	except:
		print(f'Error sending to node {leader_id}', flush=True)

def on_receive_promise(args, id):
	global condition_lock, ballot, promise_response_ballot, promise_response_block

	condition_lock.acquire()
	sent_bal = Ballot.string_to_ballot(args[0])
	if sent_bal != ballot:
		condition_lock.release()
		return

	promise_response_ballot.append(Ballot.string_to_ballot(args[1]))
	promise_response_block.append(args[2])
	condition_lock.notify_all()
	condition_lock.release()

def on_receive_accept(args, id):
	global condition_lock, leader_id, ballot, accepted_ballot, accepted_block, backup_file

	condition_lock.acquire()

	recv_bal = Ballot.string_to_ballot(args[0])
	if recv_bal < ballot:
		print('Smaller ballot, what a noob', flush=True)
		condition_lock.release()
		return

	leader_id = recv_bal.pid
	accepted_ballot = recv_bal
	accepted_block = args[1]
	backup_file.write(f'T{RS}{accepted_block}{GS}')
	msg = f'accepted{RS}{args[0]}{RS}{args[1]}{GS}'

	condition_lock.release()

	try:
		sockets[leader_id].sendall(bytes(msg, 'utf-8'))
	except:
		print(f'Error sending to node {leader_id}', flush=True)

def on_receive_accepted(args, id):
	global condition_lock, ballot, accept_response_ballot, accept_response_block

	condition_lock.acquire()

	sent_bal = Ballot.string_to_ballot(args[0])
	if sent_bal != ballot:
		condition_lock.release()
		return

	accept_response_ballot.append(Ballot.string_to_ballot(args[0]))
	accept_response_block.append(args[1]) # unnecessary
	condition_lock.notify_all()

	condition_lock.release()

def on_receive_decide(args, id):
	global forward_lock, forwarded_request_queue

	forward_lock.acquire()
	if False == forwarded_request_queue.empty() and args[0] == forwarded_request_queue.queue[0]:
		forward_lock.notify_all()
		forwarded_request_queue.get()
	forward_lock.release()

	execute_operation(args[0])

def on_receive_forward(args, id):
	global condition_lock, leader_id, request_queue
	if PROCESS_ID == leader_id or -1 == leader_id:
		condition_lock.acquire()
		request_queue.put(args[0])
		condition_lock.notify_all()

		if -1 == leader_id:
			leader_id = PROCESS_ID
			threading.Thread(target=send_prepare).start()

		condition_lock.release()
	else:
		msg = f'forward{RS}{args[0]}{RS}{GS}'
		try:
			sockets[leader_id].sendall(bytes(msg, 'utf-8'))
		except:
			print(f'Error sending to node {leader_id}', flush=True)

def execute_operation(block_string):
	global condition_lock, forum, blockchain, backup_file

	condition_lock.acquire()

	success = False
	new_block = Block.string_to_block(block_string)
	if new_block.operation == 'POST':
		success = forum.post_blog(Blog(new_block.username, new_block.title, new_block.content))
	elif new_block.operation == 'COMMENT':
		success = forum.post_comment(Comment(new_block.username, new_block.title, new_block.content))
	if False == success:
		condition_lock.release()
		return

	blockchain.commit_block(block_string)
	backup_file.write(f'D{RS}{block_string}{GS}')

	if new_block.operation == 'POST':
		print(f'NEW POST *{new_block.title}* from user *{new_block.username}*', flush=True)
	elif new_block.operation == 'COMMENT':
		print(f'NEW COMMENT on *{new_block.title}* from user *{new_block.username}*', flush=True)

	condition_lock.release()

def forward_request():
	global forward_lock, forwarded_request_queue, leader_id

	while True:
		forward_lock.acquire()
		
		while forwarded_request_queue.empty():
			forward_lock.wait()

		forward_block = forwarded_request_queue.queue[0]

		msg = f'forward{RS}{forward_block}{RS}{GS}'
		try:
			sockets[leader_id].sendall(bytes(msg, 'utf-8'))
		except:
			print(f'Error sending to node {leader_id}', flush=True)

		while False == forwarded_request_queue.empty() and forward_block == forwarded_request_queue.queue[0]:
			forward_lock.wait()

		forward_lock.release()

def restore_from_file():
	global backup_file, blockchain, forum
	backup_file.seek(0)
	content = backup_file.read().split(GS)
	for s in content:
		args = s.split(RS)
		if args[0] == 'D':
			blockchain.commit_block(args[1])
	if blockchain.length() > 0:
		blockchain.build_forum(forum)

if __name__ == "__main__":
	PROCESS_ID = int(sys.argv[1])
	ballot.seq_num = 0
	ballot.pid = PROCESS_ID
	ballot.depth = 0
	backup_file = open(f'p{PROCESS_ID}_backup.txt', 'a+')
	restore_from_file()
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

	threading.Thread(target=forward_request).start() 

	while True:
		pass # do nothing
