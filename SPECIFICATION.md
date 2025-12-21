# Software Specification: PV Hot Water Control System

## 1. Overview
This document outlines the software specification for a photovoltaic (PV) hot water control system. The system manages two 300V DC circuits powering hot water tanks, ensuring safety, efficiency, and user control. It features a responsive web interface, comprehensive data logging, hardware abstraction for testing, and robust safety mechanisms.

## 2. System Architecture
The system is divided into five main logical components:
1.  **Web Application**: User interface for monitoring and control.
2.  **Measurements & Data Pipeline**: Data acquisition, calibration, and storage.
3.  **Regulation**: Logic for temperature control and day/night cycling.
4.  **GFCI Control**: Interface with the external GFCI breaker box.
5.  **Watchdog**: Continuous safety monitoring.

### A Note on Threading

Backend stuff, web app stuff, and hardware interface stuff are combined.
Thus, it is very important that whatever wsgi server is used only spins up a SINGLE WORKER.
Multiple threads are okay, but this can only handle a single worker.

Future modification might move all hardware stuff to a separate daemon and make the webserver stateless.
For now, it seems that would be an unnecessary level of overcomplication.


## 3. Technology Stack
-   **Language**: Python 3.x
-   **Web Framework**: Flask
-   **Database**: MySQL
-   **Frontend**: HTML5, Bootstrap 5 (for responsiveness), JavaScript (Chart.js or Plotly for graphs).
-   **Suggested Python Libraries**:
    -   `Flask`, `Flask-Login`, `Flask-WTF`: Web app framework and authentication.
    -   `mysql-connector-python` or `SQLAlchemy`: Database interaction.
    -   `APScheduler`: Task scheduling (polling, regulation loops).
    -   `astral` or `suntime`: Sunrise/sunset calculation.
    -   `requests`: HTTP client for GFCI ESP32 communication.
    -   `scipy` or `numpy`: Interpolation for calibration.
    -   `smtplib`: Email notifications.
    -   `RPi.GPIO`, `smbus2`: Hardware I/O (for real drivers).

## 4. Component Specifications

### 4.1. GFCI Control
The External GFCI Panel is controlled via an ESP32 exposing a REST API. The main controller communicates with it over the network.
-   **Functionality**:
    -   Poll status of GFCI breakers.
    -   Reset GFCI breakers.
    -   Configure trip parameters (response speed factor, current thresholds).
    -   Configure network settings (IP address of ESP32).
-   **Implementation**:
    -   A Python class `GFCIManager` handling HTTP requests to the ESP32.
    -   Configuration stored in the database/config file.

### 4.2. Measurements and Data Pipeline
-   **Hardware Abstraction Layer (HAL)**:
    -   **Drivers**: Modular driver system for sensors (Voltage, Current, Temperature) and outputs (Relays, LCD).
    -   **Types**:
        -   *Real Drivers*: Interact with physical GPIO, I2C, SPI.
        -   *Dummy Drivers*: Return static/random values or do nothing (for testing).
    -   **Configuration**: Drivers and their parameters (e.g., GPIO pin, I2C address, dummy value) are selectable via the Web App.
-   **Polling**:
    -   Configurable polling rate (e.g., every 1-60 seconds).
    -   Data stored in MySQL database.
-   **Calibration**:
    -   Raw sensor values are stored.
    -   Calibration table (User Input vs Measured) allows multi-point calibration.
    -   System uses linear interpolation between points to derive "Calibrated Value".
    -   Users can apply calibration retroactively to data subsets (e.g., "Apply current calibration to last 30 days").
-   **Data Storage**:
    -   **Measurements Table**: Timestamp, Raw Values, Calibrated Values, Circuit States.
    -   **Daily Summary Table**: Date, Total kWh, Max Temp, Min Temp, etc.
    -   **Logs Table**: System events, output state changes, errors.
-   **Export**:
    -   CSV export functionality for raw/calibrated data and daily summaries.

### 4.3. Regulation (Temperature & Schedule)
-   **Thermostat Logic**:
    -   Controls relays based on Tank Temperature vs Target Temperature.
    -   Implements **Hysteresis** to prevent rapid switching.
    -   Logic: `If Temp < (Target - Hysteresis): Turn ON`. `If Temp > Target: Turn OFF`.
-   **Day/Night Cycle**:
    -   Calculates Sunrise and Sunset based on user-configured Lat/Long.
    -   **Safety Off**: Circuits disabled $N$ minutes before sunset until $M$ minutes after sunrise.
-   **State Management**:
    -   Ensures decisions are based on trends, not single data points (debouncing).

### 4.4. Web Application
A responsive Flask app using Bootstrap.
-   **Public Dashboard**:
    -   **Graphs**: Line plots of Watts vs Time (24h), Tank Temperatures (24h).
    -   **Key Metrics**: Big display of "kWh produced last 24h", "Current Tank Temps".
    -   **Status**: Visual indicators for Relays (Inside/Outside), Circuit State (On/Off).
-   **Authenticated Area (Login Required)**:
    -   **Manual Control**: Force Relays ON/OFF (overrides regulation temporarily).
    -   **Settings**:
        -   Target Temperatures & Hysteresis.
        -   Location (Lat/Long) & Day/Night offsets.
        -   Polling Rate.
    -   **Calibration**:
        -   Interface to add/remove calibration points.
        -   Graph: Measured vs Actual.
        -   Table of points.
    -   **Driver Configuration**: Select drivers (Real/Dummy) and set parameters.
    -   **GFCI Configuration**: IP setup, threshold tuning, reset button.
    -   **Watchdog Configuration**: Enable/Disable triggers, set thresholds.
    -   **User Management**: Create users, change passwords.
    -   **Logs**: View and search system logs.
    -   **Test Mode**:
        -   Disables automatic regulation.
        -   Allows manual toggling of all hardware.
        -   Custom text input for LCD.
        -   **Note**: Watchdog remains active.

### 4.5. Watchdog
A critical, always-on safety module.
-   **Architecture**:
    -   Modular `WatchdogTrigger` class.
    -   Easy to add new triggers via inheritance.
-   **Triggers**:
    1.  **Over-Current**: Immediate shutoff if current > limit.
    2.  **Over-Temperature**: Shutoff if tank temp > limit.
    3.  **Impedance Mismatch**: Shutoff if $V/I$ deviates from expected load resistance (detects shorts/opens).
    4.  **Leakage/Unexpected Current**: Shutoff if current detected when relays are OFF.
-   **Actions**:
    -   Turn off all circuits.
    -   Log the event.
    -   Send "Panic" notification (Email/Push).

## 5. Database Schema (Proposed)
-   `users`: id, username, password_hash.
-   `measurements`: id, timestamp, v1_raw, i1_raw, t1_raw, v2_raw, ... (calibrated columns).
-   `calibration_points`: id, sensor_id, measured_val, actual_val.
-   `daily_summary`: date, kwh_total, peak_watts, ...
-   `system_logs`: id, timestamp, level, message, category (output_change, watchdog, info).
-   `config`: key-value store for system settings (or use a JSON file).

### A Note on Units

As per how things are actually stored, the following units are used (all values are doubles / floats)

- All temperatures are in `Degrees F`
- All voltages are in `Volts`
- All currents are in `Amperes`
- All power levels are in `Watts`
- All energy levels are in `Watt-Hours`

## 6. Development & Testing
-   **Unit Testing**: `unittest` or `pytest` for logic (regulation, interpolation, watchdog).
-   **Simulation**: Full system run capability using Dummy Drivers without hardware.
