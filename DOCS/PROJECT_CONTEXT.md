# Project Context

将来の開発者やAIが、ソース全体を再探索せず作業を始めるための短いコンテキストです。

## 一文で

`robotbase_ws` はSIRIUS用ROS 2 Jazzyワークスペースを、新しいRoboteq駆動の差動二輪ロボットへ移植中のワークスペースである。

## 現在地

- 基準日: 2026-08-19
- Git: `master`、確認時HEAD `ae53c76`
- 手動走行: 成功
- `keyop2`: 成功
- Nav2グローバルパス生成: 成功
- Nav2実走行: 未成功。経路表示後に動き始めない
- 実機ログ・rosbag: このチェックアウトにはなし
- 原因: 未確定。最優先でRT権限と速度トピック境界を確認する

## ロボット固有値

- 駆動: 差動二輪
- 車輪: 直径200 mm、円周0.6283 m
- トレッド: 0.435 m
- エンコーダ: 950 pulse/回転
- Roboteq速度入力: `/cmd_vel` (`geometry_msgs/msg/Twist`)
- 生オドメトリ: `/odom`
- EKFオドメトリ: `/odom/filtered`
- Nav2 base frame: `sirius3/base_footprint`
- Nav2 odom frame: `sirius3/odom`
- 2D LiDAR: `/scan`
- 3D LiDAR: `/velodyne_points`（現在の実機Nav2ではSTVLプラグイン自体が無効）

## 速度指令

```text
/cmd_vel_nav (controller_server)
  -> /cmd_vel_smoothed (velocity_smoother)
  -> /cmd_vel (twist_mux)
  -> roboteq_ros2_driver
```

手動優先入力は `/cmd_vel_teleop`、直通優先入力は `/cmd_vel_direct`。`twist_mux` の優先度は teleop 100、direct 90、navigation 10、idle 0。`/stop` は255。

`collision_monitor` の `cmd_vel_collision_in/out` はどこにも接続されておらず、主経路は衝突監視を迂回している。

## Nav2無走行で最初に見る箇所

1. `params/nav2_params.yaml` の `controller_server.use_realtime_priority: true`
2. `src/navigation2/nav2_util/include/nav2_util/simple_action_server.hpp` のFollowPathスレッド開始
3. `src/navigation2/nav2_util/src/node_utils.cpp` の `sched_setscheduler()` 例外
4. `src/navigation2/nav2_bringup/launch/navigation_launch.py` の `cmd_vel -> cmd_vel_nav` リマップ
5. `src/sirius/sirius_navigation/config/twist_mux.yaml`
6. `src/roboteq_ros2_jazzy_driver/roboteq_ros2_driver/config/roboteq.yaml`

## 起動上の重要事項

- `nav2_real` はNav2だけを起動し、`twist_mux` は起動しない
- `keyop2` は `/cmd_vel_teleop` へ出すため、動作したなら試験時に `twist_mux` が動いていた可能性が高い
- 通常の `sirius_controller` は非アシスト時に `/cmd_vel` へ直接出せるため、その成功だけではNav2経路の健全性を証明しない
- `roboteq` エイリアスは `pub_odom_tf:=false`。`sf_real` が `sirius3/odom -> sirius3/base_footprint` を配信する前提
- Nav2 controller、velocity smoother、BT navigatorは `/odom/filtered` を使う

## SIRIUSから変わった主な点

- 車輪円周: 0.825 -> 0.6283 m
- トレッド: 0.40 -> 0.435 m
- pulse: 475 -> 950
- odom配信: 20 -> 50 Hz
- 右左エンコーダ符号を明示
- Nav2フットプリントを約1.20 x 0.70 mから0.85 x 0.56 mへ縮小
- 2D LiDAR入力を `scan3`/`hokuyo_scan` から `/scan` へ統一
- SAM3障害物入力を実機Nav2設定から除外
- MPPIを実機CPU向けに軽量化し `DiffDrive` を維持

## 調査範囲を狭める原則

- 最初にルートREADMEとこのファイルを読む
- 実機問題は `/cmd_vel_nav` から順に境界観測する
- `src/navigation2/` は上流コードを含むため、該当シンボルが分かるまで全体探索しない
- ロボット固有変更は原則 `params/`、`src/sirius/`、`src/roboteq_ros2_jazzy_driver/`、`bash/` を先に見る
