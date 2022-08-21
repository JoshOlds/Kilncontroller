from max31856_driver import max31856
import spidev
import threading
import time
from datetime import datetime


class MAXController:

    def __init__(self, kiln, bus_number, device_id, sleep_time):
        self.kiln = kiln

        # Enable SPI
        spi = spidev.SpiDev()

        # Open connection to bus and device (chip select pin)
        spi.open(bus_number, device_id)

        # Set SPI speed and mode
        spi.max_speed_hz = 4000000
        spi.mode = 0b01
        spi.lsbfirst = False

        self.max31856 = max31856.Max31856(spi)

        self.spi_thread = None
        self._spi_thread_flag = False
        self.spi_thread_running = False
        self.sleep_time = sleep_time

        self.thermocouple_temp_callback = None
        self.cold_junction_temp_callback = None
        self.fault_callback = None

    def start_spi_thread(self):
        if not self._spi_thread_flag:
            # print("Starting SPI Thread...")
            self._spi_thread_flag = True
            self.spi_thread = threading.Thread(group=None, target=self._run, name="max31856_spi_thread")
            self.spi_thread.start()
            return True
        else:
            print("MAX13856 Controller: Error, SPI thread already running")
            return False

    def _run(self):
        self.spi_thread_running = True
        while self._spi_thread_flag:

            # Read the cold junction temperature
            cold_junc_temp = self.max31856.read_cold_junction_temperature()
            if self.cold_junction_temp_callback is not None:
                self.cold_junction_temp_callback(cold_junc_temp)
            if self.kiln is not None:
                self.kiln.set_cold_junc_temp_c(cold_junc_temp)

            # Read the thermocouple temperature
            thermocouple_temp = self.max31856.read_thermocouple_temperature()
            if self.thermocouple_temp_callback is not None:
                self.thermocouple_temp_callback(thermocouple_temp)
            if self.kiln is not None:
                self.kiln.set_thermocouple_temp_c(thermocouple_temp)

            # Update any fault statuses
            self.max31856.read_faults()
            if self.fault_callback is not None:
                if self.max31856.has_fault():
                    self.fault_callback(self)

            time.sleep(self.sleep_time)

        self.spi_thread_running = False

    def stop_spi_thread(self):
        self._spi_thread_flag = False
        # wait for thread to shutdown
        while self.spi_thread_running:
            time.sleep(0.1)


def print_thermo_temp(val):
    temp_c = str(round(val, 1))
    temp_f = str(round(((val * 1.8) + 32), 1))
    print("Thermocouple Temp:  " + temp_c + "C,  " + temp_f + "F")


def print_cold_junc_temp(val):
    temp_c = str(round(val, 1))
    temp_f = str(round(((val * 1.8) + 32), 1))
    print("Cold Junction Temp:  " + temp_c + "C,  " + temp_f + "F")


def fault_callback(controller: MAXController):
    controller.max31856.print_faults()


if __name__ == "__main__":
    print("Running max31856_driver Controller main...")

    # Create controller, bus 0, device 0, ~1 second poll rate
    cont = MAXController(None, 0, 0, 1)

    # Set callback functions for temperature and fault updates
    cont.thermocouple_temp_callback = print_thermo_temp
    cont.cold_junction_temp_callback = print_cold_junc_temp
    cont.fault_callback = fault_callback

    # Run SPI thread
    cont.start_spi_thread()

    time.sleep(999999)

    cont.stop_spi_thread()
