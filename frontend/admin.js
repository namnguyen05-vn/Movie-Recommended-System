const API_URL = "http://127.0.0.1:8000/api";

document.addEventListener('DOMContentLoaded', () => {
    const role = localStorage.getItem('role');
    const token = localStorage.getItem('token');
    if (!token || role !== 'admin') { /*... code chặn ...*/ return; }

    // Tải toàn bộ dữ liệu khi vào trang
    loadDashboardStats(token);
    loadTopFavorites(token);
    loadTopRated(token);
});

// HÀM 1: Tải Top Phim Yêu Thích
async function loadTopFavorites(token) {
    const container = document.querySelector('.col-md-6:nth-child(1) .text-center');
    try {
        const response = await fetch(`${API_URL}/admin/top-favorites`, { headers: { 'Authorization': 'Bearer ' + token }});
        if (response.ok) {
            const data = await response.json();
            let html = '<table class="table table-dark table-hover text-start mt-3"><tbody>';
            data.forEach((item, index) => {
                html += `<tr><td style="width: 10%"><span class="badge bg-danger">${index + 1}</span></td>
                         <td>${item.title}</td>
                         <td class="text-end text-danger"><i class="bi bi-heart-fill me-1"></i>${item.count}</td></tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch (error) { container.innerHTML = '<span class="text-danger">Lỗi tải dữ liệu</span>'; }
}

// HÀM 2: Tải Top Phim Đánh Giá Cao
async function loadTopRated(token) {
    const container = document.querySelector('.col-md-6:nth-child(2) .text-center');
    try {
        const response = await fetch(`${API_URL}/admin/top-rated`, { headers: { 'Authorization': 'Bearer ' + token }});
        if (response.ok) {
            const data = await response.json();
            let html = '<table class="table table-dark table-hover text-start mt-3"><tbody>';
            data.forEach((item, index) => {
                html += `<tr><td style="width: 10%"><span class="badge bg-warning text-dark">${index + 1}</span></td>
                         <td>${item.title}</td>
                         <td class="text-end text-warning"><i class="bi bi-star-fill me-1"></i>${item.rating}</td></tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch (error) { container.innerHTML = '<span class="text-danger">Lỗi tải dữ liệu</span>'; }
}

// HÀM 3: Lắng nghe sự kiện Bấm nút Cập nhật AI
document.getElementById('retrainAIBtn').addEventListener('click', async function() {
    const token = localStorage.getItem('token');
    const btn = this;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang phân tích dữ liệu...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/admin/retrain-ai`, {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const data = await response.json();
            alert(data.message);
            document.getElementById('aiLastUpdate').innerText = data.last_update;
        } else {
            alert("Có lỗi xảy ra khi huấn luyện AI.");
        }
    } catch (error) {
        alert("Lỗi kết nối máy chủ!");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

// HÀM 4: Tải Thống kê Tổng quan
async function loadDashboardStats(token) {
    try {
        const response = await fetch(`${API_URL}/admin/stats`, {
            method: 'GET',
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('totalMovies').innerText = data.total_movies || 0;
            document.getElementById('totalUsers').innerText = data.total_users || 0;
            document.getElementById('totalRatings').innerText = data.total_ratings || 0;

            if (data.ai_last_update) {
                document.getElementById('aiLastUpdate').innerText = data.ai_last_update;
            }
        } else {
            console.error("Lỗi từ server khi tải thống kê tổng quan");
        }
    } catch (error) {
        console.error("Lỗi kết nối khi tải thống kê tổng quan:", error);
    }
}

let userCurrentPage = 1;
let userSearchQuery = '';

// HÀM 5: Tải danh sách Users (Đã tích hợp Phân trang & Tìm kiếm)
async function loadUsers(token, page = 1, search = '') {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center"><div class="spinner-border text-light mt-3"></div></td></tr>';

    try {
        // Gửi kèm tham số page và search lên URL API
        const response = await fetch(`${API_URL}/admin/users?page=${page}&limit=5&search=${encodeURIComponent(search)}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const result = await response.json();
            const users = result.users;

            if(users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary py-4">Không tìm thấy thành viên nào phù hợp</td></tr>';
                document.getElementById('usersPagination').innerHTML = '';
                return;
            }

            let html = '';
            users.forEach(user => {
                const roleBadge = user.role === 'admin' ? '<span class="badge bg-danger">Admin</span>' : '<span class="badge bg-secondary">User</span>';
                const isActive = user.is_active !== false;
                const toggleBtnClass = isActive ? 'btn-outline-warning' : 'btn-outline-success';
                const toggleIcon = isActive ? 'bi-lock-fill' : 'bi-unlock-fill';

                const currentUsername = localStorage.getItem('username');
                const isSelf = (user.username === currentUsername);
                const disabledAttr = isSelf ? 'disabled title="Không thể tự khóa chính mình"' : '';

                html += `
                    <tr class="${!isActive ? 'opacity-50' : ''}">
                        <td><span class="text-warning fw-bold">#${user.userId}</span></td>
                        <td>${user.username}</td>
                        <td>${roleBadge}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-info me-1" 
                                onclick="prepareEditModal(${user.userId}, '${user.username}', '${user.role}')">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm ${toggleBtnClass}" ${disabledAttr} onclick="toggleUserStatus(${user.userId})">
                                <i class="bi ${toggleIcon}"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;

            // Đổ các nút bấm phân trang ra màn hình
            renderUserPagination(result.total_pages, result.current_page);
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Lỗi kết nối máy chủ</td></tr>';
    }
}

// Hàm bổ sung: Tự động vẽ các nút phân trang HTML
function renderUserPagination(totalPages, currentPage) {
    const paginationUl = document.getElementById('usersPagination');
    let html = '';

    // Nút "Trước"
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link bg-dark text-light border-secondary" href="#" onclick="changeUserPage(${currentPage - 1})">Trước</a>
             </li>`;

    // Các nút số trang cụ thể (Mặc định tối đa 10 nút nếu không tìm kiếm do backend siết số lượng)
    for (let i = 1; i <= totalPages; i++) {
        const activeClass = currentPage === i ? 'active' : '';
        const btnStyle = currentPage === i ? 'bg-danger border-danger text-light' : 'bg-dark text-light border-secondary';
        html += `<li class="page-item ${activeClass}">
                    <a class="page-link ${btnStyle}" href="#" onclick="changeUserPage(${i})">${i}</a>
                 </li>`;
    }

    // Nút "Sau"
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link bg-dark text-light border-secondary" href="#" onclick="changeUserPage(${currentPage + 1})">Sau</a>
             </li>`;

    paginationUl.innerHTML = html;
}

// Hàm bổ sung: Chuyển trang khi Admin bấm vào các số 1, 2, 3...
window.changeUserPage = function(page) {
    userCurrentPage = page;
    const token = localStorage.getItem('token');
    loadUsers(token, userCurrentPage, userSearchQuery);
}

// --- ĐĂNG KÝ SỰ KIỆN CHO THANH TÌM KIẾM (LIVE SEARCH THÔNG MINH) ---
let searchTimeout = null; // Biến lưu trữ đồng hồ đếm ngược

document.getElementById('userSearchInput').addEventListener('input', function(e) {
    // 1. Hủy đồng hồ cũ nếu người dùng vẫn đang gõ liên tục
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // 2. Lấy chữ đang gõ
    const query = e.target.value;

    // 3. Đặt đồng hồ mới: Chờ 300ms (0.3 giây) sau khi ngừng gõ mới gọi API
    searchTimeout = setTimeout(() => {
        userSearchQuery = query;
        userCurrentPage = 1; // Luôn đưa về trang 1 khi tìm kiếm mới

        const token = localStorage.getItem('token');
        loadUsers(token, userCurrentPage, userSearchQuery);
    }, 300);
});

// Sửa lại sự kiện bấm Menu bên trái để đồng bộ biến trạng thái ban đầu
document.getElementById('menu-users').addEventListener('click', function(e) {
    e.preventDefault();
    const token = localStorage.getItem('token');
    document.querySelectorAll('.sidebar .nav-link').forEach(el => el.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('dashboard-section').classList.add('d-none');
    document.getElementById('users-section').classList.remove('d-none');

    // Reset lại trạng thái ban đầu khi chuyển tab menu
    userCurrentPage = 1;
    userSearchQuery = '';
    document.getElementById('userSearchInput').value = '';

    loadUsers(token, userCurrentPage, userSearchQuery);
});

// --- XỬ LÝ CHUYỂN TAB MENU BÊN TRÁI ---
document.getElementById('menu-dashboard').addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelectorAll('.sidebar .nav-link').forEach(el => el.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('dashboard-section').classList.remove('d-none');
    document.getElementById('users-section').classList.add('d-none');
});

document.getElementById('menu-users').addEventListener('click', function(e) {
    e.preventDefault();
    const token = localStorage.getItem('token');
    document.querySelectorAll('.sidebar .nav-link').forEach(el => el.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('dashboard-section').classList.add('d-none');
    document.getElementById('users-section').classList.remove('d-none');
    loadUsers(token);
});

// ==========================================
// KHỐI LỆNH XỬ LÝ MODAL THÊM/SỬA USER (ĐÃ XÓA EMAIL, THÊM CƠ CHẾ AN TOÀN)
// ==========================================

window.prepareAddModal = function() {
    document.getElementById('userModalTitle').innerText = 'Thêm User Mới';
    document.getElementById('userForm').reset();
    document.getElementById('editUserId').value = '';

    // Yêu cầu nhập mật khẩu khi thêm mới
    document.getElementById('userPassword').required = true;
    document.getElementById('passwordHint').classList.add('d-none');

    // Mở modal an toàn (chống lỗi "bootstrap is not defined" do gọi sai cách)
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
};

window.prepareEditModal = function(id, username, role) {
    document.getElementById('userModalTitle').innerText = 'Sửa Thông Tin User #' + id;
    document.getElementById('editUserId').value = id;
    document.getElementById('userName').value = username;
    document.getElementById('userRole').value = role;

    // Mật khẩu không bắt buộc khi sửa
    document.getElementById('userPassword').required = false;
    document.getElementById('passwordHint').classList.remove('d-none');

    // Mở modal an toàn
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
};

document.getElementById('saveUserBtn').addEventListener('click', async () => {
    // Ràng buộc phải nhập các ô required (như Username, Password khi thêm mới)
    const form = document.getElementById('userForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const userId = document.getElementById('editUserId').value;
    const isEdit = userId !== '';
    const token = localStorage.getItem('token');

    const payload = {
        username: document.getElementById('userName').value,
        role: document.getElementById('userRole').value
    };

    const pwd = document.getElementById('userPassword').value;
    if (pwd) payload.password = pwd;

    const url = isEdit ? `${API_URL}/admin/users/${userId}` : `${API_URL}/admin/users`;
    const method = isEdit ? 'PUT' : 'POST';

    const btn = document.getElementById('saveUserBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang lưu...';
    btn.disabled = true;

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const modalEl = document.getElementById('userModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            form.reset();
            loadUsers(token);
            alert(isEdit ? "Cập nhật thành công!" : "Tạo User thành công!");
        } else {
            const errorData = await response.json();
            alert("Lỗi không thể lưu: " + (errorData.detail || "Kiểm tra dữ liệu nhập!"));
        }
    } catch (error) {
        console.error("Lỗi:", error);
        alert("Lỗi kết nối máy chủ!");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

async function toggleUserStatus(userId) {
    if (!confirm('Bạn có chắc muốn thay đổi trạng thái tài khoản này?')) return;

    const token = localStorage.getItem('token');
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}/toggle`, {
            method: 'PATCH',
            headers: {'Authorization': 'Bearer ' + token}
        });

        if (response.ok) {
            loadUsers(token);
        } else {
            const errorData = await response.json();
            alert(errorData.detail || "Không thể thay đổi trạng thái lúc này!");
        }
    } catch (error) {
        console.error("Lỗi toggle:", error);
    }
}

// ==========================================
// KHU VỰC QUẢN LÝ PHIM (MOVIES)
// ==========================================
let movieCurrentPage = 1;
let movieSearchQuery = '';
let movieSearchTimeout = null;
let currentMoviesList = []; // KHO LƯU TRỮ PHIM TẠM THỜI ĐỂ MỞ MODAL SỬA

// 1. Chuyển Tab Menu Phim
document.getElementById('menu-movies').addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelectorAll('.sidebar .nav-link').forEach(el => el.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('dashboard-section').classList.add('d-none');
    document.getElementById('users-section').classList.add('d-none');
    document.getElementById('movies-section').classList.remove('d-none');

    movieCurrentPage = 1;
    movieSearchQuery = '';
    document.getElementById('movieSearchInput').value = '';
    loadMovies(localStorage.getItem('token'), movieCurrentPage, movieSearchQuery);
});

// 2. Tải danh sách Phim
async function loadMovies(token, page = 1, search = '') {
    const tbody = document.getElementById('moviesTableBody');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center"><div class="spinner-border text-light mt-3"></div></td></tr>';

    try {
        const response = await fetch(`${API_URL}/admin/movies?page=${page}&limit=5&search=${encodeURIComponent(search)}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const result = await response.json();
            currentMoviesList = result.movies; // LƯU VÀO KHO TẠM

            if(currentMoviesList.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary py-4">Không tìm thấy phim nào phù hợp</td></tr>';
                document.getElementById('moviesPagination').innerHTML = '';
                return;
            }

            let html = '';
            currentMoviesList.forEach(movie => {
                const isActive = movie.is_active !== false;
                const toggleBtnClass = isActive ? 'btn-outline-warning' : 'btn-outline-success';
                const toggleIcon = isActive ? 'bi-eye-fill' : 'bi-eye-slash-fill';

                html += `
                    <tr class="${!isActive ? 'opacity-50' : ''}">
                        <td><span class="text-primary fw-bold">#${movie.movieId}</span></td>
                        <td class="fw-bold">
                            ${movie.title} 
                            ${movie.release_year ? `<br><small class="text-secondary">${movie.release_year}</small>` : ''}
                        </td>
                        <td><span class="badge bg-secondary">${movie.genres || 'N/A'}</span></td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="prepareEditMovieModal(${movie.movieId})">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm ${toggleBtnClass}" onclick="toggleMovieStatus(${movie.movieId})">
                                <i class="bi ${toggleIcon}"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
            renderMoviePagination(result.total_pages, result.current_page);
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Lỗi kết nối máy chủ</td></tr>';
    }
}

// 3. Phân trang Phim
function renderMoviePagination(totalPages, currentPage) {
    const paginationUl = document.getElementById('moviesPagination');
    let html = '';
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><a class="page-link bg-dark text-light border-secondary" href="#" onclick="changeMoviePage(${currentPage - 1})">Trước</a></li>`;
    for (let i = 1; i <= totalPages; i++) {
        const activeClass = currentPage === i ? 'active' : '';
        const btnStyle = currentPage === i ? 'bg-primary border-primary text-light' : 'bg-dark text-light border-secondary';
        html += `<li class="page-item ${activeClass}"><a class="page-link ${btnStyle}" href="#" onclick="changeMoviePage(${i})">${i}</a></li>`;
    }
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><a class="page-link bg-dark text-light border-secondary" href="#" onclick="changeMoviePage(${currentPage + 1})">Sau</a></li>`;
    paginationUl.innerHTML = html;
}

window.changeMoviePage = function(page) {
    movieCurrentPage = page;
    loadMovies(localStorage.getItem('token'), movieCurrentPage, movieSearchQuery);
}

// 4. Live Search Phim
document.getElementById('movieSearchInput').addEventListener('input', function(e) {
    if (movieSearchTimeout) clearTimeout(movieSearchTimeout);
    movieSearchTimeout = setTimeout(() => {
        movieSearchQuery = e.target.value;
        movieCurrentPage = 1;
        loadMovies(localStorage.getItem('token'), movieCurrentPage, movieSearchQuery);
    }, 300);
});

// 5. Modal Thêm/Sửa Phim (ĐÃ NÂNG CẤP)
window.prepareAddMovieModal = function() {
    document.getElementById('movieModalTitle').innerText = 'Thêm Phim Mới';
    document.getElementById('movieForm').reset();
    document.getElementById('editMovieId').value = '';

    const modal = bootstrap.Modal.getInstance(document.getElementById('movieModal')) || new bootstrap.Modal(document.getElementById('movieModal'));
    modal.show();
};

window.prepareEditMovieModal = function(id) {
    // Tự động tìm phim trong kho dựa vào ID
    const movie = currentMoviesList.find(m => m.movieId === id);
    if (!movie) return;

    document.getElementById('movieModalTitle').innerText = 'Sửa Phim #' + id;
    document.getElementById('editMovieId').value = id;

    // Đổ toàn bộ dữ liệu vào Form
    document.getElementById('movieTitle').value = movie.title || '';
    document.getElementById('movieGenres').value = movie.genres || '';
    document.getElementById('movieReleaseYear').value = movie.release_year || '';
    document.getElementById('movieRuntime').value = movie.runtime || '';
    document.getElementById('movieImdb').value = movie.imdb_rating || '';
    document.getElementById('movieDirector').value = movie.director || '';
    document.getElementById('movieCast').value = movie.cast || '';
    document.getElementById('moviePoster').value = movie.poster_url || '';
    document.getElementById('movieBackdrop').value = movie.backdrop_url || '';
    document.getElementById('movieDescription').value = movie.description || '';

    const modal = bootstrap.Modal.getInstance(document.getElementById('movieModal')) || new bootstrap.Modal(document.getElementById('movieModal'));
    modal.show();
};

document.getElementById('saveMovieBtn').addEventListener('click', async () => {
    const form = document.getElementById('movieForm');
    if (!form.checkValidity()) return form.reportValidity();

    const movieId = document.getElementById('editMovieId').value;
    const isEdit = movieId !== '';
    const token = localStorage.getItem('token');

    // Gói toàn bộ dữ liệu form thành Object JSON
    const payload = {
        title: document.getElementById('movieTitle').value,
        genres: document.getElementById('movieGenres').value,
        release_year: document.getElementById('movieReleaseYear').value ? parseInt(document.getElementById('movieReleaseYear').value) : null,
        runtime: document.getElementById('movieRuntime').value ? parseInt(document.getElementById('movieRuntime').value) : null,
        imdb_rating: document.getElementById('movieImdb').value ? parseFloat(document.getElementById('movieImdb').value) : null,
        director: document.getElementById('movieDirector').value || null,
        cast: document.getElementById('movieCast').value || null,
        poster_url: document.getElementById('moviePoster').value || null,
        backdrop_url: document.getElementById('movieBackdrop').value || null,
        description: document.getElementById('movieDescription').value || null
    };

    const url = isEdit ? `${API_URL}/admin/movies/${movieId}` : `${API_URL}/admin/movies`;
    const method = isEdit ? 'PUT' : 'POST';

    const btn = document.getElementById('saveMovieBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang lưu...';
    btn.disabled = true;

    try {
        const response = await fetch(url, {
            method: method, headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('movieModal')).hide();
            form.reset();
            loadMovies(token, movieCurrentPage, movieSearchQuery);
        } else {
            const err = await response.json();
            alert("Lỗi: " + (err.detail || "Không thể lưu phim!"));
        }
    } catch (error) {
        alert("Lỗi kết nối máy chủ!");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

// 6. Ẩn/Hiện Phim
window.toggleMovieStatus = async function(movieId) {
    if (!confirm('Bạn có chắc muốn Ẩn/Hiện bộ phim này khỏi trang chủ?')) return;
    const token = localStorage.getItem('token');
    try {
        const response = await fetch(`${API_URL}/admin/movies/${movieId}/toggle`, {
            method: 'PATCH', headers: {'Authorization': 'Bearer ' + token}
        });
        if (response.ok) loadMovies(token, movieCurrentPage, movieSearchQuery);
    } catch (error) { console.error(error); }
}