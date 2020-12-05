import hashlib

URL = "http://demo.ispfy.com.br:8020/api"
ROTA_LOGIN = "/tool/assinante/login"
HEADERS = {"Content-Type":"application/json", "token": "a1422223fa2aa1cb9d9462f8e463fb06"}

def password_md5(password):
    if password:
        p = hashlib.md5(password.encode()).hexdigest()
        return(p)
    return 


def validation_user(user=str):
    user = user.strip().lower() 
    return str(user)
