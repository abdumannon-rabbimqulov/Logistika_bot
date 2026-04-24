const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

let accessTokenInMemory = null;
let refreshingPromise = null;

export function getAccessToken() {
  return accessTokenInMemory;
}

export function setAccessToken(token) {
  accessTokenInMemory = token;
}

export function getRefreshToken() {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token) {
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearSessionTokens() {
  accessTokenInMemory = null;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function persistAccessToken(token) {
  setAccessToken(token);
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function hydrateAccessToken() {
  const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    accessTokenInMemory = token;
  }
}

export function isRefreshing() {
  return refreshingPromise;
}

export function setRefreshing(promise) {
  refreshingPromise = promise;
}
