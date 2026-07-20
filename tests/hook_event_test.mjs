import os from 'node:os';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import logger from '../hooks/company-adaptive-logger/handler.ts';
import bootstrap from '../hooks/company-adaptive-bootstrap/handler.ts';

const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'company-adaptive-hook-'));
await fs.mkdir(path.join(tmp, 'adaptive-openclaw/profiles/users'), { recursive: true });
await fs.mkdir(path.join(tmp, 'adaptive-openclaw/profiles/workflows'), { recursive: true });
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/company.md'), '---\nschema: company_profile.v1\n---\n# Company\n- Safety rules active\n');
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/users/discord_123456.md'), '---\nschema: user_profile.v1\n---\n# User\n- prefers tables\n');
await fs.writeFile(path.join(tmp, 'adaptive-openclaw/profiles/workflows/_template.md'), '---\nschema: workflow_profile.v1\n---\n# Workflow\n- validate outputs\n');
await logger({ type: 'message', action: 'received', sessionKey: 's1', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, content: '請用表格，不要太長 token ghp_1234567890abcdef', channelId: 'c1', metadata: { senderId: '123456', provider: 'discord' } } });
const log = await fs.readFile(path.join(tmp, 'adaptive-openclaw/events/usage_events.jsonl'), 'utf8');
assert.match(log, /"sender_id":"123456"/);
assert.doesNotMatch(log, /ghp_1234567890abcdef/);
const event = { type: 'agent', action: 'bootstrap', sessionKey: 'discord_123456', timestamp: new Date(), messages: [], context: { workspaceDir: tmp, bootstrapFiles: [] } };
await bootstrap(event);
assert.equal(event.context.bootstrapFiles.length, 1);
assert.equal(event.context.bootstrapFiles[0].name, 'BOOTSTRAP.md');
assert.match(event.context.bootstrapFiles[0].content, /Adaptive OpenClaw Runtime Context/);

// fallback env workspace
process.env.OPENCLAW_WORKSPACE_DIR = tmp;
await logger({ type: 'message', action: 'received', sessionKey: 's2', timestamp: new Date(), messages: [], context: { content: '請用表格', channelId: 'c2', metadata: { senderId: '789', provider: 'discord' } } });
const log2 = await fs.readFile(path.join(tmp, 'adaptive-openclaw/events/usage_events.jsonl'), 'utf8');
assert.match(log2, /"sender_id":"789"/);
console.log('PASS hook_event_test');
