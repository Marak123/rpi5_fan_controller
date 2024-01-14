########################################################
#
#  Created by: Marak123
#  Source: https://github.com/Marak123/rpi5_fan_controller
#
########################################################


from sys import exit as sysexit
from os import _exit as osexit
from subprocess import run as srun, PIPE
from time import sleep
from datetime import timedelta as td, datetime as dt
from enum import Enum

import os

## Use step values to activate desired FAN value
MIN_TEMP = 35
MAX_TEMP = 70

## Change these values if you want a more/less responsive fan behavior
SLEEP_TIMER = 1      # Time interval between temperature checks
TICKS = 2
TICK_INTERVAL = 1
AVG_SIZE = 20        # One temperature reading for the amount of time specified above
DEBUG = False

## These should no be changed
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
RPM_FAN_FILE = '/sys/class/hwmon/hwmon1/fan1_input'
WARNING_LIGHT_FILE = '/sys/class/leds/PWR/brightness'
TEMP_CPU_FILE = '/sys/class/thermal/thermal_zone0/temp'
PWM_FAN_CONTROL_FILE = '/sys/class/hwmon/hwmon1/pwm1'    # Value 1-255


class RotateList:
    def __init__(self, size):
        self.size = size
        self.internal_list = []

    def append(self, element):
        if len(self.internal_list) < self.size:
            self.internal_list.append(element)
        else:
            self.internal_list.pop(0)
            self.internal_list.append(element)

    def get_list(self):
        return self.internal_list

    def getAverage(self):
        if not self.internal_list:
            return None
        return sum(self.internal_list) / len(self.internal_list)


def setSpeedFan(speedMode):
    return os.popen(f'echo {speedMode} | sudo tee -a {PWM_FAN_CONTROL_FILE} > /dev/null').read()

def getCurrentFanSpeed():
    return int(os.popen(f'cat {PWM_FAN_CONTROL_FILE}').read())

def getCurrentTemp():
    temp = int(os.popen(f'cat {TEMP_CPU_FILE}').read())

    try:
        return temp / 1000
    except (IndexError, ValueError) as e:
        return 40

def getFanRPM():
    return int(os.popen(f'cat {RPM_FAN_FILE}').read())

def setWarningLight(state: int):
    return os.popen(f'echo {state} | sudo tee -a {WARNING_LIGHT_FILE} > /dev/null').read()

def getWarningLightState():
    return int(os.popen(f'cat {WARNING_LIGHT_FILE}').read())


def main(debug=False):
    print("Running FAN control for RPI5 Ubuntu")
    t0 = dt.now()

    oldSpeed = 0
    ticks = 0

    speed = 100

    warning_light = 0

    temp_list = RotateList(AVG_SIZE)

    while True:
        sleep(SLEEP_TIMER) # force sleep, just to reduce polling calls
        t1 = dt.now()

        temp_list.append(getCurrentTemp())

        if(t1 + td(minutes=TICKS) > t0):
            t0 = t1
            avg_temp = temp_list.getAverage()

            if avg_temp < MIN_TEMP:
                speed = 0
            elif avg_temp > MAX_TEMP:
                speed = 255
            else:
                speed = int(((avg_temp - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)) * 253) + 1

            if oldSpeed != speed:
                if debug:
                    print(f'Old Speed: {oldSpeed} \t New Speed: {speed} \t Current Temp Average: {temp_list.getAverage()}')

                print(f'{"#"*30}\n' +
                      f'Updating fan speed!\t{t0.strftime(DATETIME_FORMAT)}\n' +
                      f'CPU TEMP: {avg_temp}ºC\n' +
                      f'FAN speed will be set to: {speed}\n' +
                      f'{"#"*30}\n')

                if debug:
                    print(f'Confirm FAN set to speed: {getCurrentFanSpeed()}')

                # Updating values for comparison
                oldSpeed = speed
                ticks = 0

            if getCurrentFanSpeed() != speed:
                setSpeedFan(speed)
                if debug:
                    print(f'Set New Speed: {speed}')

            if getCurrentFanSpeed() != 0 and getFanRPM() == 0:
                for x in range(6):
                    setWarningLight(1)
                    sleep(0.2)
                    setWarningLight(0)
                    sleep(0.2)

                setWarningLight(1)
                warning_light = 1

                if debug:
                    print("Fan Error Speed: (Fan Set Speed:", getCurrentFanSpeed(), "; Fan Acualy Speed:", getFanRPM(), ")")

            elif warning_light == 1 and getCurrentFanSpeed() != 0 and getFanRPM() != 0 and getWarningLightState() != 0:
                setWarningLight(0)
                warning_light = 0


            # Log minor details
            ticks += 1
            if(ticks > TICKS * TICK_INTERVAL):
                ticks = 0
                print(f'Current Temp is: {avg_temp}ºC \t {t0.strftime(DATETIME_FORMAT)}' +
                      (f'\t Fan Set Speed: {getCurrentFanSpeed()} \t Fan RPM: {getFanRPM()} \t Temp List: {temp_list.get_list()}' if debug else ''))


## RUN SCRIPT
if __name__ == '__main__':
    try:
        main(DEBUG)
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sysexit(130)
        except SystemExit:
            osexit(130)