const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });

const textEncoder = new TextEncoder();

function base64Url(bytes) {
  let binary = "";
  for (const byte of new Uint8Array(bytes)) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_");
}

function decodeBase64(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

async function sha256(value) {
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", textEncoder.encode(value)))]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function signingKey(env) {
  return crypto.subtle.importKey(
    "pkcs8",
    decodeBase64(env.LICENSE_PRIVATE_KEY_DER),
    { name: "Ed25519" },
    false,
    ["sign"],
  );
}

async function certificate(env, record, hardwareId) {
  const payload = {
    expires_at: record.expires_at,
    hardware_id: hardwareId,
    issued_at: new Date().toISOString(),
    license_id: record.id,
    status: "active",
    version: 1,
  };
  const sortedPayload = Object.fromEntries(Object.entries(payload).sort(([a], [b]) => a.localeCompare(b)));
  const payloadBytes = textEncoder.encode(JSON.stringify(sortedPayload));
  const signature = await crypto.subtle.sign("Ed25519", await signingKey(env), payloadBytes);
  return { payload: base64Url(payloadBytes), signature: base64Url(signature) };
}

function requireAdmin(request, env) {
  const supplied = request.headers.get("authorization") || "";
  if (!env.LICENSE_ADMIN_TOKEN || supplied !== `Bearer ${env.LICENSE_ADMIN_TOKEN}`) {
    throw new Response(JSON.stringify({ detail: "관리자 인증 실패" }), { status: 403 });
  }
}

async function body(request) {
  try {
    return await request.json();
  } catch {
    throw new Response(JSON.stringify({ detail: "잘못된 JSON 요청" }), { status: 400 });
  }
}

async function findLicense(env, licenseKey) {
  const keyHash = await sha256(String(licenseKey || "").trim().toUpperCase());
  const record = await env.DB.prepare("SELECT * FROM licenses WHERE key_hash = ?").bind(keyHash).first();
  if (!record) throw new Response(JSON.stringify({ detail: "등록되지 않은 라이선스 키입니다." }), { status: 404 });
  if (record.revoked) throw new Response(JSON.stringify({ detail: "사용이 중지된 라이선스입니다." }), { status: 403 });
  if (Date.now() > Date.parse(record.expires_at)) {
    throw new Response(JSON.stringify({ detail: "만료된 라이선스입니다." }), { status: 403 });
  }
  return record;
}

async function activateOrVerify(request, env, allowBinding) {
  const data = await body(request);
  const licenseKey = String(data.license_key || "").trim().toUpperCase();
  const hardwareId = String(data.hardware_id || "").trim();
  if (licenseKey.length < 10 || hardwareId.length < 32) return json({ detail: "잘못된 요청" }, 400);
  const record = await findLicense(env, licenseKey);

  if (!record.hardware_id && allowBinding) {
    const result = await env.DB.prepare(
      "UPDATE licenses SET hardware_id = ?, activated_at = ? WHERE id = ? AND hardware_id = ''",
    ).bind(hardwareId, new Date().toISOString(), record.id).run();
    if (!result.success) return json({ detail: "PC 등록에 실패했습니다." }, 500);
    if ((result.meta?.changes || 0) !== 1) {
      const latest = await env.DB.prepare("SELECT hardware_id FROM licenses WHERE id = ?").bind(record.id).first();
      if (!latest || latest.hardware_id !== hardwareId) {
        return json({ detail: "이미 다른 컴퓨터에서 활성화된 라이선스입니다." }, 403);
      }
    }
    record.hardware_id = hardwareId;
  }
  if (record.hardware_id !== hardwareId) {
    return json({ detail: "이미 다른 컴퓨터에서 활성화된 라이선스입니다." }, 403);
  }
  return json({ certificate: await certificate(env, record, hardwareId) });
}

async function createLicense(request, env) {
  requireAdmin(request, env);
  const data = await body(request);
  const customerName = String(data.customer_name || "").trim();
  const permanent = data.permanent === true;
  const days = Number(data.days || 365);
  const memo = String(data.memo || "").slice(0, 500);
  if (!customerName || (!permanent && (!Number.isInteger(days) || days < 1 || days > 3650))) {
    return json({ detail: "고객명 또는 기간이 올바르지 않습니다." }, 400);
  }
  const random = () => [...crypto.getRandomValues(new Uint8Array(3))]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("").toUpperCase();
  const licenseKey = `ASG-${random()}-${random()}-${random()}-${random()}`;
  const now = new Date();
  const expiry = permanent ? new Date("9999-12-31T23:59:59.999Z") : new Date(now.getTime() + days * 86400000);
  if (!permanent) expiry.setUTCHours(23, 59, 59, 999);
  const id = crypto.randomUUID().replace(/-/g, "").slice(0, 24);
  await env.DB.prepare(
    "INSERT INTO licenses (id,key_hash,customer_name,memo,created_at,expires_at) VALUES (?,?,?,?,?,?)",
  ).bind(id, await sha256(licenseKey), customerName, memo, now.toISOString(), expiry.toISOString()).run();
  return json({ license_key: licenseKey, expires_at: expiry.toISOString(), permanent }, 201);
}

async function route(request, env) {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/health") return json({ ok: true });
  if (request.method === "POST" && url.pathname === "/api/v1/licenses/activate") {
    return activateOrVerify(request, env, true);
  }
  if (request.method === "POST" && url.pathname === "/api/v1/licenses/verify") {
    return activateOrVerify(request, env, false);
  }
  if (request.method === "POST" && url.pathname === "/admin/api/licenses") {
    return createLicense(request, env);
  }
  if (request.method === "GET" && url.pathname === "/admin/api/licenses") {
    requireAdmin(request, env);
    const records = await env.DB.prepare(
      "SELECT id,customer_name,memo,created_at,expires_at,hardware_id,activated_at,revoked FROM licenses ORDER BY created_at DESC",
    ).all();
    return json(records.results || []);
  }
  const action = url.pathname.match(/^\/admin\/api\/licenses\/([a-f0-9]{24})\/(revoke|reset-hardware)$/);
  if (request.method === "POST" && action) {
    requireAdmin(request, env);
    if (action[2] === "revoke") {
      await env.DB.prepare("UPDATE licenses SET revoked = 1 WHERE id = ?").bind(action[1]).run();
    } else {
      await env.DB.prepare("UPDATE licenses SET hardware_id = '', activated_at = '' WHERE id = ?").bind(action[1]).run();
    }
    return json({ ok: true });
  }
  return json({ detail: "Not Found" }, 404);
}

export default {
  async fetch(request, env) {
    try {
      return await route(request, env);
    } catch (error) {
      if (error instanceof Response) return error;
      console.error(error);
      return json({ detail: "서버 오류" }, 500);
    }
  },
};
