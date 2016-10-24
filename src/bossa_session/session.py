"""Contains a class that open a zip file in memory."""
from bs4 import BeautifulSoup
import cStringIO
import hmac
import hashlib
import requests
from zipfile import ZipFile
import pandas as pd
from etc import settings


DATA_URL_BASE = 'http://moja.nova.bossa.pl/notowania/wykresy/data/'


class BossaSession(object):

    """Class to handle a BOSSA stock session."""

    stock = 'FCL'

    OHLC_URL = DATA_URL_BASE + 'n.txt?'\
        'id={stock}&kat_id={kat}&timestamp={ts}&timeframe={tf}&'\
        'timestamp1={ts1}&timestamp2={ts2}'
    INTRA_URL = DATA_URL_BASE + 'n_int.txt?'\
        'id={stock}&kat_id={kat}&timestamp={ts}&timeframe={tf}'
    INTRA_HISTORIC_URL = "http://bossa.pl/pub/intraday/mstock/cgl//{stock}.zip"

    def __init__(self, userNIK, userPIN):
        """Initialize the bossa session for the class."""
        self.dataframe = pd.DataFrame(columns=['datetime', ' <OPEN>', '<HIGH>',
                                               '<LOW>', '<CLOSE>', '<VOL>',
                                               '<OI>'])

        self.session = requests.Session()
        LgnChallengeHex = BeautifulSoup(
            self.session.get('https://www.bossa.pl/bossa/login').text,
            "html.parser"
        ).find(attrs={"name": "LgnChallengeHex"})['value']

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

    def fetch_ohlc(self):
        """Some doc."""
        data = self.fetch_stock_data(self.OHLC_URL.format(
            stock='FCL', kat='x',
            ts='', tf='0',
            ts1='', ts2=''
        ))
        return data

    def fetch_intraday(self):
        """Some doc."""
        data = self.fetch_stock_data(self.INTRA_URL.format(
            stock=self.stock, kat='x',
            ts='', tf='0',
        ))
        self.dataframe = self.dataframe.append(
            pd.read_csv(
                data, header=0,
                parse_dates={'datetime': ['<DTYYYYMMDD>', '<TIME>']},
                date_parser=lambda x: pd.datetime.strptime(x, '%Y%m%d %H%M%S')
            )
        )
        # pandas approach:
        # parse = lambda x: datetime.strptime(x, '%Y%m%d %H%M%S')
        # pd.read_csv(bossa_session.fetch_intraday(),
        # parse_dates=[['DTYYYYMMDD', 'TIME']], header=1, index_col=[0],
        # date_parser=parse)
        # return data

    def fetch_historic_intraday(self):
        """Fetch historic intraday."""
        response = self.session.get(self.INTRA_HISTORIC_URL.format(
            stock=self.stock
        ))
        memory_zip = ZipFile(cStringIO.StringIO(response.content))
        self.dataframe = self.dataframe.append(
            pd.read_csv(
                memory_zip.open(memory_zip.namelist()[0]), header=0,
                parse_dates={'datetime': ['<DTYYYYMMDD>', '<TIME>']},
                date_parser=lambda x: pd.datetime.strptime(x, '%Y%m%d %H%M%S')
            )
        )


        # TODO convert to a class' method to handle business days only
        # from datetime import date, timedelta as td
        # d1 = date(2008,8,15)
        # d2 = date(2008,9,15)
        # delta = d2 - d1
        # for i in range(delta.days + 1):
        #    print d1 + td(days=i)

        # import pandas as pd
        # # BDay is business day, not birthday...
        # from pandas.tseries.offsets import BDay
        # # pd.datetime is an alias for datetime.datetime
        # today = pd.datetime.today()
        # print today - BDay(4)
if __name__ == "__main__":
    bossa_session = BossaSession(userNIK=settings.userNIK,
                                 userPIN=settings.userPIN)
    import pytest
    pytest.set_trace()
