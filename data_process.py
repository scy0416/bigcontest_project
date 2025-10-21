import pandas as pd
from typing import Optional, List, Union
import re
from pathlib import Path
from glob import glob
import numpy as np

# ─────────────────────────────
# CSV 스마트 로더: 여러 인코딩/엔진 시도
# ─────────────────────────────
def _read_csv_smart(fp: str, **read_kwargs) -> pd.DataFrame:
    """
    CSV 인코딩을 여러 후보로 시도하여 안전하게 로드.
    우선순위: 사용자가 넘긴 encoding -> utf-8-sig -> cp949 -> euc-kr -> latin1
    구분자/따옴표 문제 시 engine="python" 재시도.
    마지막에는 errors='replace'로 최후 시도.
    """
    user_enc = read_kwargs.pop("encoding", None)
    candidates = [user_enc, "utf-8-sig", "cp949", "euc-kr", "latin1"]
    candidates = [enc for enc in candidates if enc]

    last_err = None
    for enc in candidates:
        try:
            return pd.read_csv(fp, encoding=enc, **read_kwargs)
        except UnicodeDecodeError as e:
            last_err = e
            # 인코딩 실패 → 다음 후보로
            continue
        except Exception:
            # 구분자/따옴표 문제 등 기타 오류 → engine='python'로 재시도
            try:
                return pd.read_csv(fp, encoding=enc, engine="python", **read_kwargs)
            except Exception as e2:
                last_err = e2
                continue

    # 모두 실패하면 가장 처음 후보(또는 None)로 치환 읽기 시도
    fallback_enc = candidates[0] if candidates else None
    try:
        return pd.read_csv(fp, encoding=fallback_enc, on_bad_lines="skip", engine="python")
    except Exception as e:
        raise e if last_err is None else last_err

# ─────────────────────────────
# (선택) 여러 CSV/XLSX를 한 번에 로드/병합
# ─────────────────────────────
def load_and_merge(paths: List[str], **read_kwargs) -> pd.DataFrame:
    """
    여러 CSV/XLSX 파일을 읽어 세로로 병합합니다.
    - paths 에는 파일 경로 리스트 또는 와일드카드 패턴('*')을 포함한 문자열을 넣을 수 있습니다.
    - 파일 확장자에 따라 자동으로 CSV/Excel 로더를 선택합니다.
    - 누락 컬럼은 병합 시 자동으로 채워지며(outer-like), 병합 전 후 컬럼 일관성을 유지합니다.
    """
    # 와일드카드 패턴을 허용
    expanded: List[str] = []
    for p in paths:
        if any(ch in str(p) for ch in ['*', '?', '[']):
            expanded.extend(glob(str(p)))
        else:
            expanded.append(str(p))

    if not expanded:
        raise FileNotFoundError("로드할 파일이 없습니다. (paths 인자 확인)")

    frames: List[pd.DataFrame] = []
    for fp in expanded:
        suf = Path(fp).suffix.lower()
        if suf in {'.xlsx', '.xls'}:
            df_part = pd.read_excel(fp, **{k: v for k, v in read_kwargs.items() if k != 'encoding'})
        else:
            df_part = _read_csv_smart(fp, **read_kwargs)
        frames.append(df_part)

    # 서로 다른 컬럼을 가진 경우 outer-concat 효과를 내기 위해 align
    all_cols = sorted(set().union(*[f.columns for f in frames]))
    aligned = [f.reindex(columns=all_cols) for f in frames]
    return pd.concat(aligned, ignore_index=True)


# ─────────────────────────────
# 유틸: 문자열 정규화(공백/대소문자/양끝 공백)
# ─────────────────────────────
def _norm(x: Union[str, float, int]) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip().lower().replace(" ", "")


# 고속 정규화 캐시 컬럼 생성/반환
def _norm_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .fillna("")
         .str.strip()
         .str.lower()
         .str.replace(r"\s+", "", regex=True)
    )


def _get_norm_col(df: pd.DataFrame, col: str) -> pd.Series:
    cache_col = f"__norm__{col}"
    if cache_col not in df.columns:
        if col not in df.columns:
            raise KeyError(f"'{col}' 컬럼이 데이터프레임에 없습니다. (보유 컬럼: {list(df.columns)[:10]}...)")
        df[cache_col] = _norm_series(df[col])
    return df[cache_col]


def _ensure_datetime(df: pd.DataFrame, date_col: Optional[str]) -> Optional[pd.Series]:
    if date_col is None:
        return None
    if date_col not in df.columns:
        raise KeyError(f"'{date_col}' 날짜 컬럼이 없습니다.")
    if not np.issubdtype(df[date_col].dtype, np.datetime64):
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df[date_col]


def _validate_cols(df: pd.DataFrame, cols: Optional[List[str]]):
    if cols:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"요청 컬럼이 없습니다: {missing}")


# ─────────────────────────────
# 1) 특정 점포 정보 가져오기
# ─────────────────────────────
def get_store_info(
    df: pd.DataFrame,
    key: Union[str, int],
    by: str = "가맹점명",
    cols: Optional[List[str]] = None,
    mode: str = "contains",   # 'contains' | 'exact' | 'startswith'
    drop_duplicates_subset: Optional[List[str]] = None,
    date_col: Optional[str] = None,
    latest_only: bool = False,
    start: Optional[Union[str, pd.Timestamp]] = None,
    end: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """
    특정 점포의 행(들)을 반환합니다.
    - mode로 부분일치/완전일치/접두 일치 선택 가능
    - date_col 지정 시 start~end 범위 또는 latest_only(가장 최신 월/일) 필터 가능
    - drop_duplicates_subset 으로 중복 제거 가능 (예: ['점포ID'])
    """
    # 검색 마스크
    series_norm = _get_norm_col(df, by)
    key_norm = _norm(key)

    if mode == "exact":
        mask = series_norm == key_norm
    elif mode == "startswith":
        mask = series_norm.str.startswith(key_norm, na=False)
    else:  # contains
        mask = series_norm.str.contains(key_norm, na=False)

    out = df.loc[mask].copy()

    # 날짜 필터
    dt = _ensure_datetime(out, date_col)
    if dt is not None:
        if start is not None:
            out = out[dt >= pd.to_datetime(start)]
        if end is not None:
            out = out[dt <= pd.to_datetime(end)]
        if latest_only and not out.empty:
            latest_ts = out[date_col].max()
            out = out[out[date_col] == latest_ts]

    # 중복 제거
    if drop_duplicates_subset:
        out = out.drop_duplicates(subset=drop_duplicates_subset)

    # 출력 컬럼 제한
    _validate_cols(df, cols)
    if cols:
        out = out[cols]

    if out.empty:
        raise ValueError(f"'{by}={key}' 조건에 해당하는 점포를 찾지 못했습니다.")
    return out


# ─────────────────────────────
# 2) 특정 업종의 모든 정보 가져오기
# ─────────────────────────────
def get_industry_info(
    df: pd.DataFrame,
    key: Union[str, int],
    by: str = "업종명",
    cols: Optional[List[str]] = None,
    mode: str = "contains",   # 'contains' | 'exact' | 'startswith'
    region_col: Optional[str] = None,
    region: Optional[str] = None,
    drop_duplicates_subset: Optional[List[str]] = None,
    date_col: Optional[str] = None,
    latest_only: bool = False,
    start: Optional[Union[str, pd.Timestamp]] = None,
    end: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """
    특정 업종(명/코드 등)에 속한 모든 점포 행을 반환합니다.
    - mode로 부분일치/완전일치/접두 일치 선택 가능
    - region_col/region 지정 시 특정 지역으로 추가 필터링
    - date_col 지정 시 start~end 범위 또는 latest_only(가장 최신 월/일) 필터 가능
    - drop_duplicates_subset 으로 중복 제거 가능 (예: ['점포ID'])
    """
    series_norm = _get_norm_col(df, by)
    key_norm = _norm(key)

    if mode == "exact":
        mask = series_norm == key_norm
    elif mode == "startswith":
        mask = series_norm.str.startswith(key_norm, na=False)
    else:
        mask = series_norm.str.contains(key_norm, na=False)

    out = df.loc[mask].copy()

    # 지역 필터 (선택)
    if region_col and region is not None:
        region_norm_series = _get_norm_col(out, region_col)
        region_norm_key = _norm(region)
        out = out.loc[region_norm_series == region_norm_key]

    # 날짜 필터
    dt = _ensure_datetime(out, date_col)
    if dt is not None:
        if start is not None:
            out = out[dt >= pd.to_datetime(start)]
        if end is not None:
            out = out[dt <= pd.to_datetime(end)]
        if latest_only and not out.empty:
            latest_ts = out[date_col].max()
            out = out[out[date_col] == latest_ts]

    if drop_duplicates_subset:
        out = out.drop_duplicates(subset=drop_duplicates_subset)

    _validate_cols(df, cols)
    if cols:
        out = out[cols]

    if out.empty:
        raise ValueError(f"'{by}={key}' 조건에 해당하는 업종 데이터를 찾지 못했습니다.")
    return out


# ─────────────────────────────
# 사용 예시
# ─────────────────────────────
if __name__ == "__main__":
    # 1) (선택) 여러 CSV 합치기 — 와일드카드도 지원
    df = load_and_merge(["./dataset/big_data_set*_f.csv"])  # 인코딩 자동 감지/대응
    #print(f"[INFO] Loaded rows: {len(df):,} | columns: {list(df.columns)[:8]}...")
    print(df.iloc[0])

    # === 컬럼 매핑 (현재 데이터셋 기준) ===
    SCHEMA = {
        "store_id": "ENCODED_MCT",            # 점포 식별자
        "industry_bzn": "HPSN_MCT_BZN_CD_NM", # 업종 대분류 명
        "industry_zcd": "HPSN_MCT_ZCD_NM",    # 업종 중분류 명
        "region": "ARE_D",                    # 지역
        "date": None,                           # 날짜 컬럼이 있으면 이름 입력 (예: "STD_YYYYMM")
    }

    # 방어: 필요한 컬럼이 실제로 존재하는지 확인
    required_cols = [SCHEMA["store_id"], SCHEMA["industry_bzn"], SCHEMA["region"]]
    for rc in required_cols:
        if rc not in df.columns:
            raise KeyError(f"필수 컬럼 누락: {rc} (보유 컬럼 예시: {list(df.columns)[:10]}...)")

    # 데모용 점포 하나 선택 (첫 번째 행의 점포ID 사용)
    sample_store_id = df[SCHEMA["store_id"]].dropna().astype(str).iloc[0]

    # ① 특정 점포 정보: ID로 완전일치 조회 (날짜 컬럼 없으므로 date_col 생략)
    store_df = get_store_info(
        df,
        key=sample_store_id,
        by=SCHEMA["store_id"],
        mode="exact",
        drop_duplicates_subset=[SCHEMA["store_id"]],
    )

    #print("\n[STORE] sample store by ID (exact):", sample_store_id)
    #print(store_df.head())

    # ② 특정 업종 전체: 업종 대분류명 일부 텍스트로 부분일치
    #    키워드를 자동으로 하나 뽑아 데모 수행 (NaN/빈값 제외)
    sample_industry_keyword = (
        df[SCHEMA["industry_bzn"]].dropna().astype(str).str.strip().iloc[0][:2]  # 앞 2글자 정도로 부분검색
    )

    industry_df = get_industry_info(
        df,
        key=sample_industry_keyword,
        by=SCHEMA["industry_bzn"],
        mode="contains",
        region_col=SCHEMA["region"],
        region=None,  # 특정 지역만 보려면 예: "서울"
        drop_duplicates_subset=[SCHEMA["store_id"]],
    )

    #print("\n[INDUSTRY] sample industry by keyword (contains):", sample_industry_keyword)
    #print(industry_df.head())

    # 참고: 현재 컬럼 탐색 헬퍼
    # print("\n[INFO] Columns (first 30):\n", df.columns.tolist()[:30])
    # print("[INFO] MCT-related columns:", [c for c in df.columns if "MCT" in c])
    # print("[INFO] BZN-related columns:", [c for c in df.columns if "BZN" in c])
    # print("[INFO] ZCD-related columns:", [c for c in df.columns if "ZCD" in c])