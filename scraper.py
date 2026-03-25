import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def scrape_marksix_data():
    all_draws = []
    
    # 🌟 策略：用 Proxy 隱藏身份，直接去 LotteryExtreme (全球彩票庫) 讀取純 HTML
    target_urls = [
        "https://www.lotteryextreme.com/hong_kong/mark_six_results",
        "https://www.lotteryextreme.com/hong_kong/mark_six_results2"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for target in target_urls:
        print(f"📡 準備抓取: {target[-20:]}...")
        encoded_url = urllib.parse.quote(target)
        
        # 3 條命：2 個 Proxy + 1 個直連
        proxy_urls = [
            f"https://api.allorigins.win/raw?url={encoded_url}",
            f"https://api.codetabs.com/v1/proxy/?quest={encoded_url}",
            target
        ]
        
        success = False
        for url in proxy_urls:
            print(f"   -> 嘗試連線: {url[:50]}...")
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                # 確保攞到嘅係正常網頁 (有 table)
                if resp.status_code == 200 and "<table" in resp.text.lower():
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for row in soup.find_all('tr'):
                        row_text = row.get_text(" ", strip=True)
                        
                        # 認出日期 (例如 2026-03-24)
                        date_match = re.search(r'202[3-9]-[0-1][0-9]-[0-3][0-9]', row_text)
                        if date_match:
                            # 抽出 1-49 嘅波
                            nums = [int(x) for x in re.findall(r'\b\d{1,2}\b', row_text) if 1 <= int(x) <= 49]
                            
                            unique_nums = []
                            for n in nums:
                                if n not in unique_nums: unique_nums.append(n)
                                
                            if len(unique_nums) >= 7:
                                m_balls = sorted(unique_nums[:6]) # 頭 6 個係主波
                                s_ball = unique_nums[6]          # 第 7 個係特別號碼
                                
                                all_draws.append({
                                    'date': date_match.group(0),
                                    'n1': m_balls[0], 'n2': m_balls[1], 'n3': m_balls[2],
                                    'n4': m_balls[3], 'n5': m_balls[4], 'n6': m_balls[5],
                                    'special': s_ball
                                })
                    if len(all_draws) > 0:
                        success = True
                        print("   ✅ 成功破解並讀取數據！")
                        break # 成功就跳出 proxy loop，去下一頁
            except Exception as e:
                print(f"   ⚠️ 失敗: {e}")
                
        if not success:
            print("   ❌ 呢頁所有方法都失敗。")

    df = pd.DataFrame(all_draws)
    if not df.empty:
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        # 剷走重複日期，由舊排到新
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
    print("🚀 啟動 香港六合彩 終極網頁破解版爬蟲...")
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！成功寫入 {len(final_df)} 期六合彩數據。")
    else:
        print("❌ 警告：搵唔到數據！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
