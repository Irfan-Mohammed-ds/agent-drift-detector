"""Step 3: three detectors, each adding a flag to the daily table.

Output: data/scored.csv
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

daily = pd.read_csv("data/daily.csv", keep_default_na=False)

# ---- Detector A: spend spikes, judged against each user's own normal --------
def robust_z(x):
    """How unusual each value is, using median and MAD so one spike can't hide itself."""
    median = x.median()
    mad = (x - median).abs().median()
    return (x - median) / (1.4826 * mad + 1e-9)

daily["spend_z"] = daily.groupby(["user", "agent"])["tokens"].transform(
    lambda s: robust_z(np.log1p(s)))
daily["flag_spend"] = daily.spend_z > 3.5

# ---- Detector B: manifest rule — did the agent step outside its purpose? ----
daily["flag_manifest"] = daily.out_of_manifest > 0

# ---- Detector C: Isolation Forest on behavior shape -------------------------
FEATURES = ["calls_vs_usual", "records_vs_usual", "off_hours_calls",
            "distinct_tools", "max_records"]
X = daily[FEATURES].copy()
X["max_records"] = np.log1p(X.max_records)            # tame the huge ranges
X["off_hours_calls"] = np.log1p(X.off_hours_calls)
# Only unusually HIGH activity is risky; a quiet day is not an attack.
X[["calls_vs_usual", "records_vs_usual"]] = X[["calls_vs_usual", "records_vs_usual"]].clip(lower=0)

forest = IsolationForest(n_estimators=300, random_state=42).fit(X)
daily["iforest_score"] = -forest.score_samples(X)        # higher = more unusual
ALERT_SHARE = 0.02                                       # alert budget: top 2% of days
daily["flag_iforest"] = daily.iforest_score >= daily.iforest_score.quantile(1 - ALERT_SHARE)

# ---- Combined: alert if any detector fires ---------------------------------
daily["flag_any"] = daily[["flag_spend", "flag_manifest", "flag_iforest"]].any(axis=1)

daily.to_csv("data/scored.csv", index=False)
print(daily[["flag_spend", "flag_manifest", "flag_iforest", "flag_any"]].sum())