"""assembly-bills explorer -- interactive Streamlit app."""

import os
import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


st.set_page_config(
    page_title="assembly-bills",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Minimal CSS matching the monospace / dim aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&display=swap');

    .stApp { font-family: 'IBM Plex Mono', monospace; }
    h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; font-weight: 500; }

    .bill-card {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
        background: #fafafa;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.6;
    }
    .bill-card .label { color: #999; }
    .bill-card .value { color: #222; }

    .propose-reason {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 1.2rem 1.4rem;
        background: #f8f9fa;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        line-height: 1.8;
        white-space: pre-wrap;
        max-height: 500px;
        overflow-y: auto;
    }

    .stat-box {
        text-align: center;
        padding: 1rem;
        border: 1px solid #eee;
        border-radius: 4px;
    }
    .stat-box .number { font-size: 1.8rem; font-weight: 500; color: #222; }
    .stat-box .label { font-size: 0.75rem; color: #999; text-transform: uppercase; }

    div[data-testid="stSidebar"] { font-family: 'IBM Plex Mono', monospace; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

DATA_DIR = os.environ.get("ASSEMBLY_BILLS_DATA", os.path.join(os.path.dirname(__file__), "data"))


@st.cache_data
def load_bills():
    return pd.read_parquet(os.path.join(DATA_DIR, "bills.parquet"))


@st.cache_data
def load_texts():
    return pd.read_parquet(os.path.join(DATA_DIR, "bill_texts.parquet"))


@st.cache_data
def load_proposers():
    return pd.read_parquet(os.path.join(DATA_DIR, "proposers.parquet"))


@st.cache_data
def load_mp_metadata():
    return pd.read_parquet(os.path.join(DATA_DIR, "mp_metadata.parquet"))


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.markdown("### assembly-bills")
st.sidebar.markdown(
    "<span style='color:#999;font-size:0.8rem;'>"
    "Korean National Assembly Bills Dataset<br>"
    "20th-22nd Assembly &middot; 60,925 bills"
    "</span>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "navigate",
    ["overview", "search", "bill detail", "MP lookup", "statistics"],
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

bills = load_bills()
texts = load_texts()


def page_overview():
    st.markdown("## assembly-bills")
    st.markdown(
        "<span style='color:#999;'>60,925 member-proposed bills from the 20th-22nd Korean National Assembly, "
        "with full propose-reason texts scraped from the legislative information system.</span>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    c1, c2, c3, c4 = st.columns(4)
    has_text = (texts["scrape_status"] == "ok").sum()
    for col, num, label in [
        (c1, f"{len(bills):,}", "total bills"),
        (c2, f"{has_text:,}", "with text"),
        (c3, "3", "assemblies"),
        (c4, f"{bills['COMMITTEE'].nunique()}", "committees"),
    ]:
        col.markdown(
            f"<div class='stat-box'><div class='number'>{num}</div>"
            f"<div class='label'>{label}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.markdown("### bills by year")
    bills_copy = bills.copy()
    bills_copy["year"] = pd.to_datetime(bills_copy["PROPOSE_DT"]).dt.year
    yearly = bills_copy.groupby("year").size().reset_index(name="count")
    fig = px.bar(
        yearly, x="year", y="count",
        color_discrete_sequence=["#4a4a4a"],
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="IBM Plex Mono", size=12),
        xaxis=dict(title="", tickmode="linear", dtick=1),
        yaxis=dict(title="", gridcolor="#eee"),
        margin=dict(l=40, r=20, t=20, b=40),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### bills by assembly")
    age_counts = bills.groupby("AGE").size().reset_index(name="count")
    age_counts["AGE"] = age_counts["AGE"].apply(ordinal)
    fig2 = px.bar(
        age_counts, x="AGE", y="count",
        color_discrete_sequence=["#4a4a4a"],
    )
    fig2.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Mono", size=12),
        xaxis_title="", yaxis_title="",
        yaxis=dict(gridcolor="#eee"),
        margin=dict(l=40, r=20, t=20, b=40),
        height=260,
    )
    st.plotly_chart(fig2, use_container_width=True)


def page_search():
    st.markdown("## search bills")

    col1, col2, col3 = st.columns([3, 1, 1])
    keyword = col1.text_input("keyword", placeholder="e.g. 인공지능, 부동산, 데이터")
    age_filter = col2.selectbox("assembly", [None, 20, 21, 22], format_func=lambda x: "all" if x is None else ordinal(x))
    search_text = col3.checkbox("search in text", value=False)

    if not keyword:
        st.markdown("<span style='color:#999;'>enter a keyword to search bill names</span>", unsafe_allow_html=True)
        return

    mask = bills["BILL_NAME"].str.contains(keyword, case=False, na=False)

    if search_text:
        text_mask = texts.set_index("BILL_ID")["propose_reason"].str.contains(keyword, case=False, na=False)
        text_ids = set(text_mask[text_mask].index)
        mask = mask | bills["BILL_ID"].isin(text_ids)

    if age_filter:
        mask = mask & (bills["AGE"] == age_filter)

    results = bills[mask].copy()
    st.markdown(f"<span style='color:#999;'>{len(results):,} results</span>", unsafe_allow_html=True)

    if results.empty:
        return

    display_cols = ["AGE", "BILL_NO", "PROPOSE_DT", "COMMITTEE", "BILL_NAME", "PROPOSER"]
    st.dataframe(
        results[display_cols].head(100).rename(columns={
            "AGE": "assembly", "BILL_NO": "bill_no", "PROPOSE_DT": "date",
            "COMMITTEE": "committee", "BILL_NAME": "bill_name", "PROPOSER": "proposer",
        }),
        use_container_width=True,
        hide_index=True,
        height=500,
    )


def page_bill_detail():
    st.markdown("## bill detail")

    bill_input = st.text_input("BILL_NO or BILL_ID", placeholder="e.g. 2124567")

    if not bill_input:
        st.markdown("<span style='color:#999;'>enter a bill number to view details</span>", unsafe_allow_html=True)
        return

    if bill_input.startswith("PRC_"):
        row = bills[bills["BILL_ID"] == bill_input]
    else:
        row = bills[bills["BILL_NO"].astype(str) == bill_input]

    if row.empty:
        st.warning(f"bill not found: {bill_input}")
        return

    row = row.iloc[0]
    bill_id = row["BILL_ID"]

    meta_html = "<div class='bill-card'>"
    for label, value in [
        ("bill_id", bill_id),
        ("bill_no", row["BILL_NO"]),
        ("name", row["BILL_NAME"]),
        ("assembly", ordinal(row['AGE'])),
        ("date", row["PROPOSE_DT"]),
        ("committee", row["COMMITTEE"]),
        ("proposer", row["PROPOSER"]),
        ("result", row["PROC_RESULT"]),
    ]:
        meta_html += f"<span class='label'>{label}</span>  <span class='value'>{value}</span><br>"
    meta_html += "</div>"
    st.markdown(meta_html, unsafe_allow_html=True)

    # Propose reason
    text_row = texts[texts["BILL_ID"] == bill_id]
    if not text_row.empty and pd.notna(text_row.iloc[0]["propose_reason"]):
        reason = text_row.iloc[0]["propose_reason"]
        st.markdown("### propose reason")
        st.markdown(f"<div class='propose-reason'>{reason}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:#999;'>no propose-reason text available</span>", unsafe_allow_html=True)

    # Proposers
    prop = load_proposers()
    bill_prop = prop[prop["BILL_ID"] == bill_id]
    if not bill_prop.empty:
        lead = bill_prop[bill_prop["REP_DIV"].notna()]
        cospon = bill_prop[bill_prop["REP_DIV"].isna()]
        st.markdown("### proposers")
        if not lead.empty:
            lead_str = ", ".join(f"**{r['PPSR_NM']}** ({r['PPSR_POLY_NM']})" for _, r in lead.iterrows())
            st.markdown(f"lead: {lead_str}")
        st.markdown(f"co-sponsors: {len(cospon)} members")
        if not cospon.empty:
            with st.expander("show all co-sponsors"):
                st.dataframe(
                    cospon[["PPSR_NM", "PPSR_POLY_NM"]].rename(
                        columns={"PPSR_NM": "name", "PPSR_POLY_NM": "party"}
                    ),
                    hide_index=True,
                    use_container_width=True,
                )


def page_mp_lookup():
    st.markdown("## MP lookup")

    mp_name = st.text_input("MP name", placeholder="e.g. 이재명")
    if not mp_name:
        st.markdown("<span style='color:#999;'>enter an MP name to look up</span>", unsafe_allow_html=True)
        return

    mp_df = load_mp_metadata()
    mask = mp_df["HG_NM"].str.contains(mp_name, case=False, na=False)
    matches = mp_df[mask]

    if matches.empty:
        st.warning(f"no MP found: '{mp_name}'")
        return

    for _, m in matches.iterrows():
        party = m.get("POLY_NM", "")
        district = m.get("ORIG_NM", "")
        seniority = m.get("REELE_GBN_NM", "")
        cmit = m.get("CMIT_NM", "")

        meta_html = (
            f"<div class='bill-card'>"
            f"<span class='label'>name</span>  <span class='value'><b>{m['HG_NM']}</b> ({m.get('ENG_NM', '')})</span><br>"
            f"<span class='label'>assembly</span>  <span class='value'>{ordinal(m['_age'])}</span><br>"
            f"<span class='label'>party</span>  <span class='value'>{party}</span><br>"
            f"<span class='label'>district</span>  <span class='value'>{district}</span><br>"
            f"<span class='label'>seniority</span>  <span class='value'>{seniority}</span><br>"
            f"<span class='label'>committee</span>  <span class='value'>{cmit}</span><br>"
            f"</div>"
        )
        st.markdown(meta_html, unsafe_allow_html=True)

    # Bills
    prop = load_proposers()
    lead_bills = prop[(prop["PPSR_NM"] == mp_name) & (prop["REP_DIV"].notna())]
    if not lead_bills.empty:
        led = bills[bills["BILL_ID"].isin(lead_bills["BILL_ID"])].sort_values("PROPOSE_DT", ascending=False)
        st.markdown(f"### {len(led):,} bills led by {mp_name}")
        st.dataframe(
            led[["AGE", "BILL_NO", "PROPOSE_DT", "COMMITTEE", "BILL_NAME"]].rename(columns={
                "AGE": "assembly", "BILL_NO": "bill_no", "PROPOSE_DT": "date",
                "COMMITTEE": "committee", "BILL_NAME": "bill_name",
            }),
            use_container_width=True,
            hide_index=True,
            height=400,
        )


def page_statistics():
    st.markdown("## statistics")

    tab1, tab2, tab3 = st.tabs(["by party", "by committee", "text length"])

    with tab1:
        prop = load_proposers()
        lead = prop[prop["REP_DIV"].notna()].drop_duplicates("BILL_ID")
        party_counts = lead["PPSR_POLY_NM"].value_counts().head(15).reset_index()
        party_counts.columns = ["party", "count"]
        fig = px.bar(
            party_counts, x="count", y="party", orientation="h",
            color_discrete_sequence=["#4a4a4a"],
        )
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="IBM Plex Mono", size=12),
            xaxis_title="", yaxis_title="",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(gridcolor="#eee"),
            margin=dict(l=20, r=20, t=20, b=40),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        cmit_counts = bills["COMMITTEE"].value_counts().head(20).reset_index()
        cmit_counts.columns = ["committee", "count"]
        fig = px.bar(
            cmit_counts, x="count", y="committee", orientation="h",
            color_discrete_sequence=["#4a4a4a"],
        )
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="IBM Plex Mono", size=12),
            xaxis_title="", yaxis_title="",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(gridcolor="#eee"),
            margin=dict(l=20, r=20, t=20, b=40),
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        text_lens = texts.loc[texts["propose_reason"].notna(), "propose_reason"].str.len()
        fig = px.histogram(
            text_lens, nbins=80,
            color_discrete_sequence=["#4a4a4a"],
            labels={"value": "characters", "count": "bills"},
        )
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="IBM Plex Mono", size=12),
            xaxis_title="text length (chars)", yaxis_title="count",
            yaxis=dict(gridcolor="#eee"),
            margin=dict(l=40, r=20, t=20, b=40),
            height=350,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("median", f"{text_lens.median():.0f}")
        c2.metric("mean", f"{text_lens.mean():.0f}")
        c3.metric("max", f"{text_lens.max():,}")


# Router
{
    "overview": page_overview,
    "search": page_search,
    "bill detail": page_bill_detail,
    "MP lookup": page_mp_lookup,
    "statistics": page_statistics,
}[page]()
