from flask import Flask, redirect, session
from dash import Dash, html
import dash_bootstrap_components as dbc
import os

# Initialize Flask server
server = Flask(__name__)
# Set secret key for session management
server.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')  

# Define constant for login route
LOGIN_PATH = '/login'  

# Initialize Dash apps for login and dashboard with Bootstrap styling
login_app = Dash(__name__, server=server, url_base_pathname=LOGIN_PATH + '/', 
                 external_stylesheets=[dbc.themes.BOOTSTRAP])
dashboard_app = Dash(__name__, server=server, url_base_pathname='/dashboard/', 
                     external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Import and setup app configurations from separate modules
from login_app import setup_login_app
from dashboard_app import setup_dashboard_app

# Configure login app
setup_login_app(login_app)
# Configure dashboard app
setup_dashboard_app(dashboard_app)

# Route handler for root URL
@server.route('/')
def home():
    # Redirects users to the login page
    return redirect(LOGIN_PATH)

# Route handler for login page
@server.route(LOGIN_PATH)
def login():
    # Serves the login page
    return login_app.index()

# Route handler for dashboard main page
@server.route('/dashboard')
def dashboard():
    # Serves dashboard if logged in, else redirects to login
    if not session.get('logged_in'):
        return redirect(LOGIN_PATH)
    return dashboard_app.index()

# Route handler for dashboard sub-paths
@server.route('/dashboard/<path:path>')
def serve_dashboard(path):
    # Serves dashboard content for sub-paths if logged in
    if not session.get('logged_in'):
        return redirect(LOGIN_PATH)
    return dashboard_app.index()

# Main entry point for running the application
if __name__ == '__main__':
    # Runs the Flask server in debug mode
    server.run(debug=True)