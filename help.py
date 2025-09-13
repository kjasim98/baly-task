import pandas as pd
from rapidfuzz import process, fuzz

# Normalize dataframe: clean vendor/product names, add *_clean columns, fix data types
def normalize(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["VendorID", "vendorName", "productID", "productName", "productPrice"]
    df = df[cols].copy()
    for c in ["vendorName", "productName"]:
        df[c] = df[c].astype(str).str.strip()
        df[c + "_clean"] = df[c].str.lower().str.replace(r"\s+", " ", regex=True)
    df["VendorID"] = df["VendorID"].astype(str)
    df["productID"] = df["productID"].astype(str)
    df["productPrice"] = pd.to_numeric(df["productPrice"], errors="coerce")
    return df

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
    # products
    choices_prod = c2["productName_clean"].tolist()
    best_prod = out["productName_clean"].apply(
        lambda x: process.extractOne(x, choices_prod, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
    )
    out["productName_clean"] = [
        match[0] if match else orig
        for orig, match in zip(out["productName_clean"], best_prod)
    ]
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
    idx = df.groupby(["vendorName_clean", "productName_clean"])["productPrice"].idxmin()
    return df.loc[idx].reset_index(drop=True)

# Build item match table: match products across vendors, compare prices if both exist
def build_item_matches(c1: pd.DataFrame, c2: pd.DataFrame) -> pd.DataFrame:
    keys = ["vendorName_clean", "productName_clean"]
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
    items = left.merge(right, on=keys, how="outer", indicator=True)

    def stat_map(x):
        if x == "both":
            return "Matched"
        if x == "left_only":
            return "Only in Company1"
        return "Only in Company2"

    items["match_status"] = items["_merge"].map(stat_map)
    items["price_relation_vs_c2"] = None
    both_mask = items["match_status"] == "Matched"
    items.loc[both_mask, "price_relation_vs_c2"] = (
        items.loc[both_mask, "productPrice_c1"]
        .compare(items.loc[both_mask, "productPrice_c2"], keep_shape=True)
        .pipe(lambda _: None)
    )
    # price comparison
    p1 = items["productPrice_c1"]
    p2 = items["productPrice_c2"]
    relation = pd.Series(index=items.index, dtype="object")
    relation[both_mask & (p1 > p2)] = "Company1 Higher"
    relation[both_mask & (p1 < p2)] = "Company1 Lower"
    relation[both_mask & (p1 == p2)] = "Same"
    items["price_relation_vs_c2"] = relation

    return items

# Calculate percentage safely (return 0 if denominator is 0)
def percent(n, d):
    return 0.0 if d == 0 else round(100.0 * n / d, 2)