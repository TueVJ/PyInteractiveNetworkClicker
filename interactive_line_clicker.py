import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.image as mpimg
import pandas as pd
from scipy.spatial import cKDTree

from PyQt4.QtCore import *
import PyQt4.QtGui as QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.collections import LineCollection


class AppForm(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.data = self.get_data2()
        self.busdf = self.get_prev_buses()
        self.linedf = self.get_prev_lines()
        self.curLine = []
        self.lineCollection = []
        for k, v in self.linedf.linepoints.iteritems():
            self.lineCollection.append(v)

        self.drawingflag = False
        self.curStartBus = None

        self.busindex = self.busdf.index
        x = self.busdf.x[self.busindex]
        y = self.busdf.y[self.busindex]
        self.lookuptree = cKDTree(np.array([x, y]).T)
        self.busPos = self.busdf[['x', 'y']].T.to_dict(orient='list')

        self.create_main_frame()
        self.on_draw()

    def create_main_frame(self):
        self.main_frame = QtGui.QWidget()

        self.fig = Figure((5.0, 4.0), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.canvas.setParent(self.main_frame)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.canvas.setFocus()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)

        self.save_button = QtGui.QPushButton('&Save')
        self.save_button.clicked.connect(self.save_data)

        self.voltage_combo = QtGui.QComboBox(self)
        self.voltages = [750, 500, 400, 330, 220, 110]
        self.voltagelabels = {'{0} kv'.format(v): v for v in self.voltages}
        for v in sorted(self.voltagelabels.keys()):
            self.voltage_combo.addItem(v)
            self.curVoltage = self.voltagelabels[v]
        self.voltage_combo.activated[str].connect(self.update_voltage)

        self.num_circuits_combo = QtGui.QComboBox(self)
        self.curnum_circuits = 1
        self.num_circuitslabels = {'1 circuit': 1, '2 circuits': 2, '3+ circuits': 3}
        for v in sorted(self.num_circuitslabels.keys()):
            self.num_circuits_combo.addItem(v)
        self.num_circuits_combo.activated[str].connect(self.update_num_circuits)

        # self.country_button = QtGui.QPushButton('S&witch country: {0}'.format(self.curCountry))
        # self.country_button.clicked.connect(self.update_country)

        self.buttons = QtGui.QHBoxLayout()
        self.buttons.addWidget(self.save_button)
        self.buttons.addWidget(self.voltage_combo)
        self.buttons.addWidget(self.num_circuits_combo)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.canvas.mpl_connect('button_press_event', self._on_click)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.canvas)         # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(self.buttons)
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)
        print('Loaded. Voltage: {0}, number of circuits: {1}'.format(self.curVoltage, self.curnum_circuits))

    def get_data2(self):
        return mpimg.imread('img_to_load.png')

    def get_prev_buses(self):
        df = pd.read_csv('buses.csv').set_index('ID')
        return df

    def get_prev_lines(self):
        if os.path.isfile('lines.csv'):
            df = pd.read_csv('lines.csv')
            df['linepoints'] = df.linepoints.apply(eval)
            self.curVoltage = df.voltage.iloc[-1]
        else:
            df = pd.DataFrame(columns=['startBus', 'endBus', 'linepoints', 'voltage', 'numlines'])
        return df

    def on_draw(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        self.axes.imshow(self.data, interpolation='nearest')
        self.the_scatter = self.axes.scatter(self.busdf.x.tolist(), self.busdf.y.tolist(), marker='o', c='r', s=50)
        self.curLineDraw = plt.Line2D([x for x, y in self.curLine], [y for x, y in self.curLine], color='r', lw=4, axes=self.axes)
        self.curLineCol = LineCollection(self.lineCollection, color='k', lw=2)
        self.axes.add_line(self.curLineDraw)
        self.axes.add_collection(self.curLineCol)
        self.canvas.draw()

    def on_key_press(self, event):
        if event.key == 's':
            # Start drawing a line
            self.drawingflag = True
            self.curLine = []
            print('Cleared line in progress/enabled drawing')
        if event.key == 't' and self.drawingflag and len(self.curLine) > 0:
            self.curEndBus = self.find_closest_bus(self.curLine[-1])
            self.curLine[-1] = self.busPos[self.curEndBus]
            if self.curStartBus == self.curEndBus:
                print('Start bus same as end bus. Aborting.')
            else:
                # Save the line
                print('Created line from {0} to {1} at {2} kv'.format(self.busdf.name[self.curStartBus], self.busdf.name[self.curEndBus], self.curVoltage))
                self.linedf = self.linedf.append({
                    'startBus': self.curStartBus,
                    'endBus': self.curEndBus,
                    'linepoints': self.curLine,
                    'voltage': self.curVoltage,
                    'numlines': self.curnum_circuits},
                    ignore_index=True)
                self.curStartBus = None
                self.curEndBus = None
                self.lineCollection.append(self.curLine)
                self.curLineCol.set_segments(self.lineCollection)
                self.curLine = []
                self.curLineDraw.set_data([], [])
                self.canvas.draw()
        # prin )'you pressed', event.key)

    def _on_click(self, event):
        # Middle Mouse Button
        if event.button == 2:
            if self.drawingflag:
                if self.curStartBus is None:
                    self.curStartBus = self.find_closest_bus([event.xdata, event.ydata])
                    self.curLine.append(self.busPos[self.curStartBus])
                else:
                    self.curLine.append([event.xdata, event.ydata])
                    self.curLineDraw.set_data([x for x, y in self.curLine], [y for x, y in self.curLine])
                self.canvas.draw()
        pass

    def save_data(self):
        self.linedf.set_index('startBus').to_csv('lines.csv', encoding='utf-8')
        print('Saved!')

    def update_voltage(self, text):
        self.curVoltage = self.voltagelabels[str(text)]
        print('Set voltage to {0} kV'.format(self.curVoltage))

    def update_num_circuits(self, text):
        self.curnum_circuits = self.num_circuitslabels[str(text)]
        print('Set number of circuits to {0} kV'.format(self.curnum_circuits))

    def find_closest_bus(self, pos):
        dist, idx = self.lookuptree.query(pos)
        return self.busindex[idx]


def main():
    app = QtGui.QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
