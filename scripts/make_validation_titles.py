import pandas as pd
rows = []
for f in ["data/movies.csv", "data/movies_adult.csv"]:
    df = pd.read_csv(f)
    rows += [f"{r.title},{r.year}" for r in df.itertuples()]
open("validation_titles.txt", "w", encoding="utf-8").write("\n".join(rows))
print(f"wrote validation_titles.txt ({len(rows)} films)")
