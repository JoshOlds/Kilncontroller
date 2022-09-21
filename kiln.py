import time
import curses
from datetime import datetime
import csv
from max31856_driver import max_controller
from scheduler import Scheduler, ScheduleRamp, ScheduleHold
from pi_controller import PIController
from throttle_interface import ThrottleInterface


class Kiln:

    def __init__(self):
        # Thermocouple Amp Values
        self.max_controller = max_controller.MAXController(self, 0, 0, 1)
        self.thermocouple_temp_c = 0
        self.thermocouple_temp_f = 0
        self.cold_junc_temp_c = 0
        self.cold_junc_temp_f = 0
        time.sleep(1)  # Wait for initial readings

        # Scheduler Values
        self.scheduler = Scheduler(self)
        self.setpoint_f = 0

        # Warmup ramp
        self.scheduler.schedule.append(ScheduleRamp(100, 100))

        # Fast ramp to 200
        self.scheduler.schedule.append(ScheduleRamp(300, 200))

        # Hold at 200 for 2 hours
        self.scheduler.schedule.append(ScheduleHold(200, 120))

        # 3 Stage ramp to 1950 End Temp
        self.scheduler.schedule.append(ScheduleRamp(200, 550))
        self.scheduler.schedule.append(ScheduleRamp(300, 1150))
        self.scheduler.schedule.append(ScheduleRamp(400, 1950))

        # PI Controller Values
        self.pi_controller = PIController(self, 2, 0.01, 1)
        self.throttle_percent = 0

        # Throttle Interface Values
        self.throttle_interface = ThrottleInterface(36)

        # Misc Values
        self.start_time = datetime.now()
        self.file_write_interval = 0

        # Curses for screen writing
        self.stdscr = curses.initscr()
        curses.curs_set(False)
        self.stdscr.clear()
        self.stdscr.refresh()

        # Start the threads
        self.max_controller.start_spi_thread()
        self.scheduler.start_scheduler_thread()
        self.pi_controller.start_pi_thread()
        self.throttle_interface.start_throttle_thread()

    def set_thermocouple_temp_c(self, temp_c):
        self.thermocouple_temp_c = temp_c
        self.thermocouple_temp_f = (temp_c * 1.8) + 32

    def set_cold_junc_temp_c(self, temp_c):
        self.cold_junc_temp_c = temp_c
        self.cold_junc_temp_f = (temp_c * 1.8) + 32

    def set_throttle(self, throttle_percent):
        if throttle_percent < 0:
            throttle_percent = 0
        if throttle_percent > 100:
            throttle_percent = 100
        self.throttle_percent = throttle_percent
        self.throttle_interface.set_throttle(throttle_percent)

    def run(self):
        with open("kiln.csv", 'w') as file:
            writer = csv.writer(file)
            while True:
                text = "==========================================================\n"
                text += "Kiln Controller\n\n"
                text += "Elapsed Runtime: " + str(datetime.now() - self.start_time).split('.')[0] + "\n"
                text += "Ambient Temperature: " + str(round(self.cold_junc_temp_f, 1)) + "F\n\n"
                text += self.scheduler.get_schedule_stats()
                text += "\nThermocouple Temperature: " + str(round(self.thermocouple_temp_f, 1)) + "F\n"
                text += "Target Temperature: " + str(round(self.setpoint_f, 1)) + "F\n"
                text += "Error: " + str(round(self.pi_controller.error, 1)) + "F\n"
                text += "Throttle: " + str(round(self.throttle_percent, 1)) + "%\n\n"
                text += self.pi_controller.get_values(2) + "\n"
                text += "==========================================================\n"
                self.stdscr.erase()
                self.stdscr.addstr(0, 0, text)
                self.stdscr.refresh()
                if self.file_write_interval == 10:
                    self.file_write_interval = 0
                    writer.writerow(
                        ["Temp", round(self.thermocouple_temp_f, 1), "Tgt", round(self.setpoint_f, 1), "Tht",
                         round(self.throttle_percent, 1), "P", round(self.pi_controller.p_value, 1), "I",
                         round(self.pi_controller.i_value, 1)])
                else:
                    self.file_write_interval += 1
                time.sleep(1)


if __name__ == "__main__":
    kiln = Kiln()
    kiln.run()
