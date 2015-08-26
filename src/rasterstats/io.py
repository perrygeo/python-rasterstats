import json
import fiona
from shapely.geos import ReadingError
from shapely import wkt, wkb
from collections import Iterable, Mapping


geom_types = ["Point", "LineString", "Polygon",
              "MultiPoint", "MultiLineString", "MultiPolygon"]


def wrap_geom(geom):
    """ Wraps a geometry dict in an GeoJSON Feature
    """
    return {'type': 'Feature',
            'properties': {},
            'geometry': geom}


def parse_feature(obj):
    """ Given a python object
    attemp to a GeoJSON-like Feature from it
    """

    # object implementing geo_interface
    if hasattr(obj, '__geo_interface__'):
        gi = obj.__geo_interface__
        if gi['type'] in geom_types:
            return wrap_geom(gi)
        elif gi['type'] == 'Feature':
            return gi

    # wkt
    try:
        shape = wkt.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ReadingError, TypeError, AttributeError):
        pass

    # wkb
    try:
        shape = wkb.loads(obj)
        return wrap_geom(shape.__geo_interface__)
    except (ReadingError, TypeError):
        pass

    # geojson-like python mapping
    try:
        if obj['type'] in geom_types:
            return wrap_geom(obj)
        elif obj['type'] == 'Feature':
            return obj
    except (AssertionError, TypeError):
        pass

    raise ValueError("Can't parse %s as a geojson Feature object" % obj)


def geo_records(vectors):
    for vector in vectors:
        yield parse_feature(vector)


def read_features(obj, layer_num=0):
    features_iter = None
    if isinstance(obj, str):
        try:
            # test it as fiona data source
            with fiona.open(obj, 'r') as src:
                assert len(src) > 0

            def fiona_generator(obj):
                with fiona.open(obj, 'r') as src:
                    for feature in src:
                        yield feature

            features_iter = fiona_generator(obj)
        except (AssertionError, TypeError, IOError, OSError):
            try:
                mapping = json.loads(obj)
                if 'type' in mapping and mapping['type'] == 'FeatureCollection':
                    features_iter = mapping['features']
                elif mapping['type'] in geom_types + ['Feature']:
                    features_iter = [parse_feature(mapping)]
            except ValueError:
                # Single feature-like string
                features_iter = [parse_feature(obj)]
    elif isinstance(obj, Mapping):
        if 'type' in obj and obj['type'] == 'FeatureCollection':
            features_iter = obj['features']
        else:
            features_iter = [parse_feature(obj)]
    elif isinstance(obj, Iterable):
        # Iterable of feature-like objects
        features_iter = (parse_feature(x) for x in obj)
    elif hasattr(obj, '__geo_interface__'):
        mapping = obj.__geo_interface__
        if mapping['type'] == 'FeatureCollection':
            features_iter = mapping['features']
        else:
            features_iter = [parse_feature(mapping)]
    else:
        # Single feature-like object
        features_iter = [parse_feature(obj)]

    if not features_iter:
        raise ValueError("Object is not a recognized source of Features")
    return features_iter


def read_featurecollection(obj, lazy=False):
    features = read_features(obj)
    fc = {'type': 'FeatureCollection', 'features': []}
    if lazy:
        fc['features'] = (f for f in features)
    else:
        fc['features'] = [f for f in features]
    return fc
