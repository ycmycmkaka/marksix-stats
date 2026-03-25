import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from playwright.sync_api import sync_playwright

def scrape_marksix_data():
    all_draws = []
    
    # 🌟 啟動【國家級黑客技巧】：真實瀏覽器模擬 (Playwright)
    print("🚀 啟動 香港六合彩 核武級 (Playwright 真瀏覽器) 破防爬蟲...")
    
    with sync_playwright() as p:
        # 打開一個隱形嘅 Chromium 瀏覽器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 目標：全球最大彩票庫
        urls = [
            "https://www.lotteryextreme.com/hong_kong/mark_six_results",
            "https://www.lotteryextreme.com/hong_kong/mark_six_results2"
        ]
        
        for url in urls:
            print(f"📡 駕駛真瀏覽器駛入: {url[-20:]}...")
            try:
                # 等待網頁完全 Load 完防禦系統解開 (networkidle)
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2) # 停 2 秒扮真人睇緊嘢
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                found_in_page = False
                for row in soup.find_all('tr'):
                    # 抄底一行文字
                    row_text = row.get_text(" ", strip=True)
                    # 認出 YYYY-MM-DD 格式日期
                    date_match = re.search(r'202[3-9]-[0-1]\d-[0-3]\d', row_text)
                    
                    if not date_match: continue
                        
                    # 🌟 ChatGPT 智能升級：先剷除日期，避免月/日(03/24)混入號碼！
                    clean_text = row_text.replace(date_match.group(0), " ")
                    
                    # 🌟 抽出 1 到 49 嘅數字 (用 word boundary \b 包住，防抽錯 part 號碼)
                    nums = [int(x) for x in re.findall(r'\b\d{1,2}\b', clean_text) if 1 <= int(x) <= 49]
                    
                    # 🌟 智能認證：只接受啱啱好有 7 個號碼 (6主+1特) 嘅行
                    if len(nums) == 7:
                        main_balls = sorted(nums[:6]) # 頭 6 個係主波，需要排序
                        special_ball = nums[6]       # 第 7 個係特別號碼
                        
                        all_draws.append({
                            'date': date_match.group(0),
                            'n1': main_balls[0], 'n2': main_balls[1], 'n3': main_balls[2],
                            'n4': main_balls[3], 'n5': main_balls[4], 'n6': main_balls[5],
                            'special': special_ball
                        })
                        found_in_page = True
                            
                if found_in_page:
                    print("   ✅ 成功利用 AI 邏輯突破防護罩，取得數據！")
            except Exception as e:
                print(f"   ⚠️ 失敗: {e}")
                
        browser.close()

    df = pd.DataFrame(all_draws)
    if not df.empty:
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        # 先由舊至新排列 (方便計走勢重複次數)
        df = df.sort_values('date_obj', ascending=True)
        # 剷走重複日期，由舊排到新
        return df.dropna(subset=['date_obj']).drop_duplicates('date_obj')
    return pd.DataFrame()

def calculate_metrics(df):
    """計晒所有單雙、連續、重複、分區數據"""
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
        
    # 計完，重新排返「最新至最舊」出 CSV 畀 Dashboard 用
    final_df = pd.DataFrame(results).sort_values('date_obj', ascending=False)
    final_df['date'] = final_df['date_obj'].dt.strftime('%Y-%m-%d')
    return final_df

def main():
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！成功寫入 {len(final_df)} 期無瑕疵六合彩數據。")
    else:
        print("❌ 警告：所有核武策略失敗！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
