import datetime
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
def calc_duration_price(minutes: float, is_drama: bool = False) -> tuple[int, str]:
    """
    YouTube・配信 / 番組 / ドラマ・自主映画 の補間計算を行う関数
    YouTube・番組基準:
      5分 = 6,000円
      15分 = 9,000円  (傾き 300円/分)
      30分 = 12,000円 (傾き 200円/分)
      60分 = 24,000円 (傾き 400円/分)
      60分超 = 400円/分で外挿
    ドラマ・自主映画は上記の2倍
    """
    factor = 2 if is_drama else 1

    # ミニマムチャージ（5分以内）
    if minutes <= 5:
        base_price = 6000 * factor
        formula_detail = f"基本料金（5分以内）: {base_price:,}円"
        return base_price, formula_detail

    # 5分超〜15分以内
    if minutes <= 15:
        rate = 300 * factor
        base = 6000 * factor
        diff = minutes - 5
        price = base + diff * rate
        formula_detail = f"5分基準({base:,}円) + 追加{diff:.1f}分 × {rate:,}円/分 = {int(round(price)):,}円"
        return int(round(price)), formula_detail

    # 15分超〜30分以内
    if minutes <= 30:
        rate = 200 * factor
        base = 9000 * factor
        diff = minutes - 15
        price = base + diff * rate
        formula_detail = f"15分基準({base:,}円) + 追加{diff:.1f}分 × {rate:,}円/分 = {int(round(price)):,}円"
        return int(round(price)), formula_detail

    # 30分超〜60分以内
    if minutes <= 60:
        rate = 400 * factor
        base = 12000 * factor
        diff = minutes - 30
        price = base + diff * rate
        formula_detail = f"30分基準({base:,}円) + 追加{diff:.1f}分 × {rate:,}円/分 = {int(round(price)):,}円"
        return int(round(price)), formula_detail

    # 60分超（補間・外挿）
    rate = 400 * factor
    base = 24000 * factor
    diff = minutes - 60
    price = base + diff * rate
    formula_detail = f"60分基準({base:,}円) + 超過{diff:.1f}分 × {rate:,}円/分 = {int(round(price)):,}円"
    return int(round(price)), formula_detail


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
        project_title = st.text_input("案件名・動画タイトル（任意）", placeholder="例: YouTube対談企画 MA作業")

        # 1. 案件ジャンル（「YouTube・配信」と「番組」を分割）
        genres = [
            "YouTube・配信",
            "番組",
            "ドラマ・自主映画",
            "CM（15秒・30秒）",
            "中島知子のおんせんさんぽ",
            "その他（作業時間計算）"
        ]
        selected_genre = st.selectbox("案件のジャンル", genres)

        duration_val = 0.0
        cm_pattern = "通常"
        cm_count = 1
        onsen_count = 1
        work_hours = 1.0

        # 条件付き入力項目
        if selected_genre in ["YouTube・配信", "番組", "ドラマ・自主映画"]:
            duration_val = st.number_input(
                "尺の入力（分単位）",
                min_value=1.0,
                max_value=300.0,
                value=15.0,
                step=1.0,
                help="※5分未満は基本料金（5分基準）となります。60分超は補間（外挿）計算されます。"
            )

        elif selected_genre == "CM（15秒・30秒）":
            cm_pattern = st.radio(
                "CMの取引先パターン",
                ["通常", "お得意様"],
                horizontal=True,
                help="通常: 3,000円 / 本、お得意様: 2,000円 / 本"
            )
            cm_count = st.number_input("制作本数", min_value=1, max_value=100, value=1, step=1)

        elif selected_genre == "中島知子のおんせんさんぽ":
            st.info("💡 1本固定 3,000円 です。")
            onsen_count = st.number_input("本数", min_value=1, max_value=100, value=1, step=1)

        elif selected_genre == "その他（作業時間計算）":
            work_hours = st.number_input(
                "作業時間（時間単位）",
                min_value=0.5,
                max_value=200.0,
                value=2.0,
                step=0.5,
                help="1時間あたり 3,000円 で計算します。"
            )

        # 税金・表記オプション
        tax_option = st.radio("消費税の表示", ["税込（10%）", "税抜（+消費税）", "税込（内税表記）"], horizontal=True)

        st.markdown("---")
        st.subheader("📅 制作スケジュール（案）の設定")

        # 入力モード選択
        schedule_mode = st.radio(
            "スケジュールの入力方法",
            ["📅 カレンダーから選ぶ（おすすめ）", "✏️ 自由に入力する（複数本・特殊な指定）"],
            horizontal=True
        )

        today = datetime.date.today()
        schedule_delivery_text = ""
        schedule_handover_text = ""
        schedule_work_text = ""

        if schedule_mode == "📅 カレンダーから選ぶ（おすすめ）":
            # 1. 希望納期
            col_d1, col_d2 = st.columns([3, 2])
            with col_d1:
                date_delivery = st.date_input("ご希望納期の日付", value=today + datetime.timedelta(days=3))
            with col_d2:
                time_delivery = st.selectbox(
                    "納期の時間帯",
                    ["中（終日）", "夕方まで", "午前中", "23:59まで", "18:00まで", "要相談"],
                    key="time_del"
                )
            schedule_delivery_text = f"{format_date_jp(date_delivery)} {time_delivery}"

            # 2. データご搬入
            col_h1, col_h2 = st.columns([3, 2])
            with col_h1:
                date_handover = st.date_input("データご搬入の日付", value=today + datetime.timedelta(days=1))
            with col_h2:
                time_handover = st.text_input("搬入の時間帯・詳細", value="21:30ごろ", placeholder="例: 21:30ごろ、夜、午前中")
            schedule_handover_text = f"{format_date_jp(date_handover)} {time_handover}".strip()

            # 3. 作業予定日
            col_w1, col_w2 = st.columns([3, 2])
            with col_w1:
                date_work = st.date_input("作業予定日の日付", value=today + datetime.timedelta(days=1))
            with col_w2:
                time_work = st.selectbox(
                    "作業予定の時間帯",
                    ["夜", "夕方以降", "終日", "午前中", "午後", "深夜"],
                    key="time_work"
                )
            schedule_work_text = f"{format_date_jp(date_work)} {time_work}"

            # 除外チェックボックス
            col_chk1, col_chk2, col_chk3 = st.columns(3)
            with col_chk1:
                use_delivery = st.checkbox("納期を含める", value=True)
            with col_chk2:
                use_handover = st.checkbox("搬入日を含める", value=True)
            with col_chk3:
                use_work = st.checkbox("作業日を含める", value=True)

            if not use_delivery:
                schedule_delivery_text = ""
            if not use_handover:
                schedule_handover_text = ""
            if not use_work:
                schedule_work_text = ""

        else:
            # 自由入力モード
            schedule_delivery_text = st.text_input(
                "ご希望納期",
                value="1本目：11/3（火）中、2本目：11/10（火）まで",
                placeholder="例: 1本目：11/3（火）中、2本目：11/10（火）まで"
            )
            schedule_handover_text = st.text_input(
                "データご搬入",
                value="本編：未定、ナレ：11/2（月）21:30ごろ",
                placeholder="例: 本編：未定、ナレ：11/2（月）21:30ごろ"
            )
            schedule_work_text = st.text_input(
                "作業予定日",
                value="11/2（月）夜、11/4 夕方以降",
                placeholder="例: 11/2（月）夜、11/4 夕方以降"
            )

        # スケジュールに関する注記設定
        st.markdown("**スケジュールに関する注記（トラブル防止・早期確定の促進）**")
        col_note1, col_note2 = st.columns(2)
        with col_note1:
            include_first_come_note = st.checkbox(
                "作業枠の仮押さえ不可・先着順の注記を含める",
                value=True,
                help="「作業予定日は現時点の目安となり、正式ご購入の先着順で確定します」という案内です。"
            )
        with col_note2:
            include_delay_note = st.checkbox(
                "搬入遅延に関する注記を含める",
                value=True,
                help="データ搬入が遅れた場合に納期が後ろ倒しになる可能性の注記です。"
            )

        # 納品仕様・音声レベル設定
        st.markdown("---")
        with st.expander("🎚️ 納品仕様・音声レベル設定（ココナラ・プロ向け仕様）", expanded=True):
            # ジャンルに応じたデフォルトインデックスの選定
            default_spec_idx = 1 if selected_genre == "YouTube・配信" else 0

            audio_spec = st.selectbox(
                "音声レベル（ラウドネス規準）",
                [
                    "平均ラウドネス値 -24.0 LKFS (True Peak -1.0dBTP) 【放送規格 ARIB TR-B32】",
                    "目標ラウドネス値 -14.0 LUFS (True Peak -1.0dBTP) 【YouTube・Web動画 推奨値】",
                    "目標ラウドネス値 -16.0 LUFS (True Peak -1.0dBTP) 【Podcast・音声配信向け目安】",
                    "クライアント様指定基準に準拠",
                    "指定なし（最適なバランスに調整）"
                ],
                index=default_spec_idx
            )

            # -14 LUFS 選択時（またはYouTube選択時）の注釈オプション
            include_lufs14_note = False
            if "14.0 LUFS" in audio_spec:
                include_lufs14_note = st.checkbox(
                    "音質維持に関する注記を含める（-14 LUFSが困難な場合の案内）",
                    value=True,
                    help="作品の構成や音割れ・ノイズ浮き防止のため、最適な聴きやすさ（-15〜-16 LUFS前後）を優先する旨の案内です。"
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
                "無料修正対応",
                ["2回まで無料対応（※こちらの不備・整音ミスは無制限）", "1回まで無料対応", "ご納得いただけるまで対応", "記載しない"]
            )

        with st.expander("ℹ️ 料金テーブルの確認（基準レート）"):
            st.markdown("""
            | ジャンル | 5分 | 15分 | 30分 | 60分 | 補間レート |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | **YouTube・配信** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **番組** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **ドラマ・自主映画** | 12,000円 | 18,000円 | 24,000円 | 48,000円 | 30分超: 800円/分 |
            
            - **CM（15秒・30秒）**: 通常 3,000円 / お得意様 2,000円（本数計算）
            - **中島知子のおんせんさんぽ**: 1本固定 3,000円
            - **その他（作業時間計算）**: 1時間あたり 3,000円
            """)

    # --- 計算処理 ---
    price_base = 0
    detail_text = ""
    breakdown_text = ""

    if selected_genre in ["YouTube・配信", "番組"]:
        price_base, breakdown_text = calc_duration_price(duration_val, is_drama=False)
        detail_text = f"{duration_val:.1f}分"
    elif selected_genre == "ドラマ・自主映画":
        price_base, breakdown_text = calc_duration_price(duration_val, is_drama=True)
        detail_text = f"{duration_val:.1f}分"
    elif selected_genre == "CM（15秒・30秒）":
        unit_price = 2000 if cm_pattern == "お得意様" else 3000
        price_base = unit_price * cm_count
        detail_text = f"{cm_pattern}パターン（{unit_price:,}円/本）× {cm_count}本"
        breakdown_text = f"単価 {unit_price:,}円 × {cm_count}本 = {price_base:,}円"
    elif selected_genre == "中島知子のおんせんさんぽ":
        unit_price = 3000
        price_base = unit_price * onsen_count
        detail_text = f"固定（3,000円/本）× {onsen_count}本"
        breakdown_text = f"3,000円 × {onsen_count}本 = {price_base:,}円"
    elif selected_genre == "その他（作業時間計算）":
        price_base = int(round(work_hours * 3000))
        detail_text = f"{work_hours:.1f} 時間（3,000円/時間）"
        breakdown_text = f"3,000円 × {work_hours:.1f}時間 = {price_base:,}円"

    # 税計算
    if tax_option == "税込（10%）":
        display_total = int(round(price_base * 1.10))
        price_label = f"{display_total:,} 円（税込）"
        tax_detail = f"税抜: ¥{price_base:,} / 消費税(10%): ¥{int(round(price_base * 0.10)):,}"
    elif tax_option == "税抜（+消費税）":
        display_total = price_base
        tax_amount = int(round(price_base * 0.10))
        price_label = f"{display_total:,} 円（税抜 / 税込 {display_total + tax_amount:,} 円）"
        tax_detail = f"消費税(10%): ¥{tax_amount:,}"
    else:  # 税込（内税表記）
        display_total = price_base
        price_label = f"{display_total:,} 円（税込）"
        tax_detail = f"※上記金額には消費税が含まれております。"

    # --- 右カラム: 計算結果 & メッセージ生成 ---
    with col_result:
        st.subheader("💡 お見積り結果")

        # 合計金額表示カード
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #475569; font-weight: 600;">合計お見積り金額</div>
            <div class="total-price">¥{price_label}</div>
            <div class="tax-note">{tax_detail}</div>
            <div style="margin-top: 0.8rem; font-size: 0.85rem; color: #334155;">
                <strong>内訳:</strong> {breakdown_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 宛名・案件名
        client_display = client_name.strip() if client_name.strip() else "〇〇様"
        project_display = f"「{project_title.strip()}」" if project_title.strip() else ""

        # スケジュールブロック作成
        schedule_lines = []
        if schedule_delivery_text.strip():
            schedule_lines.append(f"・ご希望納期： {schedule_delivery_text.strip()}")
        if schedule_handover_text.strip():
            schedule_lines.append(f"・データご搬入： {schedule_handover_text.strip()}")
        if schedule_work_text.strip():
            schedule_lines.append(f"・作業予定日： {schedule_work_text.strip()}")

        # スケジュール注記
        schedule_notes = []
        if include_first_come_note:
            schedule_notes.append("※作業予定日は現時点の空き状況に基づく目安となります。スケジュールの仮押さえは行っておりませんので、正式なご依頼（ご購入）の先着順にて確定とさせていただきます。万が一他案件で枠が埋まってしまった場合は、日程の再調整（またはご辞退）をご相談させていただく場合がございます。")
        if include_delay_note:
            schedule_notes.append("※データご搬入が予定より遅れた場合、納期が後ろ倒しになる可能性がございます。")

        if schedule_notes and schedule_lines:
            schedule_lines.extend(schedule_notes)

        schedule_block = ""
        if schedule_lines:
            schedule_block = "■ 制作スケジュール（案）\n" + "\n".join(schedule_lines) + "\n\n"

        # 仕様ブロック作成
        spec_lines = [
            f"・フォーマット： {audio_format}",
            f"・音声レベル： {audio_spec}"
        ]
        if include_lufs14_note:
            spec_lines.append("※作品全体のダイナミクス（音の強弱）や静寂の多い構成の場合、過度な音割れやノイズ浮きを防ぎ、聴きやすさを最優先して -15〜-16 LUFS 前後で着地・調整させていただく場合がございます。")
        if retake_policy != "記載しない":
            spec_lines.append(f"・修正対応： {retake_policy}")
        spec_block = "■ 納品データの仕様・音声レベル\n" + "\n".join(spec_lines)

        # パターン1: ココナラ・クラウドソーシング特化型
        quote_msg_coconala = f"""{client_display}

いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）のお見積もり・スケジュール案をお送りいたします。

■ お見積り金額
合計： {price_label}
（内訳：{selected_genre} {detail_text}）

{schedule_block}{spec_block}

■ 主な作業内容
・ノイズ除去（リップノイズ・部屋鳴り・環境音の低減）
・音量・音圧バランス調整（ラウドネス規準準拠）
・BGM・効果音（SE）のMA処理・整音ミックス
・マスタリングおよび指定フォーマットでの書き出し

上記スケジュールおよび内容で問題ございませんでしたら、いつでも正式にご依頼いただけますと幸いです。
ご不明点やご予算・日程のご相談がございましたら、柔軟に対応いたしますのでお気軽にお申し付けください。
何卒よろしくお願い申し上げます。"""

        # パターン2: シンプル（チャット・即答用）
        simple_sched = f"\n・希望納期: {schedule_delivery_text.strip()}" if schedule_delivery_text.strip() else ""
        quote_msg_simple = f"""{client_display}
お世話になっております！
ご相談いただきました{project_display}音声編集（MA）のお見積もりです。

【お見積り】
・ジャンル: {selected_genre}（{detail_text}）
・お見積金額: {price_label}{simple_sched}

※スケジュールは正式ご依頼の先着順で確定となります。
仕様や日程のご相談も柔軟に対応可能ですので、ご確認のほどよろしくお願いいたします！"""

        # パターン3: ビジネスメール・詳細版
        quote_msg_detailed = f"""{client_display}

いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）につきまして、お見積もりと制作進行案をご案内申し上げます。

━━━━━━━━━━━━━━━━━━━━━━━━━━
【お見積もり内容】
・案件ジャンル : {selected_genre}
・詳細 / 尺   : {detail_text}
・お見積り金額 : {price_label}
━━━━━━━━━━━━━━━━━━━━━━━━━━

{schedule_block}{spec_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━
【作業工程・内容】
1. 音声素材のノイズ低減（リップノイズ・空調音・ヒスノイズ除去）
2. 話者ごとの音量・声質バランスの調整（EQ・コンプレッサー処理）
3. BGM・SE（効果音）の配置および適切なダッキング処理
4. 規定ラウドネス値に合わせた最終マスタリング

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
