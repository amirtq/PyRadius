# RADIUS Server for OpenVPN

A tiny and easy to use Python Django-based RADIUS server for user management, concurrent session limiting, and account expiration.

## Features

- **User Authentication**: RADIUS Access-Request handling with username/password validation
- **Session Accounting**: RADIUS Accounting-Request handling (Start, Stop, Interim-Update)
- **Traffic Limiting**: Configurable data usage limits per user (e.g. 10GB, 500MB)
- **Concurrent Connection Limiting**: Configurable maximum simultaneous sessions per user
- **Account Expiration**: Support for user account expiration dates
- **NAS Client Management**: Manage multiple NAS clients (OpenVPN servers) with shared secrets
- **Django Admin**: Built-in admin interface for management (future web UI)
- **SQLite Database**: Simple file-based storage, easily upgradeable to PostgreSQL/MySQL

## Requirements

- Python 3.10+
- Django 4.2+
- pyrad 2.4+
- bcrypt 4.0+

## Docker Setup (Recommended)

1. Create the database file and set permissions:
```bash
touch backend/db.sqlite3
chmod 664 backend/db.sqlite3
```

2. Build and start the container:
```bash
docker-compose up -d --build
```
The server will start on ports 1812/1813 (UDP).

3. View logs:
```bash
docker-compose logs -f
```

### Docker Management Commands

You can run any management command using `docker exec`. Here are common examples:

**Add a NAS Client:**
```bash
docker exec -it pyradius python manage.py nasclients add openvpn 192.168.0.1 sharedsecret --description "OpenVPN Server"
```

**Create a User:**
```bash
docker exec -it pyradius python manage.py users create testuser testpassword
```

**List Active Sessions:**
```bash
docker exec -it pyradius python manage.py sessions list --active
```

## Manual Installation

1. Clone the repository and navigate to backend:
```bash
cd /home/xxx/PyRadius/backend
```

2. Create and activate a virtual environment:
```bash
python3 -m venv penv
source penv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python3 manage.py migrate
```

## Quick Start

### 1. Add a NAS Client (OpenVPN Server)

Add your OpenVPN server as a NAS client with its shared secret:

```bash
python3 manage.py nasclients add openvpn 192.168.0.1 sharedsecret --description "OpenVPN Server"
```

### 2. Create a User

Create a user with optional concurrent session limit and expiration:

```bash
# Basic user (1 concurrent session, no expiration)
python3 manage.py users create testuser testpassword

# User with 2 concurrent sessions
python3 manage.py users create user2 pass123 --max-sessions 2

# User with expiration date
python3 manage.py users create user3 pass456 --expires 2025-12-31

# User with both
python3 manage.py users create user4 pass789 --max-sessions 3 --expires 2025-06-30

# User with traffic limit
python3 manage.py users create user5 pass000 --traffic-limit 10g
```

### 3. Start the RADIUS Server

```bash
# Start with default settings (ports 1812/1813)
python3 manage.py start

# Start with custom ports
python3 manage.py start --auth-port 1812 --acct-port 1813

# Start with debug logging
python3 manage.py start --log-level DEBUG
```

**Note**: Ports below 1024 require root privileges.

## Management Commands

### User Management (`users`)

```bash
# Create user
python3 manage.py users create <username> <password> [options]
  --max-sessions, -m   Maximum concurrent sessions (default: 1)
  --expires, -e        Expiration date (YYYY-MM-DD)
  --traffic-limit, -t  Traffic limit (e.g. 5g, 100m)
  --inactive           Create as inactive
  --notes, -n          Notes about the user

# List users
python3 manage.py users list
python3 manage.py users list --active    # Only active users
python3 manage.py users list --expired   # Only expired users

# Show user details
python3 manage.py users show <username>

# Update user
python3 manage.py users update <username> [options]
  --password, -p       New password
  --max-sessions, -m   New max sessions
  --expires, -e        New expiration (or "never")
  --traffic-limit, -t  New traffic limit (or "unlimited")
  --active/--inactive  Change status

# Delete user
python3 manage.py users delete <username>
python3 manage.py users delete <username> --force
```

### NAS Management (`nasclients`)

```bash
# Add NAS
python3 manage.py nasclients add <identifier> <ip> <secret> [options]
  --auth-port          Authentication port (default: 1812)
  --acct-port          Accounting port (default: 1813)
  --description, -d    Description

# List NAS clients
python3 manage.py nasclients list

# Show NAS details
python3 manage.py nasclients show <identifier>

# Update NAS
python3 manage.py nasclients update <identifier> [options]

# Delete NAS
python3 manage.py nasclients delete <identifier>
```

### Session Management (`sessions`)

```bash
# List sessions
python3 manage.py sessions list
python3 manage.py sessions list --active  # Only active
python3 manage.py sessions list --user <username>

# Show session details
python3 manage.py sessions show <session_id>

# Terminate a session
python3 manage.py sessions kick <session_id>

# Cleanup stale sessions
python3 manage.py sessions cleanup --max-age 24
```

## OpenVPN Configuration

### radiusplugin.conf

Configure your OpenVPN RADIUS plugin to connect to this server:

```
NAS-Identifier=nasidentifier
Service-Type=5
Framed-Protocol=1
NAS-Port-Type=5
NAS-IP-Address=192.168.0.1

OpenVPNConfig=/etc/openvpn/server.conf
subnet=255.255.255.0
overwriteccfiles=true
nonfatalaccounting=false

server
{
    acctport=1813
    authport=1812
    name=<RADIUS_SERVER_IP>
    retry=1
    wait=1
    sharedsecret=sharedsecret
}
```

### OpenVPN server.conf

Add the RADIUS plugin to your OpenVPN configuration:

```
plugin /usr/lib/openvpn/radiusplugin.so /etc/openvpn/radiusplugin.conf
```

## Configuration

Server configuration is managed via environment variables or the `.env` file (inside `backend/` directory).

Default configuration in `.env`:

```bash
# RADIUS Configuration
AUTH_PORT=1812
ACCT_PORT=1813
BIND_ADDRESS=0.0.0.0
LOG_LEVEL=DEBUG
ACCT_INTERIM_INTERVAL=60
RADIUS_INACTIVE_SESSION_DB_RETENTION_LIMIT=1000
RADIUS_LOG_RETENTION=1000
```

## Architecture

```
backend/
├── manage.py                 # Django management script
├── config/                   # Django project settings
│   ├── settings.py
│   └── urls.py
├── users/                    # User management app
│   ├── models.py            # RadiusUser model
│   └── management/commands/  # users management command
├── nas/                      # NAS client management
│   ├── models.py            # NASClient model
│   └── management/commands/  # nasclients management command
├── sessions/                 # Session tracking
│   ├── models.py            # RadiusSession model
│   └── management/commands/  # sessions management command
├── radius/                   # RADIUS protocol implementation
│   ├── server.py            # UDP RADIUS server
│   ├── auth_handler.py      # Authentication handler
│   ├── acct_handler.py      # Accounting handler
│   ├── dictionary.txt       # RADIUS attribute dictionary
│   └── management/commands/ # start command
└── db.sqlite3               # SQLite database
```

## Authentication Flow

1. OpenVPN client connects with username/password
2. OpenVPN sends Access-Request to RADIUS server (port 1812)
3. RADIUS server:
   - Verifies NAS client (by IP and shared secret)
   - Looks up user in database
   - Validates password
   - Checks if account is active and not expired
   - Checks concurrent session limit
4. Returns Access-Accept or Access-Reject
5. On connection success, OpenVPN sends Accounting-Start (port 1813)
6. RADIUS server creates session record
7. On disconnect, OpenVPN sends Accounting-Stop
8. RADIUS server marks session as stopped

## Testing

Test RADIUS authentication using `radtest` (from freeradius-utils):

```bash
# Install radtest
apt install freeradius-utils

# Test authentication
radtest testuser testpassword localhost 0 amir1234
```

## Troubleshooting

### Permission Denied on Ports 1812/1813

Use elevated privileges or ports > 1024:

```bash
sudo python manage.py start
# or
python3 manage.py start --auth-port 18120 --acct-port 18130
```

### View Debug Logs

```bash
python3 manage.py start --log-level DEBUG
```

### Check Active Sessions

```bash
python3 manage.py sessions list --active
```

## License

AGPLv3
