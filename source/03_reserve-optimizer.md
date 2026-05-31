# reserve-optimizer

> 整骨院向けLINE予約管理Bot。LINE Bot + GAS + Cloudflare Workers + Stripe決済の
> サーバーレス構成で、24時間自動受付・決済・AIチャット対応を実現。

## なぜ作ったか

整骨院の予約管理は電話・紙ベースが多く、スタッフの負担が大きいという課題がありました。LINE Botで24時間自動受付・Stripe決済・AIチャット対応を実現し、予約業務をゼロにするために開発しました。

## アーキテクチャ

### レイヤー構成

```
[LINEユーザー] ←→ [LINE Messaging API]
                      ↓ Webhook
                 [Cloudflare Worker] ← 署名検証 + 即座に200 OK返却
                      ↓ waitUntil で転送
                 [GAS Web App] ← 会話ステートマシン実行
                      ↓
                 [Google Spreadsheets] ← データ保存
                      ↓
                 [Stripe Checkout] ← デポジット決済（1,000円）
```

### 設計上の判断と理由

**Q: なぜCloudflare Workerを挟んでいるのか？GASに直接Webhookしない理由**

LINEのWebhookは**5秒以内に200 OKを返さないとタイムアウト**します。しかしGASの起動は遅く（コールドスタートで3〜5秒）、処理も含めるとタイムアウトする可能性があります。そこで：

1. Cloudflare Workerが即座に200 OKを返す（LINEタイムアウト回避）
2. `waitUntil` で非同期にGASへ転送
3. WorkerでHMAC-SHA256署名検証も行う（セキュリティ層）

**Q: なぜデータベースにGoogle Spreadsheetsを選んだのか？**

- 運用者が非エンジニア（整骨院スタッフ）のため、スプレッドシートなら直接確認・修正できる
- 無料枠で十分に運用可能
- GASと同じGoogleエコシステムで連携が簡単
- 将来的にFirestore等に移行する場合も、データアクセス層を変更するだけで対応可能

**Q: なぜデポジット制（前払い1,000円）なのか？**

- 無料予約ではキャンセルやドタキャンの問題が頻発する
- 1,000円の心理的ハードルで、本気で予約する人だけに絞れる
- Stripe Checkoutを使うことで、PCI DSS準拠の安全な決済を簡単に実装

### 会話ステートマシン

LINE Botの会話フローを状態管理する仕組みです：

```
初期状態 → 日付選択 → 時間枠選択 → 予約確認 → Stripe決済 → 予約完了
                                                        ↓ キャンセル
                                                    予約取消
```

各状態でQuickReply（選択肢ボタン）を表示し、ユーザーが迷わないように設計しています。

### AIチャット（MiniMax M2.7）

整骨院に関する質問に回答するAIチャット機能：
- トピックを「整骨院関連」に限定（関係ない質問には答えない）
- 既知のFAQはテンプレート回答、未知の質問のみAI生成

## 面接で聞かれそうなポイント

### 「なぜサーバーレス構成？EC2等のサーバーではない理由」

- 予約システムは1日のアクセスが少なく（数十件）、常にサーバーを立てるのはコストの無駄
- Cloudflare Workersは無料枠（10万リクエスト/日）で十分
- GASも無料枠で運用可能
- 結果的に**月額0円**で本番稼働

### 「Stripe Checkoutの選定理由」

- 自分で決済フォームを実装するとPCI DSS（クレジットカード情報の保護基準）への対応が必要
- Stripe Checkoutを使えば、カード情報はStripeのサーバーで処理され、こちらには届かない
- セキュリティリスクを最小化できる

### 技術スタック

- TypeScript / Google Apps Script (JavaScript)
- Cloudflare Workers / LINE Messaging API
- Stripe API / Google Spreadsheets
- MiniMax M2.7（AIチャット）
