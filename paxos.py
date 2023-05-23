from control_character import *
from blockchain import *

class Ballot:
    def __init__(self, seq_num: int = 0, pid: int = -1, depth: int = 0, *, line: str = None):
        if line is None:
            self.seq_num = seq_num
            self.pid = pid
            self.depth = depth
        else:
            args = line.split(US)
            self.seq_num = int(args[0])
            self.pid = int(args[1])
            self.depth = int(args[2])
    
    def __lt__(self, other):
        if self.depth < other.depth:
            return True
        elif (self.depth == other.depth) and (self.seq_num < other.seq_num):
            return True
        elif (self.depth == other.depth) and (self.seq_num == other.seq_num) and (self.pid < other.pid):
            return True
        return False

    def __ge__(self, other):
        if self < other:
            return False
        return True
    
    def __eq__(self, other):
        if (self.depth == other.depth) and (self.seq_num == other.seq_num) and (self.pid == other.pid):
            return True
        return False

    def __ne__(self, other):
        if self == other:
            return False
        return True
    
    def to_string(self):
        return f'{self.seq_num}{US}{self.pid}{US}{self.depth}'

    # below are static functions

    def string_to_ballot(ballot_string):
        new_ballot = Ballot()
        parameters = ballot_string.split(US)
        new_ballot.seq_num = int(parameters[0])
        new_ballot.pid = int(parameters[1])
        new_ballot.depth = int(parameters[2])

        return new_ballot

    def ballot_to_string(ballot, delimiter=US):
        return f'{ballot.seq_num}{US}{ballot.pid}{US}{ballot.depth}'

# class Request:
#     def __init__(self, op: str = None, username: str = None, title: str = None, content: str = None, *, line: str = None):
#         if line is None:
#             self.op = op
#             self.username = username
#             self.title = title
#             self.content = content
#         else:
#             args = line.split(',')
#             self.op = args[0]
#             self.username = args[1]
#             self.title = args[2]
#             self.content = args[3]
    
#     def to_string(self):
#         return f'{self.op},{self.username},{self.title},{self.content}'

class Slot:
    def __init__(self, slot_num: int = -1, accept_num: Ballot = Ballot(), accept_val: Block = Block()):
        self.slot_num = slot_num
        self.accept_num = accept_num
        self.accept_val = accept_val
        self.replies = []
        self.promise_quorum = False
        self.accept_quorum = False

    def to_string(self):
        return f'{self.slot_num}{RS}{self.accept_num.to_string()}{RS}{self.accept_val.to_string()}'