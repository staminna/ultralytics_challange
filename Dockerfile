# Use miniconda3 image for conda support
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Prevent python from writing .pyc files and buffer streams
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy environment file
COPY environment.yml /app/environment.yml

# Create conda environment and install dependencies
RUN conda env create -f environment.yml && \
    conda clean -afy

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "dataset-annotation", "/bin/bash", "-c"]

# Activate environment for subsequent commands
ENV CONDA_DEFAULT_ENV=dataset-annotation
ENV PATH=/opt/conda/envs/dataset-annotation/bin:$PATH

# Copy the application source code into the container
COPY backend/ /app

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["conda", "run", "-n", "dataset-annotation", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
