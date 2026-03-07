# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "appuser" with user ID 1000
RUN useradd -m -u 1000 appuser
USER appuser
ENV HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH

# Copy everything with correct ownership
COPY --chown=appuser:appuser . .

# Install dependencies as the user
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Health check - verify app is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose port
EXPOSE 8501

# Run Streamlit with production settings
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--logger.level=error"]# Ensure the startup script is executable
RUN chmod +x scripts/run_prod.sh

# Expose the default Hugging Face port 7860
EXPOSE 7860

# Command to run the application
CMD ["./scripts/run_prod.sh"]
