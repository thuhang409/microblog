import os


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY')
    SECRET_KEY = b"!\xe9W\xb3\xb1\xf6\xde\xb9^\x8eAE\xdf\xf8\xfb\x0f\xc6H-\xbe\xd6'\x83K"
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db') 
    
    POSTS_PER_PAGE = 3


