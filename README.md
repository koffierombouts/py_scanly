# py_scanly

This project runs locally on a Raspberry py with a Pi camera and an RFID scanner. With this studentnumbers can be easily read and bound to their card RFID identifier. This data is then sent through MQTT to the operator needing this data.

## Setting up py_scanly

This version runs the application inside a container for easy deployment. Setting this project up is made easy by the usage of docker.

1. Add a `.env` file to the root of this project.
2. Enter your MQTT variables inside the `.env` file.

```
MQTT_BROKER="mqtt_broker_domain"
MQTT_PORT="mqtt_broker_port"
MQTT_TOPIC="mqqt_topic"
MQTT_USER="mqtt_user"
MQTT_PASS="mqtt_password"
```

3. Build the image with `docker compose build`.
4. Run it on your Raspberry Pi with `docker compose up -d`
