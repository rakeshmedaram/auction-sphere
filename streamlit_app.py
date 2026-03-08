import streamlit as st

st.title("Auction Sphere - Online Auction System")

st.header("Create Auction")

product = st.text_input("Product Name")
base_price = st.number_input("Base Price")

if st.button("Create Auction"):
    st.success(f"Auction created for {product} starting at ₹{base_price}")

st.header("Place Bid")

bid = st.number_input("Enter Bid Amount")

if st.button("Submit Bid"):
    st.success(f"Bid placed: ₹{bid}")