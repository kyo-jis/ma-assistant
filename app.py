import datetime
import json
import os
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
        st.markdown(f"**📌 {item_title}**")

    # 1. 希望納期
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
        "work": work_text
    }

# カスタムCSS
st.markdown("""
<style>
    /* メインタイトル */
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    /* カード風スタイル */
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .item-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .total-price {
        font-size: 2.2rem;
        font-weight: 800;
        color: #2563EB;
    }
    .tax-note {
        font-size: 0.85rem;
        color: #64748B;
    }
    /* タブデザイン */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 600;
    }
    /* コードブロックのフォントと余白改善 */
    pre code {
        font-size: 0.92rem !important;
        line-height: 1.6 !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
    }
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
# アプリケーションヘッダー
# ==========================================
st.markdown('<div class="main-header">🎙️ 音声編集（MA）業務アシスタント</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">見積もり計算からコピペ用メッセージ、納品後の評価コメントまでをワンストップで作成します。</div>', unsafe_allow_html=True)

# 2つのタブを作成
tab1, tab2 = st.tabs(["💰 見積もり・提案作成", "💬 納品・評価コメント作成"])


# ==========================================
# タブ1: 見積もり作成
# ==========================================
with tab1:
    col_input, col_result = st.columns([1, 1], gap="large")

    with col_input:
        st.subheader("📋 案件・基本情報の入力")

        # 宛名・案件名
        client_name = st.text_input("クライアント名（任意）", placeholder="例: 〇〇 様")
        project_title = st.text_input("案件名・案件全体の概要（任意）", placeholder="例: レギュラー番組 ＋ 番宣CM制作 MA作業")

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
            card_title = f"🎬 依頼内容 {idx + 1}" if num_items > 1 else "🎬 依頼内容"

            with st.container():
                st.markdown(f"#### {card_title}")

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
                            st.session_state[dur_key] = 15.0
                        duration_val = st.number_input(
                            "尺（分）",
                            min_value=1.0,
                            max_value=300.0,
                            step=step_unit,
                            key=dur_key
                        )

                    # 加減算ボタン
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        if st.button("⏪ -10分", key=f"b1_{item_id}", use_container_width=True):
                            st.session_state[dur_key] = max(1.0, duration_val - 10)
                            st.rerun()
                    with b2:
                        if st.button("◀ -5分", key=f"b2_{item_id}", use_container_width=True):
                            st.session_state[dur_key] = max(1.0, duration_val - 5)
                            st.rerun()
                    with b3:
                        if st.button("+5分 ▶", key=f"b3_{item_id}", use_container_width=True):
                            st.session_state[dur_key] = min(300.0, duration_val + 5)
                            st.rerun()
                    with b4:
                        if st.button("+10分 ⏩", key=f"b4_{item_id}", use_container_width=True):
                            st.session_state[dur_key] = min(300.0, duration_val + 10)
                            st.rerun()

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
                        selected_cond = st.selectbox("素材状態・工数補正", condition_options, key=f"cond_{item_id}")

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

                    item_price_base = int(round(final_hours * 3000))
                    item_detail_text = f"{selected_genre} {duration_val:.1f}分（想定工数：約{final_hours:.1f}h）"
                    item_breakdown_text = f"{duration_val:.1f}分（約{final_hours:.1f}h × 3,000円）= {item_price_base:,}円"

                elif selected_genre == "CM（15秒・30秒）":
                    c_cm1, c_cm2 = st.columns(2)
                    with c_cm1:
                        cm_pattern = st.radio("取引先パターン", ["通常", "お得意様"], horizontal=True, key=f"cm_pat_{item_id}")
                    with c_cm2:
                        cm_count = st.number_input("本数", min_value=1, max_value=100, value=1, step=1, key=f"cm_cnt_{item_id}")
                    u_price = 2000 if cm_pattern == "お得意様" else 3000
                    item_price_base = u_price * cm_count
                    item_detail_text = f"CM（15秒・30秒） {cm_pattern}パターン（{u_price:,}円/本）× {cm_count}本"
                    item_breakdown_text = f"{u_price:,}円 × {cm_count}本 = {item_price_base:,}円"

                elif selected_genre == "固定単価・レギュラー番組":
                    custom_programs = load_custom_programs()
                    prog_options = [f"{p['name']}（{p['price']:,}円/本）" for p in custom_programs]
                    prog_options.append("＋ 新規・一時入力（登録せず直接入力）")

                    chosen_p = st.selectbox("番組の選択", prog_options, key=f"fixed_sel_{item_id}")
                    f_name = ""
                    f_price = 3000

                    if chosen_p == "＋ 新規・一時入力（登録せず直接入力）":
                        cn1, cn2 = st.columns([3, 2])
                        with cn1:
                            f_name = st.text_input("番組名", value="レギュラー番組", key=f"fn_{item_id}")
                        with cn2:
                            f_price = st.number_input("単価（円/本）", min_value=500, max_value=100000, value=3000, step=500, key=f"fp_{item_id}")
                    else:
                        idx_p = prog_options.index(chosen_p)
                        target_p = custom_programs[idx_p]
                        f_name = target_p["name"]
                        f_price = target_p["price"]

                    f_count = st.number_input("制作本数", min_value=1, max_value=100, value=1, step=1, key=f"fc_{item_id}")
                    item_price_base = f_price * f_count
                    item_display_genre = f"固定単価番組（{f_name}）"
                    item_detail_text = f"{f_name}（{f_price:,}円/本）× {f_count}本"
                    item_breakdown_text = f"{f_price:,}円 × {f_count}本 = {item_price_base:,}円"

                elif selected_genre == "その他（作業時間計算）":
                    w_hours = st.number_input("作業時間（時間単位）", min_value=0.5, max_value=200.0, value=2.0, step=0.5, key=f"wh_{item_id}")
                    item_price_base = int(round(w_hours * 3000))
                    item_detail_text = f"作業時間計算 {w_hours:.1f}時間（3,000円/h）"
                    item_breakdown_text = f"3,000円 × {w_hours:.1f}h = {item_price_base:,}円"

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

        # 税金・表記オプション
        tax_option = st.radio("消費税の表示", ["税込（内税表記）", "税込（10%）", "税抜（+消費税）"], index=0, horizontal=True)

        st.markdown("---")
        st.subheader("📅 制作スケジュール（案）の設定")

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

        schedule_mode = st.radio("スケジュールの設定方法", schedule_mode_options, horizontal=True)

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
                use_delivery = st.checkbox("納期を含める", value=True, key="m_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=True, key="m_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=True, key="m_chk_wrk")

            sched_display_style = st.radio(
                "メッセージ内の表記スタイル",
                [
                    "📋 案件ごとにまとめて表示（おすすめ）",
                    "📑 項目別（納期・搬入・作業日順）に表示"
                ],
                horizontal=True,
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
                use_delivery = st.checkbox("納期を含める", value=True, key="s_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=True, key="s_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=True, key="s_chk_wrk")

        else:
            # 自由入力モード
            with st.container(border=True):
                sched_delivery_text = st.text_input(
                    "ご希望納期",
                    value="1本目：11/3（火）中、2本目：11/10（火）まで",
                    placeholder="例: 1本目：11/3（火）中、2本目：11/10（火）まで",
                    key="free_delivery_input"
                )
                sched_handover_text = st.text_input(
                    "データご搬入",
                    value="本編：未定、ナレ：11/2（月）21:30ごろ",
                    placeholder="例: 本編：未定、ナレ：11/2（月）21:30ごろ",
                    key="free_handover_input"
                )
                sched_work_text = st.text_input(
                    "作業予定日",
                    value="11/2（月）夜、11/4 夕方以降",
                    placeholder="例: 11/2（月）夜、11/4 夕方以降",
                    key="free_work_input"
                )

            col_chk1, col_chk2, col_chk3 = st.columns(3)
            with col_chk1:
                use_delivery = st.checkbox("納期を含める", value=True, key="f_chk_del")
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=True, key="f_chk_han")
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=True, key="f_chk_wrk")

        st.markdown("**スケジュールの確保状況（相手に合わせて選択）**")
        schedule_reservation_type = st.radio(
            "スケジュールの案内トーン",
            [
                "⚡ 先着順（新規・通常向け）",
                "🤝 仮確保中（お得意様・リピーター向け）",
                "なし（記載しない）"
            ],
            index=2,
            horizontal=True,
            help="お得意様には「枠をキープしています」、新規の方には「先着順です」と適切なトーンで伝えます。"
        )

        include_delay_note = st.checkbox(
            "搬入遅延に関する注記を含める",
            value=True,
            help="データ搬入が遅れた場合に納期が後ろ倒しになる可能性の注記です。"
        )

        # 納品仕様・作業内容・音声レベル設定
        st.markdown("---")
        with st.expander("🎚️ 納品仕様・作業内容・音声レベル設定", expanded=True):
            st.markdown("##### 🛠️ 主な作業内容の選択")
            include_work_contents = st.checkbox("メッセージに「主な作業内容」を含める", value=True, key="chk_inc_work_contents")

            c_task1 = True
            c_task2 = True
            c_task3 = True
            c_task4 = True
            c_custom_task = ""

            if include_work_contents:
                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    c_task1 = st.checkbox("ノイズ除去", value=True, key="chk_task1", help="リップノイズ・部屋鳴り・環境音の低減")
                    c_task2 = st.checkbox("音量・音圧調整", value=True, key="chk_task2", help="ラウドネス規準準拠のバランス調整")
                with t_col2:
                    c_task3 = st.checkbox("BGM・効果音MA", value=True, key="chk_task3", help="BGM・効果音（SE）のMA処理・整音ミックス")
                    c_task4 = st.checkbox("マスタリング・書出", value=True, key="chk_task4", help="マスタリングおよび指定フォーマットでの書き出し")

                c_custom_task = st.text_input("追加の作業内容（任意）", placeholder="例: テロップ合わせ、BGM選定 など", key="txt_custom_task")

            st.markdown("---")
            st.markdown("##### 🎚️ 音声仕様・修正規定")
            audio_spec = st.selectbox(
                "音声レベル（ラウドネス規準）",
                [
                    "平均ラウドネス値 -24.0 LKFS (True Peak -1.0dBTP) 【放送規格 ARIB TR-B32】",
                    "目標ラウドネス値 -14.0 LUFS (True Peak -1.0dBTP) 【YouTube・Web動画 推奨値】",
                    "目標ラウドネス値 -16.0 LUFS (True Peak -1.0dBTP) 【Podcast・音声配信向け目安】",
                    "クライアント様指定基準に準拠",
                    "指定なし（最適なバランスに調整）"
                ],
                index=0
            )

            include_lufs14_note = False
            if "14.0 LUFS" in audio_spec:
                include_lufs14_note = st.checkbox(
                    "音質維持に関する注記を含める（-14 LUFSが困難な場合の案内）",
                    value=True,
                    help="作品の構成や音割れ・ノイズ浮き防止のため、最適な聴きやすさ（-15〜-16 LUFS前後）を優先する旨の案内です。"
                )

            include_raw_audio_note = st.checkbox(
                "素材状態に関する事前注記を含める（ノイズ過多時の再見積もり予防線）",
                value=False,
                help="一般的な収録状態を想定した見積もりであり、ノイズが極端に多い場合は再見積もり相談となる旨の事前注記です。"
            )

            audio_format = st.selectbox(
                "納品フォーマット",
                [
                    "WAV (48kHz / 24bit)",
                    "WAV (48kHz / 16bit)",
                    "WAV",
                    "WAV + MP3 (320kbps)",
                    "ご指定のフォーマット"
                ]
            )

            retake_policy = st.selectbox(
                "修正対応の規定",
                [
                    "2回まで無料対応（当方のミス・見落とし等は無償対応）",
                    "2回まで無料対応（素材差し替え等は追加 3,000円/時間）",
                    "1回まで無料対応（音量バランス等の軽微な微調整）",
                    "要相談（追加調整は 3,000円/時間 にて対応）",
                    "記載しない"
                ],
                index=4
            )

            include_rework_fee_note = st.checkbox(
                "素材差し替え・構成変更に関する追加費用（3,000円/時間）の注記を含める",
                value=False,
                help="クライアント都合の素材差し替えや再収録、構成変更による再作業は追加見積もり（3,000円/時）となる旨の防衛注記です。"
            )

        with st.expander("ℹ️ 料金テーブルの確認（基準レート）"):
            st.markdown("""
            | ジャンル | 5分 (約2h) | 15分 (約3h) | 30分 (約4h) | 60分 (約8h) | 補間レート |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | **番組** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **YouTube・配信** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **ドラマ・自主映画** | 12,000円 | 18,000円 | 24,000円 | 48,000円 | 30分超: 800円/分 |
            
            - **CM（15秒・30秒）**: 通常 3,000円 / お得意様 2,000円（本数計算）
            - **固定単価・レギュラー番組**: 番組ごとに設定した単価 × 本数
            - **その他（作業時間計算）**: 1時間あたり 3,000円
            """)

    # --- 全アイテムの合算計算 ---
    total_price_base = sum(res["price_base"] for res in items_calculation_results)

    # 税計算
    if tax_option == "税込（10%）":
        display_total = int(round(total_price_base * 1.10))
        price_label = f"{display_total:,} 円（税込）"
        tax_detail = f"税抜合計: ¥{total_price_base:,} / 消費税(10%): ¥{int(round(total_price_base * 0.10)):,}"
    elif tax_option == "税抜（+消費税）":
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
        st.subheader("💡 お見積り結果")

        # 合計金額表示カード
        breakdown_html = "<ul style='margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #334155;'>"
        for i, res in enumerate(items_calculation_results):
            breakdown_html += f"<li><strong>{res['detail']}</strong> : {res['price_base']:,} 円</li>"
        breakdown_html += "</ul>"

        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #475569; font-weight: 600;">合計お見積り金額</div>
            <div class="total-price">¥{price_label}</div>
            <div class="tax-note">{tax_detail}</div>
            <div style="margin-top: 0.8rem;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #1E293B; margin-bottom: 0.3rem;">内訳明細:</div>
                {breakdown_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

        client_display = client_name.strip() if client_name.strip() else "〇〇様"
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

        if include_delay_note:
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
            spec_lines.append("※大幅な素材の差し替え、新規ナレーションの追加、構成変更等に伴う再作業は、別途追加作業費（3,000円/時間）のご相談とさせていただきます。")

        raw_audio_note_text = ""
        if include_raw_audio_note:
            raw_audio_note_text = "\n※上記は一般的な収録状態を想定したお見積りとなります。ノイズが極端に多い場合や極度の音割れ・部屋鳴り等の高度な修復を要する場合は、素材確認後に作業工数に応じた再お見積りをご相談させていただく場合がございます。\n"

        spec_block = "■ 納品データの仕様・修正規定\n" + "\n".join(spec_lines)

        # 内訳リストのテキスト生成
        if len(items_calculation_results) == 1:
            detail_items_text = f"（内訳：{items_calculation_results[0]['detail']}）"
            simple_items_summary = f"{items_calculation_results[0]['detail']}"
        else:
            detail_lines = ["【内訳明細】"]
            for i, res in enumerate(items_calculation_results):
                detail_lines.append(f"・{i + 1}. {res['detail']}: {res['price_base']:,} 円")
            detail_items_text = "\n" + "\n".join(detail_lines)
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

        # パターン1: ココナラ・クラウドソーシング特化型
        quote_msg_coconala = f"""{client_display}

いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）のお見積もり・スケジュール案をお送りいたします。

■ お見積り金額
合計： {price_label}
{detail_items_text}
{raw_audio_note_text}
{schedule_block}{spec_block}{coconala_work_part}
上記スケジュールおよび内容で問題ございませんでしたら、いつでも正式にご依頼いただけますと幸いです。
ご不明点やご予算・日程のご相談がございましたら、柔軟に対応いたしますのでお気軽にお申し付けください。
何卒よろしくお願い申し上げます。"""

        # パターン2: シンプル（チャット・即答用）
        simple_sched = f"\n・希望納期: {schedule_delivery_summary.strip()}" if schedule_delivery_summary.strip() else ""
        if schedule_reservation_type == "⚡ 先着順（新規・通常向け）":
            simple_sched_note = "\n※スケジュールは正式ご依頼の先着順で確定となります。"
        elif schedule_reservation_type == "🤝 仮確保中（お得意様・リピーター向け）":
            simple_sched_note = "\n※取り急ぎ上記日程で作業枠を仮確保しております！"
        else:
            simple_sched_note = ""

        quote_msg_simple = f"""{client_display}
お世話になっております！
ご相談いただきました{project_display}音声編集（MA）のお見積もりです。

【お見積り】
・内容: {simple_items_summary}
・合計金額: {price_label}{simple_sched}{simple_sched_note}

仕様や日程のご相談も柔軟に対応可能ですので、ご確認のほどよろしくお願いいたします！"""

        # パターン3: ビジネスメール・詳細版
        quote_msg_detailed = f"""{client_display}

いつも大変お世話になっております。
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
ご検討のほど、何卒よろしくお願い申し上げます。"""

        st.markdown("##### ✉️ コピペ用メッセージ（右上のアイコンでワンクリックコピー）")
        st.caption("枠の右上に表示されるコピーボタン（📋アイコン）を押すと、一瞬でクリップボードにコピーされます。")

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
# タブ2: 評価コメント作成
# ==========================================
with tab2:
    col_eval_input, col_eval_result = st.columns([1, 1], gap="large")

    with col_eval_input:
        st.subheader("⚙️ 案件状況・トーンの設定")

        eval_client_name = st.text_input(
            "クライアント名（任意）",
            placeholder="例: 株式会社〇〇 様",
            key="eval_client"
        )

        eval_project_name = st.text_input(
            "案件名（任意）",
            placeholder="例: YouTube対談動画 MA作業",
            key="eval_project"
        )

        # 1. やり取りの印象
        impression = st.selectbox(
            "やり取りの印象",
            ["とてもスムーズ", "普通", "少し時間がかかった"],
            help="相手の対応スピードややり取りの円滑さに合わせてコメントのトーンを自動調整します。"
        )

        # 2. 次回へのアピール
        appeal_flag = st.checkbox(
            "次回へのアピールを含める",
            value=True,
            help="チェックを入れると「また音声編集でお困りならお声がけください」といった一文を末尾に追加します。"
        )

    # --- 評価コメント生成ロジック ---
    target_name = eval_client_name.strip() if eval_client_name.strip() else "〇〇様"
    target_project = f"「{eval_project_name.strip()}」の" if eval_project_name.strip() else ""

    # アピール文（トーン別）
    appeal_short = " また音声編集でお困りの際は気軽にお声がけください！" if appeal_flag else ""
    appeal_standard = "\n\nまた今後、音声編集（MA）やノイズ処理等でお困りの際や別案件がございましたら、ぜひお気軽にお声がけいただけますと幸いです。" if appeal_flag else ""
    appeal_formal = "\n\nなお、今後とも音声編集（MA）や整音作業等のご相談がございましたら、誠心誠意ご対応させていただきますので、何卒お気軽にお申し付けくださいませ。" if appeal_flag else ""
    appeal_review = " また音声編集でお困りの際はぜひお声がけください！" if appeal_flag else ""

    # 1. シンプル
    if impression == "とてもスムーズ":
        msg_simple = f"""{target_name}
お世話になっております！
{target_project}音声編集（MA）の作業が完了いたしましたので、納品データをお送りいたします。

迅速にご対応いただき大変助かりました！ご確認のほどよろしくお願いいたします。{appeal_short}"""

        msg_standard = f"""{target_name}

いつも大変お世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました！

ご指示や素材のご手配が非常に的確で、メッセージのレスポンスも迅速にしていただいたおかげで、終始大変スムーズに作業を進行することができました。心より感謝申し上げます。

納品データについて気になる点や微調整などがございましたら、いつでもお気軽にご連絡ください。{appeal_standard}

今後ともどうぞよろしくお願いいたします。"""

        msg_formal = f"""{target_name}

いつも大変お世話になっております。
この度は、{target_project}音声編集（MA）業務のご依頼を賜り、誠にありがとうございました。

ご指示や素材のご手配を迅速にいただき、円滑に作業を進行することができましたこと、深く感謝申し上げます。
納品データを添付いたしましたので、ご査収のほどよろしくお願い申し上げます。
修正や追加のご要望がございましたら、迅速に対応いたしますので何なりとお申し付けください。{appeal_formal}

今後とも何卒よろしくお願い申し上げます。"""

        msg_review = f"迅速かつ丁寧なご対応をいただき、終始安心してスムーズにお取引を進めることができました。素晴らしいご縁に心より感謝申し上げます。{appeal_review}今後ともよろしくお願いいたします。"

    elif impression == "普通":
        msg_simple = f"""{target_name}
お世話になっております。
{target_project}音声編集（MA）の作業が完了いたしましたので、納品データをお送りいたします。

ご確認のほどよろしくお願いいたします。何か気になる点がございましたらお知らせください。{appeal_short}"""

        msg_standard = f"""{target_name}

いつも大変お世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

ご丁寧にご対応いただき、無事に納品完了まで進めることができました。
今回の仕上がりが今後の制作のお役に立てておりましたら幸いです。

納品データのご確認で何かございましたら、お申し付けください。{appeal_standard}

また機会がございましたら、どうぞよろしくお願い申し上げます。"""

        msg_formal = f"""{target_name}

いつも大変お世話になっております。
この度は、{target_project}音声編集（MA）業務のご依頼を賜り、心より御礼申し上げます。

ご丁寧なご連携をいただき、無事に納品工程を完了することができました。
仕上がりデータをご確認いただき、不都合な点などがございましたらご連絡いただけますと幸いです。{appeal_formal}

今後ともご愛顧のほど、よろしくお願い申し上げます。"""

        msg_review = f"終始丁寧にご対応いただき、無事にお取引を完了することができました。ご依頼いただき誠にありがとうございました。{appeal_review}"

    else:  # 少し時間がかかった
        msg_simple = f"""{target_name}
お世話になっております。
{target_project}音声編集（MA）の納品データをお送りいたします。

ご調整いただきありがとうございました。ご確認のほどよろしくお願いいたします。{appeal_short}"""

        msg_standard = f"""{target_name}

いつもお世話になっております。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

追加のご調整やご確認などを経て、無事に納品完了まで進めることができ安心いたしました。最後まで丁寧にお付き合いいただき、誠にありがとうございました。

今回の音声データがお役に立ちましたら幸いでございます。{appeal_standard}

またの機会がございましたら、よろしくお願い申し上げます。"""

        msg_formal = f"""{target_name}

拝啓
貴社におかれましては、ますますご清栄のこととお慶び申し上げます。
この度は{target_project}音声編集（MA）のご依頼をいただき、誠にありがとうございました。

仕様の確認および追加調整にお時間を頂戴いたしましたが、無事に納品データを仕上げることができ安心いたしました。最後まで丁寧にお付き合いいただき厚く御礼申し上げます。
添付データのご確認をよろしくお願い申し上げます。{appeal_formal}

またの機会がございましたら、何卒よろしくお願い申し上げます。
敬具"""

        msg_review = f"ご丁寧にご対応いただき、無事にお取引を完了することができました。最後までお付き合いいただきありがとうございました。{appeal_review}"

    # --- 右カラム: 生成結果 ---
    with col_eval_result:
        st.subheader("📝 生成メッセージ（選べる4パターン）")
        st.caption("枠の右上に表示されるコピーボタン（📋アイコン）を押すと、一瞬でコピーできます。")

        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "⚡ シンプル（短文チャット）",
            "📝 標準（丁寧・親しみ）",
            "👔 フォーマル（しっかり）",
            "⭐ 評価欄用（レビュー短文）"
        ])

        with subtab1:
            st.markdown("##### ⚡ シンプル版（要点のみ・短文）")
            st.code(msg_simple, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_simple, height=160, key="edit_ev_simple")

        with subtab2:
            st.markdown("##### 📝 標準版（バランス・親しみやすい丁寧さ）")
            st.code(msg_standard, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_standard, height=250, key="edit_ev_std")

        with subtab3:
            st.markdown("##### 👔 フォーマル版（ビジネス・企業向け）")
            st.code(msg_formal, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_formal, height=280, key="edit_ev_formal")

        with subtab4:
            st.markdown("##### ⭐ プラットフォーム評価欄用（レビュー短文）")
            st.code(msg_review, language="markdown")
            with st.expander("✏️ テキストを直接編集したい場合"):
                st.text_area("編集用", value=msg_review, height=120, key="edit_ev_review")
