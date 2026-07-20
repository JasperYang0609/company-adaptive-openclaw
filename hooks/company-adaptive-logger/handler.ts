import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const REDACT_PATTERNS = [
  /\b(?:sk|pk|ntn|ghp|github_pat|AIza)[A-Za-z0-9_\-]{12,}\b/g,
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
  /\b\+?\d[\d\s\-()]{7,}\d\b/g,
];

function workspaceDir(event) {
  return event?.context?.workspaceDir || process.env.OPENCLAW_WORKSPACE_DIR || process.env.OPENCLAW_WORKSPACE || process.cwd();
}

function redact(text) {
  let value = String(text || "").slice(0, 1600);
  for (const pattern of REDACT_PATTERNS) value = value.replace(pattern, "[REDACTED]");
  return value;
}

function taskType(content) {
  const lower = String(content || "").toLowerCase();
  if (/notion|資料庫|db/.test(lower)) return "notion_or_database";
  if (/excel|sheet|表格|報表/.test(lower)) return "spreadsheet_or_report";
  if (/圖|圖片|生圖|視覺/.test(lower)) return "visual_artifact";
  if (/會議|逐字稿|紀錄/.test(lower)) return "meeting_notes";
  if (/修|改|bug|測試|github|repo|commit/.test(lower)) return "development";
  return "general";
}

function correctionSignal(content) {
  const text = String(content || "");
  const hits = [];
  for (const keyword of ["太長", "太短", "用表格", "不要", "下次", "格式", "像上次", "Notion", "Excel", "圖卡", "不對", "重做"]) {
    if (text.includes(keyword)) hits.push(keyword);
  }
  return hits.join(",");
}

async function appendJsonl(file, obj) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.appendFile(file, JSON.stringify(obj) + "\n", "utf8");
}

export default async function handler(event) {
  try {
    if (event.type !== "message") return;
    const ctx = event.context || {};
    const content = ctx.content || "";
    const base = {
      event_id: "evt_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12),
      timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : new Date().toISOString(),
      platform: ctx.metadata?.provider || ctx.provider || "unknown",
      session_key: event.sessionKey || "unknown",
      channel_id: String(ctx.channelId || ctx.to || "unknown"),
      event_action: event.action,
    };
    let obj;
    if (event.action === "received") {
      obj = {
        ...base,
        sender_id: String(ctx.metadata?.senderId || ctx.from || "unknown"),
        task_type: taskType(content),
        content_summary: redact(content).slice(0, 500),
        correction_signal: correctionSignal(content),
      };
    } else if (event.action === "sent") {
      obj = {
        ...base,
        sender_id: "assistant",
        task_type: "assistant_reply",
        content_summary: redact(content).slice(0, 500),
        success_signal: ctx.success === false ? "failed" : "sent",
        artifact_delivered: /MEDIA:|\.png|\.pdf|\.xlsx|\.md/i.test(String(content || "")),
      };
    } else return;
    const file = path.join(workspaceDir(event), "adaptive-openclaw", "events", "usage_events.jsonl");
    await appendJsonl(file, obj);
  } catch (err) {
    // Hooks must never break the main OpenClaw runtime.
    console.error("[company-adaptive-logger]", err?.message || String(err));
  }
}
