#!/bin/bash
# parse workflow run outputs, generate actions.txt that contains all used actions

set -euxo pipefail

rm -f actions.txt
# this won't work with standard mac grep. run this inside a linux container
grep -rI  "Download immutable action package " artifacts/ | grep -oP "'\K[^']+(?=')" >> actions.txt
grep -rI  "Download action repository" artifacts/ | grep -oP "'\K[^']+(?=')" >> actions.txt
cat actions.txt | sort | uniq