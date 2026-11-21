import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import io

# 1. إعدادات الصفحة والتصميم العام
st.set_page_config(page_title="ملخص مباريات يلا كورة", page_icon="⚽", layout="wide")

# تحسين الاتجاه للغة العربية (RTL) وتنسيق البطاقات
st.markdown("""
<style>
    .main { direction: rtl; text-align: right; }
    .match-card {
        background-color: #1E1E1E;
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 12px;
        border-right: 5px solid #00C853;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
    }
    .team-name { font-size: 1.1rem; font-weight: bold; width: 30%; text-align: center; }
    .score-box { 
        background-color: #2E2E2E; 
        padding: 8px 18px; 
        border-radius: 8px; 
        font-size: 1.2rem; 
        font-weight: bold; 
        color: #00E676;
        text-align: center;
    }
    .match-meta { font-size: 0.85rem; color: #AAAAAA; text-align: center; width: 20%; }
</style>
""", unsafe_allow_html=True)

# 2. عنوان التطبيق
st.title("⚽ مستكشف وملخص مباريات يلا كورة")
st.write("اختر التاريخ والدوري لعرض المباريات والنتائج وتصديرها فوراً.")

# 3. دالة سحب وتنظيف البيانات
@st.cache_data(ttl=600)
def scrape_matches(date_str):
    url = f"https://www.yallakora.com/match-center?date={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return None, f"تعذر الاتصال بالموقع: {e}"

    soup = BeautifulSoup(response.content, "html.parser")
    championships = soup.find_all("div", {'class': 'matchCard'})
    
    if not championships:
        return [], None

    clean_data = []
    for champ in championships:
        champ_title = " ".join(champ.find("h2").text.split())
        matches = champ.find_all('div', {'class': 'item'})
        
        for match in matches:
            try:
                team_a = " ".join(match.find('div', {'class': 'teamA'}).text.split())
                team_b = " ".join(match.find('div', {'class': 'teamB'}).text.split())
                
                scores = match.find('div', {'class': 'MResult'}).find_all('span', {'class': 'score'})
                score_text = f"{scores[0].text.strip()} - {scores[1].text.strip()}"
                
                time_text = match.find('div', {'class': 'MResult'}).find('span', {'class': 'time'}).text.strip()
                
                status_tag = match.find('div', {'class': 'matchStatus'})
                status_text = " ".join(status_tag.text.split()) if status_tag else "مجدولة"

                if team_a and team_b:
                    clean_data.append({
                        "البطولة": champ_title,
                        "الفريق الأول": team_a,
                        "النتيجة": score_text,
                        "الفريق الثاني": team_b,
                        "التوقيت": time_text,
                        "الحالة": status_text
                    })
            except AttributeError:
                continue

    return clean_data, None

# 4. شريط التحكم (اختيار التاريخ + اختيار الدوري + بحث باسم الفريق)
col1, col2, col3 = st.columns([1, 2, 1.5])

with col1:
    selected_date = st.date_input("📅 1. اختر التاريخ:", datetime.today())

formatted_date = selected_date.strftime("%m/%d/%Y")

# جلب البيانات تلقائياً بمجرد تغيير التاريخ
with st.spinner("جاري تحديث قائمة البطولات والمباريات..."):
    all_matches, error = scrape_matches(formatted_date)

if error:
    st.error(error)
elif not all_matches:
    st.warning(f"⚠️ لا توجد مباريات مسجلة في موقع يلا كورة بتاريخ {formatted_date}.")
else:
    # استخراج أسماء البطولات المتاحة في هذا اليوم بدون تكرار
    available_leagues = list(dict.fromkeys([m["البطولة"] for m in all_matches]))
    league_options = ["عرض جميع البطولات"] + available_leagues

    with col2:
        selected_league = st.selectbox("🏆 2. اختر الدوري / البطولة:", league_options)

    with col3:
        team_search = st.text_input("🔍 بحث باسم الفريق (اختياري):", placeholder="مثال: الأهلي، ريال مدريد...")

    # تطبيق الفلترة حسب الدوري المختار
    if selected_league == "عرض جميع البطولات":
        filtered_matches = all_matches
    else:
        filtered_matches = [m for m in all_matches if m["البطولة"] == selected_league]

    # تطبيق فلتر البحث باسم الفريق إن وجد
    if team_search.strip():
        query = team_search.strip()
        filtered_matches = [
            m for m in filtered_matches 
            if query in m["الفريق الأول"] or query in m["الفريق الثاني"]
        ]

    st.divider()

    # 5. عرض النتائج وزر التحميل
    if not filtered_matches:
        st.info("لا توجد مباريات تطابق بحثك في هذا اليوم.")
    else:
        # شريط علوي يعرض العدد وزر تحميل CSV للنتائج المفلترة فقط
        info_col, btn_col = st.columns([3, 1])
        with info_col:
            st.success(f"📊 عدد المباريات المعروضة: **{len(filtered_matches)}** مباراة")
        
        with btn_col:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=filtered_matches[0].keys())
            writer.writeheader()
            writer.writerows(filtered_matches)
            csv_bytes = output.getvalue().encode('utf-8-sig')

            st.download_button(
                label="📥 تحميل هذه النتائج (Excel)",
                data=csv_bytes,
                file_name=f"matches_{selected_date.strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # عرض المباريات مقسمة حسب البطولة
        displayed_leagues = list(dict.fromkeys([m["البطولة"] for m in filtered_matches]))
        
        for league in displayed_leagues:
            st.subheader(f"🏆 {league}")
            league_matches = [m for m in filtered_matches if m["البطولة"] == league]
            
            for m in league_matches:
                st.markdown(f"""
                <div class="match-card">
                    <div class="team-name">{m['الفريق الأول']}</div>
                    <div class="score-box">{m['النتيجة']}</div>
                    <div class="team-name">{m['الفريق الثاني']}</div>
                    <div class="match-meta">⏰ {m['التوقيت']}<br>📌 {m['الحالة']}</div>
                </div>
                """, unsafe_allow_html=True)
