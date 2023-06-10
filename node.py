import socket
import threading
import sys
from os import _exit
from time import sleep
from queue import Queue
from blockchain import *
from blogapp import *
from paxos import *
import numpy as np

condition_lock = threading.Condition()
forward_lock = threading.Condition()

DELAY_TIME = 3
TIMEOUT_TIME = 15

PROCESS_ID = -1
PROCESS_PORT = -1
SERVER_IP = socket.gethostbyname('localhost')
SERVER_PORT = 9000
sockets = 6 * [None] # 0 is for server; rest are for other nodes

leader_id = -1
ballot = Ballot()
accepted_ballot = Ballot()
accepted_block = "none"

sent_ballot = Ballot()
promise_response_ballot = []
promise_response_block = []
accept_response_ballot = []
accept_response_block = []

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
		elif "wait" == parameters[0] and len(parameters) == 2:
			sleep(int(parameters[1]))
		elif "hi" == parameters[0]: # say hi to all clients, for debugging
			for i in range(1, 6):
				if PROCESS_ID != i and None != sockets[i]:
					try:
						sockets[i].sendall(bytes(f"Hello from P{PROCESS_ID}{GS}", "utf-8"))
					except:
						print(f"can't send hi to {i}\n")
		elif "fail" == parameters[0] and len(parameters) == 2:
			condition_lock.acquire()
			sockets[0].sendall(bytes(f"disconnect {parameters[1]}\n", "utf-8"))
			condition_lock.release()
		elif "fix" == parameters[0] and len(parameters) == 2:
			condition_lock.acquire()
			sockets[0].sendall(bytes(f"connect {parameters[1]}\n", "utf-8"))
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

			new_block = blockchain.add_block(operation, username, title, content, PROCESS_ID)
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

			new_block = blockchain.add_block(operation, username, title, content, PROCESS_ID)
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
		elif "q" == parameters[0]:
			temp_queue = Queue()
			while False == request_queue.empty():
				temp = request_queue.get();
				print(temp, flush=True)
				temp_queue.put(temp)
			request_queue = temp_queue
		elif 'blog' == parameters[0]:
			forum.print_all()
		elif 'view' == parameters[0] and len(parameters) == 2:
			forum.view_user(parameters[1])
		elif 'read' == parameters[0] and len(parameters) > 1:
			title = ' '.join(parameters[1:])
			forum.read_title(title)
		else:
			print('\nInvalid input!', flush=True)

def handle_message_from(id, data): #id is the id that current process receives from
	global condition_lock, leader_id, request_queue

	sleep(DELAY_TIME)

	print(f"{id}, {data}")
	parameters = []
	if data[0:7] != 'restore':
		parameters = data.split(RS)
	else: # restore message contains RS inbetween
		i1 = data.find(RS)
		i2 = data.find(RS, i1 + 1)
		parameters = [data[0:i1], data[i1 + 1:i2], data[i2 + 1:]]
	# print(parameters)	

	if "connect" == parameters[0]:
		if int(parameters[1]) >= PROCESS_ID: # only connect to client with smaller id
			return
		try:
			sockets[int(parameters[1])] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sockets[int(parameters[1])].connect((SERVER_IP, int(parameters[2])))
			sockets[int(parameters[1])].sendall(bytes(f"init {PROCESS_ID}", "utf-8")) # don't append 0x04 when initializing
			threading.Thread(target=listen_message_from, args=[int(parameters[1])]).start() # listen to message from the target client

			sleep(DELAY_TIME)
			try:
				sockets[int(parameters[1])].sendall(bytes(f'{backup_file_msg()}', 'utf-8')) # send my blockchain to the client newly connecting
			except:
				pass
		except:
			print(f'Error connecting to node {int(parameters[1])}', flush=True)
	elif "disconnect" == parameters[0]:
		sockets[int(parameters[1])].close()
	elif 'prepare' == parameters[0]:
		on_receive_prepare(parameters[1:])
	elif 'promise' == parameters[0]:
		on_receive_promise(parameters[1:])
	elif 'accept' == parameters[0]:
		on_receive_accept(parameters[1:])
	elif 'accepted' == parameters[0]:
		on_receive_accepted(parameters[1:])
	elif 'decide' == parameters[0]:
		on_receive_decide(parameters[1:])
	elif 'forward' == parameters[0]:
		on_receive_forward(parameters[1:])
	elif 'restore' == parameters[0]:
		on_receive_restore(parameters[1:])
	else:
		print('Invalid message received from another node!', flush=True)

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
		if data[0:7] != 'restore':
			data = data.split(GS)
			for line in data:
				if "" == line:
					continue
				threading.Thread(target=handle_message_from, args=[id, line]).start()
		else: # restore message contains GS inbetween
			threading.Thread(target=handle_message_from, args=[id, data]).start()

def accept_connection():
	while True:
		try:
			conn, addr = sockets[PROCESS_ID].accept() # accept connection from client with larger id
			client_id = conn.recv(1024)
			client_id = client_id.decode()
			client_id = client_id.split()
			sockets[int(client_id[1])] = conn
			try:
				sockets[int(client_id[1])].sendall(bytes(f'{backup_file_msg()}', 'utf-8')) # send my blockchain to the client newly connecting
			except:
				pass
			threading.Thread(target=listen_message_from, args=[int(client_id[1])]).start() # listen to message from the target client
		except:
			print("can't accept", flush=True)
			continue

def send_prepare():
	global condition_lock, ballot, promise_response_ballot, promise_response_block, blockchain, sent_ballot
	
	condition_lock.acquire()

	ballot.seq_num = ballot.seq_num + 1
	ballot.pid = PROCESS_ID
	ballot.depth = blockchain.length()
	sent_ballot = ballot
	promise_response_ballot = []
	promise_response_block = []
	threading.Thread(target=wait_for_promise).start()
	msg = f'prepare{RS}{Ballot.ballot_to_string(ballot)}{GS}'
	print(f"Sending {msg}", flush=True)

	condition_lock.release()

	for i in range(1, 6):
		if i != PROCESS_ID:
			try:
				sockets[i].sendall(bytes(msg, 'utf-8'))
			except:
				print(f'Error sending to node {i}', flush=True)

def wait_for_promise():
	global condition_lock, promise_response_ballot, promise_response_block, request_queue, leader_id

	condition_lock.acquire()
	while len(promise_response_ballot) < 2:
		if False == condition_lock.wait(timeout=TIMEOUT_TIME):
			print("Promise took too long, resending prepare", flush=True)
			condition_lock.notify_all()
			leader_id = PROCESS_ID
			threading.Thread(target=send_prepare).start()
			condition_lock.release()
			return

	if all(b != 'none' for b in promise_response_block):
		max_ballot_index = np.argmax(promise_response_ballot)
		request_queue.queue.insert(0, promise_response_block[max_ballot_index])
		condition_lock.notify_all()

	threading.Thread(target=become_leader).start()

	condition_lock.release()

def become_leader():
	global condition_lock, ballot, accept_response_ballot, accept_response_block, request_queue, blockchain, sent_ballot, leader_id

	while True:
		condition_lock.acquire()
		while request_queue.empty():
			condition_lock.wait()
		
		request = Block.string_to_block(request_queue.queue[0])
		new_block = Block.block_to_string(blockchain.add_block(request.operation, request.username, request.title, request.content, request.proposer))

		ballot.pid = PROCESS_ID
		ballot.depth = blockchain.length()
		sent_ballot = ballot
		accept_response_ballot = []
		accept_response_block = []
		msg = f'accept{RS}{Ballot.ballot_to_string(ballot)}{RS}{new_block}{GS}'
		print(f"Sending {msg}", flush=True)

		condition_lock.release()

		for i in range(1, 6):
			if i != PROCESS_ID:
				try:
					sockets[i].sendall(bytes(msg, 'utf-8'))
				except:
					print(f'Error sending to node {i}', flush=True)

		is_accepted = True
		condition_lock.acquire()
		while len(accept_response_ballot) < 2:
			if False == condition_lock.wait(timeout=TIMEOUT_TIME):
				is_accepted = False
				print("Accepted took too long, abort", flush=True)
				break
		
		if False == is_accepted:
			if request.proposer == PROCESS_ID:
				print("Restarting leader election", flush=True)
				condition_lock.notify_all()
				leader_id = PROCESS_ID
				threading.Thread(target=send_prepare).start()
				condition_lock.release()
				return
			request_queue.get()
			condition_lock.release()
			continue

		condition_lock.release()

		request_queue.get()
		execute_operation(new_block)
		msg = f'decide{RS}{new_block}{GS}'
		print(f"Sending {msg}", flush=True)
		for i in range(1, 6):
			if i != PROCESS_ID:
				try:
					sockets[i].sendall(bytes(msg, 'utf-8'))
				except:
					print(f'Error sending to node {i}', flush=True)

def on_receive_prepare(args):
	global condition_lock, leader_id, ballot, blockchain

	condition_lock.acquire()

	received_ballot = Ballot.string_to_ballot(args[0])
	if received_ballot < ballot:
		print('Smaller ballot, what a noob', flush=True)
		condition_lock.release()
		return
	if received_ballot.depth < blockchain.length():
		print('Shallower ballot, what a noob', flush=True)
		condition_lock.release()
		return

	ballot = received_ballot
	leader_id = received_ballot.pid
	msg = f'promise{RS}{Ballot.ballot_to_string(ballot)}{RS}{Ballot.ballot_to_string(accepted_ballot)}{RS}{accepted_block}{GS}'
	print(f"Sending {msg}", flush=True)

	condition_lock.release()

	try:
		sockets[leader_id].sendall(bytes(msg, 'utf-8'))
	except:
		print(f'Error sending to node {leader_id}', flush=True)

def on_receive_promise(args):
	global condition_lock, ballot, promise_response_ballot, promise_response_block, sent_ballot

	condition_lock.acquire()
	received_ballot = Ballot.string_to_ballot(args[0])
	if received_ballot != sent_ballot:
		condition_lock.release()
		return

	promise_response_ballot.append(Ballot.string_to_ballot(args[1]))
	promise_response_block.append(args[2])
	condition_lock.notify_all()
	condition_lock.release()

def on_receive_accept(args):
	global condition_lock, leader_id, ballot, accepted_ballot, accepted_block, blockchain, backup_file

	condition_lock.acquire()

	received_ballot = Ballot.string_to_ballot(args[0])
	if received_ballot < ballot:
		print('Smaller ballot, what a noob', flush=True)
		condition_lock.release()
		return
	if received_ballot.depth < blockchain.length():
		print('Shallower ballot, what a noob', flush=True)
		condition_lock.release()
		return

	leader_id = received_ballot.pid
	accepted_ballot = received_ballot
	accepted_block = args[1]
	backup_file.write(f'T{RS}{accepted_block}{GS}')
	msg = f'accepted{RS}{args[0]}{RS}{args[1]}{GS}'
	print(f"Sending {msg}", flush=True)

	condition_lock.release()

	try:
		sockets[leader_id].sendall(bytes(msg, 'utf-8'))
	except:
		print(f'Error sending to node {leader_id}', flush=True)

def on_receive_accepted(args):
	global condition_lock, ballot, accept_response_ballot, accept_response_block, sent_ballot

	condition_lock.acquire()

	received_ballot = Ballot.string_to_ballot(args[0])
	if received_ballot != sent_ballot:
		condition_lock.release()
		return

	accept_response_ballot.append(Ballot.string_to_ballot(args[0]))
	accept_response_block.append(args[1]) # unnecessary
	condition_lock.notify_all()

	condition_lock.release()

def on_receive_decide(args):
	global forward_lock, forwarded_request_queue

	forward_lock.acquire()
	if False == forwarded_request_queue.empty() and Block.same_block_op(args[0], forwarded_request_queue.queue[0]):
		forward_lock.notify_all()
		forwarded_request_queue.get()
	forward_lock.release()

	execute_operation(args[0])

def on_receive_forward(args):
	global condition_lock, leader_id, request_queue
	
	condition_lock.acquire()
	if PROCESS_ID == leader_id or -1 == leader_id:
		request_queue.put(args[0])
		condition_lock.notify_all()
		if -1 == leader_id:
			leader_id = PROCESS_ID
			threading.Thread(target=send_prepare).start()
	else:
		msg = f'forward{RS}{args[0]}{RS}{GS}'
		try:
			sockets[leader_id].sendall(bytes(msg, 'utf-8'))
		except:
			print(f'Error sending to node {leader_id}', flush=True)
	condition_lock.release()

def on_receive_restore(args):
	global blockchain, condition_lock

	condition_lock.acquire()
	
	if blockchain.length() >= int(args[0]):
		condition_lock.release()
		return
	
	restore_from_file_string(args[1])
	condition_lock.release()

def execute_operation(block_string):
	global condition_lock, forum, blockchain, backup_file, accepted_ballot, accepted_block

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
	accepted_ballot = Ballot()
	accepted_block = 'none'

	if new_block.operation == 'POST':
		print(f'NEW POST *{new_block.title}* from user *{new_block.username}*', flush=True)
	elif new_block.operation == 'COMMENT':
		print(f'NEW COMMENT on *{new_block.title}* from user *{new_block.username}*', flush=True)

	condition_lock.release()

def forward_request():
	global condition_lock, forward_lock, request_queue ,forwarded_request_queue, leader_id

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
			if False == forward_lock.wait(timeout=TIMEOUT_TIME):
				print("leader is not responding, send prepare", flush=True)
				condition_lock.acquire()
				while False == forwarded_request_queue.empty():
					request_queue.put(forwarded_request_queue.get())
				condition_lock.notify_all()
				leader_id = PROCESS_ID
				threading.Thread(target=send_prepare).start()
				condition_lock.release()

				break

		forward_lock.release()

def backup_file_msg():
	global backup_file
	backup_file.seek(0)
	data = backup_file.read()
	content = data.split(GS)
	length = 0
	for s in content:
		args = s.split(RS)
		if args[0] == 'D':
			length += 1
	return f'restore{RS}{length}{RS}{data}'

def restore_from_file_string(data: str):
	global backup_file, blockchain, forum, accepted_block
	backup_file.seek(0)
	backup_file.truncate()
	backup_file.write(data) # overwrite whole file

	blockchain = Blockchain()
	forum = Forum()
	content = data.split(GS)
	for s in content:
		args = s.split(RS)
		if args[0] == 'T':
			accepted_block = args[1]
		elif args[0] == 'D':
			if Block.same_block_op(accepted_block, args[1]):
				accepted_block = 'none'
			blockchain.commit_block(args[1])
	if blockchain.length() > 0:
		blockchain.build_forum(forum)

if __name__ == "__main__":
	PROCESS_ID = int(sys.argv[1])
	ballot.seq_num = 0
	ballot.pid = PROCESS_ID
	ballot.depth = 0
	backup_file = open(f'p{PROCESS_ID}_backup.txt', 'a+')
	backup_file.seek(0)
	data = backup_file.read()
	restore_from_file_string(data)
	sockets[PROCESS_ID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sockets[PROCESS_ID].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sockets[PROCESS_ID].bind((SERVER_IP, 0))
	sockets[PROCESS_ID].listen(5)
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
