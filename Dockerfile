# Use conda base image for optimized NumPy/BLAS (MKL)
FROM continuumio/miniconda3:latest

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python packages via conda (for optimized NumPy) and pip (for others)
# First install NumPy, SciPy, pandas via conda (MKL-optimized)
RUN conda install -y -c conda-forge \
    numpy=1.26.4 \
    scipy \
    pandas \
    scikit-learn \
    && conda clean -afy

# Install remaining packages via pip
RUN pip install --no-cache-dir \
    pydantic \
    python-dotenv \
    llama-cloud-services \
    matplotlib \
    Flask==2.3.3 \
    Werkzeug==2.3.7 \
    python-dateutil==2.8.2 \
    tensorflow==2.16.2 \
    "tensorflow_probability[tf]==0.24.0" \
    SQLAlchemy==2.0.39 \
    fastapi==0.115.8 \
    "uvicorn[standard]==0.34.0" \
    python-multipart==0.0.17 \
    passlib[bcrypt]==1.7.4 \
    "python-jose[cryptography]==3.3.0" \
    email-validator==2.1.0 \
    "bcrypt<4.0.0" \
    "openai>=1.0.0" \
    numba \
    alembic==1.13.0 \
    psycopg2-binary==2.9.9

# Copy application code
COPY . .

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Start command
CMD ["sh", "-c", "python scripts/migrate.py upgrade head && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

