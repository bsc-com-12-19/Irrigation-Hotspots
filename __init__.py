# -*- coding: utf-8 -*-
"""
/***************************************************************************
 irrigationHotspots
                                 A QGIS plugin
 It identifies areas that are close to rivers and roads for good irrigation and accessibility. It also tries to identify usable land.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-11-29
        copyright            : (C) 2024 by Group11
        email                : bsc-com-32-20@unima.ac.mw
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load irrigationHotspots class from file irrigationHotspots.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .irrigation_hotspots import irrigationHotspots
    return irrigationHotspots(iface)
