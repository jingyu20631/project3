import json
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ==========================================
# 1. 페이지 기본 설정 및 디자인
# ==========================================
st.set_page_config(
    page_title="전국 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide"
)

# 따뜻하고 깔끔한 톤을 위한 커스텀 CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #FFFDF9;
        color: #4A3E3D;
    }
    h1, h2, h3 {
        color: #5C3D2E !important;
        font-family: 'Nanum Gothic', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🗺️ 2026년 전국 시군구별 고령화 단계구분도")
st.write("2026년 기준 전국 시·군·구별 65세 이상 고령 인구 비율(%)을 단계구분도(Choropleth Map)로 나타냅니다.")

# ==========================================
# 2. 데이터 불러오기 (캐싱 적용)
# ==========================================
@st.cache_data
def load_geojson():
    """시군구 경계 GeoJSON 데이터 다운로드 및 JSON 변환"""
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()

@st.cache_data
def load_population_data():
    """인구 데이터 불러오기 및 2026년 시군구별 고령화율 계산"""
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url)
    
    # 2026년 데이터만 필터링
    df_2026 = df[df['연도'] == 2026].copy()
    
    # 코드를 5자리 문자열로 변환 (앞 5자리가 시군구 코드)
    df_2026['시군구코드'] = df_2026['코드'].astype(str).str.zfill(8).str[:5]
    
    # '계_'로 시작하는 모든 열 (전체 인구 계산용)
    total_cols = [col for col in df_2026.columns if col.startswith('계_')]
    
    # '계_65세'부터 '계_100세 이상'까지의 열 (65세 이상 인구 계산용)
    # 65세부터 99세까지 + 100세 이상
    senior_cols = [f'계_{i}세' for i in range(65, 100)]
    if '계_100세 이상' in df_2026.columns:
        senior_cols.append('계_100세 이상')
    elif '계_100세이상' in df_2026.columns:
        senior_cols.append('계_100세이상')

    # 동별 총인구 및 고령인구 계산
    df_2026['총인구'] = df_2026[total_cols].sum(axis=1)
    df_2026['고령인구'] = df_2026[senior_cols].sum(axis=1)
    
    # 시군구 단위 그룹화
    sigungu_df = df_2026.groupby('시군구코드', as_index=False).agg({
        '시도': 'first',
        '시군구': 'first',
        '총인구': 'sum',
        '고령인구': 'sum'
    })
    
    # 고령화율(%) 계산 (65세 이상 인구 / 전체 인구 * 100)
    sigungu_df['고령화율'] = (sigungu_df['고령인구'] / sigungu_df['총인구']) * 100
    sigungu_df['고령화율'] = sigungu_df['고령화율'].round(2)
    sigungu_df['지역명'] = sigungu_df['시도'] + " " + sigungu_df['시군구']
    
    return sigungu_df

# 데이터 로딩 애니메이션
with st.spinner("GeoJSON 경계 지도 및 인구 데이터를 불러오는 중입니다... 잠시만 기다려주세요!"):
    geojson_data = load_geojson()
    sigungu_pop = load_population_data()

# ==========================================
# 3. 요약 통계 정보 표시
# ==========================================
col1, col2, col3 = st.columns(3)
max_row = sigungu_pop.loc[sigungu_pop['고령화율'].idxmax()]
min_row = sigungu_pop.loc[sigungu_pop['고령화율'].idxmin()]

col1.metric("전국 평균 고령화율", f"{round((sigungu_pop['고령인구'].sum() / sigungu_pop['총인구'].sum()) * 100, 2)}%")
col2.metric("최고 고령화 지역", f"{max_row['지역명']}", f"{max_row['고령화율']}%")
col3.metric("최저 고령화 지역", f"{min_row['지역명']}", f"{min_row['고령화율']}%")

st.divider()

# ==========================================
# 4. Plotly 단계구분도 (Choropleth Map) 생성
# ==========================================
fig = px.choropleth(
    sigungu_pop,
    geojson=geojson_data,
    locations='시군구코드',         # DataFrame의 시군구코드
    featureidkey='properties.코드',  # GeoJSON의 properties.코드
    color='고령화율',               # 색상 기준
    color_continuous_scale="Reds",  # 고령화율이 높을수록 진한 빨간색
    hover_name='지역명',
    hover_data={
        '시군구코드': False,
        '고령화율': ':.2f',
        '총인구': ':,명',
        '고령인구': ':,명'
    },
    labels={'고령화율': '고령화율(%)', '총인구': '총인구 수', '고령인구': '65세 이상 인구'}
)

# 배경 지도 타일 없이 경계만 표시 및 스타일링
fig.update_geos(
    fitbounds="locations",  # 대한민국 지역 영역에 맞추기
    visible=False           # 배경 타일 및 기본 지리적 선 숨기기
)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    height=700,
    paper_bgcolor="#FFFDF9",
    plot_bgcolor="#FFFDF9",
    coloraxis_colorbar=dict(
        title="고령화율 (%)",
        ticksuffix="%",
        len=0.8
    )
)

st.plotly_chart(fig, use_container_width=True)

# 상위 / 하위 지역 데이터 표
with st.expander("📊 시군구별 고령화율 상세 데이터 보기"):
    st.dataframe(
        sigungu_pop[['시군구코드', '시도', '시군구', '총인구', '고령인구', '고령화율']]
        .sort_values(by='고령화율', ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )
