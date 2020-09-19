import json

import json
import zoopla, rightmove, report

ZOOPLA_QUERY = r'https://www.zoopla.co.uk/for-sale/property/truro/?beds_min=3&is_auction=false&is_retirement_home=false&is_shared_ownership=false&new_homes=exclude&price_max=650000&price_min=400000&q=Truro%2C%20Cornwall&radius=20&results_sort=newest_listings&search_source=home'
ZOOPLA_FILE = 'truro20mi_zpl.json'
ZOOPLA_RECENT_FILE = 'truro20mi_zpl_recent.json'

RTMOVE_QUERY = r'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E1365&minBedrooms=3&maxPrice=650000&minPrice=400000&radius=20.0&sortType=6&propertyTypes=bungalow%2Cdetached%2Cpark-home&includeSSTC=false&mustHave=parking&dontShow=newHome%2Cretirement%2CsharedOwnership&furnishTypes=&keywords='
RTMOVE_FILE = 'truro20mi_rmv.json'
RTMOVE_RECENT_FILE = 'truro20mi_rmv_recent.json'


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
    errors = ''

    # scrape zoopla...
    zplexisting = load_existing(ZOOPLA_FILE)
    zplproperties,zplnew = zoopla.get_all_properties(ZOOPLA_QUERY,zplexisting)
    save_json(ZOOPLA_FILE, zplproperties)
    save_json(ZOOPLA_RECENT_FILE, zplnew)
 
    # scrape rightmove...
    rmvexisting = load_existing(RTMOVE_FILE)
    rmvproperties,rmvnew = rightmove.get_all_properties(RTMOVE_QUERY,rmvexisting)
    save_json(RTMOVE_FILE, rmvproperties)
    save_json(RTMOVE_RECENT_FILE, rmvnew)
  

def gen_report_from_json(infiles, desc, outfilename):
    properties = []
    for infile in infiles:
        props = load_json(infile)
        properties += [p for p in props if 'skipped' not in p]

    properties.sort(key=lambda p: p['details']['firstlisted'], reverse=True)
    
    html = report.gen_html(properties)
    
    print("Found a total of %d %s properties" % (len(properties),desc))
    with open(outfilename, 'wt', encoding='utf-8') as outFile:
        outFile.write(html)



def refresh_reports():
    gen_report_from_json([ZOOPLA_FILE, RTMOVE_FILE], 'all unsold', 'maybe-howses.html')
    gen_report_from_json([ZOOPLA_RECENT_FILE, RTMOVE_RECENT_FILE], 'new', 'maybe-howses-new.html')
    
            
refresh_data()
refresh_reports()
