# Project Context

将来の開発者やAIが、ソース全体を再探索せず作業を始めるための短いコンテキスト。

## 一文で

`robotbase_ws` は、VLP-16とIMUを搭載するRoboteq駆動の差動二輪ロボット「ココちゃん」用ROS 2 Jazzyワークスペース。

## 現在地（2026-08-19）

- 実機手動走行、`keyop2`: 成功
- 旧Nav2: RVizにパスは出たが実機が動かなかった
- 旧設定の最有力原因: `use_realtime_priority: true` と実機OS権限
- 新Nav2: 専用最小設定へ置換し `use_realtime_priority: false`、実機再試験待ち
- Gazebo SLAM: 動作確認済み
- Gazebo Nav2: `params/sim/`、分離launch、`robot/*` TFで `(4, 0)` 到達、`SUCCEEDED`
- 実機ログ/rosbag: このチェックアウトにはなし

## 正本

最初に見る場所:

1. `README.md`
2. `src/robotbase_bringup/` — URDF、RViz、全ロボット固有params/launch
3. `src/robotbase_sim/` — Gazeboだけ
4. `bash/bash_alias2.sh` — ランチャーのボタン定義
5. `DOCS/NAV2_NO_MOTION.md` — 実機切り分け

ルート `params/` の旧Nav2/SLAM/EKF設定は削除済み。SIRIUS由来の `sirius_description` はRVizから呼ばない。

## ロボット固有値

- 車輪直径/円周: 0.20 / 0.6283 m
- トレッド: 0.435 m
- encoder: 950 pulse/回転
- footprint: 前0.40、後0.45、左右0.28 m
- 生odom: `/odom`
- EKF odom: `/odom/filtered`
- PointCloud2: `/velodyne_points`
- LaserScan: `/scan`
- IMU: `/imu`
- TF: `map -> robot/odom -> robot/base_footprint`

TFの `robot` は `robot.env` の `ROBOTBASE_TF_PREFIX` で変更可能。表示名「ココちゃん」とは独立。

## 起動コマンド

シミュレーション:

```bash
koko_sim
koko_rviz_sim
koko_slamtoolbox_sim  # 地図作成のみ
koko_nav2_sim_map     # 既存地図でNav2
koko_nav2_sim_slam    # 地図なし、SLAM + Nav2
```

実機:

```bash
koko_roboteq
koko_velodyne
koko_imu
koko_sf_real
koko_twist_mux
koko_rviz_real
koko_slamtoolbox_real # 地図生成時
koko_nav2_real        # 自律移動時
koko_nav2_real_slam   # 地図を生成・更新しながら自律移動
```

GazeboとRVizは別プロセス。`koko_nav2_sim_slam` と `koko_nav2_real_slam` はSLAMとNav2を同時起動する。シミュレーションの `twist_mux` は `koko_sim` に含まれるが、実機では `koko_twist_mux` を別途起動する。

## 速度指令

```text
/cmd_vel_nav
  -> velocity_smoother
  -> /cmd_vel_smoothed
  -> twist_mux
  -> /cmd_vel
  -> roboteq_ros2_driver
```

手動入力 `/cmd_vel_teleop` はNav2より高優先度。idleは1、`/stop` lockは255。lockが残っていてもNav2は動かない。

## Nav2無走行で最初に確認

```bash
ros2 lifecycle get /controller_server
ros2 topic hz /cmd_vel_nav
ros2 topic hz /cmd_vel_smoothed
ros2 topic hz /cmd_vel
ros2 topic hz /odom/filtered
ros2 topic hz /scan
ros2 run tf2_ros tf2_echo robot/odom robot/base_footprint
```

最初に途切れる境界が原因箇所。新設定ではRT優先度を無効化済みなので、次はtwist_mux、`/stop`、odom/scan/TF更新を優先して見る。

## 含めないもの

ココちゃんの有効なUI、alias、Nav2/SLAM paramsには次を含めない。

- ZED、SAM3、RTAB-MAP
- Hokuyo、`/scan3`、`/hokuyo_scan`
- LLM dynamic goal、status monitor、BLE gateway
- semantic costmap、STVL
- 外部連携タブ

上流または移植元ソースが `src/sirius/` に残っていても、新しいbringupから参照しない。

`src/sirius/` は `COLCON_IGNORE` によりビルド対象外。実機PCへのclone、依存導入、udev、VLP-16 NIC、段階試験は `DOCS/REAL_PC_MIGRATION.md` を正本とする。
