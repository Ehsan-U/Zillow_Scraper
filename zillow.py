import traceback
import requests
import json
from urllib.parse import urlparse,unquote,urlencode
import coloredlogs, logging



class Zillow_Request():
    logger = logging.getLogger(__name__)
    coloredlogs.install(level='INFO')

    def __init__(self):
        self.page_no = 1
        self.total_pages = [1, True]
        self.writer = open("output.json", 'w')
        self.DEFAULT_REQUEST_HEADERS = {
            'content-type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'host': 'www.zillow.com',
        }


    def start_requests(self):
        if self.filter_applied:
            query = json.loads(urlparse(self.url).query.split('=')[-1])
        else:
            query = {"pagination":{},"usersSearchTerm":self.location,"mapBounds":{"west":-80.878683078125,"east":-70.661397921875,"south":39.462558004831635,"north":45.944334224366145},"regionSelection":[{"regionId":43,"regionType":2}],"isMapVisible":True,"filterState":{"sortSelection":{"value":"globalrelevanceex"},"isAllHomes":{"value":True}},"isListVisible":True,"mapZoom":7}
        query['pagination'] = {"currentPage": self.page_no}
        url = 'https://www.zillow.com/search/GetSearchPageState.htm?searchQueryState=' + json.dumps(query) + '&wants={"cat1":["listResults","mapResults"],"cat2":["total"]}'
        resp = requests.get(url, headers=self.DEFAULT_REQUEST_HEADERS)
        return resp.json()


    def parse(self, response):
        if self.total_pages[-1]:
            self.total_pages[-1] = False
            self.total_pages[0] = response.get("cat1").get("searchList").get("totalPages")
        for property_ in response.get("cat1").get("searchResults").get("listResults"):
            zpid = property_.get("zpid")
            url, payload = self.propertyRequest(zpid)
            resp = requests.post(url, headers=self.DEFAULT_REQUEST_HEADERS, data=payload).json()
            price = resp.get('data').get("property").get('price')
            address = resp.get('data').get("property").get('streetAddress') + " " + resp.get('data').get("property").get('zipcode')
            zestimate = resp.get('data').get('property').get('adTargets').get("zestimate")
            bedrooms = resp.get('data').get('property').get("bedrooms")
            bathrooms = resp.get('data').get('property').get("bathrooms")
            sqft = resp.get('data').get('property').get("adTargets").get("sqft")
            item = {
                "price": price,
                "address": address,
                "zestimate": zestimate,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft": sqft,
            }
            for fact, value in resp.get("data").get('property').get('resoFacts').items():
                if value:
                    if type(value) == list:
                        # list of str
                        if type(value[0]) == str:
                            item[fact] = ",".join(value)
                        # list of dicts
                        elif type(value[0]) == dict:
                            for i in value:
                                for k, v in i.items():
                                    item[k] = v
                    else:
                        # str
                        item[fact] = value
            item = self.clean(item)
            self.logger.info(f" [+] Property: {item}")
            json.dump(item, self.writer)


    def propertyRequest(self, zpid):
        url_params = {
            'zpid': zpid,
            'contactFormRenderParameter': '',
            'queryId': "ec83b29cbe0161f7fc021a076bd24727",
            'operationName': "ForSaleShopperPlatformFullRenderQuery",
        }
        url = 'https://www.zillow.com/graphql/?' + urlencode(url_params)
        payload = json.dumps({
            "operationName": "ForSaleShopperPlatformFullRenderQuery",
            "variables": {
                "zpid": zpid,
                "contactFormRenderParameter": {
                    "zpid": zpid,
                    "platform": "desktop",
                    "isDoubleScroll": True
                }
            },
            "clientVersion": "home-details/6.1.1967.master.98656d8",
            "queryId": "ec83b29cbe0161f7fc021a076bd24727"
        })
        return url, payload


    def spider_opened(self):
        with open("config.json", 'r') as f:
            data = json.load(f)
            self.url = unquote(data.get("url").strip('\n'))
            self.location = data.get("location")
            if "searchQueryState" in self.url:
                self.filter_applied = True
            else:
                self.filter_applied = False


    def clean(self, item):
        return {k:v for k,v in item.items() if v and v != 'UNKNOWN'}


    def main(self):
        self.spider_opened()
        while self.page_no <= self.total_pages[0]:
            response = self.start_requests()
            try:
                self.parse(response)
                self.logger.info(f" [+] Page: {self.page_no}")
            except Exception:
                traceback.print_exc()
            finally:
                self.page_no +=1
        self.writer.close()



r = Zillow_Request()
r.main()
