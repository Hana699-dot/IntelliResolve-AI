from pathlib import Path
import re

KB_DIR = Path(__file__).parent / "knowledge_base"

def load_articles():
    articles = []
    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        title = lines[0].replace("#","").strip() if lines else path.stem
        category = path.stem.replace("_"," ").title()
        content = "\n".join(lines[1:]).strip()
        articles.append({"title":title,"category":category,"content":content,"source":path.name})
    return articles

def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def retrieve_knowledge(query, top_k=4):
    query_tokens = _tokens(query)
    scored = []
    for article in load_articles():
        body = article["title"] + " " + article["category"] + " " + article["content"]
        tokens = _tokens(body)
        overlap = len(query_tokens & tokens)
        score = overlap / max(len(query_tokens), 1)
        if score > 0:
            scored.append((score, article))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]
