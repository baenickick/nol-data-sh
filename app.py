import streamlit as st
import pandas as pd
import openai
from collections import Counter

# 1. API 키 셋팅
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

EXCLUDE = {"여름", "겨울", "가을", "봄"}  # 계절 키워드 제거

st.title("숙소후기 AI 키워드 자동 추출 및 요약")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

def smart_read_csv(file):
    for enc in ["utf-8", "cp949", "euc-kr"]:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except Exception:
            continue
    try:
        import chardet
        file.seek(0)
        raw = file.read()
        enc = chardet.detect(raw)["encoding"]
        file.seek(0)
        return pd.read_csv(file, encoding=enc)
    except Exception:
        st.error("CSV 인코딩/포맷 오류. 엑셀에서 'CSV UTF-8'로 다시 저장해 주세요.")
        st.stop()

def extract_keywords_from_gpt(review):
    prompt = (
        "다음 숙소 리뷰를 보고, '여름, 겨울, 봄, 가을' 계절 단어는 빼고 "
        "장소의 시설, 분위기, 느낌 중심으로 주요 특징 키워드 5~8개를 순수 한글 단어(공백 없이)로 추출해서 콤마(',')로 구분해줘. "
        "단, 계절명(여름, 겨울, 봄, 가을), 날짜 등 계절 관련 단어는 포함하지 말 것.\n"
        f"리뷰:\n{review}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 오류: {e}"

if uploaded_file is not None:
    df = smart_read_csv(uploaded_file)
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    st.dataframe(df.head())

    # 리뷰 컬럼 이름(후기/review) 자동 감지
    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break
    if not review_col:
        st.error(f"'숙소후기' 또는 review 컬럼이 없습니다: {list(df.columns)}")
        st.stop()
    
    # 위치 자동 감지 (주소/위치/region 등 포함 컬럼 찾기)
    location_col = None
    for col in df.columns:
        if "위치" in col or "주소" in col or "region" in col.lower():
            location_col = col
            break

    # AI키워드 컬럼 생성
    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    st.write("AI가 후기별 주요 키워드를 추출 중입니다...")
    for i, row in df.iterrows():
        if df.at[i, "AI키워드"]:
            continue
        review = str(row.get(review_col, "")).strip()
        if not review:
            df.at[i, "AI키워드"] = ""
            continue
        df.at[i, "AI키워드"] = extract_keywords_from_gpt(review)
        if i % 5 == 0:
            st.dataframe(df.head(20))

    st.success("숙소별로 중복 없이 주요 키워드를 요약합니다")

    # 숙소명/위치별 특징 키워드 집계/정리
    summary = []
    for (숙소명, 위치), group in df.groupby(["숙소명", location_col] if location_col else ["숙소명"]):
        all_keywords = []
        for keys in group["AI키워드"]:
            if keys:
                all_keywords.extend([
                    k.strip() for k in keys.split(",")
                    if k.strip() and k.strip() not in EXCLUDE
                ])
        # 많이 나온 특징 8개까지 집계
        ranked = [k for k, _ in Counter(all_keywords).most_common(8)]
        summary.append({
            "숙소명": 숙소명,
            "위치": 위치 if location_col else "",
            "주요 키워드": ", ".join(ranked),
        })

    summary_df = pd.DataFrame(summary)
    st.subheader("숙소별 대표 키워드 요약표 (계절명 제외)")

    st.dataframe(summary_df)

    # Streamlit-tags로 태그 스타일 예시 (선택)
    try:
        from streamlit_tags import st_tags
        for i, row in summary_df.iterrows():
            st.markdown(f"**{row['숙소명']} / {row['위치']}**")
            tags = [k.strip() for k in row["주요 키워드"].split(",")]
            st_tags(label='', text='주요 키워드:', value=tags, maxtags=8, key=i)
    except ImportError:
        st.info("streamlit-tags 설치 시 태그 스타일로도 표시됩니다.")

    st.download_button(
        label="요약 결과 CSV 다운로드",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="숙소별주요키워드_요약.csv",
        mime="text/csv"
    )
