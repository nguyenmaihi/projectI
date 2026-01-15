
from flask import Flask, render_template, url_for, flash, redirect, request, session
from extensions import db, bcrypt  # <-- Import từ file extensions
from models import User, Food, Recipe # <-- Import Model User (bây giờ đã an toàn)
from datetime import datetime, date
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
    # 1. Kiểm tra đăng nhập
    if 'user_id' not in session:
        return render_template('auth/login.html') # Hoặc trang giới thiệu nếu có
    
    # 2. Lấy thông tin user
    # (Tùy chọn: Lấy tên để hiển thị xin chào)
    
    # 3. Lấy danh sách thực phẩm của người dùng đó
    # Sắp xếp theo ngày hết hạn tăng dần (đồ sắp hết hạn lên đầu)
    today = date.today()
    user_foods = Food.query.filter_by(user_id=session['user_id']).order_by(Food.expiration_date.asc()).all()
    
    # 4. Gửi dữ liệu sang trang index.html
    return render_template('index.html', foods=user_foods, today=today)
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

# 2. XÓA THỰC PHẨM
@app.route('/delete_food/<int:id>')
def delete_food(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    food_to_delete = Food.query.get_or_404(id)
    # 3. QUAN TRỌNG: Kiểm tra xem thực phẩm này có đúng là của người đang đăng nhập không?
    # Tránh trường hợp ông A xóa đồ của ông B bằng cách đoán ID
    if food_to_delete.user_id != session['user_id']:
        flash('Bạn không có quyền xóa thực phẩm này!', 'danger')
        return redirect(url_for('home'))
    
    # 4. Xóa và Lưu
    try:
        db.session.delete(food_to_delete)
        db.session.commit()
        flash('Đã xóa thực phẩm thành công!', 'success')
    except:
        flash('Có lỗi xảy ra khi xóa.', 'danger')
        
    return redirect(url_for('home'))

# Route Sửa thực phẩm
@app.route('/edit_food/<int:id>', methods=['GET', 'POST'])
def edit_food(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    food = Food.query.get_or_404(id)
    
    # Kiểm tra quyền sở hữu
    if food.user_id != session['user_id']:
        flash('Bạn không có quyền sửa thực phẩm này!', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Cập nhật thông tin từ Form vào đối tượng Food cũ
        food.name = request.form.get('name')
        food.quantity = float(request.form.get('quantity'))
        food.unit = request.form.get('unit')
        food.location = request.form.get('location')
        
        # Xử lý ngày tháng
        date_str = request.form.get('expiration_date')
        food.expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        try:
            db.session.commit() # Chỉ cần commit, không cần add lại
            flash('Cập nhật thành công!', 'success')
            return redirect(url_for('home'))
        except:
            flash('Lỗi khi cập nhật.', 'danger')

    # Nếu là GET: Hiển thị form với dữ liệu cũ
    return render_template('food/edit_food.html', food=food)

@app.route('/init_recipes')
def init_recipes():
    recipes = [
        Recipe(name="Trứng chiên hành lá", ingredients_list="Trứng gà, Hành lá, Nước mắm", instructions="Đập trứng, cắt hành, đánh tan rồi chiên vàng."),
        Recipe(name="Canh cà chua trứng", ingredients_list="Trứng gà, Cà chua, Hành lá", instructions="Phi thơm hành, xào cà chua, thêm nước sôi và đổ trứng vào."),
        Recipe(name="Sữa ngũ cốc", ingredients_list="Sữa tươi, Ngũ cốc", instructions="Cho ngũ cốc vào bát, đổ sữa tươi vào và thưởng thức."),
        Recipe(name="Bánh mỳ ốp la", ingredients_list="Bánh mỳ, Trứng gà", instructions="Chiên trứng ốp la, ăn kèm với bánh mỳ."),
        Recipe(name="Salad cà chua xà lách", ingredients_list="Cà chua, Xà lách, Dầu ăn", instructions="Thái lát các nguyên liệu và trộn với dầu giấm."),
        # Bạn hãy thêm tiếp cho đủ 10-15 món tương tự...
    ]
    try:
        db.session.add_all(recipes)
        db.session.commit()
        return "Đã tạo 15 công thức mẫu thành công!"
    except:
        return "Dữ liệu đã tồn tại hoặc có lỗi."
    
@app.route('/suggest')
def suggest():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 1. Lấy thực phẩm trong tủ
    user_foods = Food.query.filter_by(user_id=session['user_id']).all()
    
    # ✅ PHẢI CÓ DÒNG NÀY: Khai báo biến fridge_items
    fridge_items = [f.name.lower().strip() for f in user_foods]

    # 2. Lấy tất cả công thức
    all_recipes = Recipe.query.all()
    suggestions = []

    # 3. Logic Matching
    for recipe in all_recipes:
        # Tách chuỗi nguyên liệu trong DB thành danh sách
        recipe_ingredients = [i.strip().lower() for i in recipe.ingredients_list.split(',')]
        
        matches = []
        for need in recipe_ingredients:
            # So sánh tương đối: "trứng" có nằm trong "trứng gà" không?
            if any(item in need or need in item for item in fridge_items):
                matches.append(need)
        
        total_needed = len(recipe_ingredients)
        if total_needed > 0:
            score = int((len(matches) / total_needed) * 100)
            if score > 0:
                suggestions.append({
                    'info': recipe,
                    'score': score,
                    'matches': matches,
                    'missing': set(recipe_ingredients) - set(matches)
                })

    # Sắp xếp theo điểm khớp
    suggestions.sort(key=lambda x: x['score'], reverse=True)

    return render_template('food/suggest.html', suggestions=suggestions)
# --- Chạy App ---
if __name__ == '__main__':
    # Tạo bảng CSDL tự động nếu chưa có (chạy 1 lần đầu)
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)