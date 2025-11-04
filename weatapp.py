import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
import pandas as pd
import altair as alt # 시각화를 위해 altair 추가

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="인터랙티브 날씨 대시보드 🌦️",
    page_icon="☀️",
    layout="wide", # 'centered' 대신 'wide' 레이아웃으로 더 넓은 화면 사용
    initial_sidebar_state="expanded" # 사이드바 초기 상태
)

# --- 2. 날씨 코드에 따른 이모지 딕셔너리 (Open-Meteo Weather Codes) ---
# https://www.open-meteo.com/en/docs 에서 WMO Weather interpretation codes 참조
weather_codes = {
    0: "☀️ 맑음",
    1: "🌤️ 대체로 맑음",
    2: "⛅ 부분적으로 흐림",
    3: "☁️ 흐림",
    45: "🌫️ 안개",
    48: "🌫️ 서리 안개",
    51: "🌧️ 약한 이슬비",
    53: "🌧️ 보통 이슬비",
    55: "🌧️ 강한 이슬비",
    56: "❄️ 약한 어는 이슬비",
    57: "❄️ 강한 어는 이슬비",
    61: "☔ 약한 비",
    63: "☔ 보통 비",
    65: "☔ 강한 비",
    66: "🌨️ 약한 어는 비",
    67: "🌨️ 강한 어는 비",
    71: "❄️ 약한 눈",
    73: "❄️ 보통 눈",
    75: "❄️ 강한 눈",
    77: "🌨️ 싸락눈",
    80: "☔️ 약한 소나기",
    81: "☔️ 보통 소나기",
    82: "☔️ 강한 소나기",
    85: "🌨️ 약한 눈 소나기",
    86: "🌨️ 강한 눈 소나기",
    95: "⚡️ 보통 천둥번개",
    96: "⚡️ 약한 우박 천둥번개",
    99: "⚡️ 강한 우박 천둥번개",
}

def get_weather_description(code):
    return weather_codes.get(code, "알 수 없는 날씨")

# --- 3. 헤더 및 설명 ---
st.title("🌏 지구촌 날씨 탐색기 🌦️")
st.markdown("---")
st.write("지도에서 원하는 위치를 클릭하면, 해당 지역의 **7일간 일별 예보**와 **48시간 시간별 예보**를 확인할 수 있습니다.")

# --- 4. 지도 섹션 ---
st.subheader("📍 위치 선택하기 (지도 클릭)")

# 한국 중심으로 초기 지도 설정
m = folium.Map(location=[36.5, 127.5], zoom_start=7) # 한국 중앙 근처

# [!!!] 여기가 수정된 부분입니다.
# 'feature_group_column="컬러"' 인자를 제거하여 TypeError 해결
map_data = st_folium(m, height=450, width=800) 

lat, lon = None, None
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.success(f"선택된 위치: 위도 {lat:.4f}, 경도 {lon:.4f}")
    
    # 클릭된 위치에 마커 추가
    folium.Marker(
        location=[lat, lon],
        tooltip="선택된 위치",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    # st_folium을 다시 호출하여 마커가 표시된 지도 업데이트
    st_folium(m, height=450, width=800, key="updated_map")


if lat is not None and lon is not None:
    # --- 5. Open-Meteo API 요청 구축 ---
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation,weathercode,windspeed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode" # daily에도 weathercode 추가
        "&timezone=auto"
        "&forecast_days=7" # 7일 예보
    )

    try:
        with st.spinner("날씨 데이터를 가져오는 중..."):
            r = requests.get(url, timeout=10)
            r.raise_for_status() # HTTP 오류 발생 시 예외 발생
            data = r.json()
    except requests.exceptions.Timeout:
        st.error("API 요청 시간이 초과되었습니다. 네트워크 연결을 확인하거나 다시 시도해주세요.")
        st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"날씨 데이터를 가져오는 데 실패했습니다: {e}")
        st.stop()
    except Exception as e:
        st.error(f"예상치 못한 오류가 발생했습니다: {e}")
        st.stop()

    # --- 6. 날씨 요약 (Summary) ---
    st.markdown("---")
    st.subheader("✨ 현재 날씨 요약 및 7일 예보")
    
    if "hourly" in data and "daily" in data:
        # 현재 날씨 정보 추출 (가장 최근 시간 데이터)
        hourly_times = data["hourly"]["time"]
        hourly_temps = data["hourly"]["temperature_2m"]
        hourly_weathercodes = data["hourly"]["weathercode"]

        # 현재 시간과 가장 가까운 데이터 찾기
        current_time_str = hourly_times[0] if hourly_times else None
        current_temp = hourly_temps[0] if hourly_temps else "N/A"
        current_weather_code = hourly_weathercodes[0] if hourly_weathercodes else "N/A"
        current_weather_desc = get_weather_description(current_weather_code)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("현재 기온", f"{current_temp}°C", current_weather_desc)
        with col2:
            st.metric("오늘 최고/최저", 
                      f"{data['daily']['temperature_2m_max'][0]}°C / {data['daily']['temperature_2m_min'][0]}°C",
                      get_weather_description(data['daily']['weathercode'][0]))
        with col3:
            st.metric("오늘 강수량 (예상)", f"{data['daily']['precipitation_sum'][0]} mm")

        st.markdown("---")

        # --- 7. 일별 요약 테이블 ---
        st.subheader("📅 7일간 일별 요약")
        daily = data["daily"]
        df_daily = pd.DataFrame({
            "날짜": daily.get("time", []),
            "날씨": [get_weather_description(code) for code in daily.get("weathercode", [])], # 날씨 코드 변환
            "최고기온 (°C)": daily.get("temperature_2m_max", []),
            "최저기온 (°C)": daily.get("temperature_2m_min", []),
            "강수량 (mm)": daily.get("precipitation_sum", []),
        })
        st.dataframe(df_daily, use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- 8. 시간별 차트 ---
        st.subheader("📊 48시간 시간별 예보")
        hourly = data["hourly"]
        df_hourly = pd.DataFrame({
            "시간": hourly.get("time", []),
            "기온 (°C)": hourly.get("temperature_2m", []),
            "강수량 (mm/h)": hourly.get("precipitation", []),
            "풍속 (km/h)": hourly.get("windspeed_10m", []),
            "날씨 코드": hourly.get("weathercode", []) # 차트에는 직접 사용하지 않지만 데이터 확인용
        })

        if not df_hourly.empty:
            df_hourly["시간"] = pd.to_datetime(df_hourly["시간"])
            # df_hourly = df_hourly.set_index("시간") # Altair는 인덱스보다 컬럼을 사용하는 것이 더 편리

            # 사용자가 보고 싶은 차트를 선택하도록 드롭다운 추가
            chart_options = {
                "기온": "기온 (°C)",
                "강수량": "강수량 (mm/h)",
                "풍속": "풍속 (km/h)",
            }
            selected_chart = st.selectbox("어떤 데이터를 보시겠어요?", list(chart_options.keys()))

            if selected_chart:
                y_axis_label = chart_options[selected_chart]
                chart = alt.Chart(df_hourly).mark_line(point=True).encode(
                    x=alt.X('시간:T', title="시간"),
                    y=alt.Y(y_axis_label, title=y_axis_label, scale=alt.Scale(zero=False)),
                    tooltip=['시간:T', alt.Tooltip(y_axis_label, format=".1f")]
                ).properties(
                    title=f"시간별 {selected_chart}"
                ).interactive()
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("표시할 차트를 선택해주세요.")
        else:
            st.write("시간별 데이터를 가져올 수 없습니다.")
    else:
        st.write("날씨 데이터를 가져올 수 없습니다.")

    # --- 9. API 응답 원본 (디버깅/확인용) ---
    with st.expander("📝 전체 API 응답 데이터 보기 (JSON)"):
        st.json(data)

else:
    st.info("👆 지도에서 위치를 클릭하여 날씨 정보를 확인해보세요!")
