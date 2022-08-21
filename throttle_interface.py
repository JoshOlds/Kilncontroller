import threading
import time

import RPi.GPIO as GPIO


class ThrottleInterface:

    def __init__(self, relay_pin):
        self.relay_pin = relay_pin

        # Setup Relay GPIO Output
        GPIO.setmode(GPIO.BOARD)  # Set BOARD output to use Raspberry Pi header numeric pin numbers
        GPIO.setup(relay_pin, GPIO.OUT, initial=GPIO.LOW)  # Output pin, default to off

        # Throttle Variables
        self._throttle_command = 0

        self.throttle_thread = None
        self._throttle_thread_flag = False
        self.throttle_thread_running = False

    def start_throttle_thread(self):
        if not self._throttle_thread_flag:
            # print("Starting Throttle Thread...")
            self._throttle_thread_flag = True
            self.throttle_thread = threading.Thread(group=None, target=self._run, name="throttle_interface_thread")
            self.throttle_thread.start()
            return True
        else:
            # print("ThrottleInterface: Tried to start Throttle thread, but thread is already running!")
            return False

    def _run(self):
        self.throttle_thread_running = True
        while self._throttle_thread_flag:

            # Grab the current throttle command - since it may change during runtime
            throttle = self._throttle_command
            # print("Throttle Command: " + str(throttle) + "%")

            # Throttle control operates on a 10-second burst window. 100% = 10 seconds on; 50% = 5 sec on, 5 sec off

            # Only turn on the element is throttle is greater than zero
            if throttle > 0:
                GPIO.output(self.relay_pin, GPIO.HIGH)
                # print("Throttle On")
            else:
                GPIO.output(self.relay_pin, GPIO.LOW)

            # Sleep for the on-time
            time.sleep(0.1 * throttle)

            # Only turn element off if throttle not full throttle (100%)
            if throttle < 100:
                GPIO.output(self.relay_pin, GPIO.LOW)
                # print("Throttle Off")
                # Sleep for the remainder of the time period
                time.sleep(0.1 * (100 - throttle))

        GPIO.output(self.relay_pin, GPIO.LOW)
        # print("Throttle Off")
        self.throttle_thread_running = False

    def set_throttle(self, throttle_command):
        throttle = int(throttle_command)
        if throttle < 0 or throttle > 100:
            print(
                "ThrottleInterface: Error - Invalid Throttle Command. Throttle must be an integer between 0 and 100. "
                "Setting Throttle to 0!")
            self._throttle_command = 0
            return False
        self._throttle_command = throttle_command
        return True

    def stop_throttle_thread(self):
        self._throttle_thread_flag = False
        # wait for thread to shutdown
        while self.throttle_thread_running:
            time.sleep(0.1)

    def cleanup(self):
        GPIO.cleanup()

