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

import sys
import psutil

RYZEN_ORANGE = QColor(243, 102, 33)
RYZEN_GRAY = QColor(89, 89, 89)
COLORS = [RYZEN_ORANGE, RYZEN_GRAY]

# Detect the operating system
if sys.platform == 'linux':
    from linux import *
elif sys.platform == 'win32':
	from windows import *
else:
    app = QApplication([])

    QMessageBox.critical(None, 'Unsupported Platform', 'This tool currently only runs on Linux')
    quit()

# Detect the processor
CPUS = {
    # Threadripper
    '1900X': (2, 2),                # 2 dies, 2 cores per CCX
    '1920X': (2, 3),
    '1950X': (2, 4),
    '2920X': (2, 3),
    '2950X': (2, 4),
    '2970WX': (4, 3),
    '2990WX': (4, 4),
    # Desktop Ryzen
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
    # EPYC
    '7351P': (4, 2),
    '7401P': (4, 3),
    '7551P': (4, 4),
    '7251': (4, 1),
    '7281': (4, 2),
    '7301': (4, 2),
    '7351': (4, 2),
    '7401': (4, 3),
    '7451': (4, 3),
    '7501': (4, 4),
    '7551': (4, 4),
    '7601': (4, 4),
}

CPU, IS_EPYC = get_cpu_name(list(CPUS.keys()))

# Print information about the processor
print('Detected', CPU if CPU else 'unknown CPU')

if CPU is not None:
    NUM_DIES = CPUS[CPU][0]
    NUM_CORES_PER_CCX = CPUS[CPU][1]
else:
    NUM_DIES = 1
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
        self.setAcceptDrops(True)

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

    def mousePressEvent(self, event):
        """ Start a drag operation of the processes associated with a thread
            to another core
        """
        if event.button() != Qt.LeftButton:
            return

        if event.x() < 30:
            thread = 0
        else:
            thread = 1

        data = QMimeData()
        data.setData("text/x-tr4-thread-index", bytes(str(self.index * 2 + thread), 'ascii'))

        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec_()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/x-tr4-thread-index"):
            event.accept()

    def dropEvent(self, event):
        """ Change the affinity of all the processes so that they move to this
            core and thread.
        """
        event.acceptProposedAction()

        if event.pos().x() < 30:
            thread = 0
        else:
            thread = 1

        original_index = int(str(event.mimeData().data("text/x-tr4-thread-index"), 'ascii'))
        target_index = self.index * 2 + thread

        if target_index != original_index:
            for p in psutil.process_iter():
                if p.uids().real == 0:
                    # Skip root processes
                    continue

                # Set the affinity of all the threads in the process
                affinity = p.cpu_affinity()

                if original_index in affinity:
                    i = affinity.index(original_index)
                    affinity[i] = target_index

                    try:
                        for t in p.threads():
                            psutil.Process(t.id).cpu_affinity(affinity)
                    except Exception as e:
                        pass

    def setCoreIndex(self, index):
        """ Set the core index of this viewer, used by drag and drop events
        """
        self.index = index

    def setPower(self, power):
        """ Display a power usage, between 0 and 25W
        """
        x = int(power / 25. * 60.)
        self.power.move(0, 50)
        self.power.resize(x, 10)

    def setUsage(self, thread, percent):
        """ Display a core usage
        """
        usage = self.threads[thread]

        pal = usage.palette()
        c = QColor(RYZEN_ORANGE)
        c.setAlpha(int(percent / 100. * 128.))
        pal.setColor(QPalette.Window, c)
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
                placeholder = QLabel()
                placeholder.setFixedSize(60, 60)

                lay.addWidget(placeholder, y, x)

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
            DieViewer(self, IS_EPYC),
            DieViewer(self, True),
            DieViewer(self, IS_EPYC)
        ]

        lay = QGridLayout(self)
        lay.setHorizontalSpacing(32)
        lay.setVerticalSpacing(16)
        lay.setContentsMargins(12, 12, 12, 12)

        if NUM_DIES == 1:
            # Desktop Ryzen
            lay.addWidget(self.dies[0], 0, 0)
        else:
            # Threadripper or EPYC
            lay.addWidget(self.dies[0], 1, 0)   # Memory die on NUMA node 0
            lay.addWidget(self.dies[1], 0, 0)   # IO die
            lay.addWidget(self.dies[2], 0, 1)   # Memory die on NUMA node 2
            lay.addWidget(self.dies[3], 1, 1)   # IO die

        # Cores as numbered by Linux, with the IO cores coming first
        self.cores = self.dies[0].cores + self.dies[2].cores + self.dies[1].cores + self.dies[3].cores

        for i, c in enumerate(self.cores):
            c.setCoreIndex(i)

        # Hide inactive dies
        if NUM_DIES != 4:
            self.dies[1].hide()
            self.dies[3].hide()

        if NUM_DIES == 1:
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

        # Statistics producer
        self.stats = Statistics(self.tr4, self.usage, self.power, NUM_CORES)
        self.stats.update()

        # Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.stats.update)
        self.timer.start()
        
        # Disable power statistics on Windows for now
        if sys.platform == 'win32':
            self.power.hide()

if __name__ == '__main__':
    app = QApplication([])
    win = Win(None)

    win.show()
    app.exec_()
