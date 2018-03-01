import sys
import os
import numpy as np
from matplotlib.figure import Figure
import matplotlib.image as mpimg
import pandas as pd

from PyQt4.QtCore import *
import PyQt4.QtGui as QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar


class AppForm(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.data = self.get_data2()
        self.busdf = self.get_prev_buses()
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
        self.country_button = QtGui.QPushButton('S&witch country: {0}'.format(self.curCountry))
        self.country_button.clicked.connect(self.update_country)
        self.buttons = QtGui.QHBoxLayout()
        self.buttons.addWidget(self.save_button)
        self.buttons.addWidget(self.country_button)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.canvas.mpl_connect('button_press_event', self._on_click)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.canvas)         # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(self.buttons)
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)

    def get_data2(self):
        return mpimg.imread('img_to_load.png')

    def get_prev_buses(self):
        if os.path.isfile('buses.csv'):
            df = pd.read_csv('buses.csv')
            self.curID = df.ID.max() + 1
            self.curCountry = df.country.iloc[-1]
        else:
            df = pd.DataFrame(columns=['ID', 'name', 'x', 'y'])
            self.curID = 2000
            self.curCountry = 'unknown'
        return df

    def on_draw(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        self.axes.imshow(self.data, interpolation='nearest')
        self.the_scatter = self.axes.scatter(self.busdf.x.tolist(), self.busdf.y.tolist(), marker='o', c='r', s=50)
        self.canvas.draw()

    def on_key_press(self, event):
        print('you pressed', event.key)

    def _on_click(self, event):
        if event.button == 2:
            text, ok = QtGui.QInputDialog.getText(
                self, 'Input Dialog',
                'Bus Name:')
            if ok:
                self.busdf = self.busdf.append({
                    'ID': self.curID,
                    'x': event.xdata,
                    'y': event.ydata,
                    'name': str(text),
                    'country': self.curCountry}, ignore_index=True)
                print(self.busdf.ix[self.busdf.index.max()])
                self.curID += 1
                self.the_scatter.set_offsets([p for p in self.the_scatter.get_offsets()]+[[event.xdata, event.ydata]])
                self.canvas.draw()

    def save_data(self):
        self.busdf.set_index('ID').to_csv('buses.csv', encoding='utf-8')

    def update_country(self):
        text, ok = QtGui.QInputDialog.getText(
            self, 'Input Dialog',
            'Country Abb:')
        if ok:
            self.curCountry = str(text)
        self.country_button.setText('S&witch country: {0}'.format(self.curCountry))
        pass


def main():
    app = QtGui.QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
