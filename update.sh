#!/usr/bin/env bash

echo "updating"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}

git pull

service ulab_thing restart