import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from filters import render_filters
from section2 import page_section2
from section3 import page_section3
from section4 import page_section4
from section_demography import page_demography

# ----------------------
# Constants and styling
# ----------------------

PINK = "#ff3366"
WHITE = "#ffffff"
GRAY = "#7a8c8e"
YELLOW = "#ffcc66"

st.set_page_config(
    page_title="Մեդիա հետազոտություն - վիզուալ անալիտիկա",
    layout="wide"
)

# Inject basic CSS for cleaner look
st.markdown(
    f"""
    <style>
    .main {{
        background-color: {WHITE};
    }}
    h1, h2, h3, h4, h5 {{
        font-family: "Segoe UI", Arial, sans-serif;
        color: #333333;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 2rem;
    }}
    .metric-title {{
        font-size: 0.9rem;
        color: {GRAY};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ----------------------
# Authentication
# ----------------------

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["credentials"]["username"]
            and st.session_state["password"] == st.secrets["credentials"]["password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 Մուտք")
            with st.form("login_form"):
                st.text_input("Username", key="username")
                st.text_input("Password", type="password", key="password")
                st.form_submit_button("Login", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 Մուտք")
            with st.form("login_form"):
                st.text_input("Username", key="username")
                st.text_input("Password", type="password", key="password")
                st.form_submit_button("Login", on_click=password_entered)
            st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# ----------------------
# Data loading
# ----------------------

@st.cache_data
def load_data(path: str = "Media_Research.xlsx") -> pd.DataFrame:
    """Load survey data from Excel and prepare basic derived fields."""
    # читаем первый лист по умолчанию
    df = pd.read_excel(path)  

    # Standardize column names (strip spaces)
    df.columns = [c.strip() for c in df.columns]

    # Create age group
    def age_to_group(age):
        if pd.isna(age):
            return np.nan
        try:
            a = int(age)
        except Exception:
            return np.nan
        if a < 16:
            return "Մինչև 16տ"
        elif 16 <= a <= 20:
            return "16-20տ."
        elif 21 <= a <= 29:
            return "21-29տ."
        elif 30 <= a <= 39:
            return "30-39տ."
        elif 40 <= a <= 49:
            return "40-49տ."
        elif 50 <= a <= 59:
            return "50-59տ."
        elif 60 <= a <= 69:
            return "60-69տ."
        else:
            return "70 և ավելի"

    if "AGE" in df.columns:
        df["AGE_GRP"] = df["AGE"].apply(age_to_group)

    dev_map = {
        1: "Սմարթֆոն",
        2: "Սովորական բջջային հեռախոս"
    }
    if "Dev" in df.columns:
        df["Dev_lbl"] = df["Dev"].map(dev_map).fillna(df["Dev"].astype(str))

    return df


df_raw = load_data()


# ----------------------
# Helper functions
# ----------------------


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
        .configure_mark(color=PINK)
    )
    st.altair_chart(chart, use_container_width=True)


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
        .properties(height=400, title=title)
        .configure_mark(color=PINK)
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
                                range=[PINK, YELLOW, GRAY, "#4fb4d8", "#a0c4ff"]
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


def show_note():
    """Global note about refusals."""
    st.markdown(
        "<i>Ընդհանուր %-ը կարող է չլինել 100, քանի որ հարցից հրաժարումների %-ները ներկայացված չեն։</i>",
        unsafe_allow_html=True
    )

# ----------------------
# Page render functions
# ----------------------




# ----------------------
# Main
# ----------------------

page = st.sidebar.radio(
    "Բաժիններ",
    ["Դեմոգրաֆիա", "Բաժին 2 - Ռադիո և TV ունկնդրման/ դիտման վարքագիծ", "Բաժին 3 - Ռադիո և TV ալիքների վարկանիշեր", "Բաժին 4 - Այլ աղբյուրներ"],
    index=0
)

if page == "Դեմոգրաֆիա":
    page_demography(df_raw)
elif page == "Բաժին 2 - Ռադիո և TV ունկնդրման/ դիտման վարքագիծ":
    page_section2(df_raw)
elif page == "Բաժին 3 - Ռադիո և TV ալիքների վարկանիշեր":
    page_section3(df_raw)
elif page == "Բաժին 4 - Այլ աղբյուրներ":
    page_section4(df_raw)
