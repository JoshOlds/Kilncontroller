import max31856
import spidev
import threading
import time


class Controller:

    def __init__(self, bus_number, device_id, sleep_time, debug=False):
        self.debug = debug

        # Enable SPI
        spi = spidev.SpiDev()

        # Open connection to bus and device (chip select pin)
        spi.open(bus_number, device_id)

        # Set SPI speed and mode
        spi.max_speed_hz = 28800
        spi.mode = 0b01
        spi.lsbfirst = False

        self.max31856 = max31856.Max31856(spi, debug=self.debug)

        self.spi_thread = None
        self._spi_thread_flag = False
        self.spi_thread_running = False
        self.sleep_time = sleep_time

        self.thermocouple_temp_callback = None
        self.cold_junction_temp_callback = None
        self.fault_callback = None

    def start_spi_thread(self):
        if not self._spi_thread_flag:
            print("Starting SPI Thread...")
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

            if self.debug:
                print("Reading CONFIG Register: ")
                self.max31856.read_data(0x00, 1)
                print("Reading THERMOCOUPLE Register: ")
                self.max31856.read_data(0x01, 1)
                print("SPI Thread Looping...")

            # Read the cold junction temperature
            cold_junc_temp = self.max31856.read_cold_junction_temperature()
            if self.cold_junction_temp_callback is not None:
                self.cold_junction_temp_callback(cold_junc_temp)

            # Read the thermocouple temperature
            thermocouple_temp = self.max31856.read_thermocouple_temperature()
            if self.thermocouple_temp_callback is not None:
                self.thermocouple_temp_callback(thermocouple_temp)

            # Update any fault statuses
            self.max31856.read_faults()
            if self.fault_callback is not None:
                if self.max31856.has_fault():
                    self.fault_callback(self)

            time.sleep(self.sleep_time)

        self.spi_thread_running = False

    def stop_spi_thread(self):
        self._spi_thread_flag = False


def print_thermo_temp(val):
    print("Thermocouple Temp: " + str(val))


def print_cold_junc_temp(val):
    print("Cold Junction Temp: " + str(val))


def fault_callback(controller: Controller):
    controller.max31856.print_faults()


if __name__ == "__main__":
    print("Running MAX31856 Controller main...")

    # Create controller, bus 0, device 0, ~1 second poll rate
    cont = Controller(0, 0, 1, debug=True)

    # Set callback functions for temperature and fault updates
    cont.thermocouple_temp_callback = print_thermo_temp
    cont.cold_junction_temp_callback = print_cold_junc_temp
    cont.fault_callback = fault_callback

    # Run SPI thread
    #cont.start_spi_thread()

    while True:
        for x in range(0, 16):
            cont.max31856.read_data(x, 20)
        time.sleep(1)
        print("\n")



    cont.stop_spi_thread()
