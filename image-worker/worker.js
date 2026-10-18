const MODEL = "@cf/black-forest-labs/flux-1-schnell";

function json(data, status = 200) {
  return Response.json(data, {
    status,
    headers: { "cache-control": "no-store", "access-control-allow-origin": "*" },
  });
}

async function verifyLicense(licenseKey, hardwareId, env) {
  if (!licenseKey || hardwareId.length < 32) return { ok: false, status: 400, reason: "missing_headers" };
  const licenseServer = String(env.LICENSE_SERVER_URL || "https://ai-shorts-license.comfreec1.workers.dev").replace(/\/$/, "");
  const request = new Request(`${licenseServer}/api/v1/licenses/verify`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ license_key: licenseKey, hardware_id: hardwareId }),
  });
  // The seller's Worker can use a private service binding. Customer-owned
  // Workers use the same public HTTPS verification endpoint, so each customer
  // gets an independent Workers AI free allocation without receiving secrets.
  const response = env.LICENSE
    ? await env.LICENSE.fetch(request)
    : await fetch(request);
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
      // The current hosted schema accepts the prompt-only form. Optional
      // generation fields have changed between runtime versions, so let the
      // model choose its supported defaults.
      const result = await env.AI.run(MODEL, { prompt });
      if (!result?.image) return json({ detail: "이미지를 생성하지 못했습니다." }, 502);
      return json({ image: result.image, format: "jpeg" });
    } catch (error) {
      const message = String(error?.message || error);
      console.error("Workers AI image generation failed", message);
      const quota = /3036|daily free allocation|quota|neuron.{0,30}(limit|exceed|used)/i.test(message);
      const capacity = /3040|out of capacity|capacity temporarily|busy/i.test(message);
      if (quota) return json({ detail: "오늘의 무료 이미지 한도를 모두 사용했습니다." }, 429);
      if (capacity) return json({ detail: "이미지 서버가 잠시 혼잡합니다. 잠시 후 다시 시도해주세요." }, 503);
      return json({ detail: "이미지 생성 서비스 오류" }, 502);
    }
  },
};
