# app.py
import pandas as pd
import streamlit as st
from help import normalize, fuzzy_align_names, build_vendor_index, deduplicate_min_price, build_item_matches, percent

# Configure the Streamlit page (title + full-width layout)
st.set_page_config(page_title="Vendors & Items Index", layout="wide")


# ---------------------------
# Data loading
# ---------------------------
@st.cache_data
def load_sheets():
    """Read both company CSVs once and cache them for performance."""
    c1 = pd.read_csv("company1.csv")
    c2 = pd.read_csv("company2.csv")
    return c1, c2


# ---------------------------
# Prepare data
# ---------------------------
c1_raw, c2_raw = load_sheets()

# Standardize columns, add *_clean fields, and fix types
c1 = normalize(c1_raw)
c2 = normalize(c2_raw)

# If a vendor lists a product multiple times with different prices,
# keep only the row with the minimum price (prevents duplicate merges later)
c1 = deduplicate_min_price(c1)
c2 = deduplicate_min_price(c2)

# Make c1 vendor/product names align to c2 using fuzzy matching
# (after this, exact joins on *_clean are more likely to succeed)
c1 = fuzzy_align_names(c1, c2, threshold=90)

# Build vendor and item match tables based on the cleaned names
vendors = build_vendor_index(c1, c2)
# items contain product-level matches and price comparison info
items = build_item_matches(c1, c2)


# ---------------------------
# KPIs / summary numbers
# ---------------------------
total_vendors_c1 = c1["vendorName_clean"].nunique()
total_vendors_c2 = c2["vendorName_clean"].nunique()
matched_vendors = (vendors["match_status"] == "Matched").sum()

total_items_c1 = len(c1)
total_items_c2 = len(c2)
matched_items = (items["match_status"] == "Matched").sum()

# Counts for price relationship (computed only among matched items)
matched_only = items[items["match_status"] == "Matched"].copy()
c1_higher = (matched_only["price_relation_vs_c2"] == "Company1 Higher").sum()
c1_lower  = (matched_only["price_relation_vs_c2"] == "Company1 Lower").sum()
same      = (matched_only["price_relation_vs_c2"] == "Same").sum()


# ---------------------------
# UI: Header + KPIs
# ---------------------------
st.title("Vendors & Items Index")
st.caption("___")

# Six quick metrics across both companies
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Vendors (Company 1)", total_vendors_c1)
kpi2.metric("Vendors (Company 2)", total_vendors_c2)
kpi3.metric("Matched Vendors", matched_vendors)
kpi4.metric("Items (Company 1)", total_items_c1)
kpi5.metric("Items (Company 2)", total_items_c2)
kpi6.metric("Matched Items", matched_items)

st.divider()


# ---------------------------
# UI: Price comparison overview
# ---------------------------
left, right = st.columns([1, 1])
with left:
    st.subheader("Price Comparison (Company1 vs Company2)")
    st.write(f"- **Company1 Higher:** {c1_higher} ({percent(c1_higher, len(matched_only))}%)")
    st.write(f"- **Company1 Lower:** {c1_lower} ({percent(c1_lower, len(matched_only))}%)")
    st.write(f"- **Same Price:** {same} ({percent(same, len(matched_only))}%)")

with right:
    # Simple bar view of higher/lower/same
    pie_df = pd.DataFrame({
        "Comparison": ["C1 Higher", "C1 Lower", "Same"],
        "Count": [c1_higher, c1_lower, same],
    })
    st.bar_chart(pie_df.set_index("Comparison"))

st.divider()


# ---------------------------
# UI: Item details for a chosen matched vendor
# ---------------------------
st.subheader("Items by Vendor (Matched Names)")
matched_vendor_names = vendors.loc[vendors["match_status"] == "Matched", "vendorName_clean"].sort_values().unique()

if len(matched_vendor_names) == 0:
    # No matched vendors found at all
    st.info("No matched vendors found.")
else:
    # Friendly label: show the original C1 name if available
    selected_vendor_clean = st.selectbox(
        "Choose a vendor (matched across both companies)",
        options=matched_vendor_names,
        format_func=lambda x: vendors.loc[vendors["vendorName_clean"] == x, "vendorName_c1"].dropna().iloc[0]
            if not vendors.loc[vendors["vendorName_clean"] == x, "vendorName_c1"].dropna().empty
            else x
    )

    # Slice items down to the chosen vendor
    iview = items[items["vendorName_clean"] == selected_vendor_clean].copy()

    # Show items that exist in both companies (same product name)
    st.markdown("**Matched Items (same product name across both)**")
    imatched = iview[iview["match_status"] == "Matched"].copy()
    if imatched.empty:
        st.write("No matched items for this vendor.")
    else:
        # Focus on human-readable product names and prices side by side
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
            height=300
        )

        # Tiny per-vendor KPIs for quick read
        sub1, sub2, sub3 = st.columns(3)
        v_c1_higher = (imatched["price_relation_vs_c2"] == "Company1 Higher").sum()
        v_c1_lower  = (imatched["price_relation_vs_c2"] == "Company1 Lower").sum()
        v_same      = (imatched["price_relation_vs_c2"] == "Same").sum()
        denom = len(imatched)
        sub1.metric("Company 1 Higher", f"{v_c1_higher} ({percent(v_c1_higher, denom)}%)")
        sub2.metric("Company 1 Lower",  f"{v_c1_lower} ({percent(v_c1_lower, denom)}%)")
        sub3.metric("Same",              f"{v_same} ({percent(v_same, denom)}%)")

    # Items that exist only in one of the companies (handy to spot catalog gaps)
    only_c1 = iview[iview["match_status"] == "Only in Company1"]
    only_c2 = iview[iview["match_status"] == "Only in Company2"]

    if not (only_c1.empty or only_c2.empty):
        st.markdown("**Unmatched Items**")
        st.write("Only in Company1")
        if only_c1.empty:
            st.write("—")
        else:
            st.dataframe(
                only_c1[["productName_c1", "productID_c1", "productPrice_c1"]]
                .rename(columns={
                    "productName_c1": "productName (C1)",
                    "productID_c1": "productID (C1)",
                    "productPrice_c1": "productPrice (C1)",
                }),
                use_container_width=True, height=200
            )

        st.write("Only in Company2")
        if only_c2.empty:
            st.write("—")
        else:
            st.dataframe(
                only_c2[["productName_c2", "productID_c2", "productPrice_c2"]]
                .rename(columns={
                    "productName_c2": "productName (C2)",
                    "productID_c2": "productID (C2)",
                    "productPrice_c2": "productPrice (C2)",
                }),
                use_container_width=True, height=200
            )
    else:
        # If either side has no unmatched items, show a simple message
        st.markdown("**No Unmatched Items Found**")
        st.write("—")

st.divider()


# ---------------------------
# Footer
# ---------------------------
st.caption("_____")