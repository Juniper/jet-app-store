"""
Copyright 2018 Juniper Networks Inc.

Using this JET APP user can get notification on intrested event topic .
"""

#!/usr/bin/env python

import argparse
import os
import time
import logging
import sys

import struct
import logging
from importlib import import_module
import paho.mqtt.client as mqtt
import json
import collections
import logging

decoder = json.JSONDecoder()
logger = logging.getLogger(__name__)

# Logging Parameters
DEFAULT_LOG_FILE_NAME = "/var/tmp/sampleNotifierApp.log"
DEFAULT_LOG_LEVEL = logging.DEBUG

# Enable Logging to a file
logging.basicConfig(filename=DEFAULT_LOG_FILE_NAME, level=DEFAULT_LOG_LEVEL)

# To display the messages from junos-jet-api package on the screen uncomment the below line
myLogHandler = logging.getLogger()
myLogHandler.setLevel(logging.INFO)
logChoice = logging.StreamHandler(sys.stdout)
logChoice.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logChoice.setFormatter(formatter)
myLogHandler.addHandler(logChoice)

DEFAULT_MQTT_PORT = 1883            # Default JET notification port
DEFAULT_MQTT_IP = '127.0.0.1'       # Default JET address for MQTT
DEFAULT_MQTT_TIMEOUT = 60           # Default Notification channel timeout

logger = logging.getLogger(__name__)

handlers = collections.defaultdict(set)

def handleEvents1(message):
    print "Event Received : " + message['jet-event']['event-id']
    print "Attributes : ", message['jet-event']['attributes']
    return

def on_message_cb(client, obj, msg):

    global handlers

    payload = msg.payload
    topic = msg.topic
    json_data = None
    json_data, end = decoder.raw_decode(payload)
    if json_data is None:
        logger.error('Received event has invalid JSON format')
        logger.error('Received payload: %s' % payload)
    if len(payload) != end:
        logger.error('Received event has additional invalid JSON format')
        logger.error('It has the following additional content: %s' % payload[end:])
    callback_called = False
    for cbs in handlers:
        if cbs != '#':
            if mqtt.topic_matches_sub(cbs, topic):
                for cb in handlers.get(cbs, []):
                    cb(json_data)
                    callback_called = True

    if callback_called == False:
        for cb in handlers.get('#', []):
            logger.debug('Sending data to callback %s' % cb)
            cb(json_data)

def mqtt_connect():
    try:
        mqtt_client =mqtt.Client()
        mqtt_client.connect(DEFAULT_MQTT_IP, DEFAULT_MQTT_PORT, DEFAULT_MQTT_TIMEOUT)
        mqtt_client.loop_start()
        mqtt_client.on_message = on_message_cb

    except struct.error as err:
        message = err.message
        err.message = 'Invalid argument value passed in %s at line no. %s\nError: %s' \
                        % (traceback.extract_stack()[0][0], traceback.extract_stack()[0][1],  message)
        logger.error('%s' %(err.message))
        raise err
    except Exception, tx:
        tx.message = 'Could not connect to the JET notification server'
        logger.error('%s' %(tx.message))
        raise Exception(tx.message)

    return mqtt_client


def mqtt_subscribe(mqtt_client, topic, callback):
    global handlers
    mqtt_client.subscribe(topic)
    handlers[topic].add(callback)

def mqtt_unsubscribe(mqtt_client, topic):
    global handlers
    mqtt_client.unsubscribe(topic)
    handlers.pop(str(topic), None)

def mqtt_disconnect(mqtt_client):
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


def Main():
    global handlers

    print "Connecting to mqtt broker"
    mqtt_client = mqtt_connect()

    # Create the topic
    #ifatopic = "/junos/events/kernel/interfaces/ifa/add/ge-0/0/2.0/inet/1.1.1.1/32"
    alltopics = "/junos/events/#"   # This will let you recieve all the notifications generated on the box
    
    # Subscribe for events
    mqtt_subscribe(mqtt_client, alltopics , handleEvents1)
    print "Subscribed to topic", alltopics

    time.sleep(20)

    # Unsubscribe events
    mqtt_unsubscribe(mqtt_client, alltopics)

    print "Disconnecting from the broker"
    # Close session
    mqtt_disconnect(mqtt_client)

    return

if __name__ == '__main__':
    Main()
