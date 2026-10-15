import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. 페이지 기본 설정 및 디자인 (따뜻한 톤)
# ==========================================
st.set_page_config(
    page_title="동네별 인구 피라미드", page_icon="👨‍👩‍👧‍👦", layout="centered"
)

# 따뜻한 톤(크림색 배경, 부드러운 글꼴)을 위한 커스텀 CSS 적용
st.markdown(
    """
    <style>
    /* 전체 배경을 따뜻한 크림톤으로 설정 */
    .stApp {
        background-color: #FFFDF9;
        color: #4A3E3D;
    }
    /* 카드 형태 컨테이너 스타일 */
    div[data-testid="stMetricValue"] {
        color: #D96B27;
    }
    /* 제목 및 헤더 스타일 */
    h1, h2, h3 {
        color: #5C3D2E !important;
        font-family: 'Nanum Gothic', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("👨‍👩‍👧‍👦 동네별 인구 피라미드")
st.write(
    "원하는 **시도 ➡️ 시군구 ➡️ 동**을 선택하면 해당 지역의 최신 연도 인구 피라미드를 보여드립니다."
)


# ==========================================
# 2. 데이터 불러오기 (캐싱 적용)
# ==========================================
# @st.cache_data를 사용하면 매번 새로고침할 때마다 다시 다운로드하지 않아 속도가 매우 빠릅니다.
@st.cache_data
def load_data():
  url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/population_ts_yearly_gender.zip"
  # pandas는 zip 파일 내의 csv를 자동으로 압축 해제하여 읽습니다.
  df = pd.read_csv(url)
  return df


with st.spinner("데이터를 불러오는 중입니다... 잠시만 기다려주세요! ☕"):
  data = load_data()

# 최신 연도만 추출 (데이터에 존재하는 가장 큰 연도)
latest_year = data["연도"].max()
df_latest = data[data["연도"] == latest_year].copy()

st.caption(
    f"💡 현재 불러온 데이터의 최신 기준 연도는 **{latest_year}년**입니다."
)


# ==========================================
# 3. 나이 라벨 정렬 및 연령대 컬럼 분류
# ==========================================
# 나이 컬럼을 0세부터 100세 이상까지 순서대로 정의합니다.
# (이 순서가 그래프 세로축에 그대로 고정됩니다)
age_labels = [f"{i}세" for i in range(101)]
age_labels[-1] = "100세 이상"  # 맨 마지막은 '100세 이상'으로 변경

male_cols = [f"남_{age}" for age in age_labels]
female_cols = [f"여_{age}" for age in age_labels]


# ==========================================
# 4. 지역 선택 드롭다운 (시도 -> 시군구 -> 동)
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
  # 1. 시도 선택
  sido_list = sorted(df_latest["시도"].dropna().unique())
  selected_sido = st.selectbox("시·도 선택", sido_list)

with col2:
  # 2. 선택한 시도에 해당하는 시군구 목록
  filtered_sigungu = df_latest[df_latest["시도"] == selected_sido]
  sigungu_list = sorted(filtered_sigungu["시군구"].dropna().unique())
  selected_sigungu = st.selectbox("시·군·구 선택", sigungu_list)

with col3:
  # 3. 선택한 시군구에 해당하는 동 목록
  filtered_dong = filtered_sigungu[filtered_sigungu["시군구"] == selected_sigungu]
  dong_list = sorted(filtered_dong["동"].dropna().unique())
  selected_dong = st.selectbox("읍·면·동 선택", dong_list)


# ==========================================
# 5. 선택한 지역의 인구 데이터 추출 및 가공
# ==========================================
# 해당 동네의 데이터행을 1개 가져옵니다.
target_row = filtered_dong[filtered_dong["동"] == selected_dong]

if not target_row.empty:
  # 남/여 연령별 인구수 데이터 시리즈 추출
  male_pop = target_row[male_cols].iloc[0].values
  female_pop = target_row[female_cols].iloc[0].values

  # 총 인구 및 남녀 합계 계산
  total_male = int(male_pop.sum())
  total_female = int(female_pop.sum())
  total_pop = total_male + total_female

  # 주요 통계 지표 표시 (요약)
  m_col1, m_col2, m_col3 = st.columns(3)
  m_col1.metric("총 인구수", f"{total_pop:,} 명")
  m_col2.metric("남성 인구", f"{total_male:,} 명")
  m_col3.metric("여성 인구", f"{total_female:,} 명")

  # ==========================================
  # 6. Plotly 인구 피라미드 그래프 생성
  # ==========================================
  fig = go.Figure()

  # [남성] 왼쪽 막대그래프 (인구수 값을 음수로 변환)
  # hovertemplate을 통해 마우스를 올렸을 때는 원래 양수 값으로 표시합니다.
  fig.add_trace(
      go.Bar(
          y=age_labels,  # 세로축: 나이 (0세 -> 100세 이상)
          x=-male_pop,  # 가로축: 남성 인구 (음수 처리하여 왼쪽에 위치)
          name="남성",
          orientation="h",
          marker=dict(
              color="#5B82A6", line=dict(color="#426585", width=1)
          ),  # 부드러운 따뜻한 파란/네이비 톤
          hovertemplate="<b>남성</b><br>나이: %{y}<br>인구: %{customdata:,}명<extra></extra>",
          customdata=male_pop,  # 마우스 호버 시 원래 인구수(양수) 표시
      )
  )

  # [여성] 오른쪽 막대그래프 (양수 그대로)
  fig.add_trace(
      go.Bar(
          y=age_labels,  # 세로축: 나이 (0세 -> 100세 이상)
          x=female_pop,  # 가로축: 여성 인구 (양수로 오른쪽에 위치)
          name="여성",
          orientation="h",
          marker=dict(
              color="#E07A5F", line=dict(color="#C2593E", width=1)
          ),  # 부드러운 따뜻한 주황/코랄 톤
          hovertemplate="<b>여성</b><br>나이: %{y}<br>인구: %{x:,}명<extra></extra>",
      )
  )

  # 세로축 순서 고정 및 그래프 스타일 설정
  fig.update_layout(
      title=dict(
          text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}] 인구 피라미드 ({latest_year}년)</b>",
          font=dict(size=18, color="#5C3D2E"),
          x=0.5,  # 중앙 정렬
      ),
      barmode="overlay",  # 남/여 막대가 중앙 축 기준으로 서로 반대 방향 확장
      bargap=0.1,  # 막대 간격
      # 세로축(y축) 설정
      yaxis=dict(
          title="연령",
          type="category",  # 범주형 축으로 설정하여 입력 배열 순서 고정
          categoryorder="array",  # 우리가 전달한 age_labels 순서를 그대로 유지
          categoryarray=age_labels,  # 맨 아래: 0세 ~ 맨 위: 100세 이상
          showgrid=True,
          gridcolor="#F0EAE1",
      ),
      # 가로축(x축) 설정 (좌우 대칭 인구수 표기)
      xaxis=dict(
          title="인구수 (명)",
          showgrid=True,
          gridcolor="#F0EAE1",
          # 음수 표시 눈금을 양수로 보이게 변환하는 콜백 형식 지정
          tickmode="linear",
      ),
      plot_bgcolor="#FFFDF9",  # 배경색 크림톤
      paper_bgcolor="#FFFDF9",
      legend=dict(
          orientation="h",
          yanchor="bottom",
          y=1.02,
          xanchor="right",
          x=1,
          font=dict(size=13),
      ),
      height=800,  # 0~100세 이상까지 잘 보이도록 높이를 넉넉히 설정
      margin=dict(l=50, r=50, t=80, b=50),
  )

  # x축 눈금값의 음수를 양수로 깔끔하게 재정의
  # max_val을 구해 적절한 눈금 간격 설정
  max_val = max(male_pop.max(), female_pop.max())
  if max_val > 0:
    # 5~6개 눈금이 나오도록 간격 조정
    step = max(1, int(max_val / 4))
    tick_vals = list(range(-step * 4, step * 5, step))
    tick_text = [str(abs(val)) for val in tick_vals]

    fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

  # 스트림릿 화면에 그래프 그리기
  st.plotly_chart(fig, use_container_width=True)

else:
  st.warning("선택한 지역의 인구 데이터를 찾을 수 없습니다.")
