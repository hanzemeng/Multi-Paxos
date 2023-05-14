#!/bin/bash

FOLDER_PATH=$(pwd)

shopt -s nocasematch

osascript -e "tell app \"terminal\" to do script \"cd $FOLDER_PATH; python3 server.py\"" 

sleep 1

    for ((x=1; x<6; x++)); do
        printf " Open %s Terminal\\n" $x
        osascript -e "tell app \"terminal\" to do script \"cd $FOLDER_PATH; python3 node.py $x\"" 
    done
shopt -u nocasematch
