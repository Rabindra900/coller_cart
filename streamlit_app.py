import streamlit as st
import pandas as pd
import os
from PIL import Image
import hashlib
from datetime import datetime
from gan_generator import generate_realistic_shirt

# ----------------------------
# Config
# ----------------------------
CSV_FILE = "image_colors.csv"
USER_DB = "users.csv"
ORDERS_DB = "orders.csv"
IMAGE_DIR = "images_all"

ORDER_STATUSES = ["Pending", "Shipped", "Out for Delivery", "Delivered", "Cancelled"]

st.set_page_config(page_title="🩵 ColorKart - AI Shirt Store", layout="wide")

# ============================
# Security helpers
# ============================
def hash_password(raw: str) -> str:
    salt = "colorkart_salt_v1"
    return hashlib.sha256((salt + raw).encode("utf-8")).hexdigest()

def verify_password(raw: str, hashed: str) -> bool:
    return hash_password(raw) == hashed

# ============================
# User DB
# ============================
def init_user_db():
    if not os.path.exists(USER_DB):
        pd.DataFrame(columns=["email", "password_h"]).to_csv(USER_DB, index=False)
    try:
        df = pd.read_csv(USER_DB)
    except Exception:
        df = pd.DataFrame(columns=["email", "password_h"])
    admin_email = "admin@colorkart.com"
    admin_pass_h = hash_password("admin123")
    if "email" not in df.columns or "password_h" not in df.columns:
        df = pd.DataFrame(columns=["email", "password_h"])
    if admin_email not in df["email"].values:
        df = pd.concat([df, pd.DataFrame([{"email": admin_email, "password_h": admin_pass_h}])], ignore_index=True)
        df.to_csv(USER_DB, index=False)

def load_users():
    init_user_db()
    try:
        return pd.read_csv(USER_DB)
    except Exception:
        return pd.DataFrame(columns=["email", "password_h"])

def save_user(email, pwd):
    df = load_users()
    if email in df["email"].values:
        return False
    df = pd.concat([df, pd.DataFrame([{"email": email, "password_h": hash_password(pwd)}])], ignore_index=True)
    df.to_csv(USER_DB, index=False)
    return True

def delete_user(email):
    df = load_users()
    if email in df["email"].values:
        df = df[df["email"] != email].reset_index(drop=True)
        df.to_csv(USER_DB, index=False)
        return True
    return False

# ============================
# Orders DB
# ============================
def init_orders_db():
    if not os.path.exists(ORDERS_DB):
        cols = ["order_id","created_at","email","full_name","phone","address","payment_type","products","total","status"]
        pd.DataFrame(columns=cols).to_csv(ORDERS_DB, index=False)

def next_order_id(df_orders: pd.DataFrame) -> int:
    if "order_id" in df_orders.columns and df_orders["order_id"].astype(str).str.isnumeric().any():
        # get max numeric id
        try:
            return int(df_orders["order_id"].astype(int).max()) + 1
        except Exception:
            return len(df_orders) + 1
    return len(df_orders) + 1

def save_order(email, full_name, phone, address, payment_type, products, total):
    init_orders_db()
    df = pd.read_csv(ORDERS_DB)
    oid = next_order_id(df)
    new = {
        "order_id": oid,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "address": address,
        "payment_type": payment_type,
        "products": products,
        "total": total,
        "status": "Pending"
    }
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    df.to_csv(ORDERS_DB, index=False)
    return oid

def update_order_status(order_id: int, new_status: str) -> bool:
    init_orders_db()
    df = pd.read_csv(ORDERS_DB)
    if "order_id" not in df.columns:
        return False
    mask = df["order_id"].astype(int) == int(order_id)
    if not mask.any():
        return False
    df.loc[mask, "status"] = new_status
    df.to_csv(ORDERS_DB, index=False)
    return True

# ============================
# Session
# ============================
defaults = {
    "logged_in": False,
    "email": None,
    "is_admin": False,
    "selected_product": None,
    "cart": [],
    "show_payment": False,
    "order_confirmed": False,
    "order_details": {},
    "admin_mode": False,
    "show_my_orders": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================
# Auth UI
# ============================
def show_auth_page():
    st.title("🩵 ColorKart - AI Shirt Store")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    with tab1:
        email = st.text_input("📧 Email").strip().lower()
        pwd = st.text_input("🔑 Password", type="password")
        if st.button("Login"):
            df = load_users()
            if email in df["email"].values:
                if verify_password(pwd, df.loc[df["email"] == email, "password_h"].iloc[0]):
                    st.session_state.logged_in = True
                    st.session_state.email = email
                    st.session_state.is_admin = (email == "admin@colorkart.com")
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("Wrong password.")
            else:
                st.error("Email not found.")
    with tab2:
        email = st.text_input("📧 Register Email").strip().lower()
        pwd = st.text_input("🔑 Create Password", type="password")
        if st.button("Register"):
            if email and pwd:
                if save_user(email, pwd):
                    st.success("✅ Registered successfully. Please log in.")
                else:
                    st.warning("⚠️ Email already exists.")
            else:
                st.error("Fill all fields.")

# ============================
# Common UI helpers
# ============================
def load_product_data():
    if not os.path.exists(CSV_FILE):
        st.error("CSV not found."); st.stop()
    df = pd.read_csv(CSV_FILE)
    needed = ['image','predicted_color','aquarius','name','price','mrp','material']
    for c in needed:
        if c not in df.columns:
            st.error("Products CSV missing required columns."); st.stop()
    return df

def show_logout_block():
    st.sidebar.markdown("---")
    who = "Admin" if st.session_state.is_admin else "User"
    st.sidebar.info(f"👋 {who}: {st.session_state.email}")
    # Nav for users
    if not st.session_state.is_admin:
        if st.sidebar.button("📦 My Orders"):
            st.session_state.show_my_orders = True
            st.session_state.selected_product = None
            st.rerun()
    if st.sidebar.button("🚪 Logout"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

def show_cart_sidebar():
    st.sidebar.title("🛒 Cart")
    if not st.session_state.cart:
        st.sidebar.info("Cart empty.")
        return
    total = sum(i["price"] for i in st.session_state.cart)
    for item in st.session_state.cart:
        st.sidebar.write(f"👕 {item['name']} — ₹{item['price']}")
    st.sidebar.markdown(f"**Total: ₹{total}**")
    if st.sidebar.button("Proceed to Checkout"):
        st.session_state.show_payment = True
        st.rerun()

# ============================
# Admin Panels
# ============================
def admin_user_panel():
    st.subheader("👥 Manage Users")
    df = load_users()
    if len(df) == 0:
        st.info("No users yet.")
        return
    # Simple HTML table (no pyarrow)
    table = """
    <style>
    table{width:100%;border-collapse:collapse;margin-top:8px}
    th,td{border:1px solid #ccc;padding:6px;text-align:left}
    th{background:#0077CC;color:#fff}
    </style>
    <table><tr><th>Email</th><th>Password Hash</th></tr>
    """
    for _, r in df.iterrows():
        table += f"<tr><td>{r['email']}</td><td>{r['password_h']}</td></tr>"
    table += "</table>"
    st.markdown(table, unsafe_allow_html=True)

    email = st.text_input("Delete user by email")
    if st.button("Delete User"):
        if email == "admin@colorkart.com":
            st.error("Cannot delete admin.")
        elif delete_user(email):
            st.success("User deleted.")
            st.rerun()
        else:
            st.warning("Not found.")

def admin_order_panel():
    st.subheader("📦 Orders & Status")
    init_orders_db()
    df = pd.read_csv(ORDERS_DB)
    if len(df) == 0:
        st.info("No orders yet.")
        return

    # Row-wise editor without pyarrow
    for idx, row in df.iterrows():
        with st.expander(f"Order #{row['order_id']} — {row['full_name']} — ₹{row['total']} — {row['status']}"):
            st.write(f"🕒 **Created:** {row['created_at']}")
            st.write(f"📧 **Email:** {row['email']}")
            st.write(f"📞 **Phone:** {row['phone']}")
            st.write(f"🏠 **Address:** {row['address']}")
            st.write(f"💳 **Payment:** {row['payment_type']}")
            st.write(f"🧾 **Products:** {row['products']}")
            st.write(f"💰 **Total:** ₹{row['total']}")
            new_status = st.selectbox("Update status", ORDER_STATUSES, index=ORDER_STATUSES.index(row['status']) if row['status'] in ORDER_STATUSES else 0, key=f"status_{row['order_id']}")
            if st.button("💾 Save Status", key=f"save_{row['order_id']}"):
                if update_order_status(int(row['order_id']), new_status):
                    st.success("Status updated.")
                    st.rerun()
                else:
                    st.error("Failed to update status.")

def admin_product_panel():
    st.subheader("🗂️ Manage Products")
    df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=['image','predicted_color','aquarius','name','price','mrp','material'])
    # Simple product list (HTML)
    if len(df) == 0:
        st.info("No products yet.")
    else:
        table = """
        <style>
        table{width:100%;border-collapse:collapse;margin-top:8px}
        th,td{border:1px solid #ccc;padding:6px;text-align:left}
        th{background:#0077CC;color:#fff}
        </style>
        <table><tr><th>Name</th><th>Color</th><th>Material</th><th>Accuracy</th><th>Price</th><th>MRP</th><th>Image</th></tr>
        """
        for _, r in df.iterrows():
            table += f"<tr><td>{r['name']}</td><td>{r['predicted_color']}</td><td>{r['material']}</td><td>{r['aquarius']}</td><td>{r['price']}</td><td>{r['mrp']}</td><td>{r['image']}</td></tr>"
        table += "</table>"
        st.markdown(table, unsafe_allow_html=True)

    # Add product
    st.markdown("### ➕ Add Product")
    img = st.file_uploader("Upload image", type=["jpg","png","jpeg"])
    name = st.text_input("Product Name")
    color = st.text_input("Color")
    material = st.text_input("Material")
    acc = st.text_input("Accuracy", "95")
    mrp = st.number_input("MRP", min_value=1)
    price = st.number_input("Price", min_value=1)
    if st.button("Add Product"):
        if img and name:
            os.makedirs(IMAGE_DIR, exist_ok=True)
            path = os.path.join(IMAGE_DIR, img.name)
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            new = {"image": img.name, "predicted_color": color, "aquarius": acc, "name": name, "price": price, "mrp": mrp, "material": material}
            df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=['image','predicted_color','aquarius','name','price','mrp','material'])
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
            st.success("Product added.")
            st.rerun()
        else:
            st.error("Please provide at least image and product name.")

    # Delete product
    st.markdown("### 🗑️ Delete Product")
    del_name = st.text_input("Delete by product name")
    if st.button("Delete Product"):
        df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=['image','predicted_color','aquarius','name','price','mrp','material'])
        if del_name in df.get("name", pd.Series([])).values:
            df = df[df["name"] != del_name]
            df.to_csv(CSV_FILE, index=False)
            st.success(f"Deleted product '{del_name}'.")
            st.rerun()
        else:
            st.warning("Product not found.")

# ============================
# Payment & Confirmation
# ============================
def show_payment_page():
    st.subheader("💳 Checkout & Delivery Info")
    full_name = st.text_input("👤 Full Name")
    phone = st.text_input("📞 Phone Number")
    email = st.text_input("📧 Delivery Email", value=st.session_state.email or "")
    address = st.text_area("🏠 Full Delivery Address")
    payment_type = st.radio("Payment Method", ["UPI / QR", "Card", "Cash on Delivery"])
    total = sum(i['price'] for i in st.session_state.cart)
    st.markdown(f"### Total Payable: ₹{total}")

    if payment_type == "UPI / QR" and os.path.exists("upi_qr.png"):
        st.image("upi_qr.png", caption="Scan to Pay", use_container_width=True)

    if payment_type == "Card":
        st.text_input("Name on Card")
        st.text_input("Card Number")
        st.text_input("Expiry (MM/YY)")
        st.text_input("CVV", type="password")

    if st.button("✅ Confirm Order"):
        if not all([full_name.strip(), phone.strip(), email.strip(), address.strip()]):
            st.error("Please fill name, phone, email, and address.")
            return
        product_list = ", ".join(i["name"] for i in st.session_state.cart)
        oid = save_order(email, full_name, phone, address, payment_type, product_list, total)
        st.session_state.order_details = {
            "order_id": oid,
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "address": address,
            "payment_type": payment_type,
            "products": product_list,
            "total": total
        }
        st.session_state.order_confirmed = True
        st.session_state.cart = []
        st.session_state.show_payment = False
        st.rerun()

    if st.button("Cancel"):
        st.session_state.show_payment = False
        st.rerun()

def show_order_confirmation():
    st.subheader("🎉 Order Confirmed!")
    d = st.session_state.order_details
    st.success("Your order has been placed successfully.")
    st.markdown(f"""
**Order ID:** #{d['order_id']}  
**Name:** {d['full_name']}  
**Phone:** {d['phone']}  
**Email:** {d['email']}  
**Address:** {d['address']}  
**Payment Type:** {d['payment_type']}  
**Products:** {d['products']}  
**Total Paid:** ₹{d['total']}
""")
    if st.button("🏠 Back to Home"):
        st.session_state.order_confirmed = False
        st.session_state.selected_product = None
        st.rerun()

# ============================
# My Orders (User)
# ============================
def show_my_orders_page():
    st.subheader("📦 My Orders")
    init_orders_db()
    df = pd.read_csv(ORDERS_DB)
    my = df[df["email"] == (st.session_state.email or "___nope___")]
    if len(my) == 0:
        st.info("You have no orders yet.")
    else:
        # HTML table (no pyarrow)
        table = """
        <style>
        table{width:100%;border-collapse:collapse;margin-top:8px}
        th,td{border:1px solid #ccc;padding:6px;text-align:left}
        th{background:#0077CC;color:#fff}
        </style>
        <table><tr><th>Order ID</th><th>Date</th><th>Products</th><th>Total</th><th>Payment</th><th>Status</th><th>Address</th></tr>
        """
        for _, r in my.sort_values(by="created_at", ascending=False).iterrows():
            table += f"<tr><td>{r['order_id']}</td><td>{r['created_at']}</td><td>{r['products']}</td><td>₹{r['total']}</td><td>{r['payment_type']}</td><td>{r['status']}</td><td>{r['address']}</td></tr>"
        table += "</table>"
        st.markdown(table, unsafe_allow_html=True)

    if st.button("🏠 Back to Home"):
        st.session_state.show_my_orders = False
        st.rerun()

# ============================
# Product UI
# ============================
def product_details(row, df):
    st.header(f"👕 {row['name']}")
    col1, col2 = st.columns([1.3, 1])

    # ----- LEFT COLUMN -----
    with col1:
        img_path = os.path.join(IMAGE_DIR, row['image'])
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.warning("⚠️ Image not found.")

    # ----- RIGHT COLUMN -----
    with col2:
        price, mrp = row['price'], row['mrp']
        discount = round((1 - price / mrp) * 100)
        st.write(f"**Color:** {row['predicted_color']} | **Material:** {row['material']} | **Accuracy:** {row['aquarius']}")
        st.write(f"💰 Price: ₹{price} (~~₹{mrp}~~)  🏷️ {discount}% OFF")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🛒 Add to Cart"):
                st.session_state.cart.append(row)
                st.success("Added to cart!")
        with c2:
            if st.button("🎨 Generate AI Shirt"):
                img = generate_realistic_shirt(row['predicted_color'])
                st.image(img, caption="AI Generated Shirt")
        with c3:
            if st.button("🔙 Back to Home"):
                st.session_state.selected_product = None
                st.rerun()

    # ---- Divider ----
    st.markdown("---")

    # ⭐ Recommended Shirts Section
    color = row['predicted_color']
    st.subheader(f"⭐ Recommended Shirts (Same Color: {color.capitalize()})")

    recommended = df[(df['predicted_color'] == color) & (df['image'] != row['image'])]

    if len(recommended) == 0:
        st.info(f"No other {color} shirts found.")
        return

    cols = st.columns(4)
    for i, (_, rec) in enumerate(recommended.iterrows()):
        with cols[i % 4]:
            rec_path = os.path.join(IMAGE_DIR, rec['image'])
            if os.path.exists(rec_path):
                st.image(rec_path, caption=f"{rec['name']} | ₹{rec['price']}", use_container_width=True)
                if st.button(f"View {rec['name']}", key=f"rec_{rec['image']}"):
                    st.session_state.selected_product = rec
                    st.rerun()
            else:
                st.warning("Image missing")


def product_grid(df):
    st.subheader("🛍️ Explore Our Collection")
    q = st.text_input("Search by name or color").lower().strip()
    filt = df if not q else df[df.apply(lambda r: q in str(r['predicted_color']).lower() or q in str(r['name']).lower(), axis=1)]
    cols = st.columns(4)
    for i, (_, r) in enumerate(filt.iterrows()):
        path = os.path.join(IMAGE_DIR, r['image'])
        with cols[i % 4]:
            if os.path.exists(path):
                st.image(path, caption=f"{r['name']} | ₹{r['price']}", use_container_width=True)
            else:
                st.warning("Image missing")
            if st.button(f"View {r['name']}", key=r['image']):
                st.session_state.selected_product = r
                st.rerun()

# ============================
# MAIN APP
# ============================
if not st.session_state.logged_in:
    show_auth_page()
else:
    show_cart_sidebar()
    show_logout_block()

    if st.session_state.is_admin:
        st.sidebar.checkbox("🧑‍💼 Admin Mode", value=st.session_state.admin_mode, key="admin_mode")

    if st.session_state.order_confirmed:
        show_order_confirmation()
        st.stop()

    if st.session_state.show_payment:
        show_payment_page()
        st.stop()

    if (not st.session_state.is_admin) and st.session_state.show_my_orders:
        show_my_orders_page()
        st.stop()

    if st.session_state.is_admin and st.session_state.admin_mode:
        t1, t2, t3 = st.tabs(["👥 Users", "📦 Orders", "🗂️ Products"])
        with t1:
            admin_user_panel()
        with t2:
            admin_order_panel()
        with t3:
            admin_product_panel()
    else:
        dfp = load_product_data()
        if st.session_state.selected_product is not None:
            product_details(st.session_state.selected_product, dfp)
        else:
            product_grid(dfp)
