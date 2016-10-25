"""Contains a class that handles the session with bossa servers."""
import cStringIO
import hmac
import hashlib
import requests
import pandas as pd

from bs4 import BeautifulSoup
from pandas.tseries.offsets import BDay
from zipfile import ZipFile

from bossa_session import config
from bossa_session.wse_indexes import STOCKS_FILTER


DATA_URL_BASE = 'http://moja.nova.bossa.pl/notowania/wykresy/data/'


def filter_stock(stock_name):
    """Filter for stock symbol."""
    return STOCKS_FILTER[stock_name]


class BossaSession(object):

    """Class to handle a BOSSA stock session."""

    # TODO: quite urgent - handle session if it's disconnected
    OHLC_URL = DATA_URL_BASE + 'n.txt?'\
        'id={stock}&kat_id={kat}&timestamp={ts}&timeframe={tf}&'\
        'timestamp1={ts1}&timestamp2={ts2}'
    INTRA_URL = DATA_URL_BASE + 'n_int.txt?'\
        'id={stock}&kat_id={kat}&timestamp={ts}&timeframe={tf}'
    INTRA_HISTORIC_URL = "http://bossa.pl/pub/intraday/mstock/cgl//{stock}.zip"

    def __init__(self, userNIK=config.userNIK, userPIN=config.userPIN):
        """Initialize the bossa session for the class."""
        self.dataframe = pd.DataFrame(
            columns=['open', 'high', 'low', 'close', 'vol', 'oi']
        )
        self.session = requests.Session()

        login_soup = BeautifulSoup(
            self.session.get('https://www.bossa.pl/bossa/login').text,
            "html.parser"
        )
        LgnChallengeHex = login_soup.find(attrs={"name": "LgnChallengeHex"})['value']

        def hex2str(string):
            """Return string form a hex."""
            out = ''
            while len(string) > 0:
                out += chr(int(string[0:2], 16))
                string = string[2:]
            return out

        LgnChallengeStr = hex2str(LgnChallengeHex)

        LgnUsrHMACPIN = hmac.new(
            LgnChallengeStr, hashlib.sha1(userPIN + userNIK).digest(),
            hashlib.sha1
        ).hexdigest()

        login_data = {
            'LgnUsrNIK': userNIK,
            'LgnVASCO': '',
            'LgnUsrHMACPIN': LgnUsrHMACPIN,
            'LgnChallengeHex': LgnChallengeHex
        }

        self.session.post('https://www.bossa.pl/bossa/login', login_data)

        self.session.get('https://www.bossa.pl/bossa/desktop')
        self.session.get(
            'https://www.bossa.pl/bossa/changeaccount?DprID=0'
        )

    def __del__(self):
        """Logout the session."""
        self.session.get('https://www.bossa.pl/bossa/logout')
        self.session.close()

    def fetch_stock_data(self, url):
        """Method fetches a zipped file like object and return its content."""
        response = self.session.get(url)
        memory_zip = ZipFile(cStringIO.StringIO(response.content))
        return memory_zip.open(memory_zip.namelist()[0])

    def fetch_ohlc(self, stock_name, ts=None, ts1=None, ts2=None):
        """Request to fetch ohlc day based stock - to be implemented."""
        data = self.fetch_stock_data(self.OHLC_URL.format(
            stock=filter_stock(stock_name), kat='x',
            ts=ts.strftime('%Y-%m-%d_%H%M%S.000') if ts else '', tf='0',
            ts1=ts1.strftime('%Y-%m-%d_%H%M%S.000') if ts1 else '',
            ts2=ts2.strftime('%Y-%m-%d_%H%M%S.000') if ts2 else ''
        )).readlines()
        if len(data) == 1:
            return None
        dataframe = pd.read_csv(
            cStringIO.StringIO(''.join(data)), header=0, index_col='datetime',
            skip_blank_lines=True, parse_dates={'datetime': ['<DTYYYYMMDD>']},
            date_parser=lambda x: pd.datetime.strptime(x, '%Y%m%d')
        )
        dataframe.columns = [s.replace('<', '') for s in dataframe.columns]
        dataframe.columns = [s.replace('>', '') for s in dataframe.columns]
        dataframe.columns = [s.lower() for s in dataframe.columns]
        dataframe = dataframe.rename(columns={'vol': 'volume'})
        return dataframe

    def fetch_intraday(self, stock_name, ts=None):
        """Request to fetch intraday based stock."""
        data = self.fetch_stock_data(self.INTRA_URL.format(
            stock=filter_stock(stock_name), kat='x',
            ts=ts.strftime('%Y-%m-%d_%H%M%S.000') if ts else '', tf='0',
        ))
        dataframe = pd.read_csv(
            data, header=0, index_col='datetime', skip_blank_lines=True,
            parse_dates={'datetime': ['<DTYYYYMMDD>', '<TIME>']},
            date_parser=lambda x: pd.datetime.strptime(x, '%Y%m%d %H%M%S')
        )
        dataframe.columns = [s.replace('<', '') for s in dataframe.columns]
        dataframe.columns = [s.replace('>', '') for s in dataframe.columns]
        dataframe.columns = [s.lower() for s in dataframe.columns]
        return dataframe.rename(columns={'vol': 'volume'})

    def quick_fetch_intraday(self, stock_name):
        """Fetch only fresh (2 days) data."""
        return self.fetch_intraday(stock_name, ts=pd.datetime.today()-BDay(1))

    def fetch_historic_intraday(self, stock_name):
        """Fetch historic intraday."""
        if stock_name not in STOCKS_FILTER:
            raise ValueError
        response = self.session.get(self.INTRA_HISTORIC_URL.format(
            stock=stock_name
        ))
        memory_zip = ZipFile(cStringIO.StringIO(response.content))
        dataframe = pd.read_csv(
            memory_zip.open(memory_zip.namelist()[0]), skip_blank_lines=True,
            header=None, index_col='datetime', names=[
                'stock', '0', '<DTYYYYMMDD>', '<TIME>', 'open',
                'high', 'low', 'close', 'volume', 'oi'
            ], parse_dates={'datetime': ['<DTYYYYMMDD>', '<TIME>']},
            date_parser=lambda x: pd.datetime.strptime(x, '%Y%m%d %H%M%S')
        )
        del dataframe['stock']
        del dataframe['0']
        return dataframe

    def post_favorite_stocks(self, stocks):
        """
        Update the list of favorite stocks in bossa.
        
        CsrfKey=23aba1d2-b859-4684-9ff3-1b4cd4a66443
        CsrfKey=23aba1d2-b859-4684-9ff3-1b4cd4a66443
        codes=AGT:ASB:COG:CRM:GTN:GRI:GCN:ATT:ITG:KZS:KRU:KSG:MLK:POZ:SOL:SNS:VVD:WAS
        layout=customerRating
        page=1
        news_cat_id=429
        cl=przebieg
        zakladka=notowania_wlasne
        """
        if len(stocks) > 20:
            raise ValueError('maximum number of stocks was exceeded')
        post_data = {
            'codes': ':'.join([STOCKS_FILTER[stock] for stock in stocks])
        }

        self.session.post('http://moja.nova.bossa.pl/index.jsp?layout=customerRating&page=1&cl=przebieg&zakladka=notowania_wlasne', post_data)

# Some very ugly comments below, with links and ideas:

# TODO convert to a class' method to handle business days only
# make PR to pandas with polish holiday calendar support

# TODO bossa orders
# BOSSA CANCEL ORDER: https://www.bossa.pl/bossa/cancelorder?OrdID=487206748
# PRZELICZ: https://www.bossa.pl/bossa/commissionnew?SecID=181&MrkID=0&OrdQty=1258&OrdLimit=3.55&OrdSide=K&OrdLimitType=L&OrdDateFrom=31.10.2016&OrdDateTo=31.10.2016&OrdDateType=S&OrdDisQty=&OrdMinQty=&OrdActLimit=&OrdType=0&OrdCurrency=PLN
# BOSSA ORDER: POST https://www.bossa.pl/bossa/ordernew HTTP/1.1
# FORM DATA: ReqNo=2883075270&OrdBasket=N&ReqID=0&AllSec=true&OrdSource=1&OrdMarketID=0&isUTP=T&OrdType=0&RFromAdm=&OrdNo=&FormID=M1&Portfolio=&OrdQuotation=3.95&OrdSecID=181&OrdSide=K&OrdQty=1258&OrdLimit=3.55&OrdLimitType=L&OrdLimitUI=L&OrdDateType=S&OrdActLimit=&OrdDisQty=&OrdMinQty=&OrdSessionDate=31.10.2016&OrdCurrency=PLN&SecSubAcc110=0&OrdGrossValue=4+465.90&OrdCommission=16.97&OrdNetValue=4+482.87&SecSubAccSCZS=0.0&SecSubAccRPT=&SecSubAccRPTV=&Funds=5+830.87&SecSubAccSCZB=0.0&SecSubAcc110A=1258&SecSubAccSCZC=3.56

# ACTIVE ORDERS: GET /bossa/activeorders
# BOSSA CANCEL: https://www.bossa.pl/bossa/cancelorder?OrdID=487206777

if __name__ == "__main__":
    bossa_session = BossaSession()
    df = bossa_session.fetch_intraday('KGHM', ts=pd.datetime.today()-BDay(5))
    bossa_session.post_favorite_stocks(['KGHM', 'MONNARI'])
