from fastapi import FastAPI

app = FastAPI()

def hello_world(name: str):
    return f'Hello, {name}!'

@app.get('/hello/{name}')
def read_root(name: str):
    return {'message': hello_world(name)}