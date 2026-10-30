import sqlite3
import json
import pandas as pd
import streamlit as st

DB_PATH = "data/scholarships.db"

st.set_page_config(
    page_title="Scholarship Intelligence Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Atlas Funding: Scholarship Intelligence Platform")
st.markdown("Automated pipeline for tracking, verifying, and scoring authentic Indian scholarship schemes.")

def get_connection():
    return sqlite3.connect(DB_PATH)

# Fetch stats and data
try:
    conn = get_connection()
    df_scholarships = pd.read_sql_query("SELECT * FROM scholarships", conn)
    df_history = pd.read_sql_query("SELECT * FROM scholarship_history ORDER BY detected_at DESC", conn)
    conn.close()
except Exception as e:
    st.error(f"Error loading database: {e}. Please run `python src/crawler.py` first.")
    st.stop()

# --- TOP METRICS CARDS ---
total_count = len(df_scholarships)
verified_count = len(df_scholarships[df_scholarships["verification_status"] == "VERIFIED"])
high_confidence_count = len(df_scholarships[df_scholarships["confidence_score"] >= 95.0])
stale_count = len(df_scholarships[df_scholarships["is_stale"] == 1])
updates_logged = len(df_history)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Records", total_count, help="Required: 20+")
col2.metric("Verified (Official)", verified_count, help="Required: 15+")
col3.metric("High Confidence (≥95%)", high_confidence_count, help="Required: 10+")
col4.metric("Stale Schemes", stale_count, help="Required: 2+")
col5.metric("Changes Tracked", updates_logged, help="Required: 2+")

st.divider()

# --- TABS FOR NAVIGATION ---
tab_directory, tab_audit, tab_breakdown = st.tabs(["📋 Scholarship Directory", "🔄 Change Detection Audit", "📊 Verification Breakdown"])

with tab_directory:
    st.subheader("Active & Monitored Scholarships")
    
    # Filter controls
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        status_filter = st.multiselect("Verification Status", options=df_scholarships["verification_status"].unique(), default=df_scholarships["verification_status"].unique())
    with f_col2:
        category_filter = st.multiselect("Category", options=df_scholarships["category"].unique(), default=df_scholarships["category"].unique())
    with f_col3:
        search_query = st.text_input("Search by Name or Keyword", "")

    # Apply filters
    filtered_df = df_scholarships[
        (df_scholarships["verification_status"].isin(status_filter)) &
        (df_scholarships["category"].isin(category_filter))
    ]
    if search_query:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search_query, case=False, na=False) |
            filtered_df["organization"].str.contains(search_query, case=False, na=False)
        ]

    # Display Table
    cols_to_show = [
        "name", "organization", "category", "confidence_score",
        "verification_status", "application_deadline", "financial_benefit"
    ]
    st.dataframe(
        filtered_df[cols_to_show],
        use_container_width=True,
        hide_index=True
    )

    # Detailed record view
    selected_name = st.selectbox("Select a scholarship to inspect full details and evidence trace:", options=df_scholarships["name"].values)
    if selected_name:
        row = df_scholarships[df_scholarships["name"] == selected_name].iloc[0]
        st.write(f"### {row['name']}")
        
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.write(f"**Organization:** {row['organization']}")
            st.write(f"**Target Group:** {row['target_group']}")
            st.write(f"**Academic Criteria:** {row['academic_criteria']}")
            st.write(f"**Income Ceiling:** {row['family_income_limit']}")
            st.write(f"**Application Mode:** {row['application_mode']}")
        with d_col2:
            st.write(f"**Confidence Score:** {row['confidence_score']}%")
            st.write(f"**Verification Status:** `{row['verification_status']}`")
            st.write(f"**Primary Official Source:** [{row['primary_source_url']}]({row['primary_source_url']})")
            st.write(f"**Documents Required:** {row['documents_required']}")
            st.write(f"**Stale Flag:** {'Yes (Expired)' if row['is_stale'] == 1 else 'No (Active)'}")

        # Raw evidence quote trace
        st.markdown("**Evidence Trace & Quote:**")
        try:
            evidence = json.loads(row["raw_evidence_trace"])
            st.json(evidence)
        except Exception:
            st.write(row["raw_evidence_trace"])

with tab_audit:
    st.subheader("Multi-Run Change Detection Log")
    st.markdown("Shows records where deadlines, benefits, or criteria changed between crawler runs.")
    if len(df_history) == 0:
        st.info("No updates detected yet.")
    else:
        st.dataframe(
            df_history[["scholarship_name", "field_name", "old_value", "new_value", "detected_at"]],
            use_container_width=True,
            hide_index=True
        )

with tab_breakdown:
    st.subheader("Authenticity Metrics")
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Confidence Score Distribution")
        st.bar_chart(df_scholarships["confidence_score"].value_counts().sort_index())
    with c2:
        st.write("#### Schemes by Category")
        st.bar_chart(df_scholarships["category"].value_counts())