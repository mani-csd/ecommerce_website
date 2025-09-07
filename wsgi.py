from run import create_app
from dotenv import load_dotenv

load_dotenv()  # load environment variables

app = create_app()  # Gunicorn needs a variable named "app"
