#!/bin/bash

# Constants
INSTALL_DIR="/opt/pv-h2o"
SERVICE_NAME="pv-h2o"

# Check for root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Functions
function install_dependencies() {
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3-venv python3-pip whiptail git
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm python python-pip libnewt git
    else
        echo "Unsupported package manager. Please install python3, pip, whiptail (libnewt), and git manually."
        exit 1
    fi
}

function create_venv() {
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
    fi
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv "$INSTALL_DIR/venv"
    fi
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install wheel
}

function install_package() {
    # Install from current directory
    # We assume the script is run from the source directory
    git pull  # Pull the latest code
    SOURCE_DIR=$(pwd)
    "$INSTALL_DIR/venv/bin/pip" install "$SOURCE_DIR"
}

function configure_env() {
    # Generate SECRET_KEY automatically
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Ask questions
    DATABASE_URL=$(whiptail --inputbox "Enter DATABASE_URL (leave empty for sqlite)" 10 60 "" 3>&1 1>&2 2>&3)
    
    DB_FILE_PATH="$INSTALL_DIR/app.db"
    LOG_FILE_PATH="$INSTALL_DIR/app.log"

    # Create .env content
    cat > "$INSTALL_DIR/.env" <<EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=$DATABASE_URL
DB_FILE_PATH=$DB_FILE_PATH
LOG_FILE_PATH=$LOG_FILE_PATH
EOF

    # Allow user to edit
    if (whiptail --title "Review Configuration" --yesno "Do you want to edit the .env file manually?" 10 60); then
        nano "$INSTALL_DIR/.env"
    fi
}

function create_service() {
    cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=PV-H2O Control Service
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 1 --threads 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
}

function uninstall() {
    systemctl stop "$SERVICE_NAME"
    systemctl disable "$SERVICE_NAME"
    rm "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    rm -rf "$INSTALL_DIR"
    echo "Uninstalled successfully."
}

function update() {
    systemctl stop "$SERVICE_NAME"
    install_package
    systemctl start "$SERVICE_NAME"
    echo "Updated successfully."
}

# Check for whiptail and install dependencies if missing
if ! command -v whiptail &> /dev/null; then
    echo "Whiptail not found. Installing dependencies..."
    install_dependencies
fi

# Main logic
ACTION=$(whiptail --menu "Choose an action" 15 60 4 \
"1" "Install" \
"2" "Update" \
"3" "Uninstall" \
"4" "Exit" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        install_dependencies
        create_venv
        install_package
        configure_env
        create_service
        whiptail --msgbox "Installation complete!" 10 60
        ;;
    2)
        update
        whiptail --msgbox "Update complete!" 10 60
        ;;
    3)
        if (whiptail --title "Confirm Uninstall" --yesno "Are you sure you want to uninstall?" 10 60); then
            uninstall
            whiptail --msgbox "Uninstallation complete!" 10 60
        fi
        ;;
    4)
        exit 0
        ;;
esac
