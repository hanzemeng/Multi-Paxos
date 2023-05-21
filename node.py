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

condition_lock = threading.Condition()

DELAY_TIME = 0.01

PROCESS_ID = -1
PROCESS_PORT = -1
SERVER_IP = socket.gethostbyname('localhost')
SERVER_PORT = 9000
sockets = 6 * [None] # 0 is for server; rest are for other nodes
link_work = 6 * [False] # 0 is for server; rest are for other nodes

blockchain = Blockchain()
leader_id = -1
ballot = Ballot()
slots = []
forum = Forum()
request_queue = Queue()

def get_user_input():
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
			
			r = Request(operation, username, title, content)
			if leader_id == -1:
				request_queue.put(r)
				send_prepare()
			elif leader_id == PROCESS_ID:
				request_queue.put(r)
			else:
				forward_request(r)
		
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
			
			r = Request(operation, username, title, content)
			if leader_id == -1:
				request_queue.put(r)
				send_prepare()
			elif leader_id == PROCESS_ID:
				request_queue.put(r)
			else:
				forward_request(r)

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
	# print(f"{id}, {data}")
	parameters = data.split(RS)
	# print(parameters)

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
		send_promise(parameters[1:], id)
	elif 'promise' == parameters[0]:
		received_promise(parameters[1:], id)
	elif 'accept' == parameters[0]:
		send_accepted(parameters[1:], id)
	elif 'accepted' == parameters[0]:
		received_accepted(parameters[1:], id)
	elif 'decide' == parameters[0]:
		received_decide(parameters[1:], id)
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
	global slots, ballot
	print(f'P{PROCESS_ID} sending prepare')
	ballot.seq_num = ballot.seq_num + 1
	ballot.pid = PROCESS_ID
	ballot.depth = blockchain.length()
	s = Slot(blockchain.length() + 1, ballot)
	slots.append(s)
	# print(';; '.join(map(Slot.to_string, slots)), flush=True)
	msg = f'prepare{RS}{s.to_string()}{GS}'
	for i in range(1, 6):
		if i != PROCESS_ID:
			try:
				sockets[i].sendall(bytes(msg, 'utf-8'))
			except:
				print(f'Error sending to node {i}', flush=True)

def send_promise(args, id):
	global leader_id, slots, ballot
	# args[0] = slot_num, args[1] = accept_num, args[2] = accept_val
	recv_bal = Ballot(line=args[1])
	print(f'Received prepare from {id}. Slot: {args[0]}, my ballot: {ballot.to_string()}, recv ballot: {recv_bal.to_string()}', flush=True)
	if recv_bal < ballot:
		print('Smaller ballot, what a noob', flush=True)
		return
	curr_slot = Slot(int(args[0]))
	for s in slots:
		if s.slot_num == int(args[0]):
			curr_slot = s
			break
	# print(';; '.join(map(Slot.to_string, slots)), flush=True)
	try:
		ballot = recv_bal
		leader_id = recv_bal.pid
		slots.append(curr_slot)
		print(f'Promising to P{leader_id}', flush=True)
		sockets[leader_id].sendall(bytes(f'promise{RS}{ballot.to_string()}{RS}{curr_slot.to_string()}{GS}', 'utf-8'))
	except:
		print(f'Error sending to node {leader_id}', flush=True)

def received_promise(args, id):
	global slots, leader_id
	# args[0] should be my own ballot, args[1] = slot_num, args[2] = accept_num, args[3] = accept_val
	print(f'Received promise from {id}', flush=True)
	curr_slot = Slot(int(args[1]))
	for s in slots:
		if s.slot_num == int(args[1]):
			if not s.promise_quorum:
				s.replies.append(args[2:])
				curr_slot = s
				break
	if curr_slot.promise_quorum:
		return
	if len(curr_slot.replies) >= 2:
		leader_id = PROCESS_ID
		curr_slot.replies = []
		curr_slot.promise_quorum = True
		send_accept(curr_slot)

def send_accept(curr_slot: Slot):
	global slots, ballot
	max_i = -1
	max_b = Ballot()
	max_v = Request()
	for i in range(0, len(curr_slot.replies)):
		bal = Ballot(line=curr_slot.replies[i][0])
		val = Request(line=curr_slot.replies[i][1])
		if (val.op != None) and (max_b < bal):
			max_i = i
			max_b = bal
			max_v = val
	if max_i > -1:
		curr_slot.accept_num = max_b
		curr_slot.accept_val = max_v
	else:
		curr_slot.accept_num = ballot
		curr_slot.accept_val = request_queue.queue[0]
	for s in slots:
		if s.slot_num == curr_slot.slot_num:
			slots.remove(s)
			break
	slots.append(curr_slot)
	print(f'Sending accept for slot {curr_slot.slot_num}, ballot {curr_slot.accept_num.to_string()}, content {curr_slot.accept_val.to_string()}', flush=True)
	# print(';; '.join(map(Slot.to_string, slots)), flush=True)
	msg = f'accept{RS}{curr_slot.to_string()}{GS}'
	for i in range(1, 6):
		if i != PROCESS_ID:
			try:
				sockets[i].sendall(bytes(msg, 'utf-8'))
			except:
				print(f'Error sending to node {i}', flush=True)

def send_accepted(args, id):
	global ballot, slots
	# args[0] = slot_num, args[1] = accept_num, args[2] = accept_val
	recv_bal = Ballot(line=args[1])
	print(f'Received accept from {id}. My ballot: {ballot.to_string()}, recv ballot: {recv_bal.to_string()}')
	if recv_bal < ballot:
		print('Smaller ballot, what a noob', flush=True)
		return
	# print(';; '.join(map(Slot.to_string, slots)), flush=True)
	for s in slots:
		if s.slot_num == int(args[0]):
			s.accept_num = recv_bal
			s.accept_val = Request(line=args[2])
			print(f'Sending accepted to P{leader_id}', flush=True)
			msg = f'accepted{RS}{s.to_string()}{GS}'
			try:
				sockets[leader_id].sendall(bytes(msg, 'utf-8'))
			except:
				print(f'Error sending to node {leader_id}', flush=True)
			break

def received_accepted(args, id):
	global slots
	# args[0] = slot_num, args[1] = accept_num, args[2] = accept_val
	print(f'Received accepted from {id}', flush=True)
	curr_slot = Slot(int(args[0]))
	for s in slots:
		if s.slot_num == int(args[0]):
			if not s.accept_quorum:
				s.replies.append(args[1:])
				curr_slot = s
				break
	# print('Sanity check:') # sanity check, all three should be the same
	# print(curr_slot.accept_val.to_string())
	# print(request_queue.queue[0].to_string())
	# print(args[2])
	if curr_slot.accept_quorum:
		return
	if len(curr_slot.replies) >= 2:
		curr_slot.accept_quorum = True
		curr_slot.replies = []
		execute_operation(request_queue.get())
		print(f'Sending decide for slot {curr_slot.slot_num}, ballot {curr_slot.accept_num.to_string()}, content {curr_slot.accept_val.to_string()}', flush=True)
		msg = f'decide{RS}{curr_slot.to_string()}{GS}'
		for i in range(1, 6):
			if i != PROCESS_ID:
				try:
					sockets[i].sendall(bytes(msg, 'utf-8'))
				except:
					print(f'Error sending to node {i}', flush=True)
		for s in slots:
			if s.slot_num == int(args[0]):
				slots.remove(s)
				break
		slots.append(curr_slot)
		# print(';; '.join(map(Slot.to_string, slots)), flush=True)

def received_decide(args, id):
	print(f'Received decide from {id}', flush=True)
	r = Request(line=args[2])
	execute_operation(r)

def forward_request(r: Request):
	pass

def execute_operation(r: Request):
	global blockchain
	with condition_lock:
		success = False
		if r.op == 'POST':
			success = forum.post_blog(Blog(r.username, r.title, r.content))
		elif r.op == 'COMMENT':
			success = forum.post_comment(Comment(r.username, r.title, r.content))
		if not success:
			return
		new_block = blockchain.add_block(r.op, r.username, r.title, r.content)
		blockchain.commit_block(Block.block_to_string(new_block))

if __name__ == "__main__":
	PROCESS_ID = int(sys.argv[1])
	ballot.pid = PROCESS_ID
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
