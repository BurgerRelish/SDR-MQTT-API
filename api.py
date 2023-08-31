from fastapi import FastAPI, Response, status, APIRouter
from authorization import UnitJWT
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, configparser
from supabase_py import Client, create_client

# CORS Origins
origins = [
    "127.0.0.1"
]

app = FastAPI()
supabase: Client
auth: UnitJWT.AuthAPI

"""
API Endpoints

"""
@app.post("/mqtt/auth", response_model=UnitJWT.AuthResponse)
def auth_mqtt(request: UnitJWT.AuthRequest):
    global auth
    return auth.auth_mqtt(request)

@app.get("/command")
def send_command():
    return

@app.get("/sign_up")
def sign_up():
    return

@app.get("/sign_in")
def sign_in():
    return

"""
API Setup

"""
def load_config() -> configparser.ConfigParser:
    return configparser.ConfigParser().read("config.ini")

def main():
    config = load_config()
    global supabase
    supabase = create_client(config["SUPABASE"]["URL"], config["SUPABASE"]["API_KEY"])

    global auth 
    auth = UnitJWT.AuthAPI()

    global app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host=str(config[]), port=api_port)
    return

if (__name__ == "__main__"):
    main()