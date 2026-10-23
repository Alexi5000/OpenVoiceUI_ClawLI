export function serializeLogData(value) {
    const seen = new WeakSet();
    try {
        return JSON.stringify(value, (_key, item) => {
            if (typeof item === 'bigint') return String(item);
            if (item && typeof item === 'object') {
                if (seen.has(item)) return '[Circular]';
                seen.add(item);
            }
            return item;
        }).replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
    } catch {
        return '"[Unserializable log data]"';
    }
}
