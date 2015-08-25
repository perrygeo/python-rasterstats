import json
import fiona
from shapely.geos import ReadingError
from shapely import wkt, wkb

def parse_geo(thing):
    """ Given a python object, try to get a geo-json like mapping from it
    """

    # object implementing geo_interface
    try:
        geo = thing.__geo_interface__
        return geo
    except AttributeError:
        pass

    # wkb
    try:
        shape = wkb.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError):
        pass

    # wkt
    try:
        shape = wkt.loads(thing)
        return shape.__geo_interface__
    except (ReadingError, TypeError, AttributeError):
        pass

    # geojson-like python mapping
    valid_types = ["Feature", "Point", "LineString", "Polygon",
                   "MultiPoint", "MultiLineString", "MultiPolygon"]
    try:
        assert thing['type'] in valid_types
        return thing
    except (AssertionError, TypeError):
        pass

    # geojson string
    try:
        maybe_geo = json.loads(thing)
        assert maybe_geo['type'] in valid_types + ["FeatureCollection"]
        return maybe_geo
    except (ValueError, AssertionError, TypeError):
        pass

    raise ValueError("Can't parse %s as a geo-like object" % thing)


def geo_records(vectors):
    for vector in vectors:
        yield parse_geo(vector)


def get_features(vectors, layer_num=0):
    if isinstance(vectors, str):
        try:
            # test it as fiona data source
            with fiona.open(vectors, 'r') as src:
                assert len(src) > 0

            def fiona_generator(vectors):
                with fiona.open(vectors, 'r') as src:
                    for feature in src:
                        yield feature

            features_iter = fiona_generator(vectors)
            strategy = 'fiona'
        except (AssertionError, IOError, OSError):
            # ... or a single string to be parsed as wkt/wkb/json
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
    elif isinstance(vectors, bytes):
        # wkb
        feat = parse_geo(vectors)
        features_iter = [feat]
        strategy = "single_geo"
    elif hasattr(vectors, '__geo_interface__'):
        geotype = vectors.__geo_interface__['type']
        if geotype.lower() == 'featurecollection':
            # ... a featurecollection
            features_iter = geo_records(vectors.__geo_interface__['features'])
            strategy = "geo_featurecollection"
        else:
            # ... or an single object
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
    elif isinstance(vectors, dict):
        # a python mapping
        if 'type' in vectors and vectors['type'] == 'FeatureCollection':
            # a feature collection
            features_iter = geo_records([f for f in vectors['features']])
            strategy = "featurecollection"
        else:
            # a single feature
            feat = parse_geo(vectors)
            features_iter = [feat]
            strategy = "single_geo"
    else:
        # ... or an iterable of objects
        features_iter = geo_records(vectors)
        strategy = "iter_geo"

    return features_iter, strategy


def get_featurecollection(path):
    features, _ = get_features(path)
    fc = {'type': 'FeatureCollection', 'features': []}
    for feature in features:
        fc['features'].append(feature)
    return fc
