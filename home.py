import streamlit as st
import bcrypt
import os
import tempfile
from PIL import Image
from supabase import create_client, Client
from pypdf import PdfReader, PdfWriter
from docx2pdf import convert as docx2pdf_convert
from streamlit_option_menu import option_menu
from pdf2docx import Converter
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
import fitz  
import io

# Supabase setup
# Load dari .env
load_dotenv()

# Ambil dari environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

st.set_page_config(layout="wide")
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
        max-width: 1000px;
        margin: 200px;
        margin-top: 100px;
        margin-left: 10px;
    }
    .title {
        text-align: center;
        font-weight: 600;
        font-size: 42px;
        color: #fff;
        margin-bottom: 2px;
    }
    .h2 {
        text-align: center;
        font-weight: 600;
        font-size: 24px;
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

        # Buka PDF dengan PyMuPDF
        doc = fitz.open(input_path)
        
        # Kompresi gambar dalam PDF
        for page in doc:
            # Dapatkan semua gambar di halaman
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Buka gambar dengan PIL
                image = Image.open(io.BytesIO(image_bytes))
                
                # Kompres gambar
                if image.mode in ['RGBA', 'LA']:
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background
                
                # Simpan gambar yang sudah dikompres
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG', quality=35, optimize=True)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Ganti gambar asli dengan yang sudah dikompres
                doc.update_stream(xref, img_byte_arr)

        # Simpan PDF yang sudah dikompres
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()

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

def show_boxes():
    st.markdown("""
        <style>
            .feature-box {
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.05);
                text-align: center;
                transition: transform 0.2s;
                height: 220px;
            }
            .feature-box:hover {
                transform: scale(1.02);
                background-color: #f0f8ff;
            }
            .feature-icon {
                font-size: 40px;
                margin-bottom: 10px;
            }
            .feature-title {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 8px;
                color: #000;
            }
            .feature-desc {
                font-size: 14px;
                color: #666;
            }
        </style>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">🧩</div>
                <div class="feature-title">Gabungkan PDF</div>
                <div class="feature-desc">Satukan beberapa file PDF menjadi satu dokumen.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">🔄</div>
                <div class="feature-title">Konversi File</div>
                <div class="feature-desc">Ubah file dari Word, PPT, gambar ke PDF, dan sebaliknya.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">📉</div>
                <div class="feature-title">Kompres PDF</div>
                <div class="feature-desc">Perkecil ukuran file PDF tanpa mengurangi kualitas.</div>
            </div>
        """, unsafe_allow_html=True)

def show_landing_page():
    # Tambahkan CSS untuk styling navbar
    st.markdown("""
    <style>
        /* Biarkan menu penuh lebar */
        .css-1r6slb0.e1tzin5v0 {
            width: 100% !important;
        }
        /* Posisikan navbar di paling atas */
        .stApp {
            margin-top: -50px; /* Naikkan margin biar nempel */
        }
        /* Gaya tambahan untuk menu agar lebih lebar */
        .css-10trblm.e16nr0p30 {
            width: 100% !important;
        }

        /* Tambahan opsional: box menu jadi transparan */
        .css-1r6slb0.e1tzin5v0 {
            background-color: rgba(0,0,0,0);
            padding: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Navbar horizontal di atas
    
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Home", "Login/Register"],
            icons=["house", "box-arrow-right"],
            orientation="horizontal",
            default_index=0,
            styles={
                "container": {"padding": "10px", "background-color": "#fafafa"},
                "nav-link": {
                    "font-size": "12px",
                    "color": "black",
                    "text-align": "center",
                    "margin": "0px 10px",
                },
                "nav-link-selected": {
                    "background-color": "#d0e8ff",
                    "color": "black",
                },
            }
        )

    if selected == "Home":
        show_hero()
        show_boxes()
    elif selected == "Login/Register":
        show_login_page()

def show_hero():
    st.markdown('<div class="title">Pseudofile</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">your PDF worker in overtime</div>', unsafe_allow_html=True)

def show_dashboard():
    # Tambahkan CSS untuk styling navbar
    st.markdown("""
    <style>
        /* Biarkan menu penuh lebar */
        .css-1r6slb0.e1tzin5v0 {
            width: 100% !important;
        }
        /* Posisikan navbar di paling atas */
        .stApp {
            margin-top: -50px; /* Naikkan margin biar nempel */
        }
        /* Gaya tambahan untuk menu agar lebih lebar */
        .css-10trblm.e16nr0p30 {
            width: 100% !important;
        }

        /* Tambahan opsional: box menu jadi transparan */
        .css-1r6slb0.e1tzin5v0 {
            background-color: rgba(0,0,0,0);
            padding: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Navbar horizontal di atas
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Home", "Compress PDF", "Gabungkan PDF", "Konversi File", "Tagihan", "Logout"],
            icons=["house", "file-earmark-zip", "files", "filetype-pdf", "currency-dollar", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "10px", "background-color": "#fafafa"},
                "nav-link": {
                    "font-size": "12px",
                    "color": "black",
                    "text-align": "center",
                    "margin": "0 10px",
                },
                "nav-link-selected": {
                    "background-color": "#d0e8ff",
                    "color": "black",
                },
                # Tambahkan style khusus buat Logout
                "nav-link:hover": {
                    "color": "red",
                },
            }
        )

    if selected == "Home":
        st.markdown('<div class="title">Welcome to Pseudofile!</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Hello, {st.session_state.user_nama} 👋! Ready to PDFs your files?</div>', unsafe_allow_html=True)
        show_home()
    elif selected == "Compress PDF":
        show_compress_pdf()
    elif selected == "Gabungkan PDF":
        show_merge_pdf()
    elif selected == "Konversi File":
        show_convert_file()
    elif selected == "Tagihan":
        show_billing()
    elif selected == "Logout":
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

def show_home():
    st.markdown("""
    ### Our features just for you 
    """)
    show_boxes()

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
    st.markdown("""
    <style>
        .billing-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background-color: #f5f8fa;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        .billing-title {
            font-size: 24px;
            font-weight: bold;
            color: #000;
        }
        .billing-metric {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 12px 20px;
            border-radius: 8px;
            text-align: right;
        }
        .billing-metric-label {
            font-size: 14px;
            color: #555;
        }
        .billing-metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #000;
        }
    </style>
    """, unsafe_allow_html=True)

    user_email = st.session_state.get("user_email")
    if user_email:
        billing_response = supabase.table("log_user_activity") \
            .select("timestamp, action, filename, file_size_mb, result_file_size_mb, billing_amount") \
            .eq("email", user_email) \
            .order("timestamp", desc=True) \
            .execute()

        billing_data = billing_response.data

        if billing_data:
            total_tagihan = sum(item.get("billing_amount", 0) or 0 for item in billing_data)

            # Header dengan judul & total tagihan di kanan
            st.markdown(f"""
            <div class="billing-header">
                <div class="billing-title">💳 Tagihan Saya</div>
                <div class="billing-metric">
                    <div class="billing-metric-label">Total Tagihan</div>
                    <div class="billing-metric-value">Rp. {total_tagihan:,.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Ubah nama kolom agar lebih ramah
            import pandas as pd
            df = pd.DataFrame(billing_data)
            # Format tanggal saja dari timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date

            df = df.rename(columns={
                "timestamp": "Waktu",
                "action": "Aksi",
                "filename": "Nama File",
                "file_size_mb": "Ukuran Awal (MB)",
                "result_file_size_mb": "Ukuran Akhir (MB)",
                "billing_amount": "Biaya (Rp)"
            })

            st.caption("Riwayat tagihan Anda")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Belum ada aktivitas dari Anda")
    else:
        st.warning("Anda belum login")

def show_login_page():
    st.markdown("""
        <style>
            .centered-tabs .stTabs {
                display: flex;
                justify-content: center;
            }
            .input-container {
                max-width: 300px;
                margin: auto;
            }
        </style>
        """, unsafe_allow_html=True)
    st.markdown('<div class="h2">Login to Pseudofile</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Masuk atau daftar akun baru</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 2, 1])
    with center:
        with st.container():
        # Tab login dan register
            tab1, tab2 = st.tabs(["Login", "Register"])

            with tab1:
                with st.container():
                    st.markdown('<div class="input-container">', unsafe_allow_html=True)
                    email = st.text_input("Email", key="login_email")
                    password = st.text_input("Password", type="password", key="login_password")
                    if st.button("Login"):
                        user = login_user(email, password)
                        if user:
                            st.success("Login berhasil!")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            with tab2:
                with st.container():
                    st.markdown('<div class="input-container">', unsafe_allow_html=True)
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
                    st.markdown('</div>', unsafe_allow_html=True)

def powered_by():
    st.markdown("""
<div style='text-align: center; margin-top: 3rem; color: #888; font-size: 14px;'>
    <img src='https://streamlit.io/images/brand/streamlit-logo-primary-colormark-darktext.png' width='100' /><br>
    Powered by <strong>Pseudofile Team</strong><br>
    Built with ❤️ using Streamlit and Supabase
</div>
""", unsafe_allow_html=True)


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
    show_landing_page()
    powered_by()

if __name__ == "__main__":
    main()
