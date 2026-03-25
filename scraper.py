import pandas as pd
import re
import time
from playwright.sync_api import sync_playwright

def scrape_marksix_data():
    all_draws = []

    print("🚀 啟動 Playwright 抽六合彩資料...")

urls = [
        "https://www.lotteryextreme.com/marksix/results",
        "https://www.lotteryextreme.com/marksix/results2", # 歷史第 2 頁
        "https://www.lotteryextreme.com/marksix/results3", # 歷史第 3 頁
        "https://www.lotteryextreme.com/marksix/results4", # 歷史第 4 頁
        "https://en.lottolyzer.com/history/hong-kong/mark-six"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for url in urls:
            print(f"📡 讀取: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                text = page.locator("body").inner_text()
                print("---- 頁面頭 1000 字 ----")
                print(text[:1000])
                print("----------------------")

                # 方案 1：LotteryExtreme 格式
                # 例：24/03/2026 Tuesday (26/032)
                pattern1 = re.compile(
                    r'(\d{2}/\d{2}/\d{4})\s+\w+\s+\(\d{2}/\d{3}\).*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b.*?'
                    r'\b([1-9]|[1-4]\d)\b',
                    re.S
                )

                for m in pattern1.finditer(text):
                    date_str = m.group(1)
                    nums = [int(m.group(i)) for i in range(2, 9)]
                    all_draws.append({
                        "date": pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d"),
                        "n1": sorted(nums[:6])[0],
                        "n2": sorted(nums[:6])[1],
                        "n3": sorted(nums[:6])[2],
                        "n4": sorted(nums[:6])[3],
                        "n5": sorted(nums[:6])[4],
                        "n6": sorted(nums[:6])[5],
                        "special": nums[6],
                    })

                # 方案 2：Lottolyzer 格式
                # 例：26/032 2026-03-24 6,9,22,26,44,49 7
                pattern2 = re.compile(
                    r'(\d{2}/\d{3})\s+'
                    r'(\d{4}-\d{2}-\d{2})\s+'
                    r'((?:[1-9]|[1-4]\d)(?:,(?:[1-9]|[1-4]\d)){5})\s+'
                    r'([1-9]|[1-4]\d)'
                )

                for m in pattern2.finditer(text):
                    date_str = m.group(2)
                    main_nums = [int(x) for x in m.group(3).split(",")]
                    special = int(m.group(4))
                    all_draws.append({
                        "date": date_str,
                        "n1": sorted(main_nums)[0],
                        "n2": sorted(main_nums)[1],
                        "n3": sorted(main_nums)[2],
                        "n4": sorted(main_nums)[3],
                        "n5": sorted(main_nums)[4],
                        "n6": sorted(main_nums)[5],
                        "special": special,
                    })

            except Exception as e:
                print(f"⚠️ 讀取失敗: {e}")

        browser.close()

    df = pd.DataFrame(all_draws)
    if df.empty:
        return pd.DataFrame()

    df["date_obj"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_obj"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date_obj", ascending=True)
    return df


def calculate_metrics(df):
    if df.empty:
        return df

    prev_numbers = set()
    results = []

    for _, row in df.iterrows():
        record = row.to_dict()
        nums = [int(record[f"n{i}"]) for i in range(1, 7)]

        record["odd_even"] = f"{sum(1 for n in nums if n % 2 != 0)}單 {sum(1 for n in nums if n % 2 == 0)}雙"
        record["consecutive"] = "Yes" if any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)) else "No"

        curr_set = set(nums)
        record["repeats"] = len(curr_set.intersection(prev_numbers)) if prev_numbers else 0
        prev_numbers = curr_set

        zones = sorted(set((n - 1) // 10 + 1 for n in nums))
        record["zone"] = f"{len(zones)}個區 ({','.join(map(str, zones))})"

        results.append(record)

    final_df = pd.DataFrame(results).sort_values("date_obj", ascending=False)
    final_df["date"] = final_df["date_obj"].dt.strftime("%Y-%m-%d")
    return final_df


def main():
    raw_df = scrape_marksix_data()

    if raw_df.empty:
        print("❌ 抽唔到任何資料")
        raise SystemExit(1)

    final_df = calculate_metrics(raw_df)
    cols = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "special",
            "odd_even", "consecutive", "repeats", "zone"]
    final_df[cols].to_csv("data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 成功寫入 {len(final_df)} 期數據到 data.csv")


if __name__ == "__main__":
    main()
