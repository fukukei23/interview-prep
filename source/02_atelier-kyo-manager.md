# atelier-kyo-manager

> BUYMA転売管理システム。出品パイプライン・自動発注ステートマシン・
> AIチャットボット・価格スクレイピングを統合したFlaskアプリ。

## なぜ作ったか

BUYMA（海外ブランドの買い付け代行プラットフォーム）での転売業務は、出品・価格調整・発注・顧客対応など多岐にわたる手作業が発生します。これらをFlask Webアプリ + AI/LLMで自動化し、1人でもスケール可能な物販システムを目指して開発しました。

## アーキテクチャ

```
Flask App Factory (create_app)
  ├── Blueprint (6モジュール)    ← HTTPルーティング
  │     analytics / orders / partners / products / misc / warehouse_webhook
  ├── Service層 (8モジュール)    ← ビジネスロジック
  │     auto_order / chatbot / image / notification / pipeline
  │     price_scraper / template / warehouse_event
  ├── Models (16種)              ← SQLAlchemyデータモデル
  ├── Utils (20+モジュール)      ← ai_llm_controller / fx_utils / pricing_calculator 等
  └── Templates / Static         ← Jinja2 + CSS/JS
```

**設計のポイント**: FlaskのBlueprint + Service層の2層構造にすることで、ルーティング（Blueprint）とビジネスロジック（Service）を分離。テスト時にService層だけを単体テスト可能にしています。

## 主要ビジネスロジック

### 自動発注ステートマシン

注文の状態遷移を自動管理する仕組みです：

```
pending → sourcing → cart_added → checkout → payment_done → shipped → completed
```

各状態遷移には**ガード条件**（遷移可能かの判定）があります。例えば `sourcing → cart_added` に遷移するには「仕入先の在庫確認が完了していること」が必要です。

### 出品パイプライン

```
画像収集 → AI背景除去（rembg） → AI説明文生成（LLM） → 出品テキスト生成 → BUYMA出品
```

各ステップが独立しているため、途中で失敗しても再開可能です。

### AIチャットボット（3段階分類）

顧客からの問い合わせを3段階で処理します：

1. **FAQテンプレートマッチ**: 既知の質問パターンに一致するか確認
2. **AI回答生成**: 一致しない場合、LLMで回答を生成
3. **エスカレーション判定**: AIが自信を持てない場合は人間（私）に通知

**なぜ3段階にしたか**: 全ての問い合わせをAIに任せると不正確な回答のリスクがある。FAQで確実に回答できるものは高速に処理し、AIが必要なものだけLLMを使うことで、品質とコストのバランスを取っています。

### 価格スクレイピング

Playwrightヘッドレスブラウザで仕入先の価格を自動取得します。

**なぜrequests/BeautifulSoupではなくPlaywrightか**: 仕入先サイトがJavaScriptレンダリングに依存しているため、静的HTMLの取得では価格情報が取得できませんでした。Playwrightなら実際のブラウザと同じようにJSを実行してからDOMを取得できます。

### 18日ルール管理

BUYMAには「18日以内に発送しないとキャンセルされる」ルールがあります。決済方法によって延長期限が異なるため、これを自動計算・管理します：

| 決済方法 | 延長期限 |
|---------|---------|
| クレジットカード | 45日 |
| 銀行振込 | 90日 |
| コンビニ決済 | 30日 |

## 面接で聞かれそうなポイント

### 「なぜFlask？Djangoではない理由」

- atelier-kyo-managerは管理画面 + APIの構成で、DjangoのORM/admin/templates等の「全部入り」機能が不要だった
- Flaskの方が軽量で、必要なライブラリ（SQLAlchemy / Playwright / rembg等）を自由に選べる
- 結果的にFlask App Factory + Blueprintの構成で十分スケールした

### 「なぜSQLite？PostgreSQLではない理由」

- 個人利用のシステムで同時接続数が少ないため、SQLiteで十分
- デプロイが簡単（サーバー不要、ファイル1つで完結）
- 将来的にスケールする必要があれば、SQLAlchemy経由でPostgreSQLに移行可能（モデル層の変更なし）

### 技術スタック

- Python 3.10+ / Flask / SQLAlchemy
- Playwright（ヘッドレスブラウザ）
- pytest（967テストケース）
- rembg（AI背景除去）
