FROM python:3.11.14-slim-bookworm

WORKDIR /app

# System packages: OpenCV runtime, ZBar, GPIO/SPI Python bindings, and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      libgl1 \
      libzbar0 \
      libjpeg62-turbo \
      libatlas3-base \
      libgomp1 \
      python3-spidev \
      build-essential \
      pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY verkort.py ./

EXPOSE 5000

# Run the application
CMD ["python", "verkort.py"]