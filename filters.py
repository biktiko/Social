import streamlit as st
import pandas as pd
import numpy as np

# ----------------------
# Constants
# ----------------------
PINK = "#ff3366"
WHITE = "#ffffff"
GRAY = "#7a8c8e"
YELLOW = "#ffcc66"


def render_filters(df: pd.DataFrame, key_prefix: str = "") -> pd.DataFrame:
    """
    Render filters in an expander and return filtered dataframe.
    
    Args:
        df: Source dataframe
        key_prefix: Unique prefix for widget keys to avoid conflicts
        
    Returns:
        Filtered dataframe
    """
    filt_df = df.copy()
    
    with st.expander("🔍 Ֆիլտրեր", expanded=False):
        st.markdown(f"""
        <style>
        .filter-section {{
            background-color: {WHITE};
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #7a8c8e;
        }}
        </style>
        """, unsafe_allow_html=True)
        
        # Create columns for filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Sex filter (S2)
            if "S2" in df.columns:
                sex_options = ["Բոլորը"] + sorted(
                    [x for x in df["S2"].dropna().unique().tolist()]
                )
                sel_sex = st.multiselect(
                    "Սեռ", 
                    options=sex_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_sex"
                )
                if "Բոլորը" not in sel_sex and sel_sex:
                    filt_df = filt_df[filt_df["S2"].isin(sel_sex)]
            
            # Age group filter
            if "AGE_GRP" in df.columns:
                age_options = ["Բոլորը"] + sorted(
                    [x for x in df["AGE_GRP"].dropna().unique().tolist()]
                )
                sel_age = st.multiselect(
                    "Տարիքի խումբ", 
                    options=age_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_age"
                )
                if "Բոլորը" not in sel_age and sel_age:
                    filt_df = filt_df[filt_df["AGE_GRP"].isin(sel_age)]
        
        with col2:
            # City (S3)
            if "S3" in df.columns:
                city_options = ["Բոլորը"] + sorted(
                    [x for x in df["S3"].dropna().unique().tolist()]
                )
                sel_city = st.multiselect(
                    "Բնակավայր", 
                    options=city_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_city"
                )
                if "Բոլորը" not in sel_city and sel_city:
                    filt_df = filt_df[filt_df["S3"].isin(sel_city)]
            
            # Region (S4) - ignore zeros
            if "S4" in df.columns:
                s4_series = filt_df["S4"].replace({0: np.nan})
                s4_options = ["Բոլորը"] + sorted(
                    [x for x in s4_series.dropna().unique().tolist()]
                )
                sel_s4 = st.multiselect(
                    "Վարչատարածք (S4)", 
                    options=s4_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_s4"
                )
                if "Բոլորը" not in sel_s4 and sel_s4:
                    filt_df = filt_df[filt_df["S4"].isin(sel_s4)]
        
        with col3:
            # Settlement type (S5)
            if "S5" in df.columns:
                s5_options = ["Բոլորը"] + sorted(
                    [x for x in df["S5"].dropna().unique().tolist()]
                )
                sel_s5 = st.multiselect(
                    "Բնակավայրի տեսակ (S5)", 
                    options=s5_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_s5"
                )
                if "Բոլորը" not in sel_s5 and sel_s5:
                    filt_df = filt_df[filt_df["S5"].isin(sel_s5)]
            
            # Device
            if "Dev_lbl" in df.columns:
                dev_options = ["Բոլորը"] + sorted(
                    [x for x in df["Dev_lbl"].dropna().unique().tolist()]
                )
                sel_dev = st.multiselect(
                    "Հեռախոսի տեսակ", 
                    options=dev_options, 
                    default=["Բոլորը"],
                    key=f"{key_prefix}_dev"
                )
                if "Բոլորը" not in sel_dev and sel_dev:
                    filt_df = filt_df[filt_df["Dev_lbl"].isin(sel_dev)]

        st.markdown("---")
        st.markdown("**Սոցիալ-դեմոգրաֆիական ֆիլտրեր**")
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            # Marital Status (D1)
            if "D1" in df.columns:
                # Import mapping locally to avoid circular import or just use raw values if mapping not available here
                # Better to map values for display if possible, but for filter raw values or mapped values in df?
                # The df has raw values (1, 2, etc). We should probably map them for display in filter.
                # Let's assume we want to filter by the mapped label if possible, or just show raw.
                # To keep it simple and consistent with other filters (which seem to use raw values or pre-mapped columns like Dev_lbl),
                # we will use raw values unless we map them on the fly.
                # Let's map them on the fly for display.
                from mappings import D1_MARITAL_STATUS_MAP
                
                d1_unique = sorted([x for x in df["D1"].dropna().unique().tolist() if x != 99])
                d1_options = ["Բոլորը"] + [D1_MARITAL_STATUS_MAP.get(x, str(x)) for x in d1_unique]
                
                sel_d1_label = st.multiselect(
                    "Ամուսնական կարգավիճակ",
                    options=d1_options,
                    default=["Բոլորը"],
                    key=f"{key_prefix}_d1"
                )
                
                if "Բոլորը" not in sel_d1_label and sel_d1_label:
                    # Reverse map to find selected IDs
                    selected_ids = [k for k, v in D1_MARITAL_STATUS_MAP.items() if v in sel_d1_label]
                    # Also handle unmapped if any
                    selected_ids.extend([x for x in d1_unique if str(x) in sel_d1_label])
                    filt_df = filt_df[filt_df["D1"].isin(selected_ids)]

        with col5:
            # Employment (D4)
            if "D4" in df.columns:
                from mappings import D4_EMPLOYMENT_STATUS_MAP
                d4_unique = sorted([x for x in df["D4"].dropna().unique().tolist() if x != 99])
                d4_options = ["Բոլորը"] + [D4_EMPLOYMENT_STATUS_MAP.get(x, str(x)) for x in d4_unique]
                
                sel_d4_label = st.multiselect(
                    "Զբաղվածություն",
                    options=d4_options,
                    default=["Բոլորը"],
                    key=f"{key_prefix}_d4"
                )
                
                if "Բոլորը" not in sel_d4_label and sel_d4_label:
                    selected_ids = [k for k, v in D4_EMPLOYMENT_STATUS_MAP.items() if v in sel_d4_label]
                    selected_ids.extend([x for x in d4_unique if str(x) in sel_d4_label])
                    filt_df = filt_df[filt_df["D4"].isin(selected_ids)]

        with col6:
            # Income (D6)
            if "D6" in df.columns:
                from mappings import D6_INCOME_MAP
                d6_unique = sorted([x for x in df["D6"].dropna().unique().tolist() if x != 99])
                d6_options = ["Բոլորը"] + [D6_INCOME_MAP.get(x, str(x)) for x in d6_unique]
                
                sel_d6_label = st.multiselect(
                    "Եկամուտ",
                    options=d6_options,
                    default=["Բոլորը"],
                    key=f"{key_prefix}_d6"
                )
                
                if "Բոլորը" not in sel_d6_label and sel_d6_label:
                    selected_ids = [k for k, v in D6_INCOME_MAP.items() if v in sel_d6_label]
                    selected_ids.extend([x for x in d6_unique if str(x) in sel_d6_label])
                    filt_df = filt_df[filt_df["D6"].isin(selected_ids)]
        
        # Show filter summary
        total_records = len(df)
        filtered_records = len(filt_df)
        GRAY = "#7a8c8e"
        st.markdown(f"""
        <div style='margin-top: 1rem; padding: 0.5rem; background-color: {GRAY}20; border-radius: 4px; text-align: center;'>
            <b>Մարդկանց քանակը:</b> {filtered_records:,} / {total_records:,}
        </div>
        """, unsafe_allow_html=True)
    
    return filt_df
