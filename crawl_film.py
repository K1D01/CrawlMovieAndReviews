from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
from datetime import datetime
import os
import re  

# Khởi tạo trình duyệt
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 1. Crawl phim ĐANG CHIẾU
driver.get("https://moveek.com/dang-chieu/")
time.sleep(2)
film_items = driver.find_elements(By.CSS_SELECTOR, "div.item")
film_now_showing = []
film_now_showing_links = set()

for item in film_items:
    film = item.find_element(By.CSS_SELECTOR, "h3.text-truncate.h4.mb-1 a").text.strip()
    film_link = item.find_element(By.CSS_SELECTOR, "h3.text-truncate.h4.mb-1 a").get_attribute("href")

    # Chuẩn hóa link về dạng https://moveek.com/phim/slug
    film_link = re.sub(r"https://moveek\.com/(lich-chieu|phim)/([^/?#]+)/?.*", r"https://moveek.com/phim/\2", film_link)

    film_now_showing.append({
        "film": film,
        "Link": film_link,
        "state": "now_showing",
        "stop_date": "NA"
    })
    film_now_showing_links.add(film_link)

# 2. Crawl phim SẮP CHIẾU (chỉ lấy phim chưa chiếu)
driver.get("https://moveek.com/sap-chieu/")
time.sleep(2)
film_items = driver.find_elements(By.CSS_SELECTOR, "div.item")
film_coming_soon = []

for item in film_items:
    film = item.find_element(By.CSS_SELECTOR, "h3.text-truncate.h4.mb-1 a").text.strip()
    film_link = item.find_element(By.CSS_SELECTOR, "h3.text-truncate.h4.mb-1 a").get_attribute("href")

    film_link = re.sub(r"https://moveek\.com/(lich-chieu|phim)/([^/?#]+)/?.*", r"https://moveek.com/phim/\2", film_link)

    if film_link not in film_now_showing_links:
        film_coming_soon.append({
            "film": film,
            "Link": film_link,
            "state": "coming_soon",
            "stop_date": "NA"
        })

# 3. So sánh với file cũ để phát hiện phim ĐÃ CHIẾU
film_stopped = []
if os.path.exists("phim_dang_chieu_test_old.csv"):
    df_old = pd.read_csv("phim_dang_chieu_test_old.csv")

    # Chuẩn hóa lại các link trong file cũ
    df_old["Link"] = df_old["Link"].apply(
        lambda x: re.sub(r"https://moveek\.com/(lich-chieu|phim)/([^/?#]+)/?.*", r"https://moveek.com/phim/\2", x) 
        if isinstance(x, str) else x
    )

    old_links = set(df_old["Link"])
    gone_links = old_links - film_now_showing_links

    if gone_links:
        df_gone = df_old[df_old["Link"].isin(gone_links)].copy()
        df_gone["state"] = "stopped"
        df_gone["stop_date"] = datetime.now().strftime("%Y-%m-%d")

        if "Tên phim" in df_gone.columns:
            df_gone = df_gone.rename(columns={"Tên phim": "film"})

        if "id_film" in df_gone.columns:
            df_gone = df_gone.drop(columns=["id_film"])

        required_cols = ["film", "Link", "state", "stop_date"]
        for col in required_cols:
            if col not in df_gone.columns:
                df_gone[col] = "NA"

        film_stopped = df_gone[required_cols].to_dict("records")
else:
    print("Chưa có file dữ liệu phim đang chiếu cũ để so sánh phim đã chiếu.")

# 4. Gộp tất cả vào 1 file tổng và tạo id số tự tăng
all_films = film_now_showing + film_coming_soon + film_stopped
df_all = pd.DataFrame(all_films)
df_all.insert(0, "id_film", range(1, len(df_all) + 1))
df_all.to_csv("film/phim_tong_hop.csv", index=False, encoding="utf-8-sig")
print("✅ Đã lưu file phim_tong_hop.csv với đường dẫn chuẩn hóa!")

# 5. Lưu lại file hôm nay thành file cũ để lần sau so sánh
pd.DataFrame(film_now_showing).to_csv("film/phim_dang_chieu_test_old.csv", index=False, encoding="utf-8-sig")
print("✅ Đã cập nhật file phim_dang_chieu_test_old.csv cho lần so sánh tiếp theo.")

films_detail = []
for index, row in df_all.iterrows():
    film = row["film"]
    link = row["Link"]
    driver.get(link)
    time.sleep(2)

    description = ""
    genre = ""
    release_date = ""
    duration = ""
    age_rating = ""
    satisfaction_score = ""
    cast = ""
    director = ""

    try:
        description = driver.find_element(By.CLASS_NAME, "mb-3.text-justify").text.strip()
    except:
        pass

    try:
        genre_text = driver.find_element(By.CSS_SELECTOR, ".mb-0.text-muted.text-truncate").text.strip()
        if "-" in genre_text:
            genre = genre_text.split("-", 1)[-1].strip()
        else: 
            genre = genre_text
    except:
        pass

    try:
        release_date = driver.find_element(By.XPATH, "//span[contains(text(), 'Khởi chiếu')]/parent::strong/following-sibling::br/following-sibling::span").text.strip()
    except:
        pass

    try:
        duration = driver.find_element(By.XPATH, "//span[contains(text(), 'Thời lượng')]/parent::strong/following-sibling::br/following-sibling::span").text.strip()
    except:
        pass

    try:
        age_rating = driver.find_element(By.XPATH, "//span[contains(text(), 'Giới hạn tuổi')]/parent::strong/following-sibling::br/following-sibling::span").text.strip()
    except:
        pass

    try:
        satisfaction_score = driver.find_element(By.CSS_SELECTOR, "a.text-white").text.strip()
    except:
        pass

    try:
        cast_tags = driver.find_elements(By.XPATH, "//p[strong[contains(text(), 'Diễn viên')]]/span/a")
        cast = ", ".join([tag.text.strip() for tag in cast_tags])
    except:
        pass

    try:
        director_tags = driver.find_elements(By.XPATH, "//p[strong[contains(text(), 'Đạo diễn')]]/span/a")
        director = ", ".join([tag.text.strip() for tag in director_tags])
    except:
        pass

    films_detail.append({
        "film": film,
        "link": link,
        "genre": genre,
        "release_date": release_date,
        "duration": duration,
        "age_rating": age_rating,
        "satisfaction_score": satisfaction_score,
        "cast": cast,
        "director": director,
        "description": description
    })

# Xuất file chi tiết
pd.DataFrame(films_detail).to_csv("film/phim_chi_tiet.csv", index=False, encoding="utf-8-sig")
print("📝 Đã ghi chi tiết phim vào phim_chi_tiet.csv")

# Kết thúc
driver.quit()

