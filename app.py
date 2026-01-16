from flask import Flask, render_template, url_for, flash, redirect, request, session
from extensions import db, bcrypt 
from models import User, Food, Recipe, Favorite 
from datetime import datetime, date
from sqlalchemy import func
import os

app = Flask(__name__)

# --- Cấu hình ---
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

db.init_app(app)
bcrypt.init_app(app)

# -----------------------------------------------------------
# ROUTES CƠ BẢN
# -----------------------------------------------------------

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Quan trọng: Luôn truyền 'today' để index.html tính toán hạn sử dụng
    today = date.today()
    user_foods = Food.query.filter_by(user_id=session['user_id']).order_by(Food.expiration_date.asc()).all()
    
    return render_template('index.html', foods=user_foods, today=today)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if 'user_id' in session: return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Tên đăng nhập hoặc Email đã tồn tại!', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Đăng ký thành công!', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('Lỗi hệ thống.', 'danger')
    return render_template('auth/register.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Chào mừng {user.username} quay trở lại!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu.', 'danger')
    return render_template('auth/login.html')

@app.route("/logout")
def logout():
    session.clear()
    flash('Đã đăng xuất.', 'info')
    return redirect(url_for('login'))

# -----------------------------------------------------------
# QUẢN LÝ THỰC PHẨM (Hỗ trợ Modal)
# -----------------------------------------------------------

@app.route("/add_food", methods=['POST'])
def add_food():
    if 'user_id' not in session: return redirect(url_for('login'))

    try:
        name = request.form.get('name')
        quantity = float(request.form.get('quantity'))
        unit = request.form.get('unit')
        location = request.form.get('location')
        date_str = request.form.get('expiration_date')
        expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        new_food = Food(
            name=name, quantity=quantity, unit=unit,
            location=location, expiration_date=expiration_date,
            user_id=session['user_id']
        )
        db.session.add(new_food)
        db.session.commit()
        flash(f'Đã thêm {name}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
        
    return redirect(url_for('home')) # Luôn quay về trang chủ vì dùng Modal

@app.route('/edit_food/<int:id>', methods=['POST'])
def edit_food(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    food = Food.query.get_or_404(id)
    if food.user_id != session['user_id']: return redirect(url_for('home'))

    try:
        food.name = request.form.get('name')
        food.quantity = float(request.form.get('quantity'))
        food.unit = request.form.get('unit')
        food.location = request.form.get('location')
        date_str = request.form.get('expiration_date')
        food.expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Cập nhật thành công!', 'success')
    except:
        db.session.rollback()
        flash('Lỗi khi cập nhật.', 'danger')

    return redirect(url_for('home')) # Quay về trang chủ sau khi sửa xong Modal

@app.route('/delete_food/<int:id>')
def delete_food(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    food = Food.query.get_or_404(id)
    if food.user_id == session['user_id']:
        db.session.delete(food)
        db.session.commit()
        flash('Đã xóa thực phẩm.', 'info')
    return redirect(url_for('home'))

# -----------------------------------------------------------
# GỢI Ý & THỐNG KÊ
# -----------------------------------------------------------

# Route Suggest
@app.route('/suggest')
def suggest():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    uid = session['user_id']
    today = date.today()
    all_foods = Food.query.filter_by(user_id=uid).all()
    
    # 1. Danh sách thực phẩm sắp hết hạn (còn <= 3 ngày) để tính trọng số
    soon_to_expire_names = [f.name.lower().strip() for f in all_foods 
                           if 0 <= (f.expiration_date - today).days <= 3]
    
    fridge_items = [f.name.lower().strip() for f in all_foods]
    fav_ids = [f.recipe_id for f in Favorite.query.filter_by(user_id=uid).all()]
    all_recipes_list = Recipe.query.all()
    
    smart_suggestions = []
    for recipe in all_recipes_list:
        recipe_ingredients = [i.strip().lower() for i in recipe.ingredients_list.split(',')]
        
        matches = []
        urgency_bonus = 0
        
        for need in recipe_ingredients:
            # Kiểm tra xem có nguyên liệu này trong tủ không
            found_in_fridge = any(item in need or need in item for item in fridge_items)
            
            if found_in_fridge:
                matches.append(need)
                # 🌟 TRỌNG SỐ MỚI: Nếu nguyên liệu này sắp hết hạn, cộng thêm 30 điểm thưởng
                is_urgent = any(soon in need or need in soon for soon in soon_to_expire_names)
                if is_urgent:
                    urgency_bonus += 10 

        # Tính điểm cơ bản (Phần trăm hoàn thành)
        base_score = int((len(matches) / len(recipe_ingredients)) * 100) if recipe_ingredients else 0
        
        # Tổng điểm = Điểm cơ bản + Điểm thưởng khẩn cấp
        total_score = base_score + urgency_bonus
        is_fav = recipe.id in fav_ids

        # ✅ Lọc: Chỉ hiện món yêu thích HOẶC món có điểm tổng hợp cao (> 50)
        if is_fav or total_score > 50:
            smart_suggestions.append({
                'info': recipe,
                'score': total_score, # Đây giờ là điểm ưu tiên tổng hợp
                'base_score': base_score,
                'is_urgent': urgency_bonus > 0,
                'matches': matches,
                'missing': set(recipe_ingredients) - set(matches),
                'is_fav': is_fav
            })

    # Sắp xếp: Ưu tiên món Yêu thích -> Sau đó đến món có tổng điểm (độ tươi + độ gấp) cao nhất
    smart_suggestions.sort(key=lambda x: (x['is_fav'], x['score']), reverse=True)

    all_recipes_sorted = sorted(all_recipes_list, key=lambda x: x.id in fav_ids, reverse=True)

    return render_template('food/suggest.html', 
                           all_recipes=all_recipes_sorted, 
                           smart_suggestions=smart_suggestions,
                           fav_ids=fav_ids)

@app.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
def toggle_favorite(recipe_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    
    uid = session['user_id']
    # Tìm xem bản ghi đã tồn tại chưa
    fav = Favorite.query.filter_by(user_id=uid, recipe_id=recipe_id).first()

    if fav:
        db.session.delete(fav)
        status = "unhearted"
    else:
        new_fav = Favorite(user_id=uid, recipe_id=recipe_id)
        db.session.add(new_fav)
        status = "hearted"
    
    db.session.commit()
    return {"status": status}

@app.route('/statistics')
def statistics():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    today = date.today()
    all_foods = Food.query.filter_by(user_id=uid).all()

    # 1. Thống kê vị trí và Phân loại hạn dùng
    location_data = db.session.query(Food.location, func.count(Food.id)).filter_by(user_id=uid).group_by(Food.location).all()
    expired_list, soon_list, fresh_list = [], [], []
    for f in all_foods:
        days = (f.expiration_date - today).days
        if days < 0: expired_list.append(f)
        elif days <= 3: soon_list.append(f)
        else: fresh_list.append(f)

    # 2. Phân tích Dinh dưỡng
    groups = {
        'Đạm': ['thịt', 'cá', 'tôm', 'trứng', 'giò', 'chả', 'sườn', 'bò', 'gà'],
        'Chất xơ': ['rau', 'cải', 'muống', 'ngót', 'bí', 'bầu', 'mướp', 'súp lơ'],
        'Vitamin': ['quả', 'trái', 'cam', 'táo', 'chuối', 'bơ', 'nho', 'xoài'],
        'Sữa/Bơ': ['sữa', 'phô mai', 'yogurt', 'váng sữa'],
        'Tinh bột': ['bánh', 'mỳ', 'miến', 'bún', 'ngô', 'khoai']
    }
    nutrition_counts = {key: 0 for key in groups}
    for f in all_foods:
        name_lower = f.name.lower()
        for group, keywords in groups.items():
            if any(k in name_lower for k in keywords):
                nutrition_counts[group] += 1
                break

    # 3. Tính điểm Sức khỏe và Lời khuyên
    health_score = 100
    if len(all_foods) > 0:
        score = 100 - (len(expired_list) * 10) - (len(soon_list) * 5)
        health_score = max(0, score)

    # Tạo danh sách lời khuyên dựa trên dữ liệu
    advice = []
    if health_score >= 80:
        advice.append("🌟 Bạn quản lý tủ lạnh rất tuyệt vời, hãy tiếp tục phát huy!")
    elif health_score >= 50:
        advice.append("⚠️ Tủ lạnh bắt đầu có dấu hiệu quá tải đồ cũ, bạn nên kiểm tra lại.")
    else:
        advice.append("🚨 Báo động! Tủ lạnh đang rất mất cân đối và nhiều đồ hỏng.")

    if expired_list:
        advice.append(f"❌ Có {len(expired_list)} món đã quá hạn. Bạn nên bỏ ngay để bảo vệ sức khỏe.")
    if soon_list:
        advice.append(f"⏰ Nhắc nhở: Hãy nấu món '{soon_list[0].name}' ngay vì nó sắp hết hạn.")
    
    # Kiểm tra nhóm chất thiếu
    missing = [group for group, count in nutrition_counts.items() if count == 0]
    if missing:
        advice.append(f"🛒 Lần tới đi chợ, hãy bổ sung thêm: {', '.join(missing)}.")

    return render_template('statistics.html', 
                           location_labels=[row[0] for row in location_data],
                           location_values=[row[1] for row in location_data],
                           status_values=[len(expired_list), len(soon_list), len(fresh_list)],
                           nutrition_labels=list(nutrition_counts.keys()),
                           nutrition_values=list(nutrition_counts.values()),
                           health_score=health_score,
                           expired_list=expired_list, soon_list=soon_list, fresh_list=fresh_list,
                           today=today,
                           advice=advice)

@app.route('/init_recipes')
def init_recipes():
    # Xóa dữ liệu cũ để nạp lại bản chuẩn hóa
    with app.app_context():
        db.session.query(Recipe).delete()
        
        recipes = [
            Recipe(name="Trứng chiên hành lá", ingredients_list="Trứng gà, Hành lá, Nước mắm", 
                   instructions="1. Đập trứng vào bát.\n2. Thêm hành lá băm nhỏ và một chút nước mắm.\n3. Đánh tan trứng rồi chiên trên chảo nóng cho đến khi vàng đều."),
            
            Recipe(name="Đậu phụ sốt cà chua", ingredients_list="Đậu phụ, Cà chua, Hành lá", 
                   instructions="1. Thái đậu phụ thành khối vuông, rán vàng.\n2. Cà chua băm nhỏ, xào cho nhuyễn thành sốt.\n3. Cho đậu đã rán vào rim cùng sốt cà chua trong 5 phút."),
            
            Recipe(name="Thịt lợn rang cháy cạnh", ingredients_list="Thịt lợn, Hành tím, Nước mắm", 
                   instructions="1. Thái thịt mỏng.\n2. Rang thịt trên chảo cho đến khi ra bớt mỡ và cạnh hơi cháy vàng.\n3. Thêm hành tím băm và nước mắm, đảo đều cho thấm."),
            
            Recipe(name="Rau muống xào tỏi", ingredients_list="Rau muống, Tỏi, Dầu ăn", 
                   instructions="1. Rau muống luộc sơ qua nước sôi.\n2. Phi thơm tỏi băm với dầu ăn.\n3. Cho rau vào xào lửa lớn, nêm gia vị vừa ăn rồi tắt bếp."),
            
            Recipe(name="Canh cà chua trứng", ingredients_list="Cà chua, Trứng gà, Hành lá", 
                   instructions="1. Xào nhuyễn cà chua với dầu ăn.\n2. Thêm nước sôi vào nồi.\n3. Đổ trứng đã đánh tan vào, khuấy nhẹ để tạo vân rồi thêm hành lá."),
            
            Recipe(name="Sườn xào chua ngọt", ingredients_list="Sườn heo, Cà chua, Hành tây", 
                   instructions="1. Sườn luộc sơ rồi rán vàng cạnh.\n2. Pha hỗn hợp sốt cà chua, đường, giấm.\n3. Cho sườn và hành tây vào rim cùng sốt cho đến khi sền sệt."),
            
            Recipe(name="Thịt kho tàu", ingredients_list="Thịt lợn, Trứng gà, Nước dừa", 
                   instructions="1. Thịt lợn thái miếng to, ướp gia vị.\n2. Cho thịt và trứng đã luộc vào nồi nước dừa.\n3. Kho nhỏ lửa cho đến khi thịt mềm và nước có màu cánh gián."),
            
            Recipe(name="Canh rau cải thịt băm", ingredients_list="Rau cải, Thịt lợn, Gừng", 
                   instructions="1. Xào sơ thịt băm với hành tím.\n2. Thêm nước và vài lát gừng vào đun sôi.\n3. Cho rau cải vào nấu chín tới rồi nêm gia vị."),
            
            Recipe(name="Gà kho gừng", ingredients_list="Thịt gà, Gừng, Hành tím", 
                   instructions="1. Gà chặt miếng vừa ăn, ướp gia vị.\n2. Gừng thái sợi, hành tím băm nhỏ.\n3. Kho gà với gừng và một ít nước màu cho đến khi thịt săn và thấm vị."),
            
            Recipe(name="Bò xào cần tây", ingredients_list="Thịt bò, Cần tây, Hành tây", 
                   instructions="1. Thịt bò thái mỏng, ướp tỏi.\n2. Xào thịt bò chín tái rồi để riêng.\n3. Xào cần tây và hành tây chín tới, sau đó cho bò vào đảo nhanh tay."),
            
            Recipe(name="Cá kho tộ", ingredients_list="Cá, Thịt lợn, Hành tím", 
                   instructions="1. Cá cắt khúc, thịt ba chỉ thái nhỏ.\n2. Xếp cá và thịt vào tộ, thêm nước mắm và nước hàng.\n3. Kho cho đến khi nước cạn gần hết và cá chắc thịt."),
            
            Recipe(name="Canh bí đỏ thịt băm", ingredients_list="Bí đỏ, Thịt lợn, Hành lá", 
                   instructions="1. Bí đỏ gọt vỏ, thái miếng vừa ăn.\n2. Nấu thịt băm với nước cho sôi.\n3. Cho bí đỏ vào hầm cho đến khi bí chín mềm."),
            
            Recipe(name="Salad cà chua dưa chuột", ingredients_list="Cà chua, Dưa chuột, Xà lách", 
                   instructions="1. Cà chua và dưa chuột thái lát mỏng.\n2. Trộn đều với xà lách.\n3. Thêm sốt dầu giấm và trộn nhẹ tay trước khi ăn."),
            
            Recipe(name="Salad ức gà áp chảo", ingredients_list="Ức gà, Xà lách, Cà chua", 
                   instructions="1. Ức gà ướp muối tiêu rồi áp chảo chín đều, thái lát.\n2. Sắp xếp xà lách và cà chua ra đĩa.\n3. Đặt thịt gà lên trên và thêm sốt mè rang."),
            
            Recipe(name="Salad bơ trứng gà", ingredients_list="Bơ, Trứng gà, Xà lách", 
                   instructions="1. Bơ thái miếng, trứng gà luộc chín thái múi cau.\n2. Trộn xà lách với sốt mayonnaise hoặc sữa chua.\n3. Trang trí bơ và trứng lên trên mặt salad.")
        ]
        
        db.session.add_all(recipes)
        db.session.commit()
    return "Hệ thống đã chuẩn hóa 15 công thức món ăn thành công!"

@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        
        if old_pass and new_pass:
            # Kiểm tra mật khẩu cũ có khớp với hash trong DB không
            if bcrypt.check_password_hash(user.password_hash, old_pass):
                user.password_hash = bcrypt.generate_password_hash(new_pass).decode('utf-8')
                db.session.commit()
                flash('Cập nhật mật khẩu thành công!', 'success')
            else:
                flash('Mật khẩu cũ không chính xác.', 'danger')
        return redirect(url_for('account'))

    # Lấy danh sách các món ăn mà user này đã nhấn yêu thích
    # Chúng ta sử dụng join để lấy được thông tin chi tiết từ bảng Recipe
    user_favorites = Favorite.query.filter_by(user_id=user.id).all()

    return render_template('auth/account.html', user=user, favorites=user_favorites)
@app.route("/init_db")
def init_db():
    with app.app_context():
        db.create_all()
    return "Database initialized!"

if __name__ == '__main__':
    app.run(debug=True)
