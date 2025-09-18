'''
Created on Sep 18, 2025

@author: boogie
'''
from tinyxbmc import stubmod
import htmlement
import re
import binascii
import base64
import random
from tinyxbmc import net


class Proxy:
    def get(self, address, clean=True):
        pass

    def clean(self, page):
        return page


class Proxiyum(Proxy):
    domain = "proxyium.com"

    def get(self, address, clean=True):
        paddress = f"https://{self.domain}"
        xpage = htmlement.fromstring(net.http(paddress, cache=None))
        server = xpage.find(".//select/option").get("value")
        data = {"type": "",
                "proxy_country": server,
                "url": address}
        pru = f"https://cdn.{self.domain}/proxyrequest.php"
        hpage = net.http(pru,
                         method="POST",
                         data=data,
                         cache=None,
                         referer=paddress)
        href = re.search(r"atob\((?:\'|\")(.+?)(?:\'|\")\)", hpage).group(1)
        href = binascii.unhexlify(base64.b64decode(href.encode())).decode()
        href = re.search(r"href\s*?\=\s*?(?:\'|\")(.+?)(?:\'|\")", href).group(1)
        href_page = net.http(href, cache=None, referer=pru)
        last_u = re.search(r"data-r\s*?\=\s*?(?:\'|\")(.+?)(?:\'|\")", href_page).group(1)
        last_u = base64.b64decode(last_u.encode()).decode()
        last_page = net.http(last_u, referer=href, cache=None)
        return last_page if not clean else self.clean(last_page)

    def clean(self, page):
        page = re.sub(r"(<head.*?>)(<.+dummy\=.+?\/script>)", "\g<1>", page)
        return page


PROXIES = [Proxiyum]


def getrandom():
    return random.choice(PROXIES)
