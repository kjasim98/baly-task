import pandas as pd
from rapidfuzz import process, fuzz
import cleantext
from pint import UnitRegistry

# Used for unit normalization (e.g., converting 1kg to 1000g)
ureg = UnitRegistry()

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize vendor and product data.
    """
    out = df[["VendorID", "vendorName", "productID", "productName", "productPrice"]].copy()

    # Convert IDs to string type
    out["VendorID"] = out["VendorID"].astype(str)
    out["productID"] = out["productID"].astype(str)

    # Clean vendor name
    out["vendorName_clean"] = out["vendorName"].astype(str).str.lower().str.strip()

    # Normalize product name and units
    def canonicalize(prod):
        cleaned = cleantext.clean(str(prod), lower=True, no_punct=True)
        try:
            for word in cleaned.split():
                try:
                    q = ureg.Quantity(word).to_base_units()
                    normalized_unit = f"{int(q.m)} {q.u}"
                    return cleaned.replace(word, normalized_unit)
                except Exception:
                    continue
            return cleaned
        except Exception:
            return cleaned

    out["productName_clean"] = out["productName"].apply(canonicalize)

    # Convert price to numeric
    out["productPrice"] = pd.to_numeric(out["productPrice"], errors="coerce")

    return out

def fuzzy_align_names(c1: pd.DataFrame, c2: pd.DataFrame, threshold=90) -> pd.DataFrame:
    """
    Align vendor and product names from c1 to c2 using fuzzy matching.
    """
    out = c1.copy()

    for column in ["vendorName_clean", "productName_clean"]:
        choices = c2[column].dropna().unique().tolist()
        aligned = []

        for value in out[column]:
            match = process.extractOne(value, choices, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
            if match:
                aligned.append(match[0])
            else:
                aligned.append(value)

        out[column] = aligned

    return out

def deduplicate_max_price(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates and keep only the highest priced version of each item.
    """
    # Sort so that the highest price comes first
    df_sorted = df.sort_values(["vendorName_clean", "productName_clean", "productPrice"], ascending=[True, True, False])
    
    # Drop duplicates, keeping the first (which will be the highest price due to sorting)
    df_unique = df_sorted.drop_duplicates(["vendorName_clean", "productName_clean"], keep="first")
    
    return df_unique.reset_index(drop=True)

def build_vendor_index(c1, c2):
    """
    Compare vendors between two companies and return match status.
    """
    left = c1[["vendorName", "vendorName_clean"]].drop_duplicates().rename(columns={"vendorName": "vendorName_c1"})
    right = c2[["vendorName", "vendorName_clean"]].drop_duplicates().rename(columns={"vendorName": "vendorName_c2"})

    vendors = left.merge(right, on="vendorName_clean", how="outer", indicator=True)

    status_map = {
        "both": "Matched",
        "left_only": "Only in Company1",
        "right_only": "Only in Company2"
    }
    vendors["match_status"] = vendors["_merge"].map(status_map)

    return vendors

def build_item_matches(c1: pd.DataFrame, c2: pd.DataFrame) -> pd.DataFrame:
    """
    Match items from two companies and compare their prices.
    """
    keys = ["vendorName_clean", "productName_clean"]

    # Rename columns to show company source
    left = c1.rename(columns={
        "VendorID": "VendorID_c1",
        "vendorName": "vendorName_c1",
        "productID": "productID_c1",
        "productName": "productName_c1",
        "productPrice": "productPrice_c1"
    })
    right = c2.rename(columns={
        "VendorID": "VendorID_c2",
        "vendorName": "vendorName_c2",
        "productID": "productID_c2",
        "productName": "productName_c2",
        "productPrice": "productPrice_c2"
    })

    items = left.merge(right, on=keys, how="outer", indicator=True)

    # Set match status
    status_map = {
        "both": "Matched",
        "left_only": "Only in Company1",
        "right_only": "Only in Company2"
    }
    items["match_status"] = items["_merge"].map(status_map)

    # Compare prices for matched items
    rel = pd.Series(index=items.index, dtype="object")
    matched = items["match_status"] == "Matched"

    price_c1 = items["productPrice_c1"]
    price_c2 = items["productPrice_c2"]

    rel[matched & (price_c1 > price_c2)] = "Company1 Higher"
    rel[matched & (price_c1 < price_c2)] = "Company1 Lower"
    rel[matched & (price_c1 == price_c2)] = "Same"

    items["price_relation_vs_c2"] = rel

    return items

def percent(n: int, denom: int) -> int:
    """
    Calculate percentage safely.
    """
    if denom == 0:
        return 0
    return int(round(100 * n / denom))

def get_vendors_with_price_duplicates(df: pd.DataFrame) -> list:
    """
    Return a list of vendor names that have at least one product 
    with more than one distinct price.
    """
    dup = (
        df.groupby(["vendorName_clean", "productName_clean"])["productPrice"]
        .nunique()
        .reset_index(name="unique_prices")
    )

    # Keep only where the same product has more than one price
    dup = dup[dup["unique_prices"] > 1]

    # Get unique vendor names
    vendor_list = dup["vendorName_clean"].unique().tolist()
    
    return vendor_list

def get_vendor_discounts(vendor_name: str, c1: pd.DataFrame, c2: pd.DataFrame) -> pd.DataFrame:
    """
    For a given vendor, checks both c1 and c2 for duplicate product prices,
    and computes the min/max price, discounted price, and discount percentage (as % string).
    
    Returns a merged dataframe with results from both companies.
    """
    def process(df, label):
        # Filter for vendor
        vendor_df = df[df["vendorName_clean"] == vendor_name]

        # Group by product, count unique prices
        grouped = vendor_df.groupby("productName_clean")["productPrice"].agg(["min", "max", "nunique"]).reset_index()
        grouped = grouped[grouped["nunique"] > 1]  # Only keep products with >1 price

        # Rename columns
        grouped = grouped.rename(columns={
            "min": f"discounted_price_{label}",
            "max": f"original_price_{label}"
        })

        # Calculate discount %
        discount_col = f"discount_percent_{label}"
        grouped[discount_col] = (
            (grouped[f"original_price_{label}"] - grouped[f"discounted_price_{label}"]) /
            grouped[f"original_price_{label}"] * 100
        )

        # Format as percentage string (e.g., 20.5 → "20.5%")
        grouped[discount_col] = grouped[discount_col].round(2).astype(str) + "%"

        return grouped[["productName_clean", f"discounted_price_{label}", f"original_price_{label}", discount_col]]

    # Process both companies
    d1 = process(c1, "c1")
    d2 = process(c2, "c2")

    # Merge on productName (outer join to keep all)
    merged = pd.merge(d1, d2, on="productName_clean", how="outer")

    return merged