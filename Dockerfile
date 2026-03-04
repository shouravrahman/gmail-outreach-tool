# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create the app directory in user's home and set it as WORKDIR
RUN mkdir -p $HOME/app
WORKDIR $HOME/app

# Copy everything with correct ownership
COPY --chown=user:user . .

# Install dependencies as the user
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Ensure the startup script is executable
RUN chmod +x scripts/run_prod.sh

# Expose the default Hugging Face port 7860
EXPOSE 7860

# Command to run the application
CMD ["./scripts/run_prod.sh"]
