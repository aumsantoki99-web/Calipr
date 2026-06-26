import streamlit as st
import streamlit.components.v1 as components

st.title("JS Tunneling Test")

selected_idx = st.radio("Select", options=[0, 1, 2], key="hidden_radio")

cards_html = """
<style>
.my-card {
    padding: 20px;
    background: lightgray;
    margin: 10px;
    border-radius: 5px;
    cursor: pointer;
}
</style>
<div class="my-card" data-idx="0">Card 0</div>
<div class="my-card" data-idx="1">Card 1</div>
<div class="my-card" data-idx="2">Card 2</div>
"""
st.markdown(cards_html, unsafe_allow_html=True)

js_code = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const doc = window.parent.document;
        const cards = doc.querySelectorAll('.my-card');
        cards.forEach(card => {
            // Remove existing listener to prevent duplicates
            card.onclick = function() {
                const idx = parseInt(this.getAttribute('data-idx'));
                const radios = doc.querySelectorAll('input[type="radio"]');
                if (radios.length > idx) {
                    radios[idx].click();
                }
            };
        });
    }, 500);
});
</script>
"""
components.html(js_code, height=0, width=0)

st.write(f"Selected: {selected_idx}")
