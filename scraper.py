import pandas as pd
import requests
from datetime import datetime

def scrape_marksix_data():
    all_draws = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 🌟 策略 1：從 GitHub 開源數據庫直接攞最乾淨嘅 JSON (保證 100% 唔會被 Block)
    print("📡 嘗試從 GitHub 開源數據庫抓取 (最高穩定性)...")
    try:
        url = "https://raw.githubusercontent.com/icelam/mark-six-data-visualization/master/data/all.json"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                date_str = item.get("date", "")
                if "202" not in date_str: continue # 只抽 2020 年後
                    
                nums = item.get("no", [])
                if isinstance(nums, str): nums = nums.split('+')
                nums = [int(x) for x in nums]
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
                print("   ✅ 成功從開源庫讀取！")
                return pd.DataFrame(all_draws)
    except Exception as e:
        print(f"   ⚠️ 開源庫讀取失敗: {e}")
        
    # 🌟 策略 2：官方馬會 API 補底
    print("📡 嘗試從香港馬會官方 API 抓取...")
    current_year = datetime.now().year
    urls = [
        f"https://bet.hkjc.com/marksix/getJSON.aspx?sd={current_year-2}0101&ed={current_year}1231&sb=0",
        f"https://bet2.hkjc.com/marksix/getJSON.aspx?sd={current_year-2}0101&ed={current_year}1231&sb=0"
    ]
    
    for url in urls:
        print(f"   -> 嘗試: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                if "<html" in resp.text.lower():
                    print("   🚫 被馬會防護系統阻擋。")
                    continue
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
                    print("   ✅ 成功從馬會官方讀取！")
                    return pd.DataFrame(all_draws)
        except Exception as e:
            print(f"   ⚠️ 讀取失敗: {e}")

    return pd.DataFrame(all_draws)

def calculate_metrics(df):
    if df.empty: return df
    df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
    
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
    print("🚀 啟動 香港六合彩 (Mark Six) 終極防 Block 爬蟲...")
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！成功寫入 {len(final_df)} 期六合彩數據。")
    else:
        print("❌ 警告：所有渠道都搵唔到數據！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
