# robotbase_ws DOCS

このフォルダは、ルートREADMEに収めると長くなるプロジェクト固有情報を保持します。Navigation2など上流パッケージの一般仕様ではなく、このロボットに固有の構成、判断、未解決事項を優先して記録します。

## 推奨する読み順

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — 現状を短時間で把握する
2. [NAV2_NO_MOTION.md](NAV2_NO_MOTION.md) — 2026-08-19のNav2無走行を切り分ける
3. [ARCHITECTURE.md](ARCHITECTURE.md) — ノード、トピック、SIRIUSとの差分を理解する
4. [CONFIGURATION.md](CONFIGURATION.md) — 設定の正本と既知の不整合を確認する

## AIへ調査を依頼するとき

最初に次のように指定すると、`src/navigation2/` 全体を読み直すトークンと時間を節約できます。

```text
robotbase_ws/README.md と DOCS/PROJECT_CONTEXT.md を先に読み、
必要な場合だけ DOCS/NAV2_NO_MOTION.md と関連ソースを確認して。
上流の src/navigation2 全体は探索しないで。
```

実機トラブル時は、次の情報も一緒に残すと再調査が短くなります。

- 実施日時とGitコミット (`git rev-parse --short HEAD`)
- 起動したエイリアス一覧
- Nav2端末の警告・エラー
- `/cmd_vel_nav`、`/cmd_vel_smoothed`、`/cmd_vel` の有無
- `/odom/filtered`、`/scan` の周波数
- `controller_server` と `velocity_smoother` のLifecycle状態
- 使用地図と初期姿勢

## 更新方針

- 実機で確認した事実と、コードからの推定を区別する
- パラメータ値を変更したら `CONFIGURATION.md` も更新する
- 速度指令の接続を変更したら全ドキュメントの経路図を更新する
- 解決した障害は、原因・確認方法・修正コミットを `NAV2_NO_MOTION.md` に追記する
