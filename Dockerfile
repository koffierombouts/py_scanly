# Base: Debian slim with Python (works on Raspberry Pi when built on Pi)
FROM python:3.11.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

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

#
# RUNTIME NOTES (Raspberry Pi):
# - Give the container access to the camera and GPIO/SPI devices.
# - The WS281x LED driver typically needs privileged access on Pi.
# Example run (broad but simple):
#   docker run --rm -it \
#     --privileged \
#     --device /dev/video0 \
#     --device /dev/gpiomem \
#     --device /dev/spidev0.0 \
#     --device /dev/spidev0.1 \
#     -v /run/udev:/run/udev:ro \
#     -e MQTT_BROKER=192.168.1.10 \
#     -e MQTT_PORT=1884 \
#     -e MQTT_TOPIC=scanly/couplings \
#     -e MQTT_USER=youruser -e MQTT_PASS=yourpass \
#     -p 5000:5000 \
#     your-image:tag
