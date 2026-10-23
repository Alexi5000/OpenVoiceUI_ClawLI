import logging

from routes import tools


def test_tool_audit_keeps_untrusted_values_on_one_record(caplog):
    hostile = 'normal\r\nFAKE-ADMIN\x00\x1b[31m\u2028\u2029'
    with caplog.at_level(logging.INFO, logger=tools.logger.name):
        tools._log_invocation(hostile, {'text': hostile}, profile=hostile, user_id=hostile, outcome='ok')
    message = caplog.records[-1].getMessage()
    assert message.startswith('tool-invoke tool=')
    assert 'FAKE-ADMIN' in message
    assert '\\r\\n' in message
    for control in ['\r', '\n', '\x00', '\x1b', '\u2028', '\u2029']:
        assert control not in message


def test_tool_audit_preserves_operation_context(caplog):
    with caplog.at_level(logging.INFO, logger=tools.logger.name):
        tools._log_invocation('search', {'query': 'hello'}, profile='default', user_id='alice', outcome='ok')
    message = caplog.records[-1].getMessage()
    for value in ['tool-invoke', 'search', 'hello', 'default', 'alice', 'ok']:
        assert value in message
