########################################################################################################################
# INITIALIZE QGIS
########################################################################################################################

# Import main modules
import os
from qgis.core import *
from qgis.PyQt.QtCore import QVariant

QgsApplication.setPrefixPath(os.environ['QGIS_PREFIX_PATH'], True)  # Supply path to qgis install location
qgs = QgsApplication([], False)  # Create a reference to the QgsApplication, setting the second argument to False disables the GUI
qgs.initQgis()  # Load providers

# Import processing modules
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms

Processing.initialize()  # Initialize processing algorithms
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())  # Register native algorithms

import processing
from processing.tools import dataobjects
context = dataobjects.createContext()
context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)
