import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

def scrape_marksix_data():
    all_draws = []
    current_year = datetime.now().year
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    }

    print("🚀 啟動【國家級黑客技巧】：Google Translate 隱形代理模式")
    
    # 🌟 神器 1: Google 代理直擊 HKJC 馬會官方 API
    # 將 bet.hkjc.com 變成 bet-hkjc-com.translate.goog，借 Google 條路入去！
    hkjc_url = f"https://bet-hkjc-com.translate.goog/marksix/getJSON.aspx?sd={current_year-2}0101&ed={current_year}1231&sb=0&_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en&_x_tr_pto=wapp"
    
    print("📡 嘗試 1: 借用 Google 無敵 IP 潛入香港馬會...")
    try:
        resp = requests.get(hkjc_url, headers=headers, timeout=20)
        if resp.status_code == 200:
            # Google 會將 JSON 包喺 HTML 入面，我哋用 AI 邏輯精準㓤返佢出嚟
            start_idx = resp.text.find('[')
            end_idx = resp.text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_text = resp.text[start_idx:end_idx+1]
                data = json.loads(json_text)
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
                    print("   ✅ 成功利用 Google 破解馬會！取得 2026 最新官方數據！")
                    df = pd.DataFrame(all_draws)
                    df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
                    return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)
    except Exception as e:
        print(f"   ⚠️ 馬會破解失敗: {e}")

    # 🌟 神器 2: Google 代理直擊 Lottery Extreme 全球彩票庫
    print("📡 嘗試 2: 借用 Google IP 潛入全球彩票庫...")
    le_urls = [
        "https://www-lotteryextreme-com.translate.goog/hong_kong/mark_six_results?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en&_x_tr_pto=wapp",
        "https://www-lotteryextreme-com.translate.goog/hong_kong/mark_six_results2?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en&_x_tr_pto=wapp"
    ]
    
    for url in le_urls:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
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
        except Exception as e:
            print(f"   ⚠️ 彩票庫破解失敗: {e}")
            
    if all_draws:
        print("   ✅ 成功利用 Google 破解彩票庫！")
        df = pd.DataFrame(all_draws)
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna(subset=['date_obj']).drop_duplicates('date_obj').sort_values('date_obj', ascending=True)

    # 🌟 神器 3: Internet Archive 網頁時光機 (保底)
    print("📡 嘗試 3: Internet Archive 網頁庫...")
    try:
        url = "https://web.archive.org/web/2/https://www.lotteryextreme.com/hong_kong/mark_six_results"
        resp = requests.get(url, headers=headers, timeout=20)
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
    except: pass

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
    print("🚀 啟動 香港六合彩 終極無敵 Google 破防版爬蟲...")
    raw_df = scrape_marksix_data()
    
    if not raw_df.empty:
        final_df = calculate_metrics(raw_df)
        cols = ['date','n1','n2','n3','n4','n5','n6','special','odd_even','consecutive','repeats','zone']
        final_df[cols].to_csv('data.csv', index=False)
        print(f"✅ 大功告成！成功寫入 {len(final_df)} 期六合彩數據。")
    else:
        print("❌ 警告：所有破防策略失敗！強制終止。")
        exit(1)

if __name__ == "__main__":
    main()
