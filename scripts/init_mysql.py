import pandas as pd
from sqlalchemy import create_engine, text

# ==========================================
# CẤU HÌNH KẾT NỐI MYSQL
# ==========================================
USER = 'root'
PASSWORD = 'namnguyenngoc2608%40'
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'movie_database'

print("⏳ BƯỚC 1: Đang kết nối đến MySQL Workbench...")
# Tạo cầu nối (Engine) giữa Python và MySQL
engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")

print("⏳ BƯỚC 2: Đang đọc dữ liệu từ file CSV...")
movies_df = pd.read_csv('../data/movies.csv')
ratings_df = pd.read_csv('../data/ratings.csv')

print("⏳ BƯỚC 3: Đang đẩy dữ liệu vào MySQL (Có thể mất 10-20 giây cho 100.000 dòng)...")
# Đẩy bảng Movies
movies_df.to_sql('movies', con=engine, if_exists='replace', index=False)
print("   -> Đã tạo xong bảng 'movies'")

# Đẩy bảng Ratings (chia nhỏ chunksize=10000 để chống tràn RAM)
ratings_df.to_sql('ratings', con=engine, if_exists='replace', index=False, chunksize=10000)
print("   -> Đã tạo xong bảng 'ratings'")

print("⏳ BƯỚC 4: Đang tạo Index để tăng tốc độ truy xuất...")
with engine.connect() as conn:
    conn.execute(text("CREATE INDEX idx_user_id ON ratings(userId)"))
    conn.execute(text("CREATE INDEX idx_movie_id_ratings ON ratings(movieId)"))
    conn.execute(text("CREATE INDEX idx_movie_id_movies ON movies(movieId)"))
    conn.commit()

print("\n✅ HOÀN TẤT! Toàn bộ dữ liệu đã nằm gọn trong MySQL Workbench!")