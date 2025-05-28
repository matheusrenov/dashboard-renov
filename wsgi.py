from app import server
from flask import Flask
from typing import cast

if __name__ == "__main__":
    flask_server = cast(Flask, server)
    flask_server.run() 