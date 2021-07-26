rm -r *
rm -r .*

apt-get install libzbar-dev libzbar0 -y

git clone https://github.com/GabrielMusat/ucloud-thing.git .

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt