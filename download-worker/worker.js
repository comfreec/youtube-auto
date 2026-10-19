const DOWNLOAD_URL =
  "https://github.com/comfreec/youtube-auto/releases/download/v2.1/AI-Shorts-Generator-v2.1.zip";
const RELEASE_URL = "https://github.com/comfreec/youtube-auto/releases/latest";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({ ok: true, version: "v2.1" }, {
        headers: { "cache-control": "no-store" },
      });
    }

    if (url.pathname === "/info") {
      return Response.redirect(RELEASE_URL, 302);
    }

    return Response.redirect(DOWNLOAD_URL, 302);
  },
};
