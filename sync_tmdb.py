import requests
import time
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Movie

# TẠO KẾT NỐI ĐỒNG BỘ ĐỘC LẬP CHO SCRIPT NÀY
sync_engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# API KEY
TMDB_API_KEY = "38a24d288a2ac72112bf20b02d65e4d0"
OMDB_API_KEY = "882ad3e1"

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_DETAIL_URL = "https://api.themoviedb.org/3/movie/{}"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_URL = "https://image.tmdb.org/t/p/original"
OMDB_BASE_URL = "http://www.omdbapi.com/"


def clean_title(raw_title):
    """Tách tên phim và năm ra để tìm kiếm chính xác."""
    match = re.match(r"^(.*?)\s*\((\d{4})\)$", raw_title.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return raw_title.strip(), None


def sync_movies_extended_data():
    db = SessionLocal()

    # Tìm những phim ĐÃ CÓ POSTER nhưng CHƯA CÓ THỜI LƯỢNG (Dấu hiệu chưa quét dữ liệu mới)
    movies_to_update = db.query(Movie).filter(
        Movie.poster_url.isnot(None),
        Movie.poster_url != "https://via.placeholder.com/500x750?text=No+Poster",
        Movie.runtime == None
    ).limit(1000).all()

    if not movies_to_update:
        print("🎉 Toàn bộ kho phim đã được cập nhật đầy đủ dữ liệu Điện Ảnh!")
        return

    print(f"🤖 Bắt đầu chiến dịch cào dữ liệu mở rộng cho {len(movies_to_update)} phim...")

    success_count = 0
    for movie in movies_to_update:
        title, year = clean_title(movie.title)
        data_found = False

        # ==========================================
        # LỚP 1: TMDB (Tìm kiếm -> Lấy Chi Tiết)
        # ==========================================
        try:
            # 1. Lấy ID phim trên TMDB
            search_params = {"api_key": TMDB_API_KEY, "query": title, "language": "vi-VN"}
            if year: search_params["primary_release_year"] = year

            search_res = requests.get(TMDB_SEARCH_URL, params=search_params, timeout=5).json()

            if search_res.get("results") and len(search_res["results"]) > 0:
                tmdb_id = search_res["results"][0]["id"]

                # 2. Lấy Chi Tiết + Danh sách Diễn Viên bằng tuyệt chiêu "append_to_response"
                detail_url = TMDB_DETAIL_URL.format(tmdb_id)
                detail_params = {
                    "api_key": TMDB_API_KEY,
                    "language": "vi-VN",
                    "append_to_response": "credits"
                }
                detail_res = requests.get(detail_url, params=detail_params, timeout=5).json()

                # Cập nhật các trường dữ liệu điện ảnh
                if detail_res.get("backdrop_path"):
                    movie.backdrop_url = TMDB_BACKDROP_URL + detail_res["backdrop_path"]
                else:
                    movie.backdrop_url = "https://via.placeholder.com/1920x1080/1a1a1a/1a1a1a"

                movie.runtime = detail_res.get("runtime")
                movie.imdb_rating = detail_res.get("vote_average")

                release_date = detail_res.get("release_date", "")
                if release_date:
                    movie.release_year = int(release_date.split("-")[0])
                elif year:
                    movie.release_year = int(year)

                # Lọc ra Đạo diễn
                crew = detail_res.get("credits", {}).get("crew", [])
                directors = [member["name"] for member in crew if member["job"] == "Director"]
                movie.director = ", ".join(directors) if directors else "Đang cập nhật"

                # Lọc ra Top 5 diễn viên chính
                cast = detail_res.get("credits", {}).get("cast", [])
                top_cast = [member["name"] for member in cast[:5]]
                movie.cast = ", ".join(top_cast) if top_cast else "Đang cập nhật"

                print(f"✅ [TMDB] Đã nâng cấp: {title} ({movie.release_year}) - {movie.runtime} min")
                data_found = True
                success_count += 1

            time.sleep(0.1)
        except Exception as e:
            pass

        # ==========================================
        # LỚP 2: OMDB FALLBACK
        # ==========================================
        if not data_found:
            try:
                omdb_params = {"apikey": OMDB_API_KEY, "t": title}
                if year: omdb_params["y"] = year

                omdb_res = requests.get(OMDB_BASE_URL, params=omdb_params, timeout=5).json()

                if omdb_res.get("Response") == "True":
                    # Xử lý chuỗi thời lượng "148 min" -> 148
                    runtime_str = omdb_res.get("Runtime", "")
                    if "min" in runtime_str:
                        try:
                            movie.runtime = int(runtime_str.replace(" min", ""))
                        except:
                            movie.runtime = 0
                    else:
                        movie.runtime = 0

                    try:
                        movie.imdb_rating = float(omdb_res.get("imdbRating", 0))
                    except:
                        pass

                    movie.director = omdb_res.get("Director", "Đang cập nhật")
                    movie.cast = omdb_res.get("Actors", "Đang cập nhật")
                    movie.release_year = int(year) if year else None
                    movie.backdrop_url = "https://via.placeholder.com/1920x1080/1a1a1a/1a1a1a"

                    print(f"🌟 [OMDb] Đã vá dữ liệu: {title}")
                    success_count += 1
                else:
                    print(f"❌ [Bỏ qua] Không có dữ liệu mở rộng cho: {title}")
                    movie.runtime = 0  # Gán = 0 để script không quét lại phim này ở lần chạy sau

                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Lỗi OMDb với phim {title}")

        db.commit()

    db.close()
    print(f"\n🎉 Hoàn tất! Đã nâng cấp thành công {success_count} bộ phim.")


if __name__ == "__main__":
    sync_movies_extended_data()