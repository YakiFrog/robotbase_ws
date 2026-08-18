# robotbase_ws

SIRIUS用の [`sirius_jazzy_ws`](../sirius_jazzy_ws) を基に、新しい差動二輪ロボット向けに調整している ROS 2 Jazzy ワークスペースです。車輪径、トレッド幅、エンコーダ、車体寸法、センサー構成がSIRIUSと異なります。

## 現在の状況（2026-08-19）

- 実機の手動操作: 動作確認済み
- `keyop2`: 動作確認済み
- Nav2: RViz上でグローバルパス生成までは確認済み
- Nav2による実機走行: 未動作。パス生成後に走り始めない
- Gazeboシミュレータ: 構築・動作確認済み
- シミュレータでの2D地図生成: 動作確認済み
- シミュレータでのNav2自律移動: 動作確認済み（障害物迂回ゴール成功）
- 原因: 実機トピックを記録していないため未確定。ただし、コード上の優先度は次のとおり

1. `controller_server.use_realtime_priority: true` に対して、実機PCのRT優先度権限が未設定
2. `twist_mux` の起動漏れ、または `/cmd_vel_nav` から `/cmd_vel` までの途中停止
3. `/odom/filtered`、`/scan`、TF、ローカルコストマップのいずれかが未更新
4. `keyop2` または `/stop` が `twist_mux` のNav2入力より高い優先度を保持

最有力は1です。現在のNav2実装では、RT権限がない状態で `use_realtime_priority: true` のままFollowPathを開始すると、速度計算スレッドが例外で終了する可能性があります。「パスは引けるが速度を出し始めない」という症状と一致します。

詳細と実機での判定手順は [Nav2無走行の切り分け](DOCS/NAV2_NO_MOTION.md) を参照してください。

## 実機なしのGazebo実験

`robotbase_sim` パッケージに、差動二輪・Velodyne VLP-16・IMUだけを持つ簡易 Gazebo Sim 環境を追加しています。実機と同じ主要寸法と `sirius3/*` TF名を使います。

```bash
cd ~/robotbase_ws
source install/setup.bash

# SLAMで地図生成
ros2 launch robotbase_sim mapping.launch.py

# 同梱地図でNav2自律移動
ros2 launch robotbase_sim navigation.launch.py
```

エイリアスを読み込んでいる場合は `robotbase_mapping` と `robotbase_nav` でも起動できます。GUI不要時は末尾に `gui:=false rviz:=false` を指定します。

Nav2モードは実験の再現性を優先し、Gazebo真値オドメトリへ `map -> sirius3/odom` を固定する簡易ローカライゼーションです。SLAMモードでは slam_toolbox がこのTFを推定します。構成、地図保存、操作、TFの前提は [シミュレータ詳細](DOCS/SIMULATION.md) を参照してください。

## 速度指令の経路

```text
Nav2 controller_server
  └─ /cmd_vel_nav
      └─ velocity_smoother
          └─ /cmd_vel_smoothed
              └─ twist_mux
                  └─ /cmd_vel
                      └─ roboteq_ros2_driver
```

この主経路のトピック名はコード上は整合しています。ただし `twist_mux` は `nav2_real` から自動起動されません。別ターミナルまたはランチャーでの起動が必須です。

`collision_monitor` は現在 `cmd_vel_collision_in` を待ち、`cmd_vel_collision_out` を出す設定ですが、主経路には接続されていません。したがって今回の「動かない」直接原因ではない一方、衝突監視が実走行指令に適用されない安全上の未完了項目です。

## 実機の主な設定

| 項目 | 現在値 |
|---|---:|
| 駆動方式 | 差動二輪 (`DiffDrive`) |
| 車輪直径 / 円周 | 200 mm / 0.6283 m |
| トレッド幅 | 0.435 m |
| エンコーダ | 950 pulse/車輪1回転 |
| Roboteq odom配信 | 50 Hz |
| Nav2フットプリント | 前0.40 m、後0.45 m、左右0.28 m |
| Nav2最大前進速度 | 0.90 m/s |
| Nav2最大角速度 | 0.90 rad/s |
| Nav2入力LaserScan | `/scan` |
| 制御用オドメトリ | `/odom/filtered` |

値の出典とSIRIUSとの差分は [構成資料](DOCS/ARCHITECTURE.md) にまとめています。

## 実機起動の基本順序

`.bashrc` から次を読み込んでいる前提です。

```bash
source ~/robotbase_ws/bash/bash_alias1.sh
source ~/robotbase_ws/bash/bash_alias2.sh
```

各コマンドは別ターミナルで起動します。

```bash
roboteq       # Roboteq。EKF使用時はdriver自身のodom TFを無効化
velodyne      # 使用する場合
hokuyo        # /scanを出す2D LiDAR。環境に応じて実際のdriverを確認
imu           # IMU
sf_real       # /odom + /imu -> /odom/filtered、odom TF
twist_mux     # Nav2/keyop2の速度指令を /cmd_vel に統合
nav2_real     # 地図を選択してNav2起動
rviz2real
keyop2        # 必要な場合のみ
```

`フルセンサーセット` プリセットには現状 `twist_mux` と `nav2_real` が含まれていません。Nav2実機試験では個別に起動してください。

## 最短の実機診断

Nav2ゴール送信中に、別ターミナルで上から順に確認します。

```bash
ros2 lifecycle get /controller_server
ros2 lifecycle get /velocity_smoother
ros2 node list | grep twist_mux

ros2 topic hz /cmd_vel_nav
ros2 topic hz /cmd_vel_smoothed
ros2 topic hz /cmd_vel

ros2 topic hz /odom/filtered
ros2 topic hz /scan
ros2 run tf2_ros tf2_echo sirius3/odom sirius3/base_footprint
```

最初に速度が途切れた箇所が故障境界です。`/cmd_vel_nav` が出ない場合はNav2端末で次の文字列を探してください。

```text
Cannot set as real-time thread
No valid trajectories
Timed out waiting for transform
Failed to make progress
```

## ディレクトリ案内

| パス | 役割 |
|---|---|
| `params/` | Nav2、EKF、SLAM等の実機・シミュレーション設定 |
| `src/sirius/` | ロボット固有のdescription、操作、navigationノード |
| `src/robotbase_sim/` | Gazebo Sim、VLP16/IMU、SLAM、Nav2の簡易実験環境 |
| `src/roboteq_ros2_jazzy_driver/` | モータ指令とホイールオドメトリ |
| `src/navigation2/` | ワークスペース内でビルドするNav2本体 |
| `src/slam_toolbox/` | 2D SLAM |
| `src/velodyne/` | Velodyneドライバ |
| `src/witmotion_ros/` | IMUドライバ |
| `bash/` | エイリアスと起動補助スクリプト |
| `other_programs/sirius_launcher/` | エイリアスをGUIボタン化するランチャー |
| `DOCS/` | 本プロジェクト固有の詳細資料と調査記録 |

## ドキュメント

- [DOCS索引](DOCS/README.md)
- [短いプロジェクトコンテキスト](DOCS/PROJECT_CONTEXT.md) — 人・AIとも最初に読む
- [構成、データフロー、SIRIUSとの差分](DOCS/ARCHITECTURE.md)
- [Nav2無走行の原因候補と切り分け](DOCS/NAV2_NO_MOTION.md)
- [設定の正本と既知の課題](DOCS/CONFIGURATION.md)
- [Gazeboシミュレータの構成と使い方](DOCS/SIMULATION.md)

## ビルド

```bash
cd ~/robotbase_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -riy
colcon build --symlink-install --executor sequential --allow-overriding nav2_costmap_2d
source install/setup.bash
```

このチェックアウトでは `build/`、`install/`、`log/` はGit管理対象外です。設定変更後は必ず再ビルドし、起動ターミナルで `install/setup.bash` を読み直してください。
