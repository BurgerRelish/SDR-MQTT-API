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

@app.post("/mqtt/ingress")
def ingress_mqtt() {
    
}

"""
API Setup

"""
def load_config() -> configparser.ConfigParser:
    return configparser.ConfigParser().read("config.ini")

def main():
    config = load_config()
    global supabase
    # supabase = create_client(config["SUPABASE"]["URL"], config["SUPABASE"]["API_KEY"])
    supabase = create_client("https://iumqawwuvkrdwykxawtp.supabase.co", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1bXFhd3d1dmtyZHd5a3hhd3RwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY5NTI4MTU3MiwiZXhwIjoyMDEwODU3NTcyfQ.9w4BCqAWl2HGBPugGYgGLoKX9-ssZrCBmI3lzcTP5Io")

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

    uvicorn.run(app, host="127.0.0.1", port=3001)
    return

if (__name__ == "__main__"):
    main()