from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from flask import session

# Constant for error styling
RED_BORDER = "1px solid red"

# Configures the login Dash app
def setup_login_app(app):
    # Define the layout for the login page
    app.layout = html.Div(
        style={"display": "flex", "justifyContent": "center", "alignItems": "center", 
               "height": "100vh", "backgroundColor": "#f8f9fa"},
        children=[
            # Component for page redirection
            dcc.Location(id='redirect', refresh=True),
            dbc.Card(
                [
                    dbc.CardHeader(html.H3("Login", className="text-center")),
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    dbc.Label("Username", html_for="username", className="form-label"),
                                    dbc.Input(
                                        id="username",
                                        type="text",
                                        placeholder="Enter your username",
                                        style={"marginBottom": "10px"}
                                    ),
                                    html.Div(id="username-error", style={"color": "red", "marginBottom": "10px"})
                                ]
                            ),
                            html.Div(
                                [
                                    dbc.Label("Password", html_for="password", className="form-label"),
                                    dbc.Input(
                                        id="password",
                                        type="password",
                                        placeholder="Enter your password",
                                        style={"marginBottom": "10px"}
                                    ),
                                    html.Div(id="password-error", style={"color": "red", "marginBottom": "10px"})
                                ]
                            ),
                            html.Div(
                                dbc.Button(
                                    "Login",
                                    id="login-button",
                                    color="primary",
                                    className="w-50",
                                    disabled=True, 
                                    style={"backgroundColor": "#c0c0c0", "borderColor": "#c0c0c0"} 
                                ),
                                className="text-center",
                                style={"marginTop": "30px"}
                            ),
                        ]
                    ),
                ],
                style={"width": "400px", "padding": "20px"},
            )
        ]
    )

    # Callback to enable/disable login button based on input
    @app.callback(
        Output("login-button", "disabled"),
        Output("login-button", "style"),
        [Input("username", "value"), Input("password", "value")]
    )
    def toggle_login_button(username, password):
        # Enable button if both fields are filled
        if username and password:
            return False, {"backgroundColor": "#007bff", "borderColor": "#007bff", "color": "white"}  
        # Disable button if either field is empty
        return True, {"backgroundColor": "#c0c0c0", "borderColor": "#c0c0c0", "color": "white"}  

    # Callback to authenticate user and handle login
    @app.callback(
        [Output("username", "style"), Output("password", "style"),
         Output("username-error", "children"), Output("password-error", "children"),
         Output("redirect", "pathname")],
        Input("login-button", "n_clicks"),
        [State("username", "value"), State("password", "value")],
        prevent_initial_call=True,
    )
    def authenticate_user(n_clicks, username, password):
        # Initialize styles and error messages
        username_style = {"marginBottom": "10px"}
        password_style = {"marginBottom": "10px"}
        username_error = ""
        password_error = ""
        redirect = None

        # Check username validity
        if username != "Rohith":
            username_style.update({"border": RED_BORDER})
            username_error = "Invalid username."
        # Check password validity if username is correct
        elif password != "password123":
            password_style.update({"border": RED_BORDER})
            password_error = "Invalid password."
        # Set session and redirect on successful login
        else:
            session['logged_in'] = True
            redirect = '/dashboard'

        # Return updated styles, errors, and redirect path
        return username_style, password_style, username_error, password_error, redirect