/** Proven Northstar Cloud demo prompts for Ask / Agent happy paths. */

export const ASK_DEMO_PROMPTS = [
  "What should I check for billing 502 errors after deployment?",
  "What was the root cause of the August 2025 billing-api 502 incident?",
  "What is the default API gateway upstream timeout for billing-api?",
  "How do I restart billing-api and verify it recovered?",
] as const;

export const AGENT_DEMO_PROMPTS = [
  "Investigate billing API 502 errors after the latest deployment and recommend checks from workspace runbooks.",
  "Summarize the August 2025 billing-api 502 incident and list follow-up actions.",
  "Compare gateway timeout guidance with the billing-api first-response checklist for post-deploy 502s.",
] as const;
