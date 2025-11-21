"""
Section 2: Radio and TV Consumption Behavior
"""
import streamlit as st
import pandas as pd
from filters import render_filters
from mappings import M0_FREQUENCY_MAP


def show_note():
    """Global note about refusals."""
    st.markdown(
        "<i>Ընդհանուր %-ը կարող է չլինել 100, քանի որ հարցից հրաժարումների %-ները ներկայացված չեն։</i>",
        unsafe_allow_html=True
    )


def freq_single(df: pd.DataFrame, col: str, mapping: dict | None = None,
                exclude_values: set | None = None, include_null: bool = False) -> pd.DataFrame:
    """Build frequency table for single-answer question."""
    if col not in df.columns:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    series = df[col].copy()
    
    # Handle null values
    if include_null:
        series = series.fillna("Տվյալներ չկան")  # "No data" in Armenian
    else:
        series = series.dropna()

    # Exclude technical codes like 0, 999 if needed
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
    """Build frequency table for multiple-answer questions with YES/blank format."""
    present_cols = [c for c in cols if c in df.columns]
    if not present_cols:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    counts = {}
    for c in present_cols:
        label = labels.get(c, c)
        yes_mask = df[c].astype(str).str.upper().eq("YES")
        cnt = yes_mask.sum()
        if cnt > 0:
            counts[label] = cnt

    if not counts:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    tab = pd.DataFrame(
        {"answer": list(counts.keys()), "count": list(counts.values())}
    )
    tab["percent"] = tab["count"] / tab["count"].sum() * 100
    tab["percent"] = tab["percent"].round(1)
    tab = tab.sort_values("percent", ascending=False)
    return tab


def bar_chart_vertical(tab: pd.DataFrame, title: str):
    """Vertical bar chart."""
    import altair as alt
    GRAY = "#7a8c8e"
    
    if tab.empty:
        st.info("Տվյալներ չկան այս հարցի համար ֆիլտրերի սահմանման դեպքում.")
        return

    base = alt.Chart(tab).encode(
        x=alt.X("answer:N", sort="-y", title=None),
        y=alt.Y("percent:Q", title="%", axis=alt.Axis(format="d")),
        tooltip=["answer", "percent"]
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
        .properties(height=350, title=title)
        .configure_mark(color=GRAY)
    )
    st.altair_chart(chart, use_container_width=True)


def bar_chart_horizontal(tab: pd.DataFrame, title: str):
    """Horizontal bar chart."""
    import altair as alt
    GRAY = "#7a8c8e"
    
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
        .properties(height=400, title=title)
        .configure_mark(color=GRAY)
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


def page_section2(df: pd.DataFrame):
    st.title("Բաժին 2 - Ռադիո և TV ունկնդրման/ դիտման վարքագիծ")
    
    # Render filters in expander on the page
    df = render_filters(df, key_prefix="sec2")

    show_note()

    st.subheader("M0 - Օգտագործման հաճախականություն")

    m0_cols = {
        "M0_M0TV": "Հեռուստացույց դիտելու հաճախականություն",
        "M0_M0_radio": "Ռադիո ունկնդրման հաճախականություն",
        "M0_M0_SM": "Սոցցանցերից օգտվելու հաճախականություն",
        "M0_M0_MES": "Մեսինջերներից օգտվելու հաճախականություն",
    }

    row1 = st.columns(2)
    row2 = st.columns(2)
    rows = row1 + row2

    for (col_name, title), col in zip(m0_cols.items(), rows):
        if col_name not in df.columns:
            continue
        with col:
            # Don't exclude 98 and 999, only exclude 0 if present
            tab = freq_single(df, col_name, mapping=M0_FREQUENCY_MAP, exclude_values={0})
            bar_chart_vertical(tab, title)
            show_table_expander(tab, f"{col_name.lower()}_freq.csv")

    st.markdown("---")

    # H4 - places for watching TV (multiple)
    st.subheader("H4 - Որտե՞ղ եք սովորաբար հեռուստացույց դիտում")

    h4_cols = ["H4_1", "H4_2", "H4_other"]
    h4_labels = {
        "H4_1": "Տանը",
        "H4_2": "Աշխատավայրում",
        "H4_other": "Այլ տեղ (մանրամասնել)"
    }
    tab_h4 = freq_multi(df, h4_cols, h4_labels)
    bar_chart_horizontal(tab_h4, "Հեռուստացույց դիտելու վայրեր")
    show_table_expander(tab_h4, "h4_tv_places.csv")

    st.markdown("---")

    # H4.1 - places for listening radio (multiple)
    st.subheader("H4.1 - Որտե՞ղ եք սովորաբար ռադիո լսում")

    h41_cols = ["H41_1", "H41_2", "H41_3", "H41_4", "H41_other"]
    h41_labels = {
        "H41_1": "Տանը",
        "H41_2": "Աշխատավայրում",
        "H41_3": "Տրանսպորտի մեջ",
        "H41_4": "Սեփական մեքենայում",
        "H41_other": "Այլ տեղ (մանրամասնել)"
    }
    tab_h41 = freq_multi(df, h41_cols, h41_labels)
    bar_chart_horizontal(tab_h41, "Ռադիո լսելու վայրեր")
    show_table_expander(tab_h41, "h41_radio_places.csv")

    st.markdown("---")

    # H2.1 - way of watching/listening (multiple, max 3)
    st.subheader("H2.1 - Ինչ տարբերակով եք սովորաբար դիտում/լսում")

    h211_cols = ["H211_1", "H211_2", "H211_3", "H211_other"]
    h211_labels = {
        "H211_1": "Հեռուստացույցով/ռադիոընդունիչով (TV ծրագրեր)",
        "H211_2": "Առցանց՝ համակարգչով (TV ծրագրեր)",
        "H211_3": "Առցանց՝ պլանշետով/սմարթֆոնով (TV ծրագրեր)",
        "H211_other": "Այլ ձև (TV, մանրամասնել)"
    }
    tab_h211 = freq_multi(df, h211_cols, h211_labels)
    bar_chart_vertical(tab_h211, "Հեռուստատեսային ծրագրերի դիտման ձևեր")
    show_table_expander(tab_h211, "h211_tv_mode.csv")

    h212_cols = ["H212_1", "H212_2", "H212_3", "H212_other"]
    h212_labels = {
        "H212_1": "Հեռուստացույցով/ռադիոընդունիչով (ռադիո)",
        "H212_2": "Առցանց՝ համակարգչով (ռադիո)",
        "H212_3": "Առցանց՝ պլանշետով/սմարթֆոնով (ռադիո)",
        "H212_other": "Այլ ձև (ռադիո, մանրամասնել)"
    }
    tab_h212 = freq_multi(df, h212_cols, h212_labels)
    bar_chart_vertical(tab_h212, "Ռադիո ծրագրերի ունկնդրման ձևեր")
    show_table_expander(tab_h212, "h212_radio_mode.csv")

    st.markdown("---")

    # H3 - time of day (multiple, 3 main slots)
    st.subheader("H3 - Ո՞ր ժամերին եք ամենից հաճախ դիտում/լսում")

    h31_cols = [
        "H31_1", "H31_2", "H31_3", "H31_4", "H31_5", "H31_6",
        "H31_7", "H31_8", "H31_9", "H31_10", "H31_11", "H31_12",
        "H31_13", "H31_14", "H31_15", "H31_16", "H31_999"
    ]
    h31_labels = {
        "H31_1": "7:00-8:00",
        "H31_2": "8:01-9:00",
        "H31_3": "9:01-10:00",
        "H31_4": "10:01-11:00",
        "H31_5": "11:01-12:00",
        "H31_6": "12:01-13:00",
        "H31_7": "13:01-14:00",
        "H31_8": "14:01-15:00",
        "H31_9": "15:01-16:00",
        "H31_10": "16:01-17:00",
        "H31_11": "17:01-18:00",
        "H31_12": "18:01-19:00",
        "H31_13": "19:01-20:00",
        "H31_14": "20:01-22:00",
        "H31_15": "22:01-00:00",
        "H31_16": "Գիշերը 00:01-ից հետո",
        "H31_999": "Դժվարանում եմ պատասխանել",
    }
    tab_h31 = freq_multi(df, h31_cols, h31_labels)
    bar_chart_horizontal(tab_h31, "Հեռուստացույց դիտելու ժամեր")
    show_table_expander(tab_h31, "h31_tv_hours.csv")

    h32_cols = [
        "H32_1", "H32_2", "H32_3", "H32_4", "H32_5", "H32_6",
        "H32_7", "H32_8", "H32_9", "H32_10", "H32_11", "H32_12",
        "H32_13", "H32_14", "H32_15", "H32_16", "H32_999"
    ]
    h32_labels = {c.replace("H32_", "H31_"): v for c, v in h31_labels.items()}
    # Fix labels for keys
    h32_labels = {k: h31_labels[k.replace("H32_", "H31_")] for k in h32_cols if k != "H32_999"}
    h32_labels["H32_999"] = "Դժվարանում եմ պատասխանել"

    tab_h32 = freq_multi(df, h32_cols, h32_labels)
    bar_chart_horizontal(tab_h32, "Ռադիո լսելու ժամեր")
    show_table_expander(tab_h32, "h32_radio_hours.csv")


