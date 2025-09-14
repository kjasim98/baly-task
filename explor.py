# app.py
import pandas as pd
from help import (
    normalize,
    fuzzy_align_names,
    build_vendor_index,
    deduplicate_min_price,
    build_item_matches,
    percent,
    find_vendors_with_exclusive_products
)

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["VendorID", "vendorName", "productID", "productName", "productPrice"]
    df = df[cols].copy()
    # Clean strings
    for c in ["vendorName", "productName"]:
        df[c] = df[c].astype(str).str.strip()
        df[c + "_clean"] = df[c].str.lower().str.replace(r"\s+", " ", regex=True)
    # Types
    df["VendorID"] = df["VendorID"].astype(str)
    df["productID"] = df["productID"].astype(str)
    df["productPrice"] = pd.to_numeric(df["productPrice"], errors="coerce")
    return df
# def load_sheets(): 
#     c1 = pd.read_csv("company1.csv")
#     c2 = pd.read_csv("company2.csv")
#     return c1, c2

# c1, c2 = load_sheets()
# print("c1_______________________________________")
# print(c1["vendorName"].unique())
# print("_______________________________________")
# print("c2_______________________________________")
# print(c2["vendorName"].unique())
# print("_______________________________________")
# # c1 = normalize(c1)
# # # print(c1.columns)
# # c2 = normalize(c2)
# # duplicates = c2[c2.duplicated(subset=["vendorName", "productName"], keep=False)]
# # print(duplicates)   # first 10 rows


# # print(c2.columns)
# # df = c1.merge(c2, on=["vendorName", "productName"], how="inner")
# # matched_count = df[["vendorName", "productName"]].drop_duplicates().shape[0]
# # print(matched_count) 
# unique_pairs = c1[["vendorName", "productName"]].drop_duplicates()
# print("Unique vendor-product pairs:", len(unique_pairs))
# unique_pairs = c2[["vendorName", "productName"]].drop_duplicates()
# print("Unique vendor-product pairs:", len(unique_pairs))

# grouped = c1.groupby(["vendorName", "productName"])["productPrice"].count().reset_index(name="price_count")

# print(grouped)
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
print(c1.head())
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
    print(merged.head())

    # Vendors that have exclusive products
    exclusive_vendors = merged.loc[merged["_merge"] != "both", "vendorName_clean"].unique().tolist()

    return exclusive_vendors
ex = find_vendors_with_exclusive_products(c1,c2)
print(ex)