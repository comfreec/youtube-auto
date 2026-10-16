const MODEL = "@cf/black-forest-labs/flux-1-schnell";

function json(data, status = 200) {
  return Response.json(data, {
    status,
    headers: { "cache-control": "no-store", "access-control-allow-origin": "*" },
  });
}

async function verifyLicense(licenseKey, hardwareId, env) {
  if (!licenseKey || hardwareId.length < 32) return { ok: false, status: 400, reason: "missing_headers" };
  const response = await env.LICENSE.fetch("https://license.internal/api/v1/licenses/verify", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ license_key: licenseKey, hardware_id: hardwareId }),
  });
  if (!response.ok) return { ok: false, status: response.status, reason: "license_server_rejected" };
  const result = await response.json();
  return { ok: Boolean(result.valid || result.certificate), status: response.status, reason: "invalid_response" };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, model: MODEL });
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "content-type",
      }});
    }
    if (request.method !== "POST" || url.pathname !== "/generate") {
      return json({ detail: "Not Found" }, 404);
    }
    let body;
    try {
      body = await request.json();
    } catch {
      return json({ detail: "잘못된 요청입니다." }, 400);
    }
    const license = await verifyLicense(String(body.license_key || ""), String(body.hardware_id || ""), env);
    if (!license.ok) {
      return json({ detail: "유효한 라이선스가 필요합니다." }, 403);
    }
    const prompt = String(body.prompt || "").trim().slice(0, 2000);
    if (!prompt) return json({ detail: "이미지 설명이 필요합니다." }, 400);
    try {
      const result = await env.AI.run(MODEL, {
        prompt,
        steps: 4,
      });
      if (!result?.image) return json({ detail: "이미지를 생성하지 못했습니다." }, 502);
      return json({ image: result.image, format: "jpeg" });
    } catch (error) {
      const message = String(error?.message || error);
      const quota = /quota|limit|neuron|exceed/i.test(message);
      return json({ detail: quota ? "오늘의 무료 이미지 한도를 모두 사용했습니다." : "이미지 생성 서비스 오류" }, quota ? 429 : 502);
    }
  },
};
