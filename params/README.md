# ココちゃん パラメータ

このフォルダをココちゃん固有パラメータの正本とする。`src/navigation2`、`src/slam_toolbox`、`src/velodyne` にある上流パッケージの既定ファイルは編集しない。

- `real/`: 実機用。Nav2、SLAM Toolbox、twist_mux、Roboteq、IMU、EKF、Velodyne。
- `sim/`: Gazebo用。Nav2、SLAM Toolbox、twist_mux、点群からLaserScanへの変換、停止時のゼロ速度発行。
- `common/`: 実機・シミュレーション共通。キーボード手動操作とFoxglove Bridge。

Nav2・SLAM Toolbox・twist_muxは、差分を直接比較して個別に調整できるよう実機用とシミュレーション用を別ファイルにしている。

Nav2のローカルコントローラは実機・シミュレーションともMPPIを使用する。ココちゃんの長方形footprint全体で障害物との衝突を評価するため、`CostCritic.consider_footprint`を有効にしている。

MPPIには固定の巡航速度パラメータがないため、実機・シミュレーションとも`vx_max`とvelocity smootherの前進上限を`0.60 m/s`にして、これを運用上の基準速度とする。低速へ偏らないよう、前後速度のサンプリング幅を`vx_std: 0.30`、操作量ペナルティをNav2標準の`gamma: 0.015`、経路進行評価を`PathFollowCritic.cost_weight: 12.0`・`offset_from_furthest: 11`としている。十分な空き領域の直線では上限付近を狙い、曲線、障害物付近、ゴール付近では自動的に減速する。

実機用は、モータが反応しない前後速度`0.10 m/s`未満をMPPIの`VelocityDeadbandCritic`、controllerのodom閾値、velocity smootherのdeadbandへ設定している。シミュレーション用も低速停滞を避けるため、MPPI Criticを0.12 m/s、odom閾値とsmootherを0.10 m/sとし、`sim/keyop.yaml`の直進刻みを0.20 m/sにする。角速度の不感帯は実測値が得られるまで0とする。

実機Roboteqの`speed_scale`はモータ指令側だけの校正値で、現在は`0.52`である。動的変更はビルド・再起動不要、YAMLへ保存した値は次回driver起動時に読み込まれる。調整手順とodom校正との区別は[構成資料](../DOCS/CONFIGURATION.md#実機の指令速度校正)を参照する。

通常はlaunchの既定値でこのフォルダが使われる。別ファイルを試す場合は、各launchへ `params_file:=...` または `slam_config_file:=...` を渡す。
