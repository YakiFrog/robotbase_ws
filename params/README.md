# ココちゃん パラメータ

このフォルダをココちゃん固有パラメータの正本とする。`src/navigation2`、`src/slam_toolbox`、`src/velodyne` にある上流パッケージの既定ファイルは編集しない。

- `real/`: 実機用。Nav2、SLAM Toolbox、twist_mux、Roboteq、IMU、EKF、Velodyne。
- `sim/`: Gazebo用。Nav2、SLAM Toolbox、twist_mux、点群からLaserScanへの変換、停止時のゼロ速度発行。
- `common/`: 実機・シミュレーション共通。キーボード手動操作とFoxglove Bridge。

Nav2・SLAM Toolbox・twist_muxは、差分を直接比較して個別に調整できるよう実機用とシミュレーション用を別ファイルにしている。

通常はlaunchの既定値でこのフォルダが使われる。別ファイルを試す場合は、各launchへ `params_file:=...` または `slam_config_file:=...` を渡す。
