import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Gemini API 키 불러오기
API_KEY = st.secrets["GEMINI_API_KEY"]

# 2. Gemini API 설정
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("장소 리뷰 AI 키워드 자동 추출 (Google Gemini API)")

st.write("CSV 파일을 올리면, 각 장소 후기를 AI가 자동으로 분석해서 주요 키워드를 뽑아줍니다!")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

def smart_read_csv(file):
    # 여러 인코딩을 안전하게 시도!
    for enc in ["utf-8", "cp949", "euc-kr"]:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            return df
        except Exception:
            continue
    st.error("CSV 파일을 읽을 수 없습니다.\n인코딩/파일 구조를 다시 확인해 주세요.")
    st.stop()

if uploaded_file is not None:
    df = smart_read_csv(uploaded_file)
    st.write("원본 데이터 미리보기:")
    st.dataframe(df)

    # 'AI키워드' 컬럼 추가
    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    st.write("AI가 각 리뷰를 분석 중입니다... (조금만 기다려 주세요)")

    # '장소후기' 컬럼, 혹은 영어로 되어 있으면 'review' 자동 인식
    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break

    if review_col is None:
        st.error("‘장소후기’(또는 review)라는 컬럼이 CSV에 없습니다! 확인해 주세요.")
        st.stop()

    # 각 후기별로 Gemini 키워드 추출
    for i, row in df.iterrows():
        review = str(row.get(review_col, ""))
        if not review.strip():
            df.at[i, "AI키워드"] = "후기 없음"
            continue

        prompt = f"아래 장소 후기에서 가장 중요한 키워드(특징) 3개를 한글로, 콤마(,)로 구분해서 뽑아줘.\n'{review}'"
        try:
            response = model.generate_content(prompt)
            df.at[i, "AI키워드"] = response.text.strip()
        except Exception as e:
            df.at[i, "AI키워드"] = f"AI 오류: {e}"

    st.success("AI 분석이 끝났습니다! 결과는 아래에서 확인하세요.")
    st.dataframe(df)

    # 결과 파일로 저장
    result_csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="분석 결과 CSV 다운로드",
        data=result_csv,
        file_name="장소리뷰_AI분석.csv",
        mime="text/csv"
    )
