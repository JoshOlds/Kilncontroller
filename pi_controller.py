import time
import threading


class PIController:

    def __init__(self, kiln, p, i, hz, print=False):
        self.kiln = kiln
        self.error = 0
        self._p = p
        self.p_value = 0
        self._i = i
        self.i_value = 0
        self._hz = hz

        self.pi_thread = None
        self._pi_thread_flag = False
        self.pi_thread_running = False

    def start_pi_thread(self):
        if not self._pi_thread_flag:
            # print("Starting PI Controller Thread...")
            self._pi_thread_flag = True
            self.pi_thread = threading.Thread(group=None, target=self._run, name="pi_controller_thread")
            self.pi_thread.start()
            return True
        else:
            print("PIController: Tried to start PI thread, but thread is already running!")
            return False

    def _run(self):
        self.pi_thread_running = True
        time.sleep(4)
        while self._pi_thread_flag:
            self.error = self.kiln.setpoint_f - self.kiln.thermocouple_temp_f
            self.p_value = self.error * self._p
            self.i_value += self.error * self._i
            # Clamp integrator at -100 & 100 (no sense in winding up above max throttle)
            if self.i_value < -100:
                self.i_value = -100
            if self.i_value > 100:
                self.i_value = 100
            throttle = self.p_value + self.i_value
            throttle = int(round(throttle, 0))
            self.kiln.set_throttle(throttle)
            time.sleep(1.0 / self._hz)

    def get_values(self, rounding_digits):
        text = "P: " + str(round(self.p_value, rounding_digits)) + ", I: " + str(round(self.i_value, rounding_digits))
        return text







