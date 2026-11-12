"""Shared settings: every script imports from here, so they always agree."""

# Each agent's manifest: the tools it is allowed to call (its declared purpose).
MANIFESTS = {
    "ticket-summarizer": ["jira.search", "jira.read", "llm.summarize"],
    "code-assistant":    ["repo.read", "repo.write", "tests.run", "llm.complete"],
    "sales-copilot":     ["crm.read", "email.draft", "llm.complete"],
    "data-analyst":      ["warehouse.query", "sheets.write", "llm.complete"],
}