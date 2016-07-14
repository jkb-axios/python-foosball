#!/usr/bin/env python

import os, sys, time, logging, signal
import RPi.GPIO as GPIO
from mongo_helper import MongoHelper as DatabaseHelper

# Define modes
mode_TEST=0 # Test mode, doesn't configure GPIO
mode_SENSOR_PER_GOAL=1 # Standard configuration
mode_TOGGLE_SENSOR=2 # Alternate configuration

# MongoDB connection info
DB_IP='127.0.0.1' # TODO
DB_PORT='27017'
DB_NAME='foosball'

# GPIO info - use BCM 23 and 24 (RPi2 board pins 16 and 18) for input
PIN_NUMBERING=GPIO.BCM
SENSOR1_PIN=23 # VISITOR GOAL SENSOR
SENSOR2_PIN=24 # HOME GOAL SENSOR
PIN_BOUNCETIME=500 #TODO - increase to avoid double trigger? (orig 300)
SENSOR_MODE=mode_TOGGLE_SENSOR #TODO - set this depending on sensor configuration

class GoalReader(object):
    def __init__(self, database_ip=DB_IP, database_port=DB_PORT, database_name=DB_NAME, sensor_mode=mode_SENSOR_PER_GOAL):
        self.log = logging.getLogger('GoalReader')
        self.log.setLevel(logging.DEBUG)
        fh = logging.FileHandler('/var/log/goalreader.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        self.log.info('Creating DatabaseHelper w/ ip=%s port=%s db=%s'%(database_ip, database_port, database_name))
        self.db = DatabaseHelper(database_ip, database_port, database_name))
        self.setupGPIO(mode=sensor_mode)

        # flag used in mode 1 (TOGGLE_SENSOR), set when goal sensor 2 is triggered
        self.__homeGoal=False

    # Functions for mode_SENSOR_PER_GOAL
    def spg_sensor1(self, channel=None):
        self.log.info('Sensor 1 triggered (BCM PIN %s)'%(SENSOR1_PIN))
        self.log.debug('Sensor 1 triggered: send visitor goal')
        status, reason = self.db.sendVisitorGoal()
        self.log.debug('STATUS: '+str(status))
        self.log.debug('REASON: '+str(reason))

    def spg_sensor2(self, channel=None):
        self.log.info('Sensor 2 triggered (BCM PIN %s)'%(SENSOR2_PIN))
        self.log.debug('Sensor 2 triggered: send home goal')
        status, reason = self.db.sendHomeGoal()
        self.log.debug('STATUS: '+str(status))
        self.log.debug('REASON: '+str(reason))

    # Functions for mode_TOGGLE_SENSOR
    def ts_sensor1(self, channel=None):
        self.log.info('Sensor 1 triggered (BCM PIN %s)'%(SENSOR1_PIN))
        if self.__homeGoal:
            self.log.debug('Sensor 1 triggered: homeGoal flag set, sending home goal')
            status, reason = self.db.sendHomeGoal()
            self.log.debug('STATUS: '+str(status))
            self.log.debug('REASON: '+str(reason))
            self.log.debug('Sensor 1 triggered: processed goal, resetting homeGoal flag')
            self.__homeGoal=False
        else:
            self.log.debug('Sensor 1 triggered: homeGoal flag unset, sending visitor goal')
            status, reason = self.db.sendVisitorGoal()
            self.log.debug('STATUS: '+str(status))
            self.log.debug('REASON: '+str(reason))

    def ts_sensor2(self, channel=None):
        self.log.info('Sensor 2 triggered (BCM PIN %s)'%(SENSOR2_PIN))
        self.log.debug('Sensor 2 triggered: set homeGoal flag')
        self.__homeGoal=True

    # GPIO configuration functions
    def setupGPIO(self, mode):
        if mode==mode_TEST:
            self.log.debug('setupGPIO: TEST mode')
            return
        self.log.info('Configuring GPIO for goal sensors - Sensor1=%s  Sensor2=%s  bouncetime=%s'%(SENSOR1_PIN,SENSOR2_PIN,PIN_BOUNCETIME))
        GPIO.setmode(PIN_NUMBERING)
        GPIO.setup(SENSOR1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(SENSOR2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if mode == mode_SENSOR_PER_GOAL:
            self.log.debug('setupGPIO: SENSOR_PER_GOAL mode')
            GPIO.add_event_detect(SENSOR1_PIN, GPIO.RISING, callback=self.spg_sensor1, bouncetime=PIN_BOUNCETIME)
            GPIO.add_event_detect(SENSOR2_PIN, GPIO.RISING, callback=self.spg_sensor2, bouncetime=PIN_BOUNCETIME)
        elif mode == mode_TOGGLE_SENSOR:
            self.log.debug('setupGPIO: TOGGLE_SENSOR mode')
            GPIO.add_event_detect(SENSOR1_PIN, GPIO.RISING, callback=self.ts_sensor1, bouncetime=PIN_BOUNCETIME)
            GPIO.add_event_detect(SENSOR2_PIN, GPIO.RISING, callback=self.ts_sensor2, bouncetime=PIN_BOUNCETIME)

    def cleanup(self):
        self.log.info('Cleaning up GPIO configuration')
        GPIO.cleanup()


if __name__=='__main__':
    def handleSignal(signal, frame): pass
    signal.signal(signal.SIGINT, handleSignal)
    signal.signal(signal.SIGTERM, handleSignal)

    reader=GoalReader(DB_IP, DB_PORT, DB_NAME, SENSOR_MODE)
    signal.pause() # wait for signal
    reader.cleanup()

