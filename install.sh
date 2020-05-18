#!/usr/bin/env bash

if [[ "$EUID" -ne 0 ]]
  then echo "Please run as root"
  exit
fi

echo "what will be the ulab server url? (default https://www.servidor3dulab.ovh)"
while true; do
    read ulab_url
    if [[ ${ulab_url} == "" ]]; then
        ulab_url="https://www.servidor3dulab.ovh"
        break
    fi
    if [[ ${ulab_url} =~ ^http[s]?://.+$ ]]; then break; else echo "that is not a valid url"; fi
done
echo "ok, ulab url will be ${ulab_url}"
echo "where will be octoprint? (default http://localhost:5000/api)"
while true; do
    read octo_url
    if [[ ${octo_url} == "" ]]; then
        octo_url="http://localhost:5000/api"
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
echo "what is the token asociated to this pandora?"
while true; do
    read token
    if [[ ${token} == "" ]]; then
        echo "the token must not be empty"
    else
        break
    fi
done
echo "ok, token will be ${token}"
echo "now we have all the info we need to install ulab_thing in this pandora, starting the party..."
echo "==== installing dependencies ===="

apt update
apt install python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install -r requeriments.txt

echo "
#!/usr/bin/env bash
cd $PWD
source venv/bin/activate
python main.py \$@
" > ulab_thing.sh

chmod +x ulab_thing.sh
mv ulab_thing.sh /bin/ulab_thing

touch /etc/systemd/system/ulab_thing.service
chmod 775 /etc/systemd/system/ulab_thing.service
chmod a+w /etc/systemd/system/ulab_thing.service

echo "
[Unit]
Description=ulab_thing

[Service]
User=root
ExecStart=/bin/bash /bin/ulab_thing --ulab-token=$token --octoprint-url=$octo_url --ulab-url=$ulab_url --octoprint-path=$octo_path
Restart=on-failure
WorkingDirectory=$PWD
StandardOutput=syslog
StandardError=syslog

[Install]
WantedBy=multi-user.target
" > /etc/systemd/system/ulab_thing.service

systemctl enable ulab_thing.service
systemctl daemon-reload
service ulab_thing start

