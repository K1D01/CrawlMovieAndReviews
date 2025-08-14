from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import re
from selenium.common.exceptions import NoSuchElementException

# Khởi tạo trình duyệt
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Đọc file phim
df_all = pd.read_csv("film/phim_dang_chieu_test_old.csv")

# Crawl đánh giá phim
all_reviews = []
for index, row in df_all.iterrows():
    film_title = row["film"]
    film_link = row["Link"]
    review_link = film_link.replace("/phim/", "/review/")

    driver.get(review_link)
    time.sleep(2)

    while True:
        try:
            view_more_button = driver.find_element(By.CSS_SELECTOR, "a.btn-view-more")
            style_attr = view_more_button.get_attribute("style")
            if "display: none" not in style_attr:
                print("[INFO] Click nút Xem thêm")
                driver.execute_script("arguments[0].click();", view_more_button)
                time.sleep(2)
            else:
                print("[INFO] Nút 'Xem thêm' không hiển thị.")
                break
        except NoSuchElementException:
            print("[INFO] Không tìm thấy nút 'Xem thêm'.")
            break
        try:
            # Kiểm tra đã đến cuối danh sách chưa
            end_element = driver.find_element(By.CSS_SELECTOR, "p.infinite-scroll-last")
            end_style = end_element.get_attribute("style")
            if end_style is None or end_style.strip() == "" or "display: none" not in end_style:
                print("[INFO] Đã đến cuối nội dung đánh giá.")
                break
        except NoSuchElementException:
            # Nếu không tìm thấy phần tử báo hết thì tiếp tục
            pass



        # Đợi loading nếu có
        try:
            loading = driver.find_element(By.CSS_SELECTOR, "div.infinite-scroll-request")
            while loading.is_displayed():
                print("[INFO] Đang loading thêm nội dung...")
                time.sleep(1)
        except:
            pass

    review_blocks = driver.find_elements(By.CSS_SELECTOR, "div.card.card-sm.article.mb-3")
    for block in review_blocks:
        try:
            reveal_btn = block.find_element(By.CSS_SELECTOR, "a.btn-reveal-spoiler")
            driver.execute_script("arguments[0].click();", reveal_btn)
            time.sleep(0.1)
        except:
            pass

        try:
            user = block.find_element(By.CSS_SELECTOR, "h4.card-title a").text.strip()
        except:
            user = ""

        try:
            score_raw = block.find_element(By.CSS_SELECTOR, "h4.card-title span").text
            score_match = re.findall(r'\d+', score_raw)
            score = score_match[0] if score_match else ""
        except:
            score = ""

        try:
            content = block.find_element(By.CSS_SELECTOR, "div.review-content").text.strip()
        except:
            content = ""

        if content:
            all_reviews.append({
                "film": film_title,
                "user": user,
                "score": score,
                "content": content
            })

# Xuất file đánh giá phim
pd.DataFrame(all_reviews).to_csv("review/danh_gia_phim.csv", index=False, encoding="utf-8-sig")
print("📦Đã xuất file đánh giá phim!")

# Kết thúc
driver.quit()
