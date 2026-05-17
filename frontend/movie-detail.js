// Đổi lại URL này nếu Backend của bạn chạy ở port khác
const API_URL = "http://127.0.0.1:8000/api";

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Đọc ID phim từ thanh địa chỉ (Ví dụ: movie-detail.html?id=123)
    const urlParams = new URLSearchParams(window.location.search);
    const movieId = urlParams.get('id');

    // Nếu không có ID, đá về trang chủ
    if (!movieId) {
        window.location.href = 'index.html';
        return;
    }

    try {
        // 2. Gọi API Backend để lấy chi tiết phim
        const response = await fetch(`${API_URL}/movies/${movieId}`);

        if (!response.ok) {
            throw new Error("Không tìm thấy bộ phim này!");
        }

        const movie = await response.json();

        // 3. Tiến hành đổ dữ liệu vào HTML
        renderMovieDetails(movie);

    } catch (error) {
        console.error("Lỗi tải phim:", error);
        document.getElementById('movieOverview').innerText = "Đã xảy ra lỗi khi tải dữ liệu phim.";
    }
});

function renderMovieDetails(movie) {
    // Đổi Tiêu đề tab trình duyệt
    document.title = `${movie.title} - NEXUS Movies`;

    // Cập nhật Backdrop (Ảnh ngang)
    const backdropUrl = movie.backdrop_url || "https://via.placeholder.com/1920x1080/1a1a1a/1a1a1a";
    document.getElementById('backdropContainer').style.backgroundImage = `url('${backdropUrl}')`;

    // Cập nhật Poster (Ảnh dọc)
    const posterUrl = movie.poster_url || "https://via.placeholder.com/500x750?text=No+Poster";
    document.getElementById('moviePoster').src = posterUrl;

    // Cập nhật Thông tin cơ bản
    document.getElementById('movieTitle').innerText = movie.title;

    const rating = movie.imdb_rating ? movie.imdb_rating.toFixed(1) : "N/A";
    document.getElementById('movieRating').innerText = rating;
    document.getElementById('statRating').innerText = rating;

    const year = movie.release_year || "Unknown";
    document.getElementById('movieYear').innerText = year;
    document.getElementById('statYear').innerText = year;

    // Cập nhật Thời lượng
    const runtime = movie.runtime ? `${movie.runtime} min` : "Unknown";
    document.getElementById('movieRuntime').innerText = runtime;

    // Cập nhật Thể loại (Thường DB lưu là Action|Adventure, ta đổi thành Action, Adventure)
    let genresText = movie.genres ? movie.genres.replace(/\|/g, ", ") : "Unknown";
    // Thẻ nhỏ gọn chỉ hiện thể loại đầu tiên
    let firstGenre = movie.genres ? movie.genres.split('|')[0] : "Unknown";
    document.getElementById('movieGenre').innerText = firstGenre;
    document.getElementById('statGenreText').innerText = firstGenre;

    // Cập nhật Đạo diễn và Mô tả
    document.getElementById('movieDirector').innerText = movie.director || "Đang cập nhật";
    document.getElementById('movieOverview').innerText = movie.description || "Chưa có mô tả cho bộ phim này.";

    // Cập nhật Diễn viên (Cắt chuỗi thành các viên thuốc - pills)
    const castContainer = document.getElementById('movieCast');
    castContainer.innerHTML = ""; // Xóa chữ Đang tải mặc định

    if (movie.cast && movie.cast !== "Đang cập nhật") {
        const actors = movie.cast.split(', ');
        actors.forEach(actor => {
            const span = document.createElement('span');
            span.className = 'cast-pill';
            span.innerText = actor;
            castContainer.appendChild(span);
        });
    } else {
        castContainer.innerHTML = '<span class="cast-pill">Đang cập nhật</span>';
    }
    // ==========================================
    // XỬ LÝ NÚT FAVORITES (BẢN FULL-STACK)
    // ==========================================
    const btnFavorite = document.getElementById('btnFavorite');
    const favIcon = document.getElementById('favIcon');
    const favText = document.getElementById('favText');
    const token = localStorage.getItem("token");

    let isFavorite = false;

    // 1. Kiểm tra trạng thái yêu thích từ Backend khi vừa load trang xong
    async function checkFavoriteStatus() {
        if (!token) return; // Chưa đăng nhập thì thôi
        try {
            const res = await fetch(`${API_URL}/favorites/status/${movie.movieId}`, {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.status === 401) return; // Token lởm/hết hạn thì bỏ qua

            const data = await res.json();
            isFavorite = data.is_favorite;
            updateFavoriteUI();
        } catch (err) {
            console.error("Lỗi kiểm tra tim:", err);
        }
    }

    function updateFavoriteUI() {
        if (isFavorite) {
            favIcon.className = "bi bi-heart-fill text-danger me-2";
            favText.innerText = "Remove from Favorites";
            btnFavorite.style.borderColor = "#e50914";
        } else {
            favIcon.className = "bi bi-heart me-2";
            favText.innerText = "Add to Favorites";
            btnFavorite.style.borderColor = "#444";
        }
    }

    // Chạy lệnh kiểm tra ngay
    checkFavoriteStatus();

    // 2. Lắng nghe hành động bấm nút để thay đổi trạng thái lên DB
    btnFavorite.addEventListener('click', async () => {
        if (!token) {
            alert("Vui lòng đăng nhập để sử dụng tính năng này!");
            return;
        }

        try {
            const res = await fetch(`${API_URL}/favorites/toggle`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ movieId: movie.movieId })
            });

            if (res.status === 401) {
                alert("Phiên đăng nhập hết hạn!");
                window.location.href = "index.html";
                return;
            }

            const data = await res.json();
            if (data.status === "success") {
                // Đổi trạng thái UI dựa trên phản hồi thực tế từ Backend
                isFavorite = (data.action === "added");
                updateFavoriteUI();
            }
        } catch (err) {
            console.error("Lỗi thay đổi yêu thích:", err);
            alert("Không thể kết nối đến máy chủ.");
        }
    });
    const starInputs = document.querySelectorAll('#userRatingStars input');
    const ratingStatus = document.getElementById('ratingStatus');
    const userToken = localStorage.getItem("token");

    // Lệnh 1: Gọi xuống MySQL lấy số sao cũ ngay khi vừa load trang chi tiết phim
    async function loadSavedRating() {
        if (!userToken) {
            ratingStatus.innerText = "Log in to rate this movie.";
            return;
        }
        try {
            const response = await fetch(`${API_URL}/rate/${movie.movieId}`, {
                headers: { 'Authorization': 'Bearer ' + userToken }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.rated) {
                    // Tìm đúng ô radio của số sao đó (VD: star5, star4...) và tích chọn
                    const savedStarInput = document.getElementById(`star${Math.round(data.rating)}`);
                    if (savedStarInput) {
                        savedStarInput.checked = true;
                        ratingStatus.innerHTML = `<span class="text-warning">★ You already rated this ${data.rating} stars</span>`;
                    }
                }
            }
        } catch (err) {
            console.error("Lỗi lấy điểm đánh giá cũ:", err);
        }
    }

    // Chạy lệnh tải sao cũ ngay lập tức
    loadSavedRating();

    // Lệnh 2: Lắng nghe sự kiện người dùng bấm chọn số sao mới để lưu lên DB
    starInputs.forEach(input => {
        input.addEventListener('change', async (e) => {
            if (!userToken) {
                alert("Vui lòng đăng nhập để đánh giá phim!");
                e.target.checked = false; // Hủy tích chọn nếu chưa đăng nhập
                return;
            }

            const ratingValue = e.target.value;
            ratingStatus.innerHTML = `<span class="spinner-border spinner-border-sm text-warning"></span> Saving your rating...`;

            try {
                const response = await fetch(`${API_URL}/rate`, {
                    method: "POST",
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + userToken
                    },
                    body: JSON.stringify({
                        movieId: movie.movieId,
                        rating: parseFloat(ratingValue)
                    })
                });

                if (response.ok) {
                    ratingStatus.innerHTML = `<span class="text-success font-weight-bold">✅ You rated this ${ratingValue} stars!</span>`;
                } else {
                    ratingStatus.innerText = "❌ Failed to save rating.";
                }
            } catch (err) {
                console.error("Lỗi gửi đánh giá:", err);
                ratingStatus.innerText = "❌ Connection error.";
            }
        });
    });
}