FROM python:3.7

WORKDIR /home/pi/ulab_thing

COPY ./ /home/pi/ulab_thing/

RUN pip install -r requeriments.txt