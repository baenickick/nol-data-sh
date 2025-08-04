import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Gemini API 키 불러오기 (Streamlit Cloud의 Secrets에서)
API_KEY = st.secrets["GEMINI_API_KEY"]

# 2. Gemini 설정
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("숙소후기 키워드 자동 추출 (Gemini AI)")

st.write(
    "CSV 파일을 업로드하면 각 ‘숙소후기’ 글에서 AI가 주요 키워드 3개를 자동으로 뽑아줍니다."
    " (인코딩/파일 구조 문제도 자동 해결)"
)

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

def smart_read_csv(file):
    # 여러 인코딩 자동 시도 + chardet 사용
    encodings = ["utf-8", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except Exception:
            continue

    # 마지막 시도: chardet으로 인코딩 추정
    try:
        file.seek(0)
        import chardet
        raw = file.read()
        result = chardet.detect(raw)
        encoding = result['encoding']
        file.seek(0)
        return pd.read_csv(file, encoding=encoding)
    except Exception:
        st.error(
            "CSV 파일을 읽을 수 없습니다. (인코딩 혹은 파일 구조 문제)\nCSV를 'UTF-8(쉼표로 분리)'로 저장하거나, 첫째 줄이 컬럼명이 맞는지 확인해 주세요."
        )
        st.stop()

if uploaded_file is not None:
    df = smart_read_csv(uploaded_file)
    st.write("원본 데이터 미리보기:")
    st.dataframe(df)

    # 'AI키워드' 컬럼 추가
    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    # REVIEW 컬럼 자동 인식 ('숙소후기' 혹은 영어 'review' 포함 컬럼 우선)
    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break

    if review_col is None:
        st.error("‘숙소후기’라는 컬럼(혹은 review/Review)이 CSV에 없는 것 같습니다. 파일을 확인해 주세요.")
        st.stop()

    st.write("AI가 각 후기를 분석 중입니다... (몇 초~몇 분 소요될 수 있습니다)")

    # 각 후기별로 AI 키워드 추출 (중복 실행 방지)
    for i, row in df.iterrows():
        review = str(row.get(review_col, ""))
        if not review.strip():
            df.at[i, "AI키워드"] = "후기 없음"
            continue
        # 이미 분석된 내용이 있으면 생략(웹앱 재실행 대비)
        if df.at[i, "AI키워드"] and df.at[i, "AI키워드"] != "":
            continue

        prompt = (
            "아래 숙소 후기에서 가장 중요한 키워드(특징)를 한글로 3개, 콤마(,)로 구분해서 뽑아줘:\n"
            f"'{review}'"
        )
        try:
            response = model.generate_content(prompt)
            out = (response.text or "").strip()
            df.at[i, "AI키워드"] = out
        except Exception as e:
            df.at[i, "AI키워드"] = f"AI 오류: {e}"

    st.success("AI 분석이 끝났습니다! 결과는 아래를 확인하세요.")
    st.dataframe(df)

    # 다운로드 기능
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="분석 결과 CSV 다운로드",
        data=csv,
        file_name="숙소후기_AI키워드분석.csv",
        mime="text/csv"
    )
