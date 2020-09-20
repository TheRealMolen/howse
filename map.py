import urllib.parse

import polyline
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def extract_path_from_staticmap(staticmap_url):
    "given a google maps static map with an encoded path, return the list of lat-long pairs"
    query = urllib.parse.urlparse(staticmap_url).query
    params = urllib.parse.parse_qs(query)
    if 'path' not in params:
        return []
    pathdef = params['path'][0]

    # search for an enc: block
    while pathdef != '' and not pathdef.startswith('enc:'):
        pathdef = pathdef.split('|',1)[1]

    points = polyline.decode(pathdef[4:])

    return Polygon(points)


def is_latlong_inside_path(path, latlong):
    if isinstance(latlong, str):
        latlong = [float(v.strip()) for v in latlong.split(',')]
    point = Point(latlong[0], latlong[1])
    return path.contains(point)



if __name__ == '__main__':
    url = r'https://maps.google.com/maps/api/staticmap?center=50.28508,-5.15066&size=75x75&path=color%3A0x000099FF%7Cweight%3A2%7Cfillcolor%3A0x00009977%7Cenc%3A%7BwgqHlue%5EsyDs%60EeoCoyCgjAgYaV%7B_BoWs%60D%7BeBkwBwWq%7BBsdCj%60Bz%60%40ngDq%7DH_q%40qbFyxQgjGlGctMopFgl%40%7DyLe_HdpBdsCrkO%60yK%7CuIl%7EKp%7CAvxDneOjtEhbI%7Br%40pjMloBf_Jh%7DFydGdoGniWmk%40r_Mv%7BG%60oTheIsrHeo%40alRynEmkT%7Cq%40imIoWcmN&scale=1&client=gme-rightmove&sensor=false&channel=defineyourarea&signature=wpPqpBSWAl3-biT6zh51NNv92no='
    path = extract_path_from_staticmap(url)
    print('path:',path)

    assert is_latlong_inside_path(path, [50.2664697,-5.050897])
    assert is_latlong_inside_path(path, '50.202959, -5.390047')
    assert not is_latlong_inside_path(path, [50.123106, -5.550078])
    assert not is_latlong_inside_path(path, [50.403919, -5.077714])
    print('All tests passed 👍')

