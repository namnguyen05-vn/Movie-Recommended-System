import requests
import time
import re
from app.db.database import SessionLocal
from app.db.models import Movie

# ĐIỀN API KEY CỦA BẠN VÀO ĐÂY
TMDB_API_KEY = "38a24d288a2ac72112bf20b02d65e4d0"
BASE_URL = "https://api.themoviedb.org/3/search/movie"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"  # w500 là kích thước ảnh (width 500px)


def clean_title(raw_title):
    """
    Tên phim trong MovieLens thường có dạng: 'Toy Story (1995)'
    Hàm này dùng Regex (Biểu thức chính quy) để tách tên phim và năm ra.
    Giúp TMDB tìm kiếm chính xác 100%.
    """
    match = re.match(r"^(.*?)\s*\((\d{4})\)$", raw_title.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return raw_title.strip(), None


def sync_movies_with_tmdb():
    db = SessionLocal()

    # Chỉ tìm những phim chưa có ảnh Poster (để rớt mạng chạy lại không bị trùng)
    movies_to_update = db.query(Movie).filter((Movie.description == "") | (Movie.description == None)).limit(100).all()

    if not movies_to_update:
        print("🎉 Toàn bộ phim đã được cập nhật Poster!")
        return

    print(f"🤖 Bắt đầu cào dữ liệu cho {len(movies_to_update)} bộ phim...")

    success_count = 0
    for movie in movies_to_update:
        title, year = clean_title(movie.title)

        # Cấu hình gói hàng gửi cho TMDB (thêm tham số language=vi-VN để ưu tiên lấy nội dung Tiếng Việt)
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "language": "vi-VN"
        }
        if year:
            params["primary_release_year"] = year

        try:
            response = requests.get(BASE_URL, params=params)
            data = response.json()

            # Nếu TMDB tìm thấy ít nhất 1 kết quả
            if data.get("results") and len(data["results"]) > 0:
                best_match = data["results"][0]  # Lấy kết quả sát nhất

                # Cập nhật thông tin vào đối tượng Movie
                if best_match.get("poster_path"):
                    movie.poster_url = IMAGE_URL + best_match["poster_path"]
                desc = best_match.get("overview", "")

                # NẾU MÔ TẢ TIẾNG VIỆT BỊ TRỐNG -> GỌI LẠI BẰNG TIẾNG ANH
                if not desc.strip():
                    params["language"] = "en-US"
                    en_response = requests.get(BASE_URL, params=params).json()
                    if en_response.get("results") and len(en_response["results"]) > 0:
                        desc = en_response["results"][0].get("overview", "Chưa có mô tả.")
                movie.description = desc

                print(f"✅ Đã tải: {title} ({year})")
                success_count += 1
            else:
                print(f"❌ Không tìm thấy: {title} trên TMDB")
                # Đánh dấu bằng ảnh mặc định để lần sau script bỏ qua phim này
                movie.poster_url = "https://via.placeholder.com/500x750?text=No+Poster"
                movie.description = "Không tìm thấy thông tin trên TMDB."

            # TMDB cho phép tối đa khoảng 40 request/giây, ta cho robot nghỉ 0.1s cho an toàn
            time.sleep(0.1)

        except Exception as e:
            print(f"⚠️ Lỗi mạng khi tải phim {title}: {e}")

    # Lưu toàn bộ dữ liệu xuống MySQL
    db.commit()
    db.close()
    print(f"✅ Hoàn tất đợt cào dữ liệu! Cập nhật thành công {success_count} phim.")


if __name__ == "__main__":
    sync_movies_with_tmdb()