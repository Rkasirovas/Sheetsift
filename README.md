# Final Project: SheetSift

SheetSift is a web application built with Python (Flask), designed to allow users to upload, process, and manage spreadsheet files with user authentication and admin features. It leverages a modular architecture and uses SQLAlchemy for database management.

![Main Index Page](index.png)

## Features

- **User Authentication:** Secure login system with Flask-Login and bcrypt password hashing.
- **Admin Interface:** Admin panel powered by Flask-Admin for managing users.
- **File Uploads:** Upload and process spreadsheet files (e.g., XLSX, CSV).
- **Custom Filtering:** Extendable filtering logic for uploaded data (see `sheetsift/filters/`).
- **Database Support:** Uses SQLite by default, easy to swap for other databases via SQLAlchemy.
- **Error Handling:** Custom 404 error page.
- **Modular Codebase:** Clean separation of main routes, authentication, models, filters, static files, and templates.

## Project Structure

```
run.py                        # Entry point to start the Flask app
sheetsift/
  __init__.py                 # App factory and Flask extension initialization
  models.py                   # Database models (User, etc.)
  routes.py                   # Main application routes
  auth.py                     # Authentication-related routes
  filters/                    # Custom filtering logic for spreadsheets
  static/                     # Static files (CSS, JS, images)
  templates/                  # HTML templates
```

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rkasirovas/Final.git
   cd Final
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

5. **Access the app:**  
   Open [http://localhost:5000](http://localhost:5000) in your browser.

## Configuration

All major configuration options (upload folders, DB URI, etc.) are set in `run.py` using the `config` dictionary and passed into the app factory.

- `UPLOAD_FOLDER`: Path for uploaded files
- `RESULT_FOLDER`: Path where processed results are stored
- `SQLALCHEMY_DATABASE_URI`: SQLite database location

## Usage

1. Register or log in to your account.
2. Upload spreadsheet files through the web UI.
3. Admins can manage users via the admin interface at `/montywizardpython`.

## Folder Descriptions

- **sheetsift/filters/**: Place your custom spreadsheet filters here.
- **sheetsift/static/**: Static files (CSS, JS, images) for the frontend.
- **sheetsift/templates/**: All HTML templates (including `404.html`).

## Development

- The app runs in debug mode by default.
- Extend models or add filters by editing files in `sheetsift/`.

*This project was created as a final assignment by [Rkasirovas](https://github.com/Rkasirovas).*
