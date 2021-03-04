# import sys
# import importlib
# importlib.reload(sys.modules['gis_udm_tools.land_cover'])

#%%
# Modules
import os
import geopandas as gpd
from gis_udm import utils, land_cover

#%%
# Set working directory
os.chdir(r'gis_udm\Examples\example_01')

#%%
# Input/Output database (Geopackage) 
# use os.path to create paths that are platform independent
input_gpkg = os.path.join(os.getcwd(), 'input_dbase.gpkg')
output_gpkg = os.path.join(os.getcwd(), 'output_dbase.gpkg')

# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------

# Generate Land Cover Topology
#%%
# Create land cover class
lc = land_cover.LandCover(input_gpkg, output_gpkg, crs='EPSG:31370')

#%%
# import boundary
lc.preprocess_boundary('boundary', simplify=1)

#%%
# import land cover layers
lc.preprocess_land_cover_layer(
    layer='building_blocks',
    priority=1,
    boundary='boundary',
    seglen=1,
    snap=0.5,
    buffer_err=0.03,
    simplify=1,
    area_thr=10,
    remove_inner_rings=True
)

# Check preprocess result
# bb = lc.gs.to_gpd('building_blocks')
# lc.gs.to_gpkg('building_blocks', 'test_db.gpkg', 'building_blocks')
# bb.crs
# bb.plot()


lc.preprocess_land_cover_layer(
    layer='permeable',
    priority=2,
    boundary='boundary',
    seglen=1,
    snap=0.55,
    buffer_err=0.03,
    simplify=1,
    area_thr=10
)

# Check preprocess result
# p = lc.gs.to_gpd('permeable')
# lc.gs.to_gpkg('permeable', 'test_db.gpkg', 'permeable')
# p.crs
# p.plot()

#%%
# generate land cover interactive
layers = ['building_blocks', 'permeable']
priorities = [1, 2]
lc.generate_land_cover_interactive(
    layers=layers,
    priorities=priorities,
    boundary='boundary',
    seglen=1,
    area_thr=10,
    snap=1,
    simplify=1,
    output='land_cover'
)

# Check land cover interactive result
# lci = lc.gs.to_gpd('land_cover')
# lci.crs
# lci.plot()

#%%
# generate land cover static
# (this is an alternative method to generate the land cover polygons, however, land cover interactive is preferred.)
layers = ['building_blocks', 'permeable']
priorities = [1, 2]
lc.generate_land_cover_static(
    layers=layers,
    priorities=priorities,
    boundary='boundary',
    resolution=0.5,
    area_thr=10,
    snap=1,
    simplify=1,
    seglen=1,
    output='land_cover_static'
)

# Check land cover static result
# lcs = lc.gs.to_gpd('land_cover_static')
# lcs.crs
# lcs.plot()

#%%
# consolidate topology land cover interactive
lc.consolidate_topology(
    boundary='boundary',
    land_cover='land_cover',
    seglen=2,
    snap=1,
    simplify=1,
    area_thr=10,
    output_boundary='boundary',
    output_land_cover='land_cover'
)

# consolidate topology land cover static
lc.consolidate_topology(
    boundary='boundary',
    land_cover='land_cover_static',
    seglen=2,
    snap=1,
    simplify=1,
    area_thr=10,
    output_boundary='boundary_static',
    output_land_cover='land_cover_static'
)

#%%
# purge land cover topology class
lc.purge()

# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------
