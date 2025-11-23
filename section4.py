"""
Section 4: Other Sources (Online, YouTube, Social, Messengers)
"""
import streamlit as st
import pandas as pd
import altair as alt
from filters import render_filters
from mappings import (
    O12_SOURCES_MAP,
    O1_YOUTUBE_REGULAR_MAP,
    O2_YOUTUBE_CONTENT_MAP,
    O3_SOCIAL_NETWORKS_MAP,
    O3_1_SOCIAL_BEHAVIOR_MAP,
    O4_MESSENGERS_MAP,
    O4_1_MESSENGER_BEHAVIOR_MAP
)

# ----------------------
# Helper functions (reused/adapted)
# ----------------------

def show_note():
    """Global note about refusals."""
    st.markdown(
        "<i>Ընդհանուր %-ը կարող է չլինել 100, քանի որ հարցից հրաժարումների %-ները ներկայացված չեն։</i>",
        unsafe_allow_html=True
    )

def show_table_expander(tab: pd.DataFrame, filename: str):
    """Show table inside expander with download button."""
    with st.expander("Բացել աղյուսակը"):
        st.dataframe(tab, use_container_width=True)
        csv = tab.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Ներբեռնել CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )

def freq_single(df: pd.DataFrame, col: str, mapping: dict | None = None,
                exclude_values: set | None = None) -> pd.DataFrame:
    """Build frequency table for single-answer question."""
    if col not in df.columns:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    series = df[col].copy()
    
    if exclude_values is not None:
        series = series[~series.isin(exclude_values)]

    if mapping is not None:
        series = series.map(mapping).fillna(series.astype(str))

    if series.empty:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    tab = series.value_counts().reset_index()
    tab.columns = ["answer", "count"]
    tab = tab[tab["count"] > 0]
    tab["percent"] = tab["count"] / tab["count"].sum() * 100
    tab["percent"] = tab["percent"].round(1)
    return tab

def freq_multi(df: pd.DataFrame, cols: list[str], labels: dict[str, str]) -> pd.DataFrame:
    """Build frequency table for multiple-answer questions."""
    present_cols = [c for c in cols if c in df.columns]
    if not present_cols:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    counts = {}
    for c in present_cols:
        label = labels.get(c, c)
        # Check for various "YES" formats or numeric 1
        # Adjust based on actual data format (often 1 or "1" or "Yes")
        # Assuming 1 means selected based on typical survey data, but checking unique values is safer.
        # If data is 1/NaN or 1/0:
        # Let's try to be robust: treat non-null/non-zero/non-empty as selected
        
        # For this dataset, it seems 1 is selected.
        # Let's assume 1 is the target value.
        # If column is object, check for "1" or "Yes".
        
        series = df[c].dropna().astype(str)
        # Common patterns for "checked": "1", "1.0", "Yes", "True"
        mask = series.isin(["1", "1.0", "Yes", "True", "checked"])
        cnt = mask.sum()
        
        if cnt > 0:
            counts[label] = cnt

    if not counts:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    tab = pd.DataFrame(
        {"answer": list(counts.keys()), "count": list(counts.values())}
    )
    # Percent of total respondents (filtered df)
    total_respondents = len(df)
    if total_respondents > 0:
        tab["percent"] = tab["count"] / total_respondents * 100
    else:
        tab["percent"] = 0
        
    tab["percent"] = tab["percent"].round(1)
    tab = tab.sort_values("percent", ascending=False)
    return tab

def process_open_ended_comments(df, prefix, max_slots=10):
    """
    Process open-ended questions where:
    - {prefix}_{i} is 'Yes'/'1' (optional check)
    - {prefix}_{i}comment is the actual text
    
    Returns:
    - segments_df: Distribution of how many items each user mentioned
    - mentions_df: Frequency of each unique mentioned item (normalized)
    """
    # 1. Calculate how many items each user mentioned
    # We can count non-null/non-empty comments for each row
    comment_cols = [f"{prefix}_{i}comment" for i in range(1, max_slots + 1)]
    valid_comment_cols = [c for c in comment_cols if c in df.columns]
    
    if not valid_comment_cols:
        return pd.DataFrame(), pd.DataFrame()

    # Function to count non-empty comments in a row
    # We work on a copy to avoid setting with copy warning on the main df if it's a slice
    # But df here is likely the filtered df.
    counts_per_user = df[valid_comment_cols].apply(
        lambda x: x.astype(str).str.strip().replace(["nan", "None", "0", ""], pd.NA).count(), 
        axis=1
    )
    
    # Segments table
    segments = counts_per_user.value_counts().reset_index()
    segments.columns = ["mentions_count", "num_users"]
    segments = segments[segments["mentions_count"] > 0].sort_values("mentions_count")
    segments["percent"] = (segments["num_users"] / len(df) * 100).round(1)
    
    # 2. Collect and clean all mentions
    all_mentions = []
    for c in valid_comment_cols:
        # Get all non-empty values
        vals = df[c].dropna().astype(str).tolist()
        for v in vals:
            v_clean = v.strip()
            if v_clean.lower() not in ["nan", "", "0", "none"]:
                all_mentions.append(v_clean)
    
    if not all_mentions:
        return segments, pd.DataFrame()

    # Create DataFrame for cleaning
    mentions_raw = pd.DataFrame({"original": all_mentions})
    # Normalize: lowercase for grouping
    mentions_raw["normalized"] = mentions_raw["original"].str.lower()
    
    # Group by normalized, but keep one representative original (e.g. the most frequent one or just first)
    grouped = mentions_raw.groupby("normalized").agg(
        count=("original", "count"),
        example=("original", "first") # Take the first appearance as label
    ).reset_index()
    
    # Sort by count
    grouped = grouped.sort_values("count", ascending=False)
    grouped = grouped.rename(columns={"example": "Mentioned", "count": "Count"})
    
    return segments, grouped[["Mentioned", "Count"]]

# ----------------------
# Charts
# ----------------------

PINK = "#ff3366"
YELLOW = "#ffcc66"
GRAY = "#7a8c8e"

def bar_chart_horizontal(tab: pd.DataFrame, title: str, height=400):
    if tab.empty:
        st.info("Տվյալներ չկան")
        return

    base = alt.Chart(tab).encode(
        y=alt.Y("answer:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
        x=alt.X("percent:Q", title="%", axis=alt.Axis(format="d")),
        tooltip=["answer", "percent", "count"]
    )

    bars = base.mark_bar()

    text = base.mark_text(
        align='left',
        baseline='middle',
        dx=3
    ).encode(
        text=alt.Text('percent:Q', format='.1f')
    )

    chart = (
        (bars + text)
        .properties(height=height, title=title)
        .configure_mark(color=GRAY)
    )
    st.altair_chart(chart, use_container_width=True)

def bar_chart_vertical(tab: pd.DataFrame, title: str, height=350):
    if tab.empty:
        st.info("Տվյալներ չկան")
        return

    base = alt.Chart(tab).encode(
        x=alt.X("answer:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-45, labelLimit=200)),
        y=alt.Y("percent:Q", title="%", axis=alt.Axis(format="d")),
        tooltip=["answer", "percent", "count"]
    )

    bars = base.mark_bar()

    text = base.mark_text(
        align='center',
        baseline='bottom',
        dy=-5
    ).encode(
        text=alt.Text('percent:Q', format='.1f')
    )

    chart = (
        (bars + text)
        .properties(height=height, title=title)
        .configure_mark(color=GRAY)
    )
    st.altair_chart(chart, use_container_width=True)

def donut_chart(tab: pd.DataFrame, title: str):
    if tab.empty:
        st.info("Տվյալներ չկան")
        return

    chart = (
        alt.Chart(tab)
        .mark_arc(innerRadius=60)
        .encode(
            theta=alt.Theta("percent:Q"),
            color=alt.Color("answer:N",
                            scale=alt.Scale(range=[GRAY, YELLOW, PINK, "#d3d3d3", "#a9a9a9"]),
                            legend=alt.Legend(title=None, orient="bottom", columns=2)),
            tooltip=["answer", "percent", "count"]
        )
        .properties(height=400, title=title)
    )
    st.altair_chart(chart, use_container_width=True)

# ... (rest of the file)

# In section 4, we have inline charts for YouTube, Bloggers, TikTok, Messengers.
# I need to update them too.

# YouTube section
# ...
# chart_seg_yt ... .configure_mark(color=GRAY)
# final_chart ... .configure_mark(color=GRAY)

# Bloggers section
# ...
# chart_seg ... .configure_mark(color=YELLOW) (Keep Yellow)

# TikTok section
# ...
# chart_seg_tt ... .configure_mark(color=PINK) (Keep Pink or change to Gray? User said "too much pink". But TikTok is distinct. Let's keep Pink for TikTok section specifically, or change to Gray. Let's change to GRAY to be safe.)
# Actually, let's use GRAY for TikTok too to avoid "too much pink".

# Messengers section
# chart_grouped ... color=alt.Color("answer:N", scale=alt.Scale(range=[GRAY, YELLOW, PINK, ...]))

# I will use multi_replace for inline charts later.
# This replacement is for the top part definitions.


# ----------------------
# Page Logic
# ----------------------

def page_section4(df: pd.DataFrame):
    st.title("Բաժին 4 - Այլ աղբյուրներ")
    
    # Render filters
    df = render_filters(df, key_prefix="sec4")
    show_note()
    
    st.markdown("### 1. Օնլայն լրատվական աղբյուրներ")
    
    # O1_2: Online news sources (Multiple)
    # Columns: O12_1 ... O12_14, O12_97, O12_999, O12_other
    # Mapping: O12_SOURCES_MAP
    # We need to construct the list of columns and labels dynamically or manually
    o12_cols = []
    o12_labels = {}
    
    # Map codes 1-14
    for code in range(1, 15):
        col = f"O12_{code}"
        if col in df.columns:
            o12_cols.append(col)
            o12_labels[col] = O12_SOURCES_MAP.get(code, str(code))
            
    # Add special codes if needed (usually we only show selected sources, not "Refused" in the main chart unless requested)
    # User request: "Տարբեակները չկարդալ, նշել բոլոր հնչած պատասխանները... 97, 999"
    # Let's include them if they are treated as checkboxes
    if "O12_97" in df.columns:
        o12_cols.append("O12_97")
        o12_labels["O12_97"] = O12_SOURCES_MAP.get(97)
    if "O12_999" in df.columns:
        o12_cols.append("O12_999")
        o12_labels["O12_999"] = O12_SOURCES_MAP.get(999)
    if "O12_other" in df.columns:
        o12_cols.append("O12_other")
        o12_labels["O12_other"] = O12_SOURCES_MAP.get(98)

    tab_o12 = freq_multi(df, o12_cols, o12_labels)
    bar_chart_horizontal(tab_o12, "Օնլայն լրատվական աղբյուրներ (Top mentions)", height=500)
    show_table_expander(tab_o12, "online_news_sources.csv")
    
    st.markdown("---")
    
    st.markdown("### 2. YouTube")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # O1: YouTube regular usage (Single)
        st.subheader("Յութուբյան ալիքների կանոնավոր դիտում")
        if "O1" in df.columns:
            tab_o1 = freq_single(df, "O1", mapping=O1_YOUTUBE_REGULAR_MAP)
            donut_chart(tab_o1, "Յութուբի օգտագործում")
            show_table_expander(tab_o1, "youtube_usage.csv")
        else:
            st.warning("O1 column not found")

    with col2:
        # O2: YouTube content types (Multiple)
        # Columns: O2_1 ... O2_7, O2_999, O2_other
        st.subheader("Յութուբում դիտվող կոնտենտի տեսակներ")
        o2_cols = []
        o2_labels = {}
        for code in range(1, 8):
            col = f"O2_{code}"
            if col in df.columns:
                o2_cols.append(col)
                o2_labels[col] = O2_YOUTUBE_CONTENT_MAP.get(code)
        
        if "O2_other" in df.columns:
            o2_cols.append("O2_other")
            o2_labels["O2_other"] = O2_YOUTUBE_CONTENT_MAP.get(98)
            
        tab_o2 = freq_multi(df, o2_cols, o2_labels)
        bar_chart_horizontal(tab_o2, "Կոնտենտի տեսակներ", height=350)
        show_table_expander(tab_o2, "youtube_content.csv")
        
    # O2.1: YouTube channels (Open ended)
    st.subheader("Նախընտրելի Յութուբյան ալիքներ")
    
    seg_yt, mentions_yt = process_open_ended_comments(df, "O21", max_slots=10)
    
    if not seg_yt.empty:
        st.markdown("**Քանի՞ ալիք է նշել յուրաքանչյուր մասնակից**")
        
        base = alt.Chart(seg_yt).encode(
            x=alt.X("mentions_count:O", title="Նշված ալիքների քանակ"),
            y=alt.Y("percent:Q", title="%"),
            tooltip=["mentions_count", "num_users", "percent"]
        )
        
        bars = base.mark_bar()
        
        text = base.mark_text(
            align='center',
            baseline='bottom',
            dy=-5
        ).encode(
            text=alt.Text('percent:Q', format='.1f')
        )
        
        chart_seg_yt = (
            (bars + text)
            .properties(height=300)
            .configure_mark(color=GRAY)
        )
        st.altair_chart(chart_seg_yt, use_container_width=True)

    if not mentions_yt.empty:
        # Show top 20 as a bar chart if possible, or just a table
        top_20 = mentions_yt.head(20)
        chart = (
            alt.Chart(top_20)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Քանակ"),
                y=alt.Y("Mentioned:N", sort="-x", title=None),
                tooltip=["Mentioned", "Count"]
            )
        )
        
        text = chart.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Count:Q')
        )
        
        final_chart = (
            (chart + text)
            .properties(title="Top 20 նշված ալիքներ")
            .configure_mark(color=GRAY)
        )
        st.altair_chart(final_chart, use_container_width=True)
        show_table_expander(mentions_yt, "youtube_channels_mentions.csv")
    else:
        st.info("Տվյալներ չկան")

    st.markdown("---")
    
    st.markdown("### 3. Սոցիալական ցանցեր")
    
    # O3: Social networks (Multiple)
    # Columns: O3_1 ... O3_6, O3_999, O3_other
    o3_cols = []
    o3_labels = {}
    for code in range(1, 7):
        col = f"O3_{code}"
        if col in df.columns:
            o3_cols.append(col)
            o3_labels[col] = O3_SOCIAL_NETWORKS_MAP.get(code)
            
    if "O3_other" in df.columns:
        o3_cols.append("O3_other")
        o3_labels["O3_other"] = O3_SOCIAL_NETWORKS_MAP.get(98)
        
    tab_o3 = freq_multi(df, o3_cols, o3_labels)
    st.subheader("Սոցիալական ցանցերից օգտվելը")
    bar_chart_vertical(tab_o3, "Սոցցանցերի օգտագործում")
    show_table_expander(tab_o3, "social_networks.csv")
    
    # O3.1: Behavior (Single)
    st.subheader("Սոցիալական ցանցերից օգտվելու վարքագիծ")
    if "O31" in df.columns:
        tab_o31 = freq_single(df, "O31", mapping=O3_1_SOCIAL_BEHAVIOR_MAP, exclude_values={0, 999})
        donut_chart(tab_o31, "Վարքագիծ")
        show_table_expander(tab_o31, "social_behavior.csv")
        


    # O3.2: Bloggers (Open ended)
    st.subheader("Նախընտրելի բլոգերներ (FB/Instagram)")
    
    # Analyze data
    seg_blog, mentions_blog = process_open_ended_comments(df, "O32", max_slots=10)
    
    if not seg_blog.empty:
        st.markdown("**Քանի՞ բլոգերի է նշել յուրաքանչյուր մասնակից**")
        
        base = alt.Chart(seg_blog).encode(
            x=alt.X("mentions_count:O", title="Նշված բլոգերների քանակ"),
            y=alt.Y("percent:Q", title="%"),
            tooltip=["mentions_count", "num_users", "percent"]
        )
        
        bars = base.mark_bar()
        
        text = base.mark_text(
            align='center',
            baseline='bottom',
            dy=-5
        ).encode(
            text=alt.Text('percent:Q', format='.1f')
        )
        
        chart_seg = (
            (bars + text)
            .properties(height=300)
            .configure_mark(color=YELLOW)
        )
        st.altair_chart(chart_seg, use_container_width=True)
    
    if not mentions_blog.empty:
        st.markdown("**Նշված բլոգերների վարկանիշը**")
        
        # Top 20 Chart
        top_20_blog = mentions_blog.head(20)
        chart_blog = (
            alt.Chart(top_20_blog)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Քանակ"),
                y=alt.Y("Mentioned:N", sort="-x", title=None),
                tooltip=["Mentioned", "Count"]
            )
        )
        
        text = chart_blog.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Count:Q')
        )
        
        final_chart_blog = (
            (chart_blog + text)
            .properties(title="Top 20")
            .configure_mark(color=YELLOW)
        )
        st.altair_chart(final_chart_blog, use_container_width=True)
        
        # Full Table
        with st.expander("Տեսնել բոլոր նշված բլոգերներին (Ամբողջական ցանկ)"):
            st.dataframe(mentions_blog, use_container_width=True)
            csv_blog = mentions_blog.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Ներբեռնել ամբողջական ցանկը CSV",
                data=csv_blog,
                file_name="bloggers_all_mentions.csv",
                mime="text/csv"
            )
    else:
        st.info("Տվյալներ չկան")
        
    st.markdown("---")

    # O3.3: TikTok (Open ended)
    st.subheader("Նախընտրելի Տիկտոկերներ")
    
    seg_tt, mentions_tt = process_open_ended_comments(df, "O33", max_slots=10)
    
    if not seg_tt.empty:
        st.markdown("**Քանի՞ տիկտոկերի է նշել յուրաքանչյուր մասնակից**")
        
        base = alt.Chart(seg_tt).encode(
            x=alt.X("mentions_count:O", title="Նշված տիկտոկերների քանակ"),
            y=alt.Y("percent:Q", title="%"),
            tooltip=["mentions_count", "num_users", "percent"]
        )
        
        bars = base.mark_bar()
        
        text = base.mark_text(
            align='center',
            baseline='bottom',
            dy=-5
        ).encode(
            text=alt.Text('percent:Q', format='.1f')
        )
        
        chart_seg_tt = (
            (bars + text)
            .properties(height=300)
            .configure_mark(color=GRAY)
        )
        st.altair_chart(chart_seg_tt, use_container_width=True)

    if not mentions_tt.empty:
        st.markdown("**Նշված տիկտոկերների վարկանիշը**")
        
        top_20_tt = mentions_tt.head(20)
        chart_tt = (
            alt.Chart(top_20_tt)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Քանակ"),
                y=alt.Y("Mentioned:N", sort="-x", title=None),
                tooltip=["Mentioned", "Count"]
            )
        )
        
        text = chart_tt.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Count:Q')
        )
        
        final_chart_tt = (
            (chart_tt + text)
            .properties(title="Top 20")
            .configure_mark(color=GRAY)
        )
        st.altair_chart(final_chart_tt, use_container_width=True)
        
        with st.expander("Տեսնել բոլոր նշված տիկտոկերներին (Ամբողջական ցանկ)"):
            st.dataframe(mentions_tt, use_container_width=True)
            csv_tt = mentions_tt.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Ներբեռնել ամբողջական ցանկը CSV",
                data=csv_tt,
                file_name="tiktokers_all_mentions.csv",
                mime="text/csv"
            )
    else:
        st.info("Տվյալներ չկան")

    st.markdown("---")
    
    st.markdown("### 4. Մեսինջերներ")
    
    # O4: Messengers (Multiple)
    # Columns: O4_1 ... O4_4, O4_other
    o4_cols = []
    o4_labels = {}
    for code in range(1, 5):
        col = f"O4_{code}"
        if col in df.columns:
            o4_cols.append(col)
            o4_labels[col] = O4_MESSENGERS_MAP.get(code)
    
    if "O4_other" in df.columns:
        o4_cols.append("O4_other")
        o4_labels["O4_other"] = O4_MESSENGERS_MAP.get(98)
        
    tab_o4 = freq_multi(df, o4_cols, o4_labels)
    st.subheader("Հաղորդակցման հավելվածներ")
    bar_chart_vertical(tab_o4, "Մեսինջերների օգտագործում")
    show_table_expander(tab_o4, "messengers.csv")
    
    # O4.1: Behavior for each messenger
    # Telegram (1) -> O411_1..4
    # Viber (2) -> O412_1..4
    # WhatsApp (3) -> O413_1..4
    # FB Messenger (4) -> O414_1..4
    
    st.subheader("Մեսինջերների օգտագործման վարքագիծ")
    
    messengers_config = [
        ("Telegram", "O411"),
        ("Viber", "O412"),
        ("WhatsApp", "O413"),
        ("Facebook Messenger", "O414"),
    ]
    
    # We want to show for each messenger, what is the distribution of behavior (1-4)
    # We can create a grouped bar chart or small multiples.
    # Or just 4 separate charts.
    
    # Let's try to aggregate data into one dataframe for a grouped chart
    # Structure: Messenger | Behavior | Percent
    
    all_behaviors = []
    
    for name, prefix in messengers_config:
        # Columns: prefix_1, prefix_2, prefix_3, prefix_4
        # These are multiple choice columns? No, the question O4.1 says "Single, rotate".
        # But the data structure provided by user shows O411_1, O411_2... which usually implies binary columns for each option if it was multiple.
        # However, if it is Single, usually it's one column O411 with value 1,2,3,4.
        # BUT user said: "O412_1 O412_2 O412_3 O412_4".
        # This looks like dummy variables for a single choice question, OR it's actually multiple choice in the data export.
        # If it's single choice stored as dummies: only one of them should be 1.
        # Let's calculate frequency for each option 1-4.
        
        # We can use freq_multi logic to get counts for each option 1-4
        cols = [f"{prefix}_{i}" for i in range(1, 5)]
        labels = {f"{prefix}_{i}": O4_1_MESSENGER_BEHAVIOR_MAP.get(i) for i in range(1, 5)}
        
        tab = freq_multi(df, cols, labels)
        if not tab.empty:
            tab["Messenger"] = name
            all_behaviors.append(tab)
            
    if all_behaviors:
        final_tab = pd.concat(all_behaviors)
        
        # Grouped bar chart
        base = alt.Chart(final_tab).encode(
            x=alt.X("percent:Q", title="%"),
            y=alt.Y("Messenger:N", title=None),
            color=alt.Color("answer:N", title="Վարքագիծ", legend=alt.Legend(orient="bottom", columns=1)),
            tooltip=["Messenger", "answer", "percent"]
        )
        
        bars = base.mark_bar()
        
        text = base.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('percent:Q', format='.1f')
        )
        
        chart_grouped = (
            (bars + text)
            .properties(height=500, title="Վարքագիծը ըստ հավելվածի")
        )
        st.altair_chart(chart_grouped, use_container_width=True)
        show_table_expander(final_tab, "messengers_behavior.csv")
    else:
        st.info("Տվյալներ չկան վարքագծի վերաբերյալ")

