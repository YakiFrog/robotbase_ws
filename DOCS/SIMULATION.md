# Robotbase Gazeboシミュレータ

## 目的と確認済み範囲

`src/robotbase_sim/` は、実機がなくても次を確認するための最小構成です。

- 差動二輪の手動走行
- Velodyne VLP-16相当の3D点群と、点群から変換した2D `/scan`
- IMUデータ
- slam_toolboxによる2D地図生成
- 同梱地図を使ったNav2の経路生成、障害物回避、速度指令、ゴール到達

2026-08-19にヘッドレス実行で確認した結果は次のとおりです。

| 確認項目 | 結果 |
|---|---|
| `/odom` | 約50 Hz |
| `/velodyne_points` / `/scan` | 点群配信あり / 約10 Hz |
| `/imu` | 約100 Hz |
| slam_toolbox | Lifecycle `active`、`map -> base` TFと `/map` を確認 |
| Nav2 | 管理ノードすべて `active` |
| 自律走行 | `(0, 0)`から障害物を迂回して`(4, 0)`へ到達、`SUCCEEDED` |
| 到着姿勢 | odom位置 `(4.076, -0.075)` |
| 停止 | 完了後の `/cmd_vel` がゼロ |

## 初回ビルド

```bash
cd ~/robotbase_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -riy
colcon build --symlink-install --packages-select robotbase_sim
source install/setup.bash
```

このワークスペースのNav2やslam_toolboxをまだビルドしていない場合、それらは読み込まれているunderlayのものを使います。本番に近い組み合わせを固定したい場合は、ルートREADMEの全体ビルドを実行してください。

必要な主な実行パッケージは `ros_gz_sim`、`ros_gz_bridge`、`twist_mux`、`velodyne_laserscan`、`slam_toolbox`、`nav2_bringup`、`rviz2` です。依存関係の正本は `src/robotbase_sim/package.xml` です。

## 起動方法

### センサーと手動走行だけ

```bash
ros2 launch robotbase_sim sim.launch.py
```

別ターミナルから次のように動かせます。

```bash
ros2 topic pub --rate 10 /cmd_vel_teleop geometry_msgs/msg/Twist \
  '{linear: {x: 0.25}, angular: {z: 0.3}}'
```

停止は発行側で `Ctrl-C` です。`idle_twist_publisher` が自動的にゼロ指令へ戻します。

### SLAMで地図生成

```bash
ros2 launch robotbase_sim mapping.launch.py
```

RVizの地図を見ながら `/cmd_vel_teleop` で走行します。保存例:

```bash
mkdir -p ~/robotbase_ws/sim_maps
ros2 run nav2_map_server map_saver_cli \
  -f ~/robotbase_ws/sim_maps/robotbase_arena
```

`robotbase_arena.yaml` と画像ファイルが生成されます。

### Nav2自律移動

```bash
# 同梱のtest_arena地図
ros2 launch robotbase_sim navigation.launch.py

# SLAMで保存した任意地図
ros2 launch robotbase_sim navigation.launch.py \
  map:=$HOME/robotbase_ws/sim_maps/robotbase_arena.yaml
```

RVizの「Nav2 Goal」でゴールを指定します。同梱地図はGazeboワールドと一致し、開始位置は `(0, 0, 0)` です。CLIで確認済みゴールを再現する場合:

```bash
ros2 action send_goal /navigate_to_pose \
  nav2_msgs/action/NavigateToPose \
  '{pose: {header: {frame_id: map}, pose: {position: {x: 4.0, y: 0.0}, orientation: {w: 1.0}}}}'
```

### GUIなし

CIやリモート端末では次を使用します。

```bash
ros2 launch robotbase_sim mapping.launch.py gui:=false rviz:=false
ros2 launch robotbase_sim navigation.launch.py gui:=false rviz:=false
```

`bash/bash_alias2.sh` を読み込んでいれば次の短縮名も使えます。

| alias | 起動内容 |
|---|---|
| `robotbase_sim` | Gazebo、ロボット、センサー、twist_mux |
| `robotbase_mapping` | 上記 + slam_toolbox + RViz |
| `robotbase_nav` | 上記 + 地図サーバー + Nav2 + RViz |

## モデルの前提

| 項目 | 値 |
|---|---:|
| 駆動 | 差動二輪 + 前後キャスター |
| 車輪直径 | 0.20 m |
| トレッド幅 | 0.435 m |
| 車体外形 | 約0.85 x 0.56 m |
| VLP16取付位置 | `base_footprint`から `(0, 0, 0.72)` m |
| IMU取付位置 | `base_footprint`から `(0, 0, 0.28)` m |
| VLP16 | 水平720点、垂直16 ring、上下±15度、10 Hz |
| 2D scan | ring 8を `/scan` へ変換 |
| IMU | 100 Hz、簡易Gaussian noise付き |

センサーの実取付位置が判明したら、SDFとURDFの両方を同じ値へ変更します。

- 物理・センサー: `src/robotbase_sim/models/robotbase.sdf`
- RViz/TF用モデル: `src/robotbase_sim/urdf/robotbase.urdf`

## TF設計

### 地図生成モード

```text
map                         slam_toolboxが推定
└─ sirius3/odom             Gazeboの開始原点
   └─ sirius3/base_footprint  Gazebo DiffDriveの動的TF
      ├─ sirius3/base_link
      ├─ sirius3/lidar_link
      └─ sirius3/imu_link
```

### Nav2モード

```text
map                         固定identity TF（真値ローカライゼーション）
└─ sirius3/odom
   └─ sirius3/base_footprint
      ├─ sirius3/base_link
      ├─ sirius3/lidar_link
      └─ sirius3/imu_link
```

Nav2モードでAMCLを使わない理由は、簡易環境で経路計画・制御・速度トピックを安定して試すためです。VLP16の単一ringから得る2D scanだけでAMCLを使う試験では、長距離走行時にGazebo真値から大きくずれることを確認しました。位置推定そのものを評価したい場合は、固定TFを外してAMCLまたはEKFを別途構成してください。

実機側と同じ `sirius3/*` 名を採用しています。変更する場合、最低でもSDF、URDF、SLAM設定、Nav2のフレーム上書きを同時に直す必要があります。

## トピック経路

センサー:

```text
Gazebo VLP16 -> /velodyne_points -> velodyne_laserscan -> /scan
Gazebo IMU   -> /imu
Gazebo DiffDrive -> /odom + odom TF
```

Nav2速度指令:

```text
controller_server
  -> /cmd_vel_nav
  -> velocity_smoother
  -> /cmd_vel_smoothed
  -> collision_monitor
  -> /cmd_vel_safe
  -> twist_mux
  -> /cmd_vel
  -> Gazebo DiffDrive
```

優先度はteleop 100、direct 90、navigation 10、idle 1、`/stop` lock 255です。実機の既知課題と異なり、このシミュレータではcollision monitorを速度経路へ接続済みです。また `controller_server.use_realtime_priority` は権限に依存しないよう無効化します。

## 最短の診断

```bash
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu
ros2 run tf2_ros tf2_echo sirius3/odom sirius3/base_footprint
ros2 run tf2_ros tf2_echo sirius3/base_footprint sirius3/lidar_link
```

Nav2ゴール中:

```bash
ros2 lifecycle get /controller_server
ros2 lifecycle get /planner_server
ros2 lifecycle get /collision_monitor
ros2 topic hz /cmd_vel_nav
ros2 topic hz /cmd_vel_smoothed
ros2 topic hz /cmd_vel_safe
ros2 topic hz /cmd_vel
```

最初に止まった境界を調べます。Nav2モードで `map -> sirius3/odom` がない場合は `map_to_sim_odom`、地図生成モードで同じTFがない場合は `/slam_toolbox` のLifecycleと `/scan` を確認します。

## ファイル一覧

| パス | 役割 |
|---|---|
| `launch/sim.launch.py` | Gazebo、bridge、TF、VLP16変換、twist_mux |
| `launch/mapping.launch.py` | sim + slam_toolbox + RViz |
| `launch/navigation.launch.py` | sim + 地図 + 真値localization + Nav2 + RViz |
| `models/robotbase.sdf` | 物理モデル、VLP16、IMU、DiffDrive plugin |
| `urdf/robotbase.urdf` | robot_state_publisher用の固定TFと表示モデル |
| `worlds/test_arena.sdf` | 外周壁と複数障害物を持つ試験場 |
| `maps/test_arena.yaml` | Nav2用の同梱地図 |
| `config/slam_toolbox.yaml` | 2D SLAM設定 |
| `config/twist_mux.yaml` | 手動/Nav2/停止の速度優先順位 |
| `rviz/robotbase.rviz` | SLAM/Nav2共通RViz設定 |

## 現在の制約

- IMUは配信確認用で、現在のオドメトリには融合していません。
- Nav2モードは真値ローカライゼーションのため、AMCL性能は評価しません。
- VLP16はGPU lidarによる近似で、実機固有のpacket timingやdriver遅延は再現しません。
- 接触、スリップ、エンコーダ誤差は簡略化されています。
- GUI環境によってEGL警告が出ても、ヘッドレス実行とROSトピックが動作する場合があります。
