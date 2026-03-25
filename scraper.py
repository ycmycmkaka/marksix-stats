import pandas as pd
import requests
from datetime import datetime
import urllib.parse
from bs4 import BeautifulSoup
import re

def scrape_marksix_data():
    all_draws = []
    current_year = datetime.now().year
    
    # 馬會官方 API (最齊最新，有齊 2026 數據)
    target_url = f"https://bet.hkjc.com/marksix/getJSON.aspx?sd={current_year-2}0101&ed={current_year}1231&sb=0"
    encoded_url = urllib.parse.quote(target_url)
    
    # 🌟 破防大絕：透過全球免洗代理 (Proxy) 去攞馬會資料，完美避開 GitHub IP 被 Block！
    proxy_urls = [
        f"https://api.allorigins.win/raw?url={encoded_url}",
        f"https://api.codetabs.com/v1/proxy/?quest={encoded_url}",
        target_url # 如果代理死咗，自己硬闖
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://bet.hkjc.com/marksix/'
    }
    
    print("📡 策略 1：透過 Proxy 直取馬會最新 JSON...")
    for url in proxy_urls:
        print(f"   -> 嘗試: {url[:60]}...")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            # 確保攞到嘅係 JSON，而唔係被 Block 嘅 HTML
            if resp.status_code == 200 and "{" in resp.text and "<html" not in resp.text.lower():
                data = resp.json()
                for item in data:
                    raw_date = item.get("date", "")
                    try:
                        date_obj = datetime.strptime(raw_date, "%d/%m/%Y")
                        date_str = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_str = raw_date
                        
                    if "202" not in date_str: continue
                        
                    no_str = item.get("no", "")
                    nums = [int(x) for x in no_str.split('+')] if no_str else []
                    sno = int(item.get("sno", 0))
                    
                    if len(nums) == 6:
                        nums = sorted(nums)
                        all_draws.append({
                            'date': date_str,
                            'n1': nums[0], 'n2': nums[1], 'n3': nums[2],
                            'n4': nums[3], 'n5': nums[4], 'n6': nums[5],
                            'special': sno
                        })
                if all_draws:
                    print("   ✅ 成功破解！取得馬會最新官方數據！")
                    df = pd.DataFrame(all_draws)
                    df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
                    return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
        except Exception as e:
            print(f"   ⚠️ 失敗: {e}")

    # 🌟 後備方案：如果馬會改制，轉去全球彩票庫爬 HTML (同樣用 Proxy)
    print("📡 策略 2：馬會無反應，轉向全球彩票庫...")
    le_url = "https://www.lotteryextreme.com/hong_kong/mark_six_results"
    try:
        resp = requests.get(f"https://api.allorigins.win/raw?url={urllib.parse.quote(le_url)}", headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                row_text = row.get_text(" ", strip=True)
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
            if all_draws:
                print("   ✅ 成功由彩票庫取得數據！")
                df = pd.DataFrame(all_draws)
                df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
                return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
    except Exception as e:
        print(f"   ⚠️ 失敗: {e}")

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
    print("🚀 啟動 香港六合彩 終極破防版爬蟲...")
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！寫入 {len(final_df)} 期最新六合彩數據。")
    else:
        print("❌ 警告：所有破防策略失敗！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
