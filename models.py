# File: models.py
from extensions import db
from datetime import datetime

# 1. Bảng User (Người dùng)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Khóa chính
    username = db.Column(db.String(50), unique=True, nullable=False) # Tên đăng nhập (không trùng)
    email = db.Column(db.String(120), unique=True, nullable=False)   # Email
    password_hash = db.Column(db.String(128), nullable=False)        # Mật khẩu đã mã hóa
    created_at = db.Column(db.DateTime, default=datetime.utcnow)     # Ngày tạo tài khoản
    
    # Quan hệ: Một User có nhiều Food (User 1 - N Food)
    # lazy=True giúp tải dữ liệu thực phẩm khi cần thiết
    foods = db.relationship('Food', backref='owner', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# 2. Bảng Food (Thực phẩm trong tủ lạnh)
class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)     # Tên thực phẩm
    quantity = db.Column(db.Float, nullable=False)       # Số lượng
    unit = db.Column(db.String(20), nullable=False)      # Đơn vị (kg, quả, hộp...)
    expiration_date = db.Column(db.Date, nullable=False) # Ngày hết hạn
    storage_location = db.Column(db.String(50), default='Ngăn mát') # Vị trí
    added_at = db.Column(db.DateTime, default=datetime.utcnow)      # Ngày thêm vào
    
    # Khóa ngoại: Liên kết với bảng User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Food('{self.name}', '{self.expiration_date}')"

# 3. Bảng Recipe (Công thức nấu ăn - Dành cho tính năng gợi ý)
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Tên món ăn
    instructions = db.Column(db.Text, nullable=False) # Hướng dẫn nấu (Text dài)
    image_url = db.Column(db.String(200))             # Link ảnh món ăn (nếu có)
    
    # Lưu danh sách nguyên liệu dưới dạng chuỗi văn bản đơn giản để dễ xử lý cho Project I
    # Ví dụ: "Thịt gà, Nấm hương, Hành tây"
    ingredients_list = db.Column(db.Text, nullable=False) 

    def __repr__(self):
        return f"Recipe('{self.name}')"