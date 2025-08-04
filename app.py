import streamlit as st
import pandas as pd
import openai
import os

# 1. OpenAI API 키 불러오기 (Streamlit Cloud Secrets 권장)
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    st.error("OpenAI API 키가 필요합니다. Secrets 또는 환경변수 등록 필수!")
    st.stop()
openai.api_key = OPENAI_API_KEY

st.title("숙소후기 키워드 자동 추출 (ChatGPT API)")
st.write("CSV 파일을 업로드하면 각 ‘숙소후기’에서 AI가 키워드 3개를 자동으로 뽑아줍니다.")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

def smart_read_csv(file):
    """여러 인코딩 + chardet 감지까지 지원."""
    if file is None:
        st.stop()
    for enc in ["utf-8", "cp949", "euc-kr"]:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except Exception:
            continue
    try:
        file.seek(0)
        import chardet
        raw = file.read()
        encoding = chardet.detect(raw)['encoding'] or "utf-8"
        file.seek(0)
        return pd.read_csv(file, encoding=encoding)
    except Exception:
        st.error("CSV 파일이 정상적인 쉼표구분 텍스트여야 하고, 첫 줄은 컬럼명(헤더)이어야 합니다.")
        st.stop()

def extract_keywords(text):
    prompt = (
        "다음 숙소 후기에서 가장 중요한 키워드(주요 특징 또는 핵심 단어) 3개를 한글로, 콤마(,)로 구분해 뽑아줘:\n"
        f"{text}"
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
    # 컬럼명 정리
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    st.subheader("업로드 데이터 미리보기")
    st.dataframe(df)

    # 리뷰 컬럼 자동 탐색
    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break
    if not review_col:
        st.error(f"‘숙소후기’(또는 review) 컬럼 없음! 현재 컬럼명: {list(df.columns)}")
        st.stop()

    # 결과 컬럼 준비
    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    st.write("AI가 각 후기를 분석 중입니다... (수 초~수 분 소요)")
    for i, row in df.iterrows():
        if df.at[i, "AI키워드"]:
            continue
        review = str(row.get(review_col, "")).strip()
        if not review:
            df.at[i, "AI키워드"] = "후기 없음"
            continue
        df.at[i, "AI키워드"] = extract_keywords(review)
        if i % 10 == 0:
            st.dataframe(df.head(20))
    st.success("AI 분석이 끝났습니다! 아래에서 결과를 확인하세요.")
    st.dataframe(df)

    # 결과 다운로드
    st.download_button(
        label="분석 결과 CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="숙소후기_AI키워드분석.csv",
        mime="text/csv"
    )
