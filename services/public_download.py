import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter


class _PinnedTLSAdapter(HTTPAdapter):
    def __init__(self, hostname):
        self.hostname = hostname
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs.update(assert_hostname=self.hostname, server_hostname=self.hostname)
        return super().init_poolmanager(connections, maxsize, block=block, **kwargs)


def _public_target(url, require_https=False, allowed_host_suffix=None):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or (require_https and parsed.scheme != 'https'):
        raise ValueError('Unsupported download protocol')
    hostname = parsed.hostname
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError('Invalid download authority')
    hostname = hostname.encode('idna').decode('ascii')
    if allowed_host_suffix and not hostname.endswith('.' + allowed_host_suffix):
        raise ValueError('Download host is not allowed')
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError('Download host did not resolve')
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError('Download host resolves to a non-public address')
    address = next((item[4][0] for item in addresses if item[0] == socket.AF_INET), addresses[0][4][0])
    authority = f'[{address}]' if ':' in address else address
    authority += f':{port}'
    pinned_url = urlunsplit((parsed.scheme, authority, parsed.path or '/', parsed.query, ''))
    host_header = f'[{hostname}]' if ':' in hostname else hostname
    if parsed.port:
        host_header += f':{port}'
    return pinned_url, hostname, host_header


def download_public(url, *, max_bytes, timeout=60, require_https=False, allowed_host_suffix=None):
    for _ in range(4):
        pinned_url, hostname, host_header = _public_target(url, require_https, allowed_host_suffix)
        with requests.Session() as session:
            session.trust_env = False
            if pinned_url.startswith('https:'):
                session.mount('https://', _PinnedTLSAdapter(hostname))
            with session.get(pinned_url, headers={'Host': host_header}, timeout=timeout,
                             stream=True, allow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get('Location')
                    if not location:
                        raise ValueError('Download redirect has no location')
                    url = urljoin(url, location)
                    continue
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError('Download did not return a complete resource')
                if int(response.headers.get('Content-Length', 0)) > max_bytes:
                    raise ValueError('Download exceeds size limit')
                chunks = []
                size = 0
                for chunk in response.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError('Download exceeds size limit')
                    chunks.append(chunk)
                if not size:
                    raise ValueError('Download returned an empty resource')
                return b''.join(chunks)
    raise ValueError('Too many download redirects')
