import streamlit as st
import bcrypt
from supabase import create_client, Client

# Supabase setup
url = "https://kgulogjssuqxrmjfzcma.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtndWxvZ2pzc3VxeHJtamZ6Y21hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc0NjQ0OTAsImV4cCI6MjA2MzA0MDQ5MH0.IQIDWtnLxMzmSlVH48vTjAo6tVyDaCD5sfa3LfkEjZ4"
supabase: Client = create_client(url, key)

# CSS Custom
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        background-color: #f4f6f8;
    }
    .main-box {
        background-color: white;
        padding: 2.5rem 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        max-width: 400px;
        margin: auto;
        margin-top: 3rem;
    }
    .title {
        text-align: center;
        font-weight: 600;
        font-size: 42px;
        color: #fff;
        margin-bottom: 5px;
    }
    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #777;
        margin-bottom: 25px;
    }
    .stButton>button {
        background-color: #4fc3f7;
        color: white;
        border-radius: 10px;
        padding: 10px 0;
        font-weight: 600;
        width: 100%;
        border: none;
    }
    .stButton>button:hover {
        background-color: #29b6f6;
        color: white;
    }
    .stTextInput>div>div>input {
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    .error-alert {
        background-color: #ef5350;
        color: white;
        padding: 10px;
        border-radius: 8px;
        font-weight: 500;
        text-align: center;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Fungsi Login
def login_user(email, password):
    try:
        result = supabase.table("user").select("*").eq("email", email).execute()
        if result.data:
            user = result.data[0]
            stored_hashed_password = user["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                st.session_state.logged_in = True
                st.session_state.user_email = user["email"]
                return user
            else:
                st.error("Password salah.")
                return None
        else:
            st.error("Email tidak ditemukan.")
            return None
    except Exception as e:
        st.error(f"Login gagal: {e}")
        return None

# Fungsi Register
def register_user(email, password):
    try:
        if not email or not password:
            st.warning("Email dan password tidak boleh kosong.")
            return None

        existing = supabase.table("user").select("*").eq("email", email).execute()
        if existing.data:
            st.warning("Email sudah terdaftar.")
            return None

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        result = supabase.table("user").insert({
            "email": email,
            "password": hashed_password
        }).execute()

        st.success("Registrasi berhasil! Silakan login.")
        return result
    except Exception as e:
        st.error(f"Registrasi gagal: {e}")
        return None


# UI Utama
def main():
    inject_css()

    # Setup session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Jika sudah login
    if st.session_state.logged_in:
        st.markdown('<div class="title">Welcome!</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Hello, {st.session_state.user_email} ðŸ‘‹</div>', unsafe_allow_html=True)
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.rerun()
        return

    # Jika belum login
    st.markdown('<div class="title">Pseudofile Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Silakan login atau daftar akun baru.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["ðŸ” Login", "ðŸ“ Register"])

    with tab1:
        st.subheader("Form Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = login_user(email, password)
            if user:
                st.success("Login berhasil!")
                st.rerun()

    with tab2:
        st.subheader("Form Register")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        confirm = st.text_input("Konfirmasi Password", type="password", key="register_confirm")
        if st.button("Register"):
            if not email or not password or not confirm:
                st.markdown('<div class="error-alert">Semua field wajib diisi.</div>', unsafe_allow_html=True)
            elif password != confirm:
                st.markdown('<div class="error-alert">Password tidak cocok.</div>', unsafe_allow_html=True)
            else:
                register_user(email, password)


# Jalankan Aplikasi
if __name__ == "__main__":
    main()