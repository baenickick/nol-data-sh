import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Gemini API 키 불러오기 (Streamlit Cloud Secret)
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("숙소후기 AI 키워드 자동 추출 (Gemini API)")
st.write(
    "CSV 파일을 업로드하면 각 ‘숙소후기’(‘review’)에서 AI가 키워드 3개를 뽑아줍니다. "
    "파일 인코딩 문제나 구조 오류가 있어도 화면에서 바로 진단할 수 있습니다."
)

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

def smart_read_csv(file):
    """여러 인코딩 + chardet 감지까지 지원."""
    if file is None:
        st.stop()
    try_enc = ["utf-8", "cp949", "euc-kr"]
    for enc in try_enc:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except Exception:
            continue
    # chardet 활용(끝판왕)
    try:
        file.seek(0)
        import chardet
        raw = file.read()
        detected = chardet.detect(raw)
        encoding = detected['encoding'] or "utf-8"
        file.seek(0)
        return pd.read_csv(file, encoding=encoding)
    except Exception:
        st.error(
            "CSV 파일 인코딩/포맷 문제입니다. "
            "엑셀에서 'CSV UTF-8(쉼표로 분리)'로 저장하거나, 첫 줄이 반드시 컬럼명이어야 합니다. "
            "샘플 파일로 정상 동작확인을 권장합니다."
        )
        # DEBUG: 파일 앞부분 미리보기(문제추적)
        try:
            file.seek(0)
            sample = file.read(500)
            st.write("==== 파일 앞부분 UTF-8로 해석 ====")
            try:
                st.text(sample.decode("utf-8"))
            except Exception:
                st.text(str(sample))
        except Exception:
            pass
        st.stop()

if uploaded_file is not None:
    # 파일로드(인코딩 자동)
    df = smart_read_csv(uploaded_file)

    # 컬럼명 띄어쓰기, 숨은문자 제거(for robustness)
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    # 미리보기
    st.subheader("업로드된 데이터 미리보기")
    st.dataframe(df)

    # ==== 리뷰 컬럼 자동 감지 ====
    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break
    if review_col is None:
        st.error(
            f"‘숙소후기’(또는 review) 컬럼이 없습니다! "
            f"컬럼명을 꼭 확인해 주세요: {list(df.columns)}"
        )
        st.stop()

    # 결과 컬럼 준비
    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    st.write("AI가 각 후기를 분석 중입니다... (수 초~수 분 소요, 중간 결과 자동 반영)")

    for i, row in df.iterrows():
        # 이미 결과 있으면 건너뛴다(중복 요청 방지)
        if df.at[i, "AI키워드"]:
            continue

        review = str(row.get(review_col, "")).strip()
        if not review:
            df.at[i, "AI키워드"] = "후기 없음"
            continue

        prompt = (
            "아래 숙소 후기에서 가장 중요한 키워드(특징)를 한글로 3개, 콤마(,)로 구분해서 뽑아줘:\n"
            f"{review}"
        )
        try:
            response = model.generate_content(prompt)
            out = (response.text or "").strip()
            df.at[i, "AI키워드"] = out
        except Exception as e:
            df.at[i, "AI키워드"] = f"AI 오류: {str(e)}"

        # 10개씩 실시간 업데이트(속도 느릴 때)
        if i % 10 == 0:
            st.dataframe(df.head(20))

    st.success("AI 분석이 끝났습니다! 아래에서 결과를 확인하세요.")
    st.dataframe(df)

    # 결과 다운로드 제공
    st.download_button(
        label="분석 결과 CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="숙소후기_AI키워드분석.csv",
        mime="text/csv"
    )
