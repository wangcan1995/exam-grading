"""生成测试答题卡图片 + 对应的答题卡模板 JSON。

用途:
1. 生成一张模拟答题卡图片(含四角锚点 + 几道选择题的选项圆圈)
2. 同时输出匹配的 template_json，直接用于创建试卷

这样我们能"自产自销"地验证整条判分流水线，不依赖真实扫描件。
"""
import json
from pathlib import Path

import cv2
import numpy as np

# ---- 画布参数 (对应 settings.ANSWER_SHEET_xxx) ----
W, H = 1240, 1754                  # A4 @ 150dpi
ANCHOR_SIZE = 50                   # 锚点方框边长
ANCHOR_MARGIN = 60                 # 锚点到边缘距离
BUBBLE_RADIUS = 28                 # 选项圆圈半径
OPTION_GAP = 90                    # 同一题选项间距
QUESTION_GAP = 110                 # 题目间距

# ---- 测试题目定义 (与生成的图保持一致) ----
# correct_answer 是"标准答案"，gen_images 时学生会涂别的(模拟答题)
TEST_QUESTIONS = [
    {"no": "1", "correct": "A", "options": 4},   # ABCD
    {"no": "2", "correct": "C", "options": 4},
    {"no": "3", "correct": "B", "options": 4},
    {"no": "4", "correct": "D", "options": 4},
    {"no": "5", "correct": "A", "options": 4},
]

# 学生作答 (故意有对有错，验证判分)
STUDENT_ANSWERS = ["A", "C", "D", "A", "A"]     # 对 对 错 错 对


def _draw_anchors(img: np.ndarray) -> list[tuple[int, int]]:
    """画四角锚点(黑色实心方块)，中心位于四角内侧 ANCHOR_MARGIN 处。

    锚点中心坐标会写入模板 JSON，作为透视矫正的参考锚点(dst)，
    使矫正后图与模板坐标系严格一致。
    """
    positions = [
        (ANCHOR_MARGIN, ANCHOR_MARGIN),                        # TL
        (W - ANCHOR_MARGIN, ANCHOR_MARGIN),                    # TR
        (W - ANCHOR_MARGIN, H - ANCHOR_MARGIN),                # BR
        (ANCHOR_MARGIN, H - ANCHOR_MARGIN),                    # BL
    ]
    half = ANCHOR_SIZE // 2
    for cx, cy in positions:
        cv2.rectangle(
            img,
            (cx - half, cy - half),
            (cx + half, cy + half),
            (0, 0, 0), -1,
        )
    return positions


def _option_labels(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(n)]


def _draw_questions(
    img: np.ndarray, student_answers: list[str]
) -> list[dict]:
    """画题目: 题号 + 选项圆圈(学生选中的涂黑)。返回模板坐标。"""
    template = []
    start_y = 300

    for qi, q in enumerate(TEST_QUESTIONS):
        qy = start_y + qi * QUESTION_GAP
        labels = _option_labels(q["options"])
        # 选项从 x=300 开始排开
        start_x = 320

        # 题号文字
        cv2.putText(
            img, f"{q['no']}.", (160, qy + 10),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2,
        )

        bubbles = []
        student_choice = student_answers[qi]
        for oi, label in enumerate(labels):
            cx = start_x + oi * OPTION_GAP
            cy = qy
            # 画空心圆
            cv2.circle(img, (cx, cy), BUBBLE_RADIUS, (0, 0, 0), 2)
            # 选项字母
            cv2.putText(
                img, label, (cx - 8, cy + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2,
            )
            # 学生选中 → 涂黑 (实心圆，模拟涂卡)
            if label == student_choice:
                cv2.circle(img, (cx, cy), BUBBLE_RADIUS - 4, (0, 0, 0), -1)

            bubbles.append({
                "option": label, "cx": float(cx), "cy": float(cy),
                "radius": float(BUBBLE_RADIUS),
            })

        template.append({
            "question_no": q["no"],
            "correct_answer": q["correct"],
            "score": 2.0,
            "options": bubbles,
        })

    return template


def generate(output_dir: str = "scripts/sample_data"):
    """生成测试答题卡图 + 模板 JSON。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 白底
    img = np.full((H, W, 3), 255, dtype=np.uint8)
    anchor_positions = _draw_anchors(img)
    template = _draw_questions(img, STUDENT_ANSWERS)

    # 锚点坐标写入模板，作为透视矫正参考(保证坐标系一致)
    anchor_meta = {
        "top_left": list(anchor_positions[0]),
        "top_right": list(anchor_positions[1]),
        "bottom_right": list(anchor_positions[2]),
        "bottom_left": list(anchor_positions[3]),
    }

    # 注: 暂不旋转。skew 矫正依赖文档大轮廓，无边框白底图检测不可靠，
    # 旋转会导致坐标系偏移。先验证 OMR 判分核心逻辑(坐标系严格一致)，
    # 歪斜容错作为后续增强(可加文档外边框或换 deskew 算法)。
    img_path = out / "sample_sheet_1.png"
    ok, buf = cv2.imencode(".png", img)
    buf.tofile(str(img_path))
    print(f"[OK] 答题卡图片已生成: {img_path}")

    # 模板 JSON (含锚点参考坐标 + 题目布局)
    tpl_obj = {"anchors": anchor_meta, "questions": template}
    tpl_path = out / "template.json"
    tpl_path.write_text(
        json.dumps(tpl_obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] 答题卡模板已生成: {tpl_path}")

    # 期望判分结果 (用于断言)。每题固定 2 分 (与 _draw_questions 中一致)
    SCORE_PER_Q = 2.0
    correct_answers = [q["correct"] for q in TEST_QUESTIONS]
    expected = {
        "student_answers": STUDENT_ANSWERS,
        "correct_answers": correct_answers,
        "expected_correct_indices": [
            i for i, (a, c) in enumerate(zip(STUDENT_ANSWERS, correct_answers))
            if a == c
        ],
        "expected_score": sum(
            SCORE_PER_Q for a, c in zip(STUDENT_ANSWERS, correct_answers) if a == c
        ),
        "total_score": len(TEST_QUESTIONS) * SCORE_PER_Q,
    }
    (out / "expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] 期望结果已生成: {out / 'expected.json'}")
    print(f"     学生答案: {STUDENT_ANSWERS}")
    print(f"     标准答案: {[q['correct'] for q in TEST_QUESTIONS]}")
    print(f"     期望得分: {expected['expected_score']}/{expected['total_score']}")
    return template


if __name__ == "__main__":
    generate()
