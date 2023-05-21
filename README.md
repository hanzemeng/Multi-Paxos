# Multi-Paxos

## Files

node.py:
    nodes that are trying to achive consensus

server.py:
    used to set up connections between the nodes.

blogapp.py:
    Bare bone implementation of the blog application

testblogapp.py:
    Simple testing

## Control Characters

All control characters are defined in control_character.py.

Append GS (decimal value 29) to every message (except for the init message) so receivers can parse multiple messages.<br>
Append RS (decimal value 30) to every parameter in a message so receivers can parse the parameters.<br>
Append US (decimal value 31) to every parameter in a block operation so Block can parse each field.<br>

### Changelog 5/20
- Got initial round of Paxos up and running: user issue request -> leader election -> request decided & executed
- Everything organized into "slots", new data structures defined in paxos.py. One slot corresponds to one final slot in the blockchain, holds intermediate values during the message passing
- Things are quite messy, no idea whether it'll work correctly with multiple rounds (but hopefully will)
- Changed a few delimiters in server.py and node.py
- Added self in blockchain init
- Cleaned up blogapp.py a bit with comment now storing title