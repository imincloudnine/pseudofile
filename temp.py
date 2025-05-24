def show_uploaded_files():
    st.markdown("""
    <style>
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
            
            # Display uploaded files
        if files_data:
                st.markdown("### 📁 File Terunggah")
                st.caption("File yang telah Anda unggah (akan dihapus setelah 1 jam)")
                
                files_df = pd.DataFrame(files_data)
                files_df["uploaded_at"] = pd.to_datetime(files_df["uploaded_at"])
                tz = files_df["uploaded_at"].dt.tz  # Get timezone from uploaded_at
                now = pd.Timestamp.now(tz=tz)  # Make now tz-aware
                files_df["time_remaining"] = (files_df["uploaded_at"] + pd.Timedelta(hours=1) - now).dt.total_seconds()

                # Format for display
                files_df = files_df.rename(columns={
                    "filename": "Nama File",
                    "filesize": "Ukuran (MB)",
                    "uploaded_at": "Waktu Unggah",
                    "time_remaining": "Waktu Tersisa (detik)",
                    "file_path": "Path File",
                    "public_url": "URL Publik"
                })

                # Create a download link column
                def make_download_link(row):
                    return f'<a href="{row["URL Publik"]}" target="_blank" class="download-link">Download</a>'

                files_df["Download"] = files_df.apply(make_download_link, axis=1)

                # Select columns to display
                display_df = files_df[["Nama File", "Ukuran (MB)", "Waktu Unggah", "Waktu Tersisa (detik)", "Path File", "URL Publik", "Download"]]
                st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Belum ada aktivitas dari Anda")
    else:
        st.warning("Anda belum login")