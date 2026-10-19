export function createMusicEmbed(document, provider, embedUrl, fallbackUrl) {
    let parsed;
    try { parsed = new URL(embedUrl); } catch {}
    const trusted = parsed && parsed.protocol === 'https:' && !parsed.username && !parsed.password &&
        ((provider === 'soundcloud' && parsed.hostname === 'w.soundcloud.com' && parsed.pathname === '/player/') ||
         (provider === 'bandcamp' && parsed.hostname === 'bandcamp.com' && parsed.pathname.startsWith('/EmbeddedPlayer/')));
    if (trusted) {
        const iframe = document.createElement('iframe');
        iframe.src = parsed.href;
        iframe.style.border = '0';
        iframe.style.width = '100%';
        iframe.style.height = provider === 'soundcloud' ? '166px' : '120px';
        iframe.title = provider === 'soundcloud' ? 'SoundCloud player' : 'Bandcamp player';
        iframe.setAttribute('allow', 'autoplay');
        iframe.setAttribute('scrolling', 'no');
        return iframe;
    }
    try {
        const url = new URL(fallbackUrl);
        if (provider !== 'bandcamp' || url.protocol !== 'https:' || url.username || url.password ||
            !(url.hostname === 'bandcamp.com' || url.hostname.endsWith('.bandcamp.com'))) return null;
        const link = document.createElement('a');
        link.href = url.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Open on Bandcamp';
        link.style.color = '#3b82f6';
        return link;
    } catch { return null; }
}
