########################################################################################################################
# MODULES
########################################################################################################################

# Import Modules
import os
import sys
import subprocess
import yaml
import numpy as np
import pandas as pd
import sqlite3

########################################################################################################################
########################################################################################################################

# tmp directory
tmp_dir = os.path.join(os.getcwd(), 'tmp_dir')
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)


########################################################################################################################
# FUNCTIONS
########################################################################################################################


# Connect to sqlite dbase
def db_connect(dbase_path):
    conn = sqlite3.connect(dbase_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables_list = np.array([i[0] for i in cursor.fetchall()])
    conn.enable_load_extension(True)
    conn.execute('SELECT load_extension("mod_spatialite.dll")')
    if len(existing_tables_list) == 0:
        conn.execute('SELECT InitSpatialMetaData(1)')
    else:
        if not np.any(existing_tables_list == 'spatial_ref_sys'):
            conn.execute('SELECT InitSpatialMetaData(1)')

    return conn, cursor


def drop_sqlite_table(dbase, table):

    if os.path.isfile(dbase):
        my_executable = os.environ['EXT_SPATIALITE_PATH']
        sql_file = os.path.join(tmp_dir, 'sql_file.sql')
        with open(sql_file, 'w') as f:
            f.write('SELECT load_extension("mod_spatialite");\n')
            f.write('SELECT DropGeoTable(\"{}\");\n'.format(table))
            f.write('DROP TABLE IF EXISTS \"{}\";\n'.format(table))
        startcmd = my_executable + ' \"' + dbase + '\" < ' + sql_file
        p = subprocess.Popen(startcmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out, err

    else:
        print('Database does not exist! Nothing deleted')


# Sqlite table to pandas
def sqlite_to_pandas(dbase_path, table, geocol=None):
    conn, cursor = db_connect(dbase_path=dbase_path)

    query_table = 'SELECT * FROM {}'.format(table)
    df = pd.read_sql_query(query_table, conn)

    if geocol:
        query_geom = 'SELECT AsWKT(\"{}\", 30) FROM \"{}\";'.format(geocol, table)
        cursor.execute(query_geom)
        geo_values = [str(i[0]) for i in cursor.fetchall()]
        df['geom'] = geo_values

    conn.close()
    return df


def get_table_names_types_sqlite(cursor, table):
    sql_query = 'PRAGMA table_info(\"{}\");'.format(table)
    cursor.execute(sql_query)
    colnames = np.array([i[1] for i in cursor.fetchall()])
    cursor.execute(sql_query)
    coltypes = np.array([i[2] for i in cursor.fetchall()])
    cursor.execute(sql_query)

    pk = [i[1] for i in cursor.fetchall() if i[-1] != 0][0]

    return colnames, coltypes, pk


def write_sqlite_table_from_pandas(dbase, table, columns_info, data, geocol='', epsg=None):

    # Drop table if exists
    drop_sqlite_table(dbase=dbase, table=table)

    cols_data = [i for i in columns_info if i[0] != geocol]
    col_geom = [i for i in columns_info if i[0] == geocol][0]

    # Create table
    connection, cursor = db_connect(dbase_path=dbase)
    cursor.execute('BEGIN TRANSACTION;')

    cols = ', '.join(['\"{}\" {}'.format(i[0], i[1]) for i in cols_data])
    cols = '\"fid\" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, ' + cols
    sql_query = 'CREATE TABLE \"{}\" ({});'.format(table, cols)
    cursor.execute(sql_query)

    if len(col_geom) == 2:
        sql_query = 'SELECT AddGeometryColumn(\"{}\", \"{}\", {}, \"{}\", \"XY\")'.format(table, col_geom[0],
                                                                                          epsg, col_geom[1])
        cursor.execute(sql_query)

    elif len(col_geom) > 2:
        print ('Error in geometry column. More than one entry')
        exit(1)

    # Add data
    colnames = [i[0] for i in cols_data]
    df = pd.DataFrame(data, columns=colnames)
    geom = pd.DataFrame(data, columns=[col_geom[0]])

    query_values = '\"' + df.astype(str) + '\"'
    query_values = query_values.apply(','.join, axis=1)
    query_values = query_values.str.replace('\"None\"', 'null', regex=False)
    query_values = query_values.str.replace('\"nan\"', 'null', regex=False)

    query_geo_values = 'GeomFromText(' + '\"' + geom + '\"' + ', ' + str(epsg) + ')'
    query_geo_values = query_geo_values.apply(','.join, axis=1)

    for query, geo_query in zip(query_values,  query_geo_values):
        # print(query)
        if geocol:
            sql_query = 'INSERT INTO \"{}\" VALUES (NULL, {}, {});'.format(table, query, geo_query)
        else:
            sql_query = 'INSERT INTO \"{}\" VALUES (NULL, {});'.format(table, query)

        cursor.execute(sql_query)

    # Create spatial index
    if geocol:
        sql_query = 'SELECT CreateSpatialIndex(\"{}\", \"{}\");'.format(table, col_geom[0])
        cursor.execute(sql_query)

    connection.commit()
