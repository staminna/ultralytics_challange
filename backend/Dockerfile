# Use an official Conda base image
FROM continuumio/miniconda3:latest

# Set the working directory
WORKDIR /app

# Prevent python from writing .pyc files and buffer streams
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the environment file and create the Conda environment
COPY ../environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml

# Make Conda available in the shell
SHELL ["conda", "run", "-n", "ultralytics-annotation", "/bin/bash", "-c"]

# Copy the application source code into the container
COPY . /app

# Expose the port the app will run on
EXPOSE 8000

# The command to run when the container starts
# This will run the application within the 'ultralytics-annotation' Conda environment
CMD ["conda", "run", "-n", "ultralytics-annotation", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
