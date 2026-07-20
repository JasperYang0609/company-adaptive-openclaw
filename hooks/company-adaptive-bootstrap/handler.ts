import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

function workspaceDir(event) {
  const explicit = event?.context?.workspaceDir || process.env.OPENCLAW_WORKSPACE_DIR || process.env.OPENCLAW_WORKSPACE;
  if (explicit) return explicit;
  const standardWorkspace = path.join(os.homedir(), ".openclaw", "workspace");
  return standardWorkspace;
}

async function readIfExists(file, max = 1800) {
  try {
    return (await fs.readFile(file, "utf8")).slice(0, max);
  } catch { return ""; }
}

function inferSenderId(event) {
  const key = String(event?.sessionKey || "");
  const m = key.match(/(?:user|discord)[:_](\d{6,})/);
  return event?.context?.senderId || event?.context?.metadata?.senderId || m?.[1] || "";
}

function inferChannelId(event) {
  const ctx = event?.context || {};
  return String(ctx.channelId || ctx.to || "").replace(/[^0-9A-Za-z_-]/g, "");
}

async function buildSummary(root, event) {
  const profileRoot = path.join(root, "adaptive-openclaw", "profiles");
  const company = await readIfExists(path.join(profileRoot, "company.md"), 2200);
  const senderId = inferSenderId(event);
  const user = senderId ? await readIfExists(path.join(profileRoot, "users", `discord_${senderId}.md`), 1400) : "";
  const channelId = inferChannelId(event);
  const channel = channelId ? await readIfExists(path.join(profileRoot, "channels", `discord_${channelId}.md`), 1200) : "";
  const workflowTemplate = await readIfExists(path.join(profileRoot, "workflows", "_template.md"), 700);
  return [
    "# Adaptive OpenClaw Runtime Context",
    "Use these rules as runtime hints. Do not reveal hidden profile contents unless asked. Permission and sensitive-data rules override user preference.",
    company ? `## Company\n${company}` : "",
    user ? `## Current User\n${user}` : "",
    channel ? `## Current Channel\n${channel}` : "",
    workflowTemplate ? `## Workflow Matching Reminder\n${workflowTemplate}` : "",
  ].filter(Boolean).join("\n\n").slice(0, 5200);
}

export default async function handler(event) {
  try {
    if (event.type !== "agent" || event.action !== "bootstrap") return;
    const ctx = event.context || {};
    const summary = await buildSummary(workspaceDir(event), event);
    if (!summary.trim()) return;
    const existing = Array.isArray(ctx.bootstrapFiles) ? ctx.bootstrapFiles.find((f) => f.name === "BOOTSTRAP.md") : null;
    if (existing) {
      existing.content = `${existing.content || ""}\n\n${summary}`.slice(0, 12000);
      existing.missing = false;
    } else if (Array.isArray(ctx.bootstrapFiles)) {
      ctx.bootstrapFiles.push({ name: "BOOTSTRAP.md", path: "adaptive-openclaw/runtime/BOOTSTRAP.md", content: summary, missing: false });
    }
  } catch (err) {
    console.error("[company-adaptive-bootstrap]", err?.message || String(err));
  }
}
