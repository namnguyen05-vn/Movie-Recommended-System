# ==========================================
# PHẦN 1: KHAI BÁO THƯ VIỆN (IMPORTS)
# ==========================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
# Bổ sung thêm Dropout và EarlyStopping
from tensorflow.keras.layers import Input, Embedding, Flatten, Concatenate, Dense, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping

# ==========================================
# PHẦN 2: CHUẨN BỊ VÀ TIỀN XỬ LÝ DỮ LIỆU
# ==========================================
print("Đang tải dữ liệu...")
df = pd.read_csv('ratings.csv')

user_encoder = LabelEncoder()
movie_encoder = LabelEncoder()

df['user_encoded'] = user_encoder.fit_transform(df['userId'])
df['movie_encoded'] = movie_encoder.fit_transform(df['movieId'])

num_users = df['user_encoded'].nunique()
num_movies = df['movie_encoded'].nunique()

X = df[['user_encoded', 'movie_encoded']].values
y = df['rating'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

X_train_user = X_train[:, 0]
X_train_movie = X_train[:, 1]
X_test_user = X_test[:, 0]
X_test_movie = X_test[:, 1]

# ==========================================
# PHẦN 3: XÂY DỰNG MÔ HÌNH (CÓ CHỐNG OVERFITTING)
# ==========================================
print("\nĐang khởi tạo cấu trúc mô hình AI...")
embedding_size = 50

user_input = Input(shape=(1,), name='user_input')
movie_input = Input(shape=(1,), name='movie_input')

user_embedding = Embedding(input_dim=num_users, output_dim=embedding_size, name='user_embedding')(user_input)
movie_embedding = Embedding(input_dim=num_movies, output_dim=embedding_size, name='movie_embedding')(movie_input)

user_vec = Flatten(name='flatten_user')(user_embedding)
movie_vec = Flatten(name='flatten_movie')(movie_embedding)

concat = Concatenate(name='user_movie_combined')([user_vec, movie_vec])

# Thêm Dropout(0.2) nghĩa là tắt ngẫu nhiên 20% nơ-ron sau mỗi lớp
fc1 = Dense(128, activation='relu', name='hidden_1')(concat)
drop1 = Dropout(0.2)(fc1)

fc2 = Dense(64, activation='relu', name='hidden_2')(drop1)
drop2 = Dropout(0.2)(fc2)

fc3 = Dense(32, activation='relu', name='hidden_3')(drop2)
drop3 = Dropout(0.2)(fc3)

output = Dense(1, name='predicted_rating')(drop3)

model = Model(inputs=[user_input, movie_input], outputs=output)
model.compile(optimizer='adam', loss='mean_squared_error')

# ==========================================
# PHẦN 4: HUẤN LUYỆN MÔ HÌNH VÀ ĐÁNH GIÁ
# ==========================================
print("\nBắt đầu quá trình huấn luyện AI (Training)...")

# Cài đặt Early Stopping: Theo dõi 'val_loss', dừng nếu không cải thiện sau 2 vòng (patience=2)
# Khôi phục trọng số tốt nhất (restore_best_weights=True)
early_stop = EarlyStopping(
    monitor='val_loss',
    patience=2,
    restore_best_weights=True,
    verbose=1
)

# Thêm callbacks=[early_stop] vào hàm fit
history = model.fit(
    x=[X_train_user, X_train_movie],
    y=y_train,
    batch_size=128,
    epochs=15, # Có thể tự tin tăng lên 15 vòng vì đã có Early Stopping lo việc dừng sớm
    validation_data=([X_test_user, X_test_movie], y_test),
    callbacks=[early_stop],
    verbose=1
)

# Đánh giá chỉ số RMSE
print("\nĐang tính toán chỉ số RMSE...")
test_loss = model.evaluate(x=[X_test_user, X_test_movie], y=y_test, verbose=0)
rmse = np.sqrt(test_loss)

print(f"\n==========================================")
print(f"🎯 KẾT QUẢ SAU KHI NÂNG CẤP: RMSE = {rmse:.4f}")
print(f"==========================================")


# Lưu mô hình lại để dùng cho giao diện Web
model.save('movie_recommender_model.keras')
print("Đã lưu mô hình thành công vào file 'movie_recommender_model.keras'")