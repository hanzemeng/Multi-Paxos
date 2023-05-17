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
