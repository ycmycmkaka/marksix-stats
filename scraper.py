import re
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError, sync_playwright

SOURCE_URL = "https://lottery.hk/en/mark-six/results/{year}"
CSV_PATH = Path(__file__).resolve().with_name("data.csv")
HISTORY_YEARS = 15
BALL_COLUMNS = [f"n{i}" for i in range(1, 7)]
DRAW_COLUMNS = ["date", *BALL_COLUMNS, "special"]
CSV_COLUMNS = [*DRAW_COLUMNS, "odd_even", "consecutive", "repeats", "zone"]
DRAW_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")


def extract_draws(html, year):
    draws = []
    for row in BeautifulSoup(html, "html.parser").select("table tr"):
        cells = row.find_all("td", recursive=False)
        for date_cell, balls_cell in zip(cells, cells[1:]):
            raw_date = date_cell.get_text(strip=True)
            if not DRAW_DATE.fullmatch(raw_date):
                continue

            try:
                draw_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
            except ValueError:
                continue

            numbers = [int(value) for value in re.findall(
                r"\b[0-9]{1,2}\b", balls_cell.get_text(" ", strip=True)
            )]
            if (
                draw_date.year != year
                or len(numbers) != 7
                or len(set(numbers)) != 7
                or not all(1 <= number <= 49 for number in numbers)
            ):
                continue

            draws.append(dict(zip(
                DRAW_COLUMNS, [draw_date.isoformat(), *sorted(numbers[:6]), numbers[6]]
            )))
            break

    return draws


def read_year(year):
    url = SOURCE_URL.format(year=year)
    print(f"讀取 {year}: {url}", flush=True)
    try:
        with urlopen(url, timeout=12) as response:
            draws = extract_draws(response.read(), year)
    except HTTPError as exc:
        raise RuntimeError(f"{year} 結果頁回傳 HTTP {exc.code}") from exc
    except (URLError, OSError) as exc:
        print(f"直接讀取逾時或連線失敗: {exc}", flush=True)
    else:
        if draws:
            return draws
        print(f"{year} 的 HTML 未找到有效結果，改用 Chromium。", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until="commit", timeout=15000)
            if response is None or not response.ok:
                status = response.status if response is not None else "無回應"
                raise RuntimeError(f"{year} Chromium 讀取結果頁失敗: {status}")

            # 等結果表出現，避免等待廣告等無關資源，並同時支援延後載入的表格。
            page.locator("table td").filter(has_text=DRAW_DATE).first.wait_for(
                state="attached", timeout=8000
            )
            draws = extract_draws(page.content(), year)
        except PlaywrightError as exc:
            raise RuntimeError(f"{year} Chromium 讀取結果頁失敗: {exc}") from exc
        finally:
            browser.close()

    if not draws:
        raise RuntimeError(f"{year} 結果頁未找到有效開獎資料")
    return draws


def read_existing_draws():
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=DRAW_COLUMNS)

    existing = pd.read_csv(CSV_PATH, encoding="utf-8-sig", usecols=DRAW_COLUMNS)
    existing = existing[DRAW_COLUMNS].copy()
    dates = pd.to_datetime(existing["date"], format="%Y-%m-%d", errors="raise")
    if dates.isna().any():
        raise ValueError("現有 data.csv 有空白日期")
    existing["date"] = dates.dt.strftime("%Y-%m-%d")
    return existing


def calculate_metrics(draws):
    records = []
    previous = set()

    for row in draws.to_dict("records"):
        numbers = [int(row[column]) for column in BALL_COLUMNS]
        current = set(numbers)
        repeats = sorted(current & previous)
        zones = sorted({(number - 1) // 10 + 1 for number in numbers})
        odd = sum(number % 2 for number in numbers)
        consecutive = sum(b - a == 1 for a, b in zip(numbers, numbers[1:]))

        row["odd_even"] = f"{odd}單 {6 - odd}雙"
        row["consecutive"] = f"{consecutive} 個連續"
        row["repeats"] = f"{len(repeats)}個"
        if repeats:
            row["repeats"] += f" ({','.join(map(str, repeats))})"
        row["zone"] = f"{len(zones)}個區 ({','.join(map(str, zones))})"
        records.append(row)
        previous = current

    return pd.DataFrame(records, columns=CSV_COLUMNS).iloc[::-1]


def write_csv(draws):
    with NamedTemporaryFile(dir=CSV_PATH.parent, delete=False) as handle:
        temporary_path = Path(handle.name)

    try:
        draws.to_csv(temporary_path, index=False, encoding="utf-8-sig")
        temporary_path.replace(CSV_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    existing = read_existing_draws()
    current_year = datetime.now(ZoneInfo("Asia/Hong_Kong")).year
    first_year = (
        current_year - HISTORY_YEARS + 1
        if existing.empty
        else min(current_year, int(existing["date"].max()[:4]))
    )

    fresh = []
    for year in range(current_year, first_year - 1, -1):
        draws = read_year(year)
        print(f"{year}: 讀到 {len(draws)} 期", flush=True)
        fresh.extend(draws)

    incoming = pd.DataFrame(fresh, columns=DRAW_COLUMNS)
    merged = pd.concat([existing, incoming], ignore_index=True)
    merged = merged.drop_duplicates("date", keep="last").sort_values("date")
    final = calculate_metrics(merged)
    write_csv(final)
    print(f"已更新 data.csv，共 {len(final)} 期。最新一期: {final.iloc[0]['date']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, PlaywrightError) as exc:
        print(f"更新失敗，保留現有 data.csv: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
