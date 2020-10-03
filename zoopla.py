from bs4 import BeautifulSoup
import datetime
import html
import re
import requests

import map, postcode


def fetch_details(url, area=None):
    r = requests.get(url)
    if r.status_code != 200:
        raise Error('couldn\'t load details url ' + url)

    detailSoup = BeautifulSoup(r.text, 'html.parser')

    details = {}

    details['address'] = detailSoup.find(class_='ui-property-summary__address').text.strip()

    history = detailSoup.find('div', class_='dp-price-history__item')
    #for history in detailSoup.find_all('div', class_='dp-price-history__item'):
    #    if 'first listed' == history.find(class_='dp-price-history__item-detail').text.strip().lower():
    firstlisted = history.find(class_='dp-price-history__item-date').text.strip()
    firstlisted = firstlisted.replace('st ',' ').replace('nd ',' ').replace('rd ',' ').replace('th ',' ')
    details['firstlisted'] = datetime.datetime.strptime(firstlisted, '%d %b %Y').isoformat()

    # grab the long-lat
    mapTag = detailSoup.find('img', class_='ui-static-map__img')
    if mapTag:
        mapSrc = mapTag.attrs['data-src']
        args = html.unescape(mapSrc)
        details['longlat'] = args.split('center=')[1].split('&')[0]
        
        if area is not None:
            if not map.is_latlong_inside_path(area, details['longlat']):
                details['outsideArea'] = True
                return details
    else:
        print('...unable to find longlat from', url)

    speedTag = detailSoup.find('article', class_='dp-broadband-speed')
    if speedTag:
        # broadband details
        details['speedClass'] = speedTag.find(class_='dp-broadband-speed__title').text.strip()
        speedText = speedTag.text
        
        speedSource = 'unknown'
        m = re.match(r'.*?([0-9.]+)\s*[kmbps]+', speedText, re.DOTALL|re.IGNORECASE)
        if m:
            details['maxSpeed'] = float(m.group(1))
        m = re.match(r'.*source:\s*([a-zA-Z0-9-_.,]+).*', speedText, re.DOTALL|re.IGNORECASE)
        if m:
            details['source'] = m.group(1)

    elif 'longlat' in details:
        print('--> engaging broadband speed wangler....')
        details['postcode'] = postcode.get_from_longlat(details['longlat'])
        if details['postcode']:
            details['maxSpeed'] = postcode.get_predicted_broadband_speed(details['postcode'])
            if details['maxSpeed'] is None or details['maxSpeed'] < 0:
                del details['maxSpeed']
                print('   ...wangletron failure T_T', url)
            else:
                details['source'] = 'bb-speed-wangler'
                print('    ...wangle complete:', details['maxSpeed'])
    
    else:
        print('unable to find broadband data for',url)

    return details



max_pagenum = -1

def get_one_page(urlstem, pagenum, area, existing):
    url = urlstem + '&page_size=100'
    if pagenum != 1:
        url += '&pn=%d' % pagenum

    res = requests.get(url)
    if res.status_code != 200:
        raise Exception('zoopla said no')

    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    # find the mage count if we haven't yet
    if pagenum == 1:
        global max_pagenum
        for page in soup.find('div', class_='paginate').find_all('a'):
            if page.text.strip().isdigit():
                pn = int(page.text.strip())
                max_pagenum = max(pn, max_pagenum)
        
        
    print('scanning page', pagenum, '/', max_pagenum, 'of listings...')

    properties = []
    newproperties = []
    for listing_results in soup.find_all('ul', class_='listing-results'):
        for listing in listing_results.find_all('li'):

            if 'data-listing-id' not in listing.attrs:
                continue

            id = 'Z' + listing.attrs['data-listing-id']
            if id in existing:
                properties.append(existing[id])
                continue

            description = 'missing description'
            for attr in listing.find_all('h2'):
                description = attr.text.replace('Just added', '').strip().lower()
                break

            if 'terrace' in description or 'flat' in description or 'semi-detached' in description:
                # fuck that shit
                print('skipping "'+description+'" cos its too close to people...')
                properties.append(dict(id=id, skipped=True, reason='people'))  
                continue
            if 'plot ' in description or 'land ' in description:
                print('skipping "'+description+'" cos its not built...')
                properties.append(dict(id=id, skipped=True, reason='unbuilt'))
                continue

            price = listing.find(class_='listing-results-price').text.strip()

            thumbTag = listing.find('a', class_='photo-hover').find('img')
            thumbUrl = thumbTag.attrs['data-src']

            blurb = ''
            for p in listing.find(class_='listing-results-right').find('p'):
                if blurb != '':
                    blurb += '\n\n'
                blurb += p.strip()

            rooms = ''
            def add_rooms(rooms, roomtype):
                tag = listing.find('span', class_='num-%s'%roomtype)
                if tag:
                    if rooms != '':
                        rooms += ', '
                    rooms += tag.attrs['title'].strip()
                return rooms
            rooms = add_rooms(rooms, 'beds')
            rooms = add_rooms(rooms, 'baths')
            rooms = add_rooms(rooms, 'reception')

            address = listing.find(class_='listing-results-address').text.strip()

            detailsUrl = None
            for a in listing.find_all('a', class_='listing-results-price'):
                detailsUrl = a['href']
                if 'http' not in detailsUrl:
                    detailsUrl = 'https://zoopla.co.uk' + detailsUrl
                break

            details = '--missing details--'
            if detailsUrl is not None:
                details = fetch_details(detailsUrl, area)
                if 'outsideArea' in details:
                    print('skipping "'+address+'" @ ' + detailsUrl + ' because it\'s outside the search area')
                    properties.append(dict(id=id, skipped=True, reason='location'))
                    continue                       
                if 'maxSpeed' in details and details['maxSpeed'] < 50:
                    print('skipping "'+description+'" @ ' + detailsUrl + ' because its internets are too slow:',details['maxSpeed'])
                    properties.append(dict(id=id, skipped=True, reason='internet'))
                    continue
            
            print(description, address, id)
            prop = dict(
                id=id,
                description=description,
                price=price,
                url=detailsUrl, 
                rooms=rooms,
                blurb=blurb, 
                thumb=thumbUrl, 
                details=details)
            properties.append(prop)
            newproperties.append(prop)

    return properties,newproperties


def get_all_properties(url, area=None, existing={}):
    global max_pagenum
    max_pagenum = -1
    properties,newproperties = get_one_page(url, 1, area, existing)
    for pn in range(2, max_pagenum+1):
        all,new = get_one_page(url, pn, area, existing)
        properties += all
        newproperties += new

    return properties,newproperties


if __name__ == '__main__':
    ZPL_TRURO_20MILES = r'https://www.zoopla.co.uk/for-sale/property/truro/?beds_min=3&is_auction=false&is_retirement_home=false&is_shared_ownership=false&new_homes=exclude&price_max=650000&price_min=450000&q=Truro%2C%20Cornwall&radius=20&results_sort=newest_listings&search_source=home'
    properties = get_all_properties(ZPL_TRURO_20MILES, {})
    with open('truro20mi_zpl.json', 'wt') as outJson:
        json.dump(properties, outJson, sort_keys=True, indent=2)
