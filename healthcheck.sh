#!/bin/bash

if pgrep -x "lolMiner" > /dev/null
then
    exit 0
else
    exit 1
fi
