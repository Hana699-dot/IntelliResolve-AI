import re
from collections import defaultdict

STOPWORDS = {"the","and","for","with","from","this","that","have","has","was","are","not","unable","cannot","issue","problem","please","employee","user","my","our","in","to","of","a","an","is","it"}

def _keywords(text):
    words = re.findall(r"[a-z]{3,}", str(text).lower())
    return {w for w in words if w not in STOPWORDS}

def find_recurring_patterns(df, minimum=2):
    if df is None or df.empty:
        return []
    groups = defaultdict(list)
    for _, row in df.iterrows():
        if row.get("status") == "Resolved":
            continue
        key = str(row.get("category","Other"))
        groups[key].append(row)
    patterns = []
    for category, rows in groups.items():
        if len(rows) < minimum:
            continue
        token_sets = [_keywords(r.get("title","") + " " + r.get("description","")) for r in rows]
        common = set.intersection(*token_sets) if token_sets else set()
        # Category-level clustering intentionally surfaces possible shared service issues.
        if len(rows) >= minimum:
            theme = " ".join(sorted(common)[:4]).title() if common else f"{category} service reports"
            team_counts = {}
            for r in rows:
                team = str(r.get("assigned_team","IT Service Desk"))
                team_counts[team] = team_counts.get(team,0)+1
            team = max(team_counts, key=team_counts.get)
            patterns.append({"theme":theme,"count":len(rows),"team":team,
                             "ticket_ids":[str(r.get("ticket_id")) for r in rows[:5]]})
    return sorted(patterns,key=lambda x:x["count"],reverse=True)
