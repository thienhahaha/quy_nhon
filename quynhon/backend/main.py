import csv
import hmac
import io
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    send_from_directory,
    session,
    url_for,
)

# ---- Đường dẫn theo cấu trúc project ----
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
IMAGE_DIR = ROOT_DIR / "image"
DB_PATH = BACKEND_DIR / "app.db"

app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR / "templates"),
    static_folder=str(FRONTEND_DIR / "static"),
    static_url_path="/static",
)
# Session cần SECRET_KEY để ký cookie. Khi chạy thật hãy đặt biến môi trường SECRET_KEY.
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-hay-doi-khi-chay-that")


# ---- SQLite ----
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tu_van (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ten      TEXT NOT NULL,
                sdt      TEXT NOT NULL,
                loi_nhan TEXT DEFAULT '',
                tao_luc  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---- Routes ----
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/image/<path:filename>")
def image(filename):
    return send_from_directory(IMAGE_DIR, filename)


@app.post("/tu-van")
def tu_van():
    ten = request.form.get("ten", "").strip()[:100]
    sdt = request.form.get("sdt", "").strip()[:20]
    loi_nhan = request.form.get("loi_nhan", "").strip()[:1000]

    if not ten or not sdt:
        flash("Vui lòng nhập họ tên và số điện thoại.")
        return redirect(url_for("index") + "#tu-van")

    data = {"ten": ten, "sdt": sdt, "loi_nhan": loi_nhan}

    # Bước 1: lưu vào session
    session["tu_van"] = data

    # Bước 2: lưu vào database
    db = get_db()
    cur = db.execute(
        "INSERT INTO tu_van (ten, sdt, loi_nhan) VALUES (?, ?, ?)",
        (ten, sdt, loi_nhan),
    )
    db.commit()

    # Ghi thêm id của bản ghi vừa lưu vào session
    session["tu_van"] = {**data, "id": cur.lastrowid}

    # Chuyển hướng để F5 không gửi lại form
    return redirect(url_for("cam_on"))


@app.get("/cam-on")
def cam_on():
    data = session.get("tu_van")  # đọc lại dữ liệu từ session
    if not data:
        return redirect(url_for("index"))
    return render_template("cam_on.html", data=data)


# ---- Khu vực quản lý (xem dữ liệu trực tiếp) ----
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


def can_dang_nhap(f):
    """Chỉ cho người đã đăng nhập vào."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/api/"):
                return jsonify(ok=False), 401
            return redirect(url_for("dang_nhap"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/dang-nhap", methods=["GET", "POST"])
def dang_nhap():
    if request.method == "POST":
        mk = request.form.get("matkhau", "")
        if ADMIN_PASSWORD and hmac.compare_digest(mk.encode(), ADMIN_PASSWORD.encode()):
            session["admin"] = True
            return redirect(url_for("quan_ly"))
        flash("Mật khẩu không đúng." if ADMIN_PASSWORD else "Máy chủ chưa đặt ADMIN_PASSWORD.")
    return render_template("dang_nhap.html")


@app.get("/dang-xuat")
def dang_xuat():
    session.pop("admin", None)
    return redirect(url_for("dang_nhap"))


@app.get("/quan-ly")
@can_dang_nhap
def quan_ly():
    return render_template("quan_ly.html")


@app.get("/api/tu-van")
@can_dang_nhap
def api_tu_van():
    """Trang quản lý gọi API này mỗi vài giây để lấy dữ liệu mới."""
    db = get_db()
    tong = db.execute("SELECT COUNT(*) FROM tu_van").fetchone()[0]
    rows = db.execute(
        "SELECT id, ten, sdt, loi_nhan, datetime(tao_luc, '+7 hours') AS tao_luc "
        "FROM tu_van ORDER BY id DESC LIMIT 200"
    ).fetchall()
    resp = jsonify(tong=tong, ds=[dict(r) for r in rows])
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _an_toan(v):
    """Chặn công thức độc hại khi mở CSV bằng Excel."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


@app.get("/xuat-csv")
@can_dang_nhap
def xuat_csv():
    rows = get_db().execute(
        "SELECT id, datetime(tao_luc, '+7 hours'), ten, sdt, loi_nhan FROM tu_van ORDER BY id"
    ).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Mã", "Thời gian", "Họ tên", "Số điện thoại", "Lời nhắn"])
    for r in rows:
        w.writerow([_an_toan(v) for v in tuple(r)])
    return Response(
        "\ufeff" + buf.getvalue(),  # BOM để Excel đọc đúng tiếng Việt
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=yeu-cau-tu-van.csv"},
    )


init_db()  # tạo bảng ngay khi server khởi động (cần cho gunicorn)

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("DEBUG", "1") == "1",
    )