#!/bin/sh

case "$1" in
    http://*|https://*) url="$1" ;;
    *) url="http://$1" ;;
esac

CR=$(printf '\r')

curl -sI "$url" | grep -i "^location:" | cut -d ' ' -f 2 | cut -d "$CR" -f 1