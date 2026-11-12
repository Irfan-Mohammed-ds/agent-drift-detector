"""Step 2: turn raw tool calls into one row of behavior per user, agent and day.

Output: data/daily.csv
"""
import numpy as np
import pandas as pd

from config import MANIFESTS

events = pd.read_csv("data/events.csv", parse_dates=["ts"], keep_default_na=False)

events["date"] = events.ts.dt.date
events["hour"] = events.ts.dt.hour
events["off_hours"] = (events.hour < 6) | (events.hour >= 22)
events["out_of_manifest"] = [t not in MANIFESTS[a] for t, a in zip(events.tool, events.agent)]

daily = events.groupby(["user", "agent", "date"]).agg(
    calls=("tool", "size"),
    tokens=("tokens", "sum"),
    records=("records", "sum"),
    max_records=("records", "max"),
    off_hours_calls=("off_hours", "sum"),
    distinct_tools=("tool", "nunique"),
    out_of_manifest=("out_of_manifest", "sum"),
    attack=("attack", lambda s: next((x for x in s if x), "")),   # answer key, NOT a feature
).reset_index()

daily["off_hours_share"] = daily.off_hours_calls / daily.calls

# Compare each day with that user's own normal: the log of today / their median day.
for col in ["calls", "tokens", "records"]:
    median = daily.groupby(["user", "agent"])[col].transform("median")
    daily[f"{col}_vs_usual"] = np.log1p(daily[col]) - np.log1p(median)

daily.to_csv("data/daily.csv", index=False)
print(f"{len(daily):,} user-agent-days | {(daily.attack != '').sum()} contain an attack")
print(daily.describe().T[["mean", "50%", "max"]].round(2))