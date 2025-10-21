# streamlit_app.py
"""
ColorKart - Smart Shirt Store
-----------------------------
Now includes realistic shirt rendering using the enhanced GAN Simulator.
"""

import streamlit as st
import pandas as pd
import os
from gan_generator import generate_realistic_shirt  # GAN Simulation Module

# ============================================================
# CONFIGURATION
# ============================================================
CSV_FILE = "image_colors.csv"
IMAGE_DIR = "images_all"

st.set_page_config(
    page_title="🩵 ColorKart - Smart Shirt Store",
    layout="wide",
    page_icon="👕"
)

# ============================================================
# LOAD CSV DATA
# ============================================================
if not os.path.exists(CSV_FILE):
    st.error("❌ CSV file not found! Run your color detection script first.")
    st.stop()

df = pd.read_csv(CSV_FILE)

required_cols = ['image', 'predicted_color', 'aquarius', 'name', 'price', 'mrp', 'material']
if not all(col in df.columns for col in required_cols):
    st.error(f"❌ CSV must contain columns: {required_cols}")
    st.stop()

# ============================================================
# SESSION STATE
# ============================================================
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None
if "cart" not in st.session_state:
    st.session_state.cart = []

# ============================================================
# SIDEBAR CART
# ============================================================
st.sidebar.title("🛍 Your Cart")

if not st.session_state.cart:
    st.sidebar.info("Your cart is empty.")
else:
    total = sum(float(item['price']) for item in st.session_state.cart)
    for item in st.session_state.cart:
        st.sidebar.write(f"👕 *{item['name']}* — ₹{item['price']}")
    st.sidebar.markdown(f"### 💰 Total: ₹{total:.2f}")

    if st.sidebar.button("🧾 Checkout"):
        st.sidebar.success("✅ Order placed successfully!")
        st.session_state.cart.clear()
        st.rerun()

# ============================================================
# PRODUCT DETAILS VIEW
# ============================================================
def show_product_details(row):
    st.markdown(f"## 🩵 {row['name']} Details")

    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    img_path = os.path.join(IMAGE_DIR, row['image'])

    # ----- Real Product -----
    with col1:
        if os.path.exists(img_path):
            st.image(img_path, caption="🖼 Real Product", use_container_width=True)
        else:
            st.warning(f"⚠ Image not found: {row['image']}")

    # ----- Product Info -----
    with col2:
        price, mrp = float(row['price']), float(row['mrp'])
        discount = max(0, round((1 - price / mrp) * 100))

        st.markdown(f"""
        ### {row['name']}
        Color: *{row['predicted_color'].capitalize()}*  
        Material: *{row['material']}*  
        Accuracy: *{row['aquarius']}*  
        Price: ₹{price:.2f}  
        MRP: ₹{mrp:.2f}  
        Discount: 🏷 *{discount}% Off*
        """)

        if st.button("🛒 Add to Cart"):
            st.session_state.cart.append(dict(row))
            st.success(f"✅ {row['name']} added to cart!")

        if st.button("🔙 Back to All Products"):
            st.session_state.selected_product = None
            st.rerun()

    # ----- GAN Simulation -----
    with col3:
        st.markdown("### 🎨 GAN Shirt Simulation")
        try:
            fake_img = generate_realistic_shirt(row['predicted_color'])
            st.image(fake_img, caption=f"Generated {row['predicted_color'].capitalize()} Shirt", use_container_width=True)
        except Exception as e:
            st.error(f"❌ GAN generation failed: {e}")

    # ----- Similar Products -----
    st.markdown("---")
    st.markdown(f"### 🎯 Similar {row['predicted_color'].capitalize()} Shirts")
    similar = df[(df['predicted_color'] == row['predicted_color']) & (df['image'] != row['image'])]

    if similar.empty:
        st.info("No similar shirts found.")
    else:
        cols = st.columns(4)
        for i, (_, sim_row) in enumerate(similar.iterrows()):
            sim_img_path = os.path.join(IMAGE_DIR, sim_row['image'])
            with cols[i % 4]:
                if os.path.exists(sim_img_path):
                    if st.button(f"🧥 {sim_row['name']}", key=f"sim_{sim_row['image']}"):
                        st.session_state.selected_product = sim_row
                        st.rerun()
                    st.image(sim_img_path, caption=f"{sim_row['predicted_color']} | ₹{sim_row['price']}", use_container_width=True)
                else:
                    st.warning(f"⚠ Missing: {sim_row['image']}")

# ============================================================
# PRODUCT GRID VIEW
# ============================================================
def show_product_grid():
    st.markdown("""
    <h1 style='text-align:center; color:#1E88E5; font-family:Trebuchet MS;'>
        👕 Welcome to <b>ColorKart</b><br>
        <span style='font-size:18px; color:gray;'>Find your favorite shirts by color and style</span>
    </h1>
    <hr style='border:1px solid #ddd;'>
    """, unsafe_allow_html=True)

    query = st.text_input("🔍 Search by color or name:").strip().lower()
    if query:
        filtered = df[df.apply(lambda r: query in str(r['predicted_color']).lower() or query in str(r['name']).lower(), axis=1)]
    else:
        filtered = df

    st.write(f"### Showing {len(filtered)} products")
    cols = st.columns(4)

    if filtered.empty:
        st.warning("No products found. Try a different search term.")
        return

    for i, (_, row) in enumerate(filtered.iterrows()):
        img_path = os.path.join(IMAGE_DIR, row['image'])
        with cols[i % 4]:
            if os.path.exists(img_path):
                if st.button(f"🧥 {row['name']}", key=f"main_{row['image']}"):
                    st.session_state.selected_product = row
                    st.rerun()
                st.image(img_path, caption=f"{row['predicted_color']} | ₹{row['price']}", use_container_width=True)
            else:
                st.warning(f"⚠ Image not found: {row['image']}")

# ============================================================
# MAIN VIEW
# ============================================================
if st.session_state.selected_product is not None:
    show_product_details(st.session_state.selected_product)
else:
    show_product_grid()
