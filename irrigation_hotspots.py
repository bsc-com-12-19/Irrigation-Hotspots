# -*- coding: utf-8 -*-
"""
/***************************************************************************
 irrigationHotspots
                                 A QGIS plugin
 It identifies areas that are close to rivers and roads for good irrigation and accessibility. It also tries to identify usable land.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-11-29
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Group11
        email                : bsc-com-32-20@unima.ac.mw
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import psycopg2
from qgis.core import QgsVectorLayer

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .irrigation_hotspots_dialog import irrigationHotspotsDialog
import os.path
from qgis.core import (
    QgsVectorLayer,
    QgsProcessingFeatureSourceDefinition,
    QgsProcessing,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProject,
    QgsProcessingFeedback,
)
from qgis import processing


class irrigationHotspots:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'irrigationHotspots_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Irrigation Hotspots')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('irrigationHotspots', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/irrigation_hotspots/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Identifies areas suitable for irrigation'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Irrigation Hotspots'),
                action)
            self.iface.removeToolBarIcon(action)


    def connect_to_database(self):
        """Establish a connection to the PostGIS database."""
        try:
            conn = psycopg2.connect(
                dbname="irrigation",
                user="postgres",
                password="postgres",
                host="localhost",
                port="5432"
            )
            return conn
        except Exception as e:
            self.iface.messageBar().pushCritical("Database Connection Error", str(e))
            return None

    def fetch_layers(self, conn):
        """Fetch available PostGIS layers for combo boxes."""
        try:
            cur = conn.cursor()
            cur.execute("SELECT f_table_name FROM geometry_columns;")
            layers = [row[0] for row in cur.fetchall()]
            cur.close()
            return layers
        except Exception as e:
            self.iface.messageBar().pushCritical("Error Fetching Layers", str(e))
            return []

    def create_buffer(self, conn, layer_name, distance):
        """Create a buffer for the specified layer in the database."""
        try:
            buffer_table = f"{layer_name}_buffer"
            query = f"""
                DROP TABLE IF EXISTS {buffer_table};
                CREATE TABLE {buffer_table} AS
                SELECT ST_Buffer(geom, {distance}) AS geom
                FROM {layer_name};
            """
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            cur.close()
            return buffer_table
        except Exception as e:
            self.iface.messageBar().pushCritical("Error Creating Buffer", str(e))
            return None

    def find_irrigation_areas(self, conn, river_buffer, road_buffer, population_layer):
        """Identify suitable irrigation areas by intersecting buffers and population layer."""
        try:
            result_table = "irrigation_areas"
            common_srid = 4326  # Ensure all geometries are in this SRID
            query = f"""
                DROP TABLE IF EXISTS {result_table};
                CREATE TABLE {result_table} AS
                SELECT 
                    ST_Intersection(
                        ST_Transform(a.geom, {common_srid}),
                        ST_Transform(b.geom, {common_srid})
                    ) AS geom
                FROM {river_buffer} AS a
                JOIN {road_buffer} AS b
                ON ST_Intersects(
                    ST_Transform(a.geom, {common_srid}),
                    ST_Transform(b.geom, {common_srid})
                )
                JOIN {population_layer} AS c
                ON ST_Intersects(
                    ST_Transform(a.geom, {common_srid}),
                    ST_Transform(c.geom, {common_srid})
                )
                WHERE c.TotalPopn < 1000;
            """
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            cur.close()
            return result_table
        except Exception as e:
            self.iface.messageBar().pushCritical("Error Finding Irrigation Areas", str(e))
            return None

    def load_layer_into_qgis(self, layer_name, layer_alias):
        """Load a PostGIS table into QGIS as a layer."""
        uri = f"dbname='irrigation' host='localhost' port='5432' user='postgres' password='postgres' table=\"{layer_name}\" (geom)"
        layer = QgsVectorLayer(uri, layer_alias, "postgres")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
        else:
            self.iface.messageBar().pushCritical("Error Loading Layer", f"Layer {layer_alias} could not be loaded.")

    def load_csv_as_layer(self, csv_path, layer_name):
        """Load a CSV file as a QGIS layer."""
        uri = f"file://{csv_path}?type=csv&xField=longitude&yField=latitude&crs=EPSG:4326"
        layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            return layer
        else:
            self.iface.messageBar().pushCritical("Error Loading CSV", f"Could not load the CSV file {layer_name}.")
            return None

    def run(self):
        """Run the plugin logic."""
        if self.first_start:
            self.first_start = False
            self.dlg = irrigationHotspotsDialog()

        # Establish database connection
        conn = self.connect_to_database()
        if not conn:
            return

        # Fetch available layers and populate combo boxes
        layers = self.fetch_layers(conn)
        self.dlg.comboBox.clear()
        self.dlg.comboBox.addItems(layers)
        self.dlg.comboBox_2.clear()
        self.dlg.comboBox_2.addItems(layers)
        self.dlg.comboBox_3.clear()
        self.dlg.comboBox_3.addItems(layers)

        # Show the dialog
        self.dlg.show()
        result = self.dlg.exec_()

        if result:
            # Get user-selected layers and buffer distance
            river_layer = self.dlg.comboBox.currentText()
            road_layer = self.dlg.comboBox_2.currentText()
            population_layer = self.dlg.comboBox_3.currentText()

            if not river_layer or not road_layer or not population_layer:
                self.iface.messageBar().pushWarning("Selection Error", "Please select all required layers.")
                return

            # Create buffers for the river and road layers
            river_buffer = self.create_buffer(conn, river_layer, 100)  # Example: 100m buffer
            road_buffer = self.create_buffer(conn, road_layer, 50)   # Example: 50m buffer

            if not river_buffer or not road_buffer:
                return

            # Identify irrigation areas
            irrigation_areas = self.find_irrigation_areas(conn, river_buffer, road_buffer, population_layer)
            if not irrigation_areas:
                return

            # Load the irrigation areas layer into QGIS
            self.load_layer_into_qgis(irrigation_areas, "Irrigation Areas")

        # Close the database connection
        conn.close()