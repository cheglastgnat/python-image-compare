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


class File(object):
  """A class for holding a single file"""
  def __init__(self, filename, index, data):
    self.filename = filename
    self.index = index
    self.data = data


class Fileset(object):
  """A class for holding a set of files"""
  def __init__(self, basename):
    self.basename = basename
    self.files = []

  def addFile(self, newfile):
    self.files.append(newfile)


class FilesetFilenamesGenerator(object):
  """Concise representation of a series of numbered filenames"""
  def __init__(self, template, length, lower, upper):
    self.template = template
    self.length = length
    self.lower = lower
    self.upper = upper

  def generateFiles(self):
    """Generate the explicit list of filenames"""
    return [self.template % (self.length, i) for i in xrange(self.lower,
                                                             self.upper+1)]

  def __str__(self):
    return """FilesetFilenamesGenerator:
      template = %s,
      length   = %d,
      lower    = %d,
      upper    = %d""" % (self.template,self.length,self.lower,self.upper)

  def __cmp__(self, other):
    """Compare two instances by cardinality (amount of files)"""
    return cmp((self.upper-self.lower), (other.upper-other.lower))


class GeneratorChooseDlg(QDialog):
  """
  Present a number of options, and allow the user to choose one (or cancel).
  The CALLER has to keep the input strings to a sensible length
  """
  def __init__(self, options, parent=None):
    super(GeneratorChooseDlg, self).__init__(parent)
    label = QLabel("The chosen image can belong to multiple image sets, depending on which part of the filename contains the file index. Please choose one of the possible image sets to continue.")
    label.setWordWrap(True)
    self.options = QListWidget()
    self.options.addItems(options)
    self.options.setMinimumWidth(min(self.options.sizeHintForColumn(0)+10, 600))
    buttonbox = QDialogButtonBox(QDialogButtonBox.Ok|
                                 QDialogButtonBox.Cancel)
    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(self.options)
    layout.addWidget(buttonbox)
    self.setLayout(layout)
    self.connect(buttonbox, SIGNAL("accepted()"),
                 self, SLOT("accept()"))
    self.connect(buttonbox, SIGNAL("rejected()"),
                 self, SLOT("reject()"))
    self.setWindowTitle("%s - Choose image set" % QApplication.applicationName())


class MainWindow(QMainWindow):
  """
  Main window class
  """
  RE_EXTRACT_NUMBER = re.compile(r'(\d+)')
  ONE_SET, TWO_SETS = range(2)

  def __init__(self, parent=None):
    super(MainWindow, self).__init__(parent)

    self.filenames = [None, None]
    self.filesets  = [None, None]
    self.masks     = [None, None]
    self.currentIndex = 0
    self.labelImage = None

    self.mode = None

    # Central label holding the montage image
    self.imageLabel = QLabel()
    self.imageLabel.setMinimumSize(320,240)
    self.imageLabel.setAlignment(Qt.AlignCenter)
    self.imageLabel.setAutoFillBackground(True)
    self.imageLabel.setPalette(QPalette(Qt.white))
    self.setCentralWidget(self.imageLabel)
    
    # Frame-control slider as QDockWidget
    self.frameSlider = QSlider(orientation=Qt.Horizontal)
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
    
    # Status bar with resize grip, for status messages
    status = self.statusBar()
    status.setSizeGripEnabled(True)
    status.showMessage("Ready", 5000)

    ## Actions
    # Open two image sets
    filesOpenAction = self.createAction("&Open two image sets",
                                        self.loadTwoImageSets,
                                        QKeySequence.Open,
                                        "24x24/2-documents-open",
                                        "Open two sets of images for viewing and comparing")
    # Open one image set
    fileOpenAction  = self.createAction("Op&en single image set",
                                        self.loadImageSet,
                                        None,
                                        "24x24/document-open",
                                        "Open a set of images for viewing")
    # Exit program
    fileQuitAction = self.createAction("&Quit",
                                       self.close,
                                       "Ctrl+Q",
                                       "24x24/exit",
                                       "Close the application")
    # Display "About" dialog
    helpAboutAction= self.createAction("&About",
                                       self.helpAbout,
                                       None,
                                       "helpabout",
                                       "More information about this program")

    # Menus and toolbars
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
    """React to the user manipulating the frame control slider"""
    if newValue == self.currentIndex:
      return
    self.changeFrame(newValue)

  def helpAbout(self):
    """Display "About" dialog"""
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
    """Add a list of actions (and separators) to a menu/toolbar target"""
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
    """Shortcut for creating a QAction object and setting attributes"""
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
    """Load a set of images, discovered from one specimen selected by the user"""
    if side not in (0,1):
      return False
    # Use previously opened folder (if applicable)
    dir = '.'
    if self.filenames[side]:
      dir = os.path.dirname(self.filenames[side])
    elif self.filenames[1-side]:
      dir = os.path.dirname(self.filenames[1-side])
    formats = ['*.%s' % unicode(format).lower() \
               for format in QImageReader.supportedImageFormats()]
    header = "Choose member of %simage set" % ["", "second "][side]
    fname = unicode(QFileDialog.getOpenFileName(
              self,
              "%s - %s" % (QApplication.applicationName(), header),
              dir,
              "Image files (%s)" % ' '.join(formats)))
    # If the user selected a file, autodiscover a fitting set
    if fname:
      self.loadFiles(fname, side)
      return True
    return False

  def resetFrameSlider(self):
    """Reset the frame control slider to 0 and update range and label"""
    if not self.filesets[0]:
      return
    self.frameSlider.setRange(0,len(self.filesets[0])-1)
    self.frameSlider.setValue(0)
    self.frameSliderLabel.setText("Frame: 1")


  def loadImageSet(self):
    """Load files for one image set"""
    if self.fileOpen(0):
      self.filesets[1] = self.filesets[0]
      self.mode = self.ONE_SET
      self.currentIndex = 0
      self.updateMask()
      self.showImage()
      self.resetFrameSlider()
      self.setWindowTitle("%s - %s" % (QApplication.applicationName(),
                                       self.filenames[0]))

  def loadTwoImageSets(self):
    """Load files for two image sets"""
    if self.fileOpen(0) and self.fileOpen(1):
      ## Ensure both image sets have the same size
      sizes = (self.filesets[0][0].size(), self.filesets[1][0].size())
      if sizes[0] != sizes[1]:
        larger_size = QSize(max(sizes[0].width(),  sizes[1].width()),
                            max(sizes[0].height(), sizes[1].height()))
        for side in [0,1]:
          if sizes[side] != larger_size:
            fs = "first" if side==0 else "second"
            for i in xrange(len(self.filesets[side])):
              self.updateStatus("Resizing %s dataset... %d/%d." % \
                                (fs, i, len(self.filesets[side])))
              self.filesets[side][i] = self.filesets[side][i].scaled(
                                      larger_size,
                                      transformMode=Qt.SmoothTransformation)
      self.mode = self.TWO_SETS
      self.currentIndex = 0
      self.updateMask()
      self.showImage()
      self.resetFrameSlider()


  def chooseFileSetGenerator(self, generators):
    """Let the user choose a file set"""
    if not generators:
      raise Exception("No generators given!")
    if len(generators) == 1:
      return generators[0]
    descriptions = []
    # Options from which the user can choose
    for g in generators:
      amount = g.upper-g.lower+1
      basename_template = os.path.split(g.template)[1]
      examples = [os.path.split(s)[1] for s in g.generateFiles()]
      if len(examples) == 1:
        descriptions.append("(Only this file) %s" % examples[0])
      elif len(examples) > 3:
        descriptions.append("(%d files) %s,..." % (amount, 
                                                  ", ".join(examples[:3])))
      else:
        descriptions.append("(%d files) %s" % (amount, ", ".join(examples)))
    # Create dialog
    dialog = GeneratorChooseDlg(descriptions, self)
    if dialog.exec_():
      return generators[dialog.options.currentRow()]


  def loadFiles(self, fname=None, side=None):
    """Load file set, given one specimen (fname)"""
    if fname is None or \
       side not in (0,1):
      return
    potential_sets = self.findFiles(fname)
    # Sort potential_sets according to set cardinality
    potential_sets.sort(reverse=True)
    chosen = self.chooseFileSetGenerator(potential_sets)
    if chosen is None:
      return
    found_filenames = chosen.generateFiles()
    if not found_filenames:
      found_filenames = [fname]
    _images = []
    # TODO Ask user to specify image range within found_filenames to load
    for i,f in enumerate(found_filenames):
      # TODO Allow cancelling
      self.updateStatus("Reading images... %d/%d." % (i, len(found_filenames)))
      image = QImage(f)
      if image.isNull():
        message = "Failed to read '%s'!" % f
        break
      else:
        _images.append(image.convertToFormat(QImage.Format_ARGB32))
    else:
      self.filesets[side] = _images
      message = "Loaded %d files around '%s'." % \
                (len(found_filenames), found_filenames[0])
    self.updateStatus(message)

  def findFiles(self, fname=None):
    """
    Discover image set, given one specimen (fname)
    Returns a list of tuples (T, l, lower, upper) where a set of found
    filenames can be generated by [T % (l,i) for i in range(lower,upper+1)]
    """
    if fname is None:
      return
    # Only search for numberings withing the filename, not the path
    # TODO future feature?
    fpathname, fbasename = os.path.split(fname)
    found_sets = []
    number_groups = []
    for match in self.RE_EXTRACT_NUMBER.finditer(fbasename):
      number = int(match.group(1))
      start, end = match.start(), match.end()
      length = end-start
      template = fpathname + '/' + fbasename[:start] + '%0*d' + fbasename[end:]
      found = []
      n = number-1
      while os.path.isfile(template % (length,n)):
        found.append(template % (length,n))
        n -= 1
      lower = n+1
      found = found[::-1]
      n = number
      while os.path.isfile(template % (length,n)):
        found.append(template % (length,n))
        n += 1
      upper = n-1
      found_sets.append(FilesetFilenamesGenerator(template, length, lower, upper))
    return found_sets
  
  def changeFrame(self, index):
    """Change the displayed frame"""
    self.currentIndex = index
    self.showImage()
    self.updateStatus("Frame %d/%d" % (self.currentIndex+1,
                                       len(self.filesets[0])))
    self.frameSliderLabel.setText("Frame: %d" % (index+1))
    self.frameSlider.setValue(index)

  def wheelEvent(self, event):
    """Scroll through image set via mouse wheel"""
    cid = self.currentIndex
    if event.delta() > 0:
      cid += 1
    else:
      cid -= 1
    cid = max(cid, 0)
    cid = min(cid, len(self.filesets[0])-1)
    self.changeFrame(cid)

  def showImage(self):
    """Update the image shown in the central label"""
    # ONE image set
    if   self.mode == self.ONE_SET:
      if not self.filesets[0] or \
         self.currentIndex < 0 or \
         self.currentIndex >= len(self.filesets[0]):
        return
      self.imageLabel.setMinimumSize(self.filesets[0][self.currentIndex].size())
      self.labelImage = QImage(self.filesets[0][self.currentIndex])
      self.imageLabel.setPixmap(QPixmap.fromImage(self.labelImage))
    # TWO image sets
    elif self.mode == self.TWO_SETS:
      if not self.filesets[0] or \
         not self.filesets[1] or \
         self.currentIndex < 0 or \
         self.currentIndex >= len(self.filesets[0]) or \
         self.currentIndex >= len(self.filesets[1]):
        return
      self.imageLabel.setMinimumSize(self.filesets[0][self.currentIndex].size())
      # Blend the two images using alpha mask
      i0 = self.filesets[0][self.currentIndex]
      i1 = self.filesets[1][self.currentIndex]
      i0.setAlphaChannel(self.masks[0])
      i1.setAlphaChannel(self.masks[1])
      self.labelImage = QImage(i0.size(), QImage.Format_ARGB32)
      painter = QPainter(self.labelImage)
      painter.drawImage(0, 0, i0)
      painter.drawImage(0, 0, i1)
      self.imageLabel.setPixmap(QPixmap.fromImage(self.labelImage))

  def updateMask(self):
    """Update the alpha masks used for blending two images"""
    if not self.filesets[0]:
      return
    mask = QImage(self.filesets[0][0].size(), QImage.Format_ARGB32)
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
    """Write a new message to the application's status bar"""
    if message is None:
      return
    self.statusBar().showMessage(message, 5000)



def main():
  #style = QStyleFactory.create("cleanlooks")
  #QApplication.setStyle(style)
  app = QApplication(sys.argv)
  app.setApplicationName("Image Changer")
  app.setWindowIcon(QIcon(':/24x24/icon.png'))
  form = MainWindow()
  form.show()
  app.exec_()

if __name__ == '__main__':
  main()

