export function createSessionId() {
    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);
    const suffix = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return `session_${Date.now()}_${suffix}`;
}
