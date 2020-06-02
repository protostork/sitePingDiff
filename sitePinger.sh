#!/bin/bash

alreadyrunning(){
	echo "script currently running, exiting..."
	exit 1
}

exec 100>/tmp/sitePinger.lock || exit 1
flock -n 100 || alreadyrunning 0 # exit 1 # (echo "already running, exiting..." &&
trap 'rm -f /tmp/sitePinger.lock' EXIT


XDG_RUNTIME_DIR=/run/user/$(id -u) timeout 5m /usr/bin/python3 sitePingDiff.py $*
