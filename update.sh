#!/usr/bin/env bash

echo "updating..."

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd "$DIR" || exit 1

git reset --hard
git pull

echo "updated"

rm -r *

git clone https://github.com/GabrielMusat/ucloud-thing.git .