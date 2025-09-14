# app.py

import pandas as pd
import streamlit as st
import altair as alt

# Import utility functions from help.py
from help import (
    normalize,
    deduplicate_max_price,
    fuzzy_align_names,
    build_vendor_index,
    build_item_matches,
    percent,
    get_vendors_with_price_duplicates,
    get_vendor_discounts
)

# ----------------------------- Page setup -----------------------------
st.set_page_config(page_title="Vendors & Items Index", layout="wide")

# ----------------------------- Data Load -----------------------------
# Cached function to load both company data sheets
@st.cache_data
def load_sheets():
    c1 = pd.read_csv("company1.csv")
    c2 = pd.read_csv("company2.csv")
    return c1, c2

# Load raw data
c1_raw, c2_raw = load_sheets()

# ----------------------------- Pipeline -----------------------------
# Step 1: Normalize both company datasets (cleans text, standardizes units, converts prices)
c1 = normalize(c1_raw)
c2 = normalize(c2_raw)

# Step 2: Fuzzy match c1 to c2 on vendor and product names (adjust threshold if needed)
c1 = fuzzy_align_names(c1, c2, threshold=80)

# Step 3: Build index of vendors match
vendors = build_vendor_index(c1, c2)

# Get vendor names with duplicates from both companies
vendors_c1 = get_vendors_with_price_duplicates(c1)
vendors_c2 = get_vendors_with_price_duplicates(c2)

c1_c = c1.copy()
c2_c = c2.copy()

# Step 4: Remove duplicates by cleaned vendor/product and keep only the lowest price
c1 = deduplicate_max_price(c1)
c2 = deduplicate_max_price(c2)

# Step 5: Build matched items between both datasets
items   = build_item_matches(c1, c2)

# ----------------------------- KPIs -----------------------------
# Calculate summary metrics for vendors and items
total_vendors_c1 = c1["vendorName_clean"].nunique()
total_vendors_c2 = c2["vendorName_clean"].nunique()
matched_vendors  = (vendors["match_status"] == "Matched").sum()

total_items_c1 = len(c1)
total_items_c2 = len(c2)
matched_items  = (items["match_status"] == "Matched").sum()

# Analyze price relationships only for matched items
matched_only   = items[items["match_status"] == "Matched"].copy()
c1_higher      = (matched_only["price_relation_vs_c2"] == "Company1 Higher").sum()
c1_lower       = (matched_only["price_relation_vs_c2"] == "Company1 Lower").sum()
same_price     = (matched_only["price_relation_vs_c2"] == "Same").sum()

# ----------------------------- Header -----------------------------
# Title and KPI metric display
st.title("Vendors & Items Index")
st.caption("Vendors & Items comparison dashboard")

# Vendors KPIs
st.markdown("###  Vendor Overview")
v1, v2, v3 = st.columns(3)
v1.metric("Company 1 Vendors", total_vendors_c1)
v2.metric("Company 2 Vendors", total_vendors_c2)
v3.metric("Matched Vendors", matched_vendors)

# Items KPIs
st.markdown("###  Product Overview")
i1, i2, i3 = st.columns(3)
i1.metric("Company 1 Items", total_items_c1)
i2.metric("Company 2 Items", total_items_c2)
i3.metric("Matched Items", matched_items)

st.divider()

# ----------------------- Price Comparison Overview -----------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("Items Price Comparison (Company1 vs Company2)")
    denom = len(matched_only)
    st.write(f"- **Company1 Higher-Priced:** {c1_higher} items ({percent(c1_higher, denom)}%)")
    st.write(f"- **Company1 Lower-Priced:** {c1_lower} items ({percent(c1_lower, denom)}%)")
    st.write(f"- **Same Price:** {same_price} ({percent(same_price, denom)}%)")

with right:
    # Create bar chart to show comparison
    pie_df = pd.DataFrame({
        "Comparison": ["C1 Higher", "C1 Lower", "Same"],
        "Count": [c1_higher, c1_lower, same_price],
    })
    chart = (
        alt.Chart(pie_df)
        .mark_bar()
        .encode(
            x=alt.X("Comparison:N", sort=["C1 Higher", "C1 Lower", "Same"], title=None),
            y=alt.Y("Count:Q", title="Count"),
            color=alt.Color(
                "Comparison:N",
                scale=alt.Scale(
                    domain=["C1 Higher", "C1 Lower", "Same"],
                    range=["#2563EB", "#F97316", "#10B981"],
                ),
                legend=None
            ),
            tooltip=["Comparison", "Count"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)

st.divider()

# ----------------------- Items by Vendor (Matched Only) -----------------------
st.subheader("Items by Vendor (Matched Names)")

# Get list of vendors that are matched
matched_vendor_names = vendors.loc[vendors["match_status"] == "Matched", "vendorName_clean"] \
                             .sort_values().unique()

# Helper to get the readable label from the clean name
def pretty_vendor_label(clean_name: str) -> str:
    row = vendors.loc[vendors["vendorName_clean"] == clean_name]
    if not row.empty:
        # Prefer original name from c1, then c2, else fallback to clean name
        for col in ["vendorName_c1", "vendorName_c2"]:
            s = row[col].dropna()
            if not s.empty:
                return s.iloc[0]
    return clean_name

# If there are no matches, show info box
if len(matched_vendor_names) == 0:
    st.info("No matched vendors found.")
else:
    # Dropdown to select a specific matched vendor
    selected_vendor_clean = st.selectbox(
        "Choose a vendor (matched across both companies)",
        options=matched_vendor_names,
        format_func=pretty_vendor_label
    )

    # Filter data for selected vendor
    iview = items[items["vendorName_clean"] == selected_vendor_clean].copy()

    st.markdown("**Matched Items (same product after cleaning)**")
    imatched = iview[iview["match_status"] == "Matched"].copy()
    if imatched.empty:
        st.write("No matched items for this vendor.")
    else:
        # Show matched items with prices and relation
        show_cols = [
            "productName_c1", "productPrice_c1",
            "productName_c2", "productPrice_c2",
            "price_relation_vs_c2",
        ]
        st.dataframe(
            imatched[show_cols].rename(columns={
                "productName_c1": "productName (C1)",
                "productPrice_c1": "productPrice (C1)",
                "productName_c2": "productName (C2)",
                "productPrice_c2": "productPrice (C2)",
                "price_relation_vs_c2": "C1 vs C2",
            }),
            use_container_width=True,
            height=320
        )

        # Show small KPI cards for selected vendor
        v_c1_higher = (imatched["price_relation_vs_c2"] == "Company1 Higher").sum()
        v_c1_lower  = (imatched["price_relation_vs_c2"] == "Company1 Lower").sum()
        v_same      = (imatched["price_relation_vs_c2"] == "Same").sum()
        denom_v = len(imatched)
        s1, s2, s3 = st.columns(3)
        s1.metric("Company 1 Higher", f"{v_c1_higher} ({percent(v_c1_higher, denom_v)}%)")
        s2.metric("Company 1 Lower",  f"{v_c1_lower} ({percent(v_c1_lower, denom_v)}%)")
        s3.metric("Same",              f"{v_same} ({percent(v_same, denom_v)}%)")

st.divider()


# Combine and deduplicate vendor names
all_problem_vendors = sorted(set(vendors_c1 + vendors_c2))

st.title("Vendors That Offered Discounts")
selected_vendor = st.selectbox("Select a Vendor", all_problem_vendors)

# ---------------------------
# Show Discount Data
# ---------------------------
print(get_vendor_discounts("bluesea imports", c1_c, c2_c))
if selected_vendor:
    # Get discount data
    df_result = get_vendor_discounts(selected_vendor, c1_c, c2_c)

    # Reorder columns to desired order
    desired_order = [
        "productName",
        "original_price_c1", "discounted_price_c1", "discount_percent_c1",
        "original_price_c2", "discounted_price_c2", "discount_percent_c2"
    ]

    # Reorder only if all columns exist
    df_result = df_result[[col for col in desired_order if col in df_result.columns]]

    # Display
    st.markdown(f"### 💰 Discount Breakdown for: **{selected_vendor}**")
    st.dataframe(df_result, use_container_width=True)