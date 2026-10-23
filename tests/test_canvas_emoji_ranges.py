from services import canvas_styles


def test_canvas_emoji_lint_keeps_supported_symbol_blocks(monkeypatch):
    monkeypatch.setattr(canvas_styles, 'get_active_style_id', lambda: None)
    for symbol in ['👋', '🇺🇸', '☀', '✂', '⬀', '⯿', '\ufe0f']:
        issues = canvas_styles.lint_page_html('<p>' + symbol + '</p>')
        assert any(issue.startswith('EMOJI-AS-UI:') for issue in issues)
    issues = canvas_styles.lint_page_html('<p>你好 日本語 한국어 café</p>')
    assert not any(issue.startswith('EMOJI-AS-UI:') for issue in issues)
