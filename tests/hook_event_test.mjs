import os from 'node:os';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import logger from '../hooks/company-adaptive-logger/handler.ts';
import bootstrap from '../hooks/company-adaptive-bootstrap/handler.ts';
import runtimeHints from '../hooks/company-adaptive-runtime-hints/handler.ts';

const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'company-adaptive-hook-'));
await fs.mkdir(path.join(tmp, 'adaptive-openclaw/profiles/users'), { recursive: true });
await fs.mkdir(path.join(tmp, 'adaptive-openclaw/profiles/workflows'), { recursive: true });
await fs.mkdir(path.join(tmp, 'adaptive-openclaw/profiles/channels'), { recursive: true });
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/company.md'), '---\nschema: company_profile.v1\n---\n# Company\n- Safety rules active\n');
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/users/discord_123456.md'), '---\nschema: user_profile.v1\n---\n# User\n- prefers tables\n');
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/workflows/_template.md'), '---\nschema: workflow_profile.v1\n---\n# Workflow\n- validate outputs\n');
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/channels/discord_c1.md'), '---\nschema: channel_profile.v1\n---\n# Channel\n- offer role-aware options before asking for prompts\n');
await logger({ type: 'thread', action: 'created', sessionKey: 's0', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, threadId: 'c0', channelId: 'parent1', threadName: '客服討論串', createdByUserId: '123456', creatorRole: '主管', creatorPosition: '客服主管', metadata: { provider: 'discord' } } });
await logger({ type: 'message', action: 'received', sessionKey: 's1', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, content: '請用表格，不要太長 token ghp_1234567890abcdef', channelId: 'c1', metadata: { senderId: '123456', provider: 'discord' } } });
const log = await fs.readFile(path.join(tmp, 'adaptive-openclaw/events/usage_events.jsonl'), 'utf8');
assert.match(log, /"event_action":"thread_created"/);
assert.match(log, /"surface_type":"thread"/);
assert.match(log, /"sender_id":"123456"/);
assert.doesNotMatch(log, /ghp_1234567890abcdef/);
const event = { type: 'agent', action: 'bootstrap', sessionKey: 'discord_123456', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, channelId: 'c1', bootstrapFiles: [] } };
await bootstrap(event);
assert.equal(event.context.bootstrapFiles.length, 1);
assert.equal(event.context.bootstrapFiles[0].name, 'BOOTSTRAP.md');
assert.match(event.context.bootstrapFiles[0].content, /Adaptive OpenClaw Runtime Context/);
assert.match(event.context.bootstrapFiles[0].content, /Current Channel/);

// fallback env workspace
process.env.OPENCLAW_WORKSPACE_DIR = tmp;
await logger({ type: 'message', action: 'received', sessionKey: 's2', timestamp: new Date(), messages: [], context: { content: '請用表格', channelId: 'c2', metadata: { senderId: '789', provider: 'discord' } } });
const log2 = await fs.readFile(path.join(tmp, 'adaptive-openclaw/events/usage_events.jsonl'), 'utf8');
assert.match(log2, /"sender_id":"789"/);

await logger({ type: 'message', action: 'received', sessionKey: 's-surrogate', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, content: 'broken \uD800 text', channelId: 'surrogate-\uD800-channel', metadata: { senderId: 'surrogate-\uD800-user', provider: 'discord' } } });
const normalizedLog = await fs.readFile(path.join(tmp, 'adaptive-openclaw/events/usage_events.jsonl'), 'utf8');
assert.doesNotMatch(normalizedLog, /\\ud800/i);
for (const line of normalizedLog.trim().split('\n')) JSON.parse(line);

await runtimeHints({ type: 'message', action: 'received', sessionKey: 's3', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, content: '下次請用表格，短一點', from: '123456', channelId: 'c3', metadata: { senderId: '123456', provider: 'discord' } } });
const hintFile = await fs.readFile(path.join(tmp, 'adaptive-openclaw/runtime_hints/discord_123456.json'), 'utf8');
assert.match(hintFile, /表格/);
const pre = { type: 'message', action: 'preprocessed', sessionKey: 's3', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, bodyForAgent: '請整理資料', from: '123456', channelId: 'c1', metadata: { senderId: '123456', provider: 'discord' } } };
await runtimeHints(pre);
assert.match(pre.context.bodyForAgent, /Adaptive runtime hints/);
assert.match(pre.context.bodyForAgent, /表格/);
assert.match(pre.context.bodyForAgent, /role-aware options/);
console.log('PASS hook_event_test');
