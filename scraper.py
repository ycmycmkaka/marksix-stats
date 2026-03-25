import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def scrape_marksix_data():
    all_draws = []
    
    # 🌟 救星降臨：直接攻入你搵到嘅台灣無防護資料庫
    urls = [
        "https://www.pilio.idv.tw/ltohk/list.asp", # 最新 50 期
        "https://www.pilio.idv.tw/ltohk/list.asp?year=2026",
        "https://www.pilio.idv.tw/ltohk/list.asp?year=2025",
        "https://www.pilio.idv.tw/ltohk/list.asp?year=2024"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for url in urls:
        print(f"📡 嘗試潛入台灣彩票資料庫: {url[-15:]}...")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            # 台灣網頁有時會用 Big5 編碼，確保中文字同符號唔會變亂碼
            resp.encoding = resp.apparent_encoding 
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for row in soup.find_all('tr'):
                    # 抽出一行入面所有嘅文字
                    row_text = row.get_text(" ", strip=True)
                    
                    # 🌟 智能日期辨識 (支援 2026/03/24, 2026-03-24, 或者 2026年3月24日)
                    date_match = re.search(r'202[4-9][-/年]\d{1,2}[-/月]\d{1,2}', row_text)
                    
                    if date_match:
                        raw_date = date_match.group(0)
                        # 清洗日期格式變成 YYYY-MM-DD
                        clean_date = re.sub(r'[年/]', '-', raw_date)
                        clean_date = re.sub(r'月|日', '', clean_date)
                        
                        # 將 2024-3-4 變成 2024-03-04 方便排序
                        try:
                            d_obj = datetime.strptime(clean_date, "%Y-%m-%d")
                            clean_date = d_obj.strftime("%Y-%m-%d")
                        except: pass
                        
                        # 🌟 智能號碼辨識：抽出所有 1 到 49 嘅數字
                        nums = [int(x) for x in re.findall(r'\b\d{1,2}\b', row_text) if 1 <= int(x) <= 49]
                        
                        # 確保號碼唔重複，因為有期數或者其他雜質
                        unique_nums = []
                        for n in nums:
                            if n not in unique_nums: unique_nums.append(n)
                            
                        # 如果抽到 7 個或者以上嘅有效波 (頭 6 個通常係主波，第 7 個係特號)
                        if len(unique_nums) >= 7:
                            # 由於 Pilio 網頁排版，特號通常係最後嗰粒波
                            main_balls = sorted(unique_nums[:6])
                            special_ball = unique_nums[6]
                            
                            all_draws.append({
                                'date': clean_date,
                                'n1': main_balls[0], 'n2': main_balls[1], 'n3': main_balls[2],
                                'n4': main_balls[3], 'n5': main_balls[4], 'n6': main_balls[5],
                                'special': special_ball
                            })
                print("   ✅ 成功讀取本頁數據！")
        except Exception as e:
            print(f"   ⚠️ 失敗: {e}")

    df = pd.DataFrame(all_draws)
    if not df.empty:
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        # 剷走重複日期，確保乾淨，然後由舊至新排列
        return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
    return pd.DataFrame()

def calculate_metrics(df):
    if df.empty: return df
    prev_numbers = set()
    results = []
    
    for _, row in df.iterrows():
        # 只用 6 個主波嚟計走勢
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
    print("🚀 啟動 香港六合彩 (Pilio 專攻版) 爬蟲...")
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
