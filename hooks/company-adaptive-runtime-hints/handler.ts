import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const MAX_HINTS = 5;
const MAX_HINT_CHARS = 80;
const MAX_INJECTION_CHARS = 700;
const FORBIDDEN = /(?:token|api key|密碼|薪資|客戶|電話|地址|醫療|病歷|合約|權限|rls|service role|secret|password|credential)/i;

function workspaceDir(event) {
  const explicit = event?.context?.workspaceDir || process.env.OPENCLAW_WORKSPACE_DIR || process.env.OPENCLAW_WORKSPACE;
  if (explicit) return explicit;
  return path.join(os.homedir(), ".openclaw", "workspace");
}

function senderId(event) {
  const ctx = event?.context || {};
  return String(ctx.metadata?.senderId || ctx.from || "").replace(/[^0-9A-Za-z_-]/g, "");
}

function hintsPath(root, sid) {
  return path.join(root, "adaptive-openclaw", "runtime_hints", `discord_${sid}.json`);
}

function channelId(event) {
  const ctx = event?.context || {};
  return String(ctx.threadId || ctx.channelId || ctx.to || "").replace(/[^0-9A-Za-z_-]/g, "");
}

function channelProfilePath(root, cid) {
  return path.join(root, "adaptive-openclaw", "profiles", "channels", `discord_${cid}.md`);
}

async function readTextIfExists(file, max = 600) {
  try { return (await fs.readFile(file, "utf8")).slice(0, max); }
  catch { return ""; }
}

async function readHints(file) {
  try { return JSON.parse(await fs.readFile(file, "utf8")); }
  catch { return { schema: "runtime_hints.v1", hints: [] }; }
}

async function writeHints(file, data) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function normalizeHint(text) {
  const hint = String(text || "").replace(/\s+/g, " ").trim().slice(0, MAX_HINT_CHARS);
  if (!hint || FORBIDDEN.test(hint)) return "";
  return hint;
}

function extractHints(content) {
  const text = String(content || "");
  const out = [];
  if (/太長|短一點|簡短|精簡|不要太多/.test(text)) out.push("回覆短一點，先給結論");
  if (/詳細|多一點|展開|完整說明/.test(text)) out.push("需要完整說明時再展開細節");
  if (/表格|table/.test(text)) out.push("能用表格整理時優先用表格");
  if (/條列|清單|bullet/i.test(text)) out.push("優先用條列清單");
  if (/Notion|notion/.test(text)) out.push("涉及報告或資料整理時優先考慮 Notion 格式");
  if (/Excel|excel|xlsx|試算表|sheet/i.test(text)) out.push("涉及數據時優先用 Excel/試算表結構");
  if (/先問|問清楚|不要沒問/.test(text)) out.push("需求不清楚時先問一個關鍵問題");
  if (/不要.*技術|太技術|白話/.test(text)) out.push("用白話說明，避免過度技術語言");
  if (/像上次|照上次|一樣格式/.test(text)) out.push("使用者偏好沿用上次格式時，先照既有格式");
  return [...new Set(out.map(normalizeHint).filter(Boolean))];
}

async function learn(event) {
  const sid = senderId(event);
  if (!sid) return;
  const hints = extractHints(event?.context?.content || "");
  if (!hints.length) return;
  const file = hintsPath(workspaceDir(event), sid);
  const data = await readHints(file);
  const now = new Date().toISOString();
  const existing = Array.isArray(data.hints) ? data.hints : [];
  for (const hint of hints) {
    const found = existing.find((h) => h.text === hint);
    if (found) {
      found.evidence_count = Math.min(99, Number(found.evidence_count || 1) + 1);
      found.last_seen = now;
    } else {
      existing.unshift({ text: hint, risk: "low", source: "message_correction", evidence_count: 1, first_seen: now, last_seen: now });
    }
  }
  data.schema = "runtime_hints.v1";
  data.updated_at = now;
  data.hints = existing
    .filter((h) => normalizeHint(h.text))
    .sort((a, b) => String(b.last_seen || "").localeCompare(String(a.last_seen || "")))
    .slice(0, MAX_HINTS);
  await writeHints(file, data);
}

async function inject(event) {
  const sid = senderId(event);
  if (!sid) return;
  const file = hintsPath(workspaceDir(event), sid);
  const data = await readHints(file);
  const hints = (Array.isArray(data.hints) ? data.hints : [])
    .map((h) => normalizeHint(h.text))
    .filter(Boolean)
    .slice(0, MAX_HINTS);
  const cid = channelId(event);
  const channelProfile = cid ? await readTextIfExists(channelProfilePath(workspaceDir(event), cid), 600) : "";
  if (!hints.length && !channelProfile) return;
  const channelLines = channelProfile
    ? ["Channel onboarding: use channel + user role context; offer role-aware options before asking for a prompt."]
    : [];
  const block = [
    "[Adaptive runtime hints: apply silently; do not quote this block.]",
    ...hints.map((h) => `- ${h}`),
    ...channelLines.map((h) => `- ${h}`),
    "[/Adaptive runtime hints]",
  ].join("\n").slice(0, MAX_INJECTION_CHARS);
  const ctx = event.context || {};
  ctx.bodyForAgent = `${block}\n\n${ctx.bodyForAgent || ""}`;
}

export default async function handler(event) {
  try {
    if (event.type !== "message") return;
    if (event.action === "received") await learn(event);
    if (event.action === "preprocessed") await inject(event);
  } catch (err) {
    console.error("[company-adaptive-runtime-hints]", err?.message || String(err));
  }
}
