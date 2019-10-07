export const IPHONE5_VIEWPORT_MIN = 320;

export const IPHONE6_VIEWPORT_MIN = 375;

export const IPHONE6S_VIEWPORT_MIN = 414;

export const LANDSCAPE_VIEWPORT_MIN = 576;

export const TABLET_VIEWPORT_MIN = 768;

export const DESKTOP_VIEWPORT_MIN = 992;

export const LARGE_DESKTOP_VIEWPORT_MIN = 1260;

export const mobileMediaQuery = `(max-width: ${LANDSCAPE_VIEWPORT_MIN - 1}px)`;

export const landscapeOnlyMediaQuery = `(min-width: ${LANDSCAPE_VIEWPORT_MIN}px) and (max-width: ${LANDSCAPE_VIEWPORT_MIN - 1}px)`;

export const tabletMinMediaQuery = `(min-width: ${TABLET_VIEWPORT_MIN}px)`;

export const tabletOnlyMediaQuery = `(min-width: ${TABLET_VIEWPORT_MIN}px) and (max-width: ${DESKTOP_VIEWPORT_MIN - 1}px)`;

export const tabletMaxMediaQuery = `(max-width: ${DESKTOP_VIEWPORT_MIN - 1}px)`;

export const desktopMediaQuery = `(min-width: ${DESKTOP_VIEWPORT_MIN}px)`;
