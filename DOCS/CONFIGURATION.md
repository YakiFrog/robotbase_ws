# 設定の正本と既知の課題

## 1. 正本

実機動作の判断では、次を正本として扱う。

| 対象 | 正本 |
|---|---|
| Roboteq・車輪・encoder | `src/roboteq_ros2_jazzy_driver/roboteq_ros2_driver/config/roboteq.yaml` |
| Nav2・AMCL・costmap・MPPI | `params/nav2_params.yaml` |
| EKF | `params/ekf_fusion.yaml` |
| mux優先順位 | `src/sirius/sirius_navigation/config/twist_mux.yaml` |
| 実機Nav2起動 | `bash/startup_bash/nav2_bringup_real.sh` |
| コマンド短縮名 | `bash/bash_alias1.sh`、`bash/bash_alias2.sh` |

`params/nav2_params_sim*.yaml` はシミュレーション用であり、実機の原因調査に混ぜない。

## 2. 現在の主要値

### Roboteq

| パラメータ | 値 |
|---|---:|
| `cmdvel_topic` | `cmd_vel` |
| `odom_topic` | `odom` |
| `wheel_circumference` | 0.6283 m |
| `track_width` | 0.435 m |
| `pulse` | 950 |
| `max_rpm` | 58 |
| `max_speed` | 1.5 m/s |
| `odom_publish_hz` | 50 Hz |
| `speed_scale` | 0.52 |
| `kp_soft` | 0.3 |
| `min_speed_threshold` | 0.18 |
| `encoder_sign_r` | -1.0 |
| `encoder_sign_l` | +1.0 |

### Nav2 controller / MPPI

| パラメータ | 値 |
|---|---:|
| controller frequency | 10 Hz |
| controller odom | `/odom/filtered` |
| motion model | `DiffDrive` |
| horizon | 50 x 0.10 s = 5.0 s |
| batch size | 800 |
| `vx_min` / `vx_max` | -0.60 / 0.90 m/s |
| `wz_min` / `wz_max` | -0.90 / 0.90 rad/s |
| `ax_min` / `ax_max` | -0.9 / 0.9 m/s² |
| `az_min` / `az_max` | -1.5 / 1.5 rad/s² |
| `use_realtime_priority` | `true` |

### velocity_smoother

| パラメータ | 値 |
|---|---:|
| frequency | 20 Hz |
| feedback | `OPEN_LOOP` |
| max velocity | `[0.9, 0.0, 0.9]` |
| max accel | `[0.9, 0.0, 1.5]` |
| velocity timeout | 1.0 s |

### costmap / AMCL

| 対象 | 値 |
|---|---|
| base frame | `sirius3/base_footprint` |
| odom frame | `sirius3/odom` |
| footprint | `[[0.40,0.28],[0.40,-0.28],[-0.45,-0.28],[-0.45,0.28]]` |
| AMCL scan | `/scan` |
| global obstacle source | `/scan` |
| local obstacle source | `/scan` |
| local costmap | 6 x 6 m、0.05 m/cell、rolling |
| local inflation | 0.70 m |

### twist_mux

| 入力 | topic | priority | timeout |
|---|---|---:|---:|
| teleop | `/cmd_vel_teleop` | 100 | 0.5 s |
| direct | `/cmd_vel_direct` | 90 | 0.5 s |
| navigation | `/cmd_vel_smoothed` | 10 | 0.5 s |
| idle | `/cmd_vel_idle` | 0 | 0.5 s |
| stop lock | `/stop` | 255 | 0.0 s |

## 3. 既知の不整合

### 3.1 collision_monitorが主経路から外れている

- 設定input: `/cmd_vel_collision_in`
- 設定output: `/cmd_vel_collision_out`
- 実際のNav2出力: `/cmd_vel_smoothed`
- muxのNav2入力: `/cmd_vel_smoothed`

結果としてcollision monitorは起動しても実指令を処理しない。安全設計として接続方針を決める必要がある。

### 3.2 nav2_realがtwist_muxを起動しない

`nav2_bringup_real.sh` は `nav2_bringup bringup_launch.py` だけを起動する。muxを忘れるとNav2は `/cmd_vel_smoothed` までしか届かない。複合bringupを作るか、ランチャープリセットへmuxを含める余地がある。

### 3.3 RT優先度が環境依存

`use_realtime_priority: true` は実機OSの `/etc/security/limits.conf` とログインセッションに依存する。新しいPCへWSだけ移植しても設定は移らない。権限未設定なら `false` で動作確認してからRT設定を導入する。

### 3.4 センサー一覧と実際の有効pluginが一致しにくい

`nav2_params.yaml` にはSTVLと `/velodyne_points` の設定ブロックが残るが、local costmapのpluginリストは `obstacle_layer` と `inflation_layer` のみである。従って現状は `/scan` しか使用しない。

コメントや起動プリセットだけを見て「3D LiDARがNav2へ入っている」と判断しないこと。

### 3.5 Hokuyoエイリアスとソース構成

`hokuyo` は `urg_node2` を起動するが、`src/urg_node2` はrobotbase_wsに含まれない。aptまたは別overlayで提供されているかを確認する。

```bash
ros2 pkg prefix urg_node2
ros2 topic info /scan -v
```

### 3.6 `sirius_navigation` の旧依存

`package.xml` にRTAB-Map依存が残るが、RTAB-MapソースはSIRIUS側にのみある。使用機能と依存宣言の整理が未完了。

### 3.7 フレーム名はSIRIUS名のまま

新しいロボットでも `sirius3/odom` と `sirius3/base_footprint` を使う。動作上は統一されていれば問題ないが、将来名称変更する場合はNav2、EKF、Roboteq、URDF、地図関連を一括変更する必要がある。

## 4. 変更後チェックリスト

### 車輪・encoder値を変えたとき

- 直進1 m指令に対する実移動距離
- その場1回転に対するyaw
- `/odom` の前進符号と左右旋回符号
- `encoder_sign_r/l`
- `wheel_circumference`、`track_width`、`pulse`

### 車体寸法を変えたとき

- global/local footprintを同時更新
- URDF/SDFのcollision形状を確認
- inflation radiusが外接半径以上か確認
- センサー自己点がfootprint内でclearされるか確認

### センサーを変えたとき

- 実topic名とmessage type
- `header.frame_id`
- base frameまでのTF
- 周波数とtimestamp
- AMCL、global costmap、local costmap、collision monitorの全参照箇所

### 速度経路を変えたとき

次が一筆書きになり、同一topicへ複数の最終publisherが競合しないことを確認する。

```text
controller -> smoother -> safety filter -> mux -> motor driver
```

### ビルド後

```bash
source ~/robotbase_ws/install/setup.bash
ros2 pkg prefix nav2_bringup
ros2 pkg prefix sirius_navigation
ros2 pkg prefix roboteq_ros2_driver
```

別ワークスペースを後からsourceしていないことも確認する。
