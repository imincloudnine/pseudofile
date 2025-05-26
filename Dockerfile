FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (opsional tapi bantu kalau ada error dependensi wheel / build)
RUN apt-get update && apt-get install -y \
    build-essential \
    libreoffice \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua source code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Jalankan aplikasi Streamlit
CMD ["streamlit", "run", "home.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
