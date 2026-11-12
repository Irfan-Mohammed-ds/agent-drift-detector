"""Step 1 : generating 30 days of AI agent activity logs, with planned attacks.

Output : data/events.csv, one row per tool call."""

import numpy as np
import pandas as pd

from config import MANIFESTS

SEED = 42
N_USERS = 40
N_DAYS = 30
START = pd.Timestamp("2026-10-01")

# Typical tokens per call (median) and records touched per call, by tool.

TOKENS = {"llm.summarize": 1800, "llm.complete": 1500, "jira.search": 300, "jira.read": 600,
          "repo.read": 800, "repo.write": 900, "tests.run": 200, "crm.read": 500,
          "email.draft": 700, "warehouse.query": 400, "sheets.write": 300, "secrets.read": 100}
RECORDS = {"jira.search": 20, "jira.read": 3, "repo.read": 5, "crm.read": 15,
           "warehouse.query": 5}

rng = np.random.default_rng(SEED)

def normal_calls(user, agent, day, n, on_call):
    "n ordinary tool will call for one user and agent every day."
    tools = MANIFESTS[agent]
    hours = rng.normal(13, 2.5, n).clip(7, 19)      # business times
    if on_call:
        night = rng.random(n) < 0.15
        hours[night] = rng.uniform(0, 6, night.sum())
    rows = []
    for h in hours:
        tool = rng.choice(tools)
        rows.append({
             "ts": START + pd.Timedelta(days=day, hours=float(h)),
            "user": user, "agent": agent, "tool": tool,
            "tokens": int(rng.lognormal(np.log(TOKENS[tool]), 0.5)),
            "records": int(rng.poisson(RECORDS.get(tool, 0))),
            "attack": "",
        })
    return rows


#----1. Normal behaviors ----------------

users = [f"u{i:02d}" for i in range(N_USERS)]
plan = {}                                                         # (user,agent ) -> calls per weekday

for u in users:
    for a in rng.choice(list(MANIFESTS), size=rng.integers(1, 3), replace = False):
        plan[(u,a)] = rng.lognormal(np.log(20), 0.6)              # mostly being light users 
on_call = set(rng.choice(users, size = 4, replace=False))

rows = []
for (u,a), rate in plan.items():
    for d in range(N_DAYS):
        weekend = (START + pd.Timedelta(days=d)).dayofweek >= 5
        n = rng.poisson(rate * (0.2 if weekend else 1.0))
        rows += normal_calls(u, a, d,n,u in on_call)

#Benign suprises: Very busy days ( end of a quarter or a big release).
#These are not attacks, so a good detector should mostly let them be and ignore them.

for(u,a) in rng.choice(list(plan), size=12, replace = False):
    d = int(rng.integers(0, N_DAYS))
    rows += normal_calls(u, a, d, int(plan[(u,a)] * 2.5), False)

#-----2. Planted attacks (answer key)------------

def spend_spike (u, a ,d):
    "Runaway agent or stolen key : same tools , ~ 15x the tokens."

    out = normal_calls(u, a, d,int(plan[u,a] * 3), False)
    for r in out:
        r["tokens"] *= 15
    return out

def bulk_export(u, a ,d):
    "Allowed tool with absurd volume: pulls thousands of records."
    tool = {"sales-copilot": "crm.read", "data-analyst": "warehouse.query",
            "ticket-summarizer": "jira.search", "code-assistant": "repo.read"}[a]
    out = normal_calls(u, a, d, 6, False)
    for r in out:
        r["tool"] , r["records"] = tool, int(rng.integers(3000, 20000))
    return out

def credential_access(u, a, d):
    """Agent reads secrets, a tool no manifest allows."""
    out = normal_calls(u, a, d, 3, False)
    for r in out:
        r["tool"], r["tokens"] = "secrets.read", 100
    return out

def off_hours_burst(u, a, d):
    """Many normal-looking calls between 1 and 4 AM."""
    out = normal_calls(u, a, d, int(rng.integers(25, 50)), False)
    for r in out:
        r["ts"] = START + pd.Timedelta(days=d, hours=float(rng.uniform(1, 4)))
    return out

def intent_drift(u, a, d):
    """Agent calls tools that belong to a different agent's purpose."""
    other = [t for ag, ts in MANIFESTS.items() if ag != a for t in ts if t not in MANIFESTS[a]]
    out = normal_calls(u, a, d, int(rng.integers(5, 12)), False)
    for r in out:
        r["tool"] = rng.choice(other)
        r["records"] = int(rng.poisson(RECORDS.get(r["tool"], 0)))
    return out

ATTACKS = [spend_spike, bulk_export, credential_access, off_hours_burst, intent_drift]
pairs = list(plan)
chosen = rng.choice(len(pairs) * N_DAYS, size=30, replace=False)   # 30 distinct user-agent-days
for i, idx in enumerate(chosen):
    u, a = pairs[idx // N_DAYS]
    d = int(idx % N_DAYS)
    attack = ATTACKS[i % len(ATTACKS)]                              # 6 of each type
    for r in attack(u, a, d):
        r["attack"] = attack.__name__
        rows.append(r)

events = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
events.to_csv("data/events.csv", index=False)
print(f"{len(events):,} events | {events.user.nunique()} users | "
      f"{(events.attack != '').sum()} attack events")
print(events[events.attack != ""].groupby("attack").size())

