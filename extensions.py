# File: extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Khởi tạo các đối tượng nhưng chưa gắn vào app ngay
db = SQLAlchemy()
bcrypt = Bcrypt()