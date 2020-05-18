#!/usr/bin/env bash

echo "updating from git..."

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}

git pull

echo "updated"