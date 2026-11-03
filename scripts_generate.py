"""Regenerate fully synthetic CSV fixtures; deterministic and no external data."""
import csv
import random
from pathlib import Path

root = Path(__file__).parent / "samples"
root.mkdir(exist_ok=True)
rng = random.Random(20261103)
base = []
for i in range(180):
    age = 21 + (i * 17 % 40)
    income = 24000 + (i * 1741 % 65000)
    channel = ["organic", "ads", "referral", "organic", "organic"][i % 5]
    label = "yes" if (age + income // 5000) % 3 == 0 else "no"
    pred = label if i % 12 else ("no" if label == "yes" else "yes")
    base.append({"age": age, "income": income, "channel": channel, "label": label, "prediction": pred})
clean = [dict(row) for row in base]
rng.shuffle(clean)
shifted = []
for i, row in enumerate(base):
    r = dict(row)
    r["age"] = int(r["age"]) + 32
    r["income"] = int(r["income"]) * 2
    r["channel"] = "partner" if i % 2 == 0 else "ads"
    if i % 5 == 0:
        r["income"] = ""
    if i % 3 == 0:
        r["prediction"] = "yes" if r["label"] == "no" else "no"
    shifted.append(r)
for name, rows in (("baseline", base), ("clean", clean), ("shifted", shifted)):
    with (root / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["age", "income", "channel", "label", "prediction"])
        writer.writeheader()
        writer.writerows(rows)
print("Wrote 3 synthetic CSVs, 180 rows each")
