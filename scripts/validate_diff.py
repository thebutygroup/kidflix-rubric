import json
import pandas as pd
DIMS = ["wealth", "agency", "core", "music", "inclusion", "romance"]
hand = pd.concat([pd.read_csv("data/movies.csv"), pd.read_csv("data/movies_adult.csv")])
api = pd.read_csv("validation_scores.csv")
m = hand.merge(api, on="title", suffixes=("_hand", "_api"))
print(f"matched {len(m)}/{len(hand)} films\n")
for d in DIMS:
    delta = (m[d + "_api"] - m[d + "_hand"])
    print(f"{d:>10}: mean abs delta {delta.abs().mean():.1f}  "
          f"| api higher on {(delta > 0).sum()}, lower on {(delta < 0).sum()}")
m["total_hand"] = m[[d + "_hand" for d in DIMS]].sum(axis=1)
m["total_api"] = m[[d + "_api" for d in DIMS]].sum(axis=1)
m["dtotal"] = m["total_api"] - m["total_hand"]
print(f"\ntotal: mean abs delta {m.dtotal.abs().mean():.1f}, max {m.dtotal.abs().max()}")
print("\nBiggest disagreements:")
cols = ["title", "total_hand", "total_api", "dtotal"]
print(m.reindex(m.dtotal.abs().sort_values(ascending=False).index)[cols].head(12).to_string(index=False))
m.to_csv("validation_diff.csv", index=False)
print("\nfull diff written to validation_diff.csv")
