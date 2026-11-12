"""Step 4: score each detector against the planted attacks, and draw the chart.

Outputs: results/summary.csv, results/recall_by_attack.csv, results/recall_by_attack.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 10)

df = pd.read_csv("data/scored.csv", keep_default_na=False)
df["is_attack"] = df.attack != ""
n_days = df.date.nunique()
DETECTORS = {"Spend spike (robust z)": "flag_spend", "Manifest rule": "flag_manifest",
             "Isolation Forest": "flag_iforest", "Combined (any)": "flag_any"}

# ---- 1. Overall: precision, recall, false alarms per day -------------------
rows = []
for name, col in DETECTORS.items():
    tp = (df[col] & df.is_attack).sum()
    fp = (df[col] & ~df.is_attack).sum()
    fn = (~df[col] & df.is_attack).sum()
    rows.append({"detector": name, "caught": f"{tp}/{tp + fn}",
                 "precision": round(tp / max(tp + fp, 1), 2),
                 "recall": round(tp / (tp + fn), 2),
                 "false_alarms_per_day": round(fp / n_days, 2)})
summary = pd.DataFrame(rows)
summary.to_csv("results/summary.csv", index=False)
print(summary.to_string(index=False), "\n")

# ---- 2. Which detector catches which attack -------------------------------
attacks = df[df.is_attack]
by_type = attacks.groupby("attack")[list(DETECTORS.values())].mean().round(2)
by_type.columns = list(DETECTORS)
by_type.to_csv("results/recall_by_attack.csv")
print(by_type, "\n")

# ---- 3. The chart: a grid of attack type x detector, cell = share caught ----
labels = by_type.index.str.replace("_", " ")
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.imshow(by_type.values, cmap="Blues", vmin=0, vmax=1.4, aspect="auto")
ax.set_xticks(range(len(by_type.columns)), by_type.columns, fontsize=9)
ax.set_yticks(range(len(labels)), labels)
for i in range(by_type.shape[0]):
    for j in range(by_type.shape[1]):
        ax.text(j, i, f"{by_type.iat[i, j]:.0%}", ha="center", va="center", fontsize=10)
ax.axvline(2.5, color="white", linewidth=4)            # separate "Combined" from the parts
ax.set_title("Each detector catches a different kind of attack (share of planted attacks caught)",
             fontsize=10, loc="left")
ax.tick_params(length=0)
for spine in ax.spines.values():
    spine.set_visible(False)
plt.tight_layout()
plt.savefig("results/recall_by_attack.png", dpi=150)

# ---- 4. What the false alarms are (read these: they're your talking points)
print("Busiest false alarms:")
print(df[df.flag_any & ~df.is_attack]
      .nlargest(5, "iforest_score")[["user", "agent", "date", "calls", "tokens", "off_hours_share"]])