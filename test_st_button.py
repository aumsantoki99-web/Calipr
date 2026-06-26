import streamlit as st
import base64

with open(r"c:\Users\AUM\OneDrive\Documents\Project 1\India Runs\assets\icons\download.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

st.button(f"![icon](data:image/jpeg;base64,{img_b64}) Test Slack")
st.button("Test Slack 2")
