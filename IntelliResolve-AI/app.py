import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from database import init_db, create_ticket, get_tickets, update_ticket, get_ticket_stats
from ai_engine import analyze_issue, generate_answer, gemini_available
from rag_engine import retrieve_knowledge
from incident_engine import find_recurring_patterns

st.set_page_config(page_title="IntelliResolve AI", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .main-header {font-size:2.1rem;font-weight:750;letter-spacing:-1px;}
    .sub-header {color:#9aa4b2;margin-top:-12px;}
    .metric-card {background:linear-gradient(135deg,#17243a,#202f49);padding:18px;border-radius:14px;border:1px solid #34445e;}
    div[data-testid="stMetric"] {background:#17243a;padding:14px;border-radius:12px;border:1px solid #34445e;}
    .stButton>button {border-radius:9px;}
</style>
""", unsafe_allow_html=True)

init_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_analysis" not in st.session_state:
    st.session_state.pending_analysis = None
if "pending_issue" not in st.session_state:
    st.session_state.pending_issue = ""

def status_badge(status):
    return {"Open":"🟠 Open","In Progress":"🔵 In Progress","Resolved":"🟢 Resolved","Escalated":"🔴 Escalated"}.get(status, status)

st.sidebar.markdown("## 🧠 IntelliResolve AI")
st.sidebar.caption("Intelligent IT Service Desk")
st.sidebar.divider()
page = st.sidebar.radio(
    "NAVIGATION",
    ["Overview", "AI Support Assistant", "Create Incident", "Manage Tickets", "Incident Intelligence", "Knowledge Base"],
)
st.sidebar.divider()
if gemini_available():
    st.sidebar.success("Gemini API connected")
else:
    st.sidebar.warning("Demo mode · Gemini key not configured")
st.sidebar.caption("HCLTech USM + Generative AI portfolio project")

tickets = get_tickets()

if page == "Overview":
    st.markdown('<div class="main-header">IT Service Desk Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Monitor incidents, service health and AI-assisted support operations.</div>', unsafe_allow_html=True)
    stats = get_ticket_stats()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total incidents", stats["total"])
    c2.metric("Open incidents", stats["open"])
    c3.metric("Resolved", stats["resolved"])
    c4.metric("High / Critical", stats["high"])
    st.write("")
    left,right = st.columns([1.35,1])
    with left:
        st.subheader("Recent incidents")
        if tickets.empty:
            st.info("No incidents yet. Create a ticket or use the AI assistant.")
        else:
            view = tickets.head(8)[["ticket_id","title","category","priority","status","created_at"]].copy()
            view.columns = ["Ticket","Issue","Category","Priority","Status","Created"]
            st.dataframe(view, use_container_width=True, hide_index=True)
    with right:
        st.subheader("Incident distribution")
        if tickets.empty:
            st.info("Charts will appear when incidents are created.")
        else:
            chart_data = tickets.groupby("priority").size().reset_index(name="count")
            fig = px.pie(chart_data, names="priority", values="count", hole=.55,
                         color="priority", color_discrete_map={"Critical":"#e05252","High":"#f59e0b","Medium":"#3b82f6","Low":"#22a06b"})
            fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
    st.subheader("Service desk activity")
    if not tickets.empty:
        trend = tickets.copy()
        trend["day"] = pd.to_datetime(trend["created_at"]).dt.date
        daily = trend.groupby("day").size().reset_index(name="incidents")
        fig2 = px.bar(daily, x="day", y="incidents", title="Incidents created by day")
        st.plotly_chart(fig2, use_container_width=True)
    st.caption("Prototype data is stored locally in SQLite. Connect a ServiceNow instance to replace the simulated ticket workflow.")

elif page == "AI Support Assistant":
    st.markdown('<div class="main-header">AI Support Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Describe an IT issue in plain language. IntelliResolve finds relevant guidance and prepares an incident.</div>', unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Example: I cannot connect to office Wi-Fi and my meeting starts in 10 minutes...")
    if prompt:
        st.session_state.chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        docs = retrieve_knowledge(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Understanding the issue and searching support knowledge..."):
                analysis = analyze_issue(prompt)
                answer = generate_answer(prompt, docs, analysis)
            st.markdown(answer)
            st.markdown("**Detected incident details**")
            a,b,c = st.columns(3)
            a.metric("Category", analysis["category"])
            b.metric("Priority", analysis["priority"])
            c.metric("Support team", analysis["assigned_team"])
            st.session_state.pending_analysis = analysis
            st.session_state.pending_issue = prompt
        st.session_state.chat_history.append({"role":"assistant","content":answer})
    if st.session_state.pending_analysis:
        st.info("The latest conversation has been analysed. You can create an incident using the detected details.")
        if st.button("Create incident from latest conversation", type="primary", key="create_from_chat"):
            analysis = st.session_state.pending_analysis
            ticket_id = create_ticket(
                title=analysis["title"], description=st.session_state.pending_issue,
                category=analysis["category"], priority=analysis["priority"],
                assigned_team=analysis["assigned_team"], status="Open",
                ai_summary=analysis["summary"]
            )
            st.success(f"Incident {ticket_id} created successfully.")
            st.session_state.pending_analysis = None
            st.session_state.pending_issue = ""
    if st.session_state.chat_history and st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()

elif page == "Create Incident":
    st.markdown('<div class="main-header">Create an Incident</div>', unsafe_allow_html=True)
    st.write("Enter an employee issue. AI can classify it and suggest routing.")
    with st.form("incident_form"):
        employee = st.text_input("Employee name", placeholder="e.g. Priya Kumar")
        title = st.text_input("Short description", placeholder="Unable to access company email")
        description = st.text_area("Detailed description", height=130, placeholder="Describe what happened, when it started and any error message...")
        use_ai = st.checkbox("Use Gemini AI to classify and route this incident", value=True)
        submitted = st.form_submit_button("Analyse and create ticket", type="primary")
    if submitted:
        if not title.strip() or not description.strip():
            st.error("Please provide both a short description and detailed description.")
        else:
            with st.spinner("Analysing incident..."):
                analysis = analyze_issue(title + ". " + description) if use_ai else {
                    "title": title, "category":"Other", "priority":"Medium",
                    "assigned_team":"IT Service Desk", "summary":description[:250]
                }
            ticket_id = create_ticket(
                title=title, description=f"Employee: {employee or 'Not provided'}\n{description}",
                category=analysis["category"], priority=analysis["priority"],
                assigned_team=analysis["assigned_team"], status="Open", ai_summary=analysis["summary"]
            )
            st.success(f"Incident created: {ticket_id}")
            st.write({"Category":analysis["category"],"Priority":analysis["priority"],"Assigned team":analysis["assigned_team"]})

elif page == "Manage Tickets":
    st.markdown('<div class="main-header">Incident Management</div>', unsafe_allow_html=True)
    tickets = get_tickets()
    if tickets.empty:
        st.info("No incidents found. Create one from the assistant or incident form.")
    else:
        f1,f2 = st.columns(2)
        status_filter = f1.selectbox("Filter by status", ["All"] + sorted(tickets["status"].unique().tolist()))
        priority_filter = f2.selectbox("Filter by priority", ["All","Critical","High","Medium","Low"])
        filtered = tickets.copy()
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]
        if priority_filter != "All":
            filtered = filtered[filtered["priority"] == priority_filter]
        st.dataframe(filtered[["ticket_id","title","category","priority","assigned_team","status","created_at"]],
                     use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("Update an incident")
        selected = st.selectbox("Select ticket", tickets["ticket_id"].tolist())
        row = tickets[tickets["ticket_id"] == selected].iloc[0]
        with st.form("update_ticket_form"):
            new_status = st.selectbox("Status", ["Open","In Progress","Resolved","Escalated"],
                                      index=["Open","In Progress","Resolved","Escalated"].index(row["status"]))
            new_team = st.text_input("Assigned team", value=row["assigned_team"])
            resolution = st.text_area("Resolution notes", value=row.get("resolution_notes","") or "")
            save = st.form_submit_button("Save changes")
        if save:
            update_ticket(selected, new_status, new_team, resolution)
            st.success(f"{selected} updated.")
            st.rerun()
        with st.expander("View selected incident details"):
            st.write("**Description**")
            st.write(row["description"])
            st.write("**AI summary**")
            st.write(row["ai_summary"] or "Not available")
            st.write("**Resolution notes**")
            st.write(row["resolution_notes"] or "Not resolved yet")

elif page == "Incident Intelligence":
    st.markdown('<div class="main-header">Incident Memory & Prevention</div>', unsafe_allow_html=True)
    st.markdown("Detect repeated reports that may indicate a shared service problem.")
    patterns = find_recurring_patterns(get_tickets())
    if not patterns:
        st.success("No recurring incident clusters detected yet. Add multiple similar incidents to test this feature.")
    else:
        for p in patterns:
            with st.container(border=True):
                st.markdown(f"**Potential common issue: {p['theme']}**")
                st.write(f"{p['count']} similar incidents · Suggested team: {p['team']}")
                st.write("Example tickets: " + ", ".join(p["ticket_ids"]))
                st.warning("AI-assisted signal only. An administrator should verify the root cause before declaring a major incident.")
    st.subheader("How the prevention engine works")
    st.write("The prototype compares issue descriptions using keyword overlap and category. Similar reports are grouped to help the service desk spot patterns. It does not claim to diagnose infrastructure automatically.")

elif page == "Knowledge Base":
    st.markdown('<div class="main-header">IT Knowledge Base</div>', unsafe_allow_html=True)
    st.write("Search the local troubleshooting articles used by the AI assistant.")
    query = st.text_input("Search knowledge articles", placeholder="e.g. Wi-Fi, password, VPN, email")
    docs = retrieve_knowledge(query, top_k=10) if query else retrieve_knowledge("common IT support issues", top_k=10)
    for doc in docs:
        with st.expander(doc["title"]):
            st.write(doc["content"])
            st.caption(f"Category: {doc['category']} · Source: Local demo knowledge base")

st.sidebar.caption("Prototype · Human approval required for sensitive actions")
