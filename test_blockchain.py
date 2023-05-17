from control_character import *
from blockchain import *
import sys


if __name__ == '__main__':
	blockchain = Blockchain()

	b1 = blockchain.add_block("POST", "hanzm", "EA", "End All Games")
	blockchain.commit_block(Block.block_to_string(b1))

	b2 = blockchain.add_block("POST", "hanzm", "Capcom", "Crapcom")
	blockchain.commit_block(Block.block_to_string(b2))

	blockchain.print()