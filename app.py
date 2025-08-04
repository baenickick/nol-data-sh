import streamlit as st
import pandas as pd
from collections import Counter
from openai import OpenAI
import os

# 최신 openai 방식 - 클라이언트 객체 생성
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

EXCLUDE = {"여름", "겨울", "가을", "봄"}

st.title("숙소후기 AI 키워드 자동 추출 (OpenAI 최신버전 SDK)")

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
        "'여름, 겨울, 봄, 가을'과 같은 계절 단어 제외, 시설/분위기/느낌 위주의 한글 명사(키워드) 5~8개를 콤마(,)로 뽑아줘:\n"
        f"{review}"
    )
    try:
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return chat_response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 오류: {e}"

if uploaded_file is not None:
    df = smart_read_csv(uploaded_file)
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    st.dataframe(df.head())

    review_col = None
    for col in df.columns:
        if "후기" in col or "review" in col.lower():
            review_col = col
            break
    if not review_col:
        st.error(f"'숙소후기' 또는 review 컬럼 없음! 현재 컬럼: {list(df.columns)}")
        st.stop()

    location_col = None
    for col in df.columns:
        if "위치" in col or "주소" in col or "region" in col.lower():
            location_col = col
            break

    if "AI키워드" not in df.columns:
        df["AI키워드"] = ""

    st.write("AI가 후기별 주요 키워드를 추출 중입니다... (계절명 자동제거, 시설/느낌/분위기 위주)")
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

    st.success("숙소별 중복 없이 주요 키워드를 요약합니다")

    # 숙소별 대표 키워드 집계
    summary = []
    for keys, group in df.groupby(["숙소명", location_col] if location_col else ["숙소명"]):
        all_keywords = []
        for kws in group["AI키워드"]:
            if kws:
                all_keywords.extend([kw.strip() for kw in kws.split(",") if kw.strip() and kw.strip() not in EXCLUDE])
        ranked = [k for k, _ in Counter(all_keywords).most_common(8)]
        summary.append({
            "숙소명": keys[0],
            "위치": keys[1] if location_col else "",
            "주요 키워드": ", ".join(ranked)
        })
    summary_df = pd.DataFrame(summary)
    st.subheader("숙소별 대표 키워드 요약표 (계절명 제외)")
    st.dataframe(summary_df)

    # (선택) streamlit-tags로 태그 디자인
    try:
        from streamlit_tags import st_tags
        for i, row in summary_df.iterrows():
            st.markdown(f"**{row['숙소명']} / {row['위치']}**")
            tags = [k.strip() for k in row["주요 키워드"].split(",")]
            st_tags(label='', text='주요 키워드:', value=tags, maxtags=8, key=i)
    except ImportError:
        st.info("streamlit-tags 설치 시 태그 디자인 지원.")

    st.download_button(
        label="요약 결과 CSV 다운로드",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="숙소별주요키워드_요약.csv",
        mime="text/csv"
    )
