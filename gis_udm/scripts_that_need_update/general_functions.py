# import importlib
# importlib.reload(ex)

# General Modules
import os
import sys
import subprocess
import shutil
import yaml
import numpy as np
import pandas as pd

# Qgis modules
from pyqgis.initialize_qgis import *
import pyqgis.sqlite_functions as sq



# Geometry check context setting
context = dataobjects.createContext()
context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)


def algorithms_list(kw=''):
    if kw == 'all':
        for alg in QgsApplication.processingRegistry().algorithms():
            print(alg.id(), "->", alg.displayName())
    else:
        for alg in QgsApplication.processingRegistry().algorithms():
            if kw in alg.id():
                print(alg.id(), "->", alg.displayName())


def algorithms_help(name):
    processing.algorithmHelp(name)


def read_shp(source=''):
    data_source = source
    layer_name = data_source.split('\\')[-1].split('.')[0]
    provider_name = 'ogr'
    layer = QgsVectorLayer(data_source, layer_name, provider_name)

    if layer.isValid():
        print('Layer loaded successfully!!')
        return layer
    else:
        raise Exception('Layer was not loaded successfully!!')


def read_shp_copy(source=''):
    data_source = source
    layer_name = data_source.split('\\')[-1].split('.')[0]
    provider_name = 'ogr'
    layer = QgsVectorLayer(data_source, layer_name, provider_name)

    if layer.isValid():
        # Create copy of layer
        layer.selectAll()
        tool = 'native:saveselectedfeatures'
        parameters = {'INPUT': layer,
                      'OUTPUT': 'memory:{}'.format(layer_name)}

        copy = processing.run(tool, parameters)['OUTPUT']

        print('Layer copy created and loaded successfully!!')
        return copy
    else:
        raise Exception('Layer was not loaded successfully!!. Copy not created!')


def read_db(dbname='', layer_name=''):
    source = '{}|layername={}'.format(dbname, layer_name)
    layer = QgsVectorLayer(source, layer_name, 'ogr')

    if layer.isValid():
        print('Layer loaded successfully!!')
        return layer
    else:
        raise Exception('Layer was not loaded successfully!!')


def read_db_copy(dbname='', layer_name=''):
    source = '{}|layername={}'.format(dbname, layer_name)
    layer = QgsVectorLayer(source, layer_name, 'ogr')

    if layer.isValid():
        # Find primary key
        con, cur = sq.db_connect(dbname)
        sql_query = 'PRAGMA table_info(\"{}\");'.format(layer_name)
        cur.execute(sql_query)
        pk = [i[1] for i in cur.fetchall() if i[-1] != 0][0]
        con.close()

        # Create copy of layer
        layer.selectAll()
        tool = 'native:saveselectedfeatures'
        parameters = {'INPUT': layer,
                      'OUTPUT': 'memory:{}'.format(layer_name)}

        copy = processing.run(tool, parameters)['OUTPUT']

        # Manage attribute table of copy
        copy_pr = copy.dataProvider()
        del_fields = [copy.fields().indexFromName(i) for i in copy.fields().names() if i in [pk]]
        copy_pr.deleteAttributes(del_fields)
        copy.updateFields()

        print('Layer copy created and loaded successfully!!')
        return copy
    else:
        raise Exception('Layer was not loaded successfully!!. Copy not created!')


def read_raster(path):
    layer_name = path.split('\\')[-1].split('.')[0]
    rlayer = QgsRasterLayer(path, layer_name)
    if rlayer.isValid():
        print("Layer loaded successfully!")
        return rlayer
    else:
        print("Layer failed to load!")


def clean_vector_qgis(layer, remove_area, remove_small_holes=False):

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': layer,
        'OUTPUT': 'memory:'
    }
    single_layer = processing.run(tool, parameters, context=context)['OUTPUT']

    # Remove null geometries
    print('REMOVE NULL GEOMETRIES')
    tool = 'native:removenullgeometries'
    parameters = {
        'INPUT': single_layer,
        'OUTPUT': 'memory:'
    }
    non_null_geometries = processing.run(tool, parameters, context=context)['OUTPUT']

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': non_null_geometries,
        'OUTPUT': 'memory:'
    }
    single_non_null_geometries = processing.run(tool, parameters, context=context)['OUTPUT']

    # Fix geometry
    print('FIX GEOMETRY')
    tool = 'native:fixgeometries'
    parameters = {
        'INPUT': single_non_null_geometries,
        'OUTPUT': 'memory:'
    }
    fixed = processing.run(tool, parameters, context=context)['OUTPUT']

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': fixed,
        'OUTPUT': 'memory:'
    }
    single_fixed = processing.run(tool, parameters, context=context)['OUTPUT']

    # Simplify
    print('SIMPLIFY GEOMETRIES WITH VERY SMALL THRESHOLD')
    tool = 'native:simplifygeometries'
    parameters = {
        'INPUT': single_fixed,
        'METHOD': 0,
        'TOLERANCE': 0.001,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }
    simplified = processing.run(tool, parameters, context=context)['OUTPUT']

    # Delete duplicate geometries
    print('DELETE DUPLICATE GEOMETRIES')
    tool = 'qgis:deleteduplicategeometries'
    parameters = {
        'INPUT': simplified,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }
    non_duplicates = processing.run(tool, parameters, context=context)['OUTPUT']

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': non_duplicates,
        'OUTPUT': 'memory:'
    }
    single_non_duplicates = processing.run(tool, parameters, context=context)['OUTPUT']

    # Eliminate small residual polygons
    print('ELIMINATE SMALL RESIDUAL POLYGONS')
    # Selection of features
    selection_ids = []
    for feat in single_non_duplicates.getFeatures():
        if feat.geometry().area() <= remove_area:
            selection_ids.append(feat.id())
    single_non_duplicates.selectByIds(selection_ids)
    QgsProject.instance().addMapLayer(single_non_duplicates, False)
    # Eliminate residual polygons
    tool = 'qgis:eliminateselectedpolygons'
    parameters = {
        'INPUT': single_non_duplicates.id(),
        'MODE': 0,
        'OUTPUT': 'memory:'
    }
    eliminate_residual = processing.run(tool, parameters, context=context)['OUTPUT']

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': eliminate_residual,
        'OUTPUT': 'memory:'
    }
    single_eliminate_residual = processing.run(tool, parameters, context=context)['OUTPUT']

    # Remove small areas
    print('REMOVE SMALL AREAS')
    # Selection of features
    selection_ids = []
    for feat in single_eliminate_residual.getFeatures():
        if feat.geometry().area() > remove_area:
            selection_ids.append(feat.id())
    single_eliminate_residual.selectByIds(selection_ids)
    # Save selected features
    tool = 'native:saveselectedfeatures'
    parameters = {
        'INPUT': single_eliminate_residual,
        'OUTPUT': 'memory:'
    }
    remove_small_areas = processing.run(tool, parameters)['OUTPUT']

    # Multi to single
    print('CONVERT MULTI-GEOMETRY TO SINGLE')
    tool = 'native:multiparttosingleparts'
    parameters = {
        'INPUT': remove_small_areas,
        'OUTPUT': 'memory:'
    }
    single_small_area = processing.run(tool, parameters, context=context)['OUTPUT']

    if remove_small_holes:
        # Delete small holes
        print('DELETE HOLES')
        tool = 'native:deleteholes'
        parameters = {
            'INPUT': single_small_area,
            'MIN_AREA': remove_area,
            'OUTPUT': 'memory:'
        }
        delete_holes = processing.run(tool, parameters)['OUTPUT']

        # Multi to single
        print('CONVERT MULTI-GEOMETRY TO SINGLE')
        tool = 'native:multiparttosingleparts'
        parameters = {
            'INPUT': delete_holes,
            'OUTPUT': 'memory:'
        }
        single_delete_holes = processing.run(tool, parameters, context=context)['OUTPUT']

        single_final = single_delete_holes
    else:
        single_final = single_small_area

    return single_final


def line_mid_point(layer):

    # Get fields from original layer
    fields = layer.fields()

    # Get epsg
    crs = layer.crs().authid()

    # Create points layer
    mid_point = QgsVectorLayer('Point?crs={}'.format(crs), 'mid_point', 'memory')
    mid_point_pr = mid_point.dataProvider()
    mid_point_pr.addAttributes(fields)
    mid_point.updateFields()

    for i in layer.getFeatures():
        geom = i.geometry()
        length = geom.length()
        point_geom = geom.interpolate(length / 2.0)
        feat = QgsFeature()
        feat.setGeometry(point_geom)
        feat.setAttributes(i.attributes())
        mid_point_pr.addFeatures([feat])

    mid_point.updateExtents()

    return mid_point


def layer_df(layer):
    data = []
    for i in layer.getFeatures():
        data.append(i.attributes())

    df = pd.DataFrame(data, columns=layer.fields().names())
    idx_ = (df.astype(str).apply(lambda col: col.str.upper()) == 'NULL') | (pd.isnull(df))
    df[idx_] = np.nan

    return df


def df_to_layer_attributes(df, layer):
    pr = layer.dataProvider()
    del_fields = [layer.fields().indexFromName(name) for name in layer.fields().names()]
    pr.deleteAttributes(del_fields)
    layer.updateFields()

    attributes = []
    for i, j in zip(df.columns, df.dtypes):
        if 'object' in str(j):
            type_ = QVariant.String
            typeName = 'string'
        elif 'float' in str(j):
            type_ = QVariant.Double
            typeName = 'double'
        elif 'int' in str(j):
            type_ = QVariant.Int
            typeName = 'integer'
        else:
            type_ = QVariant.String
            typeName = 'string'

        attributes.append(QgsField(i, type_, typeName=typeName))

    pr.addAttributes(attributes)
    layer.updateFields()

    layer_colnum = range(len(df.columns))
    layer_vals = df.values
    attrs_dict = {}
    for nn, feat in enumerate(layer.getFeatures()):
        vals_dict = {i: j for i, j in zip(layer_colnum, list(layer_vals[nn]))}
        attrs_dict[feat.id()] = vals_dict

    pr.changeAttributeValues(attrs_dict)
    layer.updateFields()
