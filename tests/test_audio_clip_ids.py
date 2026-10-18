import re

from routes.audio_clips import _make_id


def test_clip_ids_are_server_generated_and_unique():
    ids = {_make_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{32}', value) for value in ids)
