import threading
import time
from datetime import datetime


class Monitor:

    def __init__(self, kiln, max_error, max_constant_error, max_constant_error_time_minutes):
        self.kiln = kiln
        self.max_error = max_error
        self.max_constant_error = max_constant_error
        self.max_constant_error_time_minutes = max_constant_error_time_minutes

        self.monitor_thread = None
        self._monitor_thread_flag = False
        self.monitor_thread_running = False

        self.last_ok_time = datetime.now()
        self.error = 0

    def is_in_error_state(self):
        if self.error > self.max_error or self.error > self.max_constant_error:
            return True
        return False

    def start_monitor_thread(self):
        if not self.monitor_thread_running:
            self._monitor_thread_flag = True
            self.monitor_thread = threading.Thread(group=None, target=self._run, name="monitor_thread")
            self.monitor_thread.start()
            return True
        else:
            print("Monitor: Monitor thread already running!")
            return False

    def stop_monitor_thread(self):
        self._monitor_thread_flag = False
        while self.monitor_thread_running:
            time.sleep(0.1)

    def shutdown_kiln(self):
        self.kiln.shutdown()
        self._monitor_thread_flag = False

    def _run(self):
        self.monitor_thread_running = True
        while self._monitor_thread_flag:
            self.error = abs(self.kiln.setpoint_f - self.kiln.thermocouple_temp_f)

            # Shutdown if max error exceeded
            if self.error > self.max_error:
                self.shutdown_kiln()
            # If shutdown exceeds constant error for time limit
            elif ((datetime.now() - self.last_ok_time).seconds / 60) > self.max_constant_error_time_minutes:
                self.shutdown_kiln()
            elif self.error < self.max_constant_error:
                self.last_ok_time = datetime.now()
            time.sleep(1)

        self.monitor_thread_running = False
