from fastapi import FastAPI
from src.utils.string_ops import hello_world

app = FastAPI()

@app.get('/hello/{name}')
def read_root(name: str):
    return {'message': hello_world(name)}