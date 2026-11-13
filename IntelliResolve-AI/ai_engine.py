import json
import re
import streamlit as st

MODEL_NAME = "gemini-2.5-flash"

def _get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""

def gemini_available():
    return bool(_get_api_key())

def _gemini_generate(prompt):
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text or ""
    except Exception as exc:
        raise RuntimeError(f"Gemini API error: {exc}") from exc

def _fallback_analysis(issue):
    text = issue.lower()
    rules = [
        (["wifi","wi-fi","internet","network","vpn","connectivity"],"Network","Network Support"),
        (["password","login","sign in","authentication","account","access"],"Access","Identity & Access Team"),
        (["email","outlook","mailbox"],"Email","Messaging Support"),
        (["laptop","keyboard","screen","hardware","slow computer"],"Hardware","Desktop Support"),
        (["software","install","application","app"],"Software","Application Support"),
    ]
    category, team = "Other", "IT Service Desk"
    for words, cat, assigned in rules:
        if any(w in text for w in words):
            category, team = cat, assigned
            break
    priority = "Medium"
    if any(w in text for w in ["urgent","important meeting","entire team","all users","production down","cannot work"]):
        priority = "High"
    if any(w in text for w in ["security breach","ransomware","data leak","server down","critical outage"]):
        priority = "Critical"
    if any(w in text for w in ["minor","when possible","not urgent"]):
        priority = "Low"
    title = issue.strip().split("\n")[0][:75] or "IT support request"
    return {"title":title,"category":category,"priority":priority,"assigned_team":team,
            "summary":issue[:220].strip()}

def analyze_issue(issue):
    prompt = f"""
You are an enterprise IT service desk triage assistant.
Analyse this employee issue and return ONLY valid JSON with keys:
title (short, max 80 chars), category (one of Network, Access, Email, Hardware, Software, Security, Other),
priority (one of Critical, High, Medium, Low), assigned_team (short team name), summary (one or two sentences).
Priority guidance: Critical = security incident or major service outage; High = employee blocked or time-sensitive;
Medium = normal disruption; Low = minor request. Do not invent facts.
Issue: {issue}
"""
    try:
        raw = _gemini_generate(prompt)
        if raw:
            cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            data = json.loads(cleaned)
            fallback = _fallback_analysis(issue)
            return {
                "title":str(data.get("title") or fallback["title"])[:80],
                "category":data.get("category") if data.get("category") in ["Network","Access","Email","Hardware","Software","Security","Other"] else fallback["category"],
                "priority":data.get("priority") if data.get("priority") in ["Critical","High","Medium","Low"] else fallback["priority"],
                "assigned_team":str(data.get("assigned_team") or fallback["assigned_team"])[:60],
                "summary":str(data.get("summary") or fallback["summary"])[:400],
            }
    except Exception as exc:
        st.warning(f"Gemini unavailable; using local rule-based triage. Details: {exc}")
    return _fallback_analysis(issue)

def generate_answer(issue, documents, analysis):
    context = "\n\n".join([f"ARTICLE: {d['title']}\n{d['content']}" for d in documents])
    if not context:
        context = "No matching internal knowledge articles were found."
    prompt = f"""
You are IntelliResolve, a helpful enterprise IT support assistant.
Use the knowledge articles below as the primary source. Give clear, numbered troubleshooting steps.
If the articles do not contain enough information, say so and recommend contacting the assigned support team.
Never claim you have performed an action. Do not ask for passwords, MFA codes or sensitive information.
At the end, mention that an incident can be created if the problem remains unresolved.
Employee issue: {issue}
Triage: {analysis}
Knowledge articles:
{context}
"""
    try:
        answer = _gemini_generate(prompt)
        if answer:
            return answer
    except Exception as exc:
        st.warning(f"Gemini response failed; showing knowledge-based guidance. Details: {exc}")
    if documents:
        doc = documents[0]
        return (f"### Suggested troubleshooting\nBased on **{doc['title']}**:\n\n{doc['content']}\n\n"
                f"If the issue continues, contact **{analysis['assigned_team']}** or create an incident ticket.")
    return f"I couldn't find a matching knowledge article. Please contact {analysis['assigned_team']} for further assistance."
