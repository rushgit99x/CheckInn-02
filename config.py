# class Config:
#     SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://user:password@localhost/hotel_reservation'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     SECRET_KEY = 'your-secret-key'
#     CELERY_BROKER_URL = 'redis://localhost:6379/0'

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root@localhost/hotel_reservation'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'