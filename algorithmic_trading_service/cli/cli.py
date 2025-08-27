import typer
import requests

app = typer.Typer()

@app.command()
def hello():
    response = requests.get("http://127.0.0.1:8000")
    print(response.json())

if __name__ == "__main__":
    app()
