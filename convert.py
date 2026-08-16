#!/usr/bin/env python3
"""Interview Prep Guide: Markdown → モバイル最適化HTML変換スクリプト."""

import html as html_mod
import re
from pathlib import Path

from jinja2 import Template
from markdown_it import MarkdownIt

# --- 設定 ---

SOURCE_DIR = Path(__file__).parent / "source"
OUTPUT_DIR = Path(__file__).parent / "docs"

# 既存章の手動定義（タイトル・アイコン・説明をカスタマイズしたい場合に記載）
# ここに書かれていないファイルは source/ を自動スキャンして追加される
CHAPTER_MAP = {
    "00_プロジェクト一覧.md": {"slug": "00-overview", "title": "プロジェクト一覧", "icon": "📋", "desc": "1年間の成果物と定量データ"},
    "01_NexusCore.md": {"slug": "01-nexuscore", "title": "NexusCore", "icon": "🤖", "desc": "マルチエージェントAI開発フレームワーク"},
    "02_atelier-kyo-manager.md": {"slug": "02-atelier", "title": "atelier-kyo-manager", "icon": "🛒", "desc": "BUYMA転売管理システム"},
    "03_reserve-optimizer.md": {"slug": "03-reserve", "title": "reserve-optimizer", "icon": "📅", "desc": "LINE予約システム"},
    "04_OpenClaw.md": {"slug": "04-openclaw", "title": "OpenClaw", "icon": "🦉", "desc": "AIエージェント24h運用インフラ"},
    "05_数字で語る.md": {"slug": "05-numbers", "title": "数字で語る", "icon": "📊", "desc": "定量指標の正しい伝え方"},
    "06_想定質問.md": {"slug": "06-qa", "title": "想定質問", "icon": "💬", "desc": "面接で聞かれやすいQ&A"},
    "07_なぜAI駆動開発なのか.md": {"slug": "07-why-ai-driven", "title": "なぜAI駆動開発なのか", "icon": "🧠", "desc": "選択としてのAI駆動開発——理由と根拠"},
    "08_コードを読む力.md": {"slug": "08-code-reading", "title": "コードを理解する力", "icon": "📖", "desc": "AIに説明させて理解し品質を担保するプロセス"},
    "09_実践コード読解.md": {"slug": "09-practice-reading", "title": "実践コード読解", "icon": "🔍", "desc": "NexusCoreのリアルコミットを読む練習5問"},
    "10_自己紹介.md": {"slug": "10-self-introduction", "title": "自己紹介", "icon": "🎤", "desc": "面接冒頭「自己紹介お願いします」用スクリプト（30秒/1分/2分）"},
    "11_ワークフロー自動化.md": {"slug": "11-workflow-automation", "title": "ワークフロー自動化", "icon": "⚙️", "desc": "Zennパイプライン・RPA・OAuth1.0a署名の自前構築事例"},
    "12_ADiXi技術用語解説.md": {"slug": "12-adixi-glossary", "title": "ADiXi技術用語解説", "icon": "🔬", "desc": "CEOスカウトメールの専門用語（AX/RAG/MLOps等）を読み解く"},
    "13_自己紹介_ADiXi特化版.md": {"slug": "13-self-introduction-adixi", "title": "自己紹介（ADiXi特化版）", "icon": "🎯", "desc": "ビジョン共感を軸にした語り方"},
    "14_自己紹介_特性重視版.md": {"slug": "14-self-introduction-personality", "title": "自己紹介（特性重視版）", "icon": "🌱", "desc": "数字でなく人柄・継続力・探求心で語る版"},
}


# --- 自動スキャン ---

def _filename_to_slug(filename: str) -> str:
    """ファイル名からslugを生成: '13_glm-rate-proxy.md' → '13-glm-rate-proxy'"""
    stem = Path(filename).stem  # 拡張子除去
    # 先頭の数字+区切り文字を抽出: "13_foo" → "13-foo", "00_早見表" → "00-cheatsheet相当"
    # アンダースコアをハイフンに、日本語はASCIIに変換できないのでそのまま残す
    slug = stem.replace("_", "-", 1)  # 最初の _ のみハイフン化
    # 残りの _ もハイフン化
    slug = slug.replace("_", "-")
    # ASCII以外の文字を除去してslugを作る
    ascii_slug = ""
    for ch in slug:
        if ch.isascii():
            ascii_slug += ch.lower()
        elif ch == "-":
            ascii_slug += "-"
    # 連続ハイフン・末尾ハイフンを整理
    ascii_slug = re.sub(r"-+", "-", ascii_slug).strip("-")
    return ascii_slug or slug


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    """YAMLフロントマターを抽出。なければ空dictとテキストをそのまま返す。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def _extract_title_from_h1(text: str) -> str:
    """H1ヘッダーからタイトルを抽出。'# 13 GLM Rate Proxy — ...' → 'GLM Rate Proxy'"""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            # 番号プレフィックスを除去: "13 GLM Rate Proxy" → "GLM Rate Proxy"
            title = re.sub(r"^\d+\s+", "", title)
            # ダッシュ以降の説明を除去: "GLM Rate Proxy — 説明" → "GLM Rate Proxy"
            title = re.split(r"\s+[—–-]\s+", title)[0].strip()
            return title
    return ""


def _extract_desc_from_h1(text: str) -> str:
    """H1ヘッダーのダッシュ以降を説明として抽出。"""
    for line in text.splitlines():
        if line.startswith("# "):
            parts = re.split(r"\s+[—–-]\s+", line[2:].strip(), maxsplit=1)
            if len(parts) > 1:
                return parts[1].strip()
    return ""


def build_chapter_map() -> dict:
    """source/ をスキャンして完全なCHAPTER_MAPを構築。
    CHAPTER_MAPに未登録のファイルは自動検出して追加する。"""
    result = dict(CHAPTER_MAP)

    for md_file in sorted(SOURCE_DIR.glob("*.md")):
        filename = md_file.name
        if filename.startswith("_"):
            continue  # _README.md等は除外
        if filename in result:
            continue  # 既登録はスキップ

        text = md_file.read_text(encoding="utf-8")
        meta, body = _extract_frontmatter(text)

        title = meta.get("title") or _extract_title_from_h1(text) or Path(filename).stem
        desc = meta.get("card_desc") or meta.get("desc") or _extract_desc_from_h1(text) or title
        icon = meta.get("icon", "📄")
        slug = meta.get("slug") or _filename_to_slug(filename)

        result[filename] = {"slug": slug, "title": title, "icon": icon, "desc": desc}
        print(f"AUTO: {filename} → {slug} ({title})")

    return result

REMOVE_SECTIONS = [
    "## 関連",
    "## 関連ドキュメント",
    "## 次の章",
    "## あなたの現在のフック構成",
    "## あなたの環境のメモリ構成",
    "## あなたの設定ファイル一覧",
    "## あなたのLLMルーティング",
    "## あなたの環境での使い方",
    "## あなたの環境の特記事項",
    "## あなたのMCPサーバー構成",
    "## あなたのフック一覧",
]

REMOVE_PATTERNS = [
    "あなたの",
]

INLINE_REPLACEMENTS = [
    # 個人ルーティング情報 → 汎用化
    (r"GLM-5\.1にルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-4\.7にルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-4\.5-Airにルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-5\.1がデフォルト", "デフォルトモデルが自動選択"),
    (r"あなたの環境:\s*GLM-5\.1\s*→\s*MiniMax\s*→\s*Sonnet", "モデルは /model コマンドで切替可能"),
    (r"あなたの環境ではGLM-5\.1にルーティング", "API経由で利用可能"),
    (r"あなたの環境ではGLM-4\.7にルーティング", "API経由で利用可能"),
    (r"GLM-4\.5-Air に切替", "Haiku に切替"),
    (r"GLM-4\.7 に戻す", "Sonnet に戻す"),
    (r"通常タスク → 🟡 GLM-5\.1（glm_ask経由）", "通常タスク → Opus または Sonnet"),
    (r"フォールバック → 🟠 MiniMax（minimax_ask経由）", "フォールバック → Haiku"),
    (r"大量処理委譲 → 🟠 MiniMax（自動委譲）", "大量処理 → Haiku等の軽量モデル"),
    # 内部パス参照 → 除去
    (r"→ `00_SYSTEM/共通ルール/LLMルーティング\.md`", ""),
    (r"→ `00_SYSTEM/MCPツール使い分けガイド\.md`", ""),
    (r"あなたのobsidian-ssotリポジトリがこれに該当。", "単一リポジトリで一元管理する構成がこれに該当。"),
    (r"あなたのグローバルCLAUDE\.mdに含まれるもの:", "グローバルCLAUDE.mdに含まれるもの:"),
    (r"あなたの現在のメイン環境（WSL2）", "Linuxターミナル環境"),
    (r"LLMルーティング（GLM → MiniMax → Sonnet）", "モデルルーティング（上位モデル → バランス型 → 軽量型）"),
    (r"バッジ表示ルール（🟡\[GLM\]等）", "使用モデル表示ルール"),
    (r"GLM-5\.1", "Claude"),
    (r"GLM-4\.7", "Claude"),
    (r"GLM-4\.5-Air", "Claude"),
    (r"LLM（Claude / GLM / MiniMax）", "LLM（Claude）"),
    (r"Claude, GLM, MiniMax等", "Claude等"),
    (r"Opus/Sonnet/Haiku \+ GLM", "Opus / Sonnet / Haiku"),
    # MiniMax の残存（コードブロック・テーブル内）
    (r"MiniMax-M2\.7", "代替軽量モデル"),
    (r"MiniMax", "代替プロバイダー"),
    (r"minimax\.io", "fallback-provider.example"),
    (r"minimax", "フォールバック先"),
    # obsidian-ssot / 00_SYSTEM パス（スキル内コードブロック）
    (r"obsidian-ssot/00_SYSTEM/handoff/", "claude-code/handoff/"),
    (r"obsidian-ssot", "knowledge-base"),
    (r"00_SYSTEM/", "config/"),
    # 「あなたの設定」テーブル列 → 行ごと書き換え
    (r"\| あなたの設定 \|.*?\|", "| 備考 | なし |"),
]

TABLE_COL_SANITIZE = [
    # テーブルヘッダーから「あなたの設定」列を除去するパターン
    (r"\|\s*あなたの設定\s*\|", "| 備考 |"),
    (r"\|\s*`~/.secrets\.env`\s+からAPIキーを注入.*?\|", "| APIキーは環境変数で管理 |"),
    (r"\|\s*`check-command-safety\.py`\s+が危険コマンドを自動ブロック.*?\|", "| 危険コマンドを自動ブロック |"),
    (r"\|\s*MCP設定変更時の使い分けガイド自動更新.*?\|", "| 設定変更を自動検知 |"),
    (r"\|\s*セッション終了時のサマリー記録.*?\|", "| セッション終了時に記録 |"),
    (r"\|\s*Anthropic APIまたは代替プロバイダー経由で利用可能\s*\|", "| API経由で利用可能 |"),
]

MERMAID_DIAGRAMS = {
    "01_基礎概念.md": [
        (
            "## アーキテクチャ",
            """graph TD
    User["👤 ユーザー"] --> CLI["💻 Claude Code CLI"]
    CLI --> SP["📋 システムプロンプト"]
    CLI --> MCP["🔌 MCPツール定義"]
    CLI --> SK["🎯 スキル定義"]
    CLI --> MEM["🧠 メモリ読込"]
    CLI --> LLM["🤖 LLM"]
    LLM --> Tools["🔧 ツール実行"]
    Tools --> Files["📁 ファイル操作"]
    Tools --> Shell["💻 シェル実行"]
    Tools --> API["🌐 API呼出"]
    Tools --> Agent["🤖 サブエージェント"]
    LLM --> Resp["💬 レスポンス"]
    Resp --> User""",
        ),
        (
            "## コンテキストの仕組み",
            """graph LR
    subgraph "200K トークン コンテキストウィンドウ"
        A["システムプロンプト<br/>~3%"]
        B["ツール定義<br/>~20%"]
        C["メモリ・スキル<br/>~4%"]
        D["会話履歴<br/>~3%"]
        E["空き容量<br/>~70%"]
    end""",
        ),
    ],
    "05_フック.md": [
        (
            "## 4種のフック",
            """sequenceDiagram
    participant U as ユーザー
    participant CC as Claude Code
    participant Pre as PreToolUse
    participant Tool as ツール
    participant Post as PostToolUse

    Note over CC: 🔄 SessionStart Hook発火
    U->>CC: リクエスト送信
    CC->>Pre: ツール実行前チェック
    alt チェックOK
        Pre->>Tool: ✅ ツール実行
        Tool->>Post: 実行完了
        Post->>CC: ログ記録
    else チェックNG
        Pre-->>CC: 🚫 ブロック
    end
    CC->>U: レスポンス
    Note over CC: 🔄 Stop Hook発火""",
        ),
    ],
    "06_メモリ.md": [
        (
            "## メモリの種類",
            """graph TD
    subgraph "🧠 メモリシステム"
        AUTO["Auto Memory<br/>~/.claude/projects/"]
        USER["User Memory<br/>~/.claude/CLAUDE.md"]
        PROJ["Project Memory<br/>repo/CLAUDE.md"]
        IDX["MEMORY.md<br/>インデックス"]
    end
    AUTO --> T1["user: 役割・目標"]
    AUTO --> T2["feedback: 指導"]
    AUTO --> T3["project: 決定事項"]
    AUTO --> T4["reference: 外部参照"]
    IDX --> AUTO""",
        ),
    ],
    "07_エージェント.md": [
        (
            "## 並列実行の例",
            """graph TD
    MAIN["🖥️ メインセッション"] --> A1["🔍 エージェントA<br/>コード探索"]
    MAIN --> A2["📝 エージェントB<br/>レビュー"]
    MAIN --> A3["🧪 エージェントC<br/>テスト実行"]
    A1 --> |"結果"| MAIN
    A2 --> |"結果"| MAIN
    A3 --> |"結果"| MAIN
    MAIN --> |"統合表示"| USER["👤 ユーザー"]""",
        ),
    ],
    "08_設定ファイル.md": [
        (
            "## 設定の3層構造",
            """graph BT
    L1["Layer 1: グローバル<br/>~/.claude/CLAUDE.md<br/>全プロジェクト共通"]
    L2["Layer 2: プロジェクト<br/>repo/CLAUDE.md<br/>プロジェクト固有"]
    L3["Layer 3: ディレクトリ<br/>repo/dir/CLAUDE.md<br/>特定ディレクトリ"]
    L3 -->|"上書き"| L2
    L2 -->|"上書き"| L1
    style L3 fill:#e8f5e9
    style L2 fill:#fff3e0
    style L1 fill:#e3f2fd""",
        ),
    ],
    "09_統合.md": [
        (
            "## モデル切替",
            """graph TD
    A["📋 タスク受付"] --> B{"Opus<br/>デフォルト"}
    B -->|"成功"| C["✅ 結果返却"]
    B -->|"失敗"| D{"Haiku<br/>フォールバック"}
    D -->|"成功"| C
    B -->|"大量処理"| E["軽量モデルに委譲"]
    E --> C
    B -->|"高品質必要"| F{"👤 ユーザー確認"}
    F -->|"許可"| G["上位モデルで処理"]
    G --> C
    F -->|"拒否"| B""",
        ),
    ],
}

# --- HTMLテンプレート ---

CHAPTER_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="ja" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — 面接対策ガイド</title>
    <meta name="description" content="面接対策 {{ title }}の解説 — プロジェクト詳細・技術判断・想定質問">
    <meta property="og:title" content="{{ title }} — 面接対策ガイド">
    <meta property="og:description" content="面接対策 {{ title }}の解説">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://fukukei23.github.io/interview-prep/chapters/{{ slug }}.html">
    <meta property="og:image" content="https://fukukei23.github.io/interview-prep/assets/ogp.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="stylesheet" href="../assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💼</text></svg>">
</head>
<body>
    <header class="site-header">
        <button class="menu-toggle" aria-label="メニュー" id="menuToggle">
            <span></span><span></span><span></span>
        </button>
        <a href="../index.html" class="site-title">💼 面接対策ガイド</a>
        <button class="theme-toggle" id="themeToggle" aria-label="テーマ切替">
            <span class="icon-light">☀️</span>
            <span class="icon-dark">🌙</span>
        </button>
    </header>

    <nav class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <a href="../index.html">🏠 ホーム</a>
        </div>
        {% for ch in chapters %}
        <a href="{{ ch.slug }}.html"
           class="sidebar-link{{ ' active' if ch.slug == current_slug }}">
            <span class="sidebar-icon">{{ ch.icon }}</span>
            {{ ch.title }}
        </a>
        {% endfor %}
    </nav>
    <div class="sidebar-overlay" id="sidebarOverlay"></div>

    <main class="content">
        <div class="chapter-nav-top">
            {% if prev_ch %}
            <a href="{{ prev_ch.slug }}.html" class="nav-prev">← {{ prev_ch.title }}</a>
            {% endif %}
            {% if next_ch %}
            <a href="{{ next_ch.slug }}.html" class="nav-next">{{ next_ch.title }} →</a>
            {% endif %}
        </div>

        <article class="chapter-body">
            {{ content|safe }}
        </article>

        <nav class="chapter-nav-bottom">
            {% if prev_ch %}
            <a href="{{ prev_ch.slug }}.html" class="nav-card prev">
                <span class="nav-label">← 前の章</span>
                <span class="nav-title">{{ prev_ch.icon }} {{ prev_ch.title }}</span>
            </a>
            {% endif %}
            {% if next_ch %}
            <a href="{{ next_ch.slug }}.html" class="nav-card next">
                <span class="nav-label">次の章 →</span>
                <span class="nav-title">{{ next_ch.icon }} {{ next_ch.title }}</span>
            </a>
            {% endif %}
        </nav>
    </main>

    <script src="../assets/script.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
            themeVariables: { fontSize: '14px' }
        });
    </script>
</body>
</html>
""", autoescape=True)

INDEX_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="ja" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>面接対策ガイド — ふくけい</title>
    <meta name="description" content="プロジェクト解説・技術判断・想定質問 — 面接前にサクッと復習">
    <meta property="og:title" content="面接対策ガイド — ふくけい">
    <meta property="og:description" content="プロジェクト解説・技術判断・想定質問 — 面接前にサクッと復習">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://fukukei23.github.io/interview-prep/">
    <meta property="og:image" content="https://fukukei23.github.io/interview-prep/assets/ogp.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="stylesheet" href="assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💼</text></svg>">
</head>
<body class="index-page">
    <header class="site-header">
        <span class="site-title">💼 面接対策ガイド</span>
        <button class="theme-toggle" id="themeToggle" aria-label="テーマ切替">
            <span class="icon-light">☀️</span>
            <span class="icon-dark">🌙</span>
        </button>
    </header>

    <main class="content">
        <section class="hero">
            <h1>面接対策ガイド</h1>
            <p>プロジェクト解説・技術判断・想定質問<br>面接前にサクッと復習</p>
        </section>

        <section class="chapter-grid">
            {% for ch in chapters %}
            <a href="chapters/{{ ch.slug }}.html" class="chapter-card">
                <div class="card-icon">{{ ch.icon }}</div>
                <div class="card-number">第{{ ch.number }}章</div>
                <h2 class="card-title">{{ ch.title }}</h2>
                <p class="card-desc">{{ ch.desc }}</p>
            </a>
            {% endfor %}
        </section>

        <section class="features">
            <h2>📖 このガイドの特徴</h2>
            <div class="feature-grid">
                <div class="feature-item">
                    <span class="feature-icon">🎯</span>
                    <h3>初心者向け</h3>
                    <p>専門用語は初出時に説明。前提知識不要</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📊</span>
                    <h3>図解付き</h3>
                    <p>アーキテクチャやフローをMermaid図で視覚化</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📱</span>
                    <h3>モバイル対応</h3>
                    <p>スマホからいつでも見返せるレスポンシブデザイン</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🌙</span>
                    <h3>ダークモード</h3>
                    <p>目に優しいテーマ切替対応</p>
                </div>
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <p>Claude Code Guide — <a href="https://github.com/fukukei23/claude-code-guide">GitHub</a></p>
    </footer>

    <script src="assets/script.js"></script>
</body>
</html>
""", autoescape=True)


# --- フィルタリング ---

def filter_sections(text: str) -> str:
    """個人情報・環境固有セクションを除去."""
    lines = text.split("\n")
    result = []
    skip = False

    for line in lines:
        stripped = line.strip()

        # 除去対象セクションの開始（## または ### セクション）
        if stripped.startswith("## ") and any(stripped.startswith(s) for s in REMOVE_SECTIONS):
            skip = True
            continue

        # 「あなたの」で始まる## / ### セクションも除去
        if (stripped.startswith("## ") or stripped.startswith("### ")) and any(p in stripped for p in REMOVE_PATTERNS):
            skip = True
            continue

        # 次の ## セクションでスキップ解除（### はスキップ解除しない）
        if skip and stripped.startswith("## ") and not any(p in stripped for p in REMOVE_PATTERNS):
            skip = False

        if not skip:
            result.append(line)

    text = "\n".join(result)

    # 個人識別子のサニタイズ
    text = text.replace("yn4416", "<USER>")
    text = text.replace("fukukei23", "<USERNAME>")
    text = text.replace("fukukei", "<USERNAME>")

    # インライン個人情報のサニタイズ
    for pattern, replacement in INLINE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in TABLE_COL_SANITIZE:
        text = re.sub(pattern, replacement, text)

    # 未処理の「あなたの」を行内テキストから除去
    text = re.sub(r"あなたの環境では", "", text)
    text = re.sub(r"あなたの環境:", "", text)

    return text


# --- Markdown → HTML変換 ---

def convert_md_to_html(md_text: str) -> str:
    """MarkdownをHTMLに変換."""
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    return md.render(md_text)


def inject_mermaid(html: str, filename: str) -> str:
    """Mermaid図を指定位置に挿入."""
    diagrams = MERMAID_DIAGRAMS.get(filename, [])
    if not diagrams:
        return html

    for heading, diagram_code in diagrams:
        # HTMLの見出しタグを検索（<a id>タグ込みも対応）
        heading_text = heading.replace("## ", "").strip()
        mermaid_block = (
            f'<div class="mermaid-wrapper">'
            f'<div class="mermaid">\n{diagram_code}\n</div>'
            f'</div>'
        )

        # <h2>テキスト</h2> または <h2><a ...></a>テキスト</h2> の前に挿入
        pattern = f"(<h2>(?:<a[^>]*></a>)?{re.escape(heading_text)}</h2>)"
        if re.search(pattern, html):
            html = re.sub(pattern, mermaid_block + r"\1", html, count=1)

    return html


def rewrite_links(html: str, chapter_map: dict | None = None) -> str:
    """内部リンクをHTML URLに書き換え."""
    from urllib.parse import quote, unquote

    cmap = chapter_map or CHAPTER_MAP

    for filename, info in cmap.items():
        # [テキスト](XX_YY.md) → XX-yy.html
        html = html.replace(f'href="{filename}', f'href="{info["slug"]}.html')
        # [テキスト](XX_YY.md#anchor) → XX-yy.html#anchor
        html = re.sub(
            rf'href="{re.escape(filename)}#',
            f'href="{info["slug"]}.html#',
            html,
        )

        # URLエンコードされたリンク（例: 11_%E7%8F%BE%E5%A0%B4...）も処理
        encoded_name = quote(filename, safe='')
        if encoded_name != filename:
            html = html.replace(f'href="{encoded_name}', f'href="{info["slug"]}.html')
            html = re.sub(
                rf'href="{re.escape(encoded_name)}#',
                f'href="{info["slug"]}.html#',
                html,
            )

    # 未変換の.mdリンクをすべて処理
    def replace_md_link(match):
        href = match.group(1)
        for filename, info in cmap.items():
            decoded = unquote(href)
            if filename in decoded or filename in href:
                anchor = ""
                if "#" in href:
                    anchor = "#" + href.split("#", 1)[1]
                elif "#" in decoded:
                    anchor = "#" + decoded.split("#", 1)[1]
                return f'href="{info["slug"]}.html{anchor}"'
        return 'href="#"'

    html = re.sub(r'href="([^"]*\.md[^"]*)"', replace_md_link, html)

    # 外部リンク（obsidian-ssot内の他ファイル）を除去
    html = re.sub(r'href="\.\./[^"]*"', 'href="#"', html)
    html = re.sub(r'href="01_DECISIONS[^"]*"', 'href="#"', html)

    return html


def enhance_html(html: str) -> str:
    """HTMLに装飾を追加（テーブルラップ・コールアウト等）."""
    # テーブルをスクロールラッパーで囲む
    html = re.sub(
        r"(<table[^>]*>.*?</table>)",
        r'<div class="table-wrapper">\1</div>',
        html,
        flags=re.DOTALL,
    )

    # 引用ブロックをコールアウトに変換
    def callout_replace(match):
        content = match.group(1)
        if "注意" in content or "⚠" in content:
            return f'<div class="callout callout-warn"><p>{content}</p></div>'
        if "重要" in content:
            return f'<div class="callout callout-danger"><p>{content}</p></div>'
        if "現場の知見" in content or "💡" in content or "Tip" in content:
            return f'<div class="callout callout-tip"><p>{content}</p></div>'
        return f'<div class="callout callout-info"><p>{content}</p></div>'

    html = re.sub(r"<blockquote>\s*<p>(.*?)</p>\s*</blockquote>", callout_replace, html, flags=re.DOTALL)

    return html


# --- 用語ツールチップ（add-term-tooltip パターン・クリック/ホバーで解説表示） ---
# source MD は html:False で生HTMLを書けないため、レンダリング後の後処理で囲む
TERM_TOOLTIPS = {
    "最もホットな新しいプログラミング言語は英語だ": (
        "OpenAI共同創業者でAI研究者アンドレイ・カルパシー氏の言葉（2023年1月）。"
        "「プログラミングは専門用語のコードでなく、普段の話し言葉（英語・日本語）で"
        "AIに伝えれば良くなる」という時代の変化を、一言で言い表した発言。"
        "本章の「言葉で伝えれば作れる」という私の実践と同じ方向を指す"
    ),
    "ケンタウロス・モデル": (
        "チェスの元世界王者ガルリ・カスパロフが提唱した協働スタイルの名前。"
        "半人半馬のケンタウロスに例えて「人間+AIのペア」を指す。"
        "2005年頃のフリースタイル・チェス大会で、人間+AIのペアが"
        "世界王者（人間単独）もAI単独も負かした実史がある。"
        "「人間単独 ＜ AI単独 ＜ 人間+AI」という順番が実証された"
    ),
    "モラベックのパラドックス": (
        "AI研究者ハンス・モラベックが指摘した逆説（1980年代）。"
        "「人間に簡単なこと（歩く・物を見る・常識的な判断）はAIに難しく、"
        "人間に難しいこと（暗記・計算）はAIに簡単」というもの。"
        "だから知識の暗記はAIに任せて、問いを立てる・判断する役割が人間に残る——"
        "という本章の論理の裏付けになる"
    ),
    "暗黙知の存在": (
        "哲学者マイケル・ポランニーの用語（1958年）。"
        "言葉やマニュアルで説明できる知識（形式知）に対し、"
        "経験で体で覚える「言葉にできない知識」のこと。"
        "自転車の乗り方や職人の勘が例。AIが扱えるのは形式知のみなので、"
        "暗黙知は人間のまま——だからAIは「代替」でなく「拡張」だと論じられる"
    ),
    "Jensen Huang": (
        "NVIDIA（AIチップ世界最大手）の創業者CEO。"
        "「AIはあなたの仕事を奪わない。AIを使う人が奪う」"
        "という言葉で知られ、AI時代の働き方を象徴する発言としてよく引用される。"
        "「使いこなし方次第でチャレンジの幅が広がる」という私の実感と同じ構造"
    ),
    "歴史からの類推": (
        "「新しい道具が出ると職人が消える」という心配は、歴史上いつもされてきた。"
        "しかし電卓が登場しても数学者は消えず、写真が発明されても画家は消えなかった。"
        "道具の進歩は「仕事の全滅」でなく「仕事の内容の変化」を毎回もたらしてきた——"
        "という過去のパターンとの比較で考えること"
    ),
    # --- 全章共通の技術用語（06章基準・2026-08-17拡張） ---
    # ※ 包含関係のある用語は「長い方を先に」定義すること（例: CI/CD → CI）
    "Cloudflare Workers": (
        "世界中に分散したサーバー上で小さなプログラムを動かす仕組み"
        "（Cloudflare社のサービス）。使った分だけの課金なので、"
        "アクセスが少ないサービスなら実質無料で運用できる"
    ),
    "コールドスタート": (
        "しばらく使われていなかったプログラムを、次に利用が来た時に"
        "ゼロから起動すること。この起動時間が長いと利用者が待たされる。"
        "Cloudflare Workersはこの起動が速いとされる"
    ),
    "GAS": (
        "Google Apps Script（グーグル・アップス・スクリプト）の略。"
        "Googleが提供する、Gmailやスプレッドシート等のGoogleサービスを"
        "自動化するための簡易プログラミング環境"
    ),
    "FastAPI": (
        "PythonでWeb API（他のプログラムから呼び出せる機能）を作るための"
        "フレームワーク（骨組み部品のセット）。処理を待たせない「非同期」方式に"
        "対応して高速で、APIの説明書（OpenAPIドキュメント）を自動生成する"
    ),
    "Flask": (
        "PythonでWebアプリや管理画面を軽く作るためのフレームワーク。"
        "必要最小限の機能だけを提供する「軽量」設計が特徴で、"
        "小規模な社内ツール等に向く"
    ),
    "Django": (
        "Python用の「全部入り」Webフレームワーク。管理画面・ユーザー認証・"
        "データベース操作等が最初から揃っている。大規模向けだが、"
        "小さい用途には過剰になりがち"
    ),
    "Python": (
        "AI・データ分析の分野で最も使われるプログラミング言語（読み: パイソン）。"
        "AI関連の道具が最も豊富で、文法が読みやすいのが特徴"
    ),
    "OpenAPI": (
        "Web API（他のプログラムから使うための機能）の仕様書を書く標準的な書式。"
        "この書式に沿っておくと、APIの使い方を機械も人間もすぐ理解できる。"
        "FastAPIはコードからこの仕様書を自動生成する"
    ),
    "エコシステム": (
        "ある技術の周りに自然に集まった、関連道具・教材・コミュニティの総体。"
        "「エコシステムが豊富」＝困った時に道具や情報がすぐ見つかる状態"
    ),
    "非同期": (
        "1つの処理の完了を待たずに、他の処理を同時に進める方式。"
        "ファストフードで注文を受けて番号で呼ぶイメージ。"
        "Webサーバーが多数の利用者を同時に捌く時に効く"
    ),
    "API": (
        "Application Programming Interface（エーピーアイ）の略。"
        "あるプログラムの機能を、別のプログラムから呼び出せるようにした「窓口」。"
        "予約システムがLINE社の機能とやり取りするのもAPI経由"
    ),
    "エージェント": (
        "与えられた目標に向かって、自分で手順を組み立てて作業を進めるAIプログラム。"
        "質問に答えるだけのチャットAIと違い、"
        "「調べる→書く→確認する」を自律的に行う"
    ),
    "品質ゲート": (
        "次の工程（例: 本番公開）に進んで良いかを判定する関門。"
        "テストが全部通っているか・コード検査で警告が出ていないか等を"
        "機械的にチェックし、不合格なら先に進めないようにする"
    ),
    "品質ティア": (
        "LLM（AI）を能力と値段のランク（ティア＝階層）で分けて使い分けること。"
        "難しい仕事は高性能・高コストのモデルへ、簡単な仕事は低コストのモデルへ"
        "振り分けて、全体のコストを下げる"
    ),
    "LLMルーティング": (
        "タスクの内容に応じて、どのLLM（AIモデル）に処理させるかを"
        "振り分ける（ルーティング＝経路選択する）仕組み。"
        "品質とコストのバランスを取るのが目的"
    ),
    "LLMプロバイダー": (
        "LLM（大規模言語モデル＝ChatGPTのような文章生成AI）を提供する事業者。"
        "OpenAI・Anthropic・Google等。性能・値段・得意分野が違うので使い分ける"
    ),
    "CI/CD": (
        "コードの変更のたびに、自動でビルド・テスト・公開まで行う仕組み。"
        "CI＝継続的インテグレーション（自動テスト等）、"
        "CD＝継続的デリバリー（自動公開等）。人的ミスとチェック忘れを防ぐ"
    ),
    "CI": (
        "Continuous Integration（シーアイ・継続的インテグレーション）の略。"
        "コードを変更するたびに自動でテストとチェックを回し、"
        "壊れていないかを常に確認する仕組み"
    ),
    "OWASP": (
        "Open Web Application Security Project（オワスプ）の略。"
        "Webアプリの脆弱性（セキュリティ上の弱点）を体系的にまとめて"
        "公開している国際団体。「OWASP対応」＝このリストの弱点への対策経験"
    ),
    "SOP": (
        "Standard Operating Procedure（エスオーピー）の略。標準作業手順書。"
        "「どういう手順で何をするか」を文書化したもの。"
        "自衛隊の全業務マニュアル文化がこれに相当"
    ),
    "MCP": (
        "Model Context Protocol（エムシーピー）の略。"
        "AIに外部ツール（検索・GitHub・データベース等）を繋ぐための共通接続規格。"
        "USBのような「差せば繋がる」仕組みでAIの能力を拡張する"
    ),
    "RAG": (
        "Retrieval-Augmented Generation（ラグ・検索拡張生成）の略。"
        "AIに答えさせる前に、自分の文書から関連箇所を検索して渡し、"
        "その内容に基づいて答えさせる仕組み。社内文書のQA等で使われる"
    ),
    "MLOps": (
        "Machine Learning Operations（エムエルオプス）の略。"
        "機械学習のモデルを、作って終わりでなく継続的に運用・改善するための"
        "仕組みと文化。DevOpsの機械学習版"
    ),
    "OAuth": (
        "オーオースと読む。他のサービスの機能を、IDやパスワードを教えずに"
        "安全に使わせるための認可の標準規格。"
        "「○○でログイン」ボタンの裏側で動いている仕組み"
    ),
    "Docker": (
        "ドッカー。プログラムとその実行環境一式を「コンテナ」という箱に梱包して、"
        "どのPCでも同じように動かす技術。"
        "「私の環境では動くのに」という問題を防ぐ"
    ),
    "Celery": (
        "セラリー（Pythonのライブラリ）。時間のかかる処理を裏で"
        "非同期に実行するための仕組み。処理を「タスク」として"
        "待ち行列に入れて順番に回す時に使う"
    ),
    "Redis": (
        "レディス。超高速なデータ保存システム（インメモリDB）。"
        "主に一時データの保管や、同じ処理が重複して走るのを防ぐ"
        "ロック等に使う"
    ),
    "カバレッジ": (
        "テストがコードのどれくらいの割合を確認できているかを表す数字（％）。"
        "80%なら、コードの8割が少なくとも1回はテストで実行されたことになる"
    ),
    "SSOT": (
        "Single Source of Truth（エスエスオーティー・唯一の真実の情報源）の略。"
        "情報をあちこちに重複して持たず、1か所だけを正として管理する考え方。"
        "ズレや矛盾を構造的に防ぐ"
    ),
    "Webhook": (
        "ウェブフック。「イベントが起きたら指定URLに自動で通知を送る」仕組み。"
        "GitHubで更新があればDiscordに通知が飛ぶ、等の連携に使う"
    ),
    "スクレイピング": (
        "Webサイトのページを読み込んで、必要な情報（価格・在庫等）を"
        "自動で抜き出すこと"
    ),
    "RPA": (
        "Robotic Process Automation（アールピーエー）の略。"
        "人がパソコンで行う定型作業（コピペ・転記等）を"
        "ソフトウェアに代行させること"
    ),
    "型ヒント": (
        "変数や関数の入出力が「数値か文字列か」等の型であると予め宣言する書き方。"
        "書き間違いを実行前に機械が検出できるようになる"
    ),
    "ハルシネーション": (
        "AIが、事実でないことを自信満々に生成してしまう現象の呼び名（幻覚の意）。"
        "出典の確認や複数AIでの相互確認で対策する"
    ),
    "要件定義": (
        "「何を・何のために作るか」を言葉に整理して関係者で合わせる最初の作業。"
        "ここが曖昧だと手戻りが最大になる"
    ),
    "アーキテクチャ設計": (
        "システム全体の骨組み（部品の分け方・データの流れ・技術の選定）を"
        "決める設計作業"
    ),
    "テスト駆動": (
        "TDD（テスト駆動開発）。先にテストを書き、そのテストを通すように"
        "コードを書く進め方。「何をもって正しいとするか」を最初に固定できる"
    ),
    "デプロイ": (
        "作ったプログラムを、実際に動くサーバーや公開環境へ設置して"
        "動かし始めること"
    ),
    "本番環境": (
        "実際の利用者が使っている環境のこと。テスト環境と区別され、"
        "ここでの事故は直接利用者に影響する"
    ),
    "コードレビュー": (
        "書かれたコードを、書いた本人以外の視点で読んで問題を指摘する作業。"
        "バグ・読みにくさ・危険な書き方を第三者が見つけるのに有効"
    ),
    "脆弱性": (
        "セキュリティ上の弱点。攻撃者に悪用されると情報漏えい等の被害が出る、"
        "コードや設定の穴のこと"
    ),
    "トークン": (
        "AIにとっての「文字数」のようなもの。AIは文章をトークンという小片に"
        "区切って処理する。課金や入力上限はこの単位で数えられる"
    ),
    "プロンプト": (
        "AIに渡す指示文のこと。「この機能を作って」「この文を直して」等"
    ),
}


def wrap_terms(html: str) -> str:
    """登録用語の最初の出現箇所だけを、クリック解説付きマークアップで囲む.

    2フェーズ構成: 先にプレースホルダー（\\x00TERM{n}\\x00）へ置換し、
    全用語の走査が終わってから実マークアップへ差し戻す。これにより
    (1) 挿入済みpopup内の説明文が後続用語で再ラップされるネスト
    (2) 「FastAPI」が「API」で二重ラップされる部分一致
    を構造的に防ぐ。
    """
    wraps: dict[str, str] = {}
    for i, (term, desc) in enumerate(TERM_TOOLTIPS.items()):
        if term in html:
            ph = f"\x00TERM{i}\x00"
            wraps[ph] = (
                f'<span class="term" tabindex="0">{term}'
                f'<span class="term-popup">{html_mod.escape(desc)}</span></span>'
            )
            html = html.replace(term, ph, 1)
    for ph, wrapped in wraps.items():
        html = html.replace(ph, wrapped)
    return html


# --- メイン ---

def main():
    # ディレクトリ準備
    chapters_dir = OUTPUT_DIR / "chapters"
    assets_dir = OUTPUT_DIR / "assets"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 章リストを構築（自動スキャン込み）
    effective_map = build_chapter_map()
    chapters = []
    for filename, info in sorted(effective_map.items()):
        chapters.append({
            "number": info["slug"][:2],
            "slug": info["slug"],
            "title": info["title"],
            "icon": info["icon"],
            "desc": info["desc"],
            "filename": filename,
        })

    # 各章を変換
    for i, ch in enumerate(chapters):
        src = SOURCE_DIR / ch["filename"]
        if not src.exists():
            print(f"SKIP: {ch['filename']} not found")
            continue

        md_text = src.read_text(encoding="utf-8")
        md_text = filter_sections(md_text)
        html_body = convert_md_to_html(md_text)
        html_body = inject_mermaid(html_body, ch["filename"])
        html_body = rewrite_links(html_body, effective_map)
        html_body = enhance_html(html_body)
        html_body = wrap_terms(html_body)

        prev_ch = chapters[i - 1] if i > 0 else None
        next_ch = chapters[i + 1] if i < len(chapters) - 1 else None

        full_html = CHAPTER_TEMPLATE.render(
            title=ch["title"],
            slug=ch["slug"],
            current_slug=ch["slug"],
            content=html_body,
            chapters=chapters,
            prev_ch=prev_ch,
            next_ch=next_ch,
        )

        out = chapters_dir / f"{ch['slug']}.html"
        out.write_text(full_html, encoding="utf-8")
        print(f"OK: {ch['slug']}.html")

    # index.html 生成
    index_html = INDEX_TEMPLATE.render(chapters=chapters)
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("OK: index.html")

    print(f"\n完了: {len(chapters)}章 + index → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
