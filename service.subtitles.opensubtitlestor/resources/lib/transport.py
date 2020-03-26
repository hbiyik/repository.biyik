from tinyxbmc import net


import requests
import xmlrpclib


class RequestsTransport(xmlrpclib.Transport):
    user_agent = "Python XMLRPC with Requests (python-requests.org)"
    use_https = True

    def request(self, host, handler, request_body, verbose):
        url = self._build_url(host, handler)
        try:
            headers = {"X-Requested-With": "XMLHttpRequest"}
            resp = net.http(url, timeout=20, data=request_body, headers=headers, method="POST", text=False)
        except ValueError:
            raise
        except Exception:
            raise
        else:
            try:
                resp.raise_for_status()
            except requests.RequestException as e:
                raise xmlrpclib.ProtocolError(url, resp.status_code,
                                              str(e), resp.headers)
            else:
                return self.parse_response(resp)

    def parse_response(self, resp):
        p, u = self.getparser()
        p.feed(resp.content)
        p.close()
        return u.close()

    def _build_url(self, host, handler):
        scheme = 'https' if self.use_https else 'http'
        return '%s://%s%s' % (scheme, host, handler)
