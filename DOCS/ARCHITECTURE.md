# システム構成

## 1. 目的と移植方針

このワークスペースは [`sirius_jazzy_ws`](../../sirius_jazzy_ws) の構成を基礎にしつつ、新しい実機の車体とセンサーに合わせて調整している。

再利用している考え方は次のとおり。

- ROS 2 Jazzy
- Roboteqモータコントローラ
- 差動二輪運動モデル
- ホイールオドメトリとIMUのEKF統合
- AMCL + Nav2による地図ベースの自律移動
- `twist_mux` による手動操作と自律操作の優先順位付け

車体・センサー依存値はSIRIUSからそのまま使わず、`roboteq.yaml`、`nav2_params.yaml`、センサードライバ設定で置き換える方針である。

## 2. ソースパッケージ

### ロボット固有

| パッケージ | 役割 |
|---|---|
| `sirius_description` | URDF/SDF、RViz、Gazebo/Unity連携。名称はSIRIUSのまま |
| `sirius_interfaces` | キーボード・コントローラ入力、音声アクション |
| `sirius_keyop` | キーボード、外部コントローラ、`keyop2` |
| `sirius_navigation` | センサ融合、目標操作、速度mux、補助操作、各種起動 |
| `roboteq_ros2_driver` | `/cmd_vel` を左右輪指令へ変換し、`/odom` を配信 |

### ワークスペース内で保持する上流パッケージ

| ディレクトリ | 役割 |
|---|---|
| `src/navigation2` | Nav2本体。`navigation_launch.py` にロボット固有の速度リマップあり |
| `src/slam_toolbox` | 2D SLAM |
| `src/velodyne` | 3D LiDAR |
| `src/witmotion_ros` | WitMotion IMU |

### 外部またはapt導入を前提とする主な実行時パッケージ

- `robot_localization`
- `twist_mux`
- 2D LiDARドライバ（エイリアスは `urg_node2` を起動するが、ソースはこのWS内にない）
- `rtabmap_*`、`rosbridge_*` など一部の旧SIRIUS機能

`sirius_navigation/package.xml` にはRTAB-Map依存が残っている一方、RTAB-Mapソースはこのワークスペースから削減されている。apt導入で満たすか、使用しない機能の依存を今後整理する必要がある。

## 3. 実機データフロー

### 3.1 センサーと自己位置

```text
Roboteq encoders
  -> roboteq_ros2_driver
  -> /odom
             \
              -> robot_localization EKF -> /odom/filtered
             /
IMU -> /imu

/scan + map + odom/base TF
  -> AMCL
  -> map -> sirius3/odom TF
```

TFの責務は次の分担を想定する。

| TF | 配信元 |
|---|---|
| `map -> sirius3/odom` | AMCL |
| `sirius3/odom -> sirius3/base_footprint` | `robot_localization` EKF |
| `base_footprint -> sensor frame` | robot descriptionまたはセンサ起動 |

`roboteq` エイリアスは `pub_odom_tf:=false` を渡す。EKFとRoboteqが同じTFを二重配信しないためである。EKFを使わない単体試験では `roboteq_no_sf` が `pub_odom_tf:=true` を使用する。

### 3.2 Nav2速度指令

```text
RViz / NavigateToPose client
  -> bt_navigator
  -> planner_server                    /plan
  -> controller_server (MPPI)          /cmd_vel_nav
  -> velocity_smoother                 /cmd_vel_smoothed
  -> twist_mux                         /cmd_vel
  -> roboteq_ros2_driver
  -> Roboteq controller / motors
```

この接続は次のファイルで定義される。

| 境界 | 定義 |
|---|---|
| controllerの`cmd_vel`を`cmd_vel_nav`へ | `src/navigation2/nav2_bringup/launch/navigation_launch.py` |
| smootherの入力`cmd_vel`を`cmd_vel_nav`へ | 同上 |
| smoother出力`cmd_vel_smoothed` | Nav2 velocity smoother既定値 |
| muxのnavigation入力 | `src/sirius/sirius_navigation/config/twist_mux.yaml` |
| mux出力を`cmd_vel`へ | `src/sirius/sirius_navigation/launch/twist_mux.launch.py` |
| Roboteq入力`cmd_vel` | `src/roboteq_ros2_jazzy_driver/roboteq_ros2_driver/config/roboteq.yaml` |

### 3.3 手動操作と優先順位

```text
keyop2 -----------------> /cmd_vel_teleop -- priority 100 --+
direct assisted input --> /cmd_vel_direct -- priority  90 --+-> twist_mux -> /cmd_vel
Nav2 smoother ----------> /cmd_vel_smoothed priority  10 --+
idle monitor -----------> /cmd_vel_idle --- priority   0 --+
/stop ------------------------------------------------ 255 lock
```

`keyop2` は速度が非ゼロ、または最後の入力から1秒以内の場合のみpublishする。停止キー後もしばらくゼロ速度が高優先度で出るため、Nav2への復帰には最大約1秒かかる。

通常の `sirius_controller` はアシスト無効時に `/cmd_vel` へ直接publishできる。この経路はmuxとNav2 smootherを迂回するので、通常手動操作の成功だけではNav2経路の正常性を判断できない。

## 4. collision_monitorの現状

Nav2 bringupは `collision_monitor` ノードを起動するが、現在の設定は次のとおり。

```text
input:  /cmd_vel_collision_in
output: /cmd_vel_collision_out
```

このinputへpublishするノードも、outputを購読する主走行ノードも設定されていない。現在のNav2指令は `velocity_smoother -> twist_mux` と進むため、collision monitorを通らない。

影響は次の2点。

- 無走行の直接原因ではない。主経路は別に接続されている
- `FootprintApproach` による停止処理が実機指令へ反映されない

将来接続するなら、競合するpublisherを作らず次の一方向に統一する。

```text
/cmd_vel_nav
  -> velocity_smoother
  -> /cmd_vel_smoothed
  -> collision_monitor
  -> /cmd_vel_safe
  -> twist_mux navigation input
  -> /cmd_vel
```

## 5. SIRIUSとの差分

### 5.1 走行系

| 項目 | SIRIUS | robotbase | 影響 |
|---|---:|---:|---|
| 車輪円周 | 0.825 m | 0.6283 m | 速度・移動距離換算 |
| トレッド幅 | 0.40 m | 0.435 m | 角速度・旋回オドメトリ |
| pulse/回転 | 475 | 950 | オドメトリ距離換算 |
| odom publish | 20 Hz | 50 Hz | EKFと制御の更新頻度 |
| 右encoder符号 | 暗黙 | -1.0 | 前進時の符号補正 |
| 左encoder符号 | 暗黙 | +1.0 | 前進時の符号補正 |

### 5.2 Nav2車体・センサー

| 項目 | SIRIUS | robotbase |
|---|---|---|
| global footprint | 約1.20 x 0.70 m | 0.85 x 0.56 m |
| local footprint | 約1.20 x 0.60 m | 0.85 x 0.56 m |
| AMCL scan | `scan3` | `/scan` |
| global obstacle scan | `/scan3` | `/scan` |
| local obstacle scan | `/hokuyo_scan` | `/scan` |
| SAM3 obstacle input | 設定あり | 実機Nav2設定から除外 |
| MPPI footprint評価 | `true` | `false` |
| MPPI batch size | 2000 | 800 |

`robotbase` の実機設定ではSTVLの定義は残るが、local costmapの `plugins` リストに含まれないため実行されない。現在のlocal costmapが実際に使う観測源は `/scan` だけである。

## 6. 起動ファイルと設定の対応

| 操作 | 実体 | 主設定 |
|---|---|---|
| `roboteq` | Roboteq launch | `roboteq.yaml` |
| `sf_real` | `sensor_fusion.launch.py use_sim_time:=false` | `params/ekf_fusion.yaml` |
| `twist_mux` | `twist_mux.launch.py` | `config/twist_mux.yaml` |
| `nav2_real` | `bash/startup_bash/nav2_bringup_real.sh` | `params/nav2_params.yaml` |
| `keyop2` | `sirius_keyop_v2` | C++内の速度上限とpublish条件 |
| `nav2` | シミュレーションbringup | `params/nav2_params_sim*.yaml` |

`nav2_real` は地図選択、現在地図状態ファイルの更新、Nav2 bringupだけを行う。センサー、EKF、mux、Roboteqは含まれない。

## 7. ビルドとoverlay

Nav2をソースからワークスペース内でビルドするため、apt版Nav2よりこのoverlayが優先される。実際に参照しているファイルを確認するときは次を使う。

```bash
source ~/robotbase_ws/install/setup.bash
ros2 pkg prefix nav2_bringup
ros2 pkg prefix sirius_navigation
ros2 pkg prefix roboteq_ros2_driver
```

すべて `~/robotbase_ws/install/...` を指すことを確認する。別ワークスペースの `setup.bash` を後からsourceすると、同名パッケージがSIRIUS側へ切り替わる可能性がある。
