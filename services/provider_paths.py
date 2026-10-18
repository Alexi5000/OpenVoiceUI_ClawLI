import re
from urllib.parse import quote


def encode_provider_path(path: str) -> str:
    if not path.startswith('/') or path.startswith('//') or any(segment in {'.', '..'} for segment in path.split('/')) or '\\' in path or any(ord(char) < 32 or ord(char) == 127 for char in path):
        raise ValueError('Invalid provider path')
    encoded = '/'.join(quote(segment, safe='') for segment in path.split('/'))
    if not re.fullmatch(r'(?:[A-Za-z0-9_.~/-]|%[0-9A-F]{2})*', encoded):
        raise ValueError('Invalid encoded provider path')
    return encoded
