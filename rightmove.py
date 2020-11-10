from bs4 import BeautifulSoup
import datetime
import html
import json
import re
import requests
import urllib

import postcode

def fetch_legacy_details(detailSoup):
    details = {}

    details['address'] = detailSoup.find(class_='property-header-bedroom-and-price').find('address').text.strip()
    
    firstlistedtag = detailSoup.find(id='firstListedDateValue')
    if firstlistedtag:
        firstlisted = firstlistedtag.text.strip()
        details['firstlisted'] = datetime.datetime.strptime(firstlisted, '%d %B %Y').isoformat()
    elif 'listingUpdate' in dom and 'listingUpdateDate' in dom['listingUpdate']:
        details['firstlisted'] = dom['listingUpdate']['listingUpdateDate'].replace('Z','')
    elif 'firstVisibleDate' in dom:
        details['firstlisted'] = dom['firstVisibleDate'].replace('Z','')
    else:
        raise Exception('unable to find listing date for "%s"'%url)
    
    # grab the long-lat
    mapTag = detailSoup.find('a', class_='js-ga-minimap').find('img')
    if mapTag:
        mapSrc = mapTag.attrs['src']
        mapArgs = urllib.parse.parse_qs(mapSrc.split('?')[1])
        details['longlat'] = mapArgs['latitude'][0] + ',' + mapArgs['longitude'][0]
    else:
        print('...unable to find longlat from', url)

    # grab the postcode
    for script in detailSoup.find_all('script'):
        if not script.string or '"location":{' not in script.string:
            continue
        m = re.search(r"\"postcode\"\s*:\s*\"([a-zA-Z0-9 ]*)\"", script.string, re.DOTALL)
        if m:
            details['postcode'] = m.group(1).strip()
        else:
            print('couldnt find postcode for', url)
        break

    return details


def fetch_details(url, dom):
    r = requests.get(url)
    if r.status_code != 200:
        raise Error('couldn\'t load details url ' + url)

    detailSoup = BeautifulSoup(r.text, 'html.parser')

    details = {}

    for script in detailSoup.find_all('script'):
        if not script.string:
            continue
        rawJs = script.string.strip()
        if not rawJs.startswith('window.PAGE_MODEL = '):
            continue

        jsonModel = rawJs[20:]
        pageModel = json.loads(jsonModel)
        propDom = pageModel['propertyData']
        
        details['address'] = propDom['address']['displayAddress']
        
        firstlisted = propDom['listingHistory']['listingUpdateReason'].split(' ')[-1]
        if firstlisted.lower() == 'today':
            details['firstlisted'] = datetime.datetime.today().isoformat()
        elif firstlisted.lower() == 'yesterday':
            details['firstlisted'] = (datetime.datetime.today() - datetime.timedelta(days=1)).isoformat()
        else:
            details['firstlisted'] = datetime.datetime.strptime(firstlisted, '%d/%m/%Y').isoformat()
        details['firstlisted'] = details['firstlisted'].split('.')[0]

        details['longlat'] = '%f,%f' % (propDom['location']['latitude'], propDom['location']['longitude'])

        details['postcode'] = pageModel['analyticsInfo']['analyticsProperty']['postcode']
        break

    if 'address' not in details:
        details = fetch_legacy_details(detailSoup)

    # go look up the bb speed
    if 'postcode' in details:
        details['maxSpeed'] = postcode.get_predicted_broadband_speed(details['postcode'])
        if details['maxSpeed'] is None or details['maxSpeed'] < 0:
            del details['maxSpeed']

    return details


NUM_LISTINGS_PER_PAGE = 24   # seems to be hardcoded?
max_pagenum = -1

def get_one_page(url, pagenum, existing):
    offset = ((pagenum-1)*NUM_LISTINGS_PER_PAGE)
    url = url.replace('&propertyTypes=', '&index=%d&propertyTypes=' % offset)

    res = requests.get(url)
    if res.status_code != 200:
        raise Exception('rightmove said no')

    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    for script in soup.find_all('script'):
        if not script.string.startswith('window.jsonModel = '):
            continue
        jsonModel = script.string[19:]
        pageModel = json.loads(jsonModel)
        if pageModel['bot']:
            print('***** WARNING: rightmove thinks this is a bot *****')

        # find the page count if we haven't yet
        if pagenum == 1:
            global max_pagenum
            max_pagenum = int(pageModel['pagination']['total'])
        break
        
    print('scanning page', pagenum, '/', max_pagenum, 'of listings - offset', offset, '...')

    properties = []
    newproperties = []
    for listing in pageModel['properties']:
        id = 'R' + str(listing['id'])
        if id in existing:
            properties.append(existing[id])
            continue

        description = listing['propertyTypeFullDescription'].lower()
        
        if 'terrace' in description or 'flat' in description or 'semi-detached' in description:
            # fuck that shit
            print('skipping "'+description+'" cos its too close to people...')
            properties.append(dict(id=id, skipped=True, reason='people'))
            continue
        if 'plot ' in description or 'land ' in description:
            print('skipping "'+description+'" cos its not built...')
            properties.append(dict(id=id, skipped=True, reason='unbuilt'))
            continue

        displayPrice = listing['price']['displayPrices'][0]
        price = displayPrice['displayPrice']
        if 'displayPriceQualifier' in displayPrice:
            price += ' ' + displayPrice['displayPriceQualifier']

        thumbUrl = listing['propertyImages']['images'][0]['srcUrl']

        blurb = listing['summary'].capitalize()

        address = listing['displayAddress']

        detailsUrl = listing['propertyUrl']
        if 'http' not in detailsUrl:
            detailsUrl = 'https://www.rightmove.co.uk' + detailsUrl

        details = '--missing details--'
        if detailsUrl is not None:
            details = fetch_details(detailsUrl, listing)
            if 'maxSpeed' in details and details['maxSpeed'] < 50:
                print('skipping "'+description+'" @ ' + detailsUrl + ' because its internets are too slow:',details['maxSpeed'])
                properties.append(dict(id=id, skipped=True, reason='internet'))
                continue
        
        print(description, address, id)
        prop = dict(
            id=id,
            description=description,
            address=address,
            price=price,
            url=detailsUrl, 
            blurb=blurb, 
            thumb=thumbUrl, 
            details=details)
        properties.append(prop)
        newproperties.append(prop)

    return properties,newproperties



def get_all_properties(url, existing):
    global max_pagenum
    max_pagenum = -1
    properties,newproperties = get_one_page(url, 1, existing)
    for pn in range(2, max_pagenum+1):
        all,new = get_one_page(url, pn, existing)
        properties += all
        newproperties += new

    return properties,newproperties



if __name__ == '__main__':
    RMV_TRURO_20MILES = r'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E1365&minBedrooms=3&maxPrice=650000&minPrice=450000&radius=20.0&sortType=6&propertyTypes=bungalow%2Cdetached%2Cpark-home&includeSSTC=false&mustHave=parking&dontShow=newHome%2Cretirement%2CsharedOwnership&furnishTypes=&keywords='
    properties,newproperties = get_all_properties(RMV_TRURO_20MILES, {})

    # uniquify
    unique = []
    ids = set()
    for prop in properties:
        if prop['id'] not in ids:
            unique.append(prop)
            ids.add(prop['id'])

    properties = unique

    with open('truro20mi_rmv.json', 'wt') as outJson:
        json.dump(properties, outJson, sort_keys=True, indent=2)
