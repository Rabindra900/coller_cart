import streamlit as st
import pandas as pd
import os
import json
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

# NEW: profiles
USER_PROFILE_DB = "user_profiles.csv"
PROFILE_PICS_DIR = "profile_pics"

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
# Profiles DB (NEW)
# ============================
def init_profile_db():
    if not os.path.exists(USER_PROFILE_DB):
        cols = ["email", "full_name", "phone", "profile_pic", "wishlist", "recently_viewed"]
        pd.DataFrame(columns=cols).to_csv(USER_PROFILE_DB, index=False)

def load_profiles():
    init_profile_db()
    try:
        return pd.read_csv(USER_PROFILE_DB)
    except Exception:
        return pd.DataFrame(columns=["email","full_name","phone","profile_pic","wishlist","recently_viewed"])

def _empty_profile(email: str) -> dict:
    return {
        "email": email,
        "full_name": "",
        "phone": "",
        "profile_pic": "",
        "wishlist": "[]",          # JSON list of product IDs (we'll use image filename as id)
        "recently_viewed": "[]"    # JSON list (most recent first)
    }

def get_user_profile(email: str) -> dict:
    df = load_profiles()
    row = df[df["email"] == email]
    if len(row) == 0:
        profile = _empty_profile(email)
        save_user_profile(profile)
        return profile
    return row.iloc[0].to_dict()

def save_user_profile(profile: dict):
    df = load_profiles()
    mask = df["email"] == profile["email"]
    if mask.any():
        # align columns
        for k in ["full_name","phone","profile_pic","wishlist","recently_viewed"]:
            if k not in profile:
                profile[k] = _empty_profile(profile["email"])[k]
        df.loc[mask, ["email","full_name","phone","profile_pic","wishlist","recently_viewed"]] = [
            profile["email"], profile["full_name"], profile["phone"], profile["profile_pic"],
            profile["wishlist"], profile["recently_viewed"]
        ]
    else:
        df = pd.concat([df, pd.DataFrame([profile])], ignore_index=True)
    df.to_csv(USER_PROFILE_DB, index=False)

# Wishlist helpers
def get_wishlist(email: str):
    p = get_user_profile(email)
    try:
        return json.loads(p.get("wishlist","[]"))
    except Exception:
        return []

def set_wishlist(email: str, lst):
    p = get_user_profile(email)
    p["wishlist"] = json.dumps(lst)
    save_user_profile(p)

def toggle_wishlist(email: str, product_id: str):
    wl = get_wishlist(email)
    if product_id in wl:
        wl.remove(product_id)
        set_wishlist(email, wl)
        return False
    wl.append(product_id)
    # de-duplicate but keep order
    wl = list(dict.fromkeys(wl))
    set_wishlist(email, wl)
    return True

def in_wishlist(email: str, product_id: str) -> bool:
    return product_id in get_wishlist(email)

# Recently viewed helpers (keep last 10)
def push_recent(email: str, product_id: str, limit=10):
    p = get_user_profile(email)
    try:
        rv = json.loads(p.get("recently_viewed","[]"))
    except Exception:
        rv = []
    # move to front
    rv = [pid for pid in rv if pid != product_id]
    rv.insert(0, product_id)
    rv = rv[:limit]
    p["recently_viewed"] = json.dumps(rv)
    save_user_profile(p)

def get_recent(email: str):
    p = get_user_profile(email)
    try:
        return json.loads(p.get("recently_viewed","[]"))
    except Exception:
        return []

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
    "show_my_orders": False,
    "show_profile": False,   # NEW
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

    # ----------------------------
    # LOGIN TAB
    # ----------------------------
    with tab1:
        email = st.text_input("📧 Email").strip().lower()
        pwd = st.text_input("🔑 Password", type="password")

        if st.button("Login"):
            if not email or not pwd:
                st.error("⚠️ Please fill all fields.")
            elif "@" not in email or "." not in email:
                st.error("❌ Please enter a valid email address (must include '@' and domain).")
            elif len(pwd) < 6:
                st.error("🔒 Password must be at least 6 characters long.")
            else:
                df = load_users()
                if email in df["email"].values:
                    if verify_password(pwd, df.loc[df["email"] == email, "password_h"].iloc[0]):
                        st.session_state.logged_in = True
                        st.session_state.email = email
                        st.session_state.is_admin = (email == "admin@colorkart.com")
                        # ensure profile row exists
                        get_user_profile(email)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect password. Please try again.")
                else:
                    st.error("📩 Email not registered. Please register below to create your account.")

    # ----------------------------
    # REGISTER TAB
    # ----------------------------
    with tab2:
        email = st.text_input("📧 Register Email").strip().lower()
        pwd = st.text_input("🔑 Create Password", type="password")

        if st.button("Register"):
            if not email or not pwd:
                st.error("⚠️ Please fill all fields.")
            elif "@" not in email or "." not in email:
                st.error("❌ Invalid email format. Please include '@' and domain name (e.g., example@gmail.com).")
            elif len(pwd) < 6:
                st.error("🔒 Password must be at least 6 characters long.")
            else:
                if save_user(email, pwd):
                    # Create default profile row
                    save_user_profile(_empty_profile(email))
                    st.success("✅ Account created successfully! You can now log in.")
                else:
                    st.warning("⚠️ This email is already registered. Please log in.")

# ============================
# Common UI helpers
# ============================
def load_product_data():
    if not os.path.exists(CSV_FILE):
        st.error("CSV not found.")
        st.stop()
    df = pd.read_csv(CSV_FILE)
    needed = ['image', 'predicted_color', 'aquarius', 'name', 'price', 'mrp', 'material']
    for c in needed:
        if c not in df.columns:
            st.error("Products CSV missing required columns.")
            st.stop()
    return df


def show_logout_block():
    st.sidebar.markdown("---")
    who = "Admin" if st.session_state.is_admin else "User"
    st.sidebar.info(f"👋 {who}: {st.session_state.email}")

    # 🧭 User Navigation
    if not st.session_state.is_admin:
        if st.sidebar.button("👤 My Profile"):
            st.session_state.show_profile = True
            st.session_state.show_my_orders = False
            st.session_state.selected_product = None
            st.session_state.show_payment = False
            st.session_state.order_confirmed = False
            st.rerun()

        if st.sidebar.button("📦 My Orders"):
            st.session_state.show_my_orders = True
            st.session_state.show_profile = False
            st.session_state.selected_product = None
            st.session_state.show_payment = False
            st.session_state.order_confirmed = False
            st.rerun()

    st.sidebar.markdown("---")

    # 🚪 Logout Button
    if st.sidebar.button("🚪 Logout"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

    # 🏡 Return to Home Button (only one global button)
    if st.sidebar.button("🏡 Return to Home"):
        st.session_state.show_my_orders = False
        st.session_state.show_profile = False
        st.session_state.selected_product = None
        st.session_state.show_payment = False
        st.session_state.order_confirmed = False
        st.rerun()


def show_cart_sidebar():
    st.sidebar.title("🛒 Cart")
    if not st.session_state.cart:
        st.sidebar.info("🛍️ Your cart is empty.")
        return

    total = sum(i["price"] for i in st.session_state.cart)
    for item in st.session_state.cart:
        st.sidebar.write(f"👕 {item['name']} — ₹{item['price']}")

    st.sidebar.markdown(f"**💰 Total: ₹{total}**")

    if st.sidebar.button("✅ Proceed to Checkout"):
        st.session_state.show_payment = True
        st.rerun()


# ============================
# Admin Dashboard (Upgraded)
# ============================
def admin_dashboard_summary():
    """Shows high-level admin metrics."""
    init_orders_db()
    df_orders = pd.read_csv(ORDERS_DB)
    total_orders = len(df_orders)
    pending = len(df_orders[df_orders["status"] == "Pending"]) if "status" in df_orders.columns else 0
    revenue = df_orders["total"].sum() if "total" in df_orders.columns else 0

    total_users = len(load_users())
    total_products = len(pd.read_csv(CSV_FILE)) if os.path.exists(CSV_FILE) else 0

    st.markdown("### 📊 Admin Dashboard Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Users", total_users)
    c2.metric("🛍️ Products", total_products)
    c3.metric("📦 Orders", total_orders)
    c4.metric("💰 Total Revenue", f"₹{revenue:,}")

    st.markdown("---")


# ----------------------------
# User Management
# ----------------------------
def admin_user_panel():
    st.subheader("👥 Manage Users")
    df = load_users()
    if len(df) == 0:
        st.info("No users yet.")
        return

    # Display user list in HTML table
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
    if st.button("🗑️ Delete User"):
        if email == "admin@colorkart.com":
            st.error("Cannot delete admin.")
        elif delete_user(email):
            st.success("✅ User deleted successfully.")
            st.rerun()
        else:
            st.warning("⚠️ Email not found.")


# ----------------------------
# Order Management
# ----------------------------
def admin_order_panel():
    st.subheader("📦 Manage Orders & Status")
    init_orders_db()
    df = pd.read_csv(ORDERS_DB)

    if len(df) == 0:
        st.info("No orders found yet.")
        return

    # Filter by order status
    status_filter = st.selectbox("🔍 Filter by Status", ["All"] + ORDER_STATUSES)
    if status_filter != "All":
        df = df[df["status"] == status_filter]

    for _, row in df.iterrows():
        with st.expander(f"Order #{row['order_id']} — {row['full_name']} — ₹{row['total']} — {row['status']}"):
            st.write(f"🕒 **Created:** {row['created_at']}")
            st.write(f"📧 **Email:** {row['email']}")
            st.write(f"📞 **Phone:** {row['phone']}")
            st.write(f"🏠 **Address:** {row['address']}")
            st.write(f"💳 **Payment:** {row['payment_type']}")
            st.write(f"🧾 **Products:** {row['products']}")
            st.write(f"💰 **Total:** ₹{row['total']:,}")

            new_status = st.selectbox(
                "Update Status", ORDER_STATUSES,
                index=ORDER_STATUSES.index(row['status']) if row['status'] in ORDER_STATUSES else 0,
                key=f"status_{row['order_id']}"
            )

            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("💾 Save Status", key=f"save_{row['order_id']}"):
                    if update_order_status(int(row['order_id']), new_status):
                        st.success("✅ Status updated successfully.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update status.")
            with c2:
                if st.button("🗑️ Delete Order", key=f"del_{row['order_id']}"):
                    df = df[df["order_id"] != row["order_id"]]
                    df.to_csv(ORDERS_DB, index=False)
                    st.warning(f"🗑️ Order #{row['order_id']} deleted.")
                    st.rerun()

    st.markdown("---")
    st.download_button(
        "📥 Download All Orders (CSV)",
        data=pd.read_csv(ORDERS_DB).to_csv(index=False),
        file_name="orders_backup.csv",
        mime="text/csv"
    )


# ----------------------------
# Product Management
# ----------------------------
def admin_product_panel():
    st.subheader("🗂️ Manage Products")
    df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=[
        'image','predicted_color','aquarius','name','price','mrp','material'
    ])

    # Product Table with Thumbnail
    if len(df) == 0:
        st.info("No products available.")
    else:
        table = """
        <style>
        table{width:100%;border-collapse:collapse;margin-top:8px}
        th,td{border:1px solid #ccc;padding:6px;text-align:left}
        th{background:#0077CC;color:#fff}
        </style>
        <table><tr><th>Image</th><th>Name</th><th>Color</th><th>Material</th>
        <th>Accuracy</th><th>Price</th><th>MRP</th></tr>
        """
        for _, r in df.iterrows():
            img_path = os.path.join(IMAGE_DIR, r['image'])
            img_html = f"<img src='{img_path}' width='60'>" if os.path.exists(img_path) else "No Image"
            table += f"<tr><td>{img_html}</td><td>{r['name']}</td><td>{r['predicted_color']}</td>" \
                     f"<td>{r['material']}</td><td>{r['aquarius']}</td>" \
                     f"<td>₹{r['price']}</td><td>₹{r['mrp']}</td></tr>"
        table += "</table>"
        st.markdown(table, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ➕ Add Product")
    img = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    name = st.text_input("Product Name")
    color = st.text_input("Color")
    material = st.text_input("Material")
    acc = st.text_input("Accuracy (%)", "95")
    mrp = st.number_input("MRP", min_value=1)
    price = st.number_input("Selling Price", min_value=1)

    if st.button("Add Product"):
        if img and name:
            os.makedirs(IMAGE_DIR, exist_ok=True)
            path = os.path.join(IMAGE_DIR, img.name)
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            new = {"image": img.name, "predicted_color": color, "aquarius": acc,
                   "name": name, "price": price, "mrp": mrp, "material": material}
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)
            st.success(f"✅ '{name}' added successfully!")
            st.rerun()
        else:
            st.error("⚠️ Please upload an image and enter product details.")

    st.markdown("---")
    st.markdown("### ✏️ Edit Product Price")
    edit_name = st.selectbox("Select Product", df["name"] if len(df) else [])
    new_price = st.number_input("New Price", min_value=1)
    if st.button("💾 Update Price"):
        if edit_name:
            df.loc[df["name"] == edit_name, "price"] = new_price
            df.to_csv(CSV_FILE, index=False)
            st.success(f"✅ Updated {edit_name}'s price to ₹{new_price}")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🗑️ Delete Product")
    del_name = st.text_input("Enter product name to delete")
    if st.button("🗑️ Delete Product"):
        if del_name in df["name"].values:
            df = df[df["name"] != del_name]
            df.to_csv(CSV_FILE, index=False)
            st.warning(f"🗑️ '{del_name}' deleted successfully.")
            st.rerun()
        else:
            st.warning("⚠️ Product not found.")


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

    

# ============================
# Profile Page (NEW + FIXED)
# ============================
PROFILE_PICS_DIR = "profile_pics"

def _product_by_id(df: pd.DataFrame, pid: str):
    """Find product row by its image filename (used as ID)."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    rows = df[df["image"] == pid]
    return rows.iloc[0] if len(rows) else None


def _grid_of_products(df: pd.DataFrame, pids, title: str, empty_text: str):
    """Reusable product grid for wishlist/recently viewed."""
    st.markdown(f"### {title}")
    if not pids:
        st.info(empty_text)
        return
    cols = st.columns(4)
    for i, pid in enumerate(pids):
        row = _product_by_id(df, pid)
        if row is None:
            continue
        img_path = os.path.join(IMAGE_DIR, str(row["image"]))
        with cols[i % 4]:
            if isinstance(img_path, str) and os.path.exists(img_path):
                st.image(img_path, caption=f"{row['name']} | ₹{row['price']}", use_container_width=True)
            else:
                st.warning("Image missing")

            # ✅ Unique key for every button
            unique_key = f"profile_view_{title}_{row['image']}_{i}"
            if st.button(f"View {row['name']}", key=unique_key):
                st.session_state.selected_product = row
                st.session_state.show_profile = False
                st.rerun()



def show_profile_page():
    """User Profile & Settings UI"""
    st.subheader("👤 My Profile & Settings")
    email = st.session_state.email
    profile = get_user_profile(email) if "get_user_profile" in globals() else {}

    # Ensure defaults
    profile.setdefault("profile_pic", "")
    profile.setdefault("full_name", "")
    profile.setdefault("phone", "")

    # ----- LEFT: Avatar -----
    colA, colB = st.columns([1, 3])
    with colA:
        pic_path = str(profile.get("profile_pic", "") or "").strip()
        if pic_path and isinstance(pic_path, str) and os.path.exists(pic_path):
            st.image(pic_path, width=160, caption="Profile Photo")
        else:
            st.image(Image.new("RGB", (160, 160), (230, 230, 230)), caption="No photo", width=160)

        uploaded_pic = st.file_uploader("Change Profile Picture", type=["jpg", "jpeg", "png"])
        if uploaded_pic:
            os.makedirs(PROFILE_PICS_DIR, exist_ok=True)
            out_path = os.path.join(PROFILE_PICS_DIR, f"{email.replace('@', '_at_')}.jpg")
            with open(out_path, "wb") as f:
                f.write(uploaded_pic.getbuffer())
            profile["profile_pic"] = out_path
            save_user_profile(profile)
            st.success("✅ Profile picture updated!")
            st.rerun()

    # ----- RIGHT: Info -----
    with colB:
        profile["full_name"] = st.text_input("👤 Full Name", value=profile.get("full_name", ""))
        profile["phone"] = st.text_input("📞 Phone", value=profile.get("phone", ""))

        if st.button("💾 Save Profile"):
            save_user_profile(profile)
            st.success("✅ Profile updated!")

        st.markdown("---")
        st.subheader("🔐 Change Password")

        old_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            users = load_users()
            if email in users["email"].values:
                stored_h = str(users.loc[users["email"] == email, "password_h"].iloc[0])
                if verify_password(old_pwd, stored_h):
                    if len(new_pwd) < 6:
                        st.error("❌ Password must be at least 6 characters.")
                    elif new_pwd != confirm_pwd:
                        st.error("⚠️ Passwords do not match.")
                    else:
                        users.loc[users["email"] == email, "password_h"] = hash_password(new_pwd)
                        users.to_csv(USER_DB, index=False)
                        st.success("✅ Password updated successfully.")
                else:
                    st.error("❌ Incorrect current password.")

    st.markdown("---")

    # Wishlist & Recently Viewed
    df_products = load_product_data()
    wl = get_wishlist(email) if "get_wishlist" in globals() else []
    rv = get_recent(email) if "get_recent" in globals() else []

    _grid_of_products(df_products, wl, "❤️ My Wishlist", "No items in wishlist yet.")
    st.markdown("---")
    _grid_of_products(df_products, rv, "🕒 Recently Viewed", "No recently viewed items yet.")

   

# ============================
# Product UI
# ============================
def product_details(row, df):
    # track recent
    if st.session_state.email:
        push_recent(st.session_state.email, row["image"])

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

        # Wishlist toggle
        wish_added = in_wishlist(st.session_state.email, row["image"]) if st.session_state.email else False
        wish_btn_label = "💔 Remove from Wishlist" if wish_added else "❤️ Add to Wishlist"

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🛒 Add to Cart"):
                st.session_state.cart.append(row)
                st.success("Added to cart!")
        with c2:
            if st.button("🎨 Generate AI Shirt"):
                img = generate_realistic_shirt(row['predicted_color'])
                st.image(img, caption="AI Generated Shirt")
       

        # separate row for wishlist action to avoid mixing with above row's keys
        if st.session_state.email:
            if st.button(wish_btn_label, key=f"wish_{row['image']}"):
                added = toggle_wishlist(st.session_state.email, row["image"])
                st.success("Wishlist updated." if added else "Removed from wishlist.")
                st.rerun()

    # ---- Divider ----
    st.markdown("---")

    # ⭐ Recommended Shirts Section (same color)
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
    # Sidebar UI
    show_cart_sidebar()
    show_logout_block()

    # Admin mode toggle
    if st.session_state.is_admin:
        st.sidebar.checkbox("🧑‍💼 Admin Mode", value=st.session_state.admin_mode, key="admin_mode")

    # Handle order confirmation
    if st.session_state.order_confirmed:
        show_order_confirmation()
        st.stop()

    # Handle checkout page
    if st.session_state.show_payment:
        show_payment_page()
        st.stop()

    # USER views
    if (not st.session_state.is_admin) and st.session_state.show_my_orders:
        show_my_orders_page()
        st.stop()

    if (not st.session_state.is_admin) and st.session_state.get("show_profile", False):
        show_profile_page()
        st.stop()

    # ============================
    # ADMIN DASHBOARD
    # ============================
    if st.session_state.is_admin and st.session_state.admin_mode:
        st.title("🧾 Admin Dashboard Overview")

        # Quick stats section
        import pandas as pd, os

        total_users = len(load_users()) - 1  # excluding admin
        total_products = 0
        total_orders = 0
        total_revenue = 0

        if os.path.exists(CSV_FILE):
            df_p = pd.read_csv(CSV_FILE)
            total_products = len(df_p)

        if os.path.exists(ORDERS_DB):
            df_o = pd.read_csv(ORDERS_DB)
            total_orders = len(df_o)
            total_revenue = df_o["total"].sum() if "total" in df_o.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 Users", f"{total_users}")
        col2.metric("👕 Products", f"{total_products}")
        col3.metric("📦 Orders", f"{total_orders}")
        col4.metric("💰 Revenue (₹)", f"{total_revenue}")

        st.markdown("---")

        # Management tabs
        t1, t2, t3 = st.tabs(["👥 Users", "📦 Orders", "🗂️ Products"])
        with t1:
            admin_user_panel()
        with t2:
            admin_order_panel()
        with t3:
            admin_product_panel()

    # ============================
    # USER PRODUCT BROWSING
    # ============================
    else:
        dfp = load_product_data()
        if st.session_state.selected_product is not None:
            product_details(st.session_state.selected_product, dfp)
        else:
            product_grid(dfp)
