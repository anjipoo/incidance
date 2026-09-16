import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Incident Resolver", layout="wide")

page = st.sidebar.radio("Navigate", ["Analyze Incident", "History"])


def render_analysis(result: dict) -> None:
    st.subheader("Incident Analysis")

    col1, col2, col3 = st.columns(3)
    col1.metric("Category", result["category"].capitalize())
    col2.metric("Severity", result["severity"].upper())
    col3.metric("Estimated Confidence", f"{result['confidence'] * 100:.0f}%")

    st.caption(
        "Confidence is an estimated score blending retrieval similarity, "
        "classifier agreement, and the model's own assessment — not a "
        "scientifically calibrated probability."
    )

    st.markdown("**Likely Root Cause**")
    st.write(result["root_cause"])

    st.markdown("**Recommended Actions**")
    for i, action in enumerate(result["recommended_actions"], start=1):
        st.write(f"{i}. {action}")

    st.markdown("**Similar Historical Incidents**")
    st.caption("Retrieved as supporting context — not guaranteed to be the same issue.")
    for incident in result["similar_incidents"]:
        st.write(f"- {incident['log']}  \n  Similarity: {incident['similarity'] * 100:.0f}%")


def analyze_page() -> None:
    st.title("AI Incident Resolver")
    st.write("Analyze application errors using semantic retrieval + Gemini.")

    log_input = st.text_area(
        "Paste your incident log",
        height=150,
        placeholder="ERROR 2026-09-16 14:32:10\nConnection refused...\nRetry attempt 3/3 failed",
    )

    if st.button("🔍 Resolve Incident", type="primary"):
        if not log_input.strip():
            st.error("Please paste a log before analyzing.")
            return

        with st.spinner("Analyzing incident..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/incidents/analyze",
                    json={"log": log_input},
                    timeout=60,
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the backend API. Is `uvicorn backend.main:app --reload` running?")
                return

        if response.status_code == 200:
            render_analysis(response.json())
        elif response.status_code == 400:
            st.error(f"Invalid input: {response.json().get('detail')}")
        elif response.status_code == 502:
            st.error(f"Analysis failed: {response.json().get('detail')}")
        else:
            st.error(f"Unexpected error (HTTP {response.status_code}): {response.text}")


def history_page() -> None:
    st.title("Incident History")

    try:
        response = requests.get(f"{API_BASE_URL}/incidents", timeout=10)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend API. Is `uvicorn backend.main:app --reload` running?")
        return

    if response.status_code != 200:
        st.error(f"Failed to load history (HTTP {response.status_code})")
        return

    incidents = response.json()
    if not incidents:
        st.info("No incidents analyzed yet.")
        return

    table_data = [
        {
            "ID": i["id"],
            "Timestamp": i["timestamp"],
            "Category": i["category"],
            "Severity": i["severity"],
            "Root Cause": i["root_cause"],
        }
        for i in incidents
    ]
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.markdown("---")
    selected_id = st.selectbox(
        "Select an incident to inspect",
        options=[i["id"] for i in incidents],
    )

    if selected_id:
        detail_response = requests.get(f"{API_BASE_URL}/incidents/{selected_id}", timeout=10)
        if detail_response.status_code == 200:
            detail = detail_response.json()
            st.subheader(f"Incident #{detail['id']}")
            st.write(f"**Timestamp:** {detail['timestamp']}")
            st.write(f"**Category:** {detail['category']}  |  **Severity:** {detail['severity']}")
            st.write(f"**Confidence:** {detail['confidence'] * 100:.0f}%")
            st.markdown("**Root Cause**")
            st.write(detail["root_cause"])
            st.markdown("**Recommended Actions**")
            for i, action in enumerate(detail["recommended_actions"], start=1):
                st.write(f"{i}. {action}")
            with st.expander("Raw log"):
                st.code(detail["raw_log"])


if page == "Analyze Incident":
    analyze_page()
else:
    history_page()