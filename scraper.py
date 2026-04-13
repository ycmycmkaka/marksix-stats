import pandas as pd
import re
from playwright.sync_api import sync_playwright

MAX_PAGES = 40
EMPTY_PAGE_STOP = 3

def scrape_marksix_data():
    all_draws = []
    print("🚀 啟動 Playwright 抽六合彩資料...")

    empty_streak = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for page_num in range(1, MAX_PAGES + 1):
            url = f"https://en.lottolyzer.com/history/hong-kong/mark-six/page/{page_num}/per-page/50/summary-view"
            print(f"📡 讀取第 {page_num} 頁: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

                text = page.locator("body").inner_text()
                found_in_page = False

                pattern = re.compile(
                    r'(\d{4}-\d{2}-\d{2})\s+'
                    r'((?:[1-4]\d|[1-9])(?:,(?:[1-4]\d|[1-9])){5})\s+'
                    r'([1-4]\d|[1-9])'
                )

                page_draws = []

                for m in pattern.finditer(text):
                    date_str = m.group(1)
                    main_nums = [int(x) for x in m.group(2).split(",")]
                    special = int(m.group(3))

                    if len(main_nums) == 6:
                        sorted_nums = sorted(main_nums)
                        page_draws.append({
                            "date": date_str,
                            "n1": sorted_nums[0],
                            "n2": sorted_nums[1],
                            "n3": sorted_nums[2],
                            "n4": sorted_nums[3],
                            "n5": sorted_nums[4],
                            "n6": sorted_nums[5],
                            "special": special
                        })
                        found_in_page = True

                if found_in_page:
                    print(f"   ✅ 成功搵到 {len(page_draws)} 期資料")
                    all_draws.extend(page_draws)
                    empty_streak = 0
                else:
                    print("   ⚠️ 呢頁搵唔到有效結果行")
                    empty_streak += 1

                if empty_streak >= EMPTY_PAGE_STOP:
                    print(f"⏹️ 已連續 {EMPTY_PAGE_STOP} 頁冇資料，停止繼續抓取")
                    break

            except Exception as e:
                print(f"   ⚠️ 讀取失敗 (可能超時): {e}")
                empty_streak += 1

                if empty_streak >= EMPTY_PAGE_STOP:
                    print(f"⏹️ 已連續 {EMPTY_PAGE_STOP} 頁失敗/冇資料，停止繼續抓取")
                    break

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

        odd_count = sum(1 for n in nums if n % 2 != 0)
        even_count = sum(1 for n in nums if n % 2 == 0)
        record["odd_even"] = f"{odd_count}單 {even_count}雙"

        consec_count = 0
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consec_count += 1
        record["consecutive"] = f"{consec_count} 個連續"

        curr_set = set(nums)
        if prev_numbers:
            intersect = sorted(list(curr_set.intersection(prev_numbers)))
            if len(intersect) > 0:
                nums_str = ",".join(map(str, intersect))
                record["repeats"] = f"{len(intersect)}個 ({nums_str})"
            else:
                record["repeats"] = "0個"
        else:
            record["repeats"] = "0個"

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
    cols = [
        "date", "n1", "n2", "n3", "n4", "n5", "n6",
        "special", "odd_even", "consecutive", "repeats", "zone"
    ]
    final_df[cols].to_csv("data.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 成功寫入 {len(final_df)} 期大數據到 data.csv")


if __name__ == "__main__":
    main()
