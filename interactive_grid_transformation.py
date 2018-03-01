import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
import matplotlib.image as mpimg
import pandas as pd
from scipy.spatial import cKDTree

from PyQt4.QtCore import *
import PyQt4.QtGui as QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.collections import LineCollection
from mpl_toolkits.basemap import Basemap

sns.set_style('ticks')

LLCRNRLON = 4
LLCRNRLAT = 44
URCRNRLON = 38
URCRNRLAT = 81


class AppForm(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.data = self.get_data2()
        self.busdf = self.get_prev_buses()
        self.linedf = self.get_prev_lines()
        self.fitdf = self.get_prev_fit()
        self.curLine = []
        self.lineCollection = []
        for k, v in self.linedf.linepoints.iteritems():
            self.lineCollection.append(v)

        self.busindex = self.busdf.index
        x = self.busdf.x[self.busindex]
        y = self.busdf.y[self.busindex]
        self.lookuptree = cKDTree(np.array([x, y]).T)
        self.busPos = self.busdf[['x', 'y']].T.to_dict(orient='list')


        self.themap = Basemap(
            llcrnrlon=LLCRNRLON, llcrnrlat=LLCRNRLAT,
            urcrnrlon=URCRNRLON, urcrnrlat=URCRNRLAT,
            fix_aspect=True)

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

        self.outfig = Figure((5.0, 4.0), dpi=100)
        self.outcanvas = FigureCanvas(self.outfig)
        self.outcanvas.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.outcanvas.setParent(self.main_frame)
        self.outcanvas.setFocusPolicy(Qt.ClickFocus)

        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        self.mpl_toolbar_out = NavigationToolbar(self.outcanvas, self.main_frame)

        self.save_button = QtGui.QPushButton('&Save')
        self.save_button.clicked.connect(self.save_data)

        self.order_combo = QtGui.QComboBox(self)
        self.orders = [1, 2, 3]
        self.orderlabels = {'Polynomial order {0}'.format(v): v for v in self.orders}
        for v in sorted(self.orderlabels.keys()):
            self.order_combo.addItem(v)
            self.curorder = self.orderlabels[v]
        self.order_combo.activated[str].connect(self.update_order)

        self.update_fit_button = QtGui.QPushButton('&Update Fit')
        self.update_fit_button.clicked.connect(self.update_fit)


        # self.country_button = QtGui.QPushButton('S&witch country: {0}'.format(self.curCountry))
        # self.country_button.clicked.connect(self.update_country)

        self.buttons = QtGui.QHBoxLayout()
        self.buttons.addWidget(self.save_button)
        self.buttons.addWidget(self.update_fit_button)
        self.buttons.addWidget(self.order_combo)

        self.canvas.mpl_connect('button_press_event', self._on_click)

        self.hcanvases = QtGui.QHBoxLayout()
        self.hcanvases.addWidget(self.canvas)
        self.hcanvases.addWidget(self.outcanvas)

        self.toolbars = QtGui.QHBoxLayout()
        self.toolbars.addWidget(self.mpl_toolbar)
        self.toolbars.addWidget(self.mpl_toolbar_out)

        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addLayout(self.hcanvases)
        self.vbox.addLayout(self.toolbars)
        self.vbox.addLayout(self.buttons)
        self.main_frame.setLayout(self.vbox)
        self.setCentralWidget(self.main_frame)
        print('Loaded. order: {0}'.format(self.curorder))

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

    def get_prev_fit(self):
        if os.path.isfile('buses_to_fit.csv'):
            df = pd.read_csv('buses_to_fit.csv')
        else:
            df = pd.DataFrame(columns=['Bus','x','y','lon','lat'])
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

        self.outfig.clear()
        self.outaxes = self.outfig.add_subplot(111)
        self.themap.fillcontinents(sns.xkcd_rgb['light grey'], ax=self.outaxes)
        self.outcanvas.draw()

    def _on_click(self, event):
        if event.button == 2:
            self.curBus = self.find_closest_bus([event.xdata, event.ydata])
            x, y = self.busPos[self.curBus]
            lat, ok1 = QtGui.QInputDialog.getDouble(
                self, 'Input Dialog',
                'Latitude of {}:'.format(self.curBus))
            if ok1:
                lon, ok2 = QtGui.QInputDialog.getDouble(
                    self, 'Input Dialog',
                    'Longitude of {}:'.format(self.curBus))
            if ok1 and ok2:
                self.fitdf = self.busdf.append({
                    'Bus': self.curBus,
                    'x': x,
                    'y': y,
                    'lon': lon,
                    'lat': lat}, ignore_index=True)
                print('Assigned position {0} to bus {1}'.format((lon, lat), self.curBus))
                self.out_scatter.set_offsets([p for p in self.out_scatter.get_offsets()]+[[event.xdata, event.ydata]])
                self.canvas.draw()

        pass

    def save_data(self):
        self.linedf.set_index('startBus').to_csv('lines.csv', encoding='utf-8')
        print('Saved!')

    def update_order(self, text):
        self.curorder = self.orderlabels[unicode(text)]
        print('Set order to {0}'.format(self.curorder))

    def update_fit(self):
        print('Fit Updated')
        pass

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
