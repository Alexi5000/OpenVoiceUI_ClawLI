import json
from html.parser import HTMLParser

import pytest
from flask import Flask

from routes.vault import _oauth_callback_html, vault_bp


class CallbackPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.message = []
        self.script = []
        self.in_message = False
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        self.in_message = self.in_message or attrs.get("id") == "oauth-message"
        self.in_script = tag == "script"

    def handle_endtag(self, tag):
        if tag == "p":
            self.in_message = False
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_message:
            self.message.append(data)
        if self.in_script:
            self.script.append(data)


MESSAGES = [
    "Connected successfully",
    "</script><img src=x onerror=window.injected=1>",
    "<!--<script>window.injected=1</script>-->",
    "'\" & < > \\ café 😀",
    "</p><svg onload=window.injected=1>",
    "\u2028\u2029",
    "line\rreturn\r\nnext\x00end",
]


@pytest.mark.parametrize("message", MESSAGES)
@pytest.mark.parametrize("success", [False, True])
def test_callback_keeps_message_as_text_and_out_of_script(message, success):
    html, status, headers = _oauth_callback_html(success, message)
    parsed = CallbackPage()
    parsed.feed(html)
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "".join(parsed.message) == message
    assert [tag for tag, _ in parsed.tags].count("script") == 1
    assert not any(tag in ("img", "svg") for tag, _ in parsed.tags)
    assert "JSON.parse(message.dataset.payload)" in "".join(parsed.script)
    message_element = next(attrs for _, attrs in parsed.tags if attrs.get("id") == "oauth-message")
    assert json.loads(message_element["data-payload"]) == {
        "type": "oauth_callback", "status": "success" if success else "error", "message": message
    }


@pytest.mark.parametrize("message", MESSAGES)
def test_public_error_callback_renders_provider_error_as_text(message):
    app = Flask(__name__)
    app.register_blueprint(vault_bp)
    response = app.test_client().get("/api/vault/oauth/callback/google", query_string={"error": message})
    assert response.status_code == 200
    parsed = CallbackPage()
    parsed.feed(response.get_data(as_text=True))
    assert "".join(parsed.message) == "OAuth error: " + message
    assert not any(tag in ("img", "svg") for tag, _ in parsed.tags)
