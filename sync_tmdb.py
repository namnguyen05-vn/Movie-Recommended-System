import requests
import time
import re
from app.db.database import SessionLocal
from app.db.models import Movie

# API KEY
TMDB_API_KEY = "38a24d288a2ac72112bf20b02d65e4d0"
OMDB_API_KEY = "882ad3e1"

TMDB_BASE_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"  # w500 là kích thước ảnh (width 500px)
OMDB_BASE_URL = "http://www.omdbapi.com/"

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


def sync_movies_with_fallback():
    db = SessionLocal()

    # Chỉ tìm vét lại những bộ phim MÀ TMDB ĐÃ BÓ TAY (bị gán chữ mặc định)
    movies_to_update = db.query(Movie).filter(
        (Movie.description == None) |
        (Movie.description == "") |
        (Movie.description == "Chưa có mô tả.") |
        (Movie.description == "Không tìm thấy thông tin trên TMDB.") |
        (Movie.poster_url == "https://via.placeholder.com/500x750?text=No+Poster")
    ).limit(1000).all()

    if not movies_to_update:
        print("🎉 Toàn bộ kho phim đã đầy đủ dữ liệu!")
        return

    print(f"🤖 Bắt đầu cào quét 2 LỚP cho {len(movies_to_update)} bộ phim lỗi...")

    success_count = 0
    for movie in movies_to_update:
        title, year = clean_title(movie.title)
        data_found = False

        # ==========================================
        # LỚP 1: THỬ TMDB TRƯỚC
        # ==========================================
        try:
            tmdb_params = {"api_key": TMDB_API_KEY, "query": title, "language": "vi-VN"}
            if year: tmdb_params["primary_release_year"] = year

            tmdb_res = requests.get(TMDB_BASE_URL, params=tmdb_params, timeout=5).json()

            if tmdb_res.get("results") and len(tmdb_res["results"]) > 0:
                best_match = tmdb_res["results"][0]

                # Kiểm tra xem TMDB có thực sự cung cấp đủ ảnh và mô tả không
                poster_path = best_match.get("poster_path")
                desc = best_match.get("overview", "").strip()

                if not desc:
                    # Gọi thử tiếng Anh nếu tiếng Việt rỗng
                    tmdb_params["language"] = "en-US"
                    en_res = requests.get(TMDB_BASE_URL, params=tmdb_params, timeout=5).json()
                    if en_res.get("results") and len(en_res["results"]) > 0:
                        desc = en_res["results"][0].get("overview", "").strip()

                if poster_path and desc:
                    movie.poster_url = TMDB_IMAGE_URL + poster_path
                    movie.description = desc
                    print(f"✅ [TMDB] Đã phục hồi: {title}")
                    data_found = True
                    success_count += 1

            time.sleep(0.1)  # Nghỉ giữa các request TMDB
        except Exception as e:
            pass  # Bỏ qua lỗi TMDB để nhường sân cho OMDb

        # ==========================================
        # LỚP 2: NẾU TMDB BÓ TAY -> CHUYỂN SANG OMDB
        # ==========================================
        if not data_found:
            try:
                omdb_params = {"apikey": OMDB_API_KEY, "t": title}
                if year: omdb_params["y"] = year

                omdb_res = requests.get(OMDB_BASE_URL, params=omdb_params, timeout=5).json()

                if omdb_res.get("Response") == "True":
                    # Lấy Poster từ OMDb
                    omdb_poster = omdb_res.get("Poster")
                    if omdb_poster != "N/A":
                        movie.poster_url = omdb_poster
                    else:
                        movie.poster_url = "https://via.placeholder.com/500x750?text=No+Poster"

                    # Lấy Nội dung từ OMDb
                    omdb_plot = omdb_res.get("Plot")
                    if omdb_plot != "N/A":
                        movie.description = f"[Nguồn OMDb] {omdb_plot}"
                    else:
                        movie.description = "Không có mô tả cho bộ phim này."

                    print(f"🌟 [OMDb] Đã cập nhật thành công: {title}")
                    success_count += 1
                else:
                    print(f"❌ [Bó tay] Cả TMDB và OMDb đều không có: {title}")
                    movie.poster_url = "https://via.placeholder.com/500x750?text=No+Poster"
                    movie.description = "Không tìm thấy thông tin trên bất kỳ nền tảng nào."

                time.sleep(0.1)  # Nghỉ giữa các request OMDb
            except Exception as e:
                print(f"⚠️ Lỗi OMDb với phim {title}")

        # Vừa chạy vừa lưu dữ liệu ngay lập tức
        db.commit()

    db.close()
    print(f"\n🎉 Hoàn tất chiến dịch! Phục hồi thành công {success_count} phim.")


if __name__ == "__main__":
    sync_movies_with_fallback()