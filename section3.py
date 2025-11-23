"""
# Section 3: Radio and TV Channel Ratings
"""
import streamlit as st
import pandas as pd
import altair as alt
from filters import render_filters
from mappings import (
    TV_CHANNELS_MAP, RADIO_CHANNELS_MAP, TV_SUBSCRIPTION_MAP,
    CABLE_PROVIDER_MAP, TV_PROGRAM_TYPES_MAP, RADIO_PROGRAM_TYPES_MAP,
    TV_PROGRAMS_NEWS_MAP, TV_PROGRAMS_ENTERTAINMENT_MAP, TV_PROGRAMS_SERIES_MAP
)

PINK = "#ff3366"
WHITE = "#ffffff"
GRAY = "#7a8c8e"
YELLOW = "#ffcc66"


def show_note():
    """Global note about refusals."""
    st.markdown(
        "<i>Ընդհանուր %-ը կարող է չլինել 100, քանի որ հարցից հրաժարումների %-ները ներկայացված չեն։</i>",
        unsafe_allow_html=True
    )


def freq_single(df: pd.DataFrame, col: str, mapping: dict | None = None,
                exclude_values: set | None = None) -> pd.DataFrame:
    """Build frequency table for single-answer question."""
    if col not in df.columns:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    series = df[col].copy().dropna()

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


def freq_multi_numbered(df: pd.DataFrame, col_prefix: str, max_num: int, 
                        mapping: dict, exclude_values: set | None = None) -> pd.DataFrame:
    """
    Build frequency table for multiple-answer questions stored as numbered columns.
    E.g., R1Other_1, R1Other_2, ..., R1Other_19
    
    Args:
        df: DataFrame
        col_prefix: Prefix for columns (e.g., "R1Other_")
        max_num: Maximum number to check
        mapping: Dictionary to map values to labels
        exclude_values: Values to exclude (e.g., {0, 999})
    """
    counts = {}
    
    for i in range(1, max_num + 1):
        col_name = f"{col_prefix}{i}"
        if col_name not in df.columns:
            continue
        
        # Get all non-null values from this column
        values = df[col_name].dropna()
        
        if exclude_values:
            values = values[~values.isin(exclude_values)]
        
        # Count occurrences of each value
        for val in values:
            if val in mapping:
                label = mapping[val]
                counts[label] = counts.get(label, 0) + 1
    
    if not counts:
        return pd.DataFrame(columns=["answer", "count", "percent"])
    
    tab = pd.DataFrame(
        {"answer": list(counts.keys()), "count": list(counts.values())}
    )
    tab["percent"] = tab["count"] / tab["count"].sum() * 100
    tab["percent"] = tab["percent"].round(1)
    tab = tab.sort_values("percent", ascending=False)
    return tab


def freq_multi_yes(df: pd.DataFrame, col_prefix: str, max_num: int,
                   mapping: dict) -> pd.DataFrame:
    """
    Build frequency table for prompted questions where YES means selected.
    E.g., R1Propm_1, R1Propm_2, ..., R1Propm_19
    """
    counts = {}
    
    for i in range(1, max_num + 1):
        col_name = f"{col_prefix}{i}"
        if col_name not in df.columns:
            continue
        
        # Count YES responses
        yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
        
        if yes_count > 0 and i in mapping:
            label = mapping[i]
            counts[label] = yes_count
    
    # Also check for _98 and _999 columns if they exist
    for suffix in ["_98", "_999"]:
        col_name = f"{col_prefix.rstrip('_')}{suffix}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0:
                key = int(suffix.replace("_", ""))
                if key in mapping:
                    counts[mapping[key]] = yes_count
    
    if not counts:
        return pd.DataFrame(columns=["answer", "count", "percent"])
    
    tab = pd.DataFrame(
        {"answer": list(counts.keys()), "count": list(counts.values())}
    )
    tab["percent"] = tab["count"] / tab["count"].sum() * 100
    tab["percent"] = tab["percent"].round(1)
    tab = tab.sort_values("percent", ascending=False)
    return tab


def combine_tom_other_promp(df: pd.DataFrame, tom_col: str, other_prefix: str, 
                             promp_prefix: str, max_num: int, mapping: dict,
                             exclude_values: set | None = None) -> pd.DataFrame:
    """
    Combine TOM, Other, and Prompted data into single dataframe for grouped visualization.
    
    TOM column contains channel NAMES directly (e.g., "Արմենիա")
    Other_X and Propm_X columns contain "Yes" where X is the channel code
    
    Returns DataFrame with columns: channel, TOM, Other, Prompted (percentages)
    """
    all_channels = {}
    total_respondents = len(df)
    
    # 1. Get TOM (first mentioned) data - contains channel NAMES directly
    if tom_col in df.columns:
        tom_series = df[tom_col].dropna()
        # Filter out certain values if needed
        if exclude_values:
            # Since TOM has names, we need to filter by the names in the mapping
            exclude_names = {mapping.get(v, str(v)) for v in exclude_values if v in mapping}
            tom_series = tom_series[~tom_series.isin(exclude_names)]
        
        tom_counts = tom_series.value_counts().to_dict()
        
        for channel_name, count in tom_counts.items():
            # Skip "other" or text values that are not in our mapping
            if str(channel_name).lower() in ['other', 'nan', 'none']:
                continue
            if channel_name not in all_channels:
                all_channels[channel_name] = {"TOM": 0, "Other": 0, "Prompted": 0}
            all_channels[channel_name]["TOM"] = count
    
    # 2. Get Other (all mentioned without prompting) data - contains "Yes" values
    for i in range(1, max_num + 1):
        col_name = f"{other_prefix}{i}"
        if col_name not in df.columns:
            continue
        
        # Count "Yes" responses
        yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
        
        if yes_count > 0 and i in mapping:
            channel = mapping[i]
            if channel not in all_channels:
                all_channels[channel] = {"TOM": 0, "Other": 0, "Prompted": 0}
            all_channels[channel]["Other"] = yes_count
    
    # 3. Get Prompted data - contains "Yes" values
    for i in range(1, max_num + 1):
        col_name = f"{promp_prefix}{i}"
        if col_name not in df.columns:
            continue
        
        yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
        if yes_count > 0 and i in mapping:
            channel = mapping[i]
            if channel not in all_channels:
                all_channels[channel] = {"TOM": 0, "Other": 0, "Prompted": 0}
            all_channels[channel]["Prompted"] = yes_count
    
    # Also check for _98 and _999 columns in Prompted
    for suffix in [98, 999]:
        if exclude_values and suffix in exclude_values:
            continue
        col_name = f"{promp_prefix.rstrip('_')}_{suffix}"
        if col_name in df.columns and suffix in mapping:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0:
                channel = mapping[suffix]
                if channel not in all_channels:
                    all_channels[channel] = {"TOM": 0, "Other": 0, "Prompted": 0}
                all_channels[channel]["Prompted"] = yes_count
    
    # Convert to DataFrame
    if not all_channels:
        return pd.DataFrame(columns=["channel", "TOM", "Other", "Prompted", "Total"])
    
    data = []
    
    for channel, counts in all_channels.items():
        data.append({
            "channel": channel,
            "TOM": round(counts["TOM"] / total_respondents * 100, 1),
            "Other": round(counts["Other"] / total_respondents * 100, 1),
            "Prompted": round(counts["Prompted"] / total_respondents * 100, 1),
            "Total": round((counts["TOM"] + counts["Other"] + counts["Prompted"]) / total_respondents * 100, 1)
        })
    
    result_df = pd.DataFrame(data)
    result_df = result_df.sort_values("Total", ascending=False)
    
    return result_df


def grouped_bar_chart(tab: pd.DataFrame, title: str):
    """Create grouped horizontal bar chart showing TOM, Other, and Prompted together."""
    if tab.empty:
        st.info("Տվյալներ չկան այս հարցի համար ֆիլտրերի սահմանման դեպքում.")
        return
    
    # Create three separate charts side by side for clarity
    col1, col2, col3 = st.columns(3)
    
    colors = {
        'TOM': PINK,
        'Other': YELLOW,
        'Prompted': GRAY
    }
    
    labels = {
        'TOM': 'Առաջին հիշատակում',
        'Other': 'Սպոնտան հիշատակում',
        'Prompted': 'Ընդհանուր լսելիություն'
    }
    
    # Sort by total
    tab_sorted = tab.sort_values('Total', ascending=False).head(15)  # Top 15
    
    for col, (metric, label) in zip([col1, col2, col3], labels.items()):
        with col:
            st.markdown(f"**{label}**")
            chart_data = tab_sorted[['channel', metric]].rename(columns={metric: 'value'})
            
            base = alt.Chart(chart_data).encode(
                x=alt.X('value:Q', title='%', scale=alt.Scale(domain=[0, tab['Total'].max()])),
                y=alt.Y('channel:N', sort='-x', title=None, axis=alt.Axis(labelLimit=150)),
                tooltip=[
                    alt.Tooltip('channel:N', title='Ալիք'),
                    alt.Tooltip('value:Q', title='%', format='.1f')
                ]
            )

            bars = base.mark_bar(color=colors[metric])

            text = base.mark_text(
                align='left',
                baseline='middle',
                dx=3
            ).encode(
                text=alt.Text('value:Q', format='.1f')
            )

            chart = (
                (bars + text)
                .properties(height=500)
            )
            st.altair_chart(chart, use_container_width=True)
    
    # Show table in expander below charts
    with st.expander("Բացել աղյուսակը"):
        st.dataframe(
            tab[['channel', 'TOM', 'Other', 'Prompted', 'Total']].style.format({
                'TOM': '{:.1f}%',
                'Other': '{:.1f}%', 
                'Prompted': '{:.1f}%',
                'Total': '{:.1f}%'
            }),
            use_container_width=True,
            height=min(600, len(tab) * 35 + 100)
        )
        
        # Add download button
        csv = tab[['channel', 'TOM', 'Other', 'Prompted', 'Total']].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Ներբեռնել CSV",
            data=csv,
            file_name=f"{title.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )


def bar_chart_horizontal(tab: pd.DataFrame, title: str):
    """Horizontal bar chart."""
    if tab.empty:
        st.info("Տվյալներ չկան այս հարցի համար ֆիլտրերի սահմանման դեպքում.")
        return

    base = alt.Chart(tab).encode(
        y=alt.Y("answer:N", sort="-x", title=None),
        x=alt.X("percent:Q", title="%", axis=alt.Axis(format="d")),
        tooltip=["answer", "percent"]
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
        .properties(height=max(300, len(tab) * 25), title=title)
        .configure_mark(color=GRAY)
    )
    st.altair_chart(chart, use_container_width=True)


def donut_chart(tab: pd.DataFrame, title: str):
    """Donut chart."""
    if tab.empty:
        st.info("Տվյալներ չկան այս հարցի համար ֆիլտրերի սահմանման դեպքում.")
        return

    chart = (
        alt.Chart(tab)
        .mark_arc(innerRadius=60)
        .encode(
            theta=alt.Theta("percent:Q"),
            color=alt.Color("answer:N",
                            scale=alt.Scale(
                                range=[GRAY, YELLOW, PINK, "#d3d3d3", "#a9a9a9"]
                            ),
                            legend=alt.Legend(title=None)),
            tooltip=["answer", "percent"]
        )
        .properties(height=350, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


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


def page_section3(df: pd.DataFrame):
    """Main page for Section 3."""
    st.title("Բաժին 3 - Ռադիո և TV ալիքների վարկանիշեր")
    
    # Render filters in expander on the page
    df = render_filters(df, key_prefix="sec3")
    
    show_note()
    
    # ==================
    # R1 - TV Channels
    # ==================
    st.header("📺 Հեռուստաալիքներ")
    
    st.subheader("Հայկական հեռուստաալիքներ (ամբողջական վերլուծություն)")
    
    # Combined TOM + Other + Prompted visualization
    tab_tv_combined = combine_tom_other_promp(
        df, 
        tom_col="R1TOM",
        other_prefix="R1Other_",
        promp_prefix="R1Propm_",
        max_num=19,
        mapping=TV_CHANNELS_MAP,
        exclude_values={0, 999}
    )
    
    grouped_bar_chart(tab_tv_combined, "Հեռուստաալիքների ճանաչողություն")
    
    st.markdown("---")
    
    # ==================
    # R2 - TV Subscription
    # ==================
    st.header("📡 Հեռուստատեսության տեսակը")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Հեռուստատեսության տեսակ")
        tab_r2 = freq_single(df, "R2", mapping=TV_SUBSCRIPTION_MAP, exclude_values={0, 99})
        donut_chart(tab_r2, "Հեռուստատեսության տեսակի բաշխվածություն")
        show_table_expander(tab_r2, "r2_tv_subscription.csv")
    
    with col2:
        st.subheader("Կաբելային TV մատակարար")
        # Only show for those who selected cable (R2 contains text, not numbers)
        if "R2" in df.columns:
            # Filter for cable TV users (text contains "կաբելային")
            df_cable = df[df["R2"].astype(str).str.contains("կաբելային", na=False, case=False)]
        else:
            df_cable = df
        # R21 contains company names directly, no mapping needed
        tab_r21 = freq_single(df_cable, "R21", mapping=None, exclude_values={0, 99})
        donut_chart(tab_r21, "Կաբելային TV մատակարարներ")
        show_table_expander(tab_r21, "r21_cable_provider.csv")
    
    st.markdown("---")
    
    # ==================
    # R3 - Radio Channels
    # ==================
    st.header("📻 Ռադիոալիքներ")
    
    st.subheader("Հայկական ռադիոալիքներ (ամբողջական վերլուծություն)")
    
    # Combined TOM + Other + Prompted visualization
    tab_radio_combined = combine_tom_other_promp(
        df,
        tom_col="R3TOM",
        other_prefix="R3Other_",
        promp_prefix="R3Propm_",
        max_num=20,
        mapping=RADIO_CHANNELS_MAP,
        exclude_values={0, 999}
    )
    
    grouped_bar_chart(tab_radio_combined, "Ռադիոալիքների ճանաչողություն")
    
    st.markdown("---")
    
    # ==================
    # R4 - TV Program Types
    # ==================
    st.header("🎬 Հեռուստահաղորդումների տեսակներ")
    
    st.subheader("Նախընտրելի հաղորդումների տեսակներ")
    
    # R4 uses YES/NO format in columns R4_1 through R4_7
    r4_cols = [f"R4_{i}" for i in range(1, 8)]
    counts = {}
    for i in range(1, 8):
        col_name = f"R4_{i}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0 and i in TV_PROGRAM_TYPES_MAP:
                counts[TV_PROGRAM_TYPES_MAP[i]] = yes_count
    
    if counts:
        tab_r4 = pd.DataFrame(
            {"answer": list(counts.keys()), "count": list(counts.values())}
        )
        tab_r4["percent"] = tab_r4["count"] / tab_r4["count"].sum() * 100
        tab_r4["percent"] = tab_r4["percent"].round(1)
        tab_r4 = tab_r4.sort_values("percent", ascending=False)
        bar_chart_horizontal(tab_r4, "Նախընտրելի հաղորդումների տեսակներ")
        show_table_expander(tab_r4, "r4_tv_program_types.csv")
    else:
        st.info("Տվյալներ չկան")
    
    st.markdown("---")
    
    # ==================
    # R5 - Specific TV Programs
    # ==================
    st.header("📋 Կոնկրետ հեռուստահաղորդումներ")
        
    # News programs
    counts_news = {}
    for i in range(1, 8):
        col_name = f"R51_{i}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0 and i in TV_PROGRAMS_NEWS_MAP:
                counts_news[TV_PROGRAMS_NEWS_MAP[i]] = yes_count
    
    if counts_news:
        tab_news = pd.DataFrame(
            {"answer": list(counts_news.keys()), "count": list(counts_news.values())}
        )
        tab_news["percent"] = tab_news["count"] / len(df) * 100
        tab_news["percent"] = tab_news["percent"].round(1)
        tab_news = tab_news.sort_values("percent", ascending=False)
        bar_chart_horizontal(tab_news, "Լրատվական հաղորդումներ")
        show_table_expander(tab_news, "r5_news_programs.csv")
    else:
        st.info("Տվյալներ չկան")
    
    st.markdown("---")
    
    # Entertainment programs
    counts_ent = {}
    for i in range(1, 11):
        col_name = f"R53_{i}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0 and i in TV_PROGRAMS_ENTERTAINMENT_MAP:
                counts_ent[TV_PROGRAMS_ENTERTAINMENT_MAP[i]] = yes_count
    
    if counts_ent:
        tab_ent = pd.DataFrame(
            {"answer": list(counts_ent.keys()), "count": list(counts_ent.values())}
        )
        tab_ent["percent"] = tab_ent["count"] / len(df) * 100
        tab_ent["percent"] = tab_ent["percent"].round(1)
        tab_ent = tab_ent.sort_values("percent", ascending=False)
        bar_chart_horizontal(tab_ent, "Երաժշտական/ժամանցային հաղորդումներ")
        show_table_expander(tab_ent, "r5_entertainment_programs.csv")
    else:
        st.info("Տվյալներ չկան")
    
    st.markdown("---")
    
    # Series
    counts_series = {}
    for i in range(1, 5):
        col_name = f"R56_{i}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0 and i in TV_PROGRAMS_SERIES_MAP:
                counts_series[TV_PROGRAMS_SERIES_MAP[i]] = yes_count
    
    if counts_series:
        tab_series = pd.DataFrame(
            {"answer": list(counts_series.keys()), "count": list(counts_series.values())}
        )
        tab_series["percent"] = tab_series["count"] / len(df) * 100
        tab_series["percent"] = tab_series["percent"].round(1)
        tab_series = tab_series.sort_values("percent", ascending=False)
        bar_chart_horizontal(tab_series, "Սերիալներ")
        show_table_expander(tab_series, "r5_series_programs.csv")
    else:
        st.info("Տվյալներ չկան")
    
    st.markdown("---")
    
    # ==================
    # R6 - Radio Program Types
    # ==================
    st.header("🎙️ Ռադիոհաղորդումների տեսակներ")
    
    st.subheader("Լսվող ռադիոհաղորդումների տեսակներ")
    
    # R6_1 through R6_7
    counts_r6 = {}
    for i in range(1, 8):
        col_name = f"R6_{i}"
        if col_name in df.columns:
            yes_count = df[col_name].astype(str).str.upper().eq("YES").sum()
            if yes_count > 0 and i in RADIO_PROGRAM_TYPES_MAP:
                counts_r6[RADIO_PROGRAM_TYPES_MAP[i]] = yes_count
    
    if counts_r6:
        tab_r6 = pd.DataFrame(
            {"answer": list(counts_r6.keys()), "count": list(counts_r6.values())}
        )
        tab_r6["percent"] = tab_r6["count"] / tab_r6["count"].sum() * 100
        tab_r6["percent"] = tab_r6["percent"].round(1)
        tab_r6 = tab_r6.sort_values("percent", ascending=False)
        bar_chart_horizontal(tab_r6, "Ռադիոհաղորդումների տեսակներ")
        show_table_expander(tab_r6, "r6_radio_program_types.csv")
    else:
        st.info("Տվյալներ չկան")
    
    st.markdown("---")
    
    # ==================
    # R7 - Radio Program Names
    # ==================
    st.header("📝 Ռադիոհաղորդումների անուններ")
    
    st.subheader("Հիշատակված ռադիոհաղորդումներ")
    
    # R7 is free text, let's show unique values
    if "R7" in df.columns:
        r7_values = df["R7"].dropna().unique()
        if len(r7_values) > 0:
            st.write(f"Ընդամենը հիշատակված հաղորդումների քանակը: {len(r7_values)}")
            with st.expander("Տեսնել հիշատակված հաղորդումները"):
                r7_df = pd.DataFrame({"Հաղորդում": sorted(r7_values)})
                st.dataframe(r7_df, use_container_width=True)
        else:
            st.info("Տվյալներ չկան")
    else:
        st.info("Տվյալներ չկան")
