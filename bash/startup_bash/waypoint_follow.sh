#!/bin/bash
set -u

mode="${1:-real}"
case "${mode}" in
    real) use_sim_time=false ;;
    sim) use_sim_time=true ;;
    *)
        echo "Usage: $0 real|sim"
        exit 2
        ;;
esac

workspace_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
waypoints_dir="${workspace_root}/maps_waypoints/waypoints"
mkdir -p "${waypoints_dir}"

mapfile -t waypoint_files < <(find "${waypoints_dir}" -maxdepth 1 -type f -name '*.yaml' | sort)
if [ "${#waypoint_files[@]}" -eq 0 ]; then
    echo "ウェイポイントがありません: ${waypoints_dir}"
    echo "先に koko_waypoint_save または koko_waypoint_save_sim で地点を保存してください。"
    exit 1
fi

echo "========================================="
echo " ココちゃん ウェイポイント選択 (${mode})"
echo "========================================="
for index in "${!waypoint_files[@]}"; do
    printf '  [%d] %s\n' "$((index + 1))" "$(basename "${waypoint_files[index]}")"
done
read -r -p "番号を入力 [1]: " selection
selection="${selection:-1}"
if ! [[ "${selection}" =~ ^[0-9]+$ ]] || \
   [ "${selection}" -lt 1 ] || [ "${selection}" -gt "${#waypoint_files[@]}" ]; then
    echo "無効な選択です: ${selection}"
    exit 1
fi
waypoint_file="${waypoint_files[$((selection - 1))]}"

read -r -p "開始番号 [1]: " start_index
start_index="${start_index:-1}"
read -r -p "通常の中間点切替距離[m] [1.0]: " threshold
threshold="${threshold:-1.0}"
read -r -p "無限ループしますか [y/N]: " loop_answer
loop_value=false
if [[ "${loop_answer:-}" =~ ^[yY]$ ]]; then
    loop_value=true
fi

echo "ウェイポイント: ${waypoint_file}"
echo "開始番号: ${start_index}, 切替距離: ${threshold} m, loop: ${loop_value}"

# 待機中や異常終了時にも、twist_muxの無期限stop lockを必ず解除する。
release_stop_lock() {
    timeout 3 ros2 topic pub --once /stop std_msgs/msg/Bool '{data: false}' \
        >/dev/null 2>&1 || true
}
trap release_stop_lock EXIT

ros2 run robotbase_waypoint waypoint_follow --ros-args \
    -p use_sim_time:="${use_sim_time}" \
    -p waypoint_file:="${waypoint_file}" \
    -p start_index:="${start_index}" \
    -p default_threshold:="${threshold}" \
    -p loop:="${loop_value}" \
    -p base_frame:="${ROBOTBASE_TF_PREFIX:-robot}/base_footprint"
