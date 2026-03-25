import pandas as pd
import re
import time
from playwright.sync_api import sync_playwright

def scrape_marksix_data():
    all_draws = []

    print("🚀 啟動 Playwright 抽六合彩資料 (完美 300 期大數據版)...")

    # 🌟 破案關鍵：Lottolyzer 預設每頁得 50 期，我哋直接叫佢連揭 6 頁！
    urls = [
        f"https://en.lottolyzer.com/history/hong-kong/mark-six/page/{i}/per-page/50/summary-view"
        for i in range(1, 7)
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for url in urls:
            print(f"📡 讀取第 {urls.index(url)+1} 頁: {url[-25:]}")
            try:
                # 畀充足時間佢 Load 歷史數據
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

                text = page.locator("body").inner_text()

                found_in_page = False

                # Lottolyzer 專用神級公式 (完美匹配)
                pattern2 = re.compile(
                    r'(\d{4}-\d{2}-\d{2})\s+'
                    r'((?:[1-9]|[1-4]\d)(?:,(?:[1-9]|[1-4]\d)){5})\s+'
                    r'([1-9]|[1-4]\d)'
                )

                for m in pattern2.finditer(text):
                    date_str = m.group(1)
                    main_nums = [int(x) for x in m.group(2).split(",")]
                    special = int(m.group(3))
                    if len(main_nums) == 6:
                        all_draws.append({
                            "date": date_str,
                            "n1": sorted(main_nums)[0], "n2": sorted(main_nums)[1], "n3": sorted(main_nums)[2],
                            "n4": sorted(main_nums)[3], "n5": sorted(main_nums)[4], "n6": sorted(main_nums)[5],
                            "special": special
                        })
                        found_in_page = True

                if found_in_page:
                    print("   ✅ 成功搵到 50 期資料")
                else:
                    print("   ⚠️ 呢頁搵唔到有效結果行")

            except Exception as e:
                print(f"   ⚠️ 讀取失敗 (可能超時): {e}")

        browser.close()

    df = pd.DataFrame(all_draws)
    if df.empty:
        return pd.DataFrame()

    df["date_obj"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_obj"])
    # 剷除重複日子，排返舊至新畀下面計走勢
    df = df.drop_duplicates(subset=["date"]).sort_values("date_obj", ascending=True)
    return df


def calculate_metrics(df):
    if df.empty: return df
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

    # 計完走勢，排返最新到最舊畀網頁顯示
    final_df = pd.DataFrame(results).sort_values("date_obj", ascending=False)
    final_df["date"] = final_df["date_obj"].dt.strftime("%Y-%m-%d")
    return final_df


def main():
    raw_df = scrape_marksix_data()
    if raw_df.empty:
        print("❌ 抽唔到任何資料")
        raise SystemExit(1)

    final_df = calculate_metrics(raw_df)
    cols = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "special", "odd_even", "consecutive", "repeats", "zone"]
    final_df[cols].to_csv("data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 成功寫入 {len(final_df)} 期大數據到 data.csv")

if __name__ == "__main__":
    main()
