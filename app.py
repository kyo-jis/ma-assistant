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

# カスタムCSS（シンプルで見やすいデザイン）
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
        margin-bottom: 1.5rem;
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
</style>
""", unsafe_allow_html=True)


# ==========================================
# 計算ロジック
# ==========================================
def calc_duration_price(minutes: float, is_drama: bool = False) -> tuple[int, str]:
    """
    YouTube・番組 / ドラマ・自主映画 の補間計算を行う関数
    YouTube基準:
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
tab1, tab2 = st.tabs(["💰 見積もり作成", "💬 評価コメント作成"])


# ==========================================
# タブ1: 見積もり作成
# ==========================================
with tab1:
    col_input, col_result = st.columns([1, 1], gap="large")

    with col_input:
        st.subheader("📋 案件情報の入力")

        # 任意入力：宛名・案件名
        client_name = st.text_input("クライアント名（任意）", placeholder="例: 株式会社〇〇 ご担当者 様")
        project_title = st.text_input("案件名・動画タイトル（任意）", placeholder="例: YouTubeチャンネル 音声MA案件")

        # 1. 案件ジャンル
        genres = [
            "YouTube・番組",
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
        if selected_genre in ["YouTube・番組", "ドラマ・自主映画"]:
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

        with st.expander("ℹ️ 料金テーブルの確認（基準レート）"):
            st.markdown("""
            | ジャンル | 5分 | 15分 | 30分 | 60分 | 補間レート |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | **YouTube・番組** | 6,000円 | 9,000円 | 12,000円 | 24,000円 | 30分超: 400円/分 |
            | **ドラマ・自主映画** | 12,000円 | 18,000円 | 24,000円 | 48,000円 | 30分超: 800円/分 |
            
            - **CM（15秒・30秒）**: 通常 3,000円 / お得意様 2,000円（本数計算）
            - **中島知子のおんせんさんぽ**: 1本固定 3,000円
            - **その他（作業時間計算）**: 1時間あたり 3,000円
            """)

    # --- 計算処理 ---
    price_base = 0
    detail_text = ""
    breakdown_text = ""

    if selected_genre == "YouTube・番組":
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
        price_label = f"¥{display_total:,}（税込）"
        tax_detail = f"税抜: ¥{price_base:,} / 消費税(10%): ¥{int(round(price_base * 0.10)):,}"
    elif tax_option == "税抜（+消費税）":
        display_total = price_base
        tax_amount = int(round(price_base * 0.10))
        price_label = f"¥{display_total:,}（税抜 / 税込 ¥{display_total + tax_amount:,}）"
        tax_detail = f"消費税(10%): ¥{tax_amount:,}"
    else:  # 税込（内税表記）
        display_total = price_base
        price_label = f"¥{display_total:,}（税込）"
        tax_detail = f"※上記金額には消費税が含まれております。"

    # --- 右カラム: 計算結果 & メッセージ生成 ---
    with col_result:
        st.subheader("💡 お見積り結果")

        # 合計金額表示カード
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #475569; font-weight: 600;">合計お見積り金額</div>
            <div class="total-price">{price_label}</div>
            <div class="tax-note">{tax_detail}</div>
            <div style="margin-top: 0.8rem; font-size: 0.85rem; color: #334155;">
                <strong>内訳:</strong> {breakdown_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 宛名・案件名のプレースホルダー処理
        client_display = client_name.strip() if client_name.strip() else "〇〇様"
        project_display = f"「{project_title.strip()}」" if project_title.strip() else ""

        # 見積もりメッセージの複数パターン生成
        quote_msg_simple = f"""{client_display}
お世話になっております。
ご相談いただきました{project_display}音声編集（MA）のお見積もりです。

【お見積り】
・案件ジャンル : {selected_genre}（{detail_text}）
・お見積り金額 : {price_label}

ご確認のほどよろしくお願いいたします！"""

        quote_msg_detailed = f"""{client_display}

いつも大変お世話になっております。
ご相談いただきました{project_display}音声編集（MA）のお見積もりをお送りいたします。

━━━━━━━━━━━━━━━━━━━━━━━━━━
【お見積もり内容】
・案件ジャンル : {selected_genre}
・詳細 / 尺   : {detail_text}
・お見積り金額 : {price_label}
━━━━━━━━━━━━━━━━━━━━━━━━━━

【主な作業内容（想定）】
・ノイズ除去（リップノイズ・環境音・ヒスノイズ低減）
・音量・音圧バランス調整（ラウドネス規準準拠）
・BGM / 効果音（SE）のMA処理・ミックス
・最終マスタリングおよび指定フォーマットでの書き出し

ご不明な点やスケジュール、ご予算のご相談がございましたら、柔軟に対応させていただきますので、いつでもお気軽にお申し付けください。
何卒ご検討のほど、よろしくお願い申し上げます。"""

        st.markdown("##### ✉️ コピペ用お見積りメッセージ")
        st.caption("用途に合わせてタブを切り替えてそのままコピーできます。")

        q_tab1, q_tab2 = st.tabs(["⚡ シンプル版（チャット用）", "📋 詳細版（メール・正式用）"])
        with q_tab1:
            st.text_area("シンプルお見積り", value=quote_msg_simple, height=180, key="q_simple")
        with q_tab2:
            st.text_area("詳細お見積り", value=quote_msg_detailed, height=310, key="q_detailed")


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

    # 1. シンプル（短文・サクッとチャットで送りたい時）
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
        st.caption("場面や相手との関係性に合わせて、タブを切り替えてそのままコピペできます。")

        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "⚡ シンプル（短文チャット）",
            "📝 標準（丁寧・親しみ）",
            "👔 フォーマル（しっかり）",
            "⭐ 評価欄用（レビュー短文）"
        ])

        with subtab1:
            st.markdown("##### ⚡ シンプル版（要点のみ・短文）")
            st.caption("Slack、Chatwork、チャットツールでサクッと納品連絡したい時に最適です。")
            st.text_area("シンプル納品メッセージ", value=msg_simple, height=180, key="msg_simple_area")

        with subtab2:
            st.markdown("##### 📝 標準版（バランス・親しみやすい丁寧さ）")
            st.caption("一般的なクラウドソーシングや取引メッセージで最も使いやすいトーンです。")
            st.text_area("標準納品メッセージ", value=msg_standard, height=270, key="msg_std_area")

        with subtab3:
            st.markdown("##### 👔 フォーマル版（ビジネス・企業向け）")
            st.caption("企業案件やメール連絡、かしこまったやり取りの際に活用できます。")
            st.text_area("フォーマル納品メッセージ", value=msg_formal, height=290, key="msg_formal_area")

        with subtab4:
            st.markdown("##### ⭐ プラットフォーム評価欄用（レビュー短文）")
            st.caption("クラウドワークスやランサーズ等の取引完了時のレビュー欄にコピペできます。")
            st.text_area("評価コメント本文", value=msg_review, height=140, key="msg_review_area")
