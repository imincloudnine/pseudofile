import streamlit as st
import bcrypt
import os
import tempfile
from supabase import create_client, Client
from pypdf import PdfReader, PdfWriter
from docx2pdf import convert as docx2pdf_convert
from pdf2docx import Converter
import uuid
from datetime import datetime

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

def log_user_activity(
    user_id: str,
    email: str,
    action: str,
    activity_type: str,
    filename: str,
    file_size_mb: float,
    result_file_size_mb: float = None,
    billing_amount: int = 0
):
    try:
        payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "email": email,
            "action": action,
            "activity_type": activity_type,
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2),
            "result_file_size_mb": round(result_file_size_mb, 2) if result_file_size_mb else None,
            "billing_amount": billing_amount,
            "timestamp": datetime.utcnow().isoformat()
        }

        response = supabase.table("log_user_activity").insert(payload).execute()
        return response.data is not None and len(response.data) > 0
    except Exception as e:
        st.error(f"Gagal mencatat aktivitas: {e}")
        return False

def compress_pdf(input_path, output_path, user_id, email, original_filename):
    try:
        # Hitung ukuran file input (dalam MB)
        input_file_size = os.path.getsize(input_path) / (1024 * 1024)

        # Kompresi PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata({})

        with open(output_path, "wb") as f:
            writer.write(f)

        # Hitung ukuran hasil kompresi (dalam MB)
        result_file_size = os.path.getsize(output_path) / (1024 * 1024)
        billing_amount = int(input_file_size * 1000)  # 100 coin per MB

        # Log aktivitas
        if log_user_activity(
            user_id=user_id,
            email=email,
            action="compress_pdf",
            activity_type="file_operation",
            filename=original_filename,
            file_size_mb=input_file_size,
            result_file_size_mb=result_file_size,
            billing_amount=billing_amount
        ):
            return True, billing_amount
        return False, 0
    except Exception as e:
        st.error(f"Gagal mengompres PDF: {e}")
        return False, 0

def merge_pdf(input_files, output_path, user_id, email):
    try:
        writer = PdfWriter()
        total_size = 0

        for uploaded_file in input_files:
            temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            total_size += os.path.getsize(temp_path) / (1024 * 1024)
            
            reader = PdfReader(temp_path)
            for page in reader.pages:
                writer.add_page(page)
            os.remove(temp_path)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        result_size = os.path.getsize(output_path) / (1024 * 1024)
        billing_amount = int(total_size * 500)  # 50 coin per MB

        if log_user_activity(
            user_id=user_id,
            email=email,
            action="merge_pdf",
            activity_type="file_operation",
            filename="merged.pdf",
            file_size_mb=total_size,
            result_file_size_mb=result_size,
            billing_amount=billing_amount
        ):
            return True, billing_amount
        return False, 0
    except Exception as e:
        st.error(f"Gagal menggabungkan PDF: {e}")
        return False, 0

def convert_file(input_path, output_path, conversion_type, user_id, email, original_filename):
    try:
        input_size = os.path.getsize(input_path) / (1024 * 1024)
        
        if conversion_type == "word_to_pdf":
            docx2pdf_convert(input_path, output_path)
        else:  # pdf_to_word
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()

        result_size = os.path.getsize(output_path) / (1024 * 1024)
        billing_amount = int(input_size * 1500)  # 150 coin per MB

        if log_user_activity(
            user_id=user_id,
            email=email,
            action=f"convert_{conversion_type}",
            activity_type="file_operation",
            filename=original_filename,
            file_size_mb=input_size,
            result_file_size_mb=result_size,
            billing_amount=billing_amount
        ):
            return True, billing_amount
        return False, 0
    except Exception as e:
        st.error(f"Gagal konversi file: {e}")
        return False, 0

def show_dashboard():
    st.markdown('<div class="title">Welcome!</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">Hello, {st.session_state.user_nama} 👋</div>', unsafe_allow_html=True)

    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Menu",
        ["Beranda", "Kompres PDF", "Gabungkan PDF", "Konversi File", "Tagihan"]
    )

    # Logout button in sidebar
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

    if menu == "Beranda":
        show_home()
    elif menu == "Kompres PDF":
        show_compress_pdf()
    elif menu == "Gabungkan PDF":
        show_merge_pdf()
    elif menu == "Konversi File":
        show_convert_file()
    elif menu == "Tagihan":
        show_billing()

def show_home():
    st.markdown("""
    ### Selamat Datang di Pseudofile! 🎉
    
    Aplikasi ini menyediakan berbagai fitur untuk mengelola file PDF dan dokumen Anda:
    
    - 📦 **Kompres PDF**: Mengecilkan ukuran file PDF Anda
    - 🔄 **Gabungkan PDF**: Menggabungkan beberapa file PDF menjadi satu
    - 📝 **Konversi File**: Mengkonversi antara format Word dan PDF
    
    Silakan pilih menu di sidebar untuk menggunakan fitur yang Anda inginkan.
    """)

def show_compress_pdf():
    st.markdown("### 📦 Kompres PDF")
    st.markdown("Unggah file PDF yang ingin dikompres untuk mengurangi ukurannya.")
    
    uploaded_file = st.file_uploader("Unggah file PDF", type="pdf")
    if uploaded_file is not None:
        if st.button("Kompres PDF"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
                tmp_input.write(uploaded_file.read())
                tmp_input_path = tmp_input.name

            tmp_output_path = tmp_input_path.replace(".pdf", "_compressed.pdf")

            with st.spinner("Sedang mengompres PDF..."):
                success, billing_amount = compress_pdf(
                    input_path=tmp_input_path,
                    output_path=tmp_output_path,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    original_filename=uploaded_file.name
                )

                if success:
                    with open(tmp_output_path, "rb") as f:
                        st.success(f"PDF berhasil dikompres! (Biaya: Rp. {billing_amount} )")
                        st.download_button(
                            label="⬇️ Download PDF Terkompres",
                            data=f,
                            file_name="compressed.pdf",
                            mime="application/pdf"
                        )

            os.remove(tmp_input_path)
            os.remove(tmp_output_path)

def show_merge_pdf():
    st.markdown("### 🔄 Gabungkan PDF")
    st.markdown("Unggah dua atau lebih file PDF yang ingin digabungkan menjadi satu file.")
    
    uploaded_files = st.file_uploader(
        "Unggah file PDF",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    if uploaded_files and len(uploaded_files) >= 2:
        if st.button("Gabungkan PDF"):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "merged.pdf")
                
                with st.spinner("Sedang menggabungkan PDF..."):
                    success, billing_amount = merge_pdf(
                        input_files=uploaded_files,
                        output_path=output_path,
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email
                    )

                    if success:
                        with open(output_path, "rb") as f:
                            st.success(f"PDF berhasil digabungkan! (Biaya: Rp. {billing_amount} )")
                            st.download_button(
                                label="⬇️ Download PDF Gabungan",
                                data=f,
                                file_name="merged.pdf",
                                mime="application/pdf"
                            )
    else:
        st.warning("⚠️ Silakan unggah minimal dua file PDF untuk digabungkan.")

def show_convert_file():
    st.markdown("### 📝 Konversi File")
    st.markdown("Pilih jenis konversi yang Anda inginkan.")
    
    conversion_type = st.radio(
        "Jenis Konversi",
        ["Word ke PDF", "PDF ke Word"],
        horizontal=True
    )
    
    if conversion_type == "Word ke PDF":
        uploaded_file = st.file_uploader("Unggah file Word (.docx)", type=["docx"])
        if uploaded_file and st.button("Konversi ke PDF"):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input.docx")
                output_path = os.path.join(tmpdir, "output.pdf")

                with open(input_path, "wb") as f:
                    f.write(uploaded_file.read())

                with st.spinner("Mengonversi..."):
                    success, billing_amount = convert_file(
                        input_path=input_path,
                        output_path=output_path,
                        conversion_type="word_to_pdf",
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email,
                        original_filename=uploaded_file.name
                    )

                    if success:
                        with open(output_path, "rb") as f:
                            st.success(f"Konversi berhasil! (Biaya: Rp. {billing_amount} )")
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=f,
                                file_name="converted.pdf",
                                mime="application/pdf"
                            )
    else:
        uploaded_file = st.file_uploader("Unggah file PDF", type=["pdf"])
        if uploaded_file and st.button("Konversi ke Word"):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input.pdf")
                output_path = os.path.join(tmpdir, "output.docx")

                with open(input_path, "wb") as f:
                    f.write(uploaded_file.read())

                with st.spinner("Mengonversi..."):
                    success, billing_amount = convert_file(
                        input_path=input_path,
                        output_path=output_path,
                        conversion_type="pdf_to_word",
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email,
                        original_filename=uploaded_file.name
                    )

                    if success:
                        with open(output_path, "rb") as f:
                            st.success(f"Konversi berhasil! (Biaya: Rp. {billing_amount} )")
                            st.download_button(
                                label="⬇️ Download Word",
                                data=f,
                                file_name="converted.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )

def show_billing():
    st.subheader("💳 Tagihan Saya")

    user_email = st.session_state.get("user_email")
    if user_email:
        # Ambil log aktivitas user dari Supabase
        billing_response = supabase.table("log_user_activity") \
            .select("timestamp, action, filename, file_size_mb, result_file_size_mb, billing_amount") \
            .eq("email", user_email) \
            .order("timestamp", desc=True) \
            .execute()

        billing_data = billing_response.data

        if billing_data:
            total_tagihan = sum(item.get("billing_amount", 0) or 0 for item in billing_data)
            st.metric(label="Total Tagihan", value=f"Rp. {total_tagihan:,}")

            st.caption("Riwayat Aktivitas yang Ditagih:")
            st.dataframe(billing_data, use_container_width=True)
        else:
            st.info("Belum ada aktivitas yang ditagih.")
    else:
        st.warning("Anda belum login.")

def show_login_page():
    st.markdown('<div class="title">Pseudofile Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Silakan login atau daftar akun baru.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

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
        nama = st.text_input("Nama Lengkap", key="register_nama")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        confirm = st.text_input("Konfirmasi Password", type="password", key="register_confirm")
        if st.button("Register"):
            if not email or not password or not confirm:
                st.markdown('<div class="error-alert">Semua field wajib diisi.</div>', unsafe_allow_html=True)
            elif password != confirm:
                st.markdown('<div class="error-alert">Password tidak cocok.</div>', unsafe_allow_html=True)
            else:
                register_user(email, password, nama)

def login_user(email, password):
    try:
        result = supabase.table("user").select("*").eq("email", email).execute()
        if result.data:
            user = result.data[0]
            stored_hashed_password = user["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                st.session_state.logged_in = True
                st.session_state.user_email = user["email"]
                st.session_state.user_nama = user["nama"]
                st.session_state.user_id = user["id"]
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

def register_user(email, password, nama):
    try:
        if not email or not password or not nama:
            st.warning("Email, password, dan nama tidak boleh kosong.")
            return None

        existing = supabase.table("user").select("*").eq("email", email).execute()
        if existing.data:
            st.warning("Email sudah terdaftar.")
            return None

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        result = supabase.table("user").insert({
            "email": email,
            "password": hashed_password,
            "nama": nama
        }).execute()

        st.success("Registrasi berhasil! Silakan login.")
        return result
    except Exception as e:
        st.error(f"Registrasi gagal: {e}")
        return None

def main():
    inject_css()

    # Setup session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Jika sudah login
    if st.session_state.logged_in:
        show_dashboard()
        return

    # Jika belum login
    show_login_page()

if __name__ == "__main__":
    main()
