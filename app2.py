import pandas as pd
from rapidfuzz import process, fuzz

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    # ensure required columns exist (helpful if CSV headers vary)
    required = ["VendorID", "vendorName", "productID", "productName", "productPrice"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"normalize: missing columns {missing}. Have: {list(df.columns)}")

    out = df[required].copy()  # <-- copy() with parentheses

    # Cast to string where appropriate (prevents .str errors)
    out["vendorName"]  = out["vendorName"].astype(str)
    out["productName"] = out["productName"].astype(str)
    out["VendorID"]    = out["VendorID"].astype(str)
    out["productID"]   = out["productID"].astype(str)

    # Clean ONLY vendor names (products stay raw)
    out["vendorName_clean"] = (
        out["vendorName"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )

    # Prices numeric
    out["productPrice"] = pd.to_numeric(out["productPrice"], errors="coerce")

    return out

# Fuzzy-align vendor and product names in c1 with c2, overwrite c1 *_clean values if match found
def fuzzy_align_names(c1: pd.DataFrame, c2: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:
    out = c1.copy()
    # vendors
    choices_vendor = c2["vendorName_clean"].tolist()
    best_vendor = out["vendorName_clean"].apply(
        lambda x: process.extractOne(x, choices_vendor, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
    )
    out["vendorName_clean"] = [
        match[0] if match else orig
        for orig, match in zip(out["vendorName_clean"], best_vendor)
    ]
    # # products
    # choices_prod = c2["productName_clean"].tolist()
    # best_prod = out["productName_clean"].apply(
    #     lambda x: process.extractOne(x, choices_prod, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
    # )
    # out["productName_clean"] = [
    #     match[0] if match else orig
    #     for orig, match in zip(out["productName_clean"], best_prod)
    # ]
    return out

# Build vendor index table: show which vendors exist in both companies or only one
def build_vendor_index(c1: pd.DataFrame, c2: pd.DataFrame) -> pd.DataFrame:
    v1 = c1[["VendorID", "vendorName", "vendorName_clean"]].drop_duplicates("vendorName_clean")
    v2 = c2[["VendorID", "vendorName", "vendorName_clean"]].drop_duplicates("vendorName_clean")
    vendors = v1.merge(v2, on="vendorName_clean", how="outer", suffixes=("_c1", "_c2"), indicator=True)
    vendors["match_status"] = vendors["_merge"].map(
        {"both": "Matched", "left_only": "Only in Company1", "right_only": "Only in Company2"}
    )
    return vendors.drop(columns=["_merge"])

# Deduplicate rows: keep only the lowest price per (vendor, product)
def deduplicate_min_price(df: pd.DataFrame) -> pd.DataFrame:
    need = ["vendorName_clean", "productName", "productPrice"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"deduplicate_min_price: missing {missing}")

    df2 = df.sort_values(
        ["vendorName_clean", "productName", "productPrice"],
        ascending=[True, True, True]
    )
    return df2.drop_duplicates(["vendorName_clean", "productName"], keep="first").reset_index(drop=True)

def build_item_matches(c1, c2):
    c1 = c1.copy(); c2 = c2.copy()
    c1["productName_join"] = c1["productName"]
    c2["productName_join"] = c2["productName"]
    keys = ["vendorName_clean", "productName_join"]

    left = c1.rename(columns={
        "VendorID": "VendorID_c1",
        "vendorName": "vendorName_c1",
        "productID": "productID_c1",
        "productName": "productName_c1",
        "productPrice": "productPrice_c1",
    })
    right = c2.rename(columns={
        "VendorID": "VendorID_c2",
        "vendorName": "vendorName_c2",
        "productID": "productID_c2",
        "productName": "productName_c2",
        "productPrice": "productPrice_c2",
    })

    items = left.merge(right, on=keys, how="outer", indicator=True).drop(columns=["productName_join"])
    items["match_status"] = items["_merge"].map({
        "both": "Matched",
        "left_only": "Only in Company1",
        "right_only": "Only in Company2",
    })

    both = items["match_status"] == "Matched"
    p1, p2 = items["productPrice_c1"], items["productPrice_c2"]
    rel = pd.Series(index=items.index, dtype="object")
    rel[both & (p1 > p2)] = "Company1 Higher"
    rel[both & (p1 < p2)] = "Company1 Lower"
    rel[both & (p1 == p2)] = "Same"
    items["price_relation_vs_c2"] = rel
    return items

# Calculate percentage safely (return 0 if denominator is 0)
def percent(n, d):
    return 0.0 if d == 0 else round(100.0 * n / d, 2)

# function to find the vendors with exclusive products 
def find_vendors_with_exclusive_products(c1: pd.DataFrame, c2: pd.DataFrame) -> list:
    """
    Return vendor names that have products only in c1 or only in c2.
    """
    c1_pairs = c1[["vendorName_clean", "productName"]].drop_duplicates()
    c2_pairs = c2[["vendorName_clean", "productName"]].drop_duplicates()

    merged = c1_pairs.merge(
        c2_pairs,
        on=["vendorName_clean", "productName"],
        how="outer",
        indicator=True
    )
    # Vendors that have exclusive products
    exclusive_vendors = merged.loc[merged["_merge"] != "both", "vendorName_clean"].unique().tolist()

    return exclusive_vendors





# app.py
import pandas as pd
import streamlit as st
import altair as alt
from help import (
    normalize,
    fuzzy_align_names,
    build_vendor_index,
    deduplicate_min_price,
    build_item_matches,
    percent,
    find_vendors_with_exclusive_products
)

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
st.markdown('<span class="small-muted">Vendors & Items comparison dashboard</span>', unsafe_allow_html=True)

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
    st.subheader("Items Price Comparison (Company1 vs Company2)")
    st.write(f"- **Company1 Higher-Priced:** {c1_higher} items ({percent(c1_higher, len(matched_only))}%)")
    st.write(f"- **Company1 Lower-Priced:** {c1_lower} items ({percent(c1_lower, len(matched_only))}%)")
    st.write(f"- **Same Price:** {same} ({percent(same, len(matched_only))}%)")

with right:
    pie_df = pd.DataFrame({
        "Comparison": ["C1 Higher", "C1 Lower", "Same"],
        "Count": [c1_higher, c1_lower, same],
    })
    chart = (
        alt.Chart(pie_df)
        .mark_bar()
        .encode(
            x=alt.X("Comparison:N", sort=["C1 Higher","C1 Lower-priced","Same"], title=None),
            y=alt.Y("Count:Q", title="Count"),
            color=alt.Color("Comparison:N",
                scale=alt.Scale(
                    domain=["C1 Higher","C1 Lower","Same"],
                    range=["#2563EB","#F97316","#10B981"]  # blue / orange / green
                ),
                legend=None
            ),
            tooltip=["Comparison","Count"]
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)

st.divider()

# ---------------------------
# UI: Item details for a chosen matched vendor
# ---------------------------
st.subheader("Items by Vendor (Matched Names)")

matched_vendor_names = vendors.loc[vendors["match_status"] == "Matched", "vendorName_clean"].sort_values().unique()

if len(matched_vendor_names) == 0:
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

        # Tiny per-vendor KPIs
        sub1, sub2, sub3 = st.columns(3)
        v_c1_higher = (imatched["price_relation_vs_c2"] == "Company1 Higher").sum()
        v_c1_lower  = (imatched["price_relation_vs_c2"] == "Company1 Lower").sum()
        v_same      = (imatched["price_relation_vs_c2"] == "Same").sum()
        denom = len(imatched)
        sub1.metric("Company 1 Higher", f"{v_c1_higher} ({percent(v_c1_higher, denom)}%)")
        sub2.metric("Company 1 Lower",  f"{v_c1_lower} ({percent(v_c1_lower, denom)}%)")
        sub3.metric("Same",              f"{v_same} ({percent(v_same, denom)}%)")

    # Items that exist only in one of the companies
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

# ---------------------------
# Footer
# ---------------------------

st.subheader("Vendors with exclusive items")

exclusive_vendor_names = find_vendors_with_exclusive_products(c1, c2)

if len(exclusive_vendor_names) == 0:
    st.info("No vendors with exclusive items.")
else:
    # Pretty label: prefer original C1/C2 name if known, else show clean
    def pretty_vendor_label(clean_name: str) -> str:
        row = vendors.loc[vendors["vendorName_clean"] == clean_name]
        if not row.empty:
            for col in ["vendorName_c1", "vendorName_c2"]:
                s = row[col].dropna()
                if not s.empty:
                    return s.iloc[0]
        return clean_name

    selected_vendor_clean_ex = st.selectbox(
        "Choose a vendor (has exclusive items)",
        options=exclusive_vendor_names,
        format_func=pretty_vendor_label
    )

    iview = items[items["vendorName_clean"] == selected_vendor_clean_ex].copy()

    # Show ONLY the unmatched items for this vendor
    st.markdown("**Exclusive / Unmatched Items**")
    only_c1 = iview[iview["match_status"] == "Only in Company1"]
    only_c2 = iview[iview["match_status"] == "Only in Company2"]

    if not only_c1.empty or not only_c2.empty:
        st.write("Only in Company1")
        if not only_c1.empty:
            st.dataframe(
                only_c1[["productName_c1", "productID_c1", "productPrice_c1"]]
                .rename(columns={
                    "productName_c1": "productName (C1)",
                    "productID_c1": "productID (C1)",
                    "productPrice_c1": "productPrice (C1)",
                }),
                use_container_width=True, height=200
            )
        else:
            st.write("—")

        st.write("Only in Company2")
        if not only_c2.empty:
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
            st.write("—")
    else:
        st.write("—")