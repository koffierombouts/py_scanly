# py_scanly

This project runs locally on a Raspberry py with a Pi camera and an RFID scanner. With this studentnumbers can be easily read and bound to their card RFID identifier. This data is then sent through MQTT to the operator needing this data.

## Setting up py_scanly

1. Add a `.env` file to the root of this project.
2. Enter your MQTT variables. Base yourself on the `env_example` file.
3. Run 