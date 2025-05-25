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
from datetime import datetime, timedelta
import threading
import time
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
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

# New functions for file upload logging
def upload_file_to_storage(bucket_name, file_path, file_data):
    """
    Upload a file to Supabase Storage and return the public URL
    """
    try:
        # Upload file to storage
        response = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_data,
            {"content-type": "application/octet-stream"}
        )
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Upload error: {response.error}")
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return public_url
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        return None

def log_file_upload(user_id, email, action, activity_type, filename, file_size_mb, file_path, public_url):
    """
    Log file upload to both log_user_activity and files tables
    """
    try:
        # Generate a unique ID for both records
        activity_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # 1. Insert into log_user_activity table
        activity_payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "email": email,
            "action": action,
            "activity_type": activity_type,
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        activity_response = supabase.table("log_user_activity").insert(activity_payload).execute()
        
        # 2. Insert into files table - ensure filesize is a float/numeric value
        file_payload = {
            "id": file_id,
            "user_id": user_id,
            "filename": filename,
            "filesize": float(file_size_mb),  # Explicitly convert to float
            "file_path": file_path,
            "public_url": public_url,
            "uploaded_at": timestamp
        }
        
        file_response = supabase.table("files").insert(file_payload).execute()
        
        return activity_response.data is not None and file_response.data is not None
    except Exception as e:
        st.error(f"Failed to log file upload: {e}")
        return False

def handle_file_upload(uploaded_file, user_id, email, action_type):
    """
    Handle file upload, storage, and logging
    """
    try:
        # Calculate file size in MB
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        # Create a unique file path
        file_path = f"{user_id}/{uuid.uuid4()}_{uploaded_file.name}"
        
        # Upload to storage - using "files" bucket as specified
        public_url = upload_file_to_storage(
            bucket_name="files",  # Updated bucket name
            file_path=file_path,
            file_data=uploaded_file.getvalue()
        )
        
        if not public_url:
            return False, None
            
        # Log the file upload
        success = log_file_upload(
            user_id=user_id,
            email=email,
            action=action_type,
            activity_type="file_operation",
            filename=uploaded_file.name,
            file_size_mb=file_size_mb,
            file_path=file_path,
            public_url=public_url
        )
        
        return success, public_url
    except Exception as e:
        st.error(f"Failed to handle file upload: {e}")
        return False, None

def cleanup_old_files():
    """
    Clean up files older than one hour (changed from one minute)
    """
    try:
        # Calculate timestamp for one hour ago (changed from one minute)
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        # Get files older than one hour
        response = supabase.table("files").select("*").lt("uploaded_at", one_hour_ago).execute()
        
        if not response.data:
            return True  # No files to clean up
            
        for file in response.data:
            # 1. Delete from storage
            bucket_name = "files"  # Updated bucket name
            file_path = file["file_path"]
            
            supabase.storage.from_(bucket_name).remove([file_path])
            
            # 2. Update log_user_activity to remove file reference
            supabase.table("log_user_activity").update({"filename": "deleted_file"}).eq("user_id", file["user_id"]).eq("filename", os.path.basename(file_path)).execute()
            
            # 3. Delete from files table
            supabase.table("files").delete().eq("id", file["id"]).execute()
            
        return True
    except Exception as e:
        st.error(f"Failed to clean up old files: {e}")
        return False

# Original functions with modifications for file logging
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
        elif conversion_type == "pdf_to_word":  # Fixed bug: added explicit condition
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
        elif conversion_type == "image_to_pdf":
            image = Image.open(input_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(output_path, "PDF", resolution=100.0)
        else:
            raise ValueError(f"Conversion type not supported: {conversion_type}")

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
                <div class="feature-desc">Ubah file dari Word atau gambar ke PDF.</div>
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
            options=["Home", "Compress PDF", "Gabungkan PDF", "Konversi File", "Tagihan", "File saya", "Logout"],
            icons=["house", "file-earmark-zip", "files", "filetype-pdf", "currency-dollar", "folder2" ,"box-arrow-right"],
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
    elif selected == "File saya":
        show_uploaded_files()
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
            # First, handle the file upload and logging
            upload_success, public_url = handle_file_upload(
                uploaded_file=uploaded_file,
                user_id=st.session_state.user_id,
                email=st.session_state.user_email,
                action_type="upload_for_compression"
            )
            
            if not upload_success:
                st.error("Gagal mengunggah file")
                return
                
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
                        # Format billing amount as Indonesian Rupiah
                        formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                        st.success(f"PDF berhasil dikompres! (Biaya: {formatted_billing})")
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
            # Log each file upload
            for uploaded_file in uploaded_files:
                upload_success, _ = handle_file_upload(
                    uploaded_file=uploaded_file,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    action_type="upload_for_merge"
                )
                
                if not upload_success:
                    st.error(f"Gagal mengunggah file: {uploaded_file.name}")
                    return
            
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
                            # Format billing amount as Indonesian Rupiah
                            formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                            st.success(f"PDF berhasil digabungkan! (Biaya: {formatted_billing})")
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
        ["Word ke PDF", "PDF ke Word", "Image ke PDF"],
        horizontal=True
    )
    
    if conversion_type == "Word ke PDF":
        uploaded_file = st.file_uploader("Unggah file Word (.docx)", type=["docx"])
        if uploaded_file and st.button("Konversi ke PDF"):
            # Log file upload
            upload_success, _ = handle_file_upload(
                uploaded_file=uploaded_file,
                user_id=st.session_state.user_id,
                email=st.session_state.user_email,
                action_type="upload_for_word_to_pdf"
            )
            
            if not upload_success:
                st.error("Gagal mengunggah file")
                return
                
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
                            # Format billing amount as Indonesian Rupiah
                            formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                            st.success(f"Konversi berhasil! (Biaya: {formatted_billing})")
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=f,
                                file_name="converted.pdf",
                                mime="application/pdf"
                            )
    elif conversion_type == "PDF ke Word":
        uploaded_file = st.file_uploader("Unggah file PDF", type=["pdf"])
        if uploaded_file and st.button("Konversi ke Word"):
            # Log file upload
            upload_success, _ = handle_file_upload(
                uploaded_file=uploaded_file,
                user_id=st.session_state.user_id,
                email=st.session_state.user_email,
                action_type="upload_for_pdf_to_word"
            )
            
            if not upload_success:
                st.error("Gagal mengunggah file")
                return
                
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
                            # Format billing amount as Indonesian Rupiah
                            formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                            st.success(f"Konversi berhasil! (Biaya: {formatted_billing})")
                            st.download_button(
                                label="⬇️ Download Word",
                                data=f,
                                file_name="converted.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
    else: # Image to PDF
        uploaded_file = st.file_uploader("Unggah file gambar", type=["jpg", "jpeg", "png"])
        if uploaded_file and st.button("Konversi ke PDF"):
            # Log file upload
            upload_success, _ = handle_file_upload(
                uploaded_file=uploaded_file,
                user_id=st.session_state.user_id,
                email=st.session_state.user_email,
                action_type="upload_for_image_to_pdf"
            )
            
            if not upload_success:
                st.error("Gagal mengunggah file")
                return
                
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input.jpg")
                output_path = os.path.join(tmpdir, "output.pdf")

                with open(input_path, "wb") as f:
                    f.write(uploaded_file.read())

                with st.spinner("Mengonversi..."):
                    success, billing_amount = convert_file(
                        input_path=input_path,
                        output_path=output_path,
                        conversion_type="image_to_pdf",
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email,
                        original_filename=uploaded_file.name
                    )

                    if success:
                        with open(output_path, "rb") as f:
                            # Format billing amount as Indonesian Rupiah
                            formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                            st.success(f"Konversi berhasil! (Biaya: {formatted_billing})")
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=f,
                                file_name="converted.pdf",
                                mime="application/pdf"
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
        .download-link {
            color: #4fc3f7;
            text-decoration: none;
            cursor: pointer;
        }
        .download-link:hover {
            text-decoration: underline;
        }
    </style>
    """, unsafe_allow_html=True)

    user_email = st.session_state.get("user_email")
    if user_email:
        # Get billing data from log_user_activity
        billing_response = supabase.table("log_user_activity") \
            .select("timestamp, action, filename, file_size_mb, result_file_size_mb, billing_amount") \
            .eq("email", user_email) \
            .order("timestamp", desc=True) \
            .execute()

        billing_data = billing_response.data
        
        # Get file upload data from files table
        files_response = supabase.table("files") \
            .select("*") \
            .eq("user_id", st.session_state.user_id) \
            .order("uploaded_at", desc=True) \
            .execute()
            
        files_data = files_response.data

        if billing_data:
            total_tagihan = sum(item.get("billing_amount", 0) or 0 for item in billing_data)

            # Format total tagihan as Indonesian Rupiah
            formatted_total = f"Rp {total_tagihan:,}".replace(",", ".")

            # Header dengan judul & total tagihan di kanan
            st.markdown(f"""
            <div class="billing-header">
                <div class="billing-title">💳 Tagihan Saya</div>
                <div class="billing-metric">
                    <div class="billing-metric-label">Total Tagihan</div>
                    <div class="billing-metric-value">{formatted_total}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Ubah nama kolom agar lebih ramah
            import pandas as pd
            df = pd.DataFrame(billing_data)
            # Format tanggal saja dari timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date
            
            # Format billing amount as Indonesian Rupiah
            df["billing_amount"] = df["billing_amount"].apply(lambda x: f"Rp {x:,}".replace(",", ".") if x else "Rp 0")

            df = df.rename(columns={
                "timestamp": "Waktu",
                "action": "Aksi",
                "filename": "Nama File",
                "file_size_mb": "Ukuran Awal (MB)",
                "result_file_size_mb": "Ukuran Akhir (MB)",
                "billing_amount": "Biaya"
            })

            st.caption("Riwayat tagihan Anda")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Belum ada aktivitas dari Anda")
    else:
        st.warning("Anda belum login")

def show_uploaded_files():
    user_email = st.session_state.get("user_email")
    if not user_email: # Pastikan user sudah login
        st.warning("Anda belum login. Silakan login untuk melihat file Anda.")
        return

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User ID tidak ditemukan. Tidak dapat mengambil file.")
        return

    try:
        # Ambil hanya kolom yang benar-benar dibutuhkan dari tabel 'files'
        files_response = supabase.table("files") \
            .select("filename, filesize, uploaded_at, public_url") \
            .eq("user_id", user_id) \
            .order("uploaded_at", desc=True) \
            .execute()
    except Exception as e:
        st.error(f"Gagal mengambil data file dari Supabase: {e}")
        return
            
    files_data = files_response.data
            
    if not files_data:
        st.info("File expired atau belum ada file yang diunggah.")
        return

    st.markdown("### 📁 File Terunggah") # Judul disesuaikan
            
    files_df = pd.DataFrame(files_data)

    # --- Transformasi Data agar Sesuai Kolom Target Visual ---

    # 1. Waktu (dari uploaded_at, format YYYY-MM-DD)
    files_df["uploaded_at_dt"] = pd.to_datetime(files_df["uploaded_at"])
    files_df["Waktu"] = files_df["uploaded_at_dt"].dt.strftime('%Y-%m-%d')

    # 2. Aksi (statis untuk konteks ini)
    files_df["Status"] = "File Tersedia" 

    # 3. Nama File (langsung dari filename)
    files_df["Nama File"] = files_df["filename"]

    # 4. Ukuran Awal (MB) (dari filesize)
    # Asumsi 'filesize' adalah dalam MB. Jika tidak, konversi dulu.
    # Pastikan 'filesize' adalah numerik sebelum formatting
    files_df["filesize_numeric"] = pd.to_numeric(files_df["filesize"], errors='coerce')
    files_df["Ukuran Awal (MB)"] = files_df["filesize_numeric"].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
    )

    # 5. Ukuran Akhir (MB) (statis "None" karena tidak relevan untuk daftar file biasa)
    files_df["Ukuran Akhir (MB)"] = "None"
    
    # 7. Link Download (dari public_url)
    # Kolom ini akan berisi URL asli, akan dikonfigurasi sebagai link di st.dataframe
    files_df["URL Publik"] = files_df["public_url"]
    
    def make_download_link(row):
        return f'<a href="{row["URL Publik"]}" target="_blank" class="download-link">Download</a>'

    files_df["Download"] = files_df.apply(make_download_link, axis=1)

    tz = files_df["uploaded_at_dt"].dt.tz
    now_utc = pd.Timestamp.now(tz='UTC')
    if tz is None: # Jika uploaded_at adalah naive datetime, asumsikan UTC
        now_localized = now_utc
    else: # Jika uploaded_at adalah aware datetime, konversi now() ke timezone yang sama
        now_localized = now_utc.tz_convert(tz)
    
    files_df["time_remaining_seconds"] = (files_df["uploaded_at_dt"] + pd.Timedelta(hours=1) - now_localized).dt.total_seconds()
    def format_time_remaining(seconds):
        if seconds < 0: return "Expired"
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}d"
    files_df["Sisa Waktu"] = files_df["time_remaining_seconds"].apply(format_time_remaining)


    # --- Pilih Kolom yang Akan Ditampilkan Sesuai Urutan Gambar ---
    # Indeks DataFrame akan otomatis muncul seperti di gambar.
    display_df = files_df[[
        "Waktu", 
        "Status",
        "Sisa Waktu", 
        "Nama File", 
        "URL Publik",
    ]]
    
    # Tampilkan menggunakan st.dataframe dengan konfigurasi kolom
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "URL Publik": st.column_config.LinkColumn(
                "URL",  # Label untuk kolom di tabel UI
                help="Klik untuk mengunduh file", # Tooltip
                display_text="Buka" # Teks yang akan muncul sebagai link di setiap baris
            )
            # Jika ingin mengkonfigurasi kolom lain, tambahkan di sini
            # "Ukuran Awal (MB)": st.column_config.NumberColumn(format="%.2f MB"),
        },
        hide_index=False # Gambar referensi menampilkan indeks, jadi jangan disembunyikan
    )
    st.caption("*) File akan dihapus otomatis setelah 1 jam dari waktu unggah.")
    
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
                # Save session to prevent losing state on refresh
                st.session_state["_is_session_persisted"] = True
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

def setup_cleanup_job():
    """
    Set up a background thread to clean up old files
    """
    def cleanup_job():
        while True:
            cleanup_old_files()
            time.sleep(60)  # Run every minute
    
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
    cleanup_thread.start()

def main():
    inject_css()
    
    # Setup cleanup job
    setup_cleanup_job()

    # Setup session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        
    # Check for persisted session
    if st.session_state.get("_is_session_persisted"):
        # Session already exists, no need to relogin
        pass

    # Jika sudah login
    if st.session_state.logged_in:
        show_dashboard()
        return

    # Jika belum login
    show_landing_page()
    powered_by()

if __name__ == "__main__":
    main()
