from control_character import *
from blockchain import *

class Ballot:
    def __init__(self, seq_num: int = 0, pid: int = -1, depth: int = 0):
        self.seq_num = seq_num
        self.pid = pid
        self.depth = depth
    
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

    # below are static functions

    def string_to_ballot(ballot_string):
        new_ballot = Ballot()
        parameters = ballot_string.split(US)
        new_ballot.seq_num = int(parameters[0])
        new_ballot.pid = int(parameters[1])
        new_ballot.depth = int(parameters[2])

        return new_ballot

    def ballot_to_string(ballot, delimiter=US):
        return f'{ballot.seq_num}{delimiter}{ballot.pid}{delimiter}{ballot.depth}'