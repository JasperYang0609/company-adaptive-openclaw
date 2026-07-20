# Channel Onboarding Agent

## Purpose

The Channel Onboarding Agent turns a newly created Discord channel or thread into a guided, role-aware OpenClaw workflow entry point.

It must not ask customers to invent prompts or state a mature AI strategy upfront. Many customer-side managers and staff do not yet know what AI can help with. The agent should infer, offer options, produce a first visible artifact, then learn from corrections.

## Trigger

When a new customer Discord channel or discussion thread is created, log or create a channel onboarding profile with:

- channel/thread id, parent channel id when available, name, category, and initial description/topic
- creator user id
- creator identity / role / position
- permission boundary when available
- creator's initial statements and later corrections, redacted
- inferred channel purpose and confidence
- selected assistance options
- generated artifacts and accepted/corrected outcomes
- blocked points and recommended next workflow

## Onboarding flow

1. Infer the channel scene from channel name/category/topic.
2. Ask or confirm the creator's role/position.
3. Present role-aware options using this framing:

   > 依照你的角色，我可以協助你以下問題，你想先從哪個開始？

4. Offer a visible first artifact instead of asking for a complete prompt.
5. Ask whether the artifact is close enough:

   > 這比較像你要的嗎？

6. If accepted, create or update the data path, Notion path, workflow profile, report cadence, and channel usage menu.
7. If corrected, record the correction as evidence for fixed optimization.

## Role-aware examples

For the same `客服` channel:

- CEO / owner: customer-risk summary, revenue-impact risk, high-risk complaint alerts, weekly customer health report.
- Manager: repeated issues, response quality variance, unresolved cases, improvement report.
- Frontline support: response drafts, FAQ lookup, customer issue summarization, special-case escalation.

## Fixed optimization

Nightly learning should update channel recommendations from:

- selected options
- accepted artifacts
- repeated corrections
- low usage / no-reply channels
- task types observed in the channel
- role-specific friction

Identity, permission, RLS, secrets, and sensitive raw details must never auto-apply. They should stay pending or require administrator review.

## Formal flowchart v1

```mermaid
flowchart TD
  A[Customer creates a new Discord channel or discussion thread] --> B[OpenClaw starts Channel Onboarding Agent]

  B --> C[Collect safe baseline context]
  C --> C1[Channel/thread name / category]
  C --> C2[Creator user id]
  C --> C3[Creator identity / position / permission boundary]
  C --> C4[Initial topic, description, or first messages]

  C1 --> D[Infer channel purpose]
  C2 --> D
  C3 --> D
  C4 --> D

  D --> E[Generate role-aware assistance menu]
  E --> F[Ask: 依照你的角色，我可以協助你以下問題，你想先從哪個開始？]

  F --> G[User chooses one direction]
  G --> H[OpenClaw creates the first visible artifact]

  H --> I{這比較像你要的嗎？}

  I -->|Yes| J[Create formal workflow]
  J --> J1[Create data path]
  J --> J2[Create Notion / DB / document structure]
  J --> J3[Create channel task menu]
  J --> J4[Set daily / weekly reporting cadence]

  I -->|Right direction, needs changes| K[Record correction]
  K --> H

  I -->|Not what I need| L[Return to menu and try another artifact]
  L --> F

  J --> M[Enable channel workflow]
  M --> N[Record ongoing usage signals]
  N --> N1[Selected options]
  N --> N2[Accepted artifacts]
  N --> N3[Corrections]
  N --> N4[Blocked or unused steps]

  N --> O[Optimize Channel Profile on a fixed cadence]
  O --> P[Future replies fit this channel, role, and company better]
```

### Flow principle

When a new channel or discussion thread is created, OpenClaw should not ask `What do you want to do?` first. It should infer the likely purpose from the channel, creator identity, position, and permission boundary; then offer role-aware options, produce a visible artifact, and let the user confirm or correct from there.


## Discussion thread behavior

Discussion threads should use the same onboarding flow as channels. The profile key should use the thread id, while preserving the parent channel id when available. This avoids treating every thread as a blank chat and lets OpenClaw infer whether the thread is a sub-workflow, a project branch, or a temporary discussion under an existing channel.

## Discord presentation rule

Do not paste raw Mermaid flowchart blocks as the primary user-facing diagram in Discord. They are hard to read on mobile and make customer-side confirmation feel technical.

For Discord, customer onboarding, and on-site review:

- Use PNG / SVG / Notion visual blocks as the primary artifact.
- Keep Mermaid only as engineering source or documentation reference.
- If a flowchart is requested in chat, generate and attach a visual file instead of sending a large code block.
- Keep the diagram to 5-9 main steps and use short labels suitable for mobile screens.

Recommended customer-facing diagram asset:

![Channel / Thread Onboarding Flow](assets/channel_thread_onboarding_flow_v1.png)
