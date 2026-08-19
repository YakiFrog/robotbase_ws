# robotbase_ws

SIRIUS用の [`sirius_jazzy_ws`](../sirius_jazzy_ws) を基に、新しい差動二輪ロボット向けに調整している ROS 2 Jazzy ワークスペースです。車輪径、トレッド幅、エンコーダ、車体寸法、センサー構成がSIRIUSと異なります。

新機体の仮称は「ココちゃん」です。表示名、ROS Domain、Gazebo識別子は [`robot.env`](robot.env) で変更できます。この開発PC上のSIRIUSと競合しないよう、Bashコマンドは `koko_*`、ROSはDomain 57、Gazeboはpartition `koko`へ分離しています。

Foxglove Bridgeは実機・シミュレーション共通で `koko_foxglove` から起動できます。Siriusの既定ポート8765と競合しないよう、ココちゃんは8766を使います。

## 現在の状況（2026-08-19）

- 実機の手動操作: 動作確認済み
- `keyop2`: 動作確認済み
- Nav2: RViz上でグローバルパス生成までは確認済み
- Nav2による実機走行: 未動作。パス生成後に走り始めない
- Gazeboシミュレータ: 構築・動作確認済み
- シミュレータでの2D地図生成: 動作確認済み
- シミュレータでのNav2自律移動: 分離launch/シミュレーション専用params/`robot/*` TFで動作確認済み（障害物迂回ゴール成功）
- 原因: 実機トピックを記録していないため未確定。ただし、コード上の優先度は次のとおり

1. 旧設定の `controller_server.use_realtime_priority: true` に対して、実機PCのRT優先度権限が未設定
2. `twist_mux` の起動漏れ、または `/cmd_vel_nav` から `/cmd_vel` までの途中停止
3. `/odom/filtered`、`/scan3`、TF、ローカルコストマップのいずれかが未更新
4. `keyop2` または `/stop` が `twist_mux` のNav2入力より高い優先度を保持

最有力だった1に対し、新しい実機設定では `use_realtime_priority: false` に変更済みです。実機での再確認はまだです。

詳細と実機での判定手順は [Nav2無走行の切り分け](DOCS/NAV2_NO_MOTION.md) を参照してください。

## 実機なしのGazebo実験

`robotbase_sim` パッケージに、差動二輪・Velodyne VLP-16・IMUだけを持つ簡易 Gazebo Sim 環境を追加しています。TFは既定で `robot/*` を使います。

```bash
cd ~/robotbase_ws
source install/setup.bash

# 端末1: Gazeboのみ
koko_sim
# 端末2: RVizのみ
koko_rviz_sim
# 端末3: 用途に応じて1つ
koko_slamtoolbox_sim
koko_nav2_sim_map
koko_nav2_sim_slam
```

`koko_nav2_sim_map` は同梱・保存済み地図を端末の一覧から選択し、AMCLを起動します。RVizの `2D Pose Estimate` で初期姿勢を指定できます。`koko_nav2_sim_slam` は地図なしでSLAM ToolboxとNav2を同時に使います。GazeboとRVizはどちらのモードでも別起動です。`twist_mux` は `koko_sim` に含まれるため、シミュレーションで別起動する必要はありません。

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

`collision_monitor` は未接続の設定を残さず、現在の最小Nav2 launchから外しています。`/scan3` はcostmap回避に使われますが、独立した最終停止レイヤーは未実装です。

## 実機の主な設定

| 項目 | 現在値 |
|---|---:|
| 駆動方式 | 差動二輪 (`DiffDrive`) |
| 車輪直径 / 円周 | 200 mm / 0.6283 m |
| トレッド幅 | 0.435 m |
| エンコーダ | 950 pulse/車輪1回転 |
| Roboteq odom配信 | 50 Hz |
| Nav2フットプリント | 前0.425 m、後0.475 m、左右0.33 m（全長0.90 x 全幅0.66 m） |
| Nav2最大前進速度 | 0.90 m/s |
| Nav2最大角速度 | 0.90 rad/s |
| 後退方針 | 後退可能、DWB `PreferForward`で前進を強く優先 |
| Nav2入力LaserScan | `/scan3` |
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
koko_roboteq       # Roboteq + ココちゃんURDF
koko_velodyne      # VLP-16。/velodyne_points、/scan、複数リング合成/scan3
koko_imu           # IMU
koko_sf_real       # /odom + /imu -> /odom/filtered、odom TF
koko_twist_mux     # Nav2/keyop2の速度指令を /cmd_vel に統合
koko_nav2_real     # 地図を選択してNav2のみ起動
koko_nav2_real_slam # 地図を生成・更新しながらNav2を起動
koko_rviz_real     # RVizのみ
koko_keyop2        # 必要な場合のみ
koko_foxglove      # 必要な場合のみ。Foxglove WebSocketサーバー
```

`koko_nav2_real_slam` はmap serverとAMCLを起動せず、SLAM Toolboxが `/map` と `map -> robot/odom` を供給します。地図を残す場合は走行後に `koko_map_save` を実行します。

ランチャーの「実機基本」プリセットはRoboteq、VLP-16、IMU、EKF、twist_muxを起動します。「SLAMしながら自律移動（実機）」プリセットは、それらに `koko_nav2_real_slam` とRVizを加えてまとめて起動します。

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
ros2 topic hz /scan3
ros2 run tf2_ros tf2_echo robot/odom robot/base_footprint
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
| `params/real/` | 実機用Nav2・SLAM・twist_mux・Roboteq・IMU・EKF・Velodyne設定 |
| `params/sim/` | シミュレーション用Nav2・SLAM・twist_mux・点群変換設定 |
| `params/common/` | 実機・シミュレーション共通のキーボード操作・Foxglove設定 |
| `src/robotbase_bringup/` | ココちゃん専用URDF、RViz、実機起動launch |
| `src/robotbase_sim/` | Gazebo SimとVLP-16/IMUの模擬センサー |
| `src/robotbase_keyop/` | 実機・シミュレーション共通のキーボード手動操作 |
| `rviz/` | Save Configを次回起動へ引き継ぐTF接頭辞別RViz設定 |
| `src/sirius/` | 移植元コード。現在の主要launch/paramsの正本ではない |
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
- [実機PCへの移行・初回試験](DOCS/REAL_PC_MIGRATION.md)
- [構成、データフロー、SIRIUSとの差分](DOCS/ARCHITECTURE.md)
- [Nav2無走行の原因候補と切り分け](DOCS/NAV2_NO_MOTION.md)
- [設定の正本と既知の課題](DOCS/CONFIGURATION.md)
- [Gazeboシミュレータの構成と使い方](DOCS/SIMULATION.md)
- [ココちゃんBash・ランチャー・通信分離](DOCS/LAUNCHER.md)
- [Foxglove Bridgeの接続と設定](DOCS/FOXGLOVE.md)
- [SLAM Toolbox設定とSIRIUSとの差分](DOCS/SLAM_TOOLBOX.md)

## ビルド

```bash
cd ~/robotbase_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -riy
colcon build --symlink-install --executor sequential --allow-overriding nav2_costmap_2d
source install/setup.bash
```

このチェックアウトでは `build/`、`install/`、`log/` はGit管理対象外です。設定変更後は必ず再ビルドし、起動ターミナルで `install/setup.bash` を読み直してください。
