import pandas as pd
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# 新資料來源：lottery.hk
# 每年一頁，抓最近 15 年
HISTORY_YEARS = 15
SOURCE_URL = "https://lottery.hk/en/mark-six/results/{year}"


def extract_draws_from_page(page, year):
    """從 lottery.hk 某一年的 archive 頁抽出六合彩結果。"""
    page_draws = []

    # Archive 頁以 table rows 顯示每一期：
    # Draw Number / Draw Date / 7 balls
    rows = page.locator("table tr")
    row_count = rows.count()

    for i in range(row_count):
        try:
            text = rows.nth(i).inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        # 日期格式：DD/MM/YYYY
        date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
        if not date_match:
            continue

        date_raw = date_match.group(1)

        # 只在日期之後抽號碼，
        # 避免把 draw number（例如 26/095）當成開獎號碼
        tail = text[date_match.end():]

        nums = [
            int(x)
            for x in re.findall(
                r"(?<![\d/])(?:[1-9]|[1-4]\d)(?![\d/])",
                tail
            )
        ]

        # 一期應該有 6 個主號碼 + 1 個特別號
        if len(nums) < 7:
            continue

        nums = nums[:7]
        main_nums = nums[:6]
        special = nums[6]

        # 基本資料驗證
        if len(set(main_nums)) != 6:
            continue

        if not all(1 <= n <= 49 for n in nums):
            continue

        try:
            date_obj = datetime.strptime(date_raw, "%d/%m/%Y")
        except ValueError:
            continue

        # 防止頁面混入其他年份資料
        if date_obj.year != year:
            continue

        sorted_nums = sorted(main_nums)

        page_draws.append({
            "date": date_obj.strftime("%Y-%m-%d"),
            "n1": sorted_nums[0],
            "n2": sorted_nums[1],
            "n3": sorted_nums[2],
            "n4": sorted_nums[3],
            "n5": sorted_nums[4],
            "n6": sorted_nums[5],
            "special": special,
        })

    return page_draws


def extract_draws_from_body_fallback(page, year):
    """
    如果網站之後改咗 table 結構，
    改用整頁文字做 fallback。
    """

    try:
        text = page.locator("body").inner_text()
    except Exception:
        return []

    page_draws = []

    # 逐個 draw block 抽資料，例如：
    #
    # 26/095
    # 29/08/2026
    # 4 7 8 11 26 30 42

    blocks = re.finditer(
        r"\b\d{2}/\d{3}\b(?P<block>.*?)(?=\b\d{2}/\d{3}\b|\Z)",
        text,
        flags=re.S,
    )

    for match in blocks:
        block = match.group("block")

        date_match = re.search(
            r"\b(\d{2}/\d{2}/\d{4})\b",
            block
        )

        if not date_match:
            continue

        date_raw = date_match.group(1)
        tail = block[date_match.end():]

        nums = [
            int(x)
            for x in re.findall(
                r"(?<![\d/])(?:[1-9]|[1-4]\d)(?![\d/])",
                tail
            )
        ]

        if len(nums) < 7:
            continue

        nums = nums[:7]

        main_nums = nums[:6]
        special = nums[6]

        if len(set(main_nums)) != 6:
            continue

        if not all(1 <= n <= 49 for n in nums):
            continue

        try:
            date_obj = datetime.strptime(
                date_raw,
                "%d/%m/%Y"
            )
        except ValueError:
            continue

        if date_obj.year != year:
            continue

        sorted_nums = sorted(main_nums)

        page_draws.append({
            "date": date_obj.strftime("%Y-%m-%d"),
            "n1": sorted_nums[0],
            "n2": sorted_nums[1],
            "n3": sorted_nums[2],
            "n4": sorted_nums[3],
            "n5": sorted_nums[4],
            "n6": sorted_nums[5],
            "special": special,
        })

    return page_draws


def scrape_marksix_data():

    all_draws = []

    current_year = datetime.now().year

    years = list(
        range(
            current_year,
            current_year - HISTORY_YEARS,
            -1
        )
    )

    print("🚀 啟動 Playwright 抽六合彩資料...")
    print("🌐 新資料來源: lottery.hk")
    print(f"📚 抓取年份: {years[-1]} - {years[0]}")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/122.0.0.0 "
                "Safari/537.36"
            ),
            locale="en-US",
        )

        page = context.new_page()

        for year in years:

            url = SOURCE_URL.format(
                year=year
            )

            print(
                f"📡 讀取 {year}: {url}"
            )

            try:

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(1500)

                status = (
                    response.status
                    if response
                    else "unknown"
                )

                print(
                    f"   HTTP status: {status}"
                )

                if (
                    response
                    and response.status >= 400
                ):

                    print(
                        f"   ⚠️ {year} 頁面 "
                        f"HTTP {response.status}，跳過"
                    )

                    continue

                # 第一種方法：
                # 直接讀 table
                page_draws = (
                    extract_draws_from_page(
                        page,
                        year
                    )
                )

                # 如果 table parser 失敗，
                # 自動嘗試整頁文字 parser
                if not page_draws:

                    print(
                        "   ↪️ table parser 搵唔到資料，"
                        "嘗試 fallback parser..."
                    )

                    page_draws = (
                        extract_draws_from_body_fallback(
                            page,
                            year
                        )
                    )

                if page_draws:

                    print(
                        f"   ✅ 成功搵到 "
                        f"{len(page_draws)} 期資料"
                    )

                    all_draws.extend(
                        page_draws
                    )

                else:

                    title = page.title()

                    body_preview = (
                        page
                        .locator("body")
                        .inner_text()[:500]
                        .replace("\n", " | ")
                    )

                    print(
                        f"   ⚠️ {year} "
                        "搵唔到有效資料"
                    )

                    print(
                        f"   🏷️ Page title: "
                        f"{title}"
                    )

                    print(
                        f"   📝 Body preview: "
                        f"{body_preview}"
                    )

            except Exception as e:

                print(
                    f"   ⚠️ {year} "
                    f"讀取失敗: {e}"
                )

        browser.close()

    df = pd.DataFrame(
        all_draws
    )

    if df.empty:
        return pd.DataFrame()

    df["date_obj"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date_obj"]
    )

    # 防止重複期數
    df = df.drop_duplicates(
        subset=["date"]
    )

    # 先由舊至新排列，
    # 因為下面要計「上期重複號碼」
    df = df.sort_values(
        "date_obj",
        ascending=True
    )

    return df


def calculate_metrics(df):

    if df.empty:
        return df

    prev_numbers = set()
    results = []

    for _, row in df.iterrows():

        record = row.to_dict()

        nums = [
            int(record[f"n{i}"])
            for i in range(1, 7)
        ]

        # =========================
        # 奇偶比例
        # =========================

        odd_count = sum(
            1
            for n in nums
            if n % 2 != 0
        )

        even_count = sum(
            1
            for n in nums
            if n % 2 == 0
        )

        record["odd_even"] = (
            f"{odd_count}單 "
            f"{even_count}雙"
        )

        # =========================
        # 連續號碼
        # =========================

        consec_count = 0

        for i in range(
            len(nums) - 1
        ):

            if (
                nums[i + 1]
                - nums[i]
                == 1
            ):
                consec_count += 1

        record["consecutive"] = (
            f"{consec_count} 個連續"
        )

        # =========================
        # 與上一期重複號碼
        # =========================

        curr_set = set(nums)

        if prev_numbers:

            intersect = sorted(
                list(
                    curr_set.intersection(
                        prev_numbers
                    )
                )
            )

            if len(intersect) > 0:

                nums_str = ",".join(
                    map(str, intersect)
                )

                record["repeats"] = (
                    f"{len(intersect)}個 "
                    f"({nums_str})"
                )

            else:

                record["repeats"] = "0個"

        else:

            record["repeats"] = "0個"

        prev_numbers = curr_set

        # =========================
        # 分區
        #
        # Zone 1 = 1-10
        # Zone 2 = 11-20
        # Zone 3 = 21-30
        # Zone 4 = 31-40
        # Zone 5 = 41-49
        # =========================

        zones = sorted(
            set(
                (n - 1) // 10 + 1
                for n in nums
            )
        )

        record["zone"] = (
            f"{len(zones)}個區 "
            f"({','.join(map(str, zones))})"
        )

        results.append(
            record
        )

    final_df = pd.DataFrame(
        results
    )

    # 網站顯示時最新一期放最上面
    final_df = final_df.sort_values(
        "date_obj",
        ascending=False
    )

    final_df["date"] = (
        final_df["date_obj"]
        .dt
        .strftime("%Y-%m-%d")
    )

    return final_df


def main():

    raw_df = scrape_marksix_data()

    if raw_df.empty:

        print(
            "❌ 抽唔到任何資料"
        )

        raise SystemExit(1)

    final_df = calculate_metrics(
        raw_df
    )

    cols = [
        "date",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "special",
        "odd_even",
        "consecutive",
        "repeats",
        "zone"
    ]

    final_df[cols].to_csv(
        "data.csv",
        index=False,
        encoding="utf-8-sig"
    )

    newest = final_df.iloc[0]

    newest_nums = [
        int(newest[f"n{i}"])
        for i in range(1, 7)
    ]

    print(
        f"✅ 成功寫入 "
        f"{len(final_df)} 期大數據 "
        f"到 data.csv"
    )

    print(
        f"🆕 最新一期: "
        f"{newest['date']} | "
        f"主號碼 "
        f"{','.join(map(str, newest_nums))} | "
        f"特別號 "
        f"{int(newest['special'])}"
    )


if __name__ == "__main__":
    main()
