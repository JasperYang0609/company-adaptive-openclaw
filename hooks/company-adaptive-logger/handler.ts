import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

const REDACT_PATTERNS = [
  /\b(?:sk|pk|ntn|ghp|github_pat|AIza)[A-Za-z0-9_\-]{12,}\b/g,
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
  /\b\+?\d[\d\s\-()]{7,}\d\b/g,
];

function normalizeUnicode(value) {
  const text = String(value ?? "");
  let normalized = "";
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = text.charCodeAt(index + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        normalized += text[index] + text[index + 1];
        index += 1;
      } else {
        normalized += "\uFFFD";
      }
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      normalized += "\uFFFD";
    } else {
      normalized += text[index];
    }
  }
  return normalized.normalize("NFC");
}

function normalizeJsonValue(value) {
  if (typeof value === "string") return normalizeUnicode(value);
  if (Array.isArray(value)) return value.map(normalizeJsonValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [normalizeUnicode(key), normalizeJsonValue(item)]),
    );
  }
  return value;
}

function workspaceDir(event) {
  const explicit = event?.context?.workspaceDir || process.env.OPENCLAW_WORKSPACE_DIR || process.env.OPENCLAW_WORKSPACE;
  if (explicit) return explicit;
  const standardWorkspace = path.join(os.homedir(), ".openclaw", "workspace");
  return standardWorkspace;
}

function redact(text) {
  let value = normalizeUnicode(text).slice(0, 1600);
  for (const pattern of REDACT_PATTERNS) value = value.replace(pattern, "[REDACTED]");
  return value;
}

function safeString(value, fallback = "unknown") {
  const s = String(value || "").trim();
  return s ? redact(s).slice(0, 240) : fallback;
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
  const line = JSON.stringify(normalizeJsonValue(obj));
  JSON.parse(line);
  await fs.appendFile(file, line + "\n", { encoding: "utf8" });
}

export default async function handler(event) {
  try {
    const ctx = event.context || {};
    if ((event.type === "channel" || event.type === "thread") && event.action === "created") {
      const obj = {
        event_id: "evt_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12),
        timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : new Date().toISOString(),
        platform: ctx.metadata?.provider || ctx.provider || "discord",
        session_key: event.sessionKey || "unknown",
        channel_id: String(ctx.threadId || ctx.channelId || ctx.id || ctx.to || "unknown"),
        parent_channel_id: String(ctx.parentChannelId || ctx.parentId || ctx.channelId || ""),
        surface_type: event.type === "thread" ? "thread" : "channel",
        event_action: event.type === "thread" ? "thread_created" : "channel_created",
        sender_id: String(ctx.metadata?.senderId || ctx.createdByUserId || ctx.createdBy || ctx.from || "unknown"),
        channel_name: safeString(ctx.threadName || ctx.channelName || ctx.name),
        channel_category: safeString(ctx.channelCategory || ctx.parentName || ctx.category),
        creator_role: safeString(ctx.creatorRole || ctx.role),
        creator_position: safeString(ctx.creatorPosition || ctx.position),
        initial_description_summary: redact(ctx.description || ctx.topic || ctx.initialDescription || "").slice(0, 500),
        task_type: "channel_onboarding",
      };
      const file = path.join(workspaceDir(event), "adaptive-openclaw", "events", "usage_events.jsonl");
      await appendJsonl(file, obj);
      return;
    }
    if (event.type !== "message") return;
    const content = ctx.content || "";
    const base = {
      event_id: "evt_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12),
      timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : new Date().toISOString(),
      platform: ctx.metadata?.provider || ctx.provider || "unknown",
      session_key: event.sessionKey || "unknown",
      channel_id: String(ctx.threadId || ctx.channelId || ctx.to || "unknown"),
      parent_channel_id: String(ctx.parentChannelId || ctx.parentId || ctx.channelId || ""),
      surface_type: ctx.threadId ? "thread" : "channel",
      channel_name: safeString(ctx.channelName || ctx.name, ""),
      channel_category: safeString(ctx.channelCategory || ctx.parentName || ctx.category, ""),
      creator_role: safeString(ctx.creatorRole || ctx.metadata?.role, ""),
      creator_position: safeString(ctx.creatorPosition || ctx.metadata?.position, ""),
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
