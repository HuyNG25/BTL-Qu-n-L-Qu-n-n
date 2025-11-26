from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import datetime
import jwt # Bạn cần cài: pip install PyJWT
import os
import json

# --- Cấu hình và Khởi tạo ---
app = Flask(__name__)
CORS(app) # Cho phép tất cả các domain
app.config['SECRET_KEY'] = 'your_very_secret_key_for_admin'

# --- Cơ sở dữ liệu (Giả lập bằng In-Memory Dictionaries) ---
db = {
    "users": {
        "admin": {"id": 1, "name": "Admin Quản Lý", "username": "admin", "password": "123456", "role": "Quản lý"},
        "nv001": {"id": 2, "name": "Trần Thu Ngân", "username": "nv001", "password": "123", "role": "Thu ngân"}
    },
    "dishes": {
        "F001": {"id": "F001", "name": "Phở bò", "category": "Đồ ăn", "price": 50000, "status": "Còn hàng"},
        "F002": {"id": "F002", "name": "Cà phê sữa", "category": "Thức uống", "price": 25000, "status": "Còn hàng"},
        "F003": {"id": "F003", "name": "Combo gia đình", "category": "Combo", "price": 200000, "status": "Hết hàng"}
    },
    "orders": {
        "ORD001": {
            "id": "ORD001", "table": "Bàn 5", "time": "2025-11-03T14:30:00", "total": 450000, "status": "Đã thanh toán",
            "items": [
                {"name": "Phở bò", "quantity": 2, "price": 50000},
                {"name": "Combo gia đình", "quantity": 1, "price": 200000},
                {"name": "Cà phê sữa", "quantity": 6, "price": 25000}
            ]
        },
        "ORD002": {
            "id": "ORD002", "table": "Bàn 12", "time": "2025-11-04T10:15:00", "total": 320000, "status": "Đang phục vụ",
             "items": [{"name": "Cà phê sữa", "quantity": 4, "price": 25000}, {"name": "Phở bò", "quantity": 2, "price": 50000}]
        }
    },
    "tables": {
        "T1": {"id": "T1", "name": "Bàn 1", "status": "Trống", "orderId": None},
        "T2": {"id": "T2", "name": "Bàn 2", "status": "Trống", "orderId": None},
        "T3": {"id": "T3", "name": "Bàn 3", "status": "Đã đặt", "orderId": None},
        "T12": {"id": "T12", "name": "Bàn 12", "status": "Đang dùng", "orderId": "ORD002"}
    },
    "events": {
        "EV001": {"id": "EV001", "name": "Tiệc sinh nhật", "time": "2025-11-10T19:00:00", "guests": 15, "status": "Đã đặt"},
        "EV002": {"id": "EV002", "name": "Họp mặt công ty", "time": "2025-11-05T12:00:00", "guests": 30, "status": "Đã đặt"}
    },
    "customers": { # Dữ liệu này được đồng bộ từ server khách (nếu cần)
        "C001": {"id": "C001", "name": "Nguyễn Văn Khách", "email": "customer@gmail.com", "phone": "0909123456"}
    }
}

# --- Persistence: load/save DB to JSON file so data survives server restarts ---
BASE_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE_DIR, 'admin_db.json')

def load_db_from_file():
    global db
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                on_disk = json.load(f)
                # merge keys (preserve structure)
                if isinstance(on_disk, dict):
                    db = on_disk
                    print('Loaded DB from', DB_FILE)
    except Exception as e:
        print('Error loading DB file:', e)

def save_db_to_file():
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Error saving DB file:', e)

# Load existing DB (if present)
load_db_from_file()

# --- Hàm Hỗ trợ ---
def create_token(user_id, username):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id,
        'username': username
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# --- API Routes: Xác thực (Auth) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = db["users"].get(username)

    if not user or user["password"] != password:
        return jsonify({"message": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401

    token = create_token(user["id"], user["username"])
    return jsonify({"token": token, "user": {"name": user["name"], "role": user["role"]}})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    
    if not username or not data.get('password') or not data.get('name') or not data.get('role'):
        return jsonify({"message": "Thiếu thông tin đăng ký"}), 400

    if username in db["users"]:
        return jsonify({"message": "Tên đăng nhập đã tồn tại"}), 400

    new_id = f"NV{len(db['users']) + 1:03d}"
    new_user = {
        "id": new_id,
        "name": data["name"],
        "username": username,
        "password": data["password"], # Trong thực tế: băm mật khẩu
        "role": data["role"]
    }
    db["users"][username] = new_user
    print("New user registered:", new_user)
    save_db_to_file()
    return jsonify({"message": "Đăng ký thành công"}), 201

# --- API Routes: Món ăn (Dishes) ---
@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    return jsonify(list(db["dishes"].values()))

@app.route('/api/dishes', methods=['POST'])
def create_dish():
    data = request.get_json()
    new_id = f"F{len(db['dishes']) + 1:03d}"
    new_dish = {
        "id": new_id,
        "name": data["name"],
        "category": data["category"],
        "price": int(data["price"]),
        "status": data["status"]
    }
    db["dishes"][new_id] = new_dish
    save_db_to_file()
    return jsonify(new_dish), 201

@app.route('/api/dishes/<string:dish_id>', methods=['GET'])
def get_dish(dish_id):
    dish = db["dishes"].get(dish_id)
    if not dish:
        return jsonify({"message": "Không tìm thấy món ăn"}), 404
    return jsonify(dish)

@app.route('/api/dishes/<string:dish_id>', methods=['PUT'])
def update_dish(dish_id):
    if dish_id not in db["dishes"]:
        return jsonify({"message": "Không tìm thấy món ăn"}), 404
    
    data = request.get_json()
    db["dishes"][dish_id].update({
        "name": data.get("name"),
        "category": data.get("category"),
        "price": int(data.get("price")),
        "status": data.get("status")
    })
    save_db_to_file()
    return jsonify(db["dishes"][dish_id])

@app.route('/api/dishes/<string:dish_id>', methods=['DELETE'])
def delete_dish(dish_id):
    if dish_id not in db["dishes"]:
        return jsonify({"message": "Không tìm thấy món ăn"}), 404
    
    del db["dishes"][dish_id]
    save_db_to_file()
    return jsonify({"message": "Xóa món ăn thành công"}), 200

# --- API Routes: Đơn hàng (Orders) ---
@app.route('/api/orders', methods=['GET'])
def get_orders():
    limit = request.args.get('limit', type=int)
    status = request.args.get('status')
    
    orders = sorted(db["orders"].values(), key=lambda x: x['time'], reverse=True)
    
    if status:
        orders = [o for o in orders if o['status'] == status]
    if limit:
        orders = orders[:limit]
        
    return jsonify(orders)

@app.route('/api/orders/<string:order_id>', methods=['GET'])
def get_order_detail(order_id):
    order = db["orders"].get(order_id)
    if not order:
        return jsonify({"message": "Không tìm thấy đơn hàng"}), 404
    return jsonify(order)


@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    table_id = data.get('tableId') or data.get('table')
    items = data.get('items', [])

    if not table_id:
        return jsonify({"message": "Thiếu thông tin bàn"}), 400
    if not items or not isinstance(items, list):
        return jsonify({"message": "Thiếu danh sách món"}), 400

    # Validate table
    table = db['tables'].get(table_id)
    if not table:
        return jsonify({"message": "Bàn không tồn tại"}), 404

    # Build order items and calculate total
    order_items = []
    total = 0
    for it in items:
        dish_id = it.get('dishId')
        qty = int(it.get('quantity', 0))
        if not dish_id or qty <= 0:
            return jsonify({"message": "Dữ liệu món không hợp lệ"}), 400
        dish = db['dishes'].get(dish_id)
        if not dish:
            return jsonify({"message": f"Không tìm thấy món: {dish_id}"}), 404
        order_items.append({"name": dish['name'], "quantity": qty, "price": dish['price']})
        total += dish['price'] * qty

    # Create order id
    new_id = f"ORD{len(db['orders']) + 1:03d}"
    now_iso = datetime.datetime.utcnow().isoformat()
    order = {
        "id": new_id,
        "table": table['name'],
        "time": now_iso,
        "total": total,
        "status": "Đang phục vụ",
        "items": order_items
    }

    db['orders'][new_id] = order

    # Update table status
    db['tables'][table_id]['status'] = 'Đang dùng'
    db['tables'][table_id]['orderId'] = new_id

    save_db_to_file()

    return jsonify(order), 201

@app.route('/api/orders/<string:order_id>', methods=['DELETE'])
def delete_order(order_id):
    if order_id not in db["orders"]:
        return jsonify({"message": "Không tìm thấy đơn hàng"}), 404
    del db["orders"][order_id]
    save_db_to_file()
    return jsonify({"message": "Xóa đơn hàng thành công"})

@app.route('/api/orders/<string:order_id>/pay', methods=['POST'])
def pay_order(order_id):
    if order_id not in db["orders"]:
        return jsonify({"message": "Không tìm thấy đơn hàng"}), 404

    order = db["orders"][order_id]
    order["status"] = "Đã thanh toán"
    
    # Cập nhật trạng thái bàn
    table_name = order["table"]
    table_id = next((tid for tid, t in db["tables"].items() if t["name"] == table_name), None)
    if table_id:
        db["tables"][table_id]["status"] = "Trống"
        db["tables"][table_id]["orderId"] = None
    
    save_db_to_file()
    return jsonify({"message": "Thanh toán thành công", "order": order})

# --- API Routes: Bàn ăn (Tables) ---
@app.route('/api/tables', methods=['GET'])
def get_tables():
    return jsonify(list(db["tables"].values()))


@app.route('/api/tables', methods=['POST'])
def create_table():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"message": "Thiếu tên bàn"}), 400

    # Create new table id
    new_id = f"T{len(db['tables']) + 1}"
    new_table = {"id": new_id, "name": name, "status": "Trống", "orderId": None}
    db['tables'][new_id] = new_table
    save_db_to_file()
    return jsonify(new_table), 201


@app.route('/api/tables/merge', methods=['POST'])
def merge_tables():
    data = request.get_json()
    source_ids = data.get('sourceIds') or data.get('source_ids')
    name = data.get('name')
    if not source_ids or not isinstance(source_ids, list) or len(source_ids) < 2:
        return jsonify({"message": "Cần ít nhất 2 bàn để gộp"}), 400
    if not name:
        return jsonify({"message": "Thiếu tên bàn gộp"}), 400

    # Validate source tables exist
    for sid in source_ids:
        if sid not in db['tables']:
            return jsonify({"message": f"Bàn không tồn tại: {sid}"}), 404

    # Create new merged table
    new_id = f"T{len(db['tables']) + 1}"
    merged_table = {"id": new_id, "name": name, "status": "Đang dùng", "orderId": None}
    db['tables'][new_id] = merged_table

    # Mark source tables as 'Đang dùng' (or you could mark as 'Gộp')
    for sid in source_ids:
        db['tables'][sid]['status'] = 'Đang dùng'
    save_db_to_file()
    return jsonify(merged_table), 201

@app.route('/api/tables/<string:table_id>', methods=['PUT'])
def update_table_status(table_id):
    if table_id not in db["tables"]:
        return jsonify({"message": "Không tìm thấy bàn"}), 404
    
    data = request.get_json()
    if 'status' in data:
        db["tables"][table_id]["status"] = data["status"]
    if 'orderId' in data:
        db["tables"][table_id]["orderId"] = data["orderId"]
    save_db_to_file()
    return jsonify(db["tables"][table_id])

# --- API Routes: Nhân viên (Staff) ---
@app.route('/api/staff', methods=['GET'])
def get_staff():
    # Không trả về password
    staff_list = []
    for user in db["users"].values():
        staff_list.append({k: v for k, v in user.items() if k != 'password'})
    return jsonify(staff_list)

@app.route('/api/staff/<string:staff_id>', methods=['GET'])
def get_staff_detail(staff_id):
    staff = next((s for s in db["users"].values() if s["id"] == staff_id), None)
    if not staff:
        return jsonify({"message": "Không tìm thấy nhân viên"}), 404
    # Không trả về password
    staff_detail = {k: v for k, v in staff.items() if k != 'password'}
    return jsonify(staff_detail)

@app.route('/api/staff', methods=['POST'])
def create_staff():
    data = request.get_json()
    if data['username'] in db["users"]:
        return jsonify({"message": "Tên đăng nhập đã tồn tại"}), 400
    
    new_id = f"NV{len(db['users']) + 1:03d}"
    new_staff = {
        "id": new_id,
        "name": data["name"],
        "username": data["username"],
        "password": data["password"], # Cần băm
        "role": data["role"]
    }
    db["users"][data['username']] = new_staff
    save_db_to_file()
    return jsonify({k: v for k, v in new_staff.items() if k != 'password'}), 201

@app.route('/api/staff/<string:staff_id>', methods=['PUT'])
def update_staff(staff_id):
    staff = next((s for s in db["users"].values() if s["id"] == staff_id), None)
    if not staff:
        return jsonify({"message": "Không tìm thấy nhân viên"}), 404
    
    data = request.get_json()
    staff.update({
        "name": data.get("name", staff["name"]),
        "role": data.get("role", staff["role"])
    })
    if data.get("password"):
        staff["password"] = data["password"] # Cần băm
    save_db_to_file()
    return jsonify({k: v for k, v in staff.items() if k != 'password'})

@app.route('/api/staff/<string:staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    staff_username = next((username for username, s in db["users"].items() if s["id"] == staff_id), None)
    if not staff_username:
        return jsonify({"message": "Không tìm thấy nhân viên"}), 404
    
    if staff_username == 'admin':
        return jsonify({"message": "Không thể xóa tài khoản admin"}), 403
        
    del db["users"][staff_username]
    save_db_to_file()
    return jsonify({"message": "Xóa nhân viên thành công"})

# --- API Routes: Sự kiện (Events) ---
@app.route('/api/events', methods=['GET'])
def get_events():
    return jsonify(list(db["events"].values()))

@app.route('/api/events', methods=['POST'])
def create_event():
    data = request.get_json()
    new_id = f"EV{len(db['events']) + 1:03d}"
    new_event = {
        "id": new_id,
        "name": data["name"],
        "time": data["time"],
        "guests": int(data["guests"]),
        "status": data.get("status", "Đã đặt")
    }
    db["events"][new_id] = new_event
    save_db_to_file()
    return jsonify(new_event), 201

@app.route('/api/events/<string:event_id>', methods=['GET'])
def get_event_detail(event_id):
    event = db["events"].get(event_id)
    if not event:
        return jsonify({"message": "Không tìm thấy sự kiện"}), 404
    return jsonify(event)

@app.route('/api/events/<string:event_id>', methods=['PUT'])
def update_event(event_id):
    if event_id not in db["events"]:
        return jsonify({"message": "Không tìm thấy sự kiện"}), 404
    
    data = request.get_json()
    db["events"][event_id].update({
        "name": data.get("name"),
        "time": data.get("time"),
        "guests": int(data.get("guests")),
        "status": data.get("status")
    })
    save_db_to_file()
    return jsonify(db["events"][event_id])

@app.route('/api/events/<string:event_id>', methods=['DELETE'])
def delete_event(event_id):
    if event_id not in db["events"]:
        return jsonify({"message": "Không tìm thấy sự kiện"}), 404
    del db["events"][event_id]
    save_db_to_file()
    return jsonify({"message": "Hủy sự kiện thành công"})

# --- API Routes: Khách hàng (Admin view) ---
@app.route('/api/customers', methods=['GET'])
def get_admin_customers():
    # Trong thực tế, admin server có thể gọi customer server
    # Hoặc cả hai cùng dùng chung 1 CSDL.
    # Ở đây ta giả lập
    return jsonify(list(db["customers"].values()))

# --- API Routes: Dashboard ---
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    # Giả lập data, trong thực tế cần truy vấn CSDL
    today_orders = sum(1 for o in db["orders"].values() if o['time'].startswith(datetime.date.today().isoformat()))
    today_revenue = sum(o['total'] for o in db["orders"].values() if o['time'].startswith(datetime.date.today().isoformat()) and o['status'] == 'Đã thanh toán')
    occupied_tables = sum(1 for t in db["tables"].values() if t['status'] == 'Đang dùng')
    total_tables = len(db["tables"])
    low_stock_items = sum(1 for d in db["dishes"].values() if d['status'] == 'Hết hàng')
    
    return jsonify({
        "todayOrders": today_orders,
        "todayRevenue": today_revenue,
        "occupiedTables": occupied_tables,
        "totalTables": total_tables,
        "lowStockItems": low_stock_items
    })

# --- Chạy Server ---
# --- Serve simple frontend files ---
@app.route('/', methods=['GET'])
def index():
    """Serve `btl.html` or `btl_completed.html` if present, otherwise return a small JSON message."""
    base_dir = os.path.dirname(__file__)
    # prefer btl.html, fallback to btl_completed.html
    candidates = ['btl.html', 'btl_completed.html']
    for fname in candidates:
        path = os.path.join(base_dir, fname)
        if os.path.exists(path):
            return send_from_directory(base_dir, fname)
    # fallback: show a simple message so root isn't a 404
    return jsonify({"message": "Admin API server is running. Use /api/* endpoints."})


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
    app.run(port=3000, debug=True)