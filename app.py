# app.py
import pandas as pd
import streamlit as st
from help import normalize,fuzzy_align_names,build_vendor_index,deduplicate_min_price,build_item_matches,percent
st.set_page_config(page_title="Vendors & Items Index", layout="wide")
# ---------------------------
# Load
# ---------------------------
@st.cache_data
def load_sheets(): 
    c1 = pd.read_csv("company1.csv")
    c2 = pd.read_csv("company2.csv")
    return c1, c2
# ---------------------------
# Load data
# ---------------------------
c1_raw, c2_raw = load_sheets()
c1 = normalize(c1_raw)
c2 = normalize(c2_raw)

# Deduplicate inside each company
c1 = deduplicate_min_price(c1)
c2 = deduplicate_min_price(c2)

c1 = fuzzy_align_names(c1, c2, threshold=90)

vendors = build_vendor_index(c1, c2)
# print(vendors.head())
items = build_item_matches(c1, c2)

# Derived aggregates
total_vendors_c1 = c1["vendorName_clean"].nunique()
total_vendors_c2 = c2["vendorName_clean"].nunique()
matched_vendors = (vendors["match_status"] == "Matched").sum()

total_items_c1 = len(c1)
total_items_c2 = len(c2)
# print("items_____________________________")
matched_items = (items["match_status"] == "Matched").sum()

# Price comps (only matched items)
matched_only = items[items["match_status"] == "Matched"].copy()
c1_higher = (matched_only["price_relation_vs_c2"] == "Company1 Higher").sum()
c1_lower  = (matched_only["price_relation_vs_c2"] == "Company1 Lower").sum()
same      = (matched_only["price_relation_vs_c2"] == "Same").sum()

# ---------------------------
# UI
# ---------------------------


st.title("Vendors & Items Index")
st.caption("___")

# KPI row
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Vendors (Company 1)", total_vendors_c1)
kpi2.metric("Vendors (Company 2)", total_vendors_c2)
kpi3.metric("Matched Vendors", matched_vendors)
kpi4.metric("Items (Company 1)", total_items_c1)
kpi5.metric("Items (Company 2)", total_items_c2)
kpi6.metric("Matched Items", matched_items)

st.divider()

# Price comparison summary
left, right = st.columns([1, 1])
with left:
    st.subheader("Price Comparison (Company1 vs Company2)")
    st.write(f"- **Company1 Higher:** {c1_higher} ({percent(c1_higher, len(matched_only))}%)")
    st.write(f"- **Company1 Lower:** {c1_lower} ({percent(c1_lower, len(matched_only))}%)")
    st.write(f"- **Same Price:** {same} ({percent(same, len(matched_only))}%)")

with right:
    pie_df = pd.DataFrame({
        "Comparison": ["C1 Higher", "C1 Lower", "Same"],
        "Count": [c1_higher, c1_lower, same],
    })
    st.bar_chart(pie_df.set_index("Comparison"))

st.divider()

# Sidebar filters
# st.sidebar.header("Filters")
# vendor_filter_mode = st.sidebar.radio(
#     "Vendor Set",
#     ["Matched", "Only in Company1", "Only in Company2", "All"],
#     index=0
# )
# search_vendor = st.sidebar.text_input("Search vendor name (contains)")

# Vendor list view
# st.subheader("Vendors")
# vend_view = vendors.copy()
# if vendor_filter_mode != "All":
#     vend_view = vend_view[vend_view["match_status"] == vendor_filter_mode]
# if search_vendor:
#     s = search_vendor.strip().lower()
#     vend_view = vend_view[vend_view["vendorName_clean"].str.contains(s, na=False)]
# vend_cols = [
#     "vendorName_c1", "VendorID_c1", "vendorName_c2", "VendorID_c2", "match_status"
# ]
# st.dataframe(vend_view[vend_cols].rename(columns={
#     "vendorName_c1": "vendorName (C1)",
#     "VendorID_c1": "VendorID (C1)",
#     "vendorName_c2": "vendorName (C2)",
#     "VendorID_c2": "VendorID (C2)",
# }), use_container_width=True, height=300)

st.divider()

# Item details for a selected vendor (only where names match)
st.subheader("Items by Vendor (Matched Names)")
matched_vendor_names = vendors.loc[vendors["match_status"] == "Matched", "vendorName_clean"].sort_values().unique()
if len(matched_vendor_names) == 0:
    st.info("No matched vendors found.")
else:
    selected_vendor_clean = st.selectbox(
        "Choose a vendor (matched across both companies)",
        options=matched_vendor_names,
        format_func=lambda x: vendors.loc[vendors["vendorName_clean"] == x, "vendorName_c1"].dropna().iloc[0]
            if not vendors.loc[vendors["vendorName_clean"] == x, "vendorName_c1"].dropna().empty
            else x
    )

    # Filter items for that vendor
    iview = items[items["vendorName_clean"] == selected_vendor_clean].copy()

    # Show matched vs only in one company
    st.markdown("**Matched Items (same product name across both)**")
    imatched = iview[iview["match_status"] == "Matched"].copy()
    if imatched.empty:
        st.write("No matched items for this vendor.")
    else:
        # Simplify columns
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

        # Mini KPIs for this vendor
        sub1, sub2, sub3 = st.columns(3)
        v_c1_higher = (imatched["price_relation_vs_c2"] == "Company1 Higher").sum()
        v_c1_lower  = (imatched["price_relation_vs_c2"] == "Company1 Lower").sum()
        v_same      = (imatched["price_relation_vs_c2"] == "Same").sum()
        denom = len(imatched)
        sub1.metric("Company 1 Higher", f"{v_c1_higher} ({percent(v_c1_higher, denom)}%)")
        sub2.metric("Company 1 Lower",  f"{v_c1_lower} ({percent(v_c1_lower, denom)}%)")
        sub3.metric("Same",      f"{v_same} ({percent(v_same, denom)}%)")

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
        st.markdown("**No Unmatched Items Found**")
        st.write("—")

st.divider()

# Extra insights (optional)
# st.subheader("Extra Insights")
# # Top vendors by matched items
# top_match = (
#     items[items["match_status"] == "Matched"]
#     .groupby("vendorName_clean")
#     .size()
#     .sort_values(ascending=False)
#     .head(10)
#     .rename("Matched Item Count")
#     .to_frame()
# )
# if not top_match.empty:
#     st.markdown("**Top vendors by number of matched items (Top 10)**")
#     st.bar_chart(top_match)

st.caption("_____")