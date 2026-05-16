const API_URL = "http://127.0.0.1:8000/api";
let isLoginMode = true;
let currentMovieId = null;
let currentPage = 1;
const itemsPerPage = 12;
let currentGenre = '';
let currentSearch = '';
let isWatchingAI = false;

const movieModal = new bootstrap.Modal(document.getElementById('movieModal'));

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem("token");

    // Luôn mở khóa khu vực giao diện
    document.getElementById('movieSection').classList.remove('hidden');
    document.getElementById('genreSection').classList.remove('hidden');

    if (token) {
        document.getElementById('logoutBtn').classList.remove('hidden');
        showMainInterface();
        loadHome();
    } else {
        document.getElementById('logoutBtn').classList.add('hidden');
        document.getElementById('authSection').classList.remove('hidden');
        loadMoviesByGenre('');
        document.getElementById('sectionTitle').innerText = "Trending Movies (Login for AI Specs)";
    }
});

// ============ AUTH ============
document.getElementById('toggleAuth').addEventListener('click', (e) => {
    e.preventDefault();
    isLoginMode = !isLoginMode;
    document.getElementById('authTitle').innerText = isLoginMode ? "Sign In" : "Sign Up";
    document.getElementById('authBtn').innerText = isLoginMode ? "Enter" : "Create Account";
    e.target.innerText = isLoginMode ? "Don't have an account? Sign up" : "Already have an account? Sign in";
    document.getElementById('authAlert').classList.add('hidden');
});

document.getElementById('authForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const endpoint = isLoginMode ? "/auth/login" : "/auth/register";

    try {
        const response = await fetch(API_URL + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (!response.ok) return showAlert(data.detail || "Lỗi hệ thống!");

        if (isLoginMode) {
            localStorage.setItem("token", data.access_token);
            localStorage.setItem("username", username);
            // Clear form fields
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            document.getElementById('authAlert').classList.add('hidden');
            showMainInterface();
            loadHome();
        } else {
            showAlert("Account created! Please sign in.", "success");
            // Clear form fields after success
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            document.getElementById('toggleAuth').click();
        }
    } catch (error) { showAlert("Lỗi kết nối Server!"); }
});

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    location.reload();
}

function showMainInterface() {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('welcomeText').innerText = `(${localStorage.getItem("username")})`;
    document.getElementById('logoutBtn').classList.remove('hidden');
}
function showAlert(msg, type="danger") {
    const alert = document.getElementById('authAlert');
    alert.innerText = msg;
    alert.className = `alert alert-${type}`;
    alert.classList.remove('hidden');
}

// ============ LOAD DATA ============
function handleSearch(event) {
    event.preventDefault();
    currentSearch = document.getElementById('searchInput').value.trim();
    currentGenre = ''; currentPage = 1; isWatchingAI = false;
    document.getElementById('sectionTitle').innerText = `Search Results: "${currentSearch}"`;
    fetchMoviesData();
}

async function loadMoviesByGenre(genre) {
    currentGenre = genre; currentSearch = ''; currentPage = 1; isWatchingAI = false;
    document.getElementById('searchInput').value = '';
    document.getElementById('sectionTitle').innerText = genre ? `${genre} Movies` : "Trending Movies";
    fetchMoviesData();
}

async function loadHome() {
    isWatchingAI = true;
    document.getElementById('paginationControls').classList.add('hidden');
    document.getElementById('sectionTitle').innerText = "Analyzing your taste...";
    document.getElementById('movieList').innerHTML = "";

    try {
        const response = await fetch(API_URL + "/recommend", {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") }
        });
        if (response.status === 401) return logout();
        const data = await response.json();
        document.getElementById('sectionTitle').innerText = data.is_new_user ? "Trending Movies" : "Personalized For You";
        renderMovies(data.recommendations, true);
    } catch (error) { console.error(error); }
}

async function fetchMoviesData() {
    const skip = (currentPage - 1) * itemsPerPage;
    let url = `${API_URL}/movies?skip=${skip}&limit=${itemsPerPage}`;
    if (currentGenre) url += `&genre=${currentGenre}`;
    if (currentSearch) url += `&search=${currentSearch}`;

    try {
        const response = await fetch(url);
        const movies = await response.json();
        renderMovies(movies, false);

        document.getElementById('paginationControls').classList.remove('hidden');
        document.getElementById('pageInfo').innerText = `Page ${currentPage}`;
        document.getElementById('prevBtn').disabled = (currentPage === 1);
        document.getElementById('nextBtn').disabled = (movies.length < itemsPerPage);
    } catch (error) { console.error(error); }
}

function changePage(direction) {
    currentPage += direction;
    fetchMoviesData();
    window.scrollTo({ top: 350, behavior: 'smooth' }); // Scroll tới phần danh sách phim
}

// ============ RENDER ============
function renderMovies(movies, isAI = false) {
    const list = document.getElementById('movieList');
    list.innerHTML = "";

    movies.forEach(movie => {
        const poster = movie.poster_url || "https://via.placeholder.com/500x750?text=No+Poster";
        // Lọc thông minh: Cố gắng lấy năm trong ngoặc (1995), và lấy Thể loại đầu tiên
        const yearMatch = movie.title.match(/\((\d{4})\)/);
        const year = yearMatch ? yearMatch[1] : 'Unknown';
        const cleanTitle = movie.title.replace(/\(\d{4}\)/, '').trim(); // Bỏ năm khỏi tiêu đề
        const primaryGenre = movie.genres.split('|')[0] || 'Movie';
        const desc = movie.description || "Nội dung chi tiết đang được cập nhật...";

        // Mô phỏng điểm Rating hiển thị lên góc (Dùng AI rating hoặc tự random nếu là data thô)
        let ratingNum = isAI && movie.predicted_rating ? movie.predicted_rating : (Math.random() * 2 + 7);

        const html = `
            <div class="col-12 col-sm-6 col-md-4 col-lg-3 mb-4">
                <div class="movie-card">
                    <div class="movie-poster-container" onclick="openMovieDetails(${movie.movieId})">
                        <img src="${poster}" class="movie-poster" alt="${cleanTitle}">
                        <div class="rating-badge"><i class="bi bi-star-fill me-1"></i>${ratingNum.toFixed(1)}</div>
                    </div>
                    <div class="movie-info">
                        <div class="movie-title">${cleanTitle}</div>
                        <div class="movie-meta">${year} • ${primaryGenre}</div>
                        <div class="movie-desc">${desc}</div>
                        <button class="fav-btn" onclick="dummyFav(event)"><i class="bi bi-heart me-2"></i>Add to Favorites</button>
                    </div>
                </div>
            </div>
        `;
        list.insertAdjacentHTML('beforeend', html);
    });
}

function dummyFav(e) {
    e.stopPropagation(); // Ngăn click nhầm vào thẻ mở chi tiết
    alert("Đã thêm vào mục Yêu thích!");
}

// ============ MODAL DETAILS ============
async function openMovieDetails(movieId) {
    currentMovieId = movieId;
    document.getElementById('rateMessage').innerText = "";
    renderStars();
    try {
        const response = await fetch(`${API_URL}/movies/${movieId}`);
        const movie = await response.json();
        const cleanTitle = movie.title.replace(/\(\d{4}\)/, '').trim();

        document.getElementById('modalTitle').innerText = cleanTitle;
        document.getElementById('modalPoster').src = movie.poster_url || "https://via.placeholder.com/500x750?text=No+Poster";
        document.getElementById('modalGenres').innerText = movie.genres.replace(/\|/g, ' • ');
        document.getElementById('modalDesc').innerText = movie.description || "Chưa có mô tả chi tiết.";

        movieModal.show();
    } catch (error) { console.error(error); }
}

function renderStars() {
    const container = document.getElementById('starRatingContainer');
    let html = '';
    for (let i = 5; i >= 1; i--) {
        html += `<input type="radio" id="star${i}" name="rating" value="${i}" onclick="submitRating(${i})"><label for="star${i}">★</label>`;
    }
    container.innerHTML = html;
}

async function submitRating(ratingValue) {
    const token = localStorage.getItem("token");
    const msgDiv = document.getElementById('rateMessage');
    if (!token) return msgDiv.innerHTML = "<span class='text-danger'>Vui lòng Đăng nhập để đánh giá phim!</span>";

    msgDiv.innerText = "⏳ Đang gửi...";
    try {
        const response = await fetch(API_URL + "/rate", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ movieId: currentMovieId, rating: parseFloat(ratingValue) })
        });
        if (response.ok) msgDiv.innerHTML = "<span class='text-success'>✅ Cảm ơn đánh giá của bạn!</span>";
        else msgDiv.innerHTML = "<span class='text-danger'>❌ Lỗi khi đánh giá.</span>";
    } catch (error) { msgDiv.innerHTML = "<span class='text-danger'>❌ Mất kết nối mạng.</span>"; }
}