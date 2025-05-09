# class Config:
#     SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://user:password@localhost/hotel_reservation'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     SECRET_KEY = 'your-secret-key'
#     CELERY_BROKER_URL = 'redis://localhost:6379/0'

# class Config:
#     SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root@localhost/hotel_reservation'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     SECRET_KEY = 'your-secret-key'
#     CELERY_BROKER_URL = 'redis://localhost:6379/0'


# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Config:
#     SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://root@localhost/hotel_reservation')
#     SQLALCHEMY_TRACK_MODIFICATIONS = False


import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://root@localhost/hotel_reservation')
    SQLALCHEMY_TRACK_MODIFICATIONS = False