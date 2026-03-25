import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from playwright.sync_api import sync_playwright

def scrape_marksix_data():
    all_draws = []
    
    print("🚀 啟動【核武級黑客技巧】：真實瀏覽器模擬 (Playwright)")
    
    # 啟動 Playwright 引擎
    with sync_playwright() as p:
        # 真正打開一個隱形嘅 Chromium 瀏覽器
        browser = p.chromium.launch(headless=True)
        # 扮成最普通嘅 Mac 機 Chrome 用戶，完美融入人群
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 目標：全球最大彩票庫 (用真瀏覽器硬爆 Cloudflare 防護)
        urls = [
            "https://www.lotteryextreme.com/hong_kong/mark_six_results",
            "https://www.lotteryextreme.com/hong_kong/mark_six_results2"
        ]
        
        for url in urls:
            print(f"📡 駕駛真瀏覽器駛入: {url[-20:]}...")
            try:
                # 🌟 必殺技：等待網絡靜止 (networkidle)！等佢防護罩解開，畫面 100% Load 完先郁手
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2) # 停 2 秒扮真人睇緊嘢
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                found_in_page = False
                for row in soup.find_all('tr'):
                    row_text = row.get_text(" ", strip=True)
                    # 搵 2026-03-24 呢種日期
                    date_match = re.search(r'202[3-9]-[0-1][0-9]-[0-3][0-9]', row_text)
                    
                    if date_match:
                        nums = [int(x) for x in re.findall(r'\b\d{1,2}\b', row_text) if 1 <= int(x) <= 49]
                        unique_nums = []
                        for n in nums:
                            if n not in unique_nums: unique_nums.append(n)
                            
                        if len(unique_nums) >= 7:
                            m_balls = sorted(unique_nums[:6])
                            all_draws.append({
                                'date': date_match.group(0),
                                'n1': m_balls[0], 'n2': m_balls[1], 'n3': m_balls[2],
                                'n4': m_balls[3], 'n5': m_balls[4], 'n6': m_balls[5],
                                'special': unique_nums[6]
                            })
                            found_in_page = True
                            
                if found_in_page:
                    print("   ✅ 成功突破防護罩，取得最新數據！")
            except Exception as e:
                print(f"   ⚠️ 讀取失敗: {e}")
                
        browser.close()

    df = pd.DataFrame(all_draws)
    if not df.empty:
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
    return pd.DataFrame()

def calculate_metrics(df):
    if df.empty: return df
    prev_numbers = set()
    results = []
    
    for _, row in df.iterrows():
        nums = [int(row[f'n{i}']) for i in range(1, 7)]
        row['odd_even'] = f"{sum(1 for n in nums if n%2!=0)}單 {sum(1 for n in nums if n%2==0)}雙"
        row['consecutive'] = "Yes" if any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)) else "No"
        
        curr_set = set(nums)
        row['repeats'] = len(curr_set.intersection(prev_numbers)) if prev_numbers else 0
        prev_numbers = curr_set
        
        zones = sorted(list(set([(n - 1) // 10 + 1 for n in nums])))
        row['zone'] = f"{len(zones)}個區 ({','.join(map(str, zones))})"
        results.append(row)
        
    final_df = pd.DataFrame(results).sort_values('date_obj', ascending=False)
    final_df['date'] = final_df['date_obj'].dt.strftime('%Y-%m-%d')
    return final_df

def main():
    print("🚀 啟動 香港六合彩 終極核武級 (Playwright 真瀏覽器) 爬蟲...")
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！成功寫入 {len(final_df)} 期六合彩數據。")
    else:
        print("❌ 警告：連核武器都失敗！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
