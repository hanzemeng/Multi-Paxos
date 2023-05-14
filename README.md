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

append 0x04 to the end of every message (except for the init message) so receivers can parse multiple messages
