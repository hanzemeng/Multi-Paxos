from control_character import *
import hashlib

class Block:
	def __init__(self):
		pervious_block = None
		pervious_block_hash = "0000000000000000000000000000000000000000000000000000000000000000"
		operation = "unknown"
		username = "unknown"
		title = "unknown"
		content = "unknown"
		nonce = 0

	def to_bytes(self):
		temp_string = self.pervious_block_hash + self.operation + self.username + self.title + self.content + str(self.nonce)
		return bytes(temp_string, 'utf-8')

	# below are static functions

	def string_to_block(block_string):
		new_block = Block()
		parameters = block_string.split(US)
		new_block.pervious_block_hash = parameters[0][1:]
		new_block.operation = parameters[1][1:]
		new_block.username = parameters[2]
		new_block.title = parameters[3]
		new_block.content = parameters[4][:-1]
		new_block.nonce = parameters[5][:-1]
		return new_block

	def block_to_string(block, delimiter=US):
		return f"<{block.pervious_block_hash}{delimiter}<{block.operation}{delimiter}{block.username}{delimiter}{block.title}{delimiter}{block.content}>{delimiter}{block.nonce}>"

class Blockchain:
	def __init__(self):
		self.tail = None

	def commit_block(self, block_string):
		new_block = Block.string_to_block(block_string)
		new_block.pervious_block = self.tail
		self.tail = new_block

	def add_block(self, operation, username, title, content):
		block = Block()

		if None == self.tail:
			block.pervious_block_hash = "0000000000000000000000000000000000000000000000000000000000000000"
		else:
			block.pervious_block_hash = hashlib.sha256(self.tail.to_bytes()).hexdigest()
		block.operation = operation
		block.username = username
		block.title = title
		block.content = content
		block.nonce = 0
		while ('0' != hashlib.sha256(block.to_bytes()).hexdigest()[0]) and ('1' != hashlib.sha256(block.to_bytes()).hexdigest()[0]):
			block.nonce += 1

		return block

	def print(self):
		stack = []
		current = self.tail
		while None != current:
			stack.append(current)
			current = current.pervious_block

		while 0 != len(stack):
			current = stack.pop()
			print(Block.block_to_string(current, SPACE))

