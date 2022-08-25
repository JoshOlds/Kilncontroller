import threading
import time
import math
from datetime import datetime
from enum import Enum


class ScheduleRamp:

    def __init__(self, rate_deg_f, target_f):
        self.start_time = datetime.now()
        self.start_temp = 0
        self.rate_deg_f = rate_deg_f
        self.target_f = target_f

    def get_stats(self):
        text = "RAMP Step\n"
        text += "RAMP at: " + str(self.rate_deg_f) + "F per hour\n"
        text += "RAMP End Temp: " + str(round(self.target_f, 1)) + "F\n"
        return text


class ScheduleHold:

    def __init__(self, hold_temp_f, hold_time_minutes):
        self.start_time = datetime.now()
        self.remaining_minutes = hold_time_minutes
        self.hold_temp_f = hold_temp_f
        self.hold_time_minutes = hold_time_minutes

    def get_stats(self):
        text = "HOLD Step\n"
        text += "HOLD at: " + str(self.hold_temp_f) + "F\n"
        text += "Remaining Minutes: " + str(math.ceil(self.remaining_minutes)) + "\n"
        return text


class Scheduler:

    def __init__(self, kiln):
        self.kiln = kiln
        self.schedule = list()
        self._schedule_index = 0
        self._setpoint_f = 0

        self.schedule_thread = None
        self._schedule_thread_flag = False
        self.schedule_thread_running = False

    def get_schedule_stats(self):
        text = "Currently on Schedule Step: " + str(self._schedule_index + 1) + " of " + str(len(self.schedule)) + "\n"
        if self._schedule_index < len(self.schedule):
            text += self.schedule[self._schedule_index].get_stats()
        return text

    def set_setpoint(self, setpoint_f):
        self._setpoint_f = setpoint_f
        self.kiln.setpoint_f = setpoint_f

    def get_setpoint(self):
        return self._setpoint_f

    def start_scheduler_thread(self):
        if not self._schedule_thread_flag:
            # print("Scheduler: Starting Scheduler Thread...")
            self._schedule_thread_flag = True
            self.schedule_thread = threading.Thread(group=None, target=self._run, name="scheduler_thread")
            self.schedule_thread.start()
            return True
        else:
            print("Scheduler: Tried to start Scheduler thread, but thread is already running!")
            return False

    def _run(self):
        self.schedule_thread_running = True
        time.sleep(2)
        while self._schedule_thread_flag:

            # If schedule is complete
            if self._schedule_index >= len(self.schedule):
                # print("Scheduler: Schedule Complete!")
                self.set_setpoint(0)
                self._schedule_thread_flag = False
                self.schedule_thread_running = False
                return

            step = self.schedule[self._schedule_index]

            # Dispatch to appropriate step type function
            if isinstance(step, ScheduleRamp):
                self._ramp_loop(step)
            if isinstance(step, ScheduleHold):
                self._hold_loop(step)

    def _hold_loop(self, hold: ScheduleHold):
        self._setpoint_f = hold.hold_temp_f
        hold.start_time = datetime.now()

        while self._schedule_thread_flag:
            # Check the time to see if we are complete
            delta_seconds = (datetime.now() - hold.start_time).seconds
            delta_minutes = delta_seconds / 60
            hold.remaining_minutes = hold.hold_time_minutes - delta_minutes
            if delta_minutes > hold.hold_time_minutes:
                # print("Scheduler: HOLD step complete!")
                self._schedule_index += 1
                return
            time.sleep(1)

    def _ramp_loop(self, ramp: ScheduleRamp):
        ramp.start_time = datetime.now()
        ramp.start_temp = self.kiln.thermocouple_temp_f

        while self._schedule_thread_flag:
            # Check temp to see if we are complete
            if self.kiln.thermocouple_temp_f >= ramp.target_f:
                # print("Scheduler: RAMP step complete!")
                self._schedule_index += 1
                return

            delta_seconds = (datetime.now() - ramp.start_time).seconds
            delta_minutes = delta_seconds / 60
            delta_hours = delta_minutes / 60
            setpoint = ramp.start_temp + (ramp.rate_deg_f * delta_hours)
            # Clamp if we are exceeding target or max
            if setpoint > ramp.target_f:
                setpoint = ramp.target_f
            self.set_setpoint(setpoint)

            time.sleep(1)
