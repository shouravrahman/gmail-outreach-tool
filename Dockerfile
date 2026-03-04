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

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy the requirements file into the container
# Use --chown=user:user to ensure the user has ownership
COPY --chown=user:user requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application code into the container
COPY --chown=user:user . .

# Make the startup script executable
RUN chmod +x scripts/run_prod.sh

# Expose the port Streamlit will run on
EXPOSE 8501

# Command to run the application
CMD ["./scripts/run_prod.sh"]
