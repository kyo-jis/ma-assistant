import datetime
import json
import os
import re
import shutil
import streamlit as st

# ==========================================
# ページ基本設定
# ==========================================
st.set_page_config(
    page_title="音声編集（MA）業務アシスタント",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 曜日変換ヘルパー
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

def format_date_jp(d: datetime.date) -> str:
    """日付を '11/3（火）' のような曜日付きフォーマットに変換"""
    weekday = WEEKDAY_JP[d.weekday()]
    return f"{d.month}/{d.day}（{weekday}）"

# ==========================================
# 固定単価番組（マスタデータ）の読み書き
# ==========================================
PROGRAMS_FILE = os.path.join(os.path.dirname(__file__), "custom_programs.json")

def load_custom_programs() -> list[dict]:
    default_programs = [
        {"name": "中島知子のおんせんさんぽ", "price": 3000}
    ]
    if not os.path.exists(PROGRAMS_FILE):
        try:
            with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_programs, f, ensure_ascii=False, indent=2)
        except Exception:
            return default_programs
        return default_programs
    try:
        with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return default_programs
    except Exception:
        return default_programs

def save_custom_programs(programs: list[dict]):
    try:
        with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(programs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"番組データの保存に失敗しました: {e}")

# ==========================================
# 署名データ（本名 / ココナラ / ランサーズ）の読み書き
# ==========================================
SIGNATURES_FILE = os.path.join(os.path.dirname(__file__), "signatures_data.json")
SIG_OPTIONS = ["なし", "ココナラ用", "ランサーズ用", "本名・ビジネス用"]

def load_signatures() -> dict:
    default_sig = {
        "coconala": "MAクリエイター（ココナラ）",
        "lancers": "MAクリエイター（ランサーズ）",
        "realname": "山田 太郎\n音声編集・MAミキサー\nMail: info@example.com"
    }
    if not os.path.exists(SIGNATURES_FILE):
        try:
            with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
                json.dump(default_sig, f, ensure_ascii=False, indent=2)
        except Exception:
            return default_sig
        return default_sig
    try:
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                if "lancers" not in data:
                    data["lancers"] = data.get("coconala", "MAクリエイター（ランサーズ）")
                return data
            return default_sig
    except Exception:
        return default_sig

def save_signatures(sig_data: dict):
    try:
        with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
            json.dump(sig_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"署名データの保存に失敗しました: {e}")

def get_signature_text(sig_type: str) -> str:
    if not sig_type or sig_type == "なし":
        return ""
    sigs = load_signatures()
    if sig_type in ["ココナラ用", "ココナラ・ランサーズ用"]:
        sig_body = sigs.get("coconala", "").strip()
    elif sig_type == "ランサーズ用":
        sig_body = sigs.get("lancers", sigs.get("coconala", "")).strip()
    elif sig_type == "本名・ビジネス用":
        sig_body = sigs.get("realname", "").strip()
    else:
        sig_body = ""
    if not sig_body:
        return ""
    return f"\n\n{sig_body}"

# ==========================================
# Google ドライブ / 外部フォルダ同期設定・処理
# ==========================================
SYNC_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "sync_config.json")
DEFAULT_SYNC_DIR = r"G:\マイドライブ\KO SUTUDIO_仕事用\見積もりアシスタント"

def load_sync_config() -> dict:
    default_cfg = {
        "sync_dir": DEFAULT_SYNC_DIR,
        "auto_sync": True
    }
    if not os.path.exists(SYNC_CONFIG_FILE):
        return default_cfg
    try:
        with open(SYNC_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else default_cfg
    except Exception:
        return default_cfg

def save_sync_config(cfg: dict):
    try:
        with open(SYNC_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def sync_backup_to_dir(target_dir: str) -> tuple[bool, str]:
    if not target_dir or not os.path.exists(target_dir):
        return False, "指定された同期先フォルダが見つかりません。"
    try:
        # projects_data.json のコピー
        if os.path.exists(PROJECTS_FILE):
            dest_proj = os.path.join(target_dir, "projects_data.json")
            shutil.copy2(PROJECTS_FILE, dest_proj)
        # signatures_data.json のコピー
        if os.path.exists(SIGNATURES_FILE):
            dest_sig = os.path.join(target_dir, "signatures_data.json")
            shutil.copy2(SIGNATURES_FILE, dest_sig)
        # 日付入りバックアップも保存（履歴用）
        today_str = datetime.date.today().strftime("%Y%m%d")
        dest_dated = os.path.join(target_dir, f"backup_projects_{today_str}.json")
        if os.path.exists(PROJECTS_FILE):
            shutil.copy2(PROJECTS_FILE, dest_dated)
        return True, f"Googleドライブにバックアップを保存しました！（{os.path.basename(dest_proj)}）"
    except Exception as e:
        return False, f"同期エラー: {e}"

def restore_from_sync_dir(target_dir: str) -> tuple[bool, str]:
    if not target_dir or not os.path.exists(target_dir):
        return False, "指定された同期先フォルダが見つかりません。"
    src_proj = os.path.join(target_dir, "projects_data.json")
    if not os.path.exists(src_proj):
        return False, f"同期先に案件データ ({os.path.basename(src_proj)}) が見つかりません。"
    try:
        shutil.copy2(src_proj, PROJECTS_FILE)
        src_sig = os.path.join(target_dir, "signatures_data.json")
        if os.path.exists(src_sig):
            shutil.copy2(src_sig, SIGNATURES_FILE)
        return True, "Googleドライブのデータから最新状態に復元しました！"
    except Exception as e:
        return False, f"復元エラー: {e}"

# ==========================================
# プロジェクト（案件データ）の読み書き・永続化
# ==========================================
PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects_data.json")

def load_projects() -> list[dict]:
    if not os.path.exists(PROJECTS_FILE):
        default_samples = [
            {
                "id": "sample_proj_1",
                "name": "株式会社ABC 様 - YouTube対談動画 MA作業",
                "client_name": "株式会社ABC 様",
                "project_name": "YouTube対談動画 MA作業",
                "status": "🎧 制作中（初稿前）",
                "memo": "48kHz/24bit書き出し。BGM音量控えめで要望あり。",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "quote_items": [
                    {"id": 1, "genre": "YouTube・配信", "duration": 20.0}
                ],
                "comm_data": {
                    "file_type": "初稿ミックス音源",
                    "pattern": "🎧 初稿・ラフミックス送付（確認依頼）",
                    "url": "https://63.gigafile.nu/1104-sample123456",
                    "url_meta": "DLキー: 1234 / 保持期限: 7日間",
                    "free_text": "声の聞き取りやすさを重視して整音・音量調整を行っております。BGMとのバランスをご確認ください。",
                    "closing": "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。"
                },
                "eval_data": {
                    "impression": "とてもスムーズ",
                    "appeal_flag": True
                }
            }
        ]
        try:
            with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_samples, f, ensure_ascii=False, indent=2)
        except Exception:
            return default_samples
        return default_samples

    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def save_projects(projects: list[dict]):
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"案件データの保存に失敗しました: {e}")

# プロジェクトセッション管理の初期化
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = "new"

if "proj_client_name" not in st.session_state:
    st.session_state.proj_client_name = ""
if "proj_orig_client_name" not in st.session_state:
    st.session_state.proj_orig_client_name = ""
if "proj_client_honorific" not in st.session_state:
    st.session_state.proj_client_honorific = "様"
if "proj_project_name" not in st.session_state:
    st.session_state.proj_project_name = ""
if "proj_status" not in st.session_state:
    st.session_state.proj_status = "📝 お見積り中"
if "proj_memo" not in st.session_state:
    st.session_state.proj_memo = ""
if "proj_signature_type" not in st.session_state:
    st.session_state.proj_signature_type = "なし"

# 各タブ同期用キーの初期化
for k in ["t1_client_name", "t2_client_name", "t3_client_name"]:
    if k not in st.session_state:
        st.session_state[k] = st.session_state.proj_client_name

for k in ["t1_client_honorific", "t2_client_honorific", "t3_client_honorific"]:
    if k not in st.session_state:
        st.session_state[k] = st.session_state.proj_client_honorific

for k in ["t1_project_name", "t2_project_name", "t3_project_name"]:
    if k not in st.session_state:
        st.session_state[k] = st.session_state.proj_project_name

for k in ["t1_sig_choice", "t2_sig_choice", "t3_sig_choice", "sb_sig_choice"]:
    if k not in st.session_state:
        st.session_state[k] = st.session_state.proj_signature_type

def sync_signature_type(source_key: str):
    new_val = st.session_state.get(source_key, "なし")
    st.session_state.proj_signature_type = new_val
    st.session_state.t1_sig_choice = new_val
    st.session_state.t2_sig_choice = new_val
    st.session_state.t3_sig_choice = new_val
    st.session_state.sb_sig_choice = new_val

def sync_client_name(source_key: str):
    new_val = st.session_state.get(source_key, "")
    st.session_state.proj_client_name = new_val
    st.session_state.t1_client_name = new_val
    st.session_state.t2_client_name = new_val
    st.session_state.t3_client_name = new_val

def sync_client_honorific(source_key: str):
    new_val = st.session_state.get(source_key, "様")
    st.session_state.proj_client_honorific = new_val
    st.session_state.t1_client_honorific = new_val
    st.session_state.t2_client_honorific = new_val
    st.session_state.t3_client_honorific = new_val

def sync_project_name(source_key: str):
    new_val = st.session_state.get(source_key, "")
    st.session_state.proj_project_name = new_val
    st.session_state.t1_project_name = new_val
    st.session_state.t2_project_name = new_val
    st.session_state.t3_project_name = new_val

def format_client_display(name: str, honorific: str = "様") -> str:
    cleaned = name.strip() if name else ""
    if not cleaned:
        return ""
    if not honorific or honorific == "なし":
        return cleaned
    # すでに敬称が付いている場合は二重付与しない
    known_suffixes = ["様", "さん", "御中", "殿", "先生", "くん", "君", "ちゃん"]
    for sfx in known_suffixes:
        if cleaned.endswith(sfx):
            return cleaned
    return f"{cleaned} {honorific}"

def clear_quote_widget_keys():
    keys_to_delete = [
        k for k in list(st.session_state.keys())
        if any(k.startswith(prefix) for prefix in [
            "genre_", "dur_", "step_", "cond_", "custom_h_",
            "cm_pat_", "cm_price_", "cm_cnt_", "cm_cond_", "cm_adj_custom_",
            "fixed_sel_", "fn_", "fp_", "fc_", "wh_",
            "sched_del_", "sched_han_", "sched_rec_",
            "d_date_", "d_time_", "d_custom_", "h_rcv_", "h_rcv_sel_", "h_rcv_custom_", "h_date_", "h_time_",
            "w_date_", "w_time_", "w_custom_", "del_w_", "work_day_ids_", "next_work_day_id_",
            "s_chk_", "m_chk_", "f_chk_", "free_delivery_input", "free_handover_input", "free_work_input",
            "quote_tax_option", "quote_sched_mode", "quote_sched_disp_style", "quote_sched_res_type", "quote_inc_delay_note",
            "chk_inc_work_contents", "chk_task1", "chk_task2", "chk_task3", "chk_task4", "txt_custom_task",
            "quote_audio_spec", "quote_inc_lufs14", "quote_inc_raw_note", "quote_audio_fmt",
            "quote_retake_choice", "custom_retake_policy", "quote_inc_rework_note",
            "sig_choice_t1", "sig_comm", "sig_eval",
            "t1_sig_choice", "t2_sig_choice", "t3_sig_choice", "sb_sig_choice",
            "override_flag_", "override_val_", "quote_overall_adj"
        ])
    ]
    for k in keys_to_delete:
        del st.session_state[k]

def load_project_into_session(project: dict):
    clear_quote_widget_keys()

    st.session_state.active_project_id = project["id"]
    st.session_state.proj_client_name = project.get("client_name", "")
    st.session_state.proj_orig_client_name = project.get("client_name", "").strip()
    st.session_state.proj_client_honorific = project.get("client_honorific", "様")
    st.session_state.proj_project_name = project.get("project_name", "")
    st.session_state.proj_status = project.get("status", "📝 お見積り中")
    st.session_state.proj_memo = project.get("memo", "")

    st.session_state.t1_client_name = st.session_state.proj_client_name
    st.session_state.t1_client_honorific = st.session_state.proj_client_honorific
    st.session_state.t1_project_name = st.session_state.proj_project_name

    st.session_state.t2_client_name = st.session_state.proj_client_name
    st.session_state.t2_client_honorific = st.session_state.proj_client_honorific
    st.session_state.t2_project_name = st.session_state.proj_project_name

    st.session_state.t3_client_name = st.session_state.proj_client_name
    st.session_state.t3_client_honorific = st.session_state.proj_client_honorific
    st.session_state.t3_project_name = st.session_state.proj_project_name

    # 1. 見積もりアイテム復元
    if "quote_items" in project and project["quote_items"]:
        st.session_state.quote_items = project["quote_items"]
        max_id = max([it.get("id", 1) for it in project["quote_items"]], default=1)
        st.session_state.next_item_id = max_id + 1

        for it in project["quote_items"]:
            iid = it.get("id", 1)
            st.session_state[f"genre_{iid}"] = it.get("genre", "番組")
            if "duration" in it:
                st.session_state[f"dur_{iid}"] = float(it["duration"])
            if "condition" in it:
                st.session_state[f"cond_{iid}"] = it["condition"]
            if "cm_pattern" in it:
                st.session_state[f"cm_pat_{iid}"] = it["cm_pattern"]
            if "cm_unit_price" in it:
                st.session_state[f"cm_price_{iid}"] = int(it["cm_unit_price"])
            if "cm_count" in it:
                st.session_state[f"cm_cnt_{iid}"] = int(it["cm_count"])
            if "cm_condition" in it:
                st.session_state[f"cm_cond_{iid}"] = it["cm_condition"]
            if "cm_custom_adj" in it:
                st.session_state[f"cm_adj_custom_{iid}"] = int(it["cm_custom_adj"])
            if "fixed_choice" in it:
                st.session_state[f"fixed_sel_{iid}"] = it["fixed_choice"]
            if "fixed_name" in it:
                st.session_state[f"fn_{iid}"] = it["fixed_name"]
            if "fixed_price" in it:
                st.session_state[f"fp_{iid}"] = int(it["fixed_price"])
            if "fixed_count" in it:
                st.session_state[f"fc_{iid}"] = int(it["fixed_count"])
            if "work_hours" in it:
                st.session_state[f"wh_{iid}"] = float(it["work_hours"])
            if "manual_price_enabled" in it:
                st.session_state[f"override_flag_{iid}"] = bool(it["manual_price_enabled"])
            if "manual_price" in it:
                st.session_state[f"override_val_{iid}"] = int(it["manual_price"])

    # 2. 見積もり詳細設定（税・スケジュール・仕様・修正規定・署名等）の復元
    qs = project.get("quote_settings", {})
    if qs:
        if "tax_option" in qs:
            st.session_state.quote_tax_option = qs["tax_option"]
        if "schedule_mode" in qs:
            st.session_state.quote_sched_mode = qs["schedule_mode"]
        if "sched_display_style" in qs:
            st.session_state.quote_sched_disp_style = qs["sched_display_style"]
        if "schedule_reservation_type" in qs:
            st.session_state.quote_sched_res_type = qs["schedule_reservation_type"]
        if "include_delay_note" in qs:
            st.session_state.quote_inc_delay_note = qs["include_delay_note"]

        for k in ["use_delivery", "use_handover", "use_work"]:
            if k in qs:
                short_k = k.replace("use_", "")
                for pfx in ["s_chk_", "m_chk_", "f_chk_"]:
                    st.session_state[f"{pfx}{short_k}"] = qs[k]

        if "free_delivery_input" in qs:
            st.session_state.free_delivery_input = qs["free_delivery_input"]
        if "free_handover_input" in qs:
            st.session_state.free_handover_input = qs["free_handover_input"]
        if "free_work_input" in qs:
            st.session_state.free_work_input = qs["free_work_input"]

        sched_items = qs.get("schedule_items_data", {})
        for sk, sval in sched_items.items():
            if any(sk.startswith(dp) for dp in ["d_date_", "h_date_", "w_date_"]):
                try:
                    st.session_state[sk] = datetime.date.fromisoformat(sval)
                except Exception:
                    pass
            else:
                st.session_state[sk] = sval

        if "include_work_contents" in qs:
            st.session_state.chk_inc_work_contents = qs["include_work_contents"]
        for tk in ["c_task1", "c_task2", "c_task3", "c_task4"]:
            if tk in qs:
                st.session_state[tk.replace("c_", "chk_")] = qs[tk]
        if "c_custom_task" in qs:
            st.session_state.txt_custom_task = qs["c_custom_task"]

        if "audio_spec" in qs:
            st.session_state.quote_audio_spec = qs["audio_spec"]
        if "include_lufs14_note" in qs:
            st.session_state.quote_inc_lufs14 = qs["include_lufs14_note"]
        if "include_raw_audio_note" in qs:
            st.session_state.quote_inc_raw_note = qs["include_raw_audio_note"]
        if "audio_format" in qs:
            st.session_state.quote_audio_fmt = qs["audio_format"]

        if "retake_policy_choice" in qs:
            st.session_state.quote_retake_choice = qs["retake_policy_choice"]
        if "custom_retake" in qs:
            st.session_state.custom_retake_policy = qs["custom_retake"]
        if "include_rework_fee_note" in qs:
            st.session_state.quote_inc_rework_note = qs["include_rework_fee_note"]

        if "sig_choice_t1" in qs:
            st.session_state.sig_choice_t1 = qs["sig_choice_t1"]
        if "overall_adj_price" in qs:
            st.session_state.quote_overall_adj = int(qs["overall_adj_price"])
        if "overall_adj_note" in qs:
            st.session_state.quote_overall_adj_note = qs["overall_adj_note"]

    # 3. 連絡タブの復元
    comm_data = project.get("comm_data", {})
    st.session_state.comm_file_type = comm_data.get("file_type", "ミックスファイル")
    st.session_state.comm_pattern = comm_data.get("pattern", "🎵 ファイル送付（基本・シンプル）")
    st.session_state.comm_url = comm_data.get("url", "")
    st.session_state.comm_url_meta = comm_data.get("url_meta", "")
    st.session_state.comm_free_text = comm_data.get("free_text", "")
    st.session_state.comm_closing = comm_data.get("closing", "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。")
    if "sig_comm" in comm_data:
        st.session_state.sig_comm = comm_data["sig_comm"]

    # 4. 納品タブの復元
    eval_data = project.get("eval_data", {})
    st.session_state.eval_impression = eval_data.get("impression", "とてもスムーズ")
    st.session_state.eval_appeal_flag = eval_data.get("appeal_flag", True)
    if "sig_eval" in eval_data:
        st.session_state.sig_eval = eval_data["sig_eval"]

    # 5. 署名設定の全タブ復元
    saved_sig = project.get("signature_type") or qs.get("sig_choice_t1", comm_data.get("sig_comm", eval_data.get("sig_eval", "なし")))
    if saved_sig == "ココナラ・ランサーズ用":
        saved_sig = "ココナラ用"
    if saved_sig not in SIG_OPTIONS:
        saved_sig = "なし"
    st.session_state.proj_signature_type = saved_sig
    st.session_state.t1_sig_choice = saved_sig
    st.session_state.t2_sig_choice = saved_sig
    st.session_state.t3_sig_choice = saved_sig
    st.session_state.sb_sig_choice = saved_sig

def reset_to_new_project():
    clear_quote_widget_keys()

    st.session_state.active_project_id = "new"
    st.session_state.proj_client_name = ""
    st.session_state.proj_orig_client_name = ""
    st.session_state.proj_client_honorific = "様"
    st.session_state.proj_project_name = ""
    st.session_state.proj_status = "📝 お見積り中"
    st.session_state.proj_memo = ""

    st.session_state.t1_client_name = ""
    st.session_state.t1_client_honorific = "様"
    st.session_state.t1_project_name = ""

    st.session_state.t2_client_name = ""
    st.session_state.t2_client_honorific = "様"
    st.session_state.t2_project_name = ""

    st.session_state.t3_client_name = ""
    st.session_state.t3_client_honorific = "様"
    st.session_state.t3_project_name = ""

    st.session_state.quote_items = [{"id": 1, "genre": "番組", "duration": 15.0}]
    st.session_state.next_item_id = 2

    # 見積もり詳細設定のデフォルト
    st.session_state.quote_tax_option = "税込（内税表記）"
    st.session_state.quote_sched_mode = "📅 カレンダーから設定（おすすめ）"
    st.session_state.quote_sched_disp_style = "📋 案件ごとにまとめて表示（おすすめ）"
    st.session_state.quote_sched_res_type = "なし（記載しない）"
    st.session_state.quote_inc_delay_note = True
    st.session_state.chk_inc_work_contents = True
    st.session_state.chk_task1 = True
    st.session_state.chk_task2 = True
    st.session_state.chk_task3 = True
    st.session_state.chk_task4 = True
    st.session_state.txt_custom_task = ""
    st.session_state.quote_audio_spec = "平均ラウドネス値 -24.0 LKFS (TP -1.0dBTP以下)"
    st.session_state.quote_inc_lufs14 = False
    st.session_state.quote_inc_raw_note = False
    st.session_state.quote_audio_fmt = "WAV (48kHz / 24bit)"
    st.session_state.quote_retake_choice = "記載しない"
    st.session_state.custom_retake_policy = ""
    st.session_state.quote_inc_rework_note = False
    st.session_state.sig_choice_t1 = "なし"
    st.session_state.quote_overall_adj = 0
    st.session_state.quote_overall_adj_note = "端数調整・お値引き"

    # 連絡タブのデフォルト
    st.session_state.comm_file_type = "ミックスファイル"
    st.session_state.comm_pattern = "🎵 ファイル送付（基本・シンプル）"
    st.session_state.comm_url = ""
    st.session_state.comm_url_meta = ""
    st.session_state.comm_free_text = ""
    st.session_state.comm_closing = "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。"
    st.session_state.sig_comm = "なし"

    # 納品タブのデフォルト
    st.session_state.eval_impression = "とてもスムーズ"
    st.session_state.eval_appeal_flag = True
    st.session_state.sig_eval = "なし"

    # 署名選択の全タブ初期化
    st.session_state.proj_signature_type = "なし"
    st.session_state.t1_sig_choice = "なし"
    st.session_state.t2_sig_choice = "なし"
    st.session_state.t3_sig_choice = "なし"
    st.session_state.sb_sig_choice = "なし"

def save_current_project_data(force_as_new: bool = False, target_id: str = None) -> str:
    projects = load_projects()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 最新のquote_items情報をセッションステートから同期
    updated_items = []
    for it in st.session_state.quote_items:
        iid = it["id"]
        genre = st.session_state.get(f"genre_{iid}", it.get("genre", "番組"))
        item_copy = {
            "id": iid,
            "genre": genre
        }
        if genre in ["YouTube・配信", "番組", "ドラマ・自主映画"]:
            item_copy["duration"] = st.session_state.get(f"dur_{iid}", it.get("duration", 15.0))
            item_copy["condition"] = st.session_state.get(f"cond_{iid}", "標準（収録状態良好: ±0h）")
        elif genre == "CM（15秒・30秒）":
            item_copy["cm_pattern"] = st.session_state.get(f"cm_pat_{iid}", "通常")
            item_copy["cm_unit_price"] = st.session_state.get(f"cm_price_{iid}", 3000)
            item_copy["cm_count"] = st.session_state.get(f"cm_cnt_{iid}", 1)
            item_copy["cm_condition"] = st.session_state.get(f"cm_cond_{iid}", "標準（追加補正なし: ±0円）")
            item_copy["cm_custom_adj"] = st.session_state.get(f"cm_adj_custom_{iid}", 0)
        elif genre == "固定単価・レギュラー番組":
            item_copy["fixed_choice"] = st.session_state.get(f"fixed_sel_{iid}", "")
            item_copy["fixed_name"] = st.session_state.get(f"fn_{iid}", "")
            item_copy["fixed_price"] = st.session_state.get(f"fp_{iid}", 3000)
            item_copy["fixed_count"] = st.session_state.get(f"fc_{iid}", 1)
        elif genre == "その他（作業時間計算）":
            item_copy["work_hours"] = st.session_state.get(f"wh_{iid}", 2.0)
        is_ov = st.session_state.get(f"override_flag_{iid}", it.get("manual_price_enabled", False))
        item_copy["manual_price_enabled"] = is_ov
        if is_ov:
            item_copy["manual_price"] = int(st.session_state.get(f"override_val_{iid}", it.get("manual_price", 0)))
        updated_items.append(item_copy)

    st.session_state.quote_items = updated_items

    client = st.session_state.get("proj_client_name", "").strip()
    proj_title = st.session_state.get("proj_project_name", "").strip()

    if client and proj_title:
        display_name = f"{client} - {proj_title}"
    elif client:
        display_name = f"{client}（案件名未定）"
    elif proj_title:
        display_name = f"{proj_title}"
    else:
        display_name = f"無題の案件（{now_str}）"

    status = st.session_state.get("proj_status", "📝 お見積り中")
    memo = st.session_state.get("proj_memo", "")

    # スケジュール個別データの収集
    schedule_items_data = {}
    for k, v in list(st.session_state.items()):
        if any(k.startswith(pfx) for pfx in [
            "d_date_", "d_time_", "d_custom_", "h_rcv_", "h_rcv_sel_", "h_rcv_custom_",
            "h_date_", "h_time_", "w_date_", "w_time_", "w_custom_",
            "work_day_ids_", "next_work_day_id_"
        ]):
            if isinstance(v, (datetime.date, datetime.datetime)):
                schedule_items_data[k] = v.isoformat()
            else:
                schedule_items_data[k] = v

    quote_settings = {
        "tax_option": st.session_state.get("quote_tax_option", "税込（内税表記）"),
        "schedule_mode": st.session_state.get("quote_sched_mode", "📅 案件ごとに個別に設定（推奨）" if len(st.session_state.quote_items) > 1 else "📅 カレンダーから設定（おすすめ）"),
        "sched_display_style": st.session_state.get("quote_sched_disp_style", "📋 案件ごとにまとめて表示（おすすめ）"),
        "schedule_reservation_type": st.session_state.get("quote_sched_res_type", "なし（記載しない）"),
        "include_delay_note": st.session_state.get("quote_inc_delay_note", True),
        "use_delivery": st.session_state.get("s_chk_del", st.session_state.get("m_chk_del", st.session_state.get("f_chk_del", True))),
        "use_handover": st.session_state.get("s_chk_han", st.session_state.get("m_chk_han", st.session_state.get("f_chk_han", True))),
        "use_work": st.session_state.get("s_chk_wrk", st.session_state.get("m_chk_wrk", st.session_state.get("f_chk_wrk", True))),
        "free_delivery_input": st.session_state.get("free_delivery_input", ""),
        "free_handover_input": st.session_state.get("free_handover_input", ""),
        "free_work_input": st.session_state.get("free_work_input", ""),
        "schedule_items_data": schedule_items_data,
        "include_work_contents": st.session_state.get("chk_inc_work_contents", True),
        "c_task1": st.session_state.get("chk_task1", True),
        "c_task2": st.session_state.get("chk_task2", True),
        "c_task3": st.session_state.get("chk_task3", True),
        "c_task4": st.session_state.get("chk_task4", True),
        "c_custom_task": st.session_state.get("txt_custom_task", ""),
        "audio_spec": st.session_state.get("quote_audio_spec", "平均ラウドネス値 -24.0 LKFS (TP -1.0dBTP以下)"),
        "include_lufs14_note": st.session_state.get("quote_inc_lufs14", False),
        "include_raw_audio_note": st.session_state.get("quote_inc_raw_note", False),
        "audio_format": st.session_state.get("quote_audio_fmt", "WAV (48kHz / 24bit)"),
        "retake_policy_choice": st.session_state.get("quote_retake_choice", "記載しない"),
        "custom_retake": st.session_state.get("custom_retake_policy", ""),
        "include_rework_fee_note": st.session_state.get("quote_inc_rework_note", False),
        "sig_choice_t1": st.session_state.get("t1_sig_choice", st.session_state.get("proj_signature_type", "なし")),
        "overall_adj_price": int(st.session_state.get("quote_overall_adj", 0)),
        "overall_adj_note": st.session_state.get("quote_overall_adj_note", "端数調整・お値引き")
    }

    comm_data = {
        "file_type": st.session_state.get("comm_file_type", "ミックスファイル"),
        "pattern": st.session_state.get("comm_pattern", "🎵 ファイル送付（基本・シンプル）"),
        "url": st.session_state.get("comm_url", ""),
        "url_meta": st.session_state.get("comm_url_meta", ""),
        "free_text": st.session_state.get("comm_free_text", ""),
        "closing": st.session_state.get("comm_closing", ""),
        "sig_comm": st.session_state.get("t2_sig_choice", st.session_state.get("proj_signature_type", "なし"))
    }

    eval_data = {
        "impression": st.session_state.get("eval_impression", "とてもスムーズ"),
        "appeal_flag": st.session_state.get("eval_appeal_flag", True),
        "sig_eval": st.session_state.get("t3_sig_choice", st.session_state.get("proj_signature_type", "なし"))
    }

    client_honorific = st.session_state.get("proj_client_honorific", "様")
    signature_type = st.session_state.get("proj_signature_type", "なし")
    current_id = target_id or st.session_state.get("active_project_id", "new")
    if force_as_new or current_id == "new":
        new_id = f"proj_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_record = {
            "id": new_id,
            "name": display_name,
            "client_name": client,
            "client_honorific": client_honorific,
            "signature_type": signature_type,
            "project_name": proj_title,
            "status": status,
            "memo": memo,
            "created_at": now_str,
            "updated_at": now_str,
            "quote_items": st.session_state.quote_items,
            "quote_settings": quote_settings,
            "comm_data": comm_data,
            "eval_data": eval_data
        }
        projects.insert(0, project_record)
        st.session_state.active_project_id = new_id
        st.session_state.proj_orig_client_name = client
    else:
        found = False
        for p in projects:
            if p["id"] == current_id:
                p["name"] = display_name
                p["client_name"] = client
                p["client_honorific"] = client_honorific
                p["signature_type"] = signature_type
                p["project_name"] = proj_title
                p["status"] = status
                p["memo"] = memo
                p["updated_at"] = now_str
                p["quote_items"] = st.session_state.quote_items
                p["quote_settings"] = quote_settings
                p["comm_data"] = comm_data
                p["eval_data"] = eval_data
                found = True
                break
        if not found:
            project_record = {
                "id": current_id,
                "name": display_name,
                "client_name": client,
                "client_honorific": client_honorific,
                "signature_type": signature_type,
                "project_name": proj_title,
                "status": status,
                "memo": memo,
                "created_at": now_str,
                "updated_at": now_str,
                "quote_items": st.session_state.quote_items,
                "quote_settings": quote_settings,
                "comm_data": comm_data,
                "eval_data": eval_data
            }
            projects.insert(0, project_record)
        st.session_state.proj_orig_client_name = client

    save_projects(projects)

    # Googleドライブ自動バックアップ
    sync_cfg = load_sync_config()
    if sync_cfg.get("auto_sync", True):
        sync_dir = sync_cfg.get("sync_dir", "").strip()
        if sync_dir and os.path.exists(sync_dir):
            sync_backup_to_dir(sync_dir)

    return display_name

@st.dialog("💾 案件の保存確認")
def show_save_confirm_dialog(project_id: str):
    projects = load_projects()
    matched = [p for p in projects if p["id"] == project_id]
    orig_name = matched[0].get("name", "既存案件") if matched else "既存案件"
    curr_client = st.session_state.get("proj_client_name", "").strip()
    curr_proj = st.session_state.get("proj_project_name", "").strip()
    curr_display = f"{curr_client} - {curr_proj}" if (curr_client and curr_proj) else (curr_client or curr_proj or orig_name)

    st.markdown(f"""
    <div style="background: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; margin-bottom: 1rem;">
        <div style="font-size: 0.8rem; font-weight: 700; color: #64748B;">📁 保存対象の案件:</div>
        <div style="font-size: 1.05rem; font-weight: 700; color: #1E3A8A; margin-top: 2px;">{curr_display}</div>
        <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 2px;">（元の登録名: {orig_name}）</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("既存の案件データを**上書き更新**しますか？  \nそれとも別案件として**別名保存（新規追加）**しますか？")
    st.write("")

    col_dlg1, col_dlg2 = st.columns(2)
    with col_dlg1:
        if st.button("💾 上書き保存する", type="primary", use_container_width=True, key="dlg_btn_overwrite"):
            saved_title = save_current_project_data(force_as_new=False, target_id=project_id)
            st.toast(f"✅ 案件「{saved_title}」を上書き保存しました！", icon="💾")
            st.rerun()
    with col_dlg2:
        if st.button("✨ 別名で新規保存", use_container_width=True, key="dlg_btn_save_as_new"):
            saved_title = save_current_project_data(force_as_new=True)
            st.toast(f"✨ 別名（新規案件）として「{saved_title}」を保存しました！", icon="✨")
            st.rerun()

def handle_save_project():
    current_id = st.session_state.get("active_project_id", "new")
    current_client = st.session_state.get("proj_client_name", "").strip()
    orig_client = st.session_state.get("proj_orig_client_name", "").strip()

    # 1. 新規案件（まだID未発行）
    if current_id == "new":
        saved_title = save_current_project_data(force_as_new=True)
        st.toast(f"✅ 案件「{saved_title}」を新規保存しました！", icon="💾")
        st.rerun()

    # 2. 既存案件で、クライアント名が別のものが入った場合 -> 自動で別名保存！
    elif orig_client != current_client and current_client:
        saved_title = save_current_project_data(force_as_new=True)
        st.toast(f"📋 クライアント名が「{orig_client or '未設定'}」から「{current_client}」に変更されたため、別名（新規案件）として保存しました！", icon="✨")
        st.rerun()

    # 3. それ以外（既存案件でクライアント名が同じ、または未入力のままなど） -> 上書き確認ダイアログ
    else:
        show_save_confirm_dialog(current_id)

def delete_active_project():
    current_id = st.session_state.get("active_project_id", "new")
    if current_id != "new":
        projects = load_projects()
        projects = [p for p in projects if p["id"] != current_id]
        save_projects(projects)
        reset_to_new_project()

# ==========================================
# 複数案件（マルチアイテム）のセッション管理
# ==========================================
if "quote_items" not in st.session_state:
    st.session_state.quote_items = [
        {"id": 1, "genre": "番組", "duration": 15.0}
    ]
if "next_item_id" not in st.session_state:
    st.session_state.next_item_id = 2

def add_quote_item():
    st.session_state.quote_items.append({
        "id": st.session_state.next_item_id,
        "genre": "CM（15秒・30秒）",
        "duration": 15.0
    })
    st.session_state.next_item_id += 1

def remove_quote_item(item_id: int):
    if len(st.session_state.quote_items) > 1:
        st.session_state.quote_items = [it for it in st.session_state.quote_items if it["id"] != item_id]

# ==========================================
# スケジュール・作業日（複数日対応）ヘルパー
# ==========================================
TIME_OPTIONS = ["中（終日）", "夕方まで", "午前中", "23:59まで", "18:00まで", "要相談", "✏️ 直接入力"]
WORK_TIME_OPTIONS = ["夜", "夕方以降", "終日", "午前中", "午後", "深夜", "要相談", "✏️ 直接入力"]

def get_work_day_ids(item_key: str) -> list[int]:
    sess_key = f"work_day_ids_{item_key}"
    if sess_key not in st.session_state:
        st.session_state[sess_key] = [1]
    return st.session_state[sess_key]

def add_work_day(item_key: str):
    sess_key = f"work_day_ids_{item_key}"
    next_key = f"next_work_day_id_{item_key}"
    if sess_key not in st.session_state:
        st.session_state[sess_key] = [1]
    if next_key not in st.session_state:
        st.session_state[next_key] = 2
    st.session_state[sess_key].append(st.session_state[next_key])
    st.session_state[next_key] += 1

def remove_work_day(item_key: str, w_id: int):
    sess_key = f"work_day_ids_{item_key}"
    if sess_key in st.session_state and len(st.session_state[sess_key]) > 1:
        st.session_state[sess_key] = [x for x in st.session_state[sess_key] if x != w_id]
        st.session_state.pop(f"w_date_{item_key}_{w_id}", None)
        st.session_state.pop(f"w_time_{item_key}_{w_id}", None)
        st.session_state.pop(f"w_custom_{item_key}_{w_id}", None)

def render_schedule_inputs(
    item_key: str,
    item_title: str = "",
    default_del_days: int = 3,
    default_han_days: int = 1,
    default_work_days_offset: int = 1,
    show_title: bool = True
) -> dict:
    today = datetime.date.today()
    if show_title and item_title:
        st.markdown(f'<div style="font-weight: 700; color: #0F766E; font-size: 1.05rem; margin-bottom: 0.7rem; border-bottom: 1px solid #CCFBF1; padding-bottom: 0.3rem;">📌 {item_title}</div>', unsafe_allow_html=True)

    # 1. 希望納期
    st.markdown("🎯 **ご希望納期**")
    col_d1, col_d2 = st.columns([3, 2])
    with col_d1:
        del_date = st.date_input("ご希望納期の日付", value=today + datetime.timedelta(days=default_del_days), key=f"d_date_{item_key}")
    with col_d2:
        del_time = st.selectbox("納期の時間帯", TIME_OPTIONS, key=f"d_time_{item_key}")

    if del_time == "✏️ 直接入力":
        del_custom = st.text_input("具体的な納期時間", value="18:00まで", key=f"d_custom_{item_key}")
        del_text = f"{format_date_jp(del_date)} {del_custom.strip()}"
    else:
        del_text = f"{format_date_jp(del_date)} {del_time}"

    # 2. データご搬入
    col_h_hdr1, col_h_hdr2 = st.columns([3, 2])
    with col_h_hdr1:
        st.markdown("📦 **データご搬入**")
    with col_h_hdr2:
        is_received = st.checkbox("素材受領済み（搬入済み）", value=False, key=f"h_rcv_{item_key}", help="すでに素材・データを受け取り済みの場合はチェックしてください")

    if is_received:
        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            rcv_status = st.selectbox(
                "受領ステータス表記",
                ["素材受領済み", "受領済み", "データ受領済み", "搬入済み", "素材受領済み（データ確認完了）", "✏️ 直接入力"],
                key=f"h_rcv_sel_{item_key}"
            )
        with col_r2:
            if rcv_status == "✏️ 直接入力":
                han_text = st.text_input("具体的な表記", value="素材受領済み", key=f"h_rcv_custom_{item_key}").strip()
            else:
                han_text = rcv_status
                st.caption(f"※メッセージには「・データご搬入： {han_text}」と記載されます。")
    else:
        col_h1, col_h2 = st.columns([3, 2])
        with col_h1:
            han_date = st.date_input("データご搬入日", value=today + datetime.timedelta(days=default_han_days), key=f"h_date_{item_key}")
        with col_h2:
            han_time = st.text_input("搬入時間・メモ", value="21:30ごろ", placeholder="例: 21:30ごろ、夕方、ナレ11/3など", key=f"h_time_{item_key}")
        han_text = f"{format_date_jp(han_date)} {han_time}".strip()

    # 3. 作業予定日（何日でも追加可能）
    st.markdown("🛠️ **作業予定日**（大型案件や別日作業に対応）")
    w_ids = get_work_day_ids(item_key)
    work_parts = []

    for idx, w_id in enumerate(w_ids):
        day_num = idx + 1
        day_label = f"作業日（{day_num}日目）" if len(w_ids) > 1 else "作業予定日"

        if len(w_ids) > 1:
            c_w1, c_w2, c_w3 = st.columns([3, 2, 1])
        else:
            c_w1, c_w2 = st.columns([3, 2])
            c_w3 = None

        with c_w1:
            w_date = st.date_input(
                day_label,
                value=today + datetime.timedelta(days=default_work_days_offset + idx),
                key=f"w_date_{item_key}_{w_id}"
            )
        with c_w2:
            def_t_idx = min(idx, len(WORK_TIME_OPTIONS) - 2)
            w_time = st.selectbox(
                f"時間帯（{day_num}日目）" if len(w_ids) > 1 else "作業時間帯",
                WORK_TIME_OPTIONS,
                index=def_t_idx,
                key=f"w_time_{item_key}_{w_id}"
            )
        if c_w3 is not None:
            with c_w3:
                st.write("")
                st.write("")
                st.button("🗑️", key=f"del_w_{item_key}_{w_id}", help=f"{day_num}日目を削除", on_click=remove_work_day, args=(item_key, w_id))

        if w_time == "✏️ 直接入力":
            w_custom = st.text_input(f"具体的な作業時間（{day_num}日目）", value="夜", key=f"w_custom_{item_key}_{w_id}")
            work_parts.append(f"{format_date_jp(w_date)} {w_custom.strip()}")
        else:
            work_parts.append(f"{format_date_jp(w_date)} {w_time}")

    st.button(
        f"➕ 作業予定日を追加（{len(w_ids) + 1}日目）",
        key=f"add_w_btn_{item_key}",
        on_click=add_work_day,
        args=(item_key,)
    )

    work_text = "、".join(work_parts)
    return {
        "title": item_title,
        "delivery": del_text,
        "handover": han_text,
        "work": work_text,
        "is_received": is_received
    }

# カスタムCSS
st.markdown("""
<style>
    /* メインタイトル（明るいグラデーション） */
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #0D9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: 0.96rem;
        color: #475569;
        margin-bottom: 1.4rem;
        line-height: 1.6;
    }

    /* 各セクションのステップバッジ＆見出し */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        display: flex;
        align-items: center;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.75rem;
        font-weight: 800;
        padding: 3px 9px;
        border-radius: 6px;
        margin-right: 8px;
        letter-spacing: 0.5px;
    }
    .step-badge-blue {
        background-color: #DBEAFE;
        color: #1D4ED8;
    }
    .step-badge-teal {
        background-color: #CCFBF1;
        color: #0F766E;
    }
    .step-badge-purple {
        background-color: #F3E8FF;
        color: #7E22CE;
    }
    .step-badge-green {
        background-color: #DCFCE7;
        color: #15803D;
    }

    /* お見積もり結果カード（明るく視認性の高いスタイル） */
    .metric-card {
        background: linear-gradient(135deg, #F0FDF4 0%, #EFF6FF 100%);
        border: 2px solid #BFDBFE;
        border-radius: 16px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08);
    }
    .total-price {
        font-size: 2.6rem;
        font-weight: 900;
        color: #1E40AF;
        letter-spacing: -0.5px;
        margin: 0.3rem 0;
    }
    .tax-note {
        font-size: 0.82rem;
        font-weight: 600;
        color: #047857;
        background: #DCFCE7;
        padding: 3px 10px;
        border-radius: 9999px;
        display: inline-block;
    }
    .breakdown-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-top: 0.9rem;
    }
    .breakdown-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #64748B;
        margin-bottom: 0.4rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .breakdown-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0;
        border-bottom: 1px dashed #F1F5F9;
        font-size: 0.88rem;
        color: #1E293B;
    }
    .breakdown-item:last-child {
        border-bottom: none;
    }
    .breakdown-price {
        font-weight: 700;
        color: #2563EB;
        font-size: 0.95rem;
    }

    /* コピーツールチップ / 注意書き案内 */
    .copy-tip {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 0.65rem 1rem;
        border-radius: 8px;
        font-size: 0.88rem;
        color: #1E40AF;
        margin-bottom: 1rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* タブデザイン */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #F8FAFC;
        padding: 5px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        font-weight: 600;
        border-radius: 7px;
        color: #64748B;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2563EB !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    }

    /* コードブロック・メッセージ表示枠の自動折り返し（枠からはみ出さない） */
    div[data-testid="stCodeBlock"], div[data-testid="stCode"], .stCodeBlock {
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    div[data-testid="stCodeBlock"] pre, div[data-testid="stCode"] pre, .stCodeBlock pre, pre {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        font-size: 0.92rem !important;
        line-height: 1.68 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif, 'Consolas', monospace !important;
        background-color: #F8FAFC !important;
        overflow-x: hidden !important;
    }
    div[data-testid="stCodeBlock"] code, div[data-testid="stCode"] code, .stCodeBlock code, code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        font-family: inherit !important;
    }

    /* プロジェクト・ステータスバッジ */
    .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 9999px;
        letter-spacing: 0.3px;
    }
    .status-estimate { background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
    .status-working  { background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
    .status-retake   { background-color: #FFEDD5; color: #C2410C; border: 1px solid #FED7AA; }
    .status-delivery { background-color: #F3E8FF; color: #7E22CE; border: 1px solid #E9D5FF; }
    .status-done     { background-color: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 計算ロジック
# ==========================================
def calc_duration_price(minutes: float, is_drama: bool = False) -> tuple[int, float]:
    """
    YouTube・配信 / 番組 / ドラマ・自主映画 の補間計算を行う関数
    戻り値: (基本金額, 想定作業時間)
    """
    factor = 2 if is_drama else 1

    if minutes <= 5:
        base_price = 6000 * factor
    elif minutes <= 15:
        rate = 300 * factor
        base = 6000 * factor
        diff = minutes - 5
        base_price = int(round(base + diff * rate))
    elif minutes <= 30:
        rate = 200 * factor
        base = 9000 * factor
        diff = minutes - 15
        base_price = int(round(base + diff * rate))
    elif minutes <= 60:
        rate = 400 * factor
        base = 12000 * factor
        diff = minutes - 30
        base_price = int(round(base + diff * rate))
    else:
        rate = 400 * factor
        base = 24000 * factor
        diff = minutes - 60
        base_price = int(round(base + diff * rate))

    base_hours = round(base_price / 3000.0, 1)
    return base_price, base_hours


# ==========================================
# サイドバー: 案件（プロジェクト）管理
# ==========================================
with st.sidebar:
    st.markdown('<div style="font-size: 1.25rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0.8rem;">📁 案件・プロジェクト管理</div>', unsafe_allow_html=True)

    all_projects = load_projects()
    project_options = ["＋ 新規案件を作成"] + [f"{p.get('status', '').split(' ')[0]} {p.get('name', '無題')}" for p in all_projects]

    current_active_id = st.session_state.get("active_project_id", "new")
    current_idx = 0
    if current_active_id != "new":
        for i, p in enumerate(all_projects):
            if p["id"] == current_active_id:
                current_idx = i + 1
                break

    def on_project_selected():
        selected = st.session_state.sidebar_project_select
        if selected == "＋ 新規案件を作成":
            reset_to_new_project()
        else:
            idx = project_options.index(selected) - 1
            if 0 <= idx < len(all_projects):
                load_project_into_session(all_projects[idx])

    st.selectbox(
        "作業する案件を選択",
        project_options,
        index=current_idx if current_idx < len(project_options) else 0,
        key="sidebar_project_select",
        on_change=on_project_selected
    )

    st.markdown("---")

    st.markdown('<div style="font-weight: 700; font-size: 0.95rem; color: #334155; margin-bottom: 0.4rem;">⚙️ 案件基本情報</div>', unsafe_allow_html=True)
    c_name_disp = st.session_state.get('proj_client_name', '').strip() or '（未入力）'
    p_name_disp = st.session_state.get('proj_project_name', '').strip() or '（未入力）'
    st.caption(f"👤 クライアント: **{c_name_disp}**  \n🎬 案件名: **{p_name_disp}**")

    status_list = [
        "📝 お見積り中",
        "🎧 制作中（初稿前）",
        "🔄 修正対応中",
        "📦 納品・検収中",
        "✅ 取引完了"
    ]
    cur_status = st.session_state.get("proj_status", "📝 お見積り中")
    status_idx = status_list.index(cur_status) if cur_status in status_list else 0

    st.selectbox(
        "進捗ステータス",
        status_list,
        index=status_idx,
        key="proj_status"
    )

    cur_sig_p = st.session_state.get("sb_sig_choice", st.session_state.get("proj_signature_type", "なし"))
    sig_p_idx = SIG_OPTIONS.index(cur_sig_p) if cur_sig_p in SIG_OPTIONS else 0
    st.selectbox(
        "🖋️ 署名の選択（案件基本）",
        SIG_OPTIONS,
        index=sig_p_idx,
        key="sb_sig_choice",
        on_change=sync_signature_type,
        args=("sb_sig_choice",),
        help="この案件で使用する署名を選択できます（各タブの画面でもワンクリックで切り替え可能）"
    )

    st.text_area(
        "案件メモ・備忘録（任意）",
        value=st.session_state.get("proj_memo", ""),
        placeholder="例: BGM素材受領済み。フォーマット48kHz/24bit。修正2回まで無料。",
        height=90,
        key="proj_memo"
    )

    col_sb1, col_sb2 = st.columns([1, 1])
    with col_sb1:
        if st.button("💾 案件を保存", type="primary", use_container_width=True, key="btn_save_proj"):
            handle_save_project()

    with col_sb2:
        if current_active_id != "new":
            if st.button("🗑️ 案件を削除", use_container_width=True, key="btn_del_proj"):
                delete_active_project()
                st.toast("🗑️ 案件を削除しました。", icon="🗑️")
                st.rerun()

    st.markdown("---")

    with st.expander("📦 バックアップ / 復元（Googleドライブ連携）"):
        st.markdown('<div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.5rem;">全案件データのダウンロード/復元、およびGoogleドライブへの自動同期が可能です。</div>', unsafe_allow_html=True)

        # --- Googleドライブ / 外部フォルダ同期設定 ---
        st.markdown("##### 📁 Googleドライブ同期")
        sync_cfg = load_sync_config()
        cur_sync_dir = sync_cfg.get("sync_dir", DEFAULT_SYNC_DIR)
        auto_sync_val = sync_cfg.get("auto_sync", True)

        input_sync_dir = st.text_input(
            "同期フォルダパス",
            value=cur_sync_dir,
            placeholder=r"G:\マイドライブ\KO SUTUDIO_仕事用\見積もりアシスタント",
            help="Google Drive for Desktop のマイドライブ内フォルダなどを指定できます（Macの場合はMac上のパスを指定）",
            key="input_sync_dir"
        )
        ch_auto_sync = st.checkbox("案件保存時にGoogleドライブにも自動同期", value=auto_sync_val, key="chk_auto_sync")

        # 設定変更時の保存
        if input_sync_dir != cur_sync_dir or ch_auto_sync != auto_sync_val:
            save_sync_config({"sync_dir": input_sync_dir, "auto_sync": ch_auto_sync})

        # フォルダの存在チェック
        is_dir_found = bool(input_sync_dir and os.path.exists(input_sync_dir))

        if is_dir_found:
            st.success("🟢 同期フォルダを認識しました")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                if st.button("💾 今すぐ同期保存", use_container_width=True, key="btn_sync_save"):
                    ok, msg = sync_backup_to_dir(input_sync_dir)
                    if ok:
                        st.toast(msg, icon="📁")
                    else:
                        st.error(msg)
            with col_g2:
                if st.button("📂 同期先から復元", use_container_width=True, key="btn_sync_load"):
                    ok, msg = restore_from_sync_dir(input_sync_dir)
                    if ok:
                        st.toast(msg, icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.markdown(
                '<div style="font-size: 0.78rem; color: #B45309; background: #FEF3C7; padding: 6px 10px; border-radius: 6px; margin-bottom: 0.5rem;">'
                '⚠️ 指定フォルダが未検出です。<br>'
                '・<b>Windows</b>: Google Driveアプリで上記パスが存在するかご確認ください。<br>'
                '・<b>Mac</b>: Mac用パス（例: <code>/Users/名前/Google Drive/...</code>）をご指定ください。<br>'
                '・<b>Streamlit Cloud（ブラウザ）</b>: Web環境からは直接PCフォルダに書き込めないため、下の「📥 案件データを保存 (JSON)」から手動保存してください。'
                '</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("##### 📥 ファイルで保存・復元")
        all_proj_json = json.dumps(load_projects(), ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 案件データを保存 (JSON)",
            data=all_proj_json,
            file_name=f"ma_assistant_projects_{datetime.date.today().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
            key="dl_backup_btn"
        )

        uploaded_backup = st.file_uploader("📤 JSONバックアップを復元", type=["json"], key="upload_backup")
        if uploaded_backup is not None:
            if st.button("復元を実行", key="btn_restore"):
                try:
                    restore_data = json.load(uploaded_backup)
                    if isinstance(restore_data, list):
                        save_projects(restore_data)
                        st.success("✅ データを復元しました！")
                        st.rerun()
                except Exception as e:
                    st.error(f"復元エラー: {e}")

    with st.expander("🖋️ 署名の事前登録・編集"):
        st.markdown('<div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.5rem;">登録した署名は、各メッセージの末尾でワンクリックで使い分けできます。</div>', unsafe_allow_html=True)
        cur_sigs = load_signatures()
        sig_coco_val = st.text_area(
            "ココナラ用（クリエイター名・屋号等）",
            value=cur_sigs.get("coconala", ""),
            height=70,
            key="sig_coco_val"
        )
        sig_lanc_val = st.text_area(
            "ランサーズ用（クリエイター名・屋号等）",
            value=cur_sigs.get("lancers", ""),
            height=70,
            key="sig_lanc_val"
        )
        sig_real_val = st.text_area(
            "本名・ビジネス用（氏名・肩書・メール等）",
            value=cur_sigs.get("realname", ""),
            height=80,
            key="sig_real_val"
        )
        if st.button("💾 署名設定を保存", key="btn_save_sig_sb", use_container_width=True):
            save_signatures({
                "coconala": sig_coco_val.strip(),
                "lancers": sig_lanc_val.strip(),
                "realname": sig_real_val.strip()
            })
            st.toast("✅ 署名を保存しました！", icon="🖋️")
            st.rerun()


# ==========================================
# アプリケーションヘッダー & アクティブ案件バー
# ==========================================
st.markdown('<div class="main-header">🎙️ 音声編集（MA）業務アシスタント</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">見積もり計算から制作中のファイル送信・やり取りメッセージ、納品後の評価コメントまでをワンストップで作成します。</div>', unsafe_allow_html=True)

# アクティブ案件情報バー
active_name = st.session_state.get("proj_client_name", "").strip()
active_proj = st.session_state.get("proj_project_name", "").strip()
active_status = st.session_state.get("proj_status", "📝 お見積り中")

if active_name and active_proj:
    current_proj_label = f"{active_name} ｜ {active_proj}"
elif active_name:
    current_proj_label = f"{active_name}（案件名未定）"
elif active_proj:
    current_proj_label = f"{active_proj}"
else:
    current_proj_label = "＋ 新規案件（未保存）"

status_class = "status-estimate"
if "🎧" in active_status:
    status_class = "status-working"
elif "🔄" in active_status:
    status_class = "status-retake"
elif "📦" in active_status:
    status_class = "status-delivery"
elif "✅" in active_status:
    status_class = "status-done"

col_bar1, col_bar2 = st.columns([5, 1])
with col_bar1:
    bar_html = (
        f'<div style="background: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 10px; padding: 8px 16px; display: flex; align-items: center; gap: 10px; margin-bottom: 0.6rem;">'
        f'<span style="font-size: 0.82rem; font-weight: 800; color: #475569; letter-spacing: 0.5px;">📁 進行中の案件:</span>'
        f'<span style="font-size: 0.98rem; font-weight: 700; color: #1E3A8A;">{current_proj_label}</span>'
        f'<span class="status-badge {status_class}">{active_status}</span>'
        f'</div>'
    )
    st.markdown(bar_html, unsafe_allow_html=True)
with col_bar2:
    if st.button("💾 案件を保存", key="btn_quick_save", type="primary", use_container_width=True):
        handle_save_project()

# 3つのタブを作成
tab1, tab2, tab3 = st.tabs([
    "💰 見積もり・提案作成",
    "✉️ 連絡・ファイル送信",
    "💬 納品・評価コメント作成"
])


# ==========================================
# タブ1: 見積もり作成
# ==========================================
with tab1:
    col_input, col_result = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-blue">STEP 1</span>
            <span>案件情報・依頼内容の入力</span>
        </div>
        """, unsafe_allow_html=True)

        # 宛名・案件名（全タブ連動）
        col_c_name, col_c_hon = st.columns([3, 1])
        with col_c_name:
            client_name = st.text_input(
                "クライアント名（任意）",
                value=st.session_state.get("t1_client_name", ""),
                placeholder="例: 株式会社〇〇 / 田中（敬称は自動付与）",
                key="t1_client_name",
                on_change=sync_client_name,
                args=("t1_client_name",)
            )
        with col_c_hon:
            honorific_options = ["様", "さん", "なし"]
            cur_hon = st.session_state.get("t1_client_honorific", "様")
            hon_idx = honorific_options.index(cur_hon) if cur_hon in honorific_options else 0
            client_honorific = st.selectbox(
                "敬称",
                honorific_options,
                index=hon_idx,
                key="t1_client_honorific",
                on_change=sync_client_honorific,
                args=("t1_client_honorific",)
            )
        project_title = st.text_input(
            "案件名・案件全体の概要（任意）",
            value=st.session_state.get("t1_project_name", ""),
            placeholder="例: レギュラー番組 ＋ 番宣CM制作 MA作業",
            key="t1_project_name",
            on_change=sync_project_name,
            args=("t1_project_name",)
        )

        genres_list = [
            "番組",
            "CM（15秒・30秒）",
            "YouTube・配信",
            "ドラマ・自主映画",
            "固定単価・レギュラー番組",
            "その他（作業時間計算）"
        ]

        # 複数アイテムの入力ループ
        num_items = len(st.session_state.quote_items)
        items_calculation_results = []

        for idx, item in enumerate(st.session_state.quote_items):
            item_id = item["id"]
            card_title = f"依頼内容 {idx + 1}" if num_items > 1 else "依頼内容"

            with st.container(border=True):
                st.markdown(f'<div style="font-weight: 700; color: #1E3A8A; font-size: 1.05rem; margin-bottom: 0.5rem;">🎬 {card_title}</div>', unsafe_allow_html=True)

                col_g, col_del = st.columns([5, 1])
                with col_g:
                    selected_genre = st.selectbox(
                        "案件ジャンル",
                        genres_list,
                        key=f"genre_{item_id}",
                        index=genres_list.index(item.get("genre", "YouTube・配信")) if item.get("genre") in genres_list else 0
                    )
                    item["genre"] = selected_genre

                with col_del:
                    if num_items > 1:
                        st.write("")
                        st.write("")
                        st.button("🗑️ 削除", key=f"del_item_{item_id}", on_click=remove_quote_item, args=(item_id,))

                item_price_base = 0
                item_detail_text = ""
                item_breakdown_text = ""
                item_display_genre = selected_genre

                # 条件付き入力
                if selected_genre in ["YouTube・配信", "番組", "ドラマ・自主映画"]:
                    c_step, c_num = st.columns([2, 3])
                    with c_step:
                        step_unit = st.radio("増減単位", [5.0, 10.0, 1.0], format_func=lambda x: f"{int(x)}分", horizontal=True, key=f"step_{item_id}")
                    with c_num:
                        dur_key = f"dur_{item_id}"
                        if dur_key not in st.session_state:
                            st.session_state[dur_key] = float(item.get("duration", 15.0))
                        duration_val = st.number_input(
                            "尺（分）",
                            min_value=1.0,
                            max_value=300.0,
                            step=step_unit,
                            key=dur_key
                        )
                        item["duration"] = duration_val

                    # 作業時間目安 & 収録状況工数補正
                    is_drama_genre = (selected_genre == "ドラマ・自主映画")
                    base_calc_price, base_calc_hours = calc_duration_price(duration_val, is_drama=is_drama_genre)

                    col_h1, col_h2 = st.columns([2, 3])
                    with col_h1:
                        st.caption(f"基準作業時間: 約 {base_calc_hours:.1f} 時間")
                    with col_h2:
                        condition_options = [
                            "標準（収録状態良好: ±0h）",
                            "ノイズやや多め（+0.5h / +1,500円）",
                            "ノイズ多め・要整音（+1.0h / +3,000円）",
                            "素材難度高（+2.0h / +6,000円）",
                            "簡易・素材良好（-0.5h / -1,500円）",
                            "手動指定"
                        ]
                        cur_cond = item.get("condition", "標準（収録状態良好: ±0h）")
                        cond_idx = condition_options.index(cur_cond) if cur_cond in condition_options else 0
                        selected_cond = st.selectbox("素材状態・工数補正", condition_options, index=cond_idx, key=f"cond_{item_id}")
                        item["condition"] = selected_cond

                    adj_hours = 0.0
                    if "+0.5h" in selected_cond:
                        adj_hours = 0.5
                    elif "+1.0h" in selected_cond:
                        adj_hours = 1.0
                    elif "+2.0h" in selected_cond:
                        adj_hours = 2.0
                    elif "-0.5h" in selected_cond:
                        adj_hours = -0.5

                    final_hours = max(0.5, base_calc_hours + adj_hours)
                    if "手動指定" in selected_cond:
                        final_hours = st.number_input("手動作業時間（時間）", min_value=0.5, max_value=50.0, value=base_calc_hours, step=0.5, key=f"custom_h_{item_id}")
                        item["custom_hours"] = final_hours

                    item_price_base = int(round(final_hours * 3000))
                    item_detail_text = f"{selected_genre} {duration_val:.1f}分（想定工数：約{final_hours:.1f}h）"
                    item_breakdown_text = f"{duration_val:.1f}分（約{final_hours:.1f}h × 3,000円）= {item_price_base:,}円"

                elif selected_genre == "CM（15秒・30秒）":
                    c_cm1, c_cm2, c_cm3 = st.columns([2, 2, 2])
                    with c_cm1:
                        cm_options = ["通常（3,000円）", "お得意様（2,000円）", "✏️ 単価直接指定"]
                        cur_pat = item.get("cm_pattern", "通常")
                        if "お得意様" in cur_pat:
                            cm_pat_idx = 1
                        elif "直接指定" in cur_pat:
                            cm_pat_idx = 2
                        else:
                            cm_pat_idx = 0
                        cm_pattern = st.radio("取引先パターン", cm_options, index=cm_pat_idx, key=f"cm_pat_{item_id}")
                        item["cm_pattern"] = "お得意様" if "お得意様" in cm_pattern else ("✏️ 単価直接指定" if "直接指定" in cm_pattern else "通常")

                    with c_cm2:
                        price_key = f"cm_price_{item_id}"
                        last_pat_key = f"last_cm_pat_{item_id}"
                        if last_pat_key not in st.session_state:
                            st.session_state[last_pat_key] = item["cm_pattern"]

                        if st.session_state[last_pat_key] != item["cm_pattern"]:
                            if "お得意様" in item["cm_pattern"]:
                                st.session_state[price_key] = 2000
                            elif "通常" in item["cm_pattern"]:
                                st.session_state[price_key] = 3000
                            st.session_state[last_pat_key] = item["cm_pattern"]

                        if price_key not in st.session_state:
                            st.session_state[price_key] = int(item.get("cm_unit_price", 2000 if "お得意様" in cm_pattern else 3000))

                        u_price = st.number_input(
                            "単価（円/本）",
                            min_value=500,
                            max_value=100000,
                            step=500,
                            key=price_key
                        )
                        item["cm_unit_price"] = u_price

                    with c_cm3:
                        cnt_key = f"cm_cnt_{item_id}"
                        if cnt_key not in st.session_state:
                            st.session_state[cnt_key] = int(item.get("cm_count", 1))
                        cm_count = st.number_input(
                            "本数",
                            min_value=1,
                            max_value=100,
                            step=1,
                            key=cnt_key
                        )
                        item["cm_count"] = cm_count

                    # CM素材状態・工数補正
                    col_cm_c1, col_cm_c2 = st.columns([3, 2])
                    with col_cm_c1:
                        cm_condition_options = [
                            "標準（追加補正なし: ±0円）",
                            "ノイズやや多め・整音あり（+1,000円/本）",
                            "ノイズ多め・要整音（+2,000円/本）",
                            "素材難度高・音効増（+3,000円/本）",
                            "まとめ割・お値引き（-500円/本）",
                            "手動補正指定（1本当たりの金額入力）"
                        ]
                        cur_cm_cond = item.get("cm_condition", "標準（追加補正なし: ±0円）")
                        cm_cond_idx = cm_condition_options.index(cur_cm_cond) if cur_cm_cond in cm_condition_options else 0
                        selected_cm_cond = st.selectbox(
                            "素材状態・工数補正（任意）",
                            cm_condition_options,
                            index=cm_cond_idx,
                            key=f"cm_cond_{item_id}"
                        )
                        item["cm_condition"] = selected_cm_cond

                    cm_adj_price = 0
                    if "+1,000円" in selected_cm_cond:
                        cm_adj_price = 1000
                    elif "+2,000円" in selected_cm_cond:
                        cm_adj_price = 2000
                    elif "+3,000円" in selected_cm_cond:
                        cm_adj_price = 3000
                    elif "-500円" in selected_cm_cond:
                        cm_adj_price = -500
                    elif "手動補正指定" in selected_cm_cond:
                        with col_cm_c2:
                            custom_adj_key = f"cm_adj_custom_{item_id}"
                            if custom_adj_key not in st.session_state:
                                st.session_state[custom_adj_key] = int(item.get("cm_custom_adj", 0))
                            cm_adj_price = st.number_input(
                                "1本当たりの手動補正額（円）",
                                min_value=-50000,
                                max_value=50000,
                                step=500,
                                key=custom_adj_key
                            )
                            item["cm_custom_adj"] = cm_adj_price

                    final_unit_price = max(500, u_price + cm_adj_price)
                    item_price_base = final_unit_price * cm_count

                    cond_note = f"（{selected_cm_cond.split('（')[0]}）" if ("±0円" not in selected_cm_cond and "手動" not in selected_cm_cond) else ""
                    item_detail_text = f"CM（15秒・30秒）{cond_note}（{final_unit_price:,}円/本）× {cm_count}本"
                    if cm_adj_price != 0:
                        item_breakdown_text = f"（単価 {u_price:,}円 ＋ 補正 {cm_adj_price:+,}円）× {cm_count}本 = {item_price_base:,}円"
                    else:
                        item_breakdown_text = f"{final_unit_price:,}円 × {cm_count}本 = {item_price_base:,}円"

                elif selected_genre == "固定単価・レギュラー番組":
                    custom_programs = load_custom_programs()
                    prog_options = [f"{p['name']}（{p['price']:,}円/本）" for p in custom_programs]
                    prog_options.append("＋ 新規・一時入力（登録せず直接入力）")

                    cur_fixed = item.get("fixed_choice", prog_options[0] if prog_options else "")
                    f_idx = prog_options.index(cur_fixed) if cur_fixed in prog_options else 0
                    chosen_p = st.selectbox("番組の選択", prog_options, index=f_idx, key=f"fixed_sel_{item_id}")
                    item["fixed_choice"] = chosen_p
                    f_name = ""
                    f_price = 3000

                    if chosen_p == "＋ 新規・一時入力（登録せず直接入力）":
                        cn1, cn2 = st.columns([3, 2])
                        with cn1:
                            f_name = st.text_input("番組名", value=item.get("fixed_name", "レギュラー番組"), key=f"fn_{item_id}")
                            item["fixed_name"] = f_name
                        with cn2:
                            f_price = st.number_input("単価（円/本）", min_value=500, max_value=100000, value=item.get("fixed_price", 3000), step=500, key=f"fp_{item_id}")
                            item["fixed_price"] = f_price
                    else:
                        idx_p = prog_options.index(chosen_p)
                        target_p = custom_programs[idx_p]
                        f_name = target_p["name"]
                        f_price = target_p["price"]
                        item["fixed_name"] = f_name
                        item["fixed_price"] = f_price

                    f_count = st.number_input("制作本数", min_value=1, max_value=100, value=int(item.get("fixed_count", 1)), step=1, key=f"fc_{item_id}")
                    item["fixed_count"] = f_count
                    item_price_base = f_price * f_count
                    item_display_genre = f"固定単価番組（{f_name}）"
                    item_detail_text = f"{f_name}（{f_price:,}円/本）× {f_count}本"
                    item_breakdown_text = f"{f_price:,}円 × {f_count}本 = {item_price_base:,}円"

                elif selected_genre == "その他（作業時間計算）":
                    w_hours = st.number_input("作業時間（時間単位）", min_value=0.5, max_value=200.0, value=float(item.get("work_hours", 2.0)), step=0.5, key=f"wh_{item_id}")
                    item["work_hours"] = w_hours
                    item_price_base = int(round(w_hours * 3000))
                    item_detail_text = f"作業時間計算 {w_hours:.1f}時間（3,000円/h）"
                    item_breakdown_text = f"3,000円 × {w_hours:.1f}h = {item_price_base:,}円"

                # --- 料金の手直し（手動上書き・直接指定） ---
                st.markdown('<div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed #CBD5E1;"></div>', unsafe_allow_html=True)
                col_ov1, col_ov2 = st.columns([3, 2])
                with col_ov1:
                    flag_key = f"override_flag_{item_id}"
                    is_override = st.checkbox(
                        "✏️ この依頼内容の料金を手直しする",
                        value=st.session_state.get(flag_key, item.get("manual_price_enabled", False)),
                        key=flag_key,
                        help="時間単位の計算に当てはまらない場合や、ご予算・端数調整など、自由な金額を直接指定できます。"
                    )
                    item["manual_price_enabled"] = is_override

                with col_ov2:
                    if is_override:
                        val_key = f"override_val_{item_id}"
                        if val_key not in st.session_state:
                            st.session_state[val_key] = int(item.get("manual_price", item_price_base))

                        custom_price = st.number_input(
                            "手直し後の金額（円）",
                            min_value=0,
                            max_value=10000000,
                            value=int(st.session_state[val_key]),
                            step=500,
                            key=val_key
                        )
                        item["manual_price"] = custom_price
                        diff = custom_price - item_price_base
                        if diff != 0:
                            st.caption(f"💡 自動計算（{item_price_base:,}円）から {diff:+,}円 手直し適用中")
                        item_breakdown_text = f"指定金額 = {custom_price:,}円"
                        item_price_base = custom_price
                    else:
                        st.markdown(f'<div style="text-align: right; font-size: 0.88rem; color: #475569; padding-top: 0.2rem;">小計（自動計算）: <b style="font-size: 1.05rem; color: #1E3A8A;">{item_price_base:,}</b> 円</div>', unsafe_allow_html=True)

                items_calculation_results.append({
                    "id": item_id,
                    "title": card_title,
                    "genre": item_display_genre,
                    "detail": item_detail_text,
                    "breakdown": item_breakdown_text,
                    "price_base": item_price_base
                })
                st.markdown("---")

        # 案件追加ボタン
        st.button("➕ 案件・動画を追加する（例: CMや2本目の番組など）", on_click=add_quote_item, use_container_width=True)

        # 番組マスタ管理
        with st.expander("⚙️ 固定単価番組マスタの登録・削除（一覧管理）"):
            custom_programs = load_custom_programs()
            st.caption("よく受ける番組やレギュラー案件を登録しておくと、「固定単価・レギュラー番組」でいつでも選べるようになります。")
            col_add_name, col_add_price, col_add_btn = st.columns([3, 2, 2])
            with col_add_name:
                new_prog_name = st.text_input("新しい番組名", placeholder="例: 〇〇チャンネル", key="new_p_name")
            with col_add_price:
                new_prog_price = st.number_input("単価（円/本）", min_value=500, max_value=100000, value=3000, step=500, key="new_p_price")
            with col_add_btn:
                st.write("")
                st.write("")
                if st.button("➕ 登録する", use_container_width=True):
                    if new_prog_name.strip():
                        existing_names = [p["name"] for p in custom_programs]
                        if new_prog_name.strip() in existing_names:
                            st.warning("既に同名の番組が登録されています。")
                        else:
                            custom_programs.append({"name": new_prog_name.strip(), "price": int(new_prog_price)})
                            save_custom_programs(custom_programs)
                            st.success(f"「{new_prog_name.strip()}」を登録しました！")
                            st.rerun()
                    else:
                        st.warning("番組名を入力してください。")

            st.markdown("##### 📋 現在登録済みの番組一覧")
            if not custom_programs:
                st.caption("登録済みの番組はありません。")
            else:
                for i, p in enumerate(custom_programs):
                    c_info, c_del = st.columns([4, 1])
                    with c_info:
                        st.write(f"・ **{p['name']}**: {p['price']:,} 円 / 本")
                    with c_del:
                        if st.button("🗑️ 削除", key=f"del_prog_{i}", use_container_width=True):
                            custom_programs.pop(i)
                            save_custom_programs(custom_programs)
                            st.success(f"「{p['name']}」を削除しました。")
                            st.rerun()

        # 全体のお値引き・端数調整（手直し）
        with st.expander("✂️ 全体のお値引き・端数調整（手直し・任意）", expanded=False):
            st.markdown('<div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.5rem;">合計金額に対して、まとめ割や端数の切り捨て・手動お値引き等を設定できます。</div>', unsafe_allow_html=True)
            col_adj1, col_adj2 = st.columns([3, 2])
            with col_adj1:
                st.text_input(
                    "調整項目名・理由",
                    value=st.session_state.get("quote_overall_adj_note", "端数調整・お値引き"),
                    placeholder="例: 端数調整、まとめ割、リピート割引 など",
                    key="quote_overall_adj_note"
                )
            with col_adj2:
                st.number_input(
                    "調整金額（円 / 値引きはマイナス入力）",
                    value=int(st.session_state.get("quote_overall_adj", 0)),
                    step=500,
                    key="quote_overall_adj",
                    help="合計金額から直接差し引く（または加算する）金額を指定できます。値引きの場合は -1000 のようにマイナスで入力してください。"
                )

        # 税金・表記オプション
        tax_options = ["税込（内税表記）", "税抜（+消費税）", "税込（10%内訳明記）"]
        tax_captions = ["主にココナラ", "主にランサーズ", "企業・請求書向け"]
        cur_tax = st.session_state.get("quote_tax_option", "税込（内税表記）")
        tax_idx = tax_options.index(cur_tax) if cur_tax in tax_options else 0
        tax_option = st.radio(
            "消費税の表示",
            tax_options,
            captions=tax_captions,
            index=tax_idx,
            horizontal=True,
            key="quote_tax_option"
        )

        st.markdown("---")
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-teal">STEP 2</span>
            <span>制作スケジュール（案）の設定</span>
        </div>
        """, unsafe_allow_html=True)

        # スケジュール入力モード判定
        num_items = len(st.session_state.quote_items)
        if num_items > 1:
            schedule_mode_options = [
                "📅 案件ごとに個別に設定（推奨）",
                "📅 全案件まとめて共通設定",
                "✏️ 自由に入力する（ココナラ形式など）"
            ]
        else:
            schedule_mode_options = [
                "📅 カレンダーから設定（おすすめ）",
                "✏️ 自由に入力する（特殊な指定など）"
            ]

        cur_sched_mode = st.session_state.get("quote_sched_mode", schedule_mode_options[0])
        sched_mode_idx = schedule_mode_options.index(cur_sched_mode) if cur_sched_mode in schedule_mode_options else 0
        schedule_mode = st.radio(
            "スケジュールの設定方法",
            schedule_mode_options,
            index=sched_mode_idx,
            horizontal=True,
            key="quote_sched_mode"
        )

        item_schedules = []
        sched_delivery_text = ""
        sched_handover_text = ""
        sched_work_text = ""
        sched_display_style = "📋 案件ごとにまとめて表示（おすすめ）"

        if "案件ごとに個別に設定" in schedule_mode:
            st.caption("💡 各案件ごとに納期・搬入日・作業予定日を設定できます。大型案件で作業が複数日にまたがる場合は「➕ 作業予定日を追加」で2日目、3日目…と追加できます。")
            for idx, res in enumerate(items_calculation_results):
                item_id = res["id"]
                item_key = f"item_{item_id}"
                item_label = f"{idx + 1}本目：{res['detail'].split('（')[0].strip()}"
                with st.container(border=True):
                    sched_data = render_schedule_inputs(
                        item_key=item_key,
                        item_title=item_label,
                        default_del_days=3 + idx * 4,
                        default_han_days=1 + idx * 3,
                        default_work_days_offset=1 + idx * 3,
                        show_title=True
                    )
                    item_schedules.append(sched_data)

            st.markdown("##### ⚙️ スケジュールの表示・表記設定")
            col_chk1, col_chk2, col_chk3 = st.columns(3)
            with col_chk1:
                use_delivery = st.checkbox("納期を含める", value=st.session_state.get("m_chk_del", True), key="m_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=st.session_state.get("m_chk_han", True), key="m_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=st.session_state.get("m_chk_wrk", True), key="m_chk_wrk")

            cur_disp_style = st.session_state.get("quote_sched_disp_style", "📋 案件ごとにまとめて表示（おすすめ）")
            disp_style_opts = [
                "📋 案件ごとにまとめて表示（おすすめ）",
                "📑 項目別（納期・搬入・作業日順）に表示"
            ]
            disp_idx = disp_style_opts.index(cur_disp_style) if cur_disp_style in disp_style_opts else 0
            sched_display_style = st.radio(
                "メッセージ内の表記スタイル",
                disp_style_opts,
                index=disp_idx,
                horizontal=True,
                key="quote_sched_disp_style",
                help="お相手へのメッセージ内で、案件ごとにタイムラインをブロック分けして見せるか、納期・搬入日・作業日ごとに箇条書きにするかを選べます。"
            )

        elif "全案件まとめて共通設定" in schedule_mode or "カレンダーから設定" in schedule_mode:
            with st.container(border=True):
                if num_items > 1:
                    st.caption("全案件共通のスケジュールを設定します。")
                common_data = render_schedule_inputs(
                    item_key="common" if num_items > 1 else "single",
                    item_title="制作スケジュール",
                    default_del_days=3,
                    default_han_days=1,
                    default_work_days_offset=1,
                    show_title=False
                )
                sched_delivery_text = common_data["delivery"]
                sched_handover_text = common_data["handover"]
                sched_work_text = common_data["work"]

            col_chk1, col_chk2, col_chk3 = st.columns(3)
            with col_chk1:
                use_delivery = st.checkbox("納期を含める", value=st.session_state.get("s_chk_del", True), key="s_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=st.session_state.get("s_chk_han", True), key="s_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=st.session_state.get("s_chk_wrk", True), key="s_chk_wrk")

        else:
            # 自由入力モード
            with st.container(border=True):
                sched_delivery_text = st.text_input(
                    "ご希望納期",
                    value=st.session_state.get("free_delivery_input", "1本目：11/3（火）中、2本目：11/10（火）まで"),
                    placeholder="例: 1本目：11/3（火）中、2本目：11/10（火）まで",
                    key="free_delivery_input"
                )
                sched_handover_text = st.text_input(
                    "データご搬入",
                    value=st.session_state.get("free_handover_input", "本編：未定、ナレ：11/2（月）21:30ごろ"),
                    placeholder="例: 素材受領済み、または 本編：未定、ナレ：11/2（月）21:30ごろ",
                    key="free_handover_input"
                )
                sched_work_text = st.text_input(
                    "作業予定日",
                    value=st.session_state.get("free_work_input", "11/2（月）夜、11/4 夕方以降"),
                    placeholder="例: 11/2（月）夜、11/4 夕方以降",
                    key="free_work_input"
                )

            col_chk1, col_chk2, col_chk3 = st.columns(3)
            with col_chk1:
                use_delivery = st.checkbox("納期を含める", value=st.session_state.get("f_chk_del", True), key="f_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=st.session_state.get("f_chk_han", True), key="f_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=st.session_state.get("f_chk_wrk", True), key="f_chk_wrk")

        st.markdown("**スケジュールの確保状況（相手に合わせて選択）**")
        res_opts = [
            "⚡ 先着順（新規・通常向け）",
            "🤝 仮確保中（お得意様・リピーター向け）",
            "なし（記載しない）"
        ]
        cur_res = st.session_state.get("quote_sched_res_type", "なし（記載しない）")
        res_idx = res_opts.index(cur_res) if cur_res in res_opts else 2
        schedule_reservation_type = st.radio(
            "スケジュールの案内トーン",
            res_opts,
            index=res_idx,
            horizontal=True,
            key="quote_sched_res_type",
            help="お得意様には「枠をキープしています」、新規の方には「先着順です」と適切なトーンで伝えます。"
        )

        include_delay_note = st.checkbox(
            "搬入遅延に関する注記を含める",
            value=st.session_state.get("quote_inc_delay_note", True),
            help="データ搬入が遅れた場合に納期が後ろ倒しになる可能性の注記です。",
            key="quote_inc_delay_note"
        )

        # 納品仕様・作業内容・音声レベル設定
        st.markdown("---")
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-purple">STEP 3</span>
            <span>納品仕様・作業内容・修正規定</span>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("🎚️ 納品仕様・作業内容・音声レベル設定（詳細）", expanded=True):
            st.markdown("##### 🛠️ 主な作業内容の選択")
            include_work_contents = st.checkbox(
                "メッセージに「主な作業内容」を含める",
                value=st.session_state.get("chk_inc_work_contents", True),
                key="chk_inc_work_contents"
            )

            c_task1 = True
            c_task2 = True
            c_task3 = True
            c_task4 = True
            c_custom_task = ""

            if include_work_contents:
                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    c_task1 = st.checkbox("ノイズ除去", value=st.session_state.get("chk_task1", True), key="chk_task1", help="リップノイズ・部屋鳴り・環境音の低減")
                    c_task2 = st.checkbox("音量・音圧調整", value=st.session_state.get("chk_task2", True), key="chk_task2", help="ラウドネス規準準拠のバランス調整")
                with t_col2:
                    c_task3 = st.checkbox("BGM・効果音MA", value=st.session_state.get("chk_task3", True), key="chk_task3", help="BGM・効果音（SE）のMA処理・整音ミックス")
                    c_task4 = st.checkbox("マスタリング・書出", value=st.session_state.get("chk_task4", True), key="chk_task4", help="マスタリングおよび指定フォーマットでの書き出し")

                c_custom_task = st.text_input(
                    "追加の作業内容（任意）",
                    value=st.session_state.get("txt_custom_task", ""),
                    placeholder="例: テロップ合わせ、BGM選定 など",
                    key="txt_custom_task"
                )

            st.markdown("---")
            st.markdown("##### 🎚️ 音声仕様・修正規定")
            audio_spec_opts = [
                "平均ラウドネス値 -24.0 LKFS (TP -1.0dBTP以下)",
                "目標ラウドネス値 -14.0 LUFS (TP -1.0dBTP以下)",
                "目標ラウドネス値 -16.0 LUFS (TP -1.0dBTP以下)",
                "クライアント様指定基準に準拠",
                "指定なし（最適なバランスに調整）"
            ]
            cur_spec = st.session_state.get("quote_audio_spec", audio_spec_opts[0])
            spec_idx = audio_spec_opts.index(cur_spec) if cur_spec in audio_spec_opts else 0
            audio_spec = st.selectbox(
                "音声レベル（ラウドネス規準）",
                audio_spec_opts,
                index=spec_idx,
                key="quote_audio_spec"
            )

            include_lufs14_note = False
            if "14.0 LUFS" in audio_spec:
                include_lufs14_note = st.checkbox(
                    "音質維持に関する注記を含める（-14 LUFSが困難な場合の案内）",
                    value=st.session_state.get("quote_inc_lufs14", False),
                    help="作品の構成や音割れ・ノイズ浮き防止のため、最適な聴きやすさ（-15〜-16 LUFS前後）を優先する旨の案内です。",
                    key="quote_inc_lufs14"
                )

            include_raw_audio_note = st.checkbox(
                "素材状態に関する事前注記を含める（ノイズ過多時の再見積もり予防線）",
                value=st.session_state.get("quote_inc_raw_note", False),
                help="一般的な収録状態を想定した見積もりであり、ノイズが極端に多い場合は再見積もり相談となる旨の事前注記です。",
                key="quote_inc_raw_note"
            )

            audio_fmt_opts = [
                "WAV (48kHz / 24bit)",
                "WAV (48kHz / 16bit)",
                "WAV",
                "WAV + MP3 (320kbps)",
                "ご指定のフォーマット"
            ]
            cur_fmt = st.session_state.get("quote_audio_fmt", audio_fmt_opts[0])
            fmt_idx = audio_fmt_opts.index(cur_fmt) if cur_fmt in audio_fmt_opts else 0
            audio_format = st.selectbox(
                "納品フォーマット",
                audio_fmt_opts,
                index=fmt_idx,
                key="quote_audio_fmt"
            )

            retake_policy_options = [
                "2回まで無料対応（編集直しによる素材差し替え等は別途費用が掛かる場合もございます）",
                "2回まで無料対応（当方のミス・見落とし等は無償対応）",
                "1回まで無料対応（音量バランス等の軽微な微調整）",
                "要相談（修正内容・工数に応じてご相談）",
                "記載しない",
                "✏️ 直接入力"
            ]
            cur_retake = st.session_state.get("quote_retake_choice", "記載しない")
            retake_idx = retake_policy_options.index(cur_retake) if cur_retake in retake_policy_options else 4
            retake_policy_choice = st.selectbox(
                "修正対応の規定",
                retake_policy_options,
                index=retake_idx,
                key="quote_retake_choice"
            )
            if retake_policy_choice == "✏️ 直接入力":
                custom_retake = st.text_input(
                    "修正対応の直接入力",
                    value=st.session_state.get("custom_retake_policy", ""),
                    placeholder="例: 2回まで無料対応（編集直しによる素材差し替え等は別途）",
                    key="custom_retake_policy"
                )
                retake_policy = custom_retake.strip() if custom_retake.strip() else "記載しない"
            else:
                retake_policy = retake_policy_choice

            include_rework_fee_note = st.checkbox(
                "編集直し・素材差し替えに関する追加費用の注記を含める",
                value=st.session_state.get("quote_inc_rework_note", False),
                help="クライアント都合の映像編集直しや素材差し替え、構成変更による再作業は別途費用相談となる旨の注記です。",
                key="quote_inc_rework_note"
            )

        with st.expander("ℹ️ 料金テーブルの確認（基準レート）"):
            st.markdown("""
            | ジャンル | 5分 (約2h) | 15分 (約3h) | 30分 (約4h) | 60分 (約8h) | 補間レート |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | **番組** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **YouTube・配信** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **ドラマ・自主映画** | 12,000円 | 18,000円 | 24,000円 | 48,000円 | 30分超: 800円/分 |
            
            - **CM（15秒・30秒）**: 通常 3,000円 / お得意様 2,000円（単価の自由指定・素材補正も可能）
            - **固定単価・レギュラー番組**: 番組ごとに設定した単価 × 本数
            - **その他（作業時間計算）**: 1時間あたり 3,000円
            """)

    # --- 全アイテムの合算計算 ---
    items_total = sum(res["price_base"] for res in items_calculation_results)
    overall_adj = int(st.session_state.get("quote_overall_adj", 0))
    overall_note = st.session_state.get("quote_overall_adj_note", "端数調整・お値引き").strip() or "お値引き・調整"
    total_price_base = max(0, items_total + overall_adj)

    # 税計算
    if "10%" in tax_option:
        display_total = int(round(total_price_base * 1.10))
        price_label = f"{display_total:,} 円（税込）"
        tax_detail = f"税抜合計: ¥{total_price_base:,} / 消費税(10%): ¥{int(round(total_price_base * 0.10)):,}"
    elif "税抜" in tax_option:
        display_total = total_price_base
        tax_amount = int(round(total_price_base * 0.10))
        price_label = f"{display_total:,} 円（税抜 / 税込 {display_total + tax_amount:,} 円）"
        tax_detail = f"消費税(10%): ¥{tax_amount:,}"
    else:  # 税込（内税表記）
        display_total = total_price_base
        price_label = f"{display_total:,} 円（税込）"
        tax_detail = f"※上記金額には消費税が含まれております。"

    # --- 右カラム: 計算結果 & メッセージ生成 ---
    with col_result:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-green">RESULT</span>
            <span>お見積り金額・送信メッセージ</span>
        </div>
        """, unsafe_allow_html=True)

        # 合計金額表示カード（インデントによるコードブロック誤判定を防ぐため1行結合）
        breakdown_items = []
        for res in items_calculation_results:
            breakdown_items.append(
                f'<div class="breakdown-item"><span style="font-weight: 500;">{res["detail"]}</span><span class="breakdown-price">{res["price_base"]:,} 円</span></div>'
            )
        if overall_adj != 0:
            adj_color = "#059669" if overall_adj < 0 else "#2563EB"
            breakdown_items.append(
                f'<div class="breakdown-item" style="color: {adj_color}; font-weight: 600;"><span>✂️ {overall_note}</span><span class="breakdown-price">{overall_adj:+,} 円</span></div>'
            )
        breakdown_html = "".join(breakdown_items)

        metric_card_html = (
            f'<div class="metric-card">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">'
            f'<span style="font-size: 0.88rem; font-weight: 700; color: #475569; letter-spacing: 0.5px;">合計お見積り金額</span>'
            f'<span class="tax-note">{tax_detail}</span>'
            f'</div>'
            f'<div class="total-price">{price_label}</div>'
            f'<div class="breakdown-box">'
            f'<div class="breakdown-title">📋 案件別・内訳明細</div>'
            f'{breakdown_html}'
            f'</div>'
            f'</div>'
        )
        st.markdown(metric_card_html, unsafe_allow_html=True)

        client_display_name = format_client_display(client_name, client_honorific)
        client_header = f"{client_display_name}\n\n" if client_display_name else ""
        client_header_short = f"{client_display_name}\n" if client_display_name else ""
        project_display = f"「{project_title.strip()}」" if project_title.strip() else ""

        # スケジュールブロック作成
        schedule_main_text = ""
        schedule_delivery_summary = ""

        if "案件ごとに個別に設定" in schedule_mode and item_schedules:
            if sched_display_style == "📋 案件ごとにまとめて表示（おすすめ）":
                item_blocks = []
                for s in item_schedules:
                    lines = []
                    if use_delivery and s["delivery"].strip():
                        lines.append(f"・ご希望納期： {s['delivery'].strip()}")
                    if use_handover and s["handover"].strip():
                        lines.append(f"・データご搬入： {s['handover'].strip()}")
                    if use_work and s["work"].strip():
                        lines.append(f"・作業予定日： {s['work'].strip()}")
                    if lines:
                        item_blocks.append(f"【{s['title']}】\n" + "\n".join(lines))
                schedule_main_text = "\n\n".join(item_blocks)
            else:
                main_lines = []
                if use_delivery:
                    del_lines = [f"  - {s['title']}： {s['delivery'].strip()}" for s in item_schedules if s["delivery"].strip()]
                    if del_lines:
                        main_lines.append("・ご希望納期：\n" + "\n".join(del_lines))
                if use_handover:
                    han_lines = [f"  - {s['title']}： {s['handover'].strip()}" for s in item_schedules if s["handover"].strip()]
                    if han_lines:
                        main_lines.append("・データご搬入：\n" + "\n".join(han_lines))
                if use_work:
                    work_lines = [f"  - {s['title']}： {s['work'].strip()}" for s in item_schedules if s["work"].strip()]
                    if work_lines:
                        main_lines.append("・作業予定日：\n" + "\n".join(work_lines))
                schedule_main_text = "\n".join(main_lines)

            if use_delivery:
                del_items = []
                for s in item_schedules:
                    if s["delivery"].strip():
                        prefix = s["title"].split("：")[0] if "：" in s["title"] else s["title"]
                        del_items.append(f"{prefix}: {s['delivery'].strip()}")
                schedule_delivery_summary = " / ".join(del_items)
        else:
            lines = []
            if use_delivery and sched_delivery_text.strip():
                lines.append(f"・ご希望納期： {sched_delivery_text.strip()}")
            if use_handover and sched_handover_text.strip():
                lines.append(f"・データご搬入： {sched_handover_text.strip()}")
            if use_work and sched_work_text.strip():
                lines.append(f"・作業予定日： {sched_work_text.strip()}")
            schedule_main_text = "\n".join(lines)
            if use_delivery and sched_delivery_text.strip():
                schedule_delivery_summary = sched_delivery_text.strip()

        schedule_notes = []
        if schedule_reservation_type == "⚡ 先着順（新規・通常向け）":
            schedule_notes.append("※作業予定日は現時点の空き状況に基づく目安となります。スケジュールの仮押さえは行っておりませんので、正式なご依頼（ご購入）の先着順にて確定とさせていただきます。万が一他案件で枠が埋まってしまった場合は、日程の再調整（またはご辞退）をご相談させていただく場合がございます。")
        elif schedule_reservation_type == "🤝 仮確保中（お得意様・リピーター向け）":
            schedule_notes.append("※上記日程にて作業枠を仮確保（キープ）しております。素材のご準備状況やスケジュールの変更などがございましたら、柔軟に調整いたしますのでいつでもお気軽にご相談ください。")

        # 素材受領済みの判定（受領済みの場合は搬入遅延の注記を自動除外）
        is_all_received = False
        if "案件ごとに個別に設定" in schedule_mode and item_schedules:
            is_all_received = all(("受領" in s.get("handover", "") or "搬入済み" in s.get("handover", "")) for s in item_schedules)
        elif sched_handover_text:
            is_all_received = ("受領" in sched_handover_text or "搬入済み" in sched_handover_text)

        if include_delay_note and not is_all_received:
            schedule_notes.append("※データご搬入が予定より遅れた場合、納期が後ろ倒しになる可能性がございます。")

        schedule_block = ""
        if schedule_main_text.strip():
            schedule_block = "■ 制作スケジュール（案）\n" + schedule_main_text.strip()
            if schedule_notes:
                schedule_block += "\n" + "\n".join(schedule_notes)
            schedule_block += "\n\n"

        # 仕様・修正ブロック作成
        spec_lines = [
            f"・フォーマット： {audio_format}",
            f"・音声レベル： {audio_spec}"
        ]
        if include_lufs14_note:
            spec_lines.append("※作品全体のダイナミクス（音の強弱）や静寂の多い構成の場合、過度な音割れやノイズ浮きを防ぎ、聴きやすさを最優先して -15〜-16 LUFS 前後で着地・調整させていただく場合がございます。")
        if retake_policy != "記載しない":
            spec_lines.append(f"・修正対応： {retake_policy}")
        if include_rework_fee_note:
            spec_lines.append("※編集直しによる素材差し替え、新規ナレーションの追加、構成変更等に伴う再作業は、別途費用が掛かる場合もございます。")

        raw_audio_note_text = ""
        if include_raw_audio_note:
            raw_audio_note_text = "\n※上記は一般的な収録状態を想定したお見積りとなります。ノイズが極端に多い場合や極度の音割れ・部屋鳴り等の高度な修復を要する場合は、素材確認後に作業工数に応じた再お見積りをご相談させていただく場合がございます。\n"

        spec_block = "■ 納品データの仕様・修正規定\n" + "\n".join(spec_lines)

        # 内訳リストのテキスト生成
        if len(items_calculation_results) == 1 and overall_adj == 0:
            detail_items_text = f"（内訳：{items_calculation_results[0]['detail']}）"
            simple_items_summary = f"{items_calculation_results[0]['detail']}"
        else:
            detail_lines = ["【内訳明細】"]
            for i, res in enumerate(items_calculation_results):
                detail_lines.append(f"・{i + 1}. {res['detail']}: {res['price_base']:,} 円")
            if overall_adj != 0:
                detail_lines.append(f"・{overall_note}: {overall_adj:+,} 円")
            detail_items_text = "\n" + "\n".join(detail_lines)
            if overall_adj != 0:
                simple_items_summary = f"{len(items_calculation_results)}件合算 ＋ {overall_note}（{overall_adj:+,}円）"
            else:
                simple_items_summary = f"{len(items_calculation_results)}件合算（{items_calculation_results[0]['genre']} ほか）"

        # 主な作業内容ブロック作成
        work_block_coconala = ""
        work_block_detailed = ""

        if include_work_contents:
            tasks_coconala = []
            tasks_detailed = []

            if c_task1:
                tasks_coconala.append("・ノイズ除去（リップノイズ・部屋鳴り・環境音の低減）")
                tasks_detailed.append("音声素材のノイズ低減（リップノイズ・空調音・ヒスノイズ除去）")
            if c_task2:
                tasks_coconala.append("・音量・音圧バランス調整（ラウドネス規準準拠）")
                tasks_detailed.append("話者ごとの音量・声質バランスの調整（EQ・コンプレッサー処理）")
            if c_task3:
                tasks_coconala.append("・BGM・効果音（SE）のMA処理・整音ミックス")
                tasks_detailed.append("BGM・SE（効果音）の配置および適切なダッキング処理")
            if c_task4:
                tasks_coconala.append("・マスタリングおよび指定フォーマットでの書き出し")
                tasks_detailed.append("規定ラウドネス値に合わせた最終マスタリング")
            if c_custom_task.strip():
                tasks_coconala.append(f"・{c_custom_task.strip()}")
                tasks_detailed.append(c_custom_task.strip())

            if tasks_coconala:
                work_block_coconala = "■ 主な作業内容\n" + "\n".join(tasks_coconala)
            if tasks_detailed:
                work_block_detailed = "━━━━━━━━━━━━━━━━━━━━━━━━━━\n【作業工程・内容】\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(tasks_detailed)])

        coconala_work_part = f"\n\n{work_block_coconala}\n" if work_block_coconala else ""
        detailed_work_part = f"\n\n{work_block_detailed}" if work_block_detailed else ""

        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-blue">MESSAGE</span>
            <span>コピペ用送信メッセージ</span>
        </div>
        """, unsafe_allow_html=True)

        col_sig_t1_1, col_sig_t1_2 = st.columns([3, 2])
        with col_sig_t1_1:
            cur_sig_t1 = st.session_state.get("t1_sig_choice", st.session_state.get("proj_signature_type", "なし"))
            if cur_sig_t1 == "ココナラ・ランサーズ用":
                cur_sig_t1 = "ココナラ用"
            sig_t1_idx = SIG_OPTIONS.index(cur_sig_t1) if cur_sig_t1 in SIG_OPTIONS else 0
            selected_sig_t1 = st.radio(
                "🖋️ 末尾の署名を選択",
                SIG_OPTIONS,
                index=sig_t1_idx,
                horizontal=True,
                key="t1_sig_choice",
                on_change=sync_signature_type,
                args=("t1_sig_choice",)
            )
        with col_sig_t1_2:
            sig_prev_t1 = get_signature_text(selected_sig_t1).strip()
            if sig_prev_t1:
                first_line = sig_prev_t1.split("\n")[0]
                st.caption(f"👀 署名プレビュー: **{first_line}**" + ("…" if "\n" in sig_prev_t1 else ""))
            else:
                st.caption("👀 署名プレビュー: （署名なし）")

        sig_append_t1 = get_signature_text(selected_sig_t1)

        # パターン1: ココナラ・クラウドソーシング特化型
        quote_msg_coconala = f"""{client_header}いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）のお見積もり・スケジュール案をお送りいたします。

■ お見積り金額
合計： {price_label}
{detail_items_text}
{raw_audio_note_text}
{schedule_block}{spec_block}{coconala_work_part}
上記内容でご検討のほど、よろしくお願いいたします。
日程やご予算についてのご相談もお気軽にお知らせください。""" + sig_append_t1

        # パターン2: シンプル（チャット・即答用）
        simple_sched = f"\n・希望納期: {schedule_delivery_summary.strip()}" if schedule_delivery_summary.strip() else ""
        if schedule_reservation_type == "⚡ 先着順（新規・通常向け）":
            simple_sched_note = "\n※スケジュールは正式ご依頼の先着順で確定となります。"
        elif schedule_reservation_type == "🤝 仮確保中（お得意様・リピーター向け）":
            simple_sched_note = "\n※取り急ぎ上記日程で作業枠を仮確保しております！"
        else:
            simple_sched_note = ""

        quote_msg_simple = f"""{client_header_short}お世話になっております！
ご相談いただきました{project_display}音声編集（MA）のお見積もりです。

【お見積り】
・内容: {simple_items_summary}
・合計金額: {price_label}{simple_sched}{simple_sched_note}

仕様や日程のご相談も柔軟に対応可能ですので、ご確認のほどよろしくお願いいたします！""" + sig_append_t1

        # パターン3: ビジネスメール・詳細版
        quote_msg_detailed = f"""{client_header}いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）につきまして、お見積もりと制作進行案をご案内申し上げます。

━━━━━━━━━━━━━━━━━━━━━━━━━━
【お見積もり内容】
・合計金額 : {price_label}
{detail_items_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{raw_audio_note_text}
{schedule_block}{spec_block}{detailed_work_part}

━━━━━━━━━━━━━━━━━━━━━━━━━━
スケジュール等につきまして、調整のご要望がございましたらお申し付けくださいませ。
ご検討のほど、何卒よろしくお願い申し上げます。""" + sig_append_t1

        st.markdown("""
        <div class="copy-tip">
            💡 各タブ右上の <b>📋（コピーアイコン）</b> をクリックすると、一瞬でクリップボードにコピーできます。
        </div>
        """, unsafe_allow_html=True)

        q_tab1, q_tab2, q_tab3 = st.tabs([
            "🌟 ココナラ・案件提案用（スケジュール・仕様入り）",
            "⚡ シンプル版（チャット用）",
            "📋 詳細版（ビジネスメール用）"
        ])

        with q_tab1:
            st.code(quote_msg_coconala, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=quote_msg_coconala, height=350, key="edit_coconala")

        with q_tab2:
            st.code(quote_msg_simple, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=quote_msg_simple, height=200, key="edit_simple")

        with q_tab3:
            st.code(quote_msg_detailed, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=quote_msg_detailed, height=350, key="edit_detailed")


# ==========================================
# タブ2: 業務連絡・ファイル送信メッセージ
# ==========================================
with tab2:
    col_comm_input, col_comm_result = st.columns([1, 1], gap="large")

    with col_comm_input:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-blue">STEP 1</span>
            <span>メッセージ設定・URL・コメント</span>
        </div>
        """, unsafe_allow_html=True)

        col_comm_c1, col_comm_c2 = st.columns([3, 1])
        with col_comm_c1:
            comm_client_name = st.text_input(
                "宛名 / クライアント名（任意）",
                value=st.session_state.get("t2_client_name", ""),
                placeholder="例: 株式会社〇〇 / 田中（敬称は自動付与）",
                key="t2_client_name",
                on_change=sync_client_name,
                args=("t2_client_name",)
            )
        with col_comm_c2:
            honorific_options = ["様", "さん", "なし"]
            cur_t2_hon = st.session_state.get("t2_client_honorific", "様")
            hon_t2_idx = honorific_options.index(cur_t2_hon) if cur_t2_hon in honorific_options else 0
            comm_client_honorific = st.selectbox(
                "敬称",
                honorific_options,
                index=hon_t2_idx,
                key="t2_client_honorific",
                on_change=sync_client_honorific,
                args=("t2_client_honorific",)
            )

        c_comm_p1, c_comm_p2 = st.columns([1, 1])
        with c_comm_p1:
            comm_project_name = st.text_input(
                "案件名（任意）",
                value=st.session_state.get("t2_project_name", ""),
                placeholder="例: YouTube対談動画",
                key="t2_project_name",
                on_change=sync_project_name,
                args=("t2_project_name",)
            )
        with c_comm_p2:
            comm_file_type = st.selectbox(
                "ファイルの種類",
                [
                    "ミックスファイル",
                    "初稿ミックス音源",
                    "修正版ミックス音源",
                    "完パケ（マスタリング済み）データ",
                    "パラデータ・ステム音源",
                    "MA済み映像データ",
                    "✏️ 直接指定"
                ],
                key="comm_file_type"
            )
            if comm_file_type == "✏️ 直接指定":
                comm_file_custom = st.text_input(
                    "ファイル種別の直接入力",
                    placeholder="例: 2mix（WAV・MP3）データ",
                    key="comm_file_custom"
                )
                file_label = comm_file_custom.strip() if comm_file_custom.strip() else "ファイル"
            else:
                file_label = comm_file_type

        comm_pattern = st.selectbox(
            "📋 定型文テンプレート（シチュエーション）",
            [
                "🎵 ファイル送付（基本・シンプル）",
                "🎧 初稿・ラフミックス送付（確認依頼）",
                "🔄 修正版ファイル送付（差し替え）",
                "📦 最終完成データ納品（検収依頼）",
                "📥 素材受領・作業着手のご連絡",
                "💬 自由作成（カスタム）"
            ],
            key="comm_pattern"
        )

        comm_url = st.text_area(
            "🔗 ファイルダウンロードURL（ギガファイル便、Google Drive等）",
            placeholder="例:\nhttps://63.gigafile.nu/1102-efb8d3101822180e3e19859a21594d79",
            height=90,
            key="comm_url"
        )

        comm_url_meta = st.text_input(
            "⏳ 保持期限・DLキー等（任意）",
            placeholder="例: ダウンロード期限: 7日間 / DLキー: 1234",
            key="comm_url_meta"
        )

        comm_free_text = st.text_area(
            "📝 自由コメント・特記事項・連絡事項（任意）",
            placeholder="例:\nボーカルの音量を少し持ち上げております。BGMとのバランスをご確認ください。\n気になる点がございましたら何でもお知らせください。",
            height=120,
            key="comm_free_text"
        )

        comm_closing = st.selectbox(
            "🤝 締めの挨拶",
            [
                "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。",
                "ご確認のほど、よろしくお願いいたします。",
                "気になる点や微調整のご希望がございましたら、お気軽にお申し付けください。",
                "問題ございませんでしたら、検収・正式納品のお手続きへお進みいただけますと幸いです。",
                "締めの挨拶なし（自由コメントのみで終了）"
            ],
            key="comm_closing"
        )

        col_sig_t2_1, col_sig_t2_2 = st.columns([3, 2])
        with col_sig_t2_1:
            cur_sig_t2 = st.session_state.get("t2_sig_choice", st.session_state.get("proj_signature_type", "なし"))
            if cur_sig_t2 == "ココナラ・ランサーズ用":
                cur_sig_t2 = "ココナラ用"
            sig_t2_idx = SIG_OPTIONS.index(cur_sig_t2) if cur_sig_t2 in SIG_OPTIONS else 0
            comm_sig = st.radio(
                "🖋️ メッセージ末尾の署名を選択",
                SIG_OPTIONS,
                index=sig_t2_idx,
                horizontal=True,
                key="t2_sig_choice",
                on_change=sync_signature_type,
                args=("t2_sig_choice",)
            )
        with col_sig_t2_2:
            sig_prev_t2 = get_signature_text(comm_sig).strip()
            if sig_prev_t2:
                first_line = sig_prev_t2.split("\n")[0]
                st.caption(f"👀 署名プレビュー: **{first_line}**" + ("…" if "\n" in sig_prev_t2 else ""))
            else:
                st.caption("👀 署名プレビュー: （署名なし）")

    # --- メッセージ生成ロジック ---
    def generate_comm_msg(tone: str) -> str:
        c_disp = format_client_display(comm_client_name, comm_client_honorific)
        c_header = f"{c_disp}\n\n" if c_disp else ""
        proj_prefix = f"「{comm_project_name.strip()}」の" if comm_project_name.strip() else ""

        url_lines = []
        if comm_url.strip():
            url_lines.append(comm_url.strip())
        if comm_url_meta.strip():
            url_lines.append(f"※{comm_url_meta.strip()}")
        url_section = "\n".join(url_lines)

        comment_section = comm_free_text.strip()

        closing_text = ""
        if comm_closing != "締めの挨拶なし（自由コメントのみで終了）":
            if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                if tone == "simple":
                    closing_text = "ご確認よろしくお願いいたします。\n気になる点ございましたらご連絡ください。"
                elif tone == "standard":
                    closing_text = "ご確認のほど、よろしくお願いいたします。\n気になる点やご要望などがございましたら、いつでもお気軽にご連絡ください。"
                else:
                    closing_text = "恐れ入りますが、内容をご確認いただけますようお願い申し上げます。\n修正や追加のご要望がございましたら、何なりとお申し付けくださいませ。"
            else:
                closing_text = comm_closing

        sig_text = get_signature_text(comm_sig)

        if comm_pattern == "🎵 ファイル送付（基本・シンプル）":
            if tone == "simple":
                greeting = "お世話になります。"
                lead = f"{file_label}お送りします。"
            elif tone == "standard":
                greeting = "いつもお世話になっております。"
                lead = f"{proj_prefix}{file_label}をお送りいたします。"
            else:
                greeting = "いつも大変お世話になっております。"
                lead = f"ご依頼いただいておりました{proj_prefix}{file_label}の書き出しが完了いたしましたので、ダウンロードURLをご案内申し上げます。"

        elif comm_pattern == "🎧 初稿・ラフミックス送付（確認依頼）":
            if tone == "simple":
                greeting = "お世話になります。"
                lead = f"{proj_prefix}{file_label}（初稿）の作業が完了しましたのでお送りします。"
                if not comment_section:
                    comment_section = "全体の音量感やバランス等をご確認いただけますと幸いです。"
            elif tone == "standard":
                greeting = "いつもお世話になっております。"
                lead = f"{proj_prefix}{file_label}（初稿）を作成いたしましたので、音源データをお送りいたします。"
                if not comment_section:
                    comment_section = "話者の聞き取りやすさや、BGM・効果音（SE）とのバランスを中心にご確認いただけますと幸いです。"
            else:
                greeting = "いつも大変お世話になっております。"
                lead = f"{proj_prefix}{file_label}の一次編集（初稿）作業が完了いたしましたので、共有データをお送り申し上げます。"
                if not comment_section:
                    comment_section = "規定仕様および全体のバランス調整を行っております。ご視聴いただき、ご意見や調整希望がございましたらお知らせください。"

        elif comm_pattern == "🔄 修正版ファイル送付（差し替え）":
            if tone == "simple":
                greeting = "お世話になります。"
                lead = f"ご指示いただいた修正を反映した{file_label}をお送りします。"
            elif tone == "standard":
                greeting = "いつもお世話になっております。"
                lead = f"ご指示いただきました修正箇所を反映した{file_label}をお送りいたします。"
            else:
                greeting = "いつも大変お世話になっております。"
                lead = f"過日ご指示を賜りました修正箇所につきまして、反映および再調整を行った{file_label}をお送り申し上げます。"

        elif comm_pattern == "📦 最終完成データ納品（検収依頼）":
            if tone == "simple":
                greeting = "お世話になります。"
                lead = f"{proj_prefix}最終完成データ（{file_label}）をお送りします。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "問題ございませんでしたら、このまま検収・完了のお手続きへお進みいただけますと幸いです。\nどうぞよろしくお願いいたします。"
            elif tone == "standard":
                greeting = "いつも大変お世話になっております。"
                lead = f"{proj_prefix}すべての音声編集（MA）工程が完了いたしましたので、最終納品データをお送りいたします。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "データをご確認いただき、問題がないようでしたら完了のお手続き（検収・評価）へお進みいただけますと幸いです。\nこの度はご依頼いただき、誠にありがとうございました！"
            else:
                greeting = "いつも大変お世話になっております。"
                lead = f"{proj_prefix}すべての整音およびマスタリング工程が完了いたしましたので、最終完パケデータ一式をご納品申し上げます。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "最終データをご査収いただき、問題がございませんでしたら検収のお手続きを賜りますようお願い申し上げます。\n今後とも何卒よろしくお願い申し上げます。"

        elif comm_pattern == "📥 素材受領・作業着手のご連絡":
            if tone == "simple":
                greeting = "お世話になります。"
                lead = f"素材データ（{file_label}）を無事受領いたしました。ご手配ありがとうございます。\nこれより作業に着手いたします。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "初稿の仕上がりまで今しばらくお待ちください。よろしくお願いいたします。"
            elif tone == "standard":
                greeting = "いつもお世話になっております。"
                lead = f"{proj_prefix}作業素材一式を無事に受領・確認いたしました。迅速なご手配をいただき誠にありがとうございます。\nこれより音声編集（MA）作業に着手させていただきます。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "予定スケジュールに沿って丁寧に進めてまいります。初稿のお届けまで今しばらくお待ちくださいませ。\n引き続きよろしくお願いいたします。"
            else:
                greeting = "いつも大変お世話になっております。"
                lead = f"ご手配いただきました{proj_prefix}制作素材一式を確かに受領いたしました。迅速にご対応いただき厚く御礼申し上げます。\nこれより規定仕様に準拠した整音・ミックス作業を開始いたします。"
                if comm_closing == "ご確認よろしくお願いいたします。気になる点ございましたらご連絡ください。":
                    closing_text = "予定納期に向けて進捗を進めてまいりますので、何卒よろしくお願い申し上げます。"

        else:  # 💬 自由作成（カスタム）
            greeting = "お世話になります。" if tone == "simple" else ("いつもお世話になっております。" if tone == "standard" else "いつも大変お世話になっております。")
            lead = ""

        # 各ブロックの結合
        parts = []
        if c_header:
            parts.append(c_header.strip())
        
        greeting_block = f"{greeting}\n{lead}" if lead else greeting
        parts.append(greeting_block.strip())

        if url_section:
            parts.append(url_section.strip())

        if comment_section:
            parts.append(comment_section.strip())

        if closing_text:
            parts.append(closing_text.strip())

        if sig_text.strip():
            parts.append(sig_text.strip())

        raw_msg = "\n\n".join(parts)
        cleaned_msg = re.sub(r'\n{3,}', '\n\n', raw_msg.strip())
        return cleaned_msg

    comm_msg_simple = generate_comm_msg("simple")
    comm_msg_standard = generate_comm_msg("standard")
    comm_msg_formal = generate_comm_msg("formal")

    with col_comm_result:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-teal">STEP 2</span>
            <span>送信メッセージの確認・コピー</span>
        </div>
        <div class="copy-tip">
            💡 各タブ右上の <b>📋（コピーアイコン）</b> をクリックすると、一瞬でクリップボードにコピーできます。
        </div>
        """, unsafe_allow_html=True)

        comm_subtab1, comm_subtab2, comm_subtab3 = st.tabs([
            "⚡ シンプル（短文チャット用）",
            "📝 標準（丁寧・親しみ）",
            "👔 フォーマル（ビジネス用）"
        ])

        with comm_subtab1:
            st.markdown("##### ⚡ シンプル版（要点直球・短文）")
            st.code(comm_msg_simple, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=comm_msg_simple, height=220, key="edit_comm_simple")

        with comm_subtab2:
            st.markdown("##### 📝 標準版（バランス・親しみやすい丁寧さ）")
            st.code(comm_msg_standard, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=comm_msg_standard, height=250, key="edit_comm_std")

        with comm_subtab3:
            st.markdown("##### 👔 フォーマル版（ビジネス・企業向け）")
            st.code(comm_msg_formal, language="markdown")
            with st.expander("✏️ テキストを直接編集してコピーしたい場合"):
                st.text_area("編集用テキストエリア", value=comm_msg_formal, height=280, key="edit_comm_formal")


# ==========================================
# タブ3: 評価コメント作成
# ==========================================
with tab3:
    col_eval_input, col_eval_result = st.columns([1, 1], gap="large")

    with col_eval_input:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-blue">STEP 1</span>
            <span>取引状況・トーンの設定</span>
        </div>
        """, unsafe_allow_html=True)

        col_eval_c1, col_eval_c2 = st.columns([3, 1])
        with col_eval_c1:
            eval_client_name = st.text_input(
                "クライアント名（任意）",
                value=st.session_state.get("t3_client_name", ""),
                placeholder="例: 株式会社〇〇 / 田中（敬称は自動付与）",
                key="t3_client_name",
                on_change=sync_client_name,
                args=("t3_client_name",)
            )
        with col_eval_c2:
            honorific_options = ["様", "さん", "なし"]
            cur_t3_hon = st.session_state.get("t3_client_honorific", "様")
            hon_t3_idx = honorific_options.index(cur_t3_hon) if cur_t3_hon in honorific_options else 0
            eval_client_honorific = st.selectbox(
                "敬称",
                honorific_options,
                index=hon_t3_idx,
                key="t3_client_honorific",
                on_change=sync_client_honorific,
                args=("t3_client_honorific",)
            )

        eval_project_name = st.text_input(
            "案件名（任意）",
            value=st.session_state.get("t3_project_name", ""),
            placeholder="例: YouTube対談動画 MA作業",
            key="t3_project_name",
            on_change=sync_project_name,
            args=("t3_project_name",)
        )

        # 1. やり取りの印象
        impression_options = ["とてもスムーズ", "普通", "少し時間がかかった"]
        cur_imp = st.session_state.get("eval_impression", "とてもスムーズ")
        imp_idx = impression_options.index(cur_imp) if cur_imp in impression_options else 0
        impression = st.selectbox(
            "やり取りの印象",
            impression_options,
            index=imp_idx,
            help="相手の対応スピードややり取りの円滑さに合わせてコメントのトーンを自動調整します。",
            key="eval_impression"
        )

        # 2. 次回へのアピール
        appeal_flag = st.checkbox(
            "次回へのアピールを含める",
            value=st.session_state.get("eval_appeal_flag", True),
            help="チェックを入れると「また音声編集でお困りならお声がけください」といった一文を末尾に追加します。",
            key="eval_appeal_flag"
        )

        col_sig_t3_1, col_sig_t3_2 = st.columns([3, 2])
        with col_sig_t3_1:
            cur_sig_t3 = st.session_state.get("t3_sig_choice", st.session_state.get("proj_signature_type", "なし"))
            if cur_sig_t3 == "ココナラ・ランサーズ用":
                cur_sig_t3 = "ココナラ用"
            sig_t3_idx = SIG_OPTIONS.index(cur_sig_t3) if cur_sig_t3 in SIG_OPTIONS else 0
            eval_sig = st.radio(
                "🖋️ メッセージ末尾の署名を選択",
                SIG_OPTIONS,
                index=sig_t3_idx,
                horizontal=True,
                key="t3_sig_choice",
                on_change=sync_signature_type,
                args=("t3_sig_choice",)
            )
        with col_sig_t3_2:
            sig_prev_t3 = get_signature_text(eval_sig).strip()
            if sig_prev_t3:
                first_line = sig_prev_t3.split("\n")[0]
                st.caption(f"👀 署名プレビュー: **{first_line}**" + ("…" if "\n" in sig_prev_t3 else ""))
            else:
                st.caption("👀 署名プレビュー: （署名なし）")

    # --- 評価・納品コメント生成ロジック ---
    c_eval_disp = format_client_display(eval_client_name, eval_client_honorific)
    eval_hdr = f"{c_eval_disp}\n\n" if c_eval_disp else ""
    eval_hdr_short = f"{c_eval_disp}\n" if c_eval_disp else ""
    target_project = f"「{eval_project_name.strip()}」の" if eval_project_name.strip() else ""

    # アピール文（トーン別）
    appeal_short = " また音声編集でお困りの際は気軽にお声がけください！" if appeal_flag else ""
    appeal_standard = "\n\nまた今後、音声編集（MA）やノイズ処理等でお困りの際や別案件がございましたら、ぜひお気軽にお声がけいただけますと幸いです。" if appeal_flag else ""
    appeal_formal = "\n\nなお、今後とも音声編集（MA）や整音作業等のご相談がございましたら、誠心誠意ご対応させていただきますので、何卒お気軽にお申し付けくださいませ。" if appeal_flag else ""
    appeal_review = " また音声編集でお困りの際はぜひお声がけください！" if appeal_flag else ""

    sig_eval_append = get_signature_text(eval_sig)

    # 1. 評価コメント（レビュー短文集：ココナラ・ランサーズ等の相手評価欄用）
    if impression == "とてもスムーズ":
        review_patterns = [
            (
                "① 定番・迅速丁寧（最もおすすめ）",
                f"迅速かつ丁寧にご対応いただき、終始安心してお取引を進めることができました。素晴らしいご縁に心より感謝申し上げます。{appeal_review}今後ともよろしくお願いいたします。"
            ),
            (
                "② 最短・1行シンプル（サクッと完了）",
                f"スムーズで気持ちの良いお取引をありがとうございました！また機会がございましたらよろしくお願いいたします。"
            ),
            (
                "③ 的確なご指示・レスポンス称賛",
                f"的確なご指示と素早いレスポンスをいただき、大変スムーズに進行できました。{appeal_review}またよろしくお願いいたします。"
            ),
            (
                "④ リピート・継続案件向け",
                f"今回も迅速・丁寧にご対応いただき誠にありがとうございました！今後ともどうぞよろしくお願いいたします。"
            )
        ]
    elif impression == "普通":
        review_patterns = [
            (
                "① 定番・丁寧感謝（バランス重視）",
                f"終始丁寧にご対応いただき、無事にお取引を完了することができました。ご依頼いただき誠にありがとうございました。{appeal_review}"
            ),
            (
                "② 最短・1行シンプル",
                f"ご丁寧なお取引をありがとうございました。また機会がございましたらよろしくお願いいたします。"
            ),
            (
                "③ スムーズ完了",
                f"迅速にご確認いただき、滞りなく納品まで進めることができました。またのご縁を心よりお待ちしております。"
            )
        ]
    else:  # 少し時間がかかった
        review_patterns = [
            (
                "① 定番・丁寧完了（配慮・お礼）",
                f"ご丁寧にご対応いただき、無事にお取引を完了することができました。最後までお付き合いいただきありがとうございました。{appeal_review}"
            ),
            (
                "② 最短・1行シンプル",
                f"無事にお取引を完了でき安心いたしました。ご依頼いただき誠にありがとうございました。"
            ),
            (
                "③ ご調整感謝",
                f"追加のご確認やお打ち合わせにご協力いただき感謝申し上げます。また機会がございましたらよろしくお願いいたします。"
            )
        ]

    # 2. 納品メッセージ（超シンプル・短文チャット集）
    if impression == "とてもスムーズ":
        q_thanks = "迅速にご対応いただき大変助かりました！"
    elif impression == "普通":
        q_thanks = "ご丁寧にご対応いただきありがとうございました。"
    else:
        q_thanks = "ご調整いただき誠にありがとうございました。"

    q_msg1 = f"""{eval_hdr_short}お世話になっております。{target_project}音声編集（MA）の納品データをお送りいたします。
ご確認のほどよろしくお願いいたします。{appeal_short}""" + sig_eval_append

    q_msg2 = f"""{eval_hdr_short}お世話になっております！
{target_project}作業が完了いたしましたので、納品データをお送りいたします。

{q_thanks}ご確認よろしくお願いいたします。{appeal_short}""" + sig_eval_append

    q_msg3 = f"""{eval_hdr_short}お世話になっております。{target_project}音声編集データを納品いたします。

仕上がりに気になる点や微調整のご希望などがございましたら、お気軽にお申し付けください。{appeal_short}""" + sig_eval_append

    q_msg4 = f"""{eval_hdr_short}お世話になっております。{target_project}納品データをご用意いたしました。
添付ファイル（または送付URL）よりダウンロードの上、ご確認いただけますと幸いです。

問題ございませんでしたら、検収・正式納品のお手続きへお進みください。{appeal_short}""" + sig_eval_append

    quick_delivery_patterns = [
        ("① 最短・直球（要点のみ・2行）", q_msg1),
        ("② 迅速感謝＋確認依頼（親しみやすさ）", q_msg2),
        ("③ 微調整受付付き（安心感）", q_msg3),
        ("④ ファイル受渡・検収案内（手続きスムーズ）", q_msg4)
    ]

    # 3. 納品メッセージ（標準版 & フォーマル版）
    if impression == "とてもスムーズ":
        msg_standard = f"""{eval_hdr}いつも大変お世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました！

ご指示や素材のご手配が非常に的確で、メッセージのレスポンスも迅速にしていただいたおかげで、終始大変スムーズに作業を進行することができました。心より感謝申し上げます。

納品データについて気になる点や微調整などがございましたら、いつでもお気軽にご連絡ください。{appeal_standard}

今後ともどうぞよろしくお願いいたします。""" + sig_eval_append

        msg_formal = f"""{eval_hdr}いつも大変お世話になっております。
この度は、{target_project}音声編集（MA）業務のご依頼を賜り、誠にありがとうございました。

ご指示や素材のご手配を迅速にいただき、円滑に作業を進行することができましたこと、深く感謝申し上げます。
納品データを添付いたしましたので、ご査収のほどよろしくお願い申し上げます。
修正や追加のご要望がございましたら、迅速に対応いたしますので何なりとお申し付けください。{appeal_formal}

今後とも何卒よろしくお願い申し上げます。""" + sig_eval_append

    elif impression == "普通":
        msg_standard = f"""{eval_hdr}いつも大変お世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

ご丁寧にご対応いただき、無事に納品完了まで進めることができました。
今回の仕上がりが今後の制作のお役に立てておりましたら幸いです。

納品データのご確認で何かございましたら、お申し付けください。{appeal_standard}

また機会がございましたら、どうぞよろしくお願い申し上げます。""" + sig_eval_append

        msg_formal = f"""{eval_hdr}いつも大変お世話になっております。
この度は、{target_project}音声編集（MA）業務のご依頼を賜り、心より御礼申し上げます。

ご丁寧なご連携をいただき、無事に納品工程を完了することができました。
仕上がりデータをご確認いただき、不都合な点などがございましたらご連絡いただけますと幸いです。{appeal_formal}

今後ともご愛顧のほど、よろしくお願い申し上げます。""" + sig_eval_append

    else:  # 少し時間がかかった
        msg_standard = f"""{eval_hdr}いつもお世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

追加のご調整やご確認などを経て、無事に納品完了まで進めることができ安心いたしました。最後まで丁寧にお付き合いいただき、誠にありがとうございました。

今回の音声データがお役に立ちましたら幸いでございます。{appeal_standard}

またの機会がございましたら、よろしくお願い申し上げます。""" + sig_eval_append

        msg_formal = f"""{eval_hdr}拝啓
貴社におかれましては、ますますご清栄のこととお慶び申し上げます。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

仕様の確認および追加調整にお時間を頂戴いたしましたが、無事に納品データを仕上げることができ安心いたしました。最後まで丁寧にお付き合いいただき厚く御礼申し上げます。
添付データのご確認をよろしくお願い申し上げます。{appeal_formal}

またの機会がございましたら、何卒よろしくお願い申し上げます。
敬具""" + sig_eval_append

    # --- 右カラム: 生成結果 ---
    with col_eval_result:
        st.markdown("""
        <div class="section-title">
            <span class="step-badge step-badge-teal">STEP 2</span>
            <span>納品・評価コメントのコピー</span>
        </div>
        <div class="copy-tip">
            💡 各カード右上の <b>📋（コピーアイコン）</b> をクリックすると、一瞬でクリップボードにコピーできます。
        </div>
        """, unsafe_allow_html=True)

        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "⭐ 評価コメント（レビュー短文集）",
            "⚡ 納品メッセージ（超シンプル集）",
            "📝 納品メッセージ（標準・丁寧）",
            "👔 納品メッセージ（フォーマル）"
        ])

        with subtab1:
            st.markdown("##### ⭐ プラットフォーム評価欄用（レビュー短文・厳選パターン）")
            st.caption("💡 ココナラ・ランサーズ等の取引完了時の評価入力欄に最適です。右上の 📋 からワンクリックでコピーできます。")
            for title, rev_text in review_patterns:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.code(rev_text, language="text")

        with subtab2:
            st.markdown("##### ⚡ 納品メッセージ（超シンプル・短文チャット集）")
            st.caption("💡 チャットや要点のみの送付に最適です。右上の 📋 からワンクリックでコピーできます。")
            for title, q_text in quick_delivery_patterns:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.code(q_text, language="markdown")

        with subtab3:
            st.markdown("##### 📝 標準版（バランス・親しみやすい丁寧さ）")
            st.code(msg_standard, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_standard, height=250, key="edit_ev_std")

        with subtab4:
            st.markdown("##### 👔 フォーマル版（ビジネス・企業向け）")
            st.code(msg_formal, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_formal, height=280, key="edit_ev_formal")
