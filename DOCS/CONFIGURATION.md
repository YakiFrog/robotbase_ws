# 設定の正本

## 正本一覧

現在使うロボット固有設定は `src/robotbase_bringup/` に集約した。ルート `params/` にあったSIRIUS由来のNav2/SLAM/EKF複製は削除済み。

| 対象 | 正本 |
|---|---|
| 機体表示名・ROS/Gazebo分離・TF接頭辞 | `robot.env` |
| URDF | `src/robotbase_bringup/urdf/robotbase.urdf` |
| RViz | `src/robotbase_bringup/rviz/robotbase.rviz` |
| Nav2（実機/シミュ共通） | `src/robotbase_bringup/config/nav2.yaml` |
| SLAM Toolbox（実機/シミュ共通） | `src/robotbase_bringup/config/slam_toolbox.yaml` |
| EKF | `src/robotbase_bringup/config/ekf.yaml` |
| Roboteq | `src/robotbase_bringup/config/roboteq.yaml` |
| IMU | `src/robotbase_bringup/config/imu.yaml` |
| twist_mux | `src/robotbase_bringup/config/twist_mux.yaml` |
| Gazeboモデル | `src/robotbase_sim/models/robotbase.sdf` |
| 実機Nav2地図選択 | `bash/startup_bash/nav2_bringup_real.sh` |

## 機体識別とTF

`robot.env` の既定値:

```bash
ROBOTBASE_DISPLAY_NAME="ココちゃん"
ROBOTBASE_ID="koko"
ROBOTBASE_ROS_DOMAIN_ID="57"
ROBOTBASE_GZ_PARTITION="koko"
ROBOTBASE_TF_PREFIX="robot"
```

表示名とTF接頭辞は独立している。TFは既定で次の構造になる。

```text
map
└─ robot/odom
   └─ robot/base_footprint
      ├─ robot/base_link
      ├─ robot/lidar_link
      └─ robot/imu_link
```

接頭辞を変える場合は `ROBOTBASE_TF_PREFIX` だけを変更し、全プロセスを再起動する。alias経由ではGazebo、URDF、各driver、EKF、SLAM、Nav2、RVizへ同じ値が渡る。

## Nav2

実機とシミュレータは同じ `nav2.yaml` を使い、launch引数で差分だけを上書きする。

| 項目 | シミュレーション | 実機 |
|---|---|---|
| `use_sim_time` | `true` | `false` |
| localization | 固定 `map -> robot/odom` | AMCL |
| odometry | `/odom` | `/odom/filtered` |
| LaserScan | `/scan` | `/scan` |

起動するNav2ノードはcontroller、planner、smoother、behavior、BT navigator、velocity smoother、map serverと、実機時のAMCLだけ。Route、Docking、Waypoint Follower、Loopback Simulator、Collision Monitorは現在の用途から外した。

設定の要点:

| 項目 | 値 |
|---|---:|
| controller | DWB / DiffDrive |
| controller frequency | 10 Hz |
| `use_realtime_priority` | `false` |
| 最大前進速度 | 0.90 m/s |
| 最大後退速度 | -0.30 m/s |
| 最大角速度 | 0.90 rad/s |
| footprint | 前0.40、後0.45、左右0.28 m |
| local costmap | 6 x 6 m、0.05 m/cell |
| obstacle source | `/scan` のみ |

ZED、SAM3、Hokuyo、semantic layer、STVL、`/scan3` は含まない。VLP-16点群は `velodyne_laserscan` により `/scan` へ変換して使う。

## SLAM Toolbox

実機/シミュ共通設定は1ファイルで、時刻とTFだけをlaunchで切り替える。入力は `/scan`、出力TFは `map -> <prefix>/odom`。

```bash
koko_slamtoolbox_sim   # use_sim_time=true
koko_slamtoolbox_real  # use_sim_time=false
```

## 速度経路

```text
controller_server /cmd_vel_nav
  -> velocity_smoother /cmd_vel_smoothed
  -> twist_mux /cmd_vel
  -> roboteq_ros2_driver
```

twist_mux優先度:

| 入力 | priority |
|---|---:|
| `/stop` lock | 255 |
| `/cmd_vel_teleop` | 100 |
| `/cmd_vel_direct` | 90 |
| `/cmd_vel_smoothed` | 10 |
| `/cmd_vel_idle` | 1 |

Nav2とtwist_muxは別コマンドである。実機Nav2試験では `koko_twist_mux` の起動を確認する。

## 削除した旧設定

次はSIRIUS由来で、現在の構成では不要なため削除した。

- `params/nav2_params*.yaml` と各bak
- `params/mapper_params_online_async*.yaml`
- `params/ekf_fusion.yaml`、`imu_filter.yaml`、`keepout_params.yaml`
- ZED/SAM3/RTAB-MAP起動スクリプト
- semantic/STVL、Hokuyo、docking、loopbackのパラメータ
- MPPI走行モード切替スクリプト

## 変更後チェック

```bash
source ~/robotbase_ws/install/setup.bash
ros2 pkg prefix robotbase_bringup
ros2 pkg prefix robotbase_sim
ros2 launch robotbase_bringup nav2.launch.py --show-args
ros2 launch robotbase_bringup slam.launch.py --show-args
```

実機寸法を変えた場合はURDF、SDF、Roboteqの車輪値、Nav2 footprintを同時に更新する。センサー取付位置を変えた場合はURDFとSDFを同時に更新する。
