# app.py
import pandas as pd
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
def load_sheets(): 
    c1 = pd.read_csv("company1.csv")
    c2 = pd.read_csv("company2.csv")
    return c1, c2

c1, c2 = load_sheets()
print("c1_______________________________________")
print(c1["vendorName"].unique())
print("_______________________________________")
print("c2_______________________________________")
print(c2["vendorName"].unique())
print("_______________________________________")
# c1 = normalize(c1)
# # print(c1.columns)
# c2 = normalize(c2)
# duplicates = c2[c2.duplicated(subset=["vendorName", "productName"], keep=False)]
# print(duplicates)   # first 10 rows


# print(c2.columns)
# df = c1.merge(c2, on=["vendorName", "productName"], how="inner")
# matched_count = df[["vendorName", "productName"]].drop_duplicates().shape[0]
# print(matched_count) 
unique_pairs = c1[["vendorName", "productName"]].drop_duplicates()
print("Unique vendor-product pairs:", len(unique_pairs))
unique_pairs = c2[["vendorName", "productName"]].drop_duplicates()
print("Unique vendor-product pairs:", len(unique_pairs))

grouped = c1.groupby(["vendorName", "productName"])["productPrice"].count().reset_index(name="price_count")

print(grouped)