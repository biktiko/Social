"""
Section 6: Demography
"""
import streamlit as st
import pandas as pd
import altair as alt
from filters import render_filters
from mappings import (
    D1_MARITAL_STATUS_MAP,
    D4_EMPLOYMENT_STATUS_MAP,
    D4_1_INDUSTRY_MAP,
    D6_INCOME_MAP
)

# ----------------------
# Helper functions
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
                exclude_values: set | None = None, include_null: bool = False) -> pd.DataFrame:
    """Build frequency table for single-answer question."""
    if col not in df.columns:
        return pd.DataFrame(columns=["answer", "count", "percent"])

    series = df[col].copy()
    
    # Handle null values
    if include_null:
        series = series.fillna("Տվյալներ չկան")
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

# ----------------------
# Charts
# ----------------------

PINK = "#ff3366"
YELLOW = "#ffcc66"
GRAY = "#7a8c8e"
BLUE = "#4fb4d8"
LIGHT_BLUE = "#a0c4ff"

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
        .configure_mark(color=PINK)
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
        .configure_mark(color=PINK)
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
                            scale=alt.Scale(range=[PINK, YELLOW, GRAY, BLUE, LIGHT_BLUE]),
                            legend=alt.Legend(title=None, orient="bottom", columns=2)),
            tooltip=["answer", "percent", "count"]
        )
        .properties(height=400, title=title)
    )
    st.altair_chart(chart, use_container_width=True)

# ----------------------
# Page Logic
# ----------------------

def page_demography(df: pd.DataFrame):
    st.title("Մասնակիցների դեմոգրաֆիկ բնութագիրը")
    
    # Render filters in expander on the page
    df = render_filters(df, key_prefix="demo")

    show_note()

    # Row 1 - sex + age
    col1, col2 = st.columns(2)

    with col1:
        tab_sex = freq_single(df, "S2", mapping=None, exclude_values={0, 999})
        st.subheader("Սեռ")
        bar_chart_horizontal(tab_sex, "Սեռի բաշխվածություն")
        show_table_expander(tab_sex, "demography_sex.csv")

    with col2:
        if "AGE_GRP" in df.columns:
            tab_age = freq_single(df, "AGE_GRP", mapping=None, exclude_values=None)
            st.subheader("Տարիքի խմբեր")
            bar_chart_vertical(tab_age, "Տարիքի խմբերի բաշխվածություն")
            show_table_expander(tab_age, "demography_age.csv")

    st.markdown("---")

    # Row 2 - city and settlement type
    col3, col4 = st.columns(2)

    with col3:
        if "S3" in df.columns:
            tab_city = freq_single(df, "S3", mapping=None, exclude_values={0, 999})
            st.subheader("Բնակավայր (S3)")
            bar_chart_horizontal(tab_city, "Բնակավայրերի բաշխվածություն")
            show_table_expander(tab_city, "demography_city.csv")

    with col4:
        if "S5" in df.columns:
            # Include null values as separate category
            tab_s5 = freq_single(df, "S5", mapping=None, exclude_values={0, 999}, include_null=True)
            st.subheader("Բնակավայրի տեսակ (S5)")
            donut_chart(tab_s5, "Բնակավայրի տեսակի բաշխվածություն")
            show_table_expander(tab_s5, "demography_s5.csv")

    st.markdown("---")

    # Device type
    if "Dev_lbl" in df.columns:
        st.subheader("Օգտագործվող հեռախոսի տեսակ")
        tab_dev = freq_single(df, "Dev_lbl", mapping=None, exclude_values=None)
        donut_chart(tab_dev, "Հեռախոսի տեսակի բաշխվածություն")
        show_table_expander(tab_dev, "demography_device.csv")

    st.markdown("---")
    
    # New Demography Questions
    st.header("Սոցիալ-դեմոգրաֆիական այլ տվյալներ")
    
    # D1 - Marital Status
    st.subheader("D1. Ամուսնական կարգավիճակ")
    if "D1" in df.columns:
        tab_d1 = freq_single(df, "D1", mapping=D1_MARITAL_STATUS_MAP, exclude_values={99})
        donut_chart(tab_d1, "Ամուսնական կարգավիճակ")
        show_table_expander(tab_d1, "demography_marital.csv")
        
    st.markdown("---")
    
    # D4 - Employment Status
    st.subheader("D4. Զբաղվածության կարգավիճակ")
    if "D4" in df.columns:
        tab_d4 = freq_single(df, "D4", mapping=D4_EMPLOYMENT_STATUS_MAP, exclude_values={99})
        bar_chart_horizontal(tab_d4, "Զբաղվածություն", height=500)
        show_table_expander(tab_d4, "demography_employment.csv")
        
    # D4.1 - Industry (if employed)
    st.subheader("D4.1. Գործունեության ոլորտ")
    if "D41" in df.columns:
        tab_d41 = freq_single(df, "D41", mapping=D4_1_INDUSTRY_MAP, exclude_values={99})
        bar_chart_horizontal(tab_d41, "Գործունեության ոլորտ", height=600)
        show_table_expander(tab_d41, "demography_industry.csv")
        
    st.markdown("---")
    
    # D6 - Income
    st.subheader("D6. Անձնական եկամուտ")
    if "D6" in df.columns:
        tab_d6 = freq_single(df, "D6", mapping=D6_INCOME_MAP, exclude_values={99})
        bar_chart_vertical(tab_d6, "Եկամուտ")
        show_table_expander(tab_d6, "demography_income.csv")
