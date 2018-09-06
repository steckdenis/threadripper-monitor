#!/usr/bin/python3
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

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtChart import *

import subprocess

RYZEN_ORANGE = QColor(243, 102, 33)
RYZEN_GRAY = QColor(89, 89, 89)
COLORS = [RYZEN_ORANGE, RYZEN_GRAY]

# Detect the processor
CPUS = {
    '1900X': (2, 2),                # 2 dies, 2 cores per CCX
    '1920X': (2, 3),
    '1950X': (2, 4),
    '2920X': (2, 3),
    '2950X': (2, 4),
    '2970WX': (4, 3),
    '2990WX': (4, 4),
    '1400': (1, 2),
    '1500X': (1, 2),
    '1600': (1, 3),
    '1600X': (1, 3),
    '1700': (1, 4),
    '1700X': (1, 4),
    '1800X': (1, 4),
    '2600': (1, 3),
    '2600X': (1, 3),
    '2700': (1, 4),
    '2700X': (1, 4),
}

f = open('/proc/cpuinfo', 'r')

for line in f:
    parts = line.strip().split()

    if len(parts) >= 7 and parts[0] == 'model' and parts[1] == 'name':
        CPU = parts[6]

        if CPU not in CPUS:
            CPU = parts[5]  # No "Threadripper" in the name

        break

f.close()

# Print information about the processor
print('Detected', 'known' if CPU in CPUS else 'unknown', 'CPU', CPU)

if CPU in CPUS:
    NUM_DIES = CPUS[CPU][0]
    NUM_CORES_PER_CCX = CPUS[CPU][1]
else:
    NUM_DIES = 2
    NUM_CORES_PER_CCX = 4

NUM_CORES = NUM_DIES * 2 * NUM_CORES_PER_CCX

class CoreViewer(QWidget):
    """ Visualizes the CPU usage and power consumption of a core
    """
    def __init__(self, parent):
        super(CoreViewer, self).__init__(parent)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(255, 255, 255))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFixedSize(60, 60)

        # CPU usage label
        self.threads = []

        for i in range(2):
            usage = QLabel(self)
            usage.setAlignment(Qt.AlignCenter)
            usage.move(i * 30, 0)
            usage.resize(30, 60)
            usage.setAutoFillBackground(True)

            self.threads.append(usage)

        # CPU power consumption label
        self.power = QLabel(self)
        pal = self.power.palette()
        pal.setColor(QPalette.Window, QColor(255, 100, 100))
        self.power.setPalette(pal)
        self.power.setAutoFillBackground(True)

        self.setPower(0)

    def setPower(self, power):
        """ Display a power usage, between 0 and 25W
        """
        x = int(power / 25. * 60.)
        self.power.move(0, 50)
        self.power.resize(x, 10)

    def setUsage(self, thread, percent):
        """ Display a core usage
        """
        delta = 255 - int(percent / 100. * 128.)
        usage = self.threads[thread]

        pal = usage.palette()
        pal.setColor(QPalette.Window, QColor(delta, delta, 255))
        usage.setPalette(pal)
        usage.setText(str(int(percent)) + '%')

class CCXViewer(QFrame):
    """ Displays statistics about a 4-core CCX
    """
    def __init__(self, parent):
        super(CCXViewer, self).__init__(parent)

        self.setFrameShape(QFrame.Box)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setAutoFillBackground(True)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(255, 255, 255))
        self.setPalette(pal)

        # Create the cores
        self.cores = []

        lay = QGridLayout(self)
        lay.setSpacing(3)
        lay.setContentsMargins(3, 3, 3, 3)

        for x, y in [(0, 0), (1, 1), (0, 1), (1, 0)]:
            if len(self.cores) < NUM_CORES_PER_CCX:
                core = CoreViewer(self)

                lay.addWidget(core, y, x)
                self.cores.append(core)
            else:
                lay.addWidget(QLabel(), y, x)

class DieViewer(QWidget):
    """ Displays statistics about a 2-CCX die
    """
    def __init__(self, parent, is_io):
        super(DieViewer, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setAutoFillBackground(True)

        pal = self.palette()

        if is_io:
            pal.setColor(QPalette.Window, RYZEN_ORANGE)
        else:
            pal.setColor(QPalette.Window, RYZEN_GRAY)

        self.setPalette(pal)

        # Create the CCXes
        self.ccx = [
            CCXViewer(self),
            CCXViewer(self)
        ]
        self.cores = self.ccx[0].cores + self.ccx[1].cores

        lay = QHBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(12, 12, 12, 12)

        lay.addWidget(self.ccx[0])
        lay.addWidget(self.ccx[1])

class TR4Viewer(QFrame):
    """ Viewer for a 32-core Threadripper (4 dies)
    """
    def __init__(self, parent):
        super(TR4Viewer, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Create the dies
        self.dies = [
            DieViewer(self, True),
            DieViewer(self, False),
            DieViewer(self, True),
            DieViewer(self, False)
        ]

        lay = QGridLayout(self)
        lay.setHorizontalSpacing(32)
        lay.setVerticalSpacing(16)
        lay.setContentsMargins(12, 12, 12, 12)

        if NUM_DIES == 1:
            # Desktop Ryzen
            lay.addWidget(self.dies[0], 0, 0)
        else:
            # Threadripper
            lay.addWidget(self.dies[0], 1, 0)   # Memory die on NUMA node 0
            lay.addWidget(self.dies[1], 0, 0)   # IO die
            lay.addWidget(self.dies[2], 0, 1)   # Memory die on NUMA node 2
            lay.addWidget(self.dies[3], 1, 1)   # IO die

        # Cores as numbered by Linux, with the IO cores coming first
        self.cores = self.dies[0].cores + self.dies[2].cores + self.dies[1].cores + self.dies[3].cores

        # Hide inactive dies
        if NUM_DIES != 4:
            self.dies[1].hide()
            self.dies[3].hide()

        if NUM_DIES != 2:
            self.dies[2].hide()

class DynamicChart(QChartView):
    """ Chart that displays sensors readings
    """
    def __init__(self, title, maximum, series_names, unit, parent):
        super(DynamicChart, self).__init__(parent)

        self.setMinimumHeight(150)
        self.setRenderHints(QPainter.Antialiasing)

        self.series_names = series_names
        self.unit = unit
        self.maximum = maximum

        # Create the series
        self.line_series = [QLineSeries(self) for i in range(len(series_names))]
        self.series = [QAreaSeries(line) for line in self.line_series]

        # Create a chart object
        self.chart = QChart()

        for i, s in enumerate(self.series):
            s.setName(series_names[i])
            s.setPen(QPen(Qt.NoPen))
            s.setColor(COLORS[-i - 1])
            self.chart.addSeries(s)

        self.chart.setTitle(title)
        self.chart.createDefaultAxes()
        self.chart.axisX().setRange(0, 1)
        self.chart.axisX().setLabelsVisible(False)
        self.chart.legend().setAlignment(Qt.AlignRight)
        self.chart.setMargins(QMargins(0, 0, 0, 0))

        if self.maximum is not None:
            self.chart.axisY().setRange(0, maximum)

        self.setChart(self.chart)

        # Prepare for scrolling
        self._index = 0
        self._readings = []

    def addReading(self, series, reading):
        self.line_series[series].append(self._index, reading)
        self.series[series].setUpperSeries(self.line_series[series])

        if series == 0:
            self._index += 1
            self.chart.axisX().setRange(self._index - 100, self._index)

        # Update the title of the series
        self.series[series].setName('%s (%i%s)' % (self.series_names[series], int(reading), self.unit))

        # Autoscale Y
        if series == 0 and self.maximum is None:
            self._readings.append(reading)

            if len(self._readings) > 100:
                self._readings = self._readings[-100:]

            self.chart.axisY().setRange(0, max(self._readings))

class Win(QWidget):
    """ Main Window
    """
    def __init__(self, parent):
        super(Win, self).__init__(parent)

        self.setWindowTitle("AMD Ryzen Monitor (%s)" % CPU)

        # Charts
        self.usage = DynamicChart("CPU Usage", 100, ['Total'], '%', self)
        self.power = DynamicChart("Power Usage", None, ['Package', 'Cores'], 'W', self)

        # Die viewer
        self.tr4 = TR4Viewer(self)

        lay = QVBoxLayout(self)
        lay.addWidget(self.usage)
        lay.addWidget(self.power)
        lay.addStretch()
        lay.addWidget(self.tr4, 0, Qt.AlignCenter)
        lay.addStretch()
        lay.setSpacing(0)

        # Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()

        # Open the core usage statistics
        self.stat = open('/proc/stat', 'r')
        self.old_totals = [0] * 64
        self.old_idles = [0] * 64
        self.update()

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

                use = (total_delta - idle_delta) / total_delta
                total_use += use

                if cpu_number // 2 < NUM_CORES:
                    self.tr4.cores[cpu_number // 2].setUsage(cpu_number % 2, int(use * 100))

        # Total CPU usage
        self.usage.addReading(0, (total_use / (NUM_CORES * 2.)) * 100.)

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

                    if core_index < NUM_CORES:
                        self.tr4.cores[core_index].setPower(core_power)
                elif len(parts) == 3 and parts[1] == 'sum:':
                    cores_power = float(parts[2][:-1])

        self.power.addReading(1, cores_power)
        self.power.addReading(0, package_power)

if __name__ == '__main__':
    app = QApplication([])
    win = Win(None)

    win.show()
    app.exec_()
