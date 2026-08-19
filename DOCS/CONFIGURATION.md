# 設定の正本

## 正本一覧

現在使うロボット固有パラメータは、プロジェクト直下の `params/` に集約した。上流パッケージの `src/navigation2/`、`src/slam_toolbox/`、`src/velodyne/` にある既定ファイルは編集しない。

| 対象 | 正本 |
|---|---|
| 機体表示名・ROS/Gazebo分離・TF接頭辞 | `robot.env` |
| URDF | `src/robotbase_bringup/urdf/robotbase.urdf` |
| RViz | `src/robotbase_bringup/rviz/robotbase.rviz` |
| Nav2（実機） | `params/real/nav2.yaml` |
| Nav2（シミュレーション） | `params/sim/nav2.yaml` |
| SLAM Toolbox（実機 / シミュ） | `params/real/slam_toolbox.yaml` / `params/sim/slam_toolbox.yaml` |
| twist_mux（実機 / シミュ） | `params/real/twist_mux.yaml` / `params/sim/twist_mux.yaml` |
| EKF・Roboteq・IMU | `params/real/ekf.yaml`、`roboteq.yaml`、`imu.yaml` |
| Velodyne VLP-16 | `params/real/velodyne.yaml`、`VLP16db.yaml` |
| シミュレーション点群変換・停止速度 | `params/sim/velodyne_laserscan.yaml`、`idle_twist.yaml` |
| キーボード手動操作（共通） | `params/common/keyop.yaml` |
| Foxglove Bridge（共通） | `params/common/foxglove.yaml`、待受先は`robot.env` |
| Gazeboモデル | `src/robotbase_sim/models/robotbase.sdf` |
| 実機Nav2地図選択 | `bash/startup_bash/nav2_bringup_real.sh` |

RVizの配布用テンプレート `src/robotbase_bringup/rviz/robotbase.rviz` にはNav2標準のNavigation 2パネル、Global/Local Costmap、Global/Local Plan、Local Footprint表示を登録している。通常起動ではTF接頭辞ごとの `rviz/robotbase_<prefix>.rviz` を使い、RVizの通常のSave Configを次回起動へ引き継ぐ。

## 機体識別とTF

`robot.env` の既定値:

```bash
ROBOTBASE_DISPLAY_NAME="ココちゃん"
ROBOTBASE_ID="koko"
ROBOTBASE_ROS_DOMAIN_ID="57"
ROBOTBASE_GZ_PARTITION="koko"
ROBOTBASE_TF_PREFIX="robot"
ROBOTBASE_FOXGLOVE_ADDRESS="0.0.0.0"
ROBOTBASE_FOXGLOVE_PORT="8766"
```

alias経由では `ROBOTBASE_PARAMS_DIR=~/robotbase_ws/params` も設定される。直接launchした場合も同じ場所を既定値として使う。

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

実機は `params/real/nav2.yaml`、シミュレータは `params/sim/nav2.yaml` を使う。両方を別々に調整でき、現在の主要差分は次のとおり。

| 項目 | シミュレーション | 実機 |
|---|---|---|
| `use_sim_time` | `true` | `false` |
| localization | AMCL（既定）、固定TF（試験用オプション） | AMCL |
| odometry | `/odom` | `/odom/filtered` |
| LaserScan | `/scan3` | `/scan3` |

起動するNav2ノードはcontroller、planner、smoother、behavior、BT navigator、velocity smoother、map server、AMCL。Route、Docking、Waypoint Follower、Loopback Simulator、Collision Monitorは現在の用途から外した。シミュレーションでも既存地図モードの既定はAMCLなので、RVizの `2D Pose Estimate` が `/initialpose` を通して有効になる。経路制御だけを再現性優先で試す場合は `localization:=static` を明示できる。

設定の要点:

| 項目 | 値 |
|---|---:|
| controller | MPPI / DiffDrive |
| controller frequency | 10 Hz |
| prediction horizon | 2.8秒（`28 x 0.10`秒） |
| `use_realtime_priority` | `false` |
| 最大前進速度 | 0.90 m/s |
| 最大後退速度 | -0.30 m/s |
| 最大角速度 | 0.90 rad/s |
| 実機の前後速度不感帯 | 0.10 m/s（MPPI評価・odom判定・velocity smoother） |
| footprint | 前0.425、後0.475、左右0.33 m（全長0.90 x 全幅0.66 m） |
| local costmap | 6 x 6 m、0.05 m/cell |
| obstacle source | `/scan3` のみ |
| scan obstacle height | 0.0〜2.0 m（source単位で明示） |
| 後退 | `vx_min: -0.30`で脱出用に許可、`PreferForwardCritic`で通常走行は前進優先 |
| 衝突評価 | `CostCritic.consider_footprint: true`で長方形footprint全体を評価 |

ZED、SAM3、Hokuyo、semantic layer、STVLは含まない。VLP-16点群は `velodyne_laserscan` により複数リング合成 `/scan3` へ変換して使う。単一リング `/scan` も配信されるが、Nav2とSLAM Toolboxの入力には使わない。

Nav2 JazzyのObstacleLayerは、plugin全体とは別に観測source `scan.max_obstacle_height` を持ち、未指定時は `0.0` mになる。これをglobal/local costmapの両方で `2.0` mへ明示している。未指定に戻すと、床より高いVLP-16由来のLaserScan点が全件破棄され、local costmapが全セル0になる。

MPPIの予測時間は2.8秒とする。最大速度0.9 m/sでの予測移動量は2.52 mで、半径3 mのlocal costmap内に車体外形まで収まる。旧6秒設定は5.4 m先まで予測しようとしてcostmap外へ達し、空き領域で低速周回する原因になっていた。

`PreferForwardCritic.cost_weight: 40.0`で、通常走行では後退より向き直って前進する軌道を強く優先する。`vx_min: -0.30`は維持しているため、前進軌道が成立しない場合やRecoveryのbackupでは後退できる。シミュレーションの後方ゴール試験で最大後退を約`-0.027 m/s`まで抑えた。

障害物は`CostCritic.cost_weight: 4.0`、`consider_footprint: true`、`collision_cost: 1000000.0`で評価する。旧weight 10はinflation領域へ入るコストが強すぎ、経路より空き領域の周回を選びやすかった。重みを下げても、長方形footprintが接触する軌道には100万コストが付くため、衝突禁止判定は維持される。

実機は前後速度の絶対値が`0.10 m/s`未満では動かない前提とする。実機用MPPIだけに`VelocityDeadbandCritic`を追加して微小速度の軌道へコストを付け、`controller_server.min_x_velocity_threshold: 0.10`で同範囲のodomを停止として扱う。さらに`velocity_smoother.deadband_velocity: [0.10, 0.0, 0.0]`で、加減速途中や停止直前の無効な前後指令を0へ丸める。シミュレーション用は物理モデルとの比較を崩さないため0のままにしている。角速度の不感帯は未計測なので設定していない。

## SLAM Toolbox

実機は `params/real/slam_toolbox.yaml`、シミュレータは `params/sim/slam_toolbox.yaml` を使う。入力は `/scan3`、出力TFは `map -> <prefix>/odom`。

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
- 旧MPPI走行モード切替スクリプト（現在は標準設定がMPPI）

`src/robotbase_bringup/config/` の複製も廃止し、`params/` だけを正本にした。実機とシミュレーションの差分確認例:

```bash
diff -u params/real/nav2.yaml params/sim/nav2.yaml
diff -u params/real/slam_toolbox.yaml params/sim/slam_toolbox.yaml
```

## 変更後チェック

```bash
source ~/robotbase_ws/install/setup.bash
ros2 pkg prefix robotbase_bringup
ros2 pkg prefix robotbase_sim
ros2 launch robotbase_bringup nav2.launch.py --show-args
ros2 launch robotbase_bringup slam.launch.py --show-args
```

実機寸法を変えた場合はURDF、SDF、Roboteqの車輪値、Nav2 footprintを同時に更新する。センサー取付位置を変えた場合はURDFとSDFを同時に更新する。
