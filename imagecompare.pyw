#!/usr/bin/env python

#######################################################################
# Nikolaus Mayer, 2013
#######################################################################
# Compare two sets of images
#######################################################################

import os
import sys
import re
import platform
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import qrc_resources

__version__ = '0.1.0'
RE_EXTRACT_NUMBER = re.compile(r'(\d+)')


class MainWindow(QMainWindow):
  def __init__(self, parent=None):
    super(MainWindow, self).__init__(parent)

    self.filenames = [None, None]
    self.images    = [[], []]
    self.masks     = [[], []]
    self.currentIndex = 0
    self.labelImage = None

    ONE_SET, TWO_SETS = range(2)

    self.imageLabel = QLabel()
    self.imageLabel.setMinimumSize(320,240)
    self.imageLabel.setAlignment(Qt.AlignCenter)
    self.imageLabel.setAutoFillBackground(True)
    self.imageLabel.setPalette(QPalette(Qt.white))
    self.setCentralWidget(self.imageLabel)
    
    self.frameSlider = QSlider(orientation=Qt.Horizontal)
    #self.frameSlider.setEnabled(False)
    self.frameSlider.setRange(0,0)
    self.frameSlider.setTickPosition(QSlider.TicksBelow)
    self.frameSliderLabel = QLabel("Frame: 0")
    self.frameSliderLabel.setMinimumSize(80,10)
    docklayout = QHBoxLayout()
    docklayout.addWidget(self.frameSlider)
    docklayout.addWidget(self.frameSliderLabel)
    dockwidgetcontentwidget = QWidget()
    dockwidgetcontentwidget.setLayout(docklayout)
    
    dockwidget = QDockWidget()
    dockwidget.setFeatures(QDockWidget.DockWidgetMovable)
    dockwidget.setAllowedAreas(Qt.BottomDockWidgetArea|
                               Qt.TopDockWidgetArea)
    dockwidget.setWidget(dockwidgetcontentwidget)
    self.addDockWidget(Qt.BottomDockWidgetArea, dockwidget)
    
    status = self.statusBar()
    status.setSizeGripEnabled(True)
    status.showMessage("Ready", 5000)

    filesOpenAction = self.createAction("&Open two image sets",
                                        self.loadTwoImageSets,
                                        QKeySequence.Open,
                                        "24x24/2-documents-open",
                                        "Open two sets of images for viewing and comparing")
    fileOpenAction  = self.createAction("Op&en single image set",
                                        self.loadImageSet,
                                        None,
                                        "24x24/document-open",
                                        "Open a set of images for viewing")
    fileQuitAction = self.createAction("&Quit",
                                       self.close,
                                       "Ctrl+Q",
                                       "24x24/exit",
                                       "Close the application")
    helpAboutAction= self.createAction("&About",
                                       self.helpAbout,
                                       None,
                                       "helpabout",
                                       "More information about this program")

    self.fileMenu = self.menuBar().addMenu("&File")
    self.addActions(self.fileMenu, (filesOpenAction,
                                    fileOpenAction,
                                    None, 
                                    fileQuitAction,))
    self.helpMenu = self.menuBar().addMenu("&Help")
    self.addActions(self.helpMenu, (helpAboutAction,))
    
    fileToolBar = self.addToolBar("File")
    fileToolBar.setObjectName("FileToolBar")
    self.addActions(fileToolBar, (filesOpenAction,
                                  fileOpenAction))

    self.setWindowTitle("Image Compare")
    
    self.connect(self.frameSlider, SIGNAL("valueChanged(int)"),
                 self.frameSliderChange)

  def frameSliderChange(self, newValue):
    if newValue == self.currentIndex:
      return
    self.changeFrame(newValue)

  def helpAbout(self):
    QMessageBox.about(self, "About Image Compare",
        """<b>Image Compare</b> v%s
        <p>Copyright &copy; 2013 Nikolaus Mayer
        <p>This application can be used to compare two sets of images
        <p>Python %s - Qt %s - PyQt %s on %s""" % \
          ( __version__, 
            platform.python_version(),
            QT_VERSION_STR,
            PYQT_VERSION_STR,
            platform.system() ))

  def addActions(self, target, actions):
    for action in actions:
      if action is None:
        target.addSeparator()
      else:
        target.addAction(action)

  def createAction(self, text, 
                   slot=None, 
                   shortcut=None, 
                   icon=None,
                   tip=None, 
                   checkable=False, 
                   signal="triggered()"):
    action = QAction(text, self)
    if icon is not None: 
      action.setIcon(QIcon(':/%s.png' % icon))
    if shortcut is not None:
      action.setShortcut(shortcut)
    if tip is not None:
      action.setToolTip(tip)
      action.setStatusTip(tip)
    if slot is not None:
      self.connect(action, SIGNAL(signal), slot)
    if checkable:
      action.setCheckable(True)
    return action

  def fileOpen(self, side=None):
    if side not in (0,1):
      return False
    dir = '.'
    if self.filenames[side]:
      dir = os.path.dirname(self.filenames[side])
    elif self.filenames[1-side]:
      dir = os.path.dirname(self.filenames[1-side])
    formats = ['*.%s' % unicode(format).lower() \
               for format in QImageReader.supportedImageFormats()]
    header = "Choose member of %s image set" % ["first", "second"][side]
    fname = unicode(QFileDialog.getOpenFileName(
              self,
              "%s - %s" % (QApplication.applicationName(), header),
              dir,
              "Image files (%s)" % ' '.join(formats)))
    if fname:
      self.loadFiles(fname, side)
      self.filenames[side] = fname
      return True
    return False

  def loadImageSet(self):
    """Load files for one image set"""
    pass

  def loadTwoImageSets(self):
    """Load files for two image sets"""
    if self.fileOpen(0) and self.fileOpen(1):
      ## Ensure both image sets have the same size
      sizes = (self.images[0][0].size(), self.images[1][0].size())
      if sizes[0] != sizes[1]:
        larger_size = QSize(max(sizes[0].width(),  sizes[1].width()),
                            max(sizes[0].height(), sizes[1].height()))
        for side in [0,1]:
          if sizes[side] != larger_size:
            fs = "first" if side==0 else "second"
            for i in xrange(len(self.images[side])):
              self.updateStatus("Resizing %s dataset... %d/%d." % \
                                (fs, i, len(self.images[side])))
              self.images[side][i] = self.images[side][i].scaled(
                                      larger_size,
                                      transformMode=Qt.SmoothTransformation)
      self.currentIndex = 0
      self.updateMask()
      self.showImage()
      self.frameSlider.setRange(0,len(self.images[0])-1)
      self.frameSlider.setValue(0)
      self.frameSliderLabel.setText("Frame: 1")

  def loadFiles(self, fname=None, side=None):
    if fname and side in (0,1):
      _filenames = self.findFiles(fname)
      if not _filenames:
        _filenames = [fname]
      _images = []
      for i,f in enumerate(_filenames):
        self.updateStatus("Reading images... %d/%d." % (i, len(_filenames)))
        image = QImage(f)
        if image.isNull():
          message = "Failed to read '%s'!" % f
          break
        else:
          _images.append(image.convertToFormat(QImage.Format_ARGB32))
      else:
        self.images[side] = _images
        message = "Loaded %d files around '%s'." % \
                  (len(_filenames), _filenames[0])
      self.updateStatus(message)

  def findFiles(self, fname=None):
    if fname is None:
      return
    number_groups = []
    for match in RE_EXTRACT_NUMBER.finditer(fname):
      number = int(match.group(1))
      start, end = match.start(), match.end()
      length = end-start
      template = fname[:start] + '%0*d' + fname[end:]
      found = []
      n = number-1
      while os.path.isfile(template % (length,n)):
        found.append(template % (length,n))
        n -= 1
      found = found[::-1]
      n = number
      while os.path.isfile(template % (length,n)):
        found.append(template % (length,n))
        n += 1
      if len(found) > 1:
        return found
  
  def changeFrame(self, index):
    self.currentIndex = index
    self.showImage()
    self.updateStatus("Frame %d/%d" % (self.currentIndex+1,
                                       len(self.images[0])))
    self.frameSliderLabel.setText("Frame: %d" % (index+1))
    self.frameSlider.setValue(index)

  def wheelEvent(self, event):
    cid = self.currentIndex
    if event.delta() > 0:
      cid += 1
    else:
      cid -= 1
    cid = max(cid, 0)
    cid = min(cid, len(self.images[0])-1)
    self.changeFrame(cid)

  def showImage(self):
    if not self.images[0] or not self.images[1] or \
       self.currentIndex < 0 or \
       self.currentIndex >= len(self.images[0]) or \
       self.currentIndex >= len(self.images[1]):
      return
    self.imageLabel.setMinimumSize(self.images[0][self.currentIndex].size())
    
    i0 = self.images[0][self.currentIndex]
    i1 = self.images[1][self.currentIndex]
    i0.setAlphaChannel(self.masks[0])
    i1.setAlphaChannel(self.masks[1])
    self.labelImage = QImage(i0.size(), QImage.Format_ARGB32)
    painter = QPainter(self.labelImage)
    painter.drawImage(0, 0, i0)
    painter.drawImage(0, 0, i1)
    self.imageLabel.setPixmap(QPixmap.fromImage(self.labelImage))

  def updateMask(self):
    if not self.images[0]:
      return
    mask = QImage(self.images[0][0].size(), QImage.Format_ARGB32)
    h, w = mask.height(), mask.width()
    black, white = qRgb(0,0,0), qRgb(255,255,255)
    for y in xrange(h):
      for x in xrange(w-1, 0, -1):
        if float(w-x+1)/(y+1) > float(w)/h:
          mask.setPixel(x, y, white)
        else:
          mask.setPixel(x, y, black)
    self.masks[0] = mask 
    self.masks[1] = QImage(mask)
    self.masks[1].invertPixels()


  def updateStatus(self, message=None):
    if message is None:
      return
    self.statusBar().showMessage(message, 5000)


def main():
  #style = QStyleFactory.create("cleanlooks")
  #QApplication.setStyle(style)
  app = QApplication(sys.argv)
  app.setApplicationName("Image Changer")
  app.setWindowIcon(QIcon(':/icon.png'))
  form = MainWindow()
  form.show()
  app.exec_()

if __name__ == '__main__':
  main()

