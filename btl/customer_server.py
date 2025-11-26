from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import datetime
import jwt # Bạn cần cài: pip install PyJWT
import os
import json

# --- Cấu hình và Khởi tạo ---
app = Flask(__name__)
CORS(app) # Cho phép tất cả các domain
app.config['SECRET_KEY'] = 'your_very_secret_key_for_customer'

# --- Cơ sở dữ liệu (Giả lập bằng In-Memory Dictionaries) ---
db = {
    "customers": {
        "customer@gmail.com": {
            "id": "C001", 
            "name": "Nguyễn Văn Khách", 
            "email": "customer@gmail.com", 
            "phone": "0909123456",
            "password": "123456" # Phải băm (hash) trong thực tế
        }
    },
    "bookings": {
        "B001": {
            "id": "B001",
            "customerId": "C001",
            "date": "2025-11-10",
            "time": "18:30",
            "guests": 2,
            "specialRequests": "Xin bàn gần cửa sổ",
            "status": "Đã đặt"
        }
    }
}

# --- Persistence: store customer DB to JSON file ---
BASE_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE_DIR, 'customer_db.json')

def load_db_from_file():
    global db
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                on_disk = json.load(f)
                if isinstance(on_disk, dict):
                    db = on_disk
                    print('Loaded customer DB from', DB_FILE)
    except Exception as e:
        print('Error loading customer DB file:', e)

def save_db_to_file():
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Error saving customer DB file:', e)

load_db_from_file()

# --- Hàm Hỗ trợ ---
def create_customer_token(customer_id, email):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
        'sub': customer_id,
        'email': email
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# --- API Routes: Khách hàng (Customer) ---
@app.route('/api/customer/register', methods=['POST'])
def customer_register():
    data = request.get_json()
    email = data.get('email')

    if not email or not data.get('password') or not data.get('name'):
        return jsonify({"message": "Thiếu thông tin đăng ký"}), 400
        
    if email in db["customers"]:
        return jsonify({"message": "Email này đã được đăng ký"}), 400

    new_id = f"C{len(db['customers']) + 1:03d}"
    new_customer = {
        "id": new_id,
        "name": data["name"],
        "email": email,
        "phone": data.get("phone", ""),
        "password": data["password"] # Cần băm
    }
    db["customers"][email] = new_customer
    
    token = create_customer_token(new_customer["id"], new_customer["email"])
    customer_info = {k: v for k, v in new_customer.items() if k != 'password'}
    save_db_to_file()
    
    return jsonify({"token": token, "customer": customer_info}), 201

@app.route('/api/customer/login', methods=['POST'])
def customer_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    customer = db["customers"].get(email)

    if not customer or customer["password"] != password:
        return jsonify({"message": "Email hoặc mật khẩu không đúng"}), 401

    token = create_customer_token(customer["id"], customer["email"])
    customer_info = {k: v for k, v in customer.items() if k != 'password'}
    
    return jsonify({"token": token, "customer": customer_info})

# --- API Routes: Đặt bàn (Booking) ---
@app.route('/api/customer/book-table', methods=['POST'])
def book_table():
    # Cần có hàm xác thực token ở đây
    data = request.get_json()
    
    new_id = f"B{len(db['bookings']) + 1:03d}"
    new_booking = {
        "id": new_id,
        "customerId": data["customerId"],
        "date": data["date"],
        "time": data["time"],
        "guests": data["guests"],
        "specialRequests": data.get("specialRequests", ""),
        "status": "Đã đặt" # Trạng thái ban đầu
    }
    db["bookings"][new_id] = new_booking
    save_db_to_file()
    
    # Logic nghiệp vụ: Cần gửi thông báo cho admin, hoặc tạo 1 event
    # Ở đây, chúng ta cũng có thể thêm nó vào server admin (nếu 2 server có liên lạc)
    
    return jsonify(new_booking), 201

@app.route('/api/customer/bookings/<string:customer_id>', methods=['GET'])
def get_booking_history(customer_id):
    # Cần có hàm xác thực token ở đây
    
    history = [b for b in db["bookings"].values() if b["customerId"] == customer_id]
    history_sorted = sorted(history, key=lambda x: (x['date'], x['time']), reverse=True)
    
    return jsonify(history_sorted)

@app.route('/api/customer/cancel-booking/<string:booking_id>', methods=['PUT'])
def cancel_booking(booking_id):
    # Cần có hàm xác thực token ở đây
    
    if booking_id not in db["bookings"]:
        return jsonify({"message": "Không tìm thấy lịch đặt bàn"}), 404
        
    # Xác thực xem khách hàng này có sở hữu booking_id này không
    
    db["bookings"][booking_id]["status"] = "Đã hủy"
    save_db_to_file()
    
    return jsonify(db["bookings"][booking_id])



# --- Serve simple frontend files ---
@app.route('/', methods=['GET'])
def index():
    """Serve `btl.html` or `btl_completed.html` if present, otherwise return a small JSON message."""
    base_dir = os.path.dirname(__file__)
    candidates = ['btl.html', 'btl_completed.html']
    for fname in candidates:
        if os.path.exists(os.path.join(base_dir, fname)):
            return send_from_directory(base_dir, fname)
    # fallback
    return jsonify({"message": "Customer API server is running. Use /api/* endpoints."})


@app.route('/btl.html')
def serve_btl():
    base_dir = os.path.dirname(__file__)
    candidates = ['btl.html', 'btl_completed.html']
    for fname in candidates:
        if os.path.exists(os.path.join(base_dir, fname)):
            return send_from_directory(base_dir, fname)
    return jsonify({"message": "File btl.html not found"}), 404


# --- Chạy Server ---
if __name__ == '__main__':
    app.run(port=3001, debug=True)