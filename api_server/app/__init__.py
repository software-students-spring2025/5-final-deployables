import os
from flask import Flask
from pymongo import MongoClient
from app.config import config

mongo_client = None
db = None

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Load config based on environment
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Initialize MongoDB connection
    global mongo_client, db
    mongo_client = MongoClient(app.config['MONGO_URI'])
    db = mongo_client[app.config['MONGO_DBNAME']]
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app