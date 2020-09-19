import json
import requests
from urllib.parse import quote


NEARBY_API_KEY = 'e7376801b0aad7'


def get_from_longlat(longlat):
    # http://api1.nearby.org.uk/api/convert.php?key=e7376801b0aad7&p=50.205878,-5.495793&want=postcode-uk&output=text
    # => postcode,uk,TR26 2HD,Unit,0.0001,24.044662217733,north-northeast

    url = 'http://api1.nearby.org.uk/api/convert.php?key=%s&want=postcode-uk&output=text&p=%s' % (
            NEARBY_API_KEY, quote(longlat))

    res = requests.get(url)
    if res.status_code != 200:
        print('WARNING: longlat->postcode lookup failed for', url)
        return None

    if not res.text.startswith('postcode,uk,'):
        raise Error('didn\'t understand what nearby.org.uk said: "%s"' % res.text)

    return res.text.split(',')[2]


def get_predicted_broadband_speed(postcode):
    url = 'https://ofcomapi.samknows.com/fixed-line-coverage-pc?postcode=' + quote(postcode)
    
    res = requests.get(url)
    if res.status_code != 200:
        return None

    dom = json.loads(res.text)
    if 'code' in dom and dom['code'] == 'NO_DATA_FOUND':
        return None

    data = dom['data']
    max_down_speed = -1
    for service in ['adsl','sfbb','ufbb']:
        max_down_speed = max(data['max_%s_predicted_down'%service], max_down_speed)
        availability = data['%s_availability'%service]

    return max_down_speed



if __name__ == '__main__':
    pc = get_from_longlat('50.340505,-5.151169')
    mbps = get_predicted_broadband_speed(pc)
    print(mbps,'mbps @',pc)
