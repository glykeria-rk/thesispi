#!/usr/bin/env python3

import os
import RPi.GPIO as GPIO
import imutils
import pyzbar.pyzbar as pyzbar
from mfrc522 import SimpleMFRC522
from time import sleep
import cv2
import signal
import sys
import threading
import requests
import datetime
import click

#BASE_URL = "https://flex-dot-thesis-lock.ew.r.appspot.com/"
BASE_URL = None

NR_OF_SECONDS_LOCK = 2
NR_OF_SECONDS_BLOCK = 10

LAST_CHECK = datetime.datetime.fromtimestamp(0)

LOCK_PIN = 26
BUZZER_PIN = 16
GPIO.setmode(GPIO.BCM)
GPIO.setup(LOCK_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.output(LOCK_PIN, GPIO.LOW)
GPIO.output(BUZZER_PIN, GPIO.LOW)

reader = SimpleMFRC522()
cap = cv2.VideoCapture(0)

JSON_URL = " https://api.jsonbin.io/b/5f526b43993a2e110d3e53d6/4"

def fetch_ip():
    global BASE_URL
    r = requests.get(JSON_URL)
    content = r.json()
    ip_server = content["ip_server"]
    BASE_URL = ip_server


def show_feedback(text):
    click.echo("{}: {}".format(datetime.datetime.now(), text))


@click.group()
def cli():
    pass

def teardown():
    cap.release()
    cv2.destroyAllWindows()
    GPIO.cleanup()

def signal_handler(sig, frame):
    click.echo('Exiting. Cleaning up...')
    teardown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def check_access_by_tag_id(tag_id):
    url = BASE_URL + "verify-rfid-id-access/"
    payload = {"rfid_id": str(tag_id)}

    r = requests.post(url, json=payload)
    return r.status_code == 200
 
def check_access_by_jwt(jwt):
    url = BASE_URL + "verify-qr-code-access/"
    payload = {"user_jwt_token": jwt} 

    r = requests.post(url, json=payload)
    return r.status_code == 200

def open_lock(seconds: int) -> None:
    GPIO.output(LOCK_PIN, GPIO.HIGH)
    sleep(seconds)
    GPIO.output(LOCK_PIN, GPIO.LOW)

def sound_buzzer_access_approved() -> None:
    for _ in range(3):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        sleep(100/1000)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        sleep(50/1000)

def sound_buzzer_access_denied() -> None:
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

def light_led(color) -> None:
    pass
    
def verify_rfid_id(_id):
    if _id and check_access_by_tag_id(_id):
        show_feedback("NFC accepted")
        sound_buzzer_access_approved()
        open_lock(NR_OF_SECONDS_LOCK)
    else:
        show_feedback("NFC denied")
        sound_buzzer_access_denied()

def nfc_checker():
    global LAST_CHECK
    while True:
        _id, text = reader.read()  # blocking
        if LAST_CHECK < datetime.datetime.now() - datetime.timedelta(seconds=NR_OF_SECONDS_BLOCK):
            LAST_CHECK = datetime.datetime.now()
            verify_rfid_id(_id)
       
def verify_jwt(jwt):
    if check_access_by_jwt(jwt):
        show_feedback("QR accepted")
        sound_buzzer_access_approved()
        open_lock(NR_OF_SECONDS_LOCK)
    else:
        show_feedback("QR denied")
        sound_buzzer_access_denied()

def qr_checker():
    global LAST_CHECK
    while True:
        _, img = cap.read()
        img = imutils.resize(img, width=400)
        decodedObjects = pyzbar.decode(img)

        for jwt in decodedObjects:
            if LAST_CHECK < datetime.datetime.now() - datetime.timedelta(seconds=NR_OF_SECONDS_BLOCK):
                LAST_CHECK = datetime.datetime.now()
                jwt_str = jwt.data.decode("utf-8")
                verify_jwt(jwt_str)

@cli.command()       
def main():
    """
    This is the main function that the Pi
    will use to listen for input, either
    from the camera (QR-code) or the 
    RFID-reader.
    """
    fetch_ip()
    nfc_checker_thread = threading.Thread(target=nfc_checker)
    qr_checker_thread = threading.Thread(target=qr_checker)

    nfc_checker_thread.start()
    qr_checker_thread.start()

    click.echo("Listening for input")


@cli.command()
def read():
    """
    This function is used to get the id
    from an RFID tag. This can then be used to
    assign this ID to a user using the admin app.
    """
    click.echo("Hold a tag in front of the reader to read the ID...")
    _id, text = reader.read()  # blocking
    click.echo(str(_id))
    teardown()

if __name__ == '__main__':
    cli()
