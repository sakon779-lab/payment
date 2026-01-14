

from fastapi import FastAPI
app = FastAPI()


from src.utils.string_ops import reverse_string

@app.get('/reverse/{text}')
def reverse(text: str):
    reversed_text = reverse_string(text)
    return {'original': text, 'reversed': reversed_text}
