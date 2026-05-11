from app.db.database import SessionLocal
from app.db.models import User, Rating
from app.core.security import get_password_hash


def seed_old_users():
    print("⏳ Đang quét dữ liệu lịch sử và gieo mầm tài khoản...")
    db = SessionLocal()

    try:
        # 1. Lấy danh sách tất cả các ID độc nhất từ bảng ratings (những người đã từng chấm điểm phim)
        unique_user_ids = [r[0] for r in db.query(Rating.userId).distinct().all()]
        print(f"🔍 Tìm thấy {len(unique_user_ids)} người dùng cũ.")

        # 2. Băm mật khẩu chung "123456" đúng 1 lần cho nhanh
        hashed_pw = get_password_hash("123456")

        users_added = 0

        # 3. Duyệt qua từng ID để tạo tài khoản
        for uid in unique_user_ids:
            # Kiểm tra xem user này đã được tạo chưa để tránh báo lỗi trùng lặp
            existing_user = db.query(User).filter(User.userId == uid).first()

            if not existing_user:
                # Tạo username tự động dạng: user1, user2, user5...
                new_user = User(
                    userId=uid,
                    username=f"user{uid}",
                    password_hash=hashed_pw
                )
                db.add(new_user)
                users_added += 1

        # 4. Lưu toàn bộ vào MySQL
        if users_added > 0:
            db.commit()
            print(f"✅ THÀNH CÔNG! Đã tạo xong {users_added} tài khoản cũ (Mật khẩu chung là: 123456).")
        else:
            print("⚠️ Các tài khoản này đã tồn tại trong Database, không cần tạo thêm.")

    except Exception as e:
        db.rollback()
        print(f"❌ Có lỗi xảy ra: {e}")
    finally:
        db.close()  # Luôn nhớ đóng kết nối


if __name__ == "__main__":
    seed_old_users()