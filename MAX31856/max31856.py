# Driver for MAX31856 - Utilizes spidev for communication
# For details on the MAX31856 SPI protocol, see the datasheet:
# https://cdn-learn.adafruit.com/assets/assets/000/035/948/original/MAX31856.pdf

# Functionality that is currently unimplemented:
# - Helper function for setting the Fault Mask Register
import spidev


class Max31856:
    def __init__(self, spi: spidev, debug=False):
        self.spi = spi
        self.debug = debug

        # Configuration Register 1 Parameters
        self.config1_conversion_mode = 1  # 0 = off, 1 = auto conversion every 100ms
        self.config1_oneshot = 0  # 0 = Off, 1 = conversion on chip select when conv. mode is set off
        self.config1_open_circuit_detection = 3  # 0 = off, 1/2/3 = on - see datasheet for details
        self.config1_cold_junction_sensing = 0  # 0 = enabled, 1 = disabled
        self.config1_fault_mode = 0  # 0 = fault bits high only when fault active, 1 = latched faults
        self.config1_hz_filter_mode = 0  # 0 = 60hz, 1 = 50hz

        # Set the thermocouple mode defaults and
        self.set_thermocouple_mode("K", 16)
        self.write_config_reg_1()

        # Faults
        self.fault_cold_junc_out_of_range = False
        self.fault_thermocouple_out_of_range = False
        self.fault_cold_junc_high = False
        self.fault_cold_junc_low = False
        self.fault_thermocouple_high = False
        self.fault_thermocouple_low = False
        self.fault_voltage_out_of_range = False
        self.fault_open_circuit_thermocouple = False

        # Member Values
        self.thermocouple_temperature = 0
        self.cold_junction_temperature = 0

    def write_data(self, address, data):
        """
        Writes bytes to the specified address of the MAX31856
        :param address: Address to write to. See datasheet for spec
        :param data: The data bytes to write
        """
        # sanity check address size
        if address > 0x7F:
            print("MAX31856 Error: Byte Address out of range.")
            return
        data_bytes = [0x80 + address, data]
        print("Data to write: ")
        print(data_bytes)
        self.spi.xfer2(data_bytes)

    def read_data(self, address, number_of_bytes):
        """
        Reads bytes from the specified address of the MAX31856
        :param address: Address to read from. See datasheet for spec
        :param number_of_bytes: Number of bytes to read from the address.
        """
        # sanity check address size
        if address > 0x7F:
            print("MAX31856 Error: Byte Address out of range.")
            return
        address_bytes = [0x00 + address]
        for x in range(0, number_of_bytes):
            address_bytes.append(0x00)

        print("Address Bytes: " + str(address_bytes))

        received_bytes = self.spi.xfer2(address_bytes)

        received_bytes = received_bytes[1:]
        if self.debug:
            print(received_bytes)

        return received_bytes

    def write_config_reg_1(self):
        """
        Writes the configuration register with current config member variable values
        """
        config_data = 0x00

        if self.config1_conversion_mode:
            config_data = config_data | 0x80
        if self.config1_oneshot:
            config_data = config_data | 0x40
        if self.config1_open_circuit_detection == 1:
            config_data = config_data | 0x10
        if self.config1_open_circuit_detection == 2:
            config_data = config_data | 0x20
        if self.config1_open_circuit_detection == 3:
            config_data = config_data | 0x30
        if self.config1_cold_junction_sensing:
            config_data = config_data | 0x08
        if self.config1_fault_mode:
            config_data = config_data | 0x04
        if self.config1_hz_filter_mode:
            config_data = config_data | 0x01

        # Write the config register
        print("Config Data: ")
        print(config_data)
        self.write_data(0x00, config_data)

    def set_thermocouple_mode(self, thermocouple_type_string: str, averaging_samples: int):
        """
        Sets the thermocouple mode and sample averaging (config register 2)
        :type thermocouple_type_string: Specify thermocouple type as a single letter string. Supports types:
        B, E, J, K, N, R, S, T
        :param averaging_samples: Sample averaging amount. accepts 1, 2, 4, 8, 16
        """
        data_byte = 0x00

        if thermocouple_type_string == "B":
            data_byte = data_byte | 0x00
        elif thermocouple_type_string == "E":
            data_byte = data_byte | 0x01
        elif thermocouple_type_string == "J":
            data_byte = data_byte | 0x02
        elif thermocouple_type_string == "K":
            data_byte = data_byte | 0x03
        elif thermocouple_type_string == "N":
            data_byte = data_byte | 0x04
        elif thermocouple_type_string == "R":
            data_byte = data_byte | 0x05
        elif thermocouple_type_string == "S":
            data_byte = data_byte | 0x06
        elif thermocouple_type_string == "T":
            data_byte = data_byte | 0x07
        else:
            print("MAX31856 Error: Invalid thermocouple type.")
            return

        if averaging_samples == 1:
            data_byte = data_byte | 0x00
        elif averaging_samples == 2:
            data_byte = data_byte | 0x10
        elif averaging_samples == 4:
            data_byte = data_byte | 0x20
        elif averaging_samples == 8:
            data_byte = data_byte | 0x30
        elif averaging_samples == 16:
            data_byte = data_byte | 0x40
        else:
            print("MAX31856 Error: Invalid sample averaging value.")
            return

        self.write_data(0x01, data_byte)

    def read_cold_junction_temperature(self):
        """
        Reads the cold junction temperature in Degrees Celsius
        :return: Degrees C
        """
        recv_data = self.read_data(0x0A, 1)
        temp_msb = recv_data[0]
        recv_data = self.read_data(0x0B, 1)
        temp_lsb = recv_data[0]
        print("MSB: " + str(temp_msb) + " LSB: " + str(temp_lsb))
        sign = 1
        if temp_msb & 0x80:
            sign = -1

        conv_temp = ((temp_msb & 0x40 >> 6) * pow(2, 6)) + ((temp_msb & 0x20 >> 5) * pow(2, 5)) + (
                (temp_msb & 0x10 >> 4) * pow(2, 4)) + ((temp_msb & 0x08 >> 3) * pow(2, 3)) + (
                            (temp_msb & 0x04 >> 2) * pow(2, 2)) + ((temp_msb & 0x02 >> 1) * pow(2, 1)) + (
                            (temp_msb & 0x01) * pow(2, 0)) + ((temp_lsb & 0x80 >> 7) * pow(2, -1)) + (
                            (temp_lsb & 0x40 >> 6) * pow(2, -2)) + ((temp_lsb & 0x20 >> 5) * pow(2, -3)) + (
                            (temp_lsb & 0x10 >> 4) * pow(2, -4)) + ((temp_lsb & 0x08 >> 3) * pow(2, -5)) + (
                            (temp_lsb & 0x04 >> 2) * pow(2, -6))

        self.cold_junction_temperature = conv_temp
        conv_temp = conv_temp * sign
        if self.debug:
            print("Cold Junc Temp: " + str(conv_temp))

        return conv_temp

    def read_thermocouple_temperature(self):
        """
        Reads the linearized thermocouple temperature in Degrees Celsius
        :return: Degrees Celsius
        """
        recv_data = self.read_data(0x0C, 1)
        temp_2 = recv_data[0]
        recv_data = self.read_data(0x0D, 1)
        temp_1 = recv_data[0]
        recv_data = self.read_data(0x0E, 1)
        temp_0 = recv_data[0]
        sign = 1
        if temp_2 & 0x80:
            sign = -1

        conv_temp = ((temp_2 & 0x40) * pow(2, 10)) + ((temp_2 & 0x20) * pow(2, 9)) + (
                (temp_2 & 0x10) * pow(2, 8)) + ((temp_2 & 0x08) * pow(2, 7)) + (
                            (temp_2 & 0x04) * pow(2, 6)) + ((temp_2 & 0x01) * pow(2, 5)) + (
                            (temp_2 & 0x01) * pow(2, 4)) + ((temp_1 & 0x80) * pow(2, 3)) + (
                            (temp_1 & 0x40) * pow(2, 2)) + ((temp_1 & 0x20) * pow(2, 1)) + (
                            (temp_1 & 0x10) * pow(2, 0)) + ((temp_1 & 0x08) * pow(2, -1)) + (
                            (temp_1 & 0x04) * pow(2, -2)) + ((temp_1 & 0x02) * pow(2, -3)) + (
                            (temp_1 & 0x01) * pow(2, -4)) + ((temp_0 & 0x80) * pow(2, -5)) + (
                            (temp_0 & 0x40) * pow(2, -6)) + ((temp_0 & 0x20) * pow(2, -7))

        self.thermocouple_temperature = conv_temp
        conv_temp = conv_temp * sign
        if self.debug:
            print("Thermocouple Temp: " + str(conv_temp))

        return conv_temp

    def read_faults(self):
        """
        Updates the Fault member variables
        """
        recv_data = self.read_data(0x0F, 1)
        faults = recv_data[0]

        self.fault_cold_junc_out_of_range = faults & 0x80
        self.fault_thermocouple_out_of_range = faults & 0x40
        self.fault_cold_junc_high = faults & 0x20
        self.fault_cold_junc_low = faults & 0x10
        self.fault_thermocouple_high = faults & 0x08
        self.fault_thermocouple_low = faults & 0x04
        self.fault_voltage_out_of_range = faults & 0x02
        self.fault_open_circuit_thermocouple = faults & 0x01

    def has_fault(self):
        """
        Returns true if any fault is set
        """
        if self.fault_cold_junc_out_of_range:
            return True
        if self.fault_thermocouple_out_of_range:
            return True
        if self.fault_cold_junc_high:
            return True
        if self.fault_cold_junc_low:
            return True
        if self.fault_thermocouple_high:
            return True
        if self.fault_thermocouple_low:
            return True
        if self.fault_voltage_out_of_range:
            return True
        if self.fault_open_circuit_thermocouple:
            return True
        return False

    def print_faults(self):
        print("MAX31856 Faults: ")
        if self.fault_cold_junc_out_of_range:
            print("MAX31856 Fault: Cold Junction out of range")
        if self.fault_thermocouple_out_of_range:
            print("MAX31856 Fault: Thermocouple temp out of range")
        if self.fault_cold_junc_high:
            print("MAX31856 Fault: Cold Junction temperature high")
        if self.fault_cold_junc_low:
            print("MAX31856 Fault: Cold Junction temperature low")
        if self.fault_thermocouple_high:
            print("MAX31856 Fault: Thermocouple temperature high")
        if self.fault_thermocouple_low:
            print("MAX31856 Fault: Thermocouple temperature low")
        if self.fault_voltage_out_of_range:
            print("MAX31856 Fault: Thermocouple voltage out of range")
        if self.fault_open_circuit_thermocouple:
            print("MAX31856 Fault: Thermocouple Open Circuit Detected")
