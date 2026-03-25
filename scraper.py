import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def scrape_marksix_data():
    all_draws = []
    # 針對全球最大彩票庫，免被 Block，極度穩定
    urls = [
        "https://www.lotteryextreme.com/hong_kong/mark_six_results",
        "https://www.lotteryextreme.com/hong_kong/mark_six_results2"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for url in urls:
        print(f"📡 極速掃描香港六合彩: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200: continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                row_text = row.get_text(" ", strip=True)
                # 六合彩開獎日期通常係 YYYY-MM-DD
                date_match = re.search(r'202[3-9]-[0-1][0-9]-[0-3][0-9]', row_text)
                
                if date_match:
                    nums_found = []
                    # 抽號碼，六合彩係 1-49
                    for td in row.find_all('td'):
                        txt = td.get_text(strip=True)
                        if txt.isdigit() and 1 <= int(txt) <= 49:
                            nums_found.append(int(txt))
                    
                    # 容錯機制
                    if len(nums_found) < 7:
                        nums_found = [int(x) for x in re.findall(r'\b\d{1,2}\b', row_text) if 1 <= int(x) <= 49]
                        
                    if len(nums_found) >= 7:
                        # 確保抽頭 7 個唔同嘅數字
                        unique_nums = []
                        for n in nums_found:
                            if n not in unique_nums: unique_nums.append(n)
                            
                        if len(unique_nums) >= 7:
                            main_balls = sorted(unique_nums[:6])
                            special_ball = unique_nums[6] # 第 7 個就係特別號碼
                            
                            all_draws.append({
                                'date': date_match.group(0),
                                'n1': main_balls[0], 'n2': main_balls[1], 'n3': main_balls[2],
                                'n4': main_balls[3], 'n5': main_balls[4], 'n6': main_balls[5],
                                'special': special_ball
                            })
        except Exception as e:
            print(f"⚠️ 錯誤: {e}")
            
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
        nums = [int(row[f'n{i}']) for i in range(1, 7)] # 只計主號碼，特別號碼唔計入走勢
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
    print("🚀 啟動 香港六合彩 (Mark Six) 自動爬蟲...")
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
