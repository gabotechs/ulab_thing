#!/usr/bin/env bash

echo "what will be the ulab server url?"
while true; do
    read ulab_url
    if [[ ${ulab_url} =~ ^http[s]?://.+$ ]]; then break; else echo "that is not a valid url"; fi
done
echo "ok, ulab url will be ${ulab_url}"
echo "where will be octoprint? (default http://localhost)"
while true; do
    read octo_url
    if [[ ${octo_url} == "" ]]; then
        octo_url="http://localhost"
        break
    fi
    if [[ ${octo_url} =~ ^http[s]?://.+$ ]]; then break; else echo "that is not a valid url"; fi
done
echo "ok, octoprint url will be ${octo_url}"
echo "what will be the octoprint path? (/home/pi/.octoprint)"
while true; do
    read octo_path
    if [[ ${octo_path} == "" ]]; then
        octo_path="/home/pi/.octoprint"
        break
    fi
    if [[ -d ${octo_path} ]]; then
        break
    else
        echo "path $octo_path does not exists, enter a file path that exists"
    fi
done
echo "ok, octoprint path will be ${octo_path}"
echo "from who is this pandora?"
while true; do
    read user
    if [[ ${user} == "" ]]; then
        echo "the user must have a name"
    else
        break
    fi
done
echo "ok, user will be ${user}"
echo "and the password is..."
while true; do
    read pass
    if [[ ${pass} == "" ]]; then
        echo "the password must not be empty"
    else
        break
    fi
done
echo "ok, password will be *******, <- hello hackers"
echo "now we have all the info we need to install ulab_thing in this pandora, starting the party..."
echo "==== installing dependencies ===="
apt update
apt install python3.7
apt install python3-pip
python3 -m venv venv
source venv/bin/activate
pip install -r requeriments.txt


