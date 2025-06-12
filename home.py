import streamlit as st
import bcrypt
import os
import tempfile
from PIL import Image
from supabase import create_client, Client
from pypdf import PdfReader, PdfWriter
import subprocess
import sys
from streamlit_option_menu import option_menu
from pdf2docx import Converter
import uuid
from datetime import datetime, timedelta
import threading
import time
import pandas as pd
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Get from environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

st.set_page_config(layout="wide", page_title="Pseudofile - PDF Worker", page_icon="📄")

# Enhanced CSS with better styling
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
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
        margin: 200px auto;
        margin-top: 100px;
    }
    
    .title {
        text-align: center;
        font-weight: 700;
        font-size: 42px;
        color: #2c3e50;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .h2 {
        text-align: center;
        font-weight: 600;
        font-size: 24px;
        color: #2c3e50;
        margin-bottom: 15px;        
    }
    
    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #7f8c8d;
        margin-bottom: 30px;
        font-style: italic;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 12px 0;
        font-weight: 600;
        width: 100%;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stTextInput>div>div>input {
        padding: 12px;
        border-radius: 10px;
        border: 2px solid #e1e8ed;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .error-alert {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        padding: 12px;
        border-radius: 10px;
        font-weight: 500;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
    }
    
    .success-alert {
        background: linear-gradient(135deg, #51cf66, #40c057);
        color: white;
        padding: 12px;
        border-radius: 10px;
        font-weight: 500;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 4px 15px rgba(81, 207, 102, 0.3);
    }
    
    .feature-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        text-align: center;
        transition: all 0.3s ease;
        height: 240px;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .feature-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .feature-icon {
        font-size: 48px;
        margin-bottom: 15px;
        transition: transform 0.3s ease;
    }
    
    .feature-box:hover .feature-icon {
        transform: scale(1.1);
    }
    
    .feature-title {
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 12px;
        color: #2c3e50;
        transition: color 0.3s ease;
    }
    
    .feature-box:hover .feature-title {
        color: white;
    }
    
    .feature-desc {
        font-size: 14px;
        color: #7f8c8d;
        line-height: 1.5;
        transition: color 0.3s ease;
    }
    
    .feature-box:hover .feature-desc {
        color: rgba(255, 255, 255, 0.9);
    }
    
    .billing-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        color: white;
    }
    
    .billing-title {
        font-size: 26px;
        font-weight: bold;
    }
    
    .billing-metric {
        background-color: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 15px 25px;
        border-radius: 12px;
        text-align: right;
    }
    
    .billing-metric-label {
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 5px;
    }
    
    .billing-metric-value {
        font-size: 28px;
        font-weight: bold;
    }
    
    .download-link {
        color: #667eea;
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
    }
    
    .download-link:hover {
        color: #764ba2;
        text-decoration: underline;
    }
    
    .settings-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .timer-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
        font-weight: 600;
    }
    
    /* Navbar improvements */
    .css-1r6slb0.e1tzin5v0 {
        width: 100% !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stApp {
        margin-top: -50px;
    }
    
    .css-10trblm.e16nr0p30 {
        width: 100% !important;
    }
    
    /* File upload area styling */
    .stFileUploader>div>div {
        border: 2px dashed #667eea;
        border-radius: 15px;
        padding: 20px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        transition: all 0.3s ease;
    }
    
    .stFileUploader>div>div:hover {
        border-color: #764ba2;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    }
    </style>
    """, unsafe_allow_html=True)

# Session persistence functions
def save_session_to_supabase(user_id, session_data):
    """Save session data to Supabase for persistence"""
    try:
        session_payload = {
            "user_id": user_id,
            "session_data": session_data,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        response = supabase.table("user_sessions").upsert(session_payload, on_conflict="user_id").execute()
        return response.data is not None
    except Exception as e:
        print(f"Failed to save session: {e}")
        return False

def load_session_from_supabase(user_id):
    """Load session data from Supabase"""
    try:
        response = supabase.table("user_sessions").select("*").eq("user_id", user_id).execute()
        
        if response.data:
            session = response.data[0]
            expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
            if expires_at > datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
                return session["session_data"]
        return None
    except Exception as e:
        print(f"Failed to load session: {e}")
        return None

def cleanup_expired_sessions():
    """Clean up expired sessions from database"""
    try:
        current_time = datetime.utcnow().isoformat()
        supabase.table("user_sessions").delete().lt("expires_at", current_time).execute()
        return True
    except Exception as e:
        print(f"Failed to cleanup expired sessions: {e}")
        return False

# User settings functions
def save_user_settings(user_id, settings):
    """Save user settings to database"""
    try:
        settings_payload = {
            "user_id": user_id,
            "settings": settings,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("user_settings").upsert(settings_payload, on_conflict="user_id").execute()
        return response.data is not None
    except Exception as e:
        print(f"Failed to save user settings: {e}")
        return False

def load_user_settings(user_id):
    """Load user settings from database"""
    try:
        response = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
        if response.data:
            return response.data[0]["settings"]
        return {"default_expiration_hours": 1}  # Default 1 hour
    except Exception as e:
        print(f"Failed to load user settings: {e}")
        return {"default_expiration_hours": 1}

# Enhanced Word to PDF conversion with multiple fallback methods
def convert_word_to_pdf_enhanced(input_path, output_path):
    """Enhanced Word to PDF conversion with multiple fallback methods"""
    try:
        # Method 1: Try using python-docx2pdf (works on Windows)
        try:
            from docx2pdf import convert
            convert(input_path, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception as e1:
            print(f"Method 1 (docx2pdf) failed: {e1}")
            
        # Method 2: Try using LibreOffice (works on Linux/Mac)
        try:
            result = subprocess.run([
                'libreoffice', '--headless', '--convert-to', 'pdf', 
                '--outdir', os.path.dirname(output_path), input_path
            ], check=True, capture_output=True, timeout=60)
            
            expected_output = os.path.join(
                os.path.dirname(output_path), 
                os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
            )
            
            if os.path.exists(expected_output):
                if expected_output != output_path:
                    os.rename(expected_output, output_path)
                return True
        except Exception as e2:
            print(f"Method 2 (LibreOffice) failed: {e2}")
            
        # Method 3: Try using pandoc
        try:
            subprocess.run([
                'pandoc', input_path, '-o', output_path
            ], check=True, capture_output=True, timeout=60)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception as e3:
            print(f"Method 3 (pandoc) failed: {e3}")
            
        # Method 4: Try using unoconv (if available)
        try:
            subprocess.run([
                'unoconv', '-f', 'pdf', '-o', output_path, input_path
            ], check=True, capture_output=True, timeout=60)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception as e4:
            print(f"Method 4 (unoconv) failed: {e4}")
            
        return False
    except Exception as e:
        print(f"All conversion methods failed: {e}")
        return False

# File upload and storage functions
def upload_file_to_storage(bucket_name, file_path, file_data):
    """Upload a file to Supabase Storage and return the public URL"""
    try:
        response = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_data,
            {"content-type": "application/octet-stream"}
        )
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Upload error: {response.error}")
        
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return public_url
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        return None

def log_file_upload(user_id, email, action, activity_type, filename, file_size_mb, file_path, public_url):
    """Log file upload to both log_user_activity and files tables"""
    try:
        timestamp = datetime.utcnow().isoformat()
        
        # Insert into log_user_activity table
        activity_payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "email": email,
            "action": action,
            "activity_type": activity_type,
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2),
            "timestamp": timestamp
        }
        
        activity_response = supabase.table("log_user_activity").insert(activity_payload).execute()
        
        return activity_response.data is not None
    except Exception as e:
        st.error(f"Failed to log file upload: {e}")
        return False

def cleanup_old_files():
    """Clean up expired files based on user-selected expiration time"""
    try:
        # Get all files from database
        response = supabase.table("files").select("*").execute()
        
        if not response.data:
            return True
            
        current_time = datetime.utcnow()
        
        for file in response.data:
            # Skip if file has no expiration (0 means no expiration)
            if file.get("expiration_hours", 1) == 0:
                continue
                
            # Get uploaded time and expiration hours
            uploaded_time = datetime.fromisoformat(file["uploaded_at"].replace('Z', '+00:00'))
            expiration_hours = file.get("expiration_hours", 1)  # Default 1 hour if not set
            
            # Check if file has expired
            if current_time > uploaded_time + timedelta(hours=expiration_hours):
                bucket_name = "files"
                file_path = file["file_path"]
                
                # Delete from storage
                try:
                    supabase.storage.from_(bucket_name).remove([file_path])
                except:
                    pass  # Continue even if storage deletion fails
                
                # Update log_user_activity
                try:
                    supabase.table("log_user_activity").update({"filename": "deleted_file"}) \
                        .eq("user_id", file["user_id"]) \
                        .eq("filename", os.path.basename(file_path)) \
                        .execute()
                except:
                    pass
                
                # Delete from files table
                try:
                    supabase.table("files").delete().eq("id", file["id"]).execute()
                except:
                    pass
                
        return True
    except Exception as e:
        print(f"Failed to clean up old files: {e}")
        return False

def handle_file_upload(uploaded_file, user_id, email, action_type):
    """Handle file upload with default expiration time from user settings"""
    try:
        if uploaded_file is None:
            return False, None

        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        file_path = f"{user_id}/{uuid.uuid4()}_{uploaded_file.name}"
        
        # Upload file first
        public_url = upload_file_to_storage(
            bucket_name="files",
            file_path=file_path,
            file_data=uploaded_file.getvalue()
        )
        
        if not public_url:
            return False, None

        # Get user's default expiration setting
        user_settings = load_user_settings(user_id)
        default_expiration_hours = user_settings.get("default_expiration_hours", 1)
        
        # Add file record with expiration time
        file_payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "filename": uploaded_file.name,
            "filesize": float(file_size_mb),
            "file_path": file_path,
            "public_url": public_url,
            "uploaded_at": datetime.utcnow().isoformat(),
            "expiration_hours": default_expiration_hours
        }
        
        supabase.table("files").insert(file_payload).execute()
        
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
        
        # Show expiration info
        if default_expiration_hours > 0:
            expiration_time = datetime.utcnow() + timedelta(hours=default_expiration_hours)
            st.info(f"📅 File akan dihapus otomatis pada: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')} ({default_expiration_hours} jam dari sekarang)")
        else:
            st.info("♾ File tidak akan dihapus otomatis")
        
        return success, public_url

    except Exception as e:
        st.error(f"Failed to handle file upload: {e}")
        return False, None

# Core processing functions
def log_user_activity(user_id, email, action, activity_type, filename, file_size_mb, result_file_size_mb=None, billing_amount=0):
    """Log user activity to database"""
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
        st.error(f"Failed to log activity: {e}")
        return False

def compress_pdf(input_path, output_path, user_id, email, original_filename):
    """Compress PDF file"""
    try:
        input_file_size = os.path.getsize(input_path) / (1024 * 1024)

        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        # Add compression
        writer.add_metadata({})
        
        with open(output_path, "wb") as f:
            writer.write(f)

        result_file_size = os.path.getsize(output_path) / (1024 * 1024)
        billing_amount = int(input_file_size * 1000)

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
        st.error(f"Failed to compress PDF: {e}")
        return False, 0

def merge_pdf(input_files, output_path, user_id, email):
    """Merge multiple PDF files"""
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
        billing_amount = int(total_size * 500)

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
        st.error(f"Failed to merge PDF: {e}")
        return False, 0

def convert_file(input_path, output_path, conversion_type, user_id, email, original_filename):
    """Convert files between different formats"""
    try:
        input_size = os.path.getsize(input_path) / (1024 * 1024)
        
        if conversion_type == "word_to_pdf":
            success = convert_word_to_pdf_enhanced(input_path, output_path)
            if not success:
                raise Exception("Word to PDF conversion failed with all methods")
                
        elif conversion_type == "pdf_to_word":
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
        billing_amount = int(input_size * 1500)

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
        st.error(f"Failed to convert file: {e}")
        return False, 0

# UI Components
def show_enhanced_boxes():
    """Display enhanced feature boxes"""
    st.markdown("### ✨ Our Premium Features")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">🧩</div>
                <div class="feature-title">Gabungkan PDF</div>
                <div class="feature-desc">Satukan beberapa file PDF menjadi satu dokumen dengan kualitas terbaik dan proses yang cepat.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">🔄</div>
                <div class="feature-title">Konversi File</div>
                <div class="feature-desc">Ubah file dari Word, gambar, atau format lain ke PDF dengan hasil berkualitas tinggi.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="feature-box">
                <div class="feature-icon">📉</div>
                <div class="feature-title">Kompres PDF</div>
                <div class="feature-desc">Perkecil ukuran file PDF tanpa mengurangi kualitas visual dan keterbacaan.</div>
            </div>
        """, unsafe_allow_html=True)

def show_landing_page():
    """Display landing page with navigation"""
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Home", "Login/Register"],
            icons=["house", "box-arrow-right"],
            orientation="horizontal",
            default_index=0,
            styles={
                "container": {"padding": "15px", "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "border-radius": "15px"},
                "nav-link": {
                    "font-size": "14px",
                    "color": "white",
                    "text-align": "center",
                    "margin": "0px 15px",
                    "padding": "10px 20px",
                    "border-radius": "10px",
                    "transition": "all 0.3s ease",
                },
                "nav-link-selected": {
                    "background-color": "rgba(255, 255, 255, 0.2)",
                    "color": "white",
                    "backdrop-filter": "blur(10px)",
                },
            }
        )

    if selected == "Home":
        show_hero()
        show_enhanced_boxes()
    elif selected == "Login/Register":
        show_login_page()

def show_hero():
    """Display hero section"""
    st.markdown('<div class="title">Pseudofile</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your PDF worker in overtime - Fast, Reliable, Professional</div>', unsafe_allow_html=True)

def show_dashboard():
    """Display main dashboard with navigation"""
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Home", "Compress PDF", "Gabungkan PDF", "Konversi File", "Tagihan", "File saya", "Logout"],
            icons=["house", "file-earmark-zip", "files", "filetype-pdf", "currency-dollar", "folder2", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "15px", "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "border-radius": "15px"},
                "nav-link": {
                    "font-size": "12px",
                    "color": "white",
                    "text-align": "center",
                    "margin": "0 8px",
                    "padding": "8px 12px",
                    "border-radius": "8px",
                    "transition": "all 0.3s ease",
                },
                "nav-link-selected": {
                    "background-color": "rgba(255, 255, 255, 0.2)",
                    "color": "white",
                    "backdrop-filter": "blur(10px)",
                },
            }
        )

    if selected == "Home":
        st.markdown('<div class="title">Welcome to Pseudofile!</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle">Hello, {st.session_state.user_nama} 👋! Ready to process your files?</div>', unsafe_allow_html=True)
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
        # Clear session from Supabase
        if st.session_state.get("user_id"):
            try:
                supabase.table("user_sessions").delete().eq("user_id", st.session_state.user_id).execute()
            except:
                pass
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.rerun()

def show_home():
    """Display home page content"""
    show_enhanced_boxes()
    
    # Add statistics section
    st.markdown("---")
    st.markdown("### 📊 Platform Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", "1,234", "12")
    with col2:
        st.metric("Files Processed", "45,678", "234")
    with col3:
        st.metric("Storage Saved", "2.3 TB", "45 GB")
    with col4:
        st.metric("Success Rate", "99.8%", "0.1%")

def show_compress_pdf():
    """Display PDF compression interface"""
    st.markdown("### 📦 Kompres PDF")
    st.markdown("Unggah file PDF yang ingin dikompres untuk mengurangi ukurannya tanpa kehilangan kualitas.")
    
    uploaded_file = st.file_uploader("Unggah file PDF", type="pdf", help="Maksimal ukuran file: 50MB")
    
    if uploaded_file is not None:
        # Show file info
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📄 File: {uploaded_file.name} | Ukuran: {file_size:.2f} MB")
        
        if st.button("🚀 Kompres PDF", use_container_width=True):
            if file_size > 50:
                st.error("❌ Ukuran file terlalu besar. Maksimal 50MB.")
                return
                
            upload_success, public_url = handle_file_upload(
                uploaded_file=uploaded_file,
                user_id=st.session_state.user_id,
                email=st.session_state.user_email,
                action_type="upload_for_compression"
            )
            
            if not upload_success:
                st.error("❌ Gagal mengunggah file")
                return
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
                tmp_input.write(uploaded_file.read())
                tmp_input_path = tmp_input.name

            tmp_output_path = tmp_input_path.replace(".pdf", "_compressed.pdf")

            with st.spinner("🔄 Sedang mengompres PDF..."):
                success, billing_amount = compress_pdf(
                    input_path=tmp_input_path,
                    output_path=tmp_output_path,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    original_filename=uploaded_file.name
                )

                if success:
                    with open(tmp_output_path, "rb") as f:
                        compressed_size = os.path.getsize(tmp_output_path) / (1024 * 1024)
                        reduction = ((file_size - compressed_size) / file_size) * 100
                        formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                        
                        st.success(f"✅ PDF berhasil dikompres! Pengurangan ukuran: {reduction:.1f}% (Biaya: {formatted_billing})")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Ukuran Asli", f"{file_size:.2f} MB")
                        with col2:
                            st.metric("Ukuran Setelah Kompresi", f"{compressed_size:.2f} MB", f"-{reduction:.1f}%")
                        
                        st.download_button(
                            label="⬇ Download PDF Terkompres",
                            data=f,
                            file_name=f"compressed_{uploaded_file.name}",
                            mime="application/pdf",
                            use_container_width=True
                        )

            # Cleanup temp files
            try:
                os.remove(tmp_input_path)
                os.remove(tmp_output_path)
            except:
                pass

def show_merge_pdf():
    """Display PDF merging interface"""
    st.markdown("### 🔄 Gabungkan PDF")
    st.markdown("Unggah dua atau lebih file PDF yang ingin digabungkan menjadi satu file.")
    
    uploaded_files = st.file_uploader(
        "Unggah file PDF",
        type=["pdf"],
        accept_multiple_files=True,
        help="Pilih minimal 2 file PDF untuk digabungkan"
    )
    
    if uploaded_files:
        st.info(f"📄 {len(uploaded_files)} file dipilih")
        
        # Show file list
        for i, file in enumerate(uploaded_files, 1):
            file_size = len(file.getvalue()) / (1024 * 1024)
            st.write(f"{i}. {file.name} ({file_size:.2f} MB)")
    
    if uploaded_files and len(uploaded_files) >= 2:
        if st.button("🚀 Gabungkan PDF", use_container_width=True):
            total_size = sum(len(f.getvalue()) for f in uploaded_files) / (1024 * 1024)
            
            if total_size > 100:
                st.error("❌ Total ukuran file terlalu besar. Maksimal 100MB.")
                return
            
            # Log each file upload
            for uploaded_file in uploaded_files:
                upload_success, _ = handle_file_upload(
                    uploaded_file=uploaded_file,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    action_type="upload_for_merge"
                )
                
                if not upload_success:
                    st.error(f"❌ Gagal mengunggah file: {uploaded_file.name}")
                    return
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "merged.pdf")
                
                with st.spinner("🔄 Sedang menggabungkan PDF..."):
                    success, billing_amount = merge_pdf(
                        input_files=uploaded_files,
                        output_path=output_path,
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email
                    )

                    if success:
                        with open(output_path, "rb") as f:
                            merged_size = os.path.getsize(output_path) / (1024 * 1024)
                            formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                            
                            st.success(f"✅ PDF berhasil digabungkan! (Biaya: {formatted_billing})")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Total File", len(uploaded_files))
                            with col2:
                                st.metric("Ukuran Hasil", f"{merged_size:.2f} MB")
                            
                            st.download_button(
                                label="⬇ Download PDF Gabungan",
                                data=f,
                                file_name="merged.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
    else:
        st.warning("⚠ Silakan unggah minimal dua file PDF untuk digabungkan.")

def show_convert_file():
    """Display file conversion interface"""
    st.markdown("### 📝 Konversi File")
    st.markdown("Pilih jenis konversi yang Anda inginkan.")
    
    conversion_type = st.radio(
        "Jenis Konversi",
        ["Word ke PDF", "PDF ke Word", "Image ke PDF"],
        horizontal=True
    )
    
    if conversion_type == "Word ke PDF":
        st.markdown("#### 📄 Word ke PDF")
        uploaded_file = st.file_uploader("Unggah file Word (.docx)", type=["docx"])
        
        if uploaded_file:
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📄 File: {uploaded_file.name} | Ukuran: {file_size:.2f} MB")
            
            if st.button("🚀 Konversi ke PDF", use_container_width=True):
                if file_size > 25:
                    st.error("❌ Ukuran file terlalu besar. Maksimal 25MB.")
                    return
                    
                upload_success, _ = handle_file_upload(
                    uploaded_file=uploaded_file,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    action_type="upload_for_word_to_pdf"
                )
                
                if not upload_success:
                    st.error("❌ Gagal mengunggah file")
                    return
                    
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.docx")
                    output_path = os.path.join(tmpdir, "output.pdf")

                    with open(input_path, "wb") as f:
                        f.write(uploaded_file.read())

                    with st.spinner("🔄 Mengonversi Word ke PDF..."):
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
                                result_size = os.path.getsize(output_path) / (1024 * 1024)
                                formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                                
                                st.success(f"✅ Konversi berhasil! (Biaya: {formatted_billing})")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Ukuran Word", f"{file_size:.2f} MB")
                                with col2:
                                    st.metric("Ukuran PDF", f"{result_size:.2f} MB")
                                
                                st.download_button(
                                    label="⬇ Download PDF",
                                    data=f,
                                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                        
    elif conversion_type == "PDF ke Word":
        st.markdown("#### 📄 PDF ke Word")
        uploaded_file = st.file_uploader("Unggah file PDF", type=["pdf"])
        
        if uploaded_file:
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📄 File: {uploaded_file.name} | Ukuran: {file_size:.2f} MB")
            
            if st.button("🚀 Konversi ke Word", use_container_width=True):
                if file_size > 25:
                    st.error("❌ Ukuran file terlalu besar. Maksimal 25MB.")
                    return
                    
                upload_success, _ = handle_file_upload(
                    uploaded_file=uploaded_file,
                    user_id=st.session_state.user_id,
                    email=st.session_state.user_email,
                    action_type="upload_for_pdf_to_word"
                )
                
                if not upload_success:
                    st.error("❌ Gagal mengunggah file")
                    return
                    
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.pdf")
                    output_path = os.path.join(tmpdir, "output.docx")

                    with open(input_path, "wb") as f:
                        f.write(uploaded_file.read())

                    with st.spinner("🔄 Mengonversi PDF ke Word..."):
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
                                result_size = os.path.getsize(output_path) / (1024 * 1024)
                                formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                                
                                st.success(f"✅ Konversi berhasil! (Biaya: {formatted_billing})")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Ukuran PDF", f"{file_size:.2f} MB")
                                with col2:
                                    st.metric("Ukuran Word", f"{result_size:.2f} MB")
                                
                                st.download_button(
                                    label="⬇ Download Word",
                                    data=f,
                                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True
                                )
                        
    else:  # Image to PDF
        st.markdown("#### 🖼 Image ke PDF")
        uploaded_file = st.file_uploader("Unggah file gambar", type=["jpg", "jpeg", "png", "bmp", "tiff"])
        
        if uploaded_file:
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"🖼 File: {uploaded_file.name} | Ukuran: {file_size:.2f} MB")
            
            # Show image preview
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded_file, caption="Preview", use_column_width=True)
            
            with col2:
                if st.button("🚀 Konversi ke PDF", use_container_width=True):
                    if file_size > 10:
                        st.error("❌ Ukuran file terlalu besar. Maksimal 10MB.")
                        return
                        
                    upload_success, _ = handle_file_upload(
                        uploaded_file=uploaded_file,
                        user_id=st.session_state.user_id,
                        email=st.session_state.user_email,
                        action_type="upload_for_image_to_pdf"
                    )
                    
                    if not upload_success:
                        st.error("❌ Gagal mengunggah file")
                        return
                        
                    with tempfile.TemporaryDirectory() as tmpdir:
                        input_path = os.path.join(tmpdir, f"input{os.path.splitext(uploaded_file.name)[1]}")
                        output_path = os.path.join(tmpdir, "output.pdf")

                        with open(input_path, "wb") as f:
                            f.write(uploaded_file.read())

                        with st.spinner("🔄 Mengonversi gambar ke PDF..."):
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
                                    result_size = os.path.getsize(output_path) / (1024 * 1024)
                                    formatted_billing = f"Rp {billing_amount:,}".replace(",", ".")
                                    
                                    st.success(f"✅ Konversi berhasil! (Biaya: {formatted_billing})")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Ukuran Gambar", f"{file_size:.2f} MB")
                                    with col2:
                                        st.metric("Ukuran PDF", f"{result_size:.2f} MB")
                                    
                                    st.download_button(
                                        label="⬇ Download PDF",
                                        data=f,
                                        file_name=f"{os.path.splitext(uploaded_file.name)[0]}.pdf",
                                        mime="application/pdf",
                                        use_container_width=True
                                    )

def show_billing():
    """Display billing information"""
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.warning("⚠ Anda belum login")
        return

    # Get billing data
    billing_response = supabase.table("log_user_activity") \
        .select("timestamp, action, filename, file_size_mb, result_file_size_mb, billing_amount") \
        .eq("email", user_email) \
        .order("timestamp", desc=True) \
        .execute()

    billing_data = billing_response.data

    if billing_data:
        total_tagihan = sum(item.get("billing_amount", 0) or 0 for item in billing_data)
        formatted_total = f"Rp {total_tagihan:,}".replace(",", ".")

        # Enhanced billing header
        st.markdown(f"""
        <div class="billing-header">
            <div class="billing-title">💳 Tagihan Saya</div>
            <div class="billing-metric">
                <div class="billing-metric-label">Total Tagihan</div>
                <div class="billing-metric-value">{formatted_total}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transaksi", len(billing_data))
        with col2:
            total_files = sum(1 for item in billing_data if item.get("file_size_mb"))
            st.metric("File Diproses", total_files)
        with col3:
            total_size = sum(item.get("file_size_mb", 0) or 0 for item in billing_data)
            st.metric("Total Data", f"{total_size:.1f} MB")
        with col4:
            avg_billing = total_tagihan / len(billing_data) if billing_data else 0
            st.metric("Rata-rata Biaya", f"Rp {avg_billing:,.0f}".replace(",", "."))

        # Data table
        df = pd.DataFrame(billing_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime('%Y-%m-%d %H:%M')
        df["billing_amount"] = df["billing_amount"].apply(lambda x: f"Rp {x:,}".replace(",", ".") if x else "Rp 0")

        df = df.rename(columns={
            "timestamp": "Waktu",
            "action": "Aksi",
            "filename": "Nama File",
            "file_size_mb": "Ukuran Awal (MB)",
            "result_file_size_mb": "Ukuran Akhir (MB)",
            "billing_amount": "Biaya"
        })

        st.markdown("### 📊 Riwayat Transaksi")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Export option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export ke CSV",
            data=csv,
            file_name=f"billing_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("📝 Belum ada aktivitas dari Anda")
def show_uploaded_files():
    """Display uploaded files with expiration settings"""
    user_email = st.session_state.get("user_email")
    user_id = st.session_state.get("user_id")
    
    if not user_email or not user_id:
        st.warning("⚠ Anda belum login. Silakan login untuk melihat file Anda.")
        return

    st.markdown("### 📁 File Saya")
    
    st.markdown("---")
    
    # Files list section
    st.markdown("#### 📋 Daftar File")
    
    try:
        files_response = supabase.table("files") \
            .select("id, filename, filesize, uploaded_at, public_url, expiration_hours") \
            .eq("user_id", user_id) \
            .order("uploaded_at", desc=True) \
            .execute()
    except Exception as e:
        st.error(f"❌ Gagal mengambil data file: {e}")
        return
            
    files_data = files_response.data
            
    if not files_data:
        st.info("📁 Belum ada file yang diunggah.")
        return

    # Statistics
    total_files = len(files_data)
    total_size = sum(float(f.get("filesize", 0)) for f in files_data)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total File", total_files)
    with col2:
        st.metric("Total Ukuran", f"{total_size:.2f} MB")
    with col3:
        st.metric("Rata-rata Ukuran", f"{total_size/total_files:.2f} MB" if total_files > 0 else "0 MB")
    
    # Process files data
    files_df = pd.DataFrame(files_data)
    files_df["uploaded_at_dt"] = pd.to_datetime(files_df["uploaded_at"])
    files_df["Waktu Unggah"] = files_df["uploaded_at_dt"].dt.strftime('%Y-%m-%d %H:%M:%S')
    files_df["Nama File"] = files_df["filename"]
    files_df["filesize_numeric"] = pd.to_numeric(files_df["filesize"], errors='coerce')
    files_df["Ukuran (MB)"] = files_df["filesize_numeric"].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
    )
    
    # Calculate expiration info
    now_utc = pd.Timestamp.now(tz='UTC')
    
    def calculate_expiration_info(row):
        expiration_hours = row.get("expiration_hours", 1)
        if expiration_hours == 0:
            return "♾ Permanen", "✅ Aktif", float('inf')
        
        uploaded_time = row["uploaded_at_dt"]
        expiration_time = uploaded_time + pd.Timedelta(hours=expiration_hours)
        time_remaining_seconds = (expiration_time - now_utc).total_seconds()
        
        if time_remaining_seconds <= 0:
            return "⏰ Expired", "❌ Expired", 0
        
        hours = int(time_remaining_seconds // 3600)
        minutes = int((time_remaining_seconds % 3600) // 60)
        
        if hours > 0:
            remaining_text = f"⏱ {hours}j {minutes}m"
        else:
            remaining_text = f"⏱ {minutes}m"
            
        return remaining_text, "✅ Aktif", time_remaining_seconds
    
    expiration_info = files_df.apply(calculate_expiration_info, axis=1, result_type='expand')
    files_df["Sisa Waktu"] = expiration_info[0]
    files_df["Status"] = expiration_info[1]
    files_df["time_remaining_seconds"] = expiration_info[2]
    
    # Add individual file expiration controls
    st.markdown("#### 🔧 Kontrol Individual")
    
    # Group files by status
    active_files = files_df[files_df["time_remaining_seconds"] > 0].copy()
    expired_files = files_df[files_df["time_remaining_seconds"] <= 0].copy()
    
    if not active_files.empty:
        st.markdown("*File Aktif:*")
        
        expiration_options = {
            0: "♾ Tanpa batas waktu",
            1: "⏰ 1 jam",
            2: "⏰ 2 jam", 
            6: "⏰ 6 jam",
            12: "⏰ 12 jam",
            24: "⏰ 24 jam"
        }
        
        # Display active files with controls
        for idx, file_row in active_files.iterrows():
            with st.expander(f"📄 {file_row['Nama File']} - {file_row['Sisa Waktu']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"*Ukuran:* {file_row['Ukuran (MB)']} MB")
                    st.write(f"*Diunggah:* {file_row['Waktu Unggah']}")
                    st.write(f"*Status:* {file_row['Status']}")
                
                with col2:
                    # Change expiration time
                    new_expiration = st.selectbox(
                        "Ubah batas waktu:",
                        options=list(expiration_options.keys()),
                        format_func=lambda x: expiration_options[x],
                        index=list(expiration_options.keys()).index(file_row.get("expiration_hours", 1)) if file_row.get("expiration_hours", 1) in expiration_options else 1,
                        key=f"exp_{file_row['id']}"
                    )
                    
                    if st.button("🔄 Update", key=f"update_{file_row['id']}"):
                        try:
                            supabase.table("files").update({"expiration_hours": new_expiration}).eq("id", file_row['id']).execute()
                            st.success("✅ Berhasil diupdate!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Gagal update: {e}")
                
                with col3:
                    # Download link
                    st.link_button("⬇ Download", file_row['public_url'], use_container_width=True)
                    
                    # Delete button
                   
    
    if not expired_files.empty:
        st.markdown("*File Expired:*")
        st.warning(f"⚠ {len(expired_files)} file telah expired dan akan dihapus otomatis")
        
        # Show expired files (read-only)
        expired_display = expired_files[["Waktu Unggah", "Nama File", "Ukuran (MB)", "Status"]]
        st.dataframe(expired_display, use_container_width=True, hide_index=True)
    
    # Real-time timer for active files
    if not active_files.empty:
        # Add JavaScript for real-time countdown
        st.markdown("""
        <script>
        function updateCountdowns() {
            // This would update countdowns in real-time
            // Implementation depends on specific file data
        }
        setInterval(updateCountdowns, 1000);
        </script>
        """, unsafe_allow_html=True)

def show_login_page():
    """Display login/register page"""
    st.markdown('<div class="h2">🔐 Login to Pseudofile</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Masuk atau daftar akun baru untuk mengakses semua fitur</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 2, 1])
    with center:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

        with tab1:
            with st.form("login_form"):
                email = st.text_input("📧 Email", placeholder="Masukkan email Anda")
                password = st.text_input("🔒 Password", type="password", placeholder="Masukkan password Anda")
                submitted = st.form_submit_button("🚀 Login", use_container_width=True)
                
                if submitted:
                    if not email or not password:
                        st.error("❌ Email dan password harus diisi!")
                    else:
                        user = login_user(email, password)
                        if user:
                            st.success("✅ Login berhasil!")
                            time.sleep(1)
                            st.rerun()

        with tab2:
            with st.form("register_form"):
                nama = st.text_input("👤 Nama Lengkap", placeholder="Masukkan nama lengkap Anda")
                email = st.text_input("📧 Email", placeholder="Masukkan email Anda")
                password = st.text_input("🔒 Password", type="password", placeholder="Minimal 6 karakter")
                confirm = st.text_input("🔒 Konfirmasi Password", type="password", placeholder="Ulangi password Anda")
                submitted = st.form_submit_button("📝 Register", use_container_width=True)
                
                if submitted:
                    if not all([nama, email, password, confirm]):
                        st.error("❌ Semua field wajib diisi!")
                    elif len(password) < 6:
                        st.error("❌ Password minimal 6 karakter!")
                    elif password != confirm:
                        st.error("❌ Password tidak cocok!")
                    else:
                        result = register_user(email, password, nama)
                        if result:
                            st.success("✅ Registrasi berhasil! Silakan login.")

def powered_by():
    """Display footer"""
    st.markdown("""
    <div style='text-align: center; margin-top: 3rem; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;'>
        <h3 style='margin-bottom: 1rem;'>🚀 Pseudofile</h3>
        <p style='margin-bottom: 1rem; opacity: 0.9;'>Powered by <strong>Pseudofile Team</strong></p>
        <p style='margin: 0; opacity: 0.8;'>Built with ❤ using Streamlit and Supabase</p>
    </div>
    """, unsafe_allow_html=True)

# Authentication functions
def login_user(email, password):
    """Authenticate user login"""
    try:
        result = supabase.table("user").select("*").eq("email", email).execute()
        if result.data:
            user = result.data[0]
            stored_hashed_password = user["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                # Set session state
                st.session_state.logged_in = True
                st.session_state.user_email = user["email"]
                st.session_state.user_nama = user["nama"]
                st.session_state.user_id = user["id"]
                
                # Save session to Supabase
                session_data = {
                    "logged_in": True,
                    "user_email": user["email"],
                    "user_nama": user["nama"],
                    "user_id": user["id"]
                }
                save_session_to_supabase(user["id"], session_data)
                
                return user
            else:
                st.error("❌ Password salah.")
                return None
        else:
            st.error("❌ Email tidak ditemukan.")
            return None
    except Exception as e:
        st.error(f"❌ Login gagal: {e}")
        return None

def register_user(email, password, nama):
    """Register new user"""
    try:
        if not email or not password or not nama:
            st.warning("⚠ Semua field wajib diisi.")
            return None

        existing = supabase.table("user").select("*").eq("email", email).execute()
        if existing.data:
            st.warning("⚠ Email sudah terdaftar.")
            return None

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        result = supabase.table("user").insert({
            "email": email,
            "password": hashed_password,
            "nama": nama
        }).execute()

        return result
    except Exception as e:
        st.error(f"❌ Registrasi gagal: {e}")
        return None

# Background cleanup job
def setup_cleanup_job():
    """Set up background cleanup job"""
    def cleanup_job():
        while True:
            cleanup_old_files()
            cleanup_expired_sessions()
            time.sleep(300)  # Run every 5 minutes
    
    cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
    cleanup_thread.start()

def initialize_session():
    """Initialize session state"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # Try to restore session if user_id exists
    if st.session_state.get("user_id") and not st.session_state.get("logged_in"):
        session_data = load_session_from_supabase(st.session_state.user_id)
        if session_data:
            for key, value in session_data.items():
                st.session_state[key] = value

def main():
    """Main application function"""
    inject_css()
    initialize_session()
    setup_cleanup_job()

    # Route to appropriate page
    if st.session_state.logged_in:
        show_dashboard()
    else:
        show_landing_page()
        powered_by()

if _name_ == "_main_":
    main()
