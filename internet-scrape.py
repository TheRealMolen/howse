import json, re
import map, zoopla, rightmove, report

ZOOPLA_QUERY = r'https://www.zoopla.co.uk/for-sale/property/truro/?beds_min=3&is_auction=false&is_retirement_home=false&is_shared_ownership=false&new_homes=exclude&price_max=650000&price_min=400000&q=Truro%2C%20Cornwall&radius=20&results_sort=newest_listings&search_source=home'
ZOOPLA_FILE = 'truroa30_zpl.json'
ZOOPLA_RECENT_FILE = 'truroa30_zpl_recent.json'

RTMOVE_QUERY = r'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=USERDEFINEDAREA%5E%7B"id"%3A6179886%7D&minBedrooms=3&maxPrice=650000&minPrice=400000&sortType=6&propertyTypes=bungalow%2Cdetached%2Cpark-home&includeSSTC=false&mustHave=parking&dontShow=newHome%2Cretirement%2CsharedOwnership&furnishTypes=&keywords='
RTMOVE_FILE = 'truroa30_rmv.json'
RTMOVE_RECENT_FILE = 'truroa30_rmv_recent.json'


# TODO: this can probably be scraped from RTMOVE_QUERY -- although might require login 
SEARCH_AREA_STATICMAP = r'https://maps.google.com/maps/api/staticmap?center=50.28529,-5.14618&size=75x75&path=color%3A0x000099FF%7Cweight%3A2%7Cfillcolor%3A0x00009977%7Cenc%3AubsqHniw%5D%7Ba%40nXi%5Eyc%40_xAobCke%40ouCwWq%7BBsdCj%60Bz%60%40ngDq%7DH_q%40qbFyxQixGalWwfBthFxtBxjPctMopFgl%40%7DyLe_HdpBdsCrkO%60yK%7CuIl%7EKn%7CAvxDpeO%7D%5DxhMnaFzfCaa%40d%7CDloBf_Jh%7DFydGdoGniWmk%40r_Mv%7BG%60oTvwG%7EEbbBow%40dpAslAt%5Ee%7CEkbEubEgRw_KynEkkT%7Cq%40imIveCwpL_uB%7BdF%7BbFcWkgB%7DnD%7DfAkyA&scale=1&client=gme-rightmove&sensor=false&channel=defineyourarea&signature=0QYImrMIcyP25wFIlE45QSIPWW0='
SEARCH_AREA = map.extract_path_from_staticmap(SEARCH_AREA_STATICMAP)


def load_json(infilename):
    with open(infilename, 'rt', encoding='utf-8') as inJson:
        return json.load(inJson)

def save_json(outfilename, data):
    with open(outfilename, 'wt', encoding='utf-8') as outJson:
        json.dump(data, outJson, sort_keys=True, indent=2)

def safe_load_json(infilename):
    try:
        return load_json(infilename)
    except FileNotFoundError:
        return []


def load_existing(infilename):
    "loads a file and returns a dict from id->details"
    existing = safe_load_json(infilename)
    return dict([(e['id'],e) for e in existing])



def refresh_data():
    # scrape zoopla... NB. need to pass search area into zoopla because we enforce that outside
    zplexisting = load_existing(ZOOPLA_FILE)
    zplproperties,zplnew = zoopla.get_all_properties(ZOOPLA_QUERY, SEARCH_AREA, zplexisting)
    save_json(ZOOPLA_FILE, zplproperties)
    save_json(ZOOPLA_RECENT_FILE, zplnew)

    # scrape rightmove...
    rmvexisting = load_existing(RTMOVE_FILE)
    rmvproperties,rmvnew = rightmove.get_all_properties(RTMOVE_QUERY,rmvexisting)
    save_json(RTMOVE_FILE, rmvproperties)
    save_json(RTMOVE_RECENT_FILE, rmvnew)
  


def get_prop_key(property):
    rawprice = re.search(r'£([0-9,]+)', property['price']).group(1).replace(',','')
    rawblurb = re.sub(r'\s', '', property['blurb'][:100]).lower()
    key = rawprice + '#' + rawblurb
    return key

def collapse_dupes(properties):
    prop_by_key = {}
    collapsed = []
    collapsedids = set()
    for prop in properties:
        if prop['id'][0] != 'R':
            continue
        if prop['id'] in collapsedids:
            continue
        key = get_prop_key(prop)
        prop_by_key[key] = prop
        collapsed.append(prop)
        collapsedids.add(prop['id'])

    for prop in properties:
        if prop['id'][0] == 'R':
            continue
        if prop['id'] in collapsedids:
            continue
        key = get_prop_key(prop)
        if key in prop_by_key:
            if 'dupes' not in prop_by_key[key]:
                prop_by_key[key]['dupes'] = [prop]
            else:
                prop_by_key[key]['dupes'].append(prop)
        
        else:
            collapsed.append(prop)
            collapsedids.add(prop['id'])

    return collapsed


def gen_report_from_json(infiles, desc, outfilename):
    properties = []
    for infile in infiles:
        props = load_json(infile)
        properties += [p for p in props if 'skipped' not in p]

    uniqproperties = collapse_dupes(properties)
    print('collapsed', len(properties) - len(uniqproperties), '/', len(properties), 'dupes')

    uniqproperties.sort(key=lambda p: p['details']['firstlisted'], reverse=True)
    
    html = report.gen_html(uniqproperties)
    
    print("Found a total of %d %s properties" % (len(uniqproperties),desc))
    with open(outfilename, 'wt', encoding='utf-8') as outFile:
        outFile.write(html)



def refresh_reports():
    gen_report_from_json([ZOOPLA_FILE, RTMOVE_FILE], 'all unsold', 'maybe-howses.html')
    gen_report_from_json([ZOOPLA_RECENT_FILE, RTMOVE_RECENT_FILE], 'new', 'maybe-howses-new.html')
    
            
refresh_data()
refresh_reports()
