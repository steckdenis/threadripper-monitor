# AMD Threadripper CPU Usage Monitor
# Copyright (C) 2018 Denis Steckelmacher <steckdenis@yahoo.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import subprocess

def get_cpu_name(all_known_names):
    """ Return the name of the CPU, such as "1920X" or "7551P", along with information
        about the family of the CPU. main.py uses this information to infer
        the topology of the CPU
    """
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            parts = line.strip().split()

            if 'Ryzen' in parts or 'EPYC' in parts:
                for name in all_known_names:
                    if name in parts:
                        return name, 'EPYC' in parts

    return None, False

class Statistics:
    """ Get CPU usage and power consumption statistics
    """
    def __init__(self, tr4, usage_chart, power_chart, num_cores):
        """ Initialize the class. tr4 is a TR4Viewer object that is updated with
            usage information. usage_chart and power_chart are DynamicChart instances
            that displayed summarized power and usage values.
        """

        self.tr4 = tr4
        self.power = power_chart
        self.usage = usage_chart
        self.num_cores = num_cores

        # Open the core usage statistics
        self.stat = open('/proc/stat', 'r')
        self.old_totals = [0] * 64
        self.old_idles = [0] * 64

    def update(self):
        """ Update statistics
        """
        # Update CPU core usage
        self.stat.seek(0)
        core = 0
        total_use = 0.

        for line in self.stat:
            parts = line.split()

            if len(parts) == 11 and len(parts[0]) > 3 and parts[0][0:3] == 'cpu':
                cpu_number = int(parts[0][3:])
                user = int(parts[1])
                nice = int(parts[2])
                system = int(parts[3])
                idle = int(parts[4])
                total = user + nice + system + idle

                total_delta = total - self.old_totals[cpu_number]
                idle_delta = idle - self.old_idles[cpu_number]
                skip = (self.old_totals[cpu_number] == 0)

                self.old_totals[cpu_number] = total
                self.old_idles[cpu_number] = idle

                if skip:
                    continue

                use = (total_delta - idle_delta) / (total_delta + 1e-6)
                total_use += use

                if cpu_number // 2 < self.num_cores:
                    self.tr4.cores[cpu_number // 2].setUsage(cpu_number % 2, int(use * 100))

        # Total CPU usage
        self.usage.addReading(0, (total_use / (self.num_cores * 2.)) * 100.)

        # Use RAPL to get the power usage
        cores_power = 0
        package_power = 0

        with subprocess.Popen(['rapl'], stdout=subprocess.PIPE) as rapl:
            for line in rapl.stdout:
                parts = str(line, 'ascii').strip().split()

                if len(parts) == 7 and parts[0] == 'Core':
                    # A core consumption, with total package consumption
                    core_index = int(parts[1][:-1])     # there is a comma at the end of the number
                    core_power = float(parts[4][:-2])   # there is a "W," at the end of the number
                    package_power = float(parts[6][:-1])

                    if core_index < self.num_cores:
                        self.tr4.cores[core_index].setPower(core_power)
                elif len(parts) == 3 and parts[1] == 'sum:':
                    cores_power = float(parts[2][:-1])

        self.power.addReading(1, cores_power)
        self.power.addReading(0, package_power)
