#!/usr/bin/env python

import os, sys, time, logging, signal
import RPi.GPIO as GPIO
from foosball_utils import DigitalFoosballSimulator as DFSim

# Define modes
mode_TEST=0 # Test mode, doesn't configure GPIO
mode_SENSOR_PER_GOAL=1 # Standard configuration
mode_TOGGLE_SENSOR=2 # Alternate configuration

# DigitalFoosball server info
SERVER_IP='127.0.0.1' # TODO
SERVER_PORT='80'

# GPIO info - use BCM 23 and 24 (RPi2 board pins 16 and 18) for input
PIN_NUMBERING=GPIO.BCM
SENSOR1_PIN=23 # VISITOR GOAL SENSOR
SENSOR2_PIN=24 # HOME GOAL SENSOR
PIN_BOUNCETIME=500 #TODO - increase to avoid double trigger? (orig 300)
SENSOR_MODE=mode_TOGGLE_SENSOR #TODO - set this depending on sensor configuration

class GoalReader(object):
    def __init__(self, server_ip='127.0.0.1', server_port='80', sensor_mode=mode_SENSOR_PER_GOAL):
        self.log = logging.getLogger('GoalReader')
        self.log.setLevel(logging.DEBUG)
        fh = logging.FileHandler('/var/log/goalreader.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        self.log.info('Creating DigitalFoosballSimulator w/ ip=%s  port=%s'%(server_ip,server_port))
        self.sim=DFSim(ip=server_ip, port=server_port)
        self.setupGPIO(mode=sensor_mode)

        # flag used in mode 1 (TOGGLE_SENSOR), set when goal sensor 2 is triggered
        self.__homeGoal=False

    # Functions for mode_SENSOR_PER_GOAL
    def spg_sensor1(self, channel=None):
        self.log.info('Sensor 1 triggered (BCM PIN %s)'%(SENSOR1_PIN))
        self.log.debug('Sensor 1 triggered: send visitor goal')
        status, reason = self.sim.sendVisitorGoal()
        self.log.debug('STATUS: '+str(status))
        self.log.debug('REASON: '+str(reason))

    def spg_sensor2(self, channel=None):
        self.log.info('Sensor 2 triggered (BCM PIN %s)'%(SENSOR2_PIN))
        self.log.debug('Sensor 2 triggered: send home goal')
        status, reason = self.sim.sendHomeGoal()
        self.log.debug('STATUS: '+str(status))
        self.log.debug('REASON: '+str(reason))

    # Functions for mode_TOGGLE_SENSOR
    def ts_sensor1(self, channel=None):
        self.log.info('Sensor 1 triggered (BCM PIN %s)'%(SENSOR1_PIN))
        if self.__homeGoal:
            self.log.debug('Sensor 1 triggered: homeGoal flag set, sending home goal')
            status, reason = self.sim.sendHomeGoal()
            self.log.debug('STATUS: '+str(status))
            self.log.debug('REASON: '+str(reason))
            self.log.debug('Sensor 1 triggered: processed goal, resetting homeGoal flag')
            self.__homeGoal=False
        else:
            self.log.debug('Sensor 1 triggered: homeGoal flag unset, sending visitor goal')
            status, reason = self.sim.sendVisitorGoal()
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

    reader=GoalReader(SERVER_IP, SERVER_PORT, SENSOR_MODE)
    signal.pause() # wait for signal
    reader.cleanup()

