import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException
import configparser

config = configparser.ConfigParser()
config.read("configuration.ini")
JWT_SECRET = config["API"]["jwt_secret"]
JWT_ALGORITHM = config["API"]["jwt_algorithm"]
BROKER_JWT_SECRET = config["EMQX"]["emqx_jwt_secret"]


def encode_jwt(payload: dict[str, any]) -> str:
    """Signs a JWT with the provided payload and secret"""
    
    return jwt.encode(payload=payload, key=JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token
    except Exception as e:
        print(e)
        return {}
    
class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = decode_jwt(jwtoken)
        except:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid
        
        
def encode_broker_jwt(payload: dict[str, any]) -> str:
    """Signs a JWT with the provided payload and secret"""
    
    return jwt.encode(payload=payload, key=BROKER_JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_broker_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, BROKER_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token
    except Exception as e:
        print(e)
        return {}

class BrokerJWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(BrokerJWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(BrokerJWTBearer, self).__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        is_token_valid: bool = False

        try:
            payload = decode_broker_jwt(jwtoken)
        except:
            payload = None
        if payload:
            is_token_valid = True
        return is_token_valid
