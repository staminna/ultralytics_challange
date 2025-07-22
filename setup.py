from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="yolo-annotation-service",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A FastAPI-based service for managing YOLO format datasets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/yolo-annotation-service",
    packages=find_packages(exclude=["tests"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0,<0.104.0",
        "uvicorn>=0.15.0,<0.24.0",
        "python-multipart>=0.0.5,<0.0.7",
        "python-dotenv>=0.19.0,<2.0.0",
        "firebase-admin>=6.2.0,<7.0.0",
        "google-cloud-storage>=2.0.0,<3.0.0",
        "google-cloud-firestore>=2.0.0,<3.0.0",
        "pydantic>=1.8.0,<2.0.0",
        "requests>=2.25.0,<3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0",
            "isort>=5.0.0",
            "flake8>=3.9.0",
            "mypy>=0.900",
        ],
    },
)
