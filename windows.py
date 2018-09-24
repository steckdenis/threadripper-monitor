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

import wmi
import win32pdh
import win32pdhutil
import win32pdhquery

def get_cpu_name(all_known_names):
    """ Use WMI to get the processor name
    """
    p = wmi.WMI().Win32_Processor()[0]
    parts = p.name.split()
    print(parts)

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
        self.query = win32pdhquery.Query()
        processor = win32pdhutil.find_pdh_counter_localized_name('Processor')       # Oh my goodness... Windows...
        cputime = win32pdhutil.find_pdh_counter_localized_name('% Processor Time')
        
        for i in range(num_cores):
            self.query.rawaddcounter(processor, cputime, str(i))

        self.query.open()

    def update(self):
        """ Update statistics
        """
        # Get CPU usage
        total_use = 0
        total_cpus = 0

        for i, percent in enumerate(self.query.collectdata()):
            if percent == -1:
                break   # Got past the end of the CPUs actually present in the system
            
            self.tr4.cores[i // 2].setUsage(i % 2, percent)

            total_use += percent
            total_cpus += 1

        if total_cpus > 0:
            # The first reading is invalid, so total_cpus will be zero
            self.usage.addReading(0, total_use / total_cpus)
            

