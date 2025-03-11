import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from pathlib import Path

# ページ設定
st.set_page_config(
    page_title="12条点検 Web アプリ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if "deterioration_items" not in st.session_state:
    st.session_state.deterioration_items = []
if "next_deterioration_id" not in st.session_state:
    st.session_state.next_deterioration_id = 1
if "editing_item_index" not in st.session_state:
    st.session_state.editing_item_index = -1
if "saved_items" not in st.session_state:
    st.session_state.saved_items = []

# データディレクトリの確認・作成
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
INSPECTION_DATA_PATH = DATA_DIR / "inspection_data.csv"
LOCATION_MASTER_PATH = DATA_DIR / "location_master.csv"
DETERIORATION_MASTER_PATH = DATA_DIR / "deterioration_master.csv"

# マスターデータの読み込み
def load_master_data(file_path, default_data=None):
    try:
        if file_path.exists():
            # 複数のエンコーディングを試行
            encodings = ['shift_jis', 'utf-8', 'cp932', 'utf-8-sig']
            for encoding in encodings:
                try:
                    return pd.read_csv(file_path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            st.error(f"マスターデータの読み込みに失敗しました: {file_path}")
            return pd.DataFrame()
        else:
            if default_data:
                df = pd.DataFrame(default_data)
                df.to_csv(file_path, encoding="shift_jis", index=False)
                return df
            return pd.DataFrame()
    except Exception as e:
        st.error(f"マスターデータの読み込みエラー: {e}")
        return pd.DataFrame()

# デフォルトのマスターデータ
default_locations = {"場所": ["1階廊下", "2階廊下", "屋上", "外壁", "階段", "玄関", "機械室", "駐車場"]}
default_deteriorations = {"劣化名": ["ひび割れ", "剥離", "漏水", "腐食", "変形", "欠損", "さび", "変色"]}

# マスターデータの読み込み
location_master = load_master_data(LOCATION_MASTER_PATH, default_locations)
deterioration_master = load_master_data(DETERIORATION_MASTER_PATH, default_deteriorations)

# 保存済みデータの読み込み
def load_inspection_data():
    try:
        if INSPECTION_DATA_PATH.exists():
            # 複数のエンコーディングを試行
            encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
            for encoding in encodings:
                try:
                    return pd.read_csv(INSPECTION_DATA_PATH, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            st.error(f"点検データの読み込みに失敗しました")
            return pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"点検データの読み込みエラー: {e}")
        return pd.DataFrame()

# 劣化項目の追加
def add_deterioration_item():
    st.session_state.deterioration_items.append({
        "劣化番号": st.session_state.next_deterioration_id,
        "場所": st.session_state.location_input,
        "劣化名": st.session_state.deterioration_input,
        "写真番号": st.session_state.photo_number_input
    })
    st.session_state.next_deterioration_id += 1
    
    # 入力欄をクリア
    st.session_state.location_input = ""
    st.session_state.deterioration_input = ""
    st.session_state.photo_number_input = ""

# 劣化項目の削除
def remove_deterioration_item(index):
    if 0 <= index < len(st.session_state.deterioration_items):
        # 保存済みリストから削除
        item = st.session_state.deterioration_items[index]
        item_key = f"{item['劣化番号']}_{item['場所']}_{item['劣化名']}_{item['写真番号']}"
        if item_key in st.session_state.saved_items:
            st.session_state.saved_items.remove(item_key)
            
        # リストから削除
        st.session_state.deterioration_items.pop(index)

# 劣化項目の編集
def edit_item(index):
    if 0 <= index < len(st.session_state.deterioration_items):
        st.session_state.editing_item_index = index
        item = st.session_state.deterioration_items[index]
        st.session_state.location_input = item["場所"]
        st.session_state.deterioration_input = item["劣化名"]
        st.session_state.photo_number_input = item["写真番号"]

# データの保存
def save_inspection_data():
    if not st.session_state.deterioration_items:
        st.warning("保存する劣化項目がありません。")
        return 0
    
    # 基本情報の取得
    inspection_date = st.session_state.get("inspection_date", datetime.now())
    inspector_name = st.session_state.get("inspector_name", "")
    site_name = st.session_state.get("site_name", "")
    building_name = st.session_state.get("building_name", "")
    remarks = st.session_state.get("remarks", "")
    
    # 保存データの作成
    rows = []
    newly_saved_items = []
    
    for item in st.session_state.deterioration_items:
        # 既に保存済みの項目はスキップ
        item_key = f"{item['劣化番号']}_{item['場所']}_{item['劣化名']}_{item['写真番号']}"
        if item_key in st.session_state.saved_items:
            continue
            
        rows.append({
            "点検日": inspection_date.strftime("%Y-%m-%d"),
            "点検者名": inspector_name,
            "現場名": site_name,
            "棟名": building_name,
            "備考": remarks,
            "劣化番号": item["劣化番号"],
            "場所": item["場所"],
            "劣化名": item["劣化名"],
            "写真番号": item["写真番号"],
            "作成日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 保存済みリストに追加
        newly_saved_items.append(item_key)
    
    # 保存するデータがある場合のみ処理
    if rows:
        df_save = pd.DataFrame(rows)
        
        # 既存データとの結合
        if INSPECTION_DATA_PATH.exists():
            try:
                df_existing = pd.read_csv(INSPECTION_DATA_PATH, encoding="utf-8-sig")
                df_save = pd.concat([df_existing, df_save], ignore_index=True)
            except Exception as e:
                st.error(f"既存データの読み込み中にエラーが発生しました: {e}")
                return 0
        
        # CSVファイルへの保存
        try:
            df_save.to_csv(INSPECTION_DATA_PATH, encoding="utf-8-sig", index=False)
            
            # 保存済みリストを更新
            st.session_state.saved_items.extend(newly_saved_items)
            return len(newly_saved_items)
        except Exception as e:
            st.error(f"データの保存中にエラーが発生しました: {e}")
            return 0
    
    return 0

# メインアプリケーション
def main():
    st.title("12条点検 Web アプリ")
    
    # タブの作成
    tab1, tab2 = st.tabs(["点検入力", "データ閲覧"])
    
    # 点検入力タブ
    with tab1:
        st.header("点検情報入力")
        
        # 基本情報セクション
        with st.expander("基本情報", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.inspection_date = st.date_input(
                    "点検日",
                    value=st.session_state.get("inspection_date", datetime.now())
                )
                st.session_state.inspector_name = st.text_input(
                    "点検者名",
                    value=st.session_state.get("inspector_name", "")
                )
            with col2:
                st.session_state.site_name = st.text_input(
                    "現場名",
                    value=st.session_state.get("site_name", "")
                )
                st.session_state.building_name = st.text_input(
                    "棟名",
                    value=st.session_state.get("building_name", "")
                )
                st.session_state.remarks = st.text_area(
                    "備考",
                    value=st.session_state.get("remarks", "")
                )
        
        # 劣化内容セクション
        st.subheader("劣化内容")
        
        # 劣化項目の入力フォーム
        with st.form(key="deterioration_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 場所の入力（セレクトボックス）
                location_options = [""] + location_master["場所"].tolist()
                st.session_state.location_input = st.selectbox(
                    "場所",
                    options=location_options,
                    index=0 if "location_input" not in st.session_state else 
                          (location_options.index(st.session_state.location_input) 
                           if st.session_state.location_input in location_options else 0)
                )
            
            with col2:
                # 劣化名の入力（セレクトボックス）
                deterioration_options = [""] + deterioration_master["劣化名"].tolist()
                st.session_state.deterioration_input = st.selectbox(
                    "劣化名",
                    options=deterioration_options,
                    index=0 if "deterioration_input" not in st.session_state else 
                          (deterioration_options.index(st.session_state.deterioration_input) 
                           if st.session_state.deterioration_input in deterioration_options else 0)
                )
            
            with col3:
                # 写真番号の入力
                st.session_state.photo_number_input = st.text_input(
                    "写真番号",
                    value="" if "photo_number_input" not in st.session_state else st.session_state.photo_number_input
                )
            
            # 編集モード時のボタンテキストを変更
            button_text = "更新" if st.session_state.editing_item_index >= 0 else "劣化項目を追加"
            
            # フォーム送信ボタン
            submit_button = st.form_submit_button(button_text)
            
            if submit_button:
                if not st.session_state.location_input or not st.session_state.deterioration_input:
                    st.error("場所と劣化名は必須項目です")
                else:
                    if st.session_state.editing_item_index >= 0:
                        # 編集モードの場合
                        item = st.session_state.deterioration_items[st.session_state.editing_item_index]
                        
                        # 保存済みリストから古い項目を削除
                        old_item_key = f"{item['劣化番号']}_{item['場所']}_{item['劣化名']}_{item['写真番号']}"
                        if old_item_key in st.session_state.saved_items:
                            st.session_state.saved_items.remove(old_item_key)
                        
                        # 項目を更新
                        item["場所"] = st.session_state.location_input
                        item["劣化名"] = st.session_state.deterioration_input
                        item["写真番号"] = st.session_state.photo_number_input
                        
                        # 編集モードを終了
                        st.session_state.editing_item_index = -1
                        st.success(f"劣化項目を更新しました")
                    else:
                        # 新規追加モード
                        add_deterioration_item()
                        st.success(f"劣化項目を追加しました")
                    
                    # 入力欄をクリア
                    st.session_state.location_input = ""
                    st.session_state.deterioration_input = ""
                    st.session_state.photo_number_input = ""
                    st.rerun()
        
        # 劣化項目の表示と編集
        if st.session_state.deterioration_items:
            st.subheader("入力済み劣化項目")
            
            for i, item in enumerate(st.session_state.deterioration_items):
                with st.container():
                    # 保存済みかどうかを判定
                    item_key = f"{item['劣化番号']}_{item['場所']}_{item['劣化名']}_{item['写真番号']}"
                    is_saved = item_key in st.session_state.saved_items
                    
                    # 項目の表示
                    col1, col2, col3, col4, col5 = st.columns([1, 3, 3, 2, 1])
                    
                    with col1:
                        st.write(f"**No.{item['劣化番号']}**")
                        if is_saved:
                            st.write("✅ 保存済")
                    
                    with col2:
                        st.write(f"**場所**: {item['場所']}")
                    
                    with col3:
                        st.write(f"**劣化名**: {item['劣化名']}")
                    
                    with col4:
                        st.write(f"**写真番号**: {item['写真番号']}")
                    
                    with col5:
                        # 編集ボタン
                        if st.button("編集", key=f"edit_{i}"):
                            edit_item(i)
                            st.rerun()
                        
                        # 削除ボタン
                        if st.button("削除", key=f"delete_{i}"):
                            remove_deterioration_item(i)
                            st.rerun()
                
                st.divider()
        
        # 保存ボタン
        if st.button("保存", type="primary"):
            saved_count = save_inspection_data()
            
            if saved_count > 0:
                st.success(f"{saved_count}件のデータを保存しました")
            elif saved_count == 0:
                st.info("保存するデータがありません。すべての項目は既に保存済みです。")
    
    # データ閲覧タブ
    with tab2:
        st.header("点検データ閲覧")
        
        # データの読み込み
        inspection_data = load_inspection_data()
        
        if inspection_data.empty:
            st.info("保存された点検データがありません。")
        else:
            # 検索・フィルタリング機能
            search_term = st.text_input("検索（点検日、現場名、劣化番号、写真番号など）")
            
            if search_term:
                # 部分一致検索
                filtered_data = inspection_data[
                    inspection_data.astype(str).apply(
                        lambda row: row.str.contains(search_term, case=False).any(),
                        axis=1
                    )
                ]
            else:
                filtered_data = inspection_data
            
            # データの表示
            st.write(f"合計 {len(filtered_data)} 件のデータがあります")
            st.dataframe(filtered_data, use_container_width=True)
            
            # CSVダウンロード機能
            csv_data = filtered_data.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="CSVダウンロード",
                data=csv_data,
                file_name="inspection_data.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main() 