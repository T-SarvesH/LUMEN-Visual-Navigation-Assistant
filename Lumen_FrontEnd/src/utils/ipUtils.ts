import { NativeModules } from 'react-native';

/**
 * Automatically detects the IP address of the packager (PC) when running in development mode.
 * This is useful for connecting to backend services running on the same machine as the bundler.
 * 
 * @returns {string | null} The IP address of the PC, or null if not found.
 */
export const getPCIpAddress = (): string | null => {
    const scriptURL = NativeModules.SourceCode.scriptURL;
    if (!scriptURL) {
        return null;
    }

    // The scriptURL is typically in the format: http://192.168.x.x:8081/index.bundle?...
    const address = scriptURL.split('://')[1].split('/')[0];
    const ip = address.split(':')[0];

    return ip;
};

/**
 * Returns the WebSocket URL using the automatically detected IP.
 * Defaults to localhost if detection fails.
 */
export const getWebSocketUrl = (port: number = 8001, path: string = 'Lumen-ws'): string => {
    const ip = getPCIpAddress();
    const host = ip || '192.168.29.63'; // Fallback to last known good IP or localhost
    return `ws://${host}:${port}/${path}`;
};
