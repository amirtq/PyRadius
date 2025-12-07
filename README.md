# RADIUS Server for OpenVPN

A tiny, easy-to-use, and feature-rich Python Django-based RADIUS server for user management, concurrent session limiting, and traffic accounting. Includes a modern React-based Web UI and REST API.

## Features

- **Modern Web Dashboard**: Comprehensive React-based UI for managing users, NAS clients, sessions, and viewing logs.
- **REST API**: Full-featured JSON API with JWT authentication for programmatic access.
- **User Authentication**: RADIUS Access-Request handling with username/password validation.
- **Session Accounting**: RADIUS Accounting-Request handling (Start, Stop, Interim-Update).
- **Traffic Limiting**: Configurable data usage limits per user (e.g. 10GB, 500MB).
- **Concurrent Connection Limiting**: Configurable maximum simultaneous sessions per user.
- **Account Expiration**: Support for user account expiration dates.
- **NAS Client Management**: Manage multiple NAS clients (OpenVPN servers) with shared secrets.
- **Real-time Logging**: View RADIUS server logs in real-time via Web UI or CLI.
- **SQLite Database**: Simple file-based storage, easily upgradeable to PostgreSQL/MySQL.

## Requirements

- Python 3.12+
- Django 6.0+
- pyrad 2.4+
- bcrypt 4.0+
- djangorestframework
- djangorestframework-simplejwt
- django-cors-headers
- django-filter
- python-dotenv
- (Optional) Node.js 22+ for frontend development

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
- **Web Dashboard**: http://server_ip (port 80)
- **RADIUS Auth Port**: 1812/udp
- **RADIUS Acct Port**: 1813/udp

3. Create an Administrator (required for Web UI):
```bash
docker exec -it pyradius python manage.py users add --admin-user admin password123
```

4. View logs:
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
docker exec -it pyradius python manage.py users add --radius-user testuser testpassword
```

**List Active Sessions:**
```bash
docker exec -it pyradius python manage.py sessions list --active
```

**View RADIUS Logs:**
```bash
docker exec -it pyradius python manage.py logs -n 100
```

## Manual Installation

1. Clone the repository and navigate to backend:
```bash
cd /path/to/PyRadius/backend
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

5. Create an Administrator (required for Web UI):
```bash
python3 manage.py users add --admin-user admin password123
```

> **Note**: The frontend is pre-built in `backend/frontend_dist`. If you want to modify the frontend, you'll need to build it using `cd frontend && npm install && npm run build` and ensure the output is in `backend/frontend_dist`.

## Quick Start (Manual)

### 1. Start the RADIUS Server

```bash
# Start with default settings (Web on 8000, RADIUS on 1812/1813)
python3 manage.py start &
python3 manage.py runserver 0.0.0.0:8000
```
Visit **http://server_ip:8000** to login with your admin credentials.

### 2. Add a NAS Client (OpenVPN Server)

Add your OpenVPN server as a NAS client with its shared secret:

```bash
python3 manage.py nasclients add openvpn 192.168.0.1 sharedsecret --description "OpenVPN Server"
```

### 3. Create a User

Create a user with optional concurrent session limit and expiration:

```bash
# Basic RADIUS user (1 concurrent session, no expiration)
python3 manage.py users add --radius-user testuser testpassword

# User with 2 concurrent sessions
python3 manage.py users add --radius-user user2 pass123 --max-sessions 2

# User with expiration date
python3 manage.py users add --radius-user user3 pass456 --expires 2025-12-31

# User with both
python3 manage.py users add --radius-user user4 pass789 --max-sessions 3 --expires 2025-06-30

# User with traffic limit
python3 manage.py users add --radius-user user5 pass000 --traffic-limit 10g

# User with cleartext password (stored as ctp:password)
python3 manage.py users add --radius-user user6 pass123 -ctp

# User created as inactive
python3 manage.py users add --radius-user user7 pass123 --inactive
```

## Web Dashboard

The Web Dashboard provides a modern interface for managing all aspects of the RADIUS server:

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Overview with statistics |
| Users | `/users` | Manage RADIUS and Admin users |
| NAS Clients | `/nas` | Manage NAS/OpenVPN servers |
| Sessions | `/sessions` | View and manage active sessions |
| Logs | `/logs` | Real-time RADIUS server logs |
| Login | `/login` | Authentication page |

### Authentication

The Web UI uses JWT (JSON Web Token) authentication. Login with your Admin user credentials to access the dashboard.

## REST API

The API uses JWT authentication. First obtain a token, then include it in subsequent requests.

### Authentication Endpoints

```bash
# Obtain JWT tokens
POST /api/token/
{
  "username": "admin",
  "password": "password123"
}
# Returns: { "access": "...", "refresh": "..." }

# Refresh access token
POST /api/token/refresh/
{
  "refresh": "refresh_token_here"
}
# Returns: { "access": "..." }
```

### API Endpoints

All endpoints require `Authorization: Bearer <access_token>` header.

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/radius-users/` | GET, POST | List/Create RADIUS users |
| `/api/radius-users/{id}/` | GET, PUT, PATCH, DELETE | Retrieve/Update/Delete RADIUS user |
| `/api/admins/` | GET, POST | List/Create Admin users |
| `/api/admins/{id}/` | GET, PUT, PATCH, DELETE | Retrieve/Update/Delete Admin user |
| `/api/nas/` | GET, POST | List/Create NAS clients |
| `/api/nas/{id}/` | GET, PUT, PATCH, DELETE | Retrieve/Update/Delete NAS client |
| `/api/sessions/` | GET | List sessions |
| `/api/sessions/{id}/` | GET, DELETE | Retrieve/Terminate session |
| `/api/logs/` | GET | List RADIUS logs |

### Example API Usage

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' | jq -r '.access')

# List RADIUS users
curl -s http://localhost:8000/api/radius-users/ \
  -H "Authorization: Bearer $TOKEN"

# Create a RADIUS user
curl -s -X POST http://localhost:8000/api/radius-users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"pass123","max_concurrent_sessions":2}'

# List active sessions
curl -s "http://localhost:8000/api/sessions/?status=active" \
  -H "Authorization: Bearer $TOKEN"

# View logs
curl -s http://localhost:8000/api/logs/ \
  -H "Authorization: Bearer $TOKEN"
```

## Management Commands

The Web UI is the easiest way to manage users and settings, but the CLI is fully supported.

### User Management (`users`)

**General Usage:**
```bash
python3 manage.py users <action> [options]

# Global flags:
python3 manage.py users --flushusers  # Clear all RADIUS users
```

**Create User:**
```bash
# Add a RADIUS User
python3 manage.py users add --radius-user <username> <password> [options]
  --clear-text-password, -ctp  Store password in clear text
  --max-sessions, -m           Maximum concurrent sessions (default: 1)
  --expires, -e                Expiration date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
  --traffic-limit, -t          Traffic limit (e.g. 5g, 100m)
  --inactive                   Create as inactive
  --notes, -n                  Notes about the user

# Add an Admin User (for Web Dashboard)
python3 manage.py users add --admin-user <username> <password>
```

**List Users:**
```bash
# List all users (both RADIUS and Admin)
python3 manage.py users list

# List specific user types
python3 manage.py users list --radius-user
python3 manage.py users list --admin-user

# Filter lists
python3 manage.py users list --active    # Only active users
python3 manage.py users list --expired   # Only expired users (RADIUS only)
python3 manage.py users list --inactive  # Only inactive users
```

**Update User:**
```bash
# Update a RADIUS User
python3 manage.py users update --radius-user <username> [options]
  --password, -p       New password
  --clear-text-password, -ctp  Store password in clear text
  --max-sessions, -m   New max sessions
  --expires, -e        New expiration (or "never")
  --traffic-limit, -t  New traffic limit (or "unlimited")
  --active/--inactive  Change status
  --notes, -n          Update notes

# Update an Admin User
python3 manage.py users update --admin-user <username> [options]
  --password, -p       New password
  --active/--inactive  Change status
```

**Delete User:**
```bash
# Delete a RADIUS User
python3 manage.py users delete <username>
python3 manage.py users delete <username> --force
```

**Show User Details:**
```bash
# Show RADIUS User details
python3 manage.py users show <username>
```

### NAS Management (`nasclients`)

```bash
# Global flags:
python3 manage.py nasclients --flushnas  # Clear all NAS clients

# Add NAS
python3 manage.py nasclients add <identifier> <ip> <secret> [options]
  --auth-port          Authentication port (default: 1812)
  --acct-port          Accounting port (default: 1813)
  --description, -d    Description
  --inactive           Create as inactive

# List NAS clients
python3 manage.py nasclients list
python3 manage.py nasclients list --active  # Only active NAS clients

# Show NAS details
python3 manage.py nasclients show <identifier>

# Update NAS
python3 manage.py nasclients update <identifier> [options]
  --ip                 New IP address
  --secret             New shared secret
  --auth-port          New authentication port
  --acct-port          New accounting port
  --description, -d    New description
  --active/--inactive  Change status

# Delete NAS
python3 manage.py nasclients delete <identifier>
python3 manage.py nasclients delete <identifier> --force
```

### Session Management (`sessions`)

```bash
# Global flags:
python3 manage.py sessions --flushsessions  # Clear all sessions and reset counters

# List sessions
python3 manage.py sessions list
python3 manage.py sessions list --active           # Only active sessions
python3 manage.py sessions list --stopped          # Only stopped sessions
python3 manage.py sessions list --user <username>  # Filter by user
python3 manage.py sessions list --nas <identifier> # Filter by NAS
python3 manage.py sessions list --limit 100        # Limit results (default: 50)

# Show session details
python3 manage.py sessions show <session_id>

# Terminate a session
python3 manage.py sessions kick <session_id>
python3 manage.py sessions kick <session_id> --force

# Cleanup stale sessions
python3 manage.py sessions cleanup --max-age 24    # Sessions older than 24 hours
python3 manage.py sessions cleanup --dry-run       # Preview without deleting
```

### RADIUS Server (`start`)

```bash
python3 manage.py start [options]
  --auth-port          Authentication port (default: from settings or 1812)
  --acct-port          Accounting port (default: from settings or 1813)
  --bind               Bind address (default: from settings or 0.0.0.0)
  --log-level          Logging level: DEBUG, INFO, WARNING, ERROR
```

### Log Management (`logs`)

```bash
# View recent logs (default: 50 lines)
python3 manage.py logs

# View specific number of lines
python3 manage.py logs -n 100

# Filter logs by string (case-insensitive)
python3 manage.py logs -f "authentication"
python3 manage.py logs -f "error"

# Clear all logs
python3 manage.py logs --flushlogs
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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (insecure default) | Django secret key - **change in production** |
| `DEBUG` | `False` | Enable debug mode |
| `AUTH_PORT` | `1812` | RADIUS authentication port |
| `ACCT_PORT` | `1813` | RADIUS accounting port |
| `BIND_ADDRESS` | `0.0.0.0` | Server bind address |
| `LOG_LEVEL` | `DEBUG` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ACCT_INTERIM_INTERVAL` | `600` | Accounting interim interval in seconds |
| `RADIUS_INACTIVE_SESSION_DB_RETENTION_LIMIT` | `100` | Max inactive sessions to retain |
| `RADIUS_LOG_RETENTION` | `1000` | Max log entries to retain |
| `RADIUS_STALE_SESSION_MULTIPLIER` | `5` | Multiplier for detecting dead sessions |

### Example `.env` file

```bash
# Django Settings
SECRET_KEY=your-secure-secret-key-here
DEBUG=False

# RADIUS Configuration
AUTH_PORT=1812
ACCT_PORT=1813
BIND_ADDRESS=0.0.0.0
LOG_LEVEL=INFO
ACCT_INTERIM_INTERVAL=600
RADIUS_INACTIVE_SESSION_DB_RETENTION_LIMIT=1000
RADIUS_LOG_RETENTION=1000
RADIUS_STALE_SESSION_MULTIPLIER=5
```

## Architecture

```
.
├── backend/                  # Django Backend
│   ├── config/               # Django project configuration
│   │   ├── settings.py       # Settings with RADIUS_CONFIG
│   │   ├── urls.py           # API routes and frontend catch-all
│   │   └── pagination.py     # API pagination config
│   ├── users/                # User management app
│   │   ├── models.py         # RadiusUser and AdminUser models
│   │   ├── views.py          # REST API views
│   │   ├── serializers.py    # DRF serializers
│   │   └── management/       # CLI commands
│   ├── nas/                  # NAS client management app
│   │   ├── models.py         # NASClient model
│   │   ├── views.py          # REST API views
│   │   └── management/       # CLI commands
│   ├── sessions/             # Session tracking app
│   │   ├── models.py         # RadiusSession model
│   │   ├── views.py          # REST API views
│   │   └── management/       # CLI commands
│   ├── radius/               # RADIUS protocol implementation
│   │   ├── server.py         # RADIUS server (pyrad)
│   │   ├── auth_handler.py   # Authentication handler
│   │   ├── acct_handler.py   # Accounting handler
│   │   ├── models.py         # RadiusLog model
│   │   ├── logging_handler.py # Database logging handler
│   │   └── management/       # CLI commands (start, logs)
│   ├── frontend_dist/        # Compiled Frontend assets (served by Django)
│   ├── manage.py             # Django management script
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Environment configuration
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── api/              # API client with JWT handling
│   │   ├── pages/            # Dashboard, Users, NAS, Sessions, Logs, Login
│   │   ├── components/       # Layout, Modal components
│   │   └── App.jsx           # Router configuration
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Build configuration
├── docker-compose.yml        # Docker orchestration
├── Dockerfile                # Multi-stage Docker build
└── entrypoint.sh             # Container startup script
```

## Authentication Flow

1. OpenVPN client connects with username/password
2. OpenVPN sends Access-Request to RADIUS server (port 1812)
3. RADIUS server:
   - Verifies NAS client (by IP and shared secret)
   - Looks up user in database
   - Validates password (bcrypt or cleartext)
   - Checks if account is active and not expired
   - Checks traffic limit
   - Checks concurrent session limit
4. Returns Access-Accept or Access-Reject
5. On connection success, OpenVPN sends Accounting-Start (port 1813)
6. RADIUS server creates session record
7. Periodic Interim-Update packets update traffic statistics
8. On disconnect, OpenVPN sends Accounting-Stop
9. RADIUS server marks session as stopped and updates user traffic totals

## Testing

Test RADIUS authentication using `radtest` (from freeradius-utils):

```bash
# Install radtest
apt install freeradius-utils

# Test authentication
radtest testuser testpassword localhost 0 sharedsecret
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
# Via CLI
python3 manage.py start --log-level DEBUG

# View stored logs
python3 manage.py logs -n 100

# Filter for errors
python3 manage.py logs -f "error"
```

### Check Active Sessions

```bash
python3 manage.py sessions list --active
```

### Reset All Sessions (if stuck)

```bash
python3 manage.py sessions --flushsessions
```

### Reset All Data

```bash
# Clear users
python3 manage.py users --flushusers

# Clear NAS clients
python3 manage.py nasclients --flushnas

# Clear sessions
python3 manage.py sessions --flushsessions

# Clear logs
python3 manage.py logs --flushlogs
```

## License

AGPLv3
