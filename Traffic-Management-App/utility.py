"""
Copyright 2018 Juniper Networks Inc.

This file contains the methods used for syslog subscription.
"""

import collections
import logging
import json
import struct

import paho.mqtt.client as mqtt
handlers = collections.defaultdict(set)
logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "#"                           # Implies all value
SYSLOG_TOPIC_HEADER = r"/junos/events/syslog"  # Syslog event topic header
DEFAULT_MQTT_PORT = 1883            # Default JET notification port
DEFAULT_MQTT_IP = '127.0.0.1'       # Default JET address for MQTT
DEFAULT_MQTT_TIMEOUT = 160           # Default Notification channel timeout


def createSyslogTopic(event_id=DEFAULT_TOPIC):
        """
        This method creates the syslog topic.
        :param event_id: Syslog event id. Default is all syslog events.
        :return: Returns the Topic Object
        """
        data = {}
        data['event_id'] = event_id
        data['topic'] = "{0}/{1}".format(SYSLOG_TOPIC_HEADER, data['event_id'])
        data['subscribed'] = 0
        logger.info('Successfully appended the topic %s' % data['topic'])
        return type('Topic', (), data)


def subscribe(mqtt_client, subscriptionType, handler=None, qos=0):
        """
        This method subscribes to a specific topic the client app is interested
        in. This takes subscription type and the callback function as parameters.
        When the notification for the subscribed topic is received, user passed
        callback function will be called. Callback function receives the
        notification message in json format.
        :param mqtt_client = mqtt client object to subsribe to
        :param subscriptionType : Type of notification user wants to subscribe
        :param handler: Callback function for each notification
        """
        global handlers
        topic = subscriptionType.topic
        mqtt_client.subscribe(topic, qos)
        subscriptionType.subscribed = 1
        if(handler):
            handlers[topic].add(handler)
        logger.info('Successfully subscribed to event:%s'
                    % subscriptionType.topic)


def _on_message_cb(client, obj, msg):
        """
        This method will invoke the specified callback handler by the client app
        when a notification is received by the app based on the notification type.
        :param client: the client instance for this callback
        :param obj: the private user data as set in Client() or userdata_set()
        :param msg: an instance of Message. This is a class with members topic, payload, qos, retain
        """
        payload = msg.payload
        topic = msg.topic
        json_data = None
        decoder = json.JSONDecoder()
        json_data, end = decoder.raw_decode(payload)
        if json_data is None:
            logger.error('Received event has invalid JSON format')
            logger.error('Received payload: %s' % payload)
        if len(payload) != end:
            logger.error('Received event has additional invalid JSON format')
            logger.error('It has the following additional content: %s'
                         % payload[end:])
        callback_called = False
        for cbs in handlers:
            if cbs != '#':
                if mqtt.topic_matches_sub(cbs, topic):
                    for cb in handlers.get(cbs, []):
                        cb(json_data)
                        callback_called = True

        if callback_called is False:
            for cb in handlers.get('#', []):
                logger.debug('Sending data to callback %s' % cb)
                cb(json_data)


def openNotificationSession(device=DEFAULT_MQTT_IP, port=DEFAULT_MQTT_PORT,
                             user=None, password=None, tls=None,
                             keepalive=DEFAULT_MQTT_TIMEOUT,
                             bind_address="", is_stream=False):
        """
        Create a request response session with the  JET server. Raises
        exception in case of invalid arguments or when JET notification
        server is not accessible.
        :param device: JET Server IP address. Default is localhost
        :param port: JET Notification port number. Default is 1883
        :param user: Username on the JET server, used for authentication and authorization.
        :param password: Password to access the JET server, used for authentication and authorization.
        :param keepalive: Maximum period in seconds between communications with the broker. Default is 60.
        :param bind_address: Client source address to bind. Can be used to control access at broker side.
        :return: JET Notification object.
        """
        try:
            notifier_client = mqtt.Client()
            logger.info('Connecting to JET notification server')
            notifier_client.connect(device, port, keepalive, bind_address)
            notifier_client.loop_start()
            notifier_client.on_message = _on_message_cb
        except struct.error as err:
            message = err.message
            err.message = 'Invalid argument value passed in %s at line no. %s\n\
                           Error: %s' % (traceback.extract_stack()[0][0],
                                         traceback.extract_stack()[0][1],
                                         message)
            logger.error('%s' % (err.message))
            raise err
        except Exception, tx:
            tx.message = 'Could not connect to the JET notification server'
            logger.error('%s' % (tx.message))
            raise Exception(tx.message)

        return notifier_client

