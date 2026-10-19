import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createMusicEmbed } from '../../src/security/music-embed.mjs';
const document = { createElement(tag) { return { tag, style: {}, attributes: {}, setAttribute(k,v) { this.attributes[k] = v; } }; } };
test('preserves supported players and sizes', () => {
    for (const [provider, url, height] of [['soundcloud','https://w.soundcloud.com/player/?url=track&auto_play=true','166px'], ['bandcamp','https://bandcamp.com/EmbeddedPlayer/track=123/','120px']]) {
        const frame = createMusicEmbed(document,provider,url);
        assert.equal(frame.tag,'iframe'); assert.equal(frame.src,url); assert.equal(frame.style.height,height);
    }
});
test('rejects script schemes, markup, credentials and lookalike hosts', () => {
    for (const url of ['javascript:alert(1)','data:text/html,<script>alert(1)</script>','<img src=x onerror=alert(1)>','https://w.soundcloud.com.evil.test/player/','https://user@w.soundcloud.com/player/','https://bandcamp.com/not-a-player']) {
        assert.equal(createMusicEmbed(document,'soundcloud',url),null);
    }
});
test('fallback uses safe text and only bandcamp HTTPS destinations', () => {
    const link=createMusicEmbed(document,'bandcamp',null,'https://artist.bandcamp.com/album/song');
    assert.equal(link.tag,'a'); assert.equal(link.textContent,'Open on Bandcamp'); assert.equal(link.rel,'noopener noreferrer');
    for (const url of ['javascript:alert(1)','https://bandcamp.com.evil.test/','https://x@bandcamp.com/']) assert.equal(createMusicEmbed(document,'bandcamp',null,url),null);
});
