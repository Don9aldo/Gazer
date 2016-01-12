from __future__ import unicode_literals, division, print_function

import logging
import sys

from PyQt4 import QtGui

import gcviewer.eyetracking.api
from gcviewer.qt_gui.mainwindow import GCImageViewerMainWindow

logging.basicConfig(filename='log.debug', level=logging.DEBUG)

logger = logging.getLogger(__name__)


def run_qt_gui():
    """
    Set up example configuration to run qt gui with eyex and save log files.
    """

    app = QtGui.QApplication(sys.argv)
    tracking_apis = gcviewer.eyetracking.api.get_available()
    logger.debug(
        'Available tracking apis: {}'.format(str(tracking_apis.keys())))
    imageViewer = GCImageViewerMainWindow(tracking_apis)
    imageViewer.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        run_qt_gui()
    except Exception:
        logging.exception('Program terminated with an exception. ')
