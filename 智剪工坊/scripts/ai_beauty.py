# -*- coding: utf-8 -*-
"""
智剪工坊 · beauty 子技能
美颜:磨皮 + 美白 + 瘦脸 + 大眼(L2 标准版)

用法:
  # 4 个独立参数
  python beauty.py --input v.mp4 --output out.mp4 --smooth 0.5 --whiten 0.3 --slim 0.3 --enlarge 0.3

  # 用预设
  python beauty.py --input v.mp4 --output out.mp4 --preset natural
  python beauty.py --input v.mp4 --output out.mp4 --preset strong

  # 只磨皮(瘦脸/大眼关闭)
  python beauty.py --input v.mp4 --output out.mp4 --smooth 0.5 --slim 0 --enlarge 0

技术方案:
  - 人脸检测:mediapipe 0.10 tasks.FaceLandmarker(478 关键点 = 468 mesh + 10 iris)
  - 模型:首次运行自动下载到 assets/face_landmarker.task(3.7MB)
  - 磨皮:脸部 oval 区域做高斯模糊,alpha mask blend
  - 美白:HSV 提亮 + 降饱和
  - 瘦脸/大眼:Delaunay 三角剖分 + 仿射变形(经典 CV)
  - 视频:逐帧处理(慢 5-10x),音频 ffmpeg 单独处理后 mux

依赖:opencv-python, mediapipe>=0.10, numpy


📖 SKILL.md §14 索引 → REQUIRED: read references/12-beauty.md
"""
import argparse
import os
import sys
import subprocess
import tempfile
import shutil
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, log_progress, safe_run,
    get_ffmpeg_path, ASSETS_DIR, setup_logging,
)

try:
    import cv2
    import numpy as np
    import mediapipe as mp
    MEDIAPIPE_OK = True
except ImportError as e:
    MEDIAPIPE_OK = False
    _IMPORT_ERR = str(e)


# ============================================================
# 关键点索引(mediapipe FaceLandmarker 478 点:468 mesh + 10 iris)
# ============================================================

FACE_OVAL_INDICES = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]

SLIM_INDICES = [
    234, 93, 132, 58,
    454, 323, 361, 288,
    152, 175, 171, 148, 176, 149,
    207, 187, 123, 116,
    427, 411, 352, 345,
]

LEFT_EYE_INDICES = [33, 133, 160, 144, 158, 153, 145, 246, 161, 163, 157, 154, 155, 173]
RIGHT_EYE_INDICES = [362, 263, 385, 380, 386, 373, 374, 466, 388, 390, 384, 381, 382, 398]
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473


# ============================================================
# 预设
# ============================================================

PRESETS = {
    "off":       {"smooth": 0.0, "whiten": 0.0, "slim": 0.0, "enlarge": 0.0},
    "slight":    {"smooth": 0.3, "whiten": 0.15, "slim": 0.2, "enlarge": 0.2},
    "natural":   {"smooth": 0.5, "whiten": 0.25, "slim": 0.3, "enlarge": 0.3},
    "strong":    {"smooth": 0.7, "whiten": 0.4, "slim": 0.5, "enlarge": 0.4},
    "max":       {"smooth": 0.9, "whiten": 0.5, "slim": 0.7, "enlarge": 0.5},
}

FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
FACE_LANDMARKER_MODEL_PATH = ASSETS_DIR / "face_landmarker.task"


# mediapipe 0.10.35 在 Windows 上有 bug:模型路径含非 ASCII(中文)字符会
# 报 "Unable to open file"。fallback:复制到 C:\ 根目录的纯 ASCII 路径。
SAFE_MODEL_DIR = Path("C:/zhijian_models")
SAFE_MODEL_PATH = SAFE_MODEL_DIR / "face_landmarker.task"


def _has_non_ascii(s) -> bool:
    try:
        s.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def ensure_model() -> Path:
    """下载 + 准备 face_landmarker 模型(自动处理 mediapipe 0.10 Windows bug)"""
    ensure_dir(ASSETS_DIR)
    if not FACE_LANDMARKER_MODEL_PATH.exists():
        log_info(f"下载 face_landmarker 模型(首次): {FACE_LANDMARKER_MODEL_URL}")
        try:
            urllib.request.urlretrieve(
                FACE_LANDMARKER_MODEL_URL,
                str(FACE_LANDMARKER_MODEL_PATH),
            )
            log_info(f"模型已保存: {FACE_LANDMARKER_MODEL_PATH} "
                     f"({FACE_LANDMARKER_MODEL_PATH.stat().st_size // 1024} KB)")
        except Exception as e:
            log_error(f"模型下载失败: {e}\n  修复: 手动从 {FACE_LANDMARKER_MODEL_URL} "
                      f"下载到 {FACE_LANDMARKER_MODEL_PATH}")
            sys.exit(6)

    if _has_non_ascii(str(FACE_LANDMARKER_MODEL_PATH)):
        ensure_dir(SAFE_MODEL_DIR)
        if not SAFE_MODEL_PATH.exists() or \
           SAFE_MODEL_PATH.stat().st_size != FACE_LANDMARKER_MODEL_PATH.stat().st_size:
            shutil.copy2(FACE_LANDMARKER_MODEL_PATH, SAFE_MODEL_PATH)
            log_warn(f"模型路径含非 ASCII,已复制到 {SAFE_MODEL_PATH}(mediapipe Windows bug)")
        return SAFE_MODEL_PATH
    return FACE_LANDMARKER_MODEL_PATH


def create_landmarker(running_mode):
    model_path = ensure_model()
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=running_mode,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return FaceLandmarker.create_from_options(options)


# ============================================================
# 关键步骤
# ============================================================

def check_deps():
    if not MEDIAPIPE_OK:
        log_error(f"缺依赖:{_IMPORT_ERR}\n  修复: pip install mediapipe opencv-python numpy")
        sys.exit(3)


def get_landmarks(landmarker, frame_bgr, timestamp_ms=None):
    """检测人脸,返回 478 个关键点 (x, y) 像素坐标"""
    h, w = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    if timestamp_ms is None:
        result = landmarker.detect(mp_image)
    else:
        result = landmarker.detect_for_video(mp_image, timestamp_ms)
    if not result.face_landmarks:
        return None
    face = result.face_landmarks[0]
    return [(int(lm.x * w), int(lm.y * h)) for lm in face]


def get_face_mask(shape, landmarks, feather=15):
    h, w = shape[:2]
    oval_points = np.array([landmarks[i] for i in FACE_OVAL_INDICES], dtype=np.int32)
    mask = np.zeros((h, w), dtype=np.float32)
    cv2.fillPoly(mask, [oval_points], 1.0)
    if feather > 0:
        ksize = feather * 2 + 1
        mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)
    return mask


def apply_smoothing(frame, face_mask, strength):
    if strength <= 0:
        return frame
    blurred = cv2.GaussianBlur(frame, (15, 15), 0)
    mask3 = np.stack([face_mask] * 3, axis=-1)
    return (frame * (1 - mask3 * strength) + blurred * (mask3 * strength)).astype(np.uint8)


def apply_whitening(frame, face_mask, strength):
    if strength <= 0:
        return frame
    white = cv2.convertScaleAbs(frame, alpha=1.0 + 0.1 * strength, beta=int(8 * strength))
    hsv = cv2.cvtColor(white, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= (1.0 - 0.15 * strength)
    white = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    mask3 = np.stack([face_mask] * 3, axis=-1)
    return (frame * (1 - mask3 * strength) + white * (mask3 * strength)).astype(np.uint8)


def compute_slim_landmarks(landmarks, strength):
    if strength <= 0:
        return list(landmarks)
    new_lm = list(landmarks)
    cx = (landmarks[234][0] + landmarks[454][0]) // 2
    for idx in SLIM_INDICES:
        x, y = landmarks[idx]
        new_x = int(x + (cx - x) * strength * 0.35)
        new_lm[idx] = (new_x, y)
    return new_lm


def compute_enlarge_landmarks(landmarks, strength):
    if strength <= 0:
        return list(landmarks)
    new_lm = list(landmarks)
    left_center = landmarks[LEFT_IRIS_CENTER]
    right_center = landmarks[RIGHT_IRIS_CENTER]
    for eye_indices, center in [(LEFT_EYE_INDICES, left_center),
                                 (RIGHT_EYE_INDICES, right_center)]:
        cx, cy = center
        for idx in eye_indices:
            x, y = landmarks[idx]
            scale = 1.0 + strength * 0.4
            new_x = int(cx + (x - cx) * scale)
            new_y = int(cy + (y - cy) * scale)
            new_lm[idx] = (new_x, new_y)
    return new_lm


def warp_face(frame, src_landmarks, dst_landmarks):
    """Delaunay 三角剖分 + 仿射变形"""
    h, w = frame.shape[:2]
    rect = (0, 0, w, h)
    subdiv = cv2.Subdiv2D(rect)
    src_lookup = {}
    for i, lm in enumerate(src_landmarks):
        src_lookup[(int(lm[0]), int(lm[1]))] = i
    for pt in src_landmarks:
        subdiv.insert((int(pt[0]), int(pt[1])))
    triangles = subdiv.getTriangleList()
    output = frame.copy()
    for tri in triangles:
        idx_list = []
        for v in range(3):
            vx, vy = int(tri[v * 2]), int(tri[v * 2 + 1])
            idx = src_lookup.get((vx, vy))
            if idx is None:
                found = False
                for (kx, ky), ki in src_lookup.items():
                    if abs(kx - vx) <= 1 and abs(ky - vy) <= 1:
                        idx_list.append(ki)
                        found = True
                        break
                if not found:
                    break
            else:
                idx_list.append(idx)
        if len(idx_list) != 3:
            continue
        src_tri = np.array([src_landmarks[i] for i in idx_list], dtype=np.float32)
        dst_tri = np.array([dst_landmarks[i] for i in idx_list], dtype=np.float32)
        try:
            M = cv2.getAffineTransform(src_tri, dst_tri)
            warped = cv2.warpAffine(frame, M, (w, h), None,
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT_101)
            mask_tri = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(mask_tri, np.int32(dst_tri), 255)
            output = np.where(mask_tri[..., None].astype(bool), warped, output)
        except cv2.error:
            continue
    return output


def process_frame(frame, landmarker, smooth, whiten, slim, enlarge, timestamp_ms=None):
    landmarks = get_landmarks(landmarker, frame, timestamp_ms)
    if landmarks is None:
        return frame

    out = frame
    if smooth > 0 or whiten > 0:
        face_mask = get_face_mask(out.shape, landmarks, feather=15)
        if smooth > 0:
            out = apply_smoothing(out, face_mask, smooth)
        if whiten > 0:
            out = apply_whitening(out, face_mask, whiten)

    if slim > 0 or enlarge > 0:
        src_lm = landmarks
        dst_lm = src_lm
        if slim > 0:
            dst_lm = compute_slim_landmarks(dst_lm, slim)
        if enlarge > 0:
            dst_lm = compute_enlarge_landmarks(dst_lm, enlarge)
        warped = warp_face(out, src_lm, dst_lm)
        face_mask = get_face_mask(out.shape, landmarks, feather=25)
        mask3 = np.stack([face_mask] * 3, axis=-1)
        out = (out * (1 - mask3 * 0.85) + warped * (mask3 * 0.85)).astype(np.uint8)

    return out


# ============================================================
# 主流程
# ============================================================

def process_video(input_path, output_path, smooth, whiten, slim, enlarge, max_frames=None):
    check_deps()
    log_section(f"美颜: {Path(input_path).name}")
    log_info(f"参数: smooth={smooth}, whiten={whiten}, slim={slim}, enlarge={enlarge}")

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        log_error(f"无法打开视频: {input_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    log_info(f"视频: {w}x{h} @ {fps:.1f}fps, 共 {total} 帧")

    ensure_dir(Path(output_path).parent)
    tmp_dir = Path(tempfile.mkdtemp(prefix="beauty_"))
    tmp_video = tmp_dir / "video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (w, h))
    if not writer.isOpened():
        log_error(f"无法创建输出: {tmp_video}")
        cap.release()
        sys.exit(1)

    VisionRunningMode = mp.tasks.vision.RunningMode
    landmarker = create_landmarker(VisionRunningMode.VIDEO)
    frame_idx = 0
    faces_detected = 0
    frame_errors = 0
    import time as _time
    start_time = _time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if max_frames and frame_idx >= max_frames:
                break
            timestamp_ms = int(frame_idx * 1000 / fps)
            try:
                new_frame = process_frame(frame, landmarker, smooth, whiten, slim, enlarge, timestamp_ms)
                if new_frame is not frame:
                    faces_detected += 1
                writer.write(new_frame)
            except Exception as e:
                # 单帧失败不中断整批,写原帧
                frame_errors += 1
                if frame_errors <= 3:
                    log_warn(f"第 {frame_idx} 帧处理失败(用原帧): {e}")
                writer.write(frame)
            frame_idx += 1
            if frame_idx % 10 == 0 or frame_idx == total:
                elapsed = _time.time() - start_time
                fps_proc = frame_idx / elapsed if elapsed > 0 else 0
                log_progress(frame_idx, total, f"处理中 ({fps_proc:.1f} fps)")
    except KeyboardInterrupt:
        log_warn("用户中断")
    finally:
        cap.release()
        writer.release()
        landmarker.close()

    elapsed_total = _time.time() - start_time
    log_info(f"处理完成: {frame_idx} 帧, 检出脸 {faces_detected} 帧, 失败 {frame_errors} 帧, 用时 {elapsed_total:.1f}s")

    log_info("合并音频...")
    ffmpeg = get_ffmpeg_path()
    has_audio = False
    try:
        probe = subprocess.run(
            [ffmpeg, "-i", str(input_path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        has_audio = "Audio:" in probe.stderr
    except Exception:
        has_audio = False

    if has_audio:
        audio_tmp = tmp_dir / "audio.aac"
        run_ffmpeg([
            "-i", str(input_path),
            "-vn", "-acodec", "copy",
            str(audio_tmp),
        ], timeout=300)
        run_ffmpeg([
            "-i", str(tmp_video),
            "-i", str(audio_tmp),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path),
        ], timeout=600)
    else:
        run_ffmpeg([
            "-i", str(tmp_video),
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ], timeout=600)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def process_image(input_path, output_path, smooth, whiten, slim, enlarge):
    check_deps()
    log_section(f"美颜图片: {Path(input_path).name}")
    log_info(f"参数: smooth={smooth}, whiten={whiten}, slim={slim}, enlarge={enlarge}")

    frame = cv2.imread(str(input_path))
    if frame is None:
        log_error(f"无法读图: {input_path}")
        sys.exit(1)

    VisionRunningMode = mp.tasks.vision.RunningMode
    landmarker = create_landmarker(VisionRunningMode.IMAGE)
    try:
        out = process_frame(frame, landmarker, smooth, whiten, slim, enlarge)
    finally:
        landmarker.close()

    cv2.imwrite(str(output_path), out)
    log_info(f"输出: {output_path}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 美颜(L2 标准版:磨皮+美白+瘦脸+大眼)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "预设 (--preset): " + ", ".join(PRESETS.keys()) + "\n"
            "示例: --preset natural 或单独调 --smooth 0.5 --slim 0.3"
        ),
    )
    parser.add_argument("-i", "--input", required=True, help="输入视频或图片")
    parser.add_argument("-o", "--output", required=True, help="输出路径")
    parser.add_argument("--preset", choices=list(PRESETS.keys()),
                       help="用预设档位(natural/strong/...)")
    parser.add_argument("--smooth", type=float, default=None, help="磨皮强度 0-1")
    parser.add_argument("--whiten", type=float, default=None, help="美白强度 0-1")
    parser.add_argument("--slim", type=float, default=None, help="瘦脸强度 0-1")
    parser.add_argument("--enlarge", type=float, default=None, help="大眼强度 0-1")
    parser.add_argument("--max-frames", type=int, default=None,
                       help="最多处理多少帧(测试用,默认全跑)")
    parser.add_argument("--verbose", action="store_true", help="显示 debug 日志")
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    if args.preset:
        p = PRESETS[args.preset]
        smooth = args.smooth if args.smooth is not None else p["smooth"]
        whiten = args.whiten if args.whiten is not None else p["whiten"]
        slim = args.slim if args.slim is not None else p["slim"]
        enlarge = args.enlarge if args.enlarge is not None else p["enlarge"]
    else:
        smooth = args.smooth or 0.0
        whiten = args.whiten or 0.0
        slim = args.slim or 0.0
        enlarge = args.enlarge or 0.0

    for name, val in [("smooth", smooth), ("whiten", whiten),
                      ("slim", slim), ("enlarge", enlarge)]:
        if not 0 <= val <= 1:
            log_error(f"--{name} 必须在 0-1 之间: {val}")
            sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        log_error(f"输入不存在: {input_path}")
        sys.exit(1)
    is_image = input_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    if is_image:
        process_image(input_path, args.output, smooth, whiten, slim, enlarge)
    else:
        process_video(input_path, args.output, smooth, whiten, slim, enlarge, args.max_frames)


if __name__ == "__main__":
    safe_run(main)()
