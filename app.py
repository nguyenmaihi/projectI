
from flask import Flask, render_template, url_for, flash, redirect, request, session
from extensions import db, bcrypt  # <-- Import từ file extensions
from models import User, Food # <-- Import Model User (bây giờ đã an toàn)
from datetime import datetime
app = Flask(__name__)

# --- Cấu hình ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'chuoi-bi-mat-cua-ban' 

# --- Gắn db và bcrypt vào app ---
db.init_app(app)
bcrypt.init_app(app)

# -----------------------------------------------------------
# CÁC ROUTES (Định tuyến)
# -----------------------------------------------------------

# 1. TRANG CHỦ
@app.route('/')
def home():
    if 'user_id' in session:
        name = session.get('username')
        # Thêm cái link dẫn đến /add_food
        return f"""
        <h1>Xin chào, {name}!</h1>
        <p>Đây là tủ lạnh của bạn.</p>
        <a href='/add_food' style='font-size: 20px; font-weight: bold;'>[+] Thêm thực phẩm mới</a>
        <br><br>
        <a href='/logout'>Đăng xuất</a>
        """
    return "<h1>Hệ thống Tủ lạnh thông minh</h1> <p><a href='/login'>Đăng nhập</a> hoặc <a href='/register'>Đăng ký</a></p>"
# 2. ĐĂNG KÝ
@app.route("/register", methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Kiểm tra tồn tại
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Tên đăng nhập hoặc Email đã tồn tại!', 'danger')
            return redirect(url_for('register'))

        # Tạo user mới
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('Lỗi không xác định.', 'danger')

    return render_template('auth/register.html', title='Đăng ký')

# 3. ĐĂNG NHẬP
@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Sai thông tin đăng nhập.', 'danger')

    return render_template('auth/login.html', title='Đăng nhập')

# 4. ĐĂNG XUẤT
@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Đã đăng xuất.', 'info')
    return redirect(url_for('login'))
# -----------------------------------------------------------
# CÁC ROUTES QUẢN LÝ THỰC PHẨM (CRUD)
# -----------------------------------------------------------

# 1. THÊM THỰC PHẨM MỚI
@app.route("/add_food", methods=['GET', 'POST'])
def add_food():
    # Kiểm tra đăng nhập (Bắt buộc)
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để thêm thực phẩm.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 1. Lấy dữ liệu từ form
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        unit = request.form.get('unit')
        location = request.form.get('location')
        date_str = request.form.get('expiration_date') # Dạng chuỗi 'YYYY-MM-DD'
        
        # 2. Xử lý dữ liệu (Chuyển chuỗi ngày thành đối tượng Python Date)
        # HTML trả về '2025-11-20', ta cần chuyển nó để lưu vào DB
        expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 3. Tạo đối tượng Food mới
        new_food = Food(
            name=name,
            quantity=float(quantity), # Chuyển sang số thực
            unit=unit,
            location=location,
            expiration_date=expiration_date,
            user_id=session['user_id'] # Gán cho người dùng hiện tại
        )
        
        # 4. Lưu vào CSDL
        try:
            db.session.add(new_food)
            db.session.commit()
            flash(f'Đã thêm "{name}" vào tủ lạnh!', 'success')
            return redirect(url_for('home')) # Quay về trang chủ để xem danh sách
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm thực phẩm: {e}', 'danger')

    # Hiển thị form thêm
    return render_template('food/add_food.html', title='Thêm thực phẩm')

# --- Chạy App ---
if __name__ == '__main__':
    # Tạo bảng CSDL tự động nếu chưa có (chạy 1 lần đầu)
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)