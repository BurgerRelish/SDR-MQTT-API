from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import uvicorn
import configparser
import os

app = FastAPI()

supabase_api_key: str
supabase_url: str
supabase: Client

origins = [
    "http://localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    supabase_api_key = config['SUPABASE']['API_KEY']
    supabase_url = config['SUPABASE']['URL']

    return [supabase_url, supabase_api_key]

def get_rows_by_id(table_name, id):
    try:
        response = supabase.table(table_name).select("*").eq('id', id).execute()
    except:
        return None
    
    return response.data if (response.data) else None
    
class AuthBody(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    result: str
    is_superuser: bool

#Authentication method for EMQX HTTP Auth API. Queries the Supabase server for any entries matching the username and checks if 
@app.post('/auth')
async def auth_mqtt(auth_request: AuthBody, response: Response):
    username = auth_request.username
    password = auth_request.password
    
    client_params =  get_rows_by_id('sdr_units', username)
    response.status_code = status.HTTP_403_FORBIDDEN

    if (client_params):
        row = client_params[0]
        if (password == row['mqtt_password']):
            response.status_code = status.HTTP_200_OK
            return AuthResponse(result="allow", is_superuser=row['is_superuser'])
    
    return AuthResponse(result="deny", is_superuser=False)

if __name__ == "__main__": # Start uvicorn with the python file.
    config = load_config()
    supabase = create_client(config[0], config[1])
    uvicorn.run(app, host="0.0.0.0", port=8000)
