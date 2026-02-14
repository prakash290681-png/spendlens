/// <reference lib="webworker" />

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", () => {
  console.log("SpendLens service worker active");
});

self.addEventListener("fetch", () => {});
