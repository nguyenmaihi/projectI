# 🧊 SMART FRIDGE - QUẢN LÝ TỦ LẠNH THÔNG MINH

### 📝 Giới thiệu dự án
Dự án được thực hiện cho học phần **Project I** tại **HUST**. Ứng dụng giúp số hóa việc quản lý thực phẩm, cảnh báo hạn dùng và gợi ý món ăn.

---

### 🌟 Tính năng chính
* **Quản lý thực phẩm:** Theo dõi tên, số lượng, vị trí và ngày hết hạn.
* **Cảnh báo thông minh:** Tự động đổi màu thực phẩm sắp hết hạn.
* **Gợi ý món ăn:** Thuật toán khớp nguyên liệu và ưu tiên đồ sắp hỏng.
* **Thống kê:** Biểu đồ Radar và Doughnut trực quan.

---

### 🛠️ Công nghệ sử dụng
* **Backend:** Python, Flask Framework.
* **Database:** SQLite (SQLAlchemy ORM).
* **Frontend:** HTML5, CSS3, JS, Chart.js.

---

### 📂 Cấu trúc mã nguồn
```text
SMART FRIDGE/
│
├── app.py              # Xử lý logic nghiệp vụ và điều hướng chính
├── models.py           # Định nghĩa cấu trúc các bảng dữ liệu (User, Food,...)
├── extensions.py       # Khởi tạo các tiện ích (SQLAlchemy, Bcrypt, Login)
├── requirements.txt    # Danh sách thư viện cần thiết cho dự án
├── database.db         # Cơ sở dữ liệu SQLite của hệ thống
├── templates/          # Thư mục chứa giao diện Jinja2
│   ├── auth/           # Giao diện Login, Register, Account
│   ├── food/           # Giao diện Suggest (Gợi ý món ăn)
│   ├── base.html       # Giao diện khung (Layout chính)
│   ├── index.html      # Trang quản lý tủ lạnh
│   └── statistics.html # Trang thống kê biểu đồ
├── static/             # Chứa CSS, JS và hình ảnh giao diện
└── venv/               # Môi trường ảo của Python
```
---

### ⚙️ Hướng dẫn khởi chạy
#### Cách 1: Clone dự án từ github
1. `python -m venv venv`
2. `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `python app.py`
##### Cách 2: trai nghiệm hệ thống tại
[https://smart-fridge-1zrb.onrender.com/](url)

---

### 🎓 Tác giả
* **Sinh viên:** Nguyễn Thị Tuyết Mai
* **Ngành:** Kỹ thuật Máy tính - HUST
