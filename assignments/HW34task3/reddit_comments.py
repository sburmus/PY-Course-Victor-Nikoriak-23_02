import requests
import json
import threading

SUBREDDIT = "python"
URL = "https://api.pushshift.io/reddit/comment/search/"
OUTPUT_FILE = f"{SUBREDDIT}_comments.json"

all_comments = []
lock = threading.Lock()

def fetch_comments(before=None):
    params = {"subreddit": SUBREDDIT, "size": 100}
    if before:
        params["before"] = before

    response = requests.get(URL, params=params)
    if response.status_code == 200:
        data = response.json().get("data", [])
        with lock:
            all_comments.extend(data)
        # якщо є ще коментарі — запускаємо наступний потік
        if data:
            last_time = data[-1]["created_utc"]
            thread = threading.Thread(target=fetch_comments, args=(last_time,))
            thread.start()
            thread.join()

def main():
    # стартовий потік
    fetch_comments()

    # сортуємо коментарі за часом
    sorted_comments = sorted(all_comments, key=lambda x: x["created_utc"])

    # зберігаємо у файл
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_comments, f, ensure_ascii=False, indent=2)

    print(f"✅ Збережено {len(sorted_comments)} коментарів у {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

